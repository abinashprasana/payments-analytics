"""Atomically rebuild and load the PostgreSQL demonstration snapshot.

All seven source tables, their constraints, and their indexes are committed as
one transaction.  A failed COPY or validation therefore leaves the previously
committed snapshot intact.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

try:
    from scripts.db_connection import get_connection
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from db_connection import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "customers": (
        "customer_id", "full_name", "email", "country", "join_date",
        "segment", "is_active",
    ),
    "accounts": (
        "account_id", "customer_id", "account_type", "currency",
        "opened_date", "status",
    ),
    "merchants": (
        "merchant_id", "merchant_name", "category", "country",
        "registration_date", "risk_tier",
    ),
    "merchant_terms": (
        "merchant_id", "valid_from", "fee_rate_bps", "settlement_sla_days",
        "valid_to",
    ),
    "transactions": (
        "transaction_id", "account_id", "merchant_id", "amount", "currency",
        "transaction_date", "transaction_type", "status",
    ),
    "settlements": (
        "settlement_id", "transaction_id", "settlement_date", "currency",
        "settled_amount", "processing_fee", "status",
    ),
    "fraud_flags": (
        "flag_id", "transaction_id", "flagged_date", "flag_reason",
        "is_resolved", "resolved_date",
    ),
}


def _validate_headers(raw_data_dir: Path) -> None:
    for table, expected in TABLE_COLUMNS.items():
        path = raw_data_dir / f"{table}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing snapshot source: {path}")
        with path.open(newline="", encoding="utf-8") as handle:
            actual = tuple(next(csv.reader(handle), ()))
        if actual != expected:
            raise ValueError(
                f"Unexpected columns for {table}: {actual!r}; expected {expected!r}"
            )


def _post_load_checks(cursor: Any) -> None:
    checks = {
        "accepted transaction currencies": """
            SELECT COUNT(*) FROM transactions
            WHERE currency NOT IN ('EUR', 'GBP', 'AUD', 'CAD')
        """,
        "accepted settlement currencies": """
            SELECT COUNT(*) FROM settlements
            WHERE currency NOT IN ('EUR', 'GBP', 'AUD', 'CAD')
        """,
        "accepted transaction statuses": """
            SELECT COUNT(*) FROM transactions
            WHERE status NOT IN ('completed', 'pending', 'failed')
        """,
        "accepted settlement statuses": """
            SELECT COUNT(*) FROM settlements
            WHERE status NOT IN ('settled', 'delayed', 'disputed')
        """,
        "merchant nullability": """
            SELECT COUNT(*) FROM transactions
            WHERE NOT (
                (transaction_type = 'transfer' AND merchant_id IS NULL)
                OR (transaction_type IN ('purchase', 'refund') AND merchant_id IS NOT NULL)
            )
        """,
        "resolved-date consistency": """
            SELECT COUNT(*) FROM fraud_flags
            WHERE NOT (
                (is_resolved AND resolved_date IS NOT NULL
                    AND resolved_date >= flagged_date)
                OR (NOT is_resolved AND resolved_date IS NULL)
            )
        """,
    }
    failures: list[str] = []
    for label, statement in checks.items():
        cursor.execute(statement)
        failing_rows = int(cursor.fetchone()[0])
        if failing_rows:
            failures.append(f"{label}: {failing_rows} failing rows")
    if failures:
        raise ValueError("Snapshot validation failed: " + "; ".join(failures))


def load_snapshot(
    raw_data_dir: Path | str = DEFAULT_RAW_DIR,
    *,
    connection: Any | None = None,
) -> dict[str, int]:
    """Rebuild and load all source tables in one PostgreSQL transaction."""

    raw_dir = Path(raw_data_dir)
    _validate_headers(raw_dir)
    owns_connection = connection is None
    conn = connection or get_connection()
    counts: dict[str, int] = {}
    try:
        conn.autocommit = False
        with conn.cursor() as cursor:
            cursor.execute(
                (PROJECT_ROOT / "schema" / "create_tables.sql").read_text(
                    encoding="utf-8"
                )
            )
            for table, columns in TABLE_COLUMNS.items():
                path = raw_dir / f"{table}.csv"
                column_sql = ", ".join(columns)
                copy_sql = (
                    f"COPY {table} ({column_sql}) FROM STDIN "
                    "WITH (FORMAT CSV, HEADER TRUE, NULL '')"
                )
                with path.open("r", newline="", encoding="utf-8") as handle:
                    cursor.copy_expert(copy_sql, handle)
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = int(cursor.fetchone()[0])
            _post_load_checks(cursor)
            cursor.execute(
                (PROJECT_ROOT / "schema" / "indexes.sql").read_text(
                    encoding="utf-8"
                )
            )
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atomically rebuild and load the PostgreSQL demo snapshot."
    )
    parser.add_argument(
        "--raw-data-dir", type=Path, default=DEFAULT_RAW_DIR,
        help="Directory containing the seven generated CSV files.",
    )
    args = parser.parse_args()
    counts = load_snapshot(args.raw_data_dir)
    detail = ", ".join(f"{name}={count:,}" for name, count in counts.items())
    print(f"Committed synthetic snapshot: {detail}")


if __name__ == "__main__":
    main()
