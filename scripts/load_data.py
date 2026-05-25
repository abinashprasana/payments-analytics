"""Load CSV datasets into PostgreSQL database tables.

This script reads raw synthetic data from CSV files and loads them into
PostgreSQL in dependency order (Customers -> Accounts -> Merchants ->
Transactions -> Settlements -> Fraud Flags).
"""

import os
import sys
from db_connection import get_connection

RAW_DATA_DIR = os.path.join("data", "raw")

# Tables and their respective CSV files, ordered by dependency
TABLE_LOAD_ORDER = [
    ("customers", "customers.csv"),
    ("accounts", "accounts.csv"),
    ("merchants", "merchants.csv"),
    ("transactions", "transactions.csv"),
    ("settlements", "settlements.csv"),
    ("fraud_flags", "fraud_flags.csv")
]


def load_all_data():
    """Reads raw CSVs and performs bulk loading into Postgres."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Clear existing data to ensure idempotent run
            cur.execute(
                "TRUNCATE TABLE fraud_flags, settlements, transactions, "
                "merchants, accounts, customers RESTART IDENTITY CASCADE;"
            )
            conn.commit()

            for table, filename in TABLE_LOAD_ORDER:
                print(f"Loading {table}...", end="", flush=True)
                file_path = os.path.join(RAW_DATA_DIR, filename)
                
                with open(file_path, "r", encoding="utf-8") as f:
                    # PostgreSQL COPY command provides maximum ingestion speed
                    cur.copy_expert(
                        f"COPY {table} FROM STDIN WITH CSV HEADER NULL ''",
                        f
                    )
                conn.commit()

                # Verify loaded row count
                cur.execute(f"SELECT COUNT(*) FROM {table};")
                row_count = cur.fetchone()[0]
                print(f" done ({row_count} rows)")
                
    except Exception as e:
        conn.rollback()
        print(f"\nError occurred loading database: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    load_all_data()
