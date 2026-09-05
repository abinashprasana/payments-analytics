"""Canonical, read-only analytics interface for the v2 demonstration snapshot.

The public application can execute only the query IDs registered here.  Every
join, classification, and aggregation is performed by the portable SQL model
chain; Pandas is used solely as the returned table representation.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Mapping, Sequence

import duckdb
import pandas as pd

try:
    from scripts.anomaly_scoring import score_exceptions
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from anomaly_scoring import score_exceptions


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
MODEL_DIR = PROJECT_ROOT / "sql" / "models"
SCENARIO_MANIFEST = PROJECT_ROOT / "data" / "scenarios.json"

SOURCE_TABLES = (
    "customers",
    "accounts",
    "merchants",
    "merchant_terms",
    "transactions",
    "settlements",
    "fraud_flags",
)
VALID_CURRENCIES = frozenset({"EUR", "GBP", "AUD", "CAD"})

QUERY_PARAMETERS: dict[str, frozenset[str]] = {
    "scenario_options": frozenset(),
    "close_summary": frozenset(
        {"scenario", "currency", "start_date", "end_date", "as_of_date"}
    ),
    "segment_isolation": frozenset(
        {"scenario", "currency", "start_date", "end_date", "as_of_date"}
    ),
    "exception_queue": frozenset(
        {"scenario", "currency", "start_date", "end_date", "as_of_date"}
    ),
    "payment_trace": frozenset(
        {
            "scenario",
            "currency",
            "start_date",
            "end_date",
            "as_of_date",
            "payment_id",
        }
    ),
    "catalog_metrics": frozenset(),
    "quality_results": frozenset(),
    "exception_scoring": frozenset({"as_of_date"}),
    "exception_rate_screen": frozenset(),
    "benford_conformity": frozenset(),
}

QUERY_REQUIRED: dict[str, frozenset[str]] = {
    "scenario_options": frozenset(),
    "close_summary": frozenset({"scenario"}),
    "segment_isolation": frozenset({"scenario"}),
    "exception_queue": frozenset({"scenario"}),
    "payment_trace": frozenset({"scenario", "payment_id"}),
    "catalog_metrics": frozenset(),
    "quality_results": frozenset(),
    "exception_scoring": frozenset(),
    "exception_rate_screen": frozenset(),
    "benford_conformity": frozenset(),
}


class AnalyticsEngine:
    """Build and query a cached-friendly in-memory DuckDB snapshot."""

    def __init__(
        self,
        raw_data_dir: Path | str | None = None,
        *,
        build_sha: str | None = None,
        repo_root: Path | str | None = None,
    ) -> None:
        self.project_root = Path(repo_root) if repo_root is not None else PROJECT_ROOT
        self.raw_data_dir = (
            Path(raw_data_dir)
            if raw_data_dir is not None
            else self.project_root / "data" / "raw"
        )
        self.model_dir = self.project_root / "sql" / "models"
        self.manifest_path = self.project_root / "data" / "scenarios.json"
        self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self._scenarios = {
            item["scenarioId"]: item for item in self._manifest["scenarios"]
        }
        self.connection = duckdb.connect(database=":memory:")
        self._query_lock = threading.RLock()
        self._load_sources()
        self.connection.execute("CREATE TABLE analytics_context (as_of_date DATE NOT NULL)")
        self.connection.execute(
            "INSERT INTO analytics_context VALUES (?)",
            [self._date(self._manifest["asOfDate"], "asOfDate")],
        )
        self._execute_models()
        detected_sha = build_sha or os.getenv("BUILD_SHA") or os.getenv("GITHUB_SHA")
        if not detected_sha:
            try:
                detected_sha = subprocess.run(
                    ["git", "rev-parse", "--short=12", "HEAD"],
                    cwd=self.project_root,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=3,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                detected_sha = "local"
        self.build_metadata = {
            "dataset_version": self._manifest["datasetVersion"],
            "snapshot_label": self._manifest["snapshotLabel"],
            "as_of_date": self._manifest["asOfDate"],
            "build_sha": detected_sha,
            "runtime_mode": "DuckDB · in-memory repository snapshot",
        }

    @property
    def query_ids(self) -> tuple[str, ...]:
        return tuple(QUERY_PARAMETERS)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "AnalyticsEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _load_sources(self) -> None:
        for table in SOURCE_TABLES:
            path = self.raw_data_dir / f"{table}.csv"
            if not path.is_file():
                raise FileNotFoundError(f"Missing snapshot source: {path}")
            escaped = path.resolve().as_posix().replace("'", "''")
            self.connection.execute(
                f"CREATE TABLE {table} AS "
                f"SELECT * FROM read_csv_auto('{escaped}', header=true, "
                "sample_size=-1, nullstr='')"
            )

    def _execute_models(self) -> None:
        files = sorted(self.model_dir.glob("*.sql"))
        if not files:
            raise FileNotFoundError(f"No canonical SQL models found in {self.model_dir}")
        for path in files:
            self.connection.execute(path.read_text(encoding="utf-8"))

    @staticmethod
    def _date(value: Any, name: str) -> dt.date:
        if isinstance(value, dt.datetime):
            return value.date()
        if isinstance(value, dt.date):
            return value
        try:
            return dt.date.fromisoformat(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an ISO date (YYYY-MM-DD)") from exc

    def _validated_params(
        self, query_id: str, params: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        if query_id not in QUERY_PARAMETERS:
            raise ValueError(
                f"Unknown query_id {query_id!r}; allowed: {', '.join(self.query_ids)}"
            )
        supplied = dict(params or {})
        unknown = set(supplied) - QUERY_PARAMETERS[query_id]
        if unknown:
            raise ValueError(
                f"Unsupported parameters for {query_id}: {', '.join(sorted(unknown))}"
            )
        clean = {key: value for key, value in supplied.items() if value not in (None, "")}
        missing = QUERY_REQUIRED[query_id] - set(clean)
        if missing:
            raise ValueError(
                f"Missing required parameters for {query_id}: "
                + ", ".join(sorted(missing))
            )
        if "scenario" in clean:
            clean["scenario"] = str(clean["scenario"])
            if clean["scenario"] not in self._scenarios:
                raise ValueError(f"Unknown scenario: {clean['scenario']}")
        if "currency" in clean:
            clean["currency"] = str(clean["currency"]).upper()
            if clean["currency"] not in VALID_CURRENCIES:
                raise ValueError(f"Unsupported currency: {clean['currency']}")
        for name in ("start_date", "end_date", "as_of_date"):
            if name in clean:
                clean[name] = self._date(clean[name], name)
        if clean.get("start_date") and clean.get("end_date"):
            if clean["start_date"] > clean["end_date"]:
                raise ValueError("start_date cannot be after end_date")
        if "payment_id" in clean:
            text = str(clean["payment_id"]).strip()
            if not text.isdigit() or int(text) <= 0:
                raise ValueError("payment_id must be a positive integer")
            clean["payment_id"] = int(text)
        return clean

    def _as_of(self, params: Mapping[str, Any]) -> dt.date:
        return params.get("as_of_date") or self._date(
            self._manifest["asOfDate"], "asOfDate"
        )

    def _set_as_of(self, as_of: dt.date) -> None:
        self.connection.execute("UPDATE analytics_context SET as_of_date = ?", [as_of])

    def _scope(
        self,
        params: Mapping[str, Any],
        *,
        alias: str = "r",
        date_column: str = "close_date",
        currency_column: str = "currency",
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        scenario = self._scenarios.get(str(params.get("scenario", "")))
        if scenario:
            clauses.extend(
                [
                    f"CAST({alias}.{date_column} AS DATE) = ?",
                    f"{alias}.{currency_column} = ?",
                ]
            )
            values.extend(
                [self._date(scenario["closeDate"], "closeDate"), scenario["defaultCurrency"]]
            )
        if "currency" in params:
            clauses.append(f"{alias}.{currency_column} = ?")
            values.append(params["currency"])
        if "start_date" in params:
            clauses.append(f"CAST({alias}.{date_column} AS DATE) >= ?")
            values.append(params["start_date"])
        if "end_date" in params:
            clauses.append(f"CAST({alias}.{date_column} AS DATE) <= ?")
            values.append(params["end_date"])
        return (" AND ".join(clauses) if clauses else "1 = 1"), values

    def _scenario_options(self) -> pd.DataFrame:
        rows = []
        for item in self._manifest["scenarios"]:
            signal = item["expectedSignal"]
            rows.append(
                {
                    "scenario_id": item["scenarioId"],
                    "name": item["name"],
                    "description": item["description"],
                    "close_date": self._date(item["closeDate"], "closeDate"),
                    "as_of_date": self._date(
                        item.get("investigationAsOfDate", self._manifest["asOfDate"]),
                        "investigationAsOfDate",
                    ),
                    "default_currency": item["defaultCurrency"],
                    "focus_category": item["focusCategory"],
                    "is_default": bool(item.get("isDefault", False)),
                    "expected_primary_reason": signal["primaryReason"],
                    "expected_affected_payments": int(signal["affectedPayments"]),
                }
            )
        return pd.DataFrame(rows)

    def _close_summary(self, params: Mapping[str, Any]) -> pd.DataFrame:
        as_of = self._as_of(params)
        scope, scope_values = self._scope(params)
        sql = f"""
SELECT
    r.*,
    CAST(? AS DATE) AS as_of_date
FROM mart_daily_close AS r
WHERE {scope}
ORDER BY r.close_date, r.currency
"""
        return self.connection.execute(sql, [as_of] + scope_values).df()

    def _segment_isolation(self, params: Mapping[str, Any]) -> pd.DataFrame:
        as_of = self._as_of(params)
        scope, scope_values = self._scope(params)
        sql = f"""
SELECT
    r.*,
    CAST(? AS DATE) AS as_of_date
FROM mart_category_health AS r
WHERE {scope}
ORDER BY exception_count DESC, eligible_count DESC, r.merchant_category
"""
        return self.connection.execute(sql, [as_of] + scope_values).df()

    def _exception_queue(self, params: Mapping[str, Any]) -> pd.DataFrame:
        as_of = self._as_of(params)
        scope, scope_values = self._scope(
            params, date_column="transaction_date"
        )
        sql = f"""
SELECT
    r.*,
    CAST(? AS DATE) AS as_of_date
FROM mart_exception_queue AS r
WHERE {scope}
ORDER BY
    r.priority_rank,
    r.gross_minor_units DESC,
    r.payment_id
"""
        return self.connection.execute(sql, [as_of] + scope_values).df()

    def _payment_trace(self, params: Mapping[str, Any]) -> pd.DataFrame:
        as_of = self._as_of(params)
        scope, scope_values = self._scope(
            params,
            date_column="transaction_date",
            currency_column="transaction_currency",
        )
        payment_clause = ""
        payment_values: list[Any] = []
        if "payment_id" in params:
            payment_clause = " AND r.payment_id = ?"
            payment_values.append(params["payment_id"])
        sql = f"""
SELECT
    r.*,
    CAST(? AS DATE) AS as_of_date
FROM mart_payment_trace AS r
WHERE {scope}{payment_clause}
ORDER BY r.payment_id
LIMIT 1
"""
        return self.connection.execute(
            sql,
            [as_of] + scope_values + payment_values,
        ).df()

    def _catalog_metrics(self) -> pd.DataFrame:
        return self.connection.execute(
            """
SELECT * FROM (VALUES
    ('settlement_coverage', 'Settlement coverage',
     'Purchases with evidence, matching currency, and gross identity within 0.01 divided by eligible purchases.',
     'Completed merchant purchases only; refunds and transfers are excluded.',
     'close date and currency', 'Never aggregated across currencies', 'mart_daily_close'),
    ('overdue_value', 'Overdue value',
     'Gross value missing past its effective SLA or actually settled after that SLA.',
     'Completed merchant purchases only.', 'close date and currency',
     'Never aggregated across currencies', 'mart_daily_close'),
    ('fee_delta', 'Fee delta',
     'Recorded processing fee minus the effective merchant-term fee.',
     'Eligible purchases with settlement evidence.', 'payment, then date and currency',
     'Never aggregated across currencies', 'int_settlement_reconciliation'),
    ('exception_count', 'Exception count',
     'Distinct eligible payments with at least one independent exception flag.',
     'Completed merchant purchases only.', 'payment',
     'Payment currency retained', 'mart_exception_queue')
) AS metrics(metric_id, name, definition, population, grain, currency_boundary, sql_model)
ORDER BY metric_id
"""
        ).df()

    def _exception_scoring(self, params: Mapping[str, Any]) -> pd.DataFrame:
        """The one query id that wraps a fitted model instead of pure SQL."""

        as_of = self._as_of(params)
        return score_exceptions(self.connection, as_of=as_of)

    def _exception_rate_screen(self) -> pd.DataFrame:
        return self.connection.execute(
            "SELECT * FROM mart_quality_screens ORDER BY currency, close_date"
        ).df()

    def _benford_conformity(self) -> pd.DataFrame:
        return self.connection.execute(
            "SELECT * FROM mart_benford_conformity ORDER BY currency, leading_digit"
        ).df()

    def _quality_results(self) -> pd.DataFrame:
        return self.connection.execute(
            """
WITH checks AS (
    SELECT
        'eligible_purchase_unique' AS check_id,
        'Eligible purchases are unique at payment grain' AS label,
        COUNT(*) AS checked_rows,
        COUNT(*) - COUNT(DISTINCT payment_id) AS failing_rows
    FROM int_expected_settlements
    UNION ALL
    SELECT 'effective_term_join', 'Every eligible purchase selects exactly one term',
        (SELECT COUNT(*) FROM stg_transactions
         WHERE transaction_type = 'purchase' AND status = 'completed'),
        (SELECT COUNT(*) FROM stg_transactions
         WHERE transaction_type = 'purchase' AND status = 'completed')
          - (SELECT COUNT(*) FROM int_expected_settlements)
    UNION ALL
    SELECT 'reconciliation_unique', 'Reconciliation remains unique at payment grain',
        COUNT(*), COUNT(*) - COUNT(DISTINCT payment_id)
    FROM int_settlement_reconciliation
    UNION ALL
    SELECT 'daily_close_unique', 'Daily close is unique by date and currency',
        COUNT(*), COUNT(*) - COUNT(DISTINCT CAST(close_date AS VARCHAR) || '|' || currency)
    FROM mart_daily_close
    UNION ALL
    SELECT 'accepted_currencies', 'Source currencies use the accepted ISO set',
        COUNT(*), SUM(CASE WHEN currency IN ('EUR', 'GBP', 'AUD', 'CAD') THEN 0 ELSE 1 END)
    FROM stg_transactions
    UNION ALL
    SELECT 'merchant_nullability', 'Only transfers are merchantless',
        COUNT(*), SUM(CASE
            WHEN (transaction_type = 'transfer' AND merchant_id IS NULL)
              OR (transaction_type IN ('purchase', 'refund') AND merchant_id IS NOT NULL)
            THEN 0 ELSE 1 END)
    FROM stg_transactions
    UNION ALL
    SELECT 'resolved_date_consistency', 'Review resolution dates match resolution state',
        COUNT(*), SUM(CASE
            WHEN (is_resolved AND resolved_date IS NOT NULL AND resolved_date >= flagged_date)
              OR (NOT is_resolved AND resolved_date IS NULL)
            THEN 0 ELSE 1 END)
    FROM stg_fraud_flags
    UNION ALL
    SELECT 'matched_monetary_identity',
        'Matched payments satisfy currency and gross identity',
        COUNT(*), SUM(CASE
            WHEN settlement_id IS NOT NULL
             AND settlement_currency = transaction_currency
             AND ABS(gross_amount - (recorded_settled_amount + recorded_fee)) <= 0.01
            THEN 0 ELSE 1 END)
    FROM int_settlement_reconciliation
    WHERE is_match
    UNION ALL
    SELECT 'daily_currency_grain',
        'Daily-close rows remain unique inside one currency partition',
        COUNT(*), COUNT(*) - COUNT(DISTINCT CAST(close_date AS VARCHAR) || '|' || currency)
    FROM mart_daily_close
    UNION ALL
    SELECT 'anomaly_features_complete',
        'Every reconciled payment has scoring features',
        COUNT(*), COUNT(*) - (SELECT COUNT(*) FROM int_anomaly_features)
    FROM int_settlement_reconciliation
    UNION ALL
    SELECT 'quality_screens_populated',
        'Every daily close has a control-limit screen',
        COUNT(*), COUNT(*) - (SELECT COUNT(*) FROM mart_quality_screens)
    FROM mart_daily_close
    UNION ALL
    SELECT 'benford_digit_coverage',
        'Every currency screens all nine leading digits',
        COUNT(*),
        COUNT(*) - (SELECT COUNT(DISTINCT currency) * 9 FROM mart_benford_conformity)
    FROM mart_benford_conformity
)
SELECT
    check_id,
    label,
    CASE WHEN failing_rows = 0 THEN 'pass' ELSE 'fail' END AS status,
    checked_rows,
    CAST(failing_rows AS BIGINT) AS failing_rows,
    CASE WHEN failing_rows = 0
        THEN 'No failing rows.'
        ELSE CAST(failing_rows AS VARCHAR) || ' failing rows.' END AS detail
FROM checks
ORDER BY check_id
"""
        ).df()

    def query(
        self, query_id: str, params: Mapping[str, Any] | None = None
    ) -> pd.DataFrame:
        """Execute one validated registry query and return a fresh DataFrame."""

        clean = self._validated_params(query_id, params)
        dispatch = {
            "scenario_options": lambda _: self._scenario_options(),
            "close_summary": self._close_summary,
            "segment_isolation": self._segment_isolation,
            "exception_queue": self._exception_queue,
            "payment_trace": self._payment_trace,
            "catalog_metrics": lambda _: self._catalog_metrics(),
            "quality_results": lambda _: self._quality_results(),
            "exception_scoring": self._exception_scoring,
            "exception_rate_screen": lambda _: self._exception_rate_screen(),
            "benford_conformity": lambda _: self._benford_conformity(),
        }
        with self._query_lock:
            if query_id in {
                "close_summary",
                "segment_isolation",
                "exception_queue",
                "payment_trace",
                "exception_scoring",
            }:
                self._set_as_of(self._as_of(clean))
            elif query_id == "quality_results":
                self._set_as_of(self._date(self._manifest["asOfDate"], "asOfDate"))
            return dispatch[query_id](clean).copy()


__all__ = [
    "AnalyticsEngine", "QUERY_PARAMETERS", "QUERY_REQUIRED", "SOURCE_TABLES"
]
