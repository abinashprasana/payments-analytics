"""Synthetic Transaction Data Generator for Payments Analytics SQL.

This script generates realistic synthetic datasets representing customers,
accounts, merchants, transactions, settlements, and fraud flags.
It outputs CSV files to the 'data/raw' directory, which are later loaded
into a PostgreSQL database for analysis.
"""

import csv
import datetime
import os
import random
from faker import Faker

# Seed for reproducibility
random.seed(42)
fake = Faker()
Faker.seed(42)

# Row counts as specified by project requirements
NUM_CUSTOMERS = 5000
NUM_ACCOUNTS = 6000
NUM_MERCHANTS = 800
NUM_TRANSACTIONS = 80000
NUM_SETTLEMENTS = 70000
NUM_FRAUD_FLAGS = 2500

# Constants for distributions and dates
START_DATE = datetime.date(2022, 1, 1)
END_DATE = datetime.date(2024, 12, 31)

COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Germany",
    "France", "Australia", "Singapore", "India", "Japan", "Brazil"
]

MERCHANT_CATEGORIES = [
    "Retail", "Travel", "Entertainment", "Electronics",
    "Utilities", "Food & Beverage", "Services", "Healthcare"
]

FRAUD_REASONS = [
    "Velocity Limit Exceeded",
    "High Risk Country Match",
    "Suspicious Amount Spike",
    "Mismatched Billing Details",
    "Card-Not-Present Anomaly"
]

OUTPUT_DIR = os.path.join("data", "raw")


def get_random_date(start, end):
    """Generates a random date between two date objects."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + datetime.timedelta(days=random_days)


def get_random_timestamp(start_date_val, end_date_val):
    """Generates a random timestamp between two date objects."""
    base_date = get_random_date(start_date_val, end_date_val)
    random_time = datetime.time(
        random.randint(0, 23),
        random.randint(0, 59),
        random.randint(0, 59)
    )
    return datetime.datetime.combine(base_date, random_time)


def generate_customers():
    """Generates customer records and saves them to customers.csv."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    customers = []
    
    for customer_id in range(1, NUM_CUSTOMERS + 1):
        name = fake.name()
        # Ensure email uniqueness by appending the unique customer ID
        email = f"{name.lower().replace(' ', '.').replace('.', '')}_{customer_id}@example.com"
        country = random.choice(COUNTRIES)
        join_date = get_random_date(START_DATE, END_DATE)
        segment = random.choices(
            ["retail", "business", "premium"],
            weights=[0.80, 0.15, 0.05],
            k=1
        )[0]
        is_active = random.choices([True, False], weights=[0.90, 0.10], k=1)[0]
        
        customers.append({
            "customer_id": customer_id,
            "full_name": name,
            "email": email,
            "country": country,
            "join_date": join_date.isoformat(),
            "segment": segment,
            "is_active": is_active
        })
        
    file_path = os.path.join(OUTPUT_DIR, "customers.csv")
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=customers[0].keys())
        writer.writeheader()
        writer.writerows(customers)
        
    return customers


def generate_accounts(customers):
    """Generates account records linking to customers and saves to accounts.csv."""
    accounts = []
    
    # Ensure every customer has at least one account
    for customer in customers:
        customer_id = customer["customer_id"]
        account_id = len(accounts) + 1
        opened_date = get_random_date(
            datetime.date.fromisoformat(customer["join_date"]),
            END_DATE
        )
        account_type = random.choices(
            ["current", "savings", "merchant"],
            weights=[0.60, 0.35, 0.05],
            k=1
        )[0]
        currency = random.choice(["EUR", "EUR", "GBP", "AUD", "CAD"])
        status = random.choices(
            ["active", "closed", "suspended"],
            weights=[0.92, 0.05, 0.03],
            k=1
        )[0]
        
        accounts.append({
            "account_id": account_id,
            "customer_id": customer_id,
            "account_type": account_type,
            "currency": currency,
            "opened_date": opened_date.isoformat(),
            "status": status
        })
        
    # Generate remaining accounts to reach target count
    while len(accounts) < NUM_ACCOUNTS:
        account_id = len(accounts) + 1
        customer = random.choice(customers)
        customer_id = customer["customer_id"]
        opened_date = get_random_date(
            datetime.date.fromisoformat(customer["join_date"]),
            END_DATE
        )
        account_type = random.choices(
            ["current", "savings", "merchant"],
            weights=[0.60, 0.35, 0.05],
            k=1
        )[0]
        currency = random.choice(["EUR", "EUR", "GBP", "AUD", "CAD"])
        status = random.choices(
            ["active", "closed", "suspended"],
            weights=[0.92, 0.05, 0.03],
            k=1
        )[0]
        
        accounts.append({
            "account_id": account_id,
            "customer_id": customer_id,
            "account_type": account_type,
            "currency": currency,
            "opened_date": opened_date.isoformat(),
            "status": status
        })
        
    file_path = os.path.join(OUTPUT_DIR, "accounts.csv")
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=accounts[0].keys())
        writer.writeheader()
        writer.writerows(accounts)
        
    return accounts


def generate_merchants():
    """Generates merchant records and saves them to merchants.csv."""
    merchants = []
    
    for merchant_id in range(1, NUM_MERCHANTS + 1):
        name = fake.company()
        category = random.choice(MERCHANT_CATEGORIES)
        country = random.choice(COUNTRIES)
        registration_date = get_random_date(START_DATE, END_DATE)
        risk_tier = random.choices(
            ["low", "medium", "high"],
            weights=[0.85, 0.12, 0.03],
            k=1
        )[0]
        
        merchants.append({
            "merchant_id": merchant_id,
            "merchant_name": name,
            "category": category,
            "country": country,
            "registration_date": registration_date.isoformat(),
            "risk_tier": risk_tier
        })
        
    file_path = os.path.join(OUTPUT_DIR, "merchants.csv")
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=merchants[0].keys())
        writer.writeheader()
        writer.writerows(merchants)
        
    return merchants


def generate_transactions(accounts, merchants):
    """Generates transactions linked to accounts and merchants and saves to transactions.csv."""
    transactions = []
    account_lookup = {a["account_id"]: a for a in accounts}
    merchant_lookup = {m["merchant_id"]: m for m in merchants}
    
    for transaction_id in range(1, NUM_TRANSACTIONS + 1):
        account_id = random.randint(1, len(accounts))
        account = account_lookup[account_id]
        account_opened = datetime.date.fromisoformat(account["opened_date"])
        
        # Transaction date must be after account opened date
        tx_timestamp = get_random_timestamp(account_opened, END_DATE)
        tx_date = tx_timestamp.date()
        
        transaction_type = random.choices(
            ["purchase", "refund", "transfer"],
            weights=[0.80, 0.05, 0.15],
            k=1
        )[0]
        
        # Purchases and refunds require merchants, transfers do not
        merchant_id = ""
        if transaction_type in ["purchase", "refund"]:
            merchant_id = random.randint(1, len(merchants))
            merchant = merchant_lookup[merchant_id]
            merchant_reg = datetime.date.fromisoformat(merchant["registration_date"])
            # Adjust transaction date to be after merchant registration date if necessary
            if tx_date < merchant_reg:
                tx_timestamp = get_random_timestamp(merchant_reg, END_DATE)
                
        # Generate amount skewed by type and segment
        if transaction_type == "refund":
            amount = round(random.uniform(5.00, 300.00), 2)
        else:
            amount = round(random.uniform(1.00, 5000.00), 2)
            
        currency = account["currency"]
        
        # Target ~8% failed, ~2% pending, ~90% completed
        status = random.choices(
            ["completed", "failed", "pending"],
            weights=[0.90, 0.08, 0.02],
            k=1
        )[0]
        
        transactions.append({
            "transaction_id": transaction_id,
            "account_id": account_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "currency": currency,
            "transaction_date": tx_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_type": transaction_type,
            "status": status
        })
        
    file_path = os.path.join(OUTPUT_DIR, "transactions.csv")
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
        writer.writeheader()
        writer.writerows(transactions)
        
    return transactions


def generate_settlements(transactions, merchants):
    """Generates settlements for a subset of completed transactions."""
    settlements = []
    merchant_lookup = {m["merchant_id"]: m for m in merchants}
    
    # Only completed purchase or refund transactions with merchants can be settled
    eligible_transactions = [
        tx for tx in transactions
        if tx["status"] == "completed" and tx["merchant_id"] != ""
    ]
    
    # Shuffle and select target count
    random.shuffle(eligible_transactions)
    settled_txs = eligible_transactions[:NUM_SETTLEMENTS]
    
    for idx, tx in enumerate(settled_txs):
        settlement_id = idx + 1
        tx_id = tx["transaction_id"]
        tx_date = datetime.datetime.strptime(tx["transaction_date"], "%Y-%m-%d %H:%M:%S")
        
        # Settlement happens 1 to 5 days after transaction
        settle_date = tx_date + datetime.timedelta(
            days=random.randint(1, 5),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        # Fee structure based on risk tier of merchant
        merchant = merchant_lookup[tx["merchant_id"]]
        if merchant["risk_tier"] == "high":
            fee_pct = random.uniform(0.035, 0.050)
        elif merchant["risk_tier"] == "medium":
            fee_pct = random.uniform(0.020, 0.030)
        else:
            fee_pct = random.uniform(0.010, 0.018)
            
        processing_fee = round(tx["amount"] * fee_pct, 2)
        settled_amount = round(tx["amount"] - processing_fee, 2)
        
        # Ensure settled amount is non-negative
        if settled_amount < 0:
            settled_amount = 0.0
            
        status = random.choices(
            ["settled", "delayed", "disputed"],
            weights=[0.94, 0.05, 0.01],
            k=1
        )[0]
        
        settlements.append({
            "settlement_id": settlement_id,
            "transaction_id": tx_id,
            "settlement_date": settle_date.strftime("%Y-%m-%d %H:%M:%S"),
            "settled_amount": settled_amount,
            "processing_fee": processing_fee,
            "status": status
        })
        
    file_path = os.path.join(OUTPUT_DIR, "settlements.csv")
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=settlements[0].keys())
        writer.writeheader()
        writer.writerows(settlements)
        
    return settlements


def generate_fraud_flags(transactions):
    """Generates fraud flags for a subset of transactions."""
    fraud_flags = []
    
    # Shuffle and select target count of flagged transactions
    shuffled_txs = list(transactions)
    random.shuffle(shuffled_txs)
    flagged_txs = shuffled_txs[:NUM_FRAUD_FLAGS]
    
    for idx, tx in enumerate(flagged_txs):
        flag_id = idx + 1
        tx_id = tx["transaction_id"]
        tx_date = datetime.datetime.strptime(tx["transaction_date"], "%Y-%m-%d %H:%M:%S")
        
        # Fraud detection flag is triggered within 0 to 4 hours of the transaction
        flagged_time = tx_date + datetime.timedelta(
            hours=random.randint(0, 3),
            minutes=random.randint(0, 59)
        )
        
        reason = random.choice(FRAUD_REASONS)
        is_resolved = random.choices([True, False], weights=[0.80, 0.20], k=1)[0]
        
        resolved_date = ""
        if is_resolved:
            # Resolved 1 to 7 days later
            res_time = flagged_time + datetime.timedelta(
                days=random.randint(1, 7),
                hours=random.randint(0, 23)
            )
            resolved_date = res_time.strftime("%Y-%m-%d %H:%M:%S")
            
        fraud_flags.append({
            "flag_id": flag_id,
            "transaction_id": tx_id,
            "flagged_date": flagged_time.strftime("%Y-%m-%d %H:%M:%S"),
            "flag_reason": reason,
            "is_resolved": is_resolved,
            "resolved_date": resolved_date
        })
        
    file_path = os.path.join(OUTPUT_DIR, "fraud_flags.csv")
    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fraud_flags[0].keys())
        writer.writeheader()
        writer.writerows(fraud_flags)
        
    return fraud_flags


def main():
    """Main orchestrator for generating and saving all synthetic tables."""
    customers = generate_customers()
    accounts = generate_accounts(customers)
    merchants = generate_merchants()
    transactions = generate_transactions(accounts, merchants)
    generate_settlements(transactions, merchants)
    generate_fraud_flags(transactions)


if __name__ == "__main__":
    main()
