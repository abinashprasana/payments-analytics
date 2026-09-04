"""Load PostgreSQL and reject drift from the canonical DuckDB snapshot.

The command reads the standard ``DB_*`` environment variables (including a
local ``.env`` file through ``db_connection``), atomically reloads all source
CSV files, executes the same ordered SQL model files, and compares payment
classifications plus currency-partitioned aggregates.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from scripts.analytics_engine import AnalyticsEngine
    from scripts.db_connection import get_connection
    from scripts.load_data import load_snapshot
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from analytics_engine import AnalyticsEngine
    from db_connection import get_connection
    from load_data import load_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "sql" / "models"
MANIFEST_PATH = PROJECT_ROOT / "data" / "scenarios.json"

MODEL_NAMES = (
    "int_expected_settlements",
    "int_settlement_reconciliation",
    "mart_daily_close",
    "mart_exception_queue",
    "mart_merchant_health",
    "mart_payment_trace",
    "mart_category_health",
)

CLASSIFICATION_SQL = """
SELECT
    payment_id, primary_reason, exception_reasons,
    is_missing, is_currency_mismatch, is_amount_mismatch,
    is_fee_mismatch, is_late, is_disputed, is_sla_breach, is_match
FROM int_settlement_reconciliation
WHERE primary_reason <> 'matched'
ORDER BY payment_id
"""

DAILY_SQL = """
SELECT
    close_date, currency, eligible_count, matched_count, exception_count,
    coverage_rate, gross_minor_units, settled_minor_units,
    overdue_minor_units, fee_delta_minor_units, missing_count,
    missing_minor_units, currency_mismatch_count,
    currency_mismatch_minor_units, amount_mismatch_count,
    amount_mismatch_minor_units, fee_mismatch_count,
    fee_mismatch_minor_units, late_count, late_minor_units,
    disputed_count, disputed_minor_units, sla_breach_count
FROM mart_daily_close
ORDER BY close_date, currency
"""

CATEGORY_SQL = """
SELECT
    merchant_category, close_date, currency, eligible_count, matched_count,
    exception_count, missing_count, currency_mismatch_count,
    amount_mismatch_count, fee_mismatch_count, late_count, disputed_count,
    overdue_minor_units, fee_delta_minor_units, exception_rate, primary_reason
FROM mart_category_health
ORDER BY close_date, currency, merchant_category
"""


def _normal(value: Any) -> Any:
    if isinstance(value, dt.datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.000001"))
    if isinstance(value, float):
        return Decimal(str(value)).quantize(Decimal("0.000001"))
    return value


def _normal_rows(rows: Iterable[Sequence[Any]]) -> list[tuple[Any, ...]]:
    return [tuple(_normal(value) for value in row) for row in rows]


def _duck_rows(engine: AnalyticsEngine, statement: str) -> list[tuple[Any, ...]]:
    return _normal_rows(engine.connection.execute(statement).fetchall())


def _postgres_rows(cursor: Any, statement: str) -> list[tuple[Any, ...]]:
    cursor.execute(statement)
    return _normal_rows(cursor.fetchall())


def _assert_equal(label: str, duck_rows: list[Any], postgres_rows: list[Any]) -> None:
    if duck_rows == postgres_rows:
        return
    duck_set, postgres_set = set(duck_rows), set(postgres_rows)
    duck_only = list(duck_set - postgres_set)[:3]
    postgres_only = list(postgres_set - duck_set)[:3]
    raise AssertionError(
        f"{label} drift: DuckDB={len(duck_rows):,}, "
        f"PostgreSQL={len(postgres_rows):,}; "
        f"DuckDB-only sample={duck_only!r}; PostgreSQL-only sample={postgres_only!r}"
    )


def _set_context(engine: AnalyticsEngine, cursor: Any, as_of: dt.date) -> None:
    engine.connection.execute("UPDATE analytics_context SET as_of_date = ?", [as_of])
    cursor.execute("UPDATE analytics_context SET as_of_date = %s", [as_of])


def run_parity_check() -> dict[str, int]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    default_as_of = dt.date.fromisoformat(manifest["asOfDate"])
    delayed_close = dt.date.fromisoformat(
        next(
            item["closeDate"]
            for item in manifest["scenarios"]
            if item["scenarioId"] == "delayed_travel_gbp"
        )
    )
    comparison_dates = (
        delayed_close,
        delayed_close + dt.timedelta(days=3),
        delayed_close + dt.timedelta(days=6),
        default_as_of,
    )

    conn = get_connection()
    try:
        load_snapshot(connection=conn)
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS analytics_context CASCADE")
            cursor.execute("CREATE TABLE analytics_context (as_of_date DATE NOT NULL)")
            cursor.execute("INSERT INTO analytics_context VALUES (%s)", [default_as_of])
            for path in sorted(MODEL_DIR.glob("*.sql")):
                cursor.execute(path.read_text(encoding="utf-8"))
        conn.commit()

        compared = {
            "as_of_dates": 0,
            "model_counts": 0,
            "classification_rows": 0,
            "daily_rows": 0,
            "category_rows": 0,
            "public_query_rows": 0,
        }
        with AnalyticsEngine(build_sha="parity-check") as engine, conn.cursor() as cursor:
            for as_of in comparison_dates:
                _set_context(engine, cursor, as_of)
                for model in MODEL_NAMES:
                    duck_count = _duck_rows(engine, f"SELECT COUNT(*) FROM {model}")
                    postgres_count = _postgres_rows(cursor, f"SELECT COUNT(*) FROM {model}")
                    _assert_equal(f"{model} row count as of {as_of}", duck_count, postgres_count)
                    compared["model_counts"] += 1

                duck_classifications = _duck_rows(engine, CLASSIFICATION_SQL)
                postgres_classifications = _postgres_rows(cursor, CLASSIFICATION_SQL)
                _assert_equal(
                    f"exception classifications as of {as_of}",
                    duck_classifications,
                    postgres_classifications,
                )
                compared["classification_rows"] += len(duck_classifications)

                duck_daily = _duck_rows(engine, DAILY_SQL)
                postgres_daily = _postgres_rows(cursor, DAILY_SQL)
                _assert_equal(
                    f"currency daily aggregates as of {as_of}",
                    duck_daily,
                    postgres_daily,
                )
                compared["daily_rows"] += len(duck_daily)

                duck_categories = _duck_rows(engine, CATEGORY_SQL)
                postgres_categories = _postgres_rows(cursor, CATEGORY_SQL)
                _assert_equal(
                    f"category aggregates as of {as_of}",
                    duck_categories,
                    postgres_categories,
                )
                compared["category_rows"] += len(duck_categories)
                compared["as_of_dates"] += 1

            _set_context(engine, cursor, default_as_of)
            for scenario in manifest["scenarios"]:
                close_date = dt.date.fromisoformat(scenario["closeDate"])
                currency = scenario["defaultCurrency"]
                filters = "WHERE close_date = %s AND currency = %s"
                duck_filters = "WHERE close_date = ? AND currency = ?"
                for model, order_by in (
                    ("mart_daily_close", "close_date, currency"),
                    ("mart_category_health", "exception_count DESC, eligible_count DESC, merchant_category"),
                ):
                    duck_rows = _normal_rows(
                        engine.connection.execute(
                            f"SELECT * FROM {model} {duck_filters} ORDER BY {order_by}",
                            [close_date, currency],
                        ).fetchall()
                    )
                    cursor.execute(
                        f"SELECT * FROM {model} {filters} ORDER BY {order_by}",
                        [close_date, currency],
                    )
                    postgres_rows = _normal_rows(cursor.fetchall())
                    _assert_equal(
                        f"public {model} query for {scenario['scenarioId']}",
                        duck_rows,
                        postgres_rows,
                    )
                    compared["public_query_rows"] += len(duck_rows)

                queue_sql_duck = """
                    SELECT * FROM mart_exception_queue
                    WHERE CAST(transaction_date AS DATE) = ? AND currency = ?
                    ORDER BY priority_rank, gross_minor_units DESC, payment_id
                """
                queue_sql_pg = queue_sql_duck.replace("?", "%s")
                duck_queue = _normal_rows(
                    engine.connection.execute(
                        queue_sql_duck, [close_date, currency]
                    ).fetchall()
                )
                cursor.execute(queue_sql_pg, [close_date, currency])
                postgres_queue = _normal_rows(cursor.fetchall())
                _assert_equal(
                    f"public exception_queue for {scenario['scenarioId']}",
                    duck_queue,
                    postgres_queue,
                )
                compared["public_query_rows"] += len(duck_queue)

                if duck_queue:
                    payment_id = duck_queue[0][0]
                    duck_trace = _normal_rows(
                        engine.connection.execute(
                            "SELECT * FROM mart_payment_trace WHERE payment_id = ?",
                            [payment_id],
                        ).fetchall()
                    )
                    cursor.execute(
                        "SELECT * FROM mart_payment_trace WHERE payment_id = %s",
                        [payment_id],
                    )
                    postgres_trace = _normal_rows(cursor.fetchall())
                    _assert_equal(
                        f"public payment_trace for {payment_id}",
                        duck_trace,
                        postgres_trace,
                    )
                    compared["public_query_rows"] += len(duck_trace)
        conn.rollback()
        return compared
    finally:
        conn.close()


def main() -> None:
    compared = run_parity_check()
    print(
        "SQL parity passed: "
        f"{compared['as_of_dates']} as-of dates, "
        f"{compared['model_counts']} model counts, "
        f"{compared['classification_rows']:,} exception rows, "
        f"{compared['daily_rows']:,} daily aggregates, "
        f"{compared['category_rows']:,} category aggregates, and "
        f"{compared['public_query_rows']:,} public query rows."
    )


if __name__ == "__main__":
    main()
