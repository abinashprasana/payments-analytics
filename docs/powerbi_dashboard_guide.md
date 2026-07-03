# Power BI Dashboard Guide — Payments Analytics Project

> **Who this is for:** Complete beginners to Power BI who want to turn this project's data into a portfolio-worthy dashboard that shows real analytical skill.

---

## 1. What This Project Contains (Plain English)

This project is a **simulated corporate payments system** — like a mini version of how Stripe, PayPal, or a bank's back-end works. It has **6 tables** of realistic synthetic data covering 3 years (2022–2024):

| Table | What It Holds | Row Count |
|---|---|---|
| `customers.csv` | People who use the payment platform | 5,000 |
| `accounts.csv` | Bank-style accounts owned by customers | 6,000 |
| `merchants.csv` | Shops/businesses receiving payments | 800 |
| `transactions.csv` | Every payment event (purchase, refund, transfer) | 80,000 |
| `settlements.csv` | Money paid out to merchants after fees | 70,000 |
| `fraud_flags.csv` | Transactions flagged as suspicious | 2,500 |

---

## 2. The Files You Import Into Power BI

All 6 CSV files live in `data/raw/`. Import all of them.

### Step-by-Step Import:
1. Open Power BI Desktop → **Get Data** → **Text/CSV**
2. Import each file one at a time:
   - `data/raw/customers.csv`
   - `data/raw/accounts.csv`
   - `data/raw/merchants.csv`
   - `data/raw/transactions.csv`
   - `data/raw/settlements.csv`
   - `data/raw/fraud_flags.csv`

---

## 3. What Each Column Means (Column Dictionary)

### customers.csv
| Column | Type | Values / Notes |
|---|---|---|
| `customer_id` | Number | Unique ID (1–5000) |
| `full_name` | Text | Customer's name |
| `email` | Text | Unique email |
| `country` | Text | One of 10 countries (US, UK, Canada, Germany, France, Australia, Singapore, India, Japan, Brazil) |
| `join_date` | Date | When they joined the platform (2022–2024) |
| `segment` | Text | **retail** (80%), **business** (15%), **premium** (5%) |
| `is_active` | True/False | Whether the customer is still active (90% are True) |

### accounts.csv
| Column | Type | Values / Notes |
|---|---|---|
| `account_id` | Number | Unique ID |
| `customer_id` | Number | Links to customers table |
| `account_type` | Text | **current** (60%), **savings** (35%), **merchant** (5%) |
| `currency` | Text | EUR (most common), GBP, AUD, CAD |
| `opened_date` | Date | When the account was opened |
| `status` | Text | **active** (92%), **closed** (5%), **suspended** (3%) |

### merchants.csv
| Column | Type | Values / Notes |
|---|---|---|
| `merchant_id` | Number | Unique ID (1–800) |
| `merchant_name` | Text | Company name |
| `category` | Text | Retail, Travel, Entertainment, Electronics, Utilities, Food & Beverage, Services, Healthcare |
| `country` | Text | Same 10 countries |
| `registration_date` | Date | When the merchant joined |
| `risk_tier` | Text | **low** (85%), **medium** (12%), **high** (3%) |

### transactions.csv
| Column | Type | Values / Notes |
|---|---|---|
| `transaction_id` | Number | Unique ID (1–80,000) |
| `account_id` | Number | Links to accounts table |
| `merchant_id` | Number | Links to merchants table (blank for transfers) |
| `amount` | Decimal | €1.00–€5,000.00 (refunds capped at €300) |
| `currency` | Text | EUR, GBP, AUD, CAD |
| `transaction_date` | DateTime | 2022–2024, includes time |
| `transaction_type` | Text | **purchase** (80%), **transfer** (15%), **refund** (5%) |
| `status` | Text | **completed** (90%), **failed** (8%), **pending** (2%) |

### settlements.csv
| Column | Type | Values / Notes |
|---|---|---|
| `settlement_id` | Number | Unique ID |
| `transaction_id` | Number | Links to transactions table (1-to-1) |
| `settlement_date` | DateTime | 1–5 days after the transaction |
| `settled_amount` | Decimal | Amount paid to merchant (after fees) |
| `processing_fee` | Decimal | Fee charged (1–5% depending on risk tier) |
| `status` | Text | **settled** (94%), **delayed** (5%), **disputed** (1%) |

### fraud_flags.csv
| Column | Type | Values / Notes |
|---|---|---|
| `flag_id` | Number | Unique ID |
| `transaction_id` | Number | Links to transactions table |
| `flagged_date` | DateTime | Within 4 hours of the transaction |
| `flag_reason` | Text | Velocity Limit Exceeded / High Risk Country Match / Suspicious Amount Spike / Mismatched Billing Details / Card-Not-Present Anomaly |
| `is_resolved` | True/False | Whether the flag was investigated (80% = True) |
| `resolved_date` | DateTime | 1–7 days after flagging (blank if not resolved) |

---

## 4. How to Connect the Tables (Data Model / Relationships)

In Power BI, go to **Model view** and set up these connections. This is the **most important step** — without it, your visuals won't work correctly.

```
customers  ──(1:Many)──  accounts  ──(1:Many)──  transactions  ──(1:1)──  settlements
                                                       │
                                                  (Many:1)
                                                       │
                                                  merchants
                                                       │
                                              transactions ──(1:1)──  fraud_flags
```

### Exact Relationships to Create:
| From Table | Column | To Table | Column | Type |
|---|---|---|---|---|
| customers | customer_id | accounts | customer_id | One-to-Many |
| accounts | account_id | transactions | account_id | One-to-Many |
| merchants | merchant_id | transactions | merchant_id | One-to-Many |
| transactions | transaction_id | settlements | transaction_id | One-to-One |
| transactions | transaction_id | fraud_flags | transaction_id | One-to-One |

---

## 5. Data Cleaning Steps (Do These in Power Query)

Before building visuals, clean the data. In Power BI, click **Transform Data**.

### For `transactions.csv`:
- Change `transaction_date` column type → **Date/Time**
- Change `amount` column type → **Decimal Number**
- Change `merchant_id` column type → **Whole Number** (Power BI may error on blanks — replace blank/null with 0 or keep as-is)
- Add a new column: `transaction_year_month` = `Date.ToText([transaction_date], "yyyy-MM")`

### For `customers.csv`:
- Change `join_date` → **Date**
- Change `is_active` → **True/False** (it may import as text)

### For `settlements.csv`:
- Change `settlement_date` → **Date/Time**
- Change `settled_amount` and `processing_fee` → **Decimal Number**

### For `fraud_flags.csv`:
- Change `flagged_date` and `resolved_date` → **Date/Time**
- Change `is_resolved` → **True/False**

---

## 6. DAX Measures to Create (Copy-Paste Ready)

In Power BI, go to the **transactions** table and create these **measures** (click "New Measure").

```dax
-- Basic KPIs
Total Completed Transactions = 
    CALCULATE(COUNTROWS(transactions), transactions[status] = "completed")

Total Transaction Volume = 
    CALCULATE(SUM(transactions[amount]), transactions[status] = "completed")

Average Transaction Value = 
    CALCULATE(AVERAGE(transactions[amount]), transactions[status] = "completed")

Total Revenue Settled = 
    SUM(settlements[settled_amount])

Total Processing Fees = 
    SUM(settlements[processing_fee])

-- Fraud Metrics
Total Fraud Flags = 
    COUNTROWS(fraud_flags)

Fraud Resolution Rate % = 
    DIVIDE(
        CALCULATE(COUNTROWS(fraud_flags), fraud_flags[is_resolved] = TRUE()),
        COUNTROWS(fraud_flags)
    ) * 100

Fraud Rate % = 
    DIVIDE([Total Fraud Flags], [Total Completed Transactions]) * 100

-- Customer Metrics
Active Customers = 
    CALCULATE(COUNTROWS(customers), customers[is_active] = TRUE())

-- Settlement Metrics
Delayed Settlements = 
    CALCULATE(COUNTROWS(settlements), settlements[status] = "delayed")

Settlement Delay Rate % = 
    DIVIDE([Delayed Settlements], COUNTROWS(settlements)) * 100

-- Transaction Failure Rate
Failed Transaction Rate % = 
    DIVIDE(
        CALCULATE(COUNTROWS(transactions), transactions[status] = "failed"),
        COUNTROWS(transactions)
    ) * 100
```

---

## 7. Dashboard Pages to Build (Recommended Layout)

Build **4 pages** — one per topic. This matches exactly what the SQL queries in this project analyze.

---

### Page 1: Executive Overview

**Purpose:** Show the big picture at a glance. This is the first thing anyone will see.

**Visuals to add:**
1. **4 KPI Cards** across the top:
   - Total Completed Transactions → `[Total Completed Transactions]`
   - Total Volume (EUR) → `[Total Transaction Volume]`
   - Average Transaction Value → `[Average Transaction Value]`
   - Active Customers → `[Active Customers]`

2. **Line + Bar combo chart** — Monthly Transaction Trends:
   - X-axis: `transaction_date` (grouped by Month)
   - Bar (Y-axis left): Count of `transaction_id`
   - Line (Y-axis right): Sum of `amount`
   - Filter: `status = completed`
   - Title: "Monthly Transaction Volume & Count (2022–2024)"

3. **Donut/Pie chart** — Transaction Types:
   - Legend: `transaction_type`
   - Values: Count of `transaction_id`
   - Title: "Transaction Type Breakdown"

4. **Slicer** — Year filter using `transaction_date` year
5. **Slicer** — Currency filter using `currency`

---

### Page 2: Merchant Performance

**Purpose:** Show which merchants are generating the most revenue and where the risk is.

**Visuals to add:**
1. **Horizontal Bar Chart** — Top 10 Merchants by Revenue:
   - Y-axis: `merchant_name`
   - X-axis: `[Total Revenue Settled]`
   - Color: `category`
   - Filter: Top 10 by settled amount
   - Title: "Merchant Revenue Leaderboard"

2. **Clustered Bar Chart** — Revenue by Category:
   - X-axis: `category` (from merchants)
   - Y-axis: `[Total Revenue Settled]`
   - Title: "Settlement Revenue by Merchant Category"

3. **Table/Matrix** — Merchant details:
   - Columns: merchant_name, category, risk_tier, Total Revenue Settled, Processing Fees
   - Sort by Revenue descending

4. **Donut Chart** — Merchants by Risk Tier:
   - Legend: `risk_tier`
   - Values: Count of `merchant_id`
   - Title: "Merchant Risk Distribution"

5. **Slicer** — Category filter
6. **Slicer** — Risk Tier filter (low / medium / high)

---

### Page 3: Fraud & Risk Overview

**Purpose:** Show compliance and risk patterns — a very impressive section for any analytics portfolio.

**Visuals to add:**
1. **3 KPI Cards** across the top:
   - Total Fraud Flags → `[Total Fraud Flags]`
   - Fraud Rate % → `[Fraud Rate %]`
   - Fraud Resolution Rate % → `[Fraud Resolution Rate %]`

2. **Bar Chart** — Fraud Rate by Merchant Category:
   - X-axis: `category` (from merchants)
   - Y-axis: `[Fraud Rate %]`
   - Color gradient (darker = higher risk)
   - Title: "Fraud Flag Rate by Merchant Category"

3. **Pie/Donut Chart** — Fraud Reasons Breakdown:
   - Legend: `flag_reason` (from fraud_flags)
   - Values: Count of `flag_id`
   - Title: "Fraud Flag Reasons Distribution"
   - Shows: Velocity Limit Exceeded, High Risk Country Match, Suspicious Amount Spike, Mismatched Billing Details, Card-Not-Present Anomaly

4. **Stacked Bar Chart** — Resolved vs Unresolved Flags by Month:
   - X-axis: `flagged_date` (Month)
   - Y-axis: Count of `flag_id`
   - Legend: `is_resolved`
   - Title: "Monthly Fraud Flag Resolution Status"

5. **Table** — High-Risk Unresolved Flags:
   - Columns: transaction_id, flagged_date, flag_reason, is_resolved
   - Filter: `is_resolved = False`

6. **Slicer** — Flag Reason filter
7. **Slicer** — Resolution Status (Resolved / Unresolved)

---

### Page 4: Customer Segments & Cohort Analysis

**Purpose:** Show customer lifetime value and retention — the most advanced analytics section.

**Visuals to add:**
1. **Bar Chart** — Customer Count by Segment & Country:
   - X-axis: `country`
   - Y-axis: Count of `customer_id`
   - Legend: `segment` (retail / business / premium)
   - Title: "Customer Distribution by Country and Segment"

2. **Donut Chart** — Active vs Inactive Customers:
   - Legend: `is_active`
   - Values: Count of `customer_id`
   - Title: "Active Customer Ratio"

3. **Bar Chart** — New Customers Joined Per Month:
   - X-axis: `join_date` (grouped by Month)
   - Y-axis: Count of `customer_id`
   - Title: "Monthly Customer Acquisition (2022–2024)"

4. **Map Visual** — Customers by Country:
   - Location: `country`
   - Size/Color: Count of `customer_id`
   - Title: "Geographic Customer Distribution"

5. **Matrix (Cohort Table)** — Customer Retention:
   - Rows: Cohort month (join_date grouped by Month)
   - Columns: Months since joining (0, 1, 2 ... 12)
   - Values: Count of distinct customers still active
   - This is the most impressive visual — it shows who keeps coming back

6. **Slicer** — Segment filter (retail / business / premium)
7. **Slicer** — Country filter

---

## 8. Suggested Dashboard Theme & Design Tips

To make it look professional (not like a default Power BI report):

1. **Use a dark theme**: Go to View → Themes → pick a dark theme or import a custom one
2. **Color palette** (matches the project's existing charts):
   - Purple: `#8A2387`
   - Orange: `#F27121`
   - Red-Pink: `#E94057`
3. **Consistent card borders**: Add subtle border lines to all visual cards
4. **Page navigation buttons**: Add buttons linking pages so it looks like an app
5. **Title on every page**: Use a text box with a large bold title
6. **Add this subtitle**: "MSc AI Portfolio Project — Synthetic Payments Intelligence (2022–2024)"

---

## 9. What Skills This Dashboard Demonstrates

When someone looks at your Power BI dashboard, here is what they will see you know:

| Skill | Where It Shows |
|---|---|
| Data modelling (star schema) | The 5-table relationship setup |
| DAX calculations | KPI cards, fraud rate %, resolution rate % |
| Time intelligence | Monthly trends, cohort retention |
| Data storytelling | 4 well-structured pages with clear titles |
| SQL knowledge | The 8 SQL queries this project already has |
| Risk/compliance analytics | Fraud & Risk page |
| Customer analytics | Cohort retention, segmentation |
| Financial analytics | Settlement fees, revenue leaderboard |

---

## 10. Quick Summary of Numbers (For Reference)

These are the approximate values you'll see in your dashboard based on the generated data:

| Metric | Approximate Value |
|---|---|
| Date range | 2022-01-01 to 2024-12-31 (3 years) |
| Total customers | 5,000 |
| Active customers | ~4,500 (90%) |
| Retail segment customers | ~4,000 (80%) |
| Business segment customers | ~750 (15%) |
| Premium segment customers | ~250 (5%) |
| Total transactions | 80,000 |
| Completed transactions | ~72,000 (90%) |
| Failed transactions | ~6,400 (8%) |
| Purchase type | ~64,000 (80%) |
| Transfer type | ~12,000 (15%) |
| Refund type | ~4,000 (5%) |
| Currencies | EUR (dominant), GBP, AUD, CAD |
| Total merchants | 800 |
| Low-risk merchants | ~680 (85%) |
| High-risk merchants | ~24 (3%) |
| Merchant categories | 8 categories |
| Total settlements | 70,000 |
| Settlement fee range | 1%–5% (based on risk tier) |
| Settled status | ~65,800 (94%) |
| Disputed settlements | ~700 (1%) |
| Total fraud flags | 2,500 |
| Fraud rate | ~3.1% of all transactions |
| Resolved fraud flags | ~2,000 (80%) |
| Fraud reasons | 5 distinct reasons |
| Countries covered | 10 countries |

---

## 11. Step-by-Step Action Plan (Do This in Order)

1. Open Power BI Desktop (download free from Microsoft if needed)
2. Import all 6 CSV files from `data/raw/`
3. Go to **Transform Data** → clean column types as listed in Section 5
4. Go to **Model view** → create the 5 relationships from Section 4
5. Go back to **Report view** → create the measures from Section 6
6. Build Page 1 (Executive Overview)
7. Build Page 2 (Merchant Performance)
8. Build Page 3 (Fraud & Risk)
9. Build Page 4 (Customer Segments)
10. Apply a dark theme and consistent colours
11. Add page navigation buttons and titles
12. Save as a `.pbix` file and add it to your portfolio/GitHub

---

*This guide was generated from the `payments_analytics_sql` project — a synthetic corporate payments analytics system built with PostgreSQL, Python, and Streamlit.*
