"""Export verified, deterministic project facts for the case-study site.

The public payload is derived from the repository CSVs through the same pure
analytics functions used by the Streamlit dashboard. Run with ``--check`` in
CI to fail when the tracked payload no longer matches its sources.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.analytics import (  # noqa: E402
    dataset_scope,
    normalise_tables,
    risk_metrics,
    settlement_statuses,
)


RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT = PROJECT_ROOT / "site" / "src" / "data" / "project-data.json"
TABLE_FILES = (
    ("customers", "customers.csv", "customer_id"),
    ("accounts", "accounts.csv", "account_id"),
    ("merchants", "merchants.csv", "merchant_id"),
    ("transactions", "transactions.csv", "transaction_id"),
    ("settlements", "settlements.csv", "settlement_id"),
    ("fraud_flags", "fraud_flags.csv", "flag_id"),
)


def _read_tables(raw_data_dir: Path) -> tuple[pd.DataFrame, ...]:
    frames: dict[str, pd.DataFrame] = {}
    for name, filename, primary_key in TABLE_FILES:
        path = raw_data_dir / filename
        if not path.is_file():
            raise ValueError(f"Missing source table: {path}")
        frame = pd.read_csv(path)
        if primary_key not in frame.columns:
            raise ValueError(f"{filename} is missing primary key {primary_key}")
        if frame[primary_key].isna().any() or frame[primary_key].duplicated().any():
            raise ValueError(f"{filename} contains an invalid {primary_key}")
        frames[name] = frame

    normalized = normalise_tables(
        frames["customers"],
        frames["accounts"],
        frames["merchants"],
        frames["transactions"],
        frames["settlements"],
        frames["fraud_flags"],
    )
    _validate_relationships(*normalized)
    return normalized


def _validate_foreign_key(
    child: pd.Series,
    parent: pd.Series,
    relationship: str,
    *,
    nullable: bool = False,
) -> None:
    values = child.dropna() if nullable else child
    if not nullable and values.isna().any():
        raise ValueError(f"{relationship} contains a null foreign key")
    missing = values[~values.isin(parent)]
    if not missing.empty:
        sample = ", ".join(str(value) for value in missing.head(3).tolist())
        raise ValueError(f"{relationship} contains unknown keys: {sample}")


def _validate_relationships(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    merchants: pd.DataFrame,
    transactions: pd.DataFrame,
    settlements: pd.DataFrame,
    fraud_flags: pd.DataFrame,
) -> None:
    _validate_foreign_key(
        accounts["customer_id"], customers["customer_id"], "accounts.customer_id"
    )
    _validate_foreign_key(
        transactions["account_id"], accounts["account_id"], "transactions.account_id"
    )
    _validate_foreign_key(
        transactions["merchant_id"],
        merchants["merchant_id"],
        "transactions.merchant_id",
        nullable=True,
    )
    _validate_foreign_key(
        settlements["transaction_id"],
        transactions["transaction_id"],
        "settlements.transaction_id",
    )
    _validate_foreign_key(
        fraud_flags["transaction_id"],
        transactions["transaction_id"],
        "fraud_flags.transaction_id",
    )
    if settlements["transaction_id"].duplicated().any():
        raise ValueError("settlements.transaction_id must be unique")
    if fraud_flags["transaction_id"].duplicated().any():
        raise ValueError("fraud_flags.transaction_id must be unique")


def build_project_data(raw_data_dir: Path = RAW_DATA_DIR) -> dict[str, Any]:
    """Build the versioned public payload from normalized repository data."""

    (
        customers,
        accounts,
        merchants,
        transactions,
        settlements,
        fraud_flags,
    ) = _read_tables(raw_data_dir)
    scope = dataset_scope(
        customers,
        accounts,
        merchants,
        transactions,
        settlements,
        fraud_flags,
    )
    settlement_rows = settlement_statuses(settlements)
    reviews = risk_metrics(transactions, fraud_flags)
    merchant_links = int(transactions["merchant_id"].notna().sum())

    return {
        "schemaVersion": 1,
        "datasetWindow": {
            "firstTransactionDate": scope["first_transaction_date"].isoformat(),
            "lastTransactionDate": scope["last_transaction_date"].isoformat(),
        },
        "recordCounts": {
            "customers": int(scope["customer_count"]),
            "accounts": int(scope["account_count"]),
            "merchants": int(scope["merchant_count"]),
            "transactions": int(scope["transaction_count"]),
            "settlements": int(scope["settlement_count"]),
            "fraudFlags": int(scope["fraud_flag_count"]),
            "merchantlessTransactions": int(
                scope["merchantless_transaction_count"]
            ),
        },
        "relationships": {
            "customerToAccounts": {
                "cardinality": "one-to-many",
                "description": "One customer can hold multiple accounts.",
                "linkedRecords": int(len(accounts)),
            },
            "accountToTransactions": {
                "cardinality": "one-to-many",
                "description": "Every transaction belongs to one account.",
                "linkedRecords": int(len(transactions)),
            },
            "transactionToMerchant": {
                "cardinality": "many-to-zero-or-one",
                "description": "Purchases and refunds can link to a merchant; transfers can remain merchantless.",
                "linkedRecords": merchant_links,
            },
            "transactionToSettlement": {
                "cardinality": "one-to-zero-or-one",
                "description": "A transaction can produce at most one settlement record.",
                "linkedRecords": int(len(settlements)),
            },
            "transactionToFraudFlag": {
                "cardinality": "one-to-zero-or-one",
                "description": "A transaction can carry at most one review flag.",
                "linkedRecords": int(len(fraud_flags)),
            },
        },
        "settlementOutcomes": [
            {
                "status": str(row.status),
                "count": int(row.count),
                "share": round(float(row.share), 2),
            }
            for row in settlement_rows.itertuples(index=False)
        ],
        "reviewOutcomes": {
            "total": int(reviews["flag_count"]),
            "resolved": int(reviews["resolved_count"]),
            "unresolved": int(reviews["unresolved_count"]),
            "resolutionRate": round(float(reviews["resolution_rate"]), 2),
            "flagRate": round(float(reviews["flag_rate"]), 2),
        },
        "technology": [
            "PostgreSQL",
            "Python",
            "Pandas",
            "Streamlit",
            "Plotly",
            "OGL",
            "Next.js",
            "TypeScript",
        ],
        "limitations": [
            "The repository dataset is synthetic and demonstrates analytical workflows rather than real customer behaviour.",
            "Currency values are aggregated nominally; no foreign-exchange conversion is applied.",
            "Fraud flags are generated, randomly sampled review signals and must not be interpreted as confirmed fraud or predictive risk.",
        ],
    }


def render_project_data(data: dict[str, Any]) -> str:
    """Serialize with a stable format suitable for byte-for-byte drift checks."""

    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the tracked payload has drifted.",
    )
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Directory containing the six source CSV files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination for the versioned JSON payload.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    rendered = render_project_data(build_project_data(args.raw_data_dir))

    if args.check:
        if not args.output.is_file():
            print(f"Project data is missing: {args.output}", file=sys.stderr)
            return 1
        if args.output.read_text(encoding="utf-8") != rendered:
            print(
                "Project data has drifted. Run "
                "`python scripts/export_site_data.py` and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"Project data is current: {args.output}")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote verified project data: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
