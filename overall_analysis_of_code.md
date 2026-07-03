# Overall Analysis of Code

This report provides a comprehensive code inspection, system architecture overview, database schema analysis, and UI layout breakdown of the `payments-analytics-sql` repository.

---

## 1. System Architecture Overview

The system is designed as a self-contained, 3-tier business intelligence (BI) application:
1. **Data Layer (PostgreSQL Database):** Models standard transactional ledger schemas including customer metrics, accounting, merchants, completed settlements, and compliance fraud alerts.
2. **Control & Scripting Layer (Python Lifecycle scripts):** Handles programmatic data generation (Faker), high-speed ingestion (COPY expert), and scheduled offline SVG/PNG image rendering (Kaleido).
3. **Application & Visualisation Layer (Streamlit & Plotly Frontend):** Serves as an interactive web-based BI tool with custom CSS branding, query caching, and client-side visualization tables.

---

## 2. Directory Structure & Code Responsibilities

* **`schema/` (Database DDL Definitions):**
  - `create_tables.sql`: Recreates the relational schema cleanly. Ensures referential integrity with foreign key actions (`ON DELETE CASCADE` on transactional relationships and `ON DELETE SET NULL` on merchant lookups).
  - `indexes.sql`: Implements optimized indexes targeting foreign keys, timestamps, and category filters. Ensures join speeds scale cleanly for large datasets.
* **`data/` (Synthetic Engine):**
  - `generate_data.py`: A parameter-driven python script leveraging the `Faker` library. Generates balanced relational CSVs under deterministic distributions (80% retail, 15% business, 5% high-value customer splits; 90% completed, 8% failed, 2% pending transaction splits).
* **`scripts/` (Database Helpers & Exporters):**
  - `db_connection.py`: Instantiates a standard connection context via `psycopg2` loading credentials from a local `.env` environment.
  - `load_data.py`: Ingests raw CSV data into PostgreSQL tables using bulk copy routines.
  - `export_charts.py`: Generates the Plotly dashboard charts programmatically and saves them to `outputs/charts/` as static PNG files via the `kaleido` engine.
* **`queries/` (SQL Analytics Scripts):**
  - Comprises 8 standalone SQL scripts demonstrating intermediate analytics queries (Window aggregates, Cohort lifecycle grids, latency averages, and Customer Lifetime Value chaining).
* **`dashboard/` (Streamlit front-end):**
  - `app.py`: Implements a multi-tab analytical user interface using cached database transactions, Plotly charts, and styled HTML matrix frames.

---

## 3. Database Schema & Index Inspection

The database consists of 6 primary relational tables:
- **`customers` (Parent):** Base profile data (`customer_id`, `full_name`, `email`, `country`, `join_date`, `segment`, `is_active`).
- **`accounts` (Child of customers):** Financial accounts owned by customer profiles (`account_id`, `customer_id`, `account_type`, `currency`, `opened_date`, `status`).
- **`merchants` (Parent):** Registered merchant profiles accepting purchases (`merchant_id`, `merchant_name`, `category`, `country`, `registration_date`, `risk_tier`).
- **`transactions` (Child of accounts and merchants):** Centered transaction log ledger (`transaction_id`, `account_id`, `merchant_id`, `amount`, `currency`, `transaction_date`, `transaction_type`, `status`).
- **`settlements` (Child of transactions 1:1):** Tracks settlement payouts and acquiring processing fees (`settlement_id`, `transaction_id`, `settlement_date`, `settled_amount`, `processing_fee`, `status`).
- **`fraud_flags` (Child of transactions 1:1):** Tracks risk flags raised by transaction compliance rules (`flag_id`, `transaction_id`, `flagged_date`, `flag_reason`, `is_resolved`, `resolved_date`).

### Performance Tuning:
To prevent full table scans on large tables (e.g. `transactions` with 80,000 rows):
- **Foreign Key Indexes:** Speeds up inner and left joins between `transactions`, `accounts`, and `merchants`.
- **Temporal Indexes:** `idx_transactions_transaction_date` and `idx_settlements_settlement_date` accelerate chronological cohorting and running totals.
- **Categorical Index:** `idx_transactions_status` allows the database to instantly filter out completed records.

---

## 4. UI Dashboard Tab-by-Tab Inspection

The UI in `dashboard/app.py` is configured with page setup attributes, custom dark-themed styling, and standard typography elements.

### Typography & Branding (Custom CSS Injection):
Streamlit is customized via `st.markdown(..., unsafe_allow_html=True)` to use:
- **Font Family:** Google Font *Outfit* (`font-family: 'Outfit', sans-serif`), which matches contemporary design standards.
- **Page Headings:** A gradient background clip creates an aesthetic typography design for the title.
- **Metric Cards:** Custom CSS classes style metric cards with background colors (`rgba(28, 30, 41, 0.4)`) and subtle grey borders to fit a dark-mode look.

### Tab 1: Overview
- **KPI Metrics Grid:** Displays total completed transaction counts, overall volume in EUR, and average transaction sizes in a 3-column layout.
- **Trends Chart:** Plots monthly aggregates. Incorporates a dual-axis Plotly figure where monthly counts are plotted as a bar chart (purple `#8A2387`) and total volume as a line chart (orange `#F27121`).

### Tab 2: Merchant Analysis
- **Leaderboard Visualisation:** A horizontal Plotly bar chart showcasing the top 10 merchants sorted by settled revenue. Data is categorized and colored using the Plotly `Bold` palette.
- **Data Table:** Formats a data grid showing the merchant statistics, using Streamlit's column configurations to display currency formats cleanly.

### Tab 3: Risk Overview
- **Category Fraud Flag Rate:** A Plotly bar chart displaying the percentage rate of transactions flagged for fraud across merchant categories (e.g., Food & Beverage, Travel, Retail). Darker shades of purple indicate higher risk rates.
- **Risk Data Table:** Lists total transaction counts, total flag triggers, and fraud rates (%) side-by-side.

### Tab 4: Cohort Retention
- **Heatmap Grid:** Displays month-over-month cohort retention matrices up to 12 months.
- **Conditional Styling:** Formats cell background colors based on value range (0% to 100%) using a purple gradient (`cmap="Purples"`). Non-active month cells are represented with a clean hyphen (`-`).

---

## 5. Script & Pipeline Analysis

### Programmatic Data Generation (`generate_data.py`):
- Leverages `faker` to mock customer records and merchant identities.
- Applies logical rules to ensure validity:
  - Account opened dates are after customer join dates.
  - Transactions occur after account creation dates.
  - Settlements occur 1 to 5 days after transactions.
  - Fraud flags trigger within 0 to 4 hours post-transaction.
  - Settlement processing fees are dynamically determined by merchant risk tier (low, medium, high).

### High-Speed Ingestion (`load_data.py`):
- Clears table contents in correct relational cascade dependency order.
- Utilizes the PostgreSQL `COPY` syntax through python's `copy_expert` interface, ingestion is highly optimized (loading 80,000 transactions in less than a second).

### Programmatic Exporter (`export_charts.py`):
- Connects directly to the PostgreSQL database and runs query logic equivalent to `dashboard/app.py`.
- Compiles the 4 dashboard figures using the `plotly.express` and `plotly.graph_objects` APIs.
- Saves high-quality images directly into `outputs/charts/` using the `kaleido` rendering library.
- Prints clean console updates: `Exporting <chart>.png... done`.

---

## 6. Project Evaluation

* **Correctness:** The database setups, generators, loaders, exporters, and dashboard run without syntax or import exceptions.
* **Performance:** Streamlit functions use the `@st.cache_data(ttl=600)` decorator, meaning database queries only run once every 10 minutes, ensuring the dashboard remains fast and responsive.
* **Security:** Database configurations are isolated in a `.env` file, and a custom `.gitignore` excludes it from source control, preventing accidental credential leaks.
* **Database Design:** Constraints (e.g. `CHECK` statements, `NOT NULL`, `UNIQUE`) are utilized, and indexes are in place to ensure database integrity and performance.
