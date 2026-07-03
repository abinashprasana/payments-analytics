import os
import sys

from db_connection import get_connection

RAW_DATA_DIR = os.path.join("data", "raw")

TABLE_LOAD_ORDER = [
    ("customers", "customers.csv"),
    ("accounts", "accounts.csv"),
    ("merchants", "merchants.csv"),
    ("transactions", "transactions.csv"),
    ("settlements", "settlements.csv"),
    ("fraud_flags", "fraud_flags.csv"),
]


def load_all_data():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE fraud_flags, settlements, transactions, "
                "merchants, accounts, customers RESTART IDENTITY CASCADE;"
            )
            conn.commit()

            for table, filename in TABLE_LOAD_ORDER:
                print(f"Loading {table}...", end="", flush=True)
                file_path = os.path.join(RAW_DATA_DIR, filename)

                with open(file_path, "r", encoding="utf-8") as f:
                    cur.copy_expert(
                        f"COPY {table} FROM STDIN WITH CSV HEADER NULL ''",
                        f,
                    )
                conn.commit()

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
