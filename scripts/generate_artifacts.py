"""Generate the case-study payload and optional canonical mart exports.

The analytical content is deterministic. ``--check`` ignores only the two
build-identity fields that legitimately differ between a checked-in local
artifact and a Pages build. Deployments should pass ``--build-sha`` (or set
``BUILD_SHA``/``GITHUB_SHA``); ordinary local generation uses ``development``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.analytics_engine import AnalyticsEngine, SOURCE_TABLES
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from analytics_engine import AnalyticsEngine, SOURCE_TABLES


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "site" / "src" / "data" / "project-data.json"
DEFAULT_MART_DIR = PROJECT_ROOT / "outputs" / "marts"

SELECTED_SCENARIO_ID = "delayed_travel_gbp"
PRIMARY_PRECEDENCE = (
    "missing",
    "currency_mismatch",
    "amount_mismatch",
    "fee_mismatch",
    "late",
    "disputed",
)

SQL_EXCERPTS = {
    "close_summary": """-- analytics_context.as_of_date = :investigation_as_of_date
SELECT
  close_date, currency, eligible_count, matched_count,
  coverage_rate, overdue_minor_units, fee_delta_minor_units
FROM mart_daily_close
WHERE close_date = :scenario_date
  AND currency = :currency
ORDER BY close_date, currency;""",
    "segment_isolation": """SELECT
  merchant_category, currency, eligible_count,
  exception_count, exception_rate, primary_reason,
  overdue_minor_units, fee_delta_minor_units
FROM mart_category_health
WHERE close_date = :scenario_date
  AND currency = :currency
ORDER BY exception_count DESC, eligible_count DESC, merchant_category;""",
    "exception_queue": """SELECT
  payment_id, primary_reason, exception_reasons, currency,
  gross_minor_units, expected_settlement_date, actual_settlement_date
FROM mart_exception_queue
WHERE CAST(transaction_date AS DATE) = :scenario_date
  AND currency = :currency
ORDER BY priority_rank, gross_minor_units DESC, payment_id;""",
}


def _missing(value: Any) -> bool:
    return value is None or bool(pd.isna(value))


def _integer(value: Any) -> int:
    if _missing(value):
        return 0
    return int(round(float(value)))


def _date(value: Any) -> str | None:
    if _missing(value):
        return None
    if isinstance(value, str):
        return value[:10]
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value)[:10]


def _money(currency: str, minor_units: Any) -> dict[str, Any]:
    return {"currency": currency, "minorUnits": _integer(minor_units)}


def _basis_points(rate: Any) -> int:
    return _integer(float(rate) * 10_000)


def _scenario_copy(item: dict[str, Any]) -> dict[str, Any]:
    reason = item["expectedSignal"]["primaryReason"]
    count = int(item["expectedSignal"]["affectedPayments"])
    kind = {
        "matched": "control",
        "late": "late settlement",
        "fee_mismatch": "fee mismatch",
        "missing": "missing settlement",
    }[reason]
    readable_reason = reason.replace("_", " ")
    if count:
        expected = (
            f"Exactly {count} guided payments classify as {readable_reason} in "
            f"{item['focusCategory']} / {item['defaultCurrency']}."
        )
    else:
        expected = (
            "The guided close has no reconciliation exceptions and serves as "
            "the clean control."
        )
    return {
        "id": item["scenarioId"],
        "label": item["name"],
        "kind": kind,
        "date": item["closeDate"],
        "currency": item["defaultCurrency"],
        "merchantCategory": item["focusCategory"],
        "expectedSignal": expected,
        "disclosure": (
            "Deterministic synthetic scenario from data/scenarios.json; it is "
            "not a real payment incident."
        ),
    }


def _record_counts(engine: AnalyticsEngine) -> tuple[dict[str, Any], str, str]:
    transaction_count, first_date, last_date = engine.connection.execute(
        """
        SELECT COUNT(*), MIN(CAST(transaction_date AS DATE)),
               MAX(CAST(transaction_date AS DATE))
        FROM stg_transactions
        """
    ).fetchone()
    eligible_count = engine.connection.execute(
        "SELECT COUNT(*) FROM int_expected_settlements"
    ).fetchone()[0]
    settlement_count = engine.connection.execute(
        "SELECT COUNT(*) FROM stg_settlements"
    ).fetchone()[0]
    return (
        {
            "sourceTables": len(SOURCE_TABLES),
            "transactions": _integer(transaction_count),
            "eligiblePurchases": _integer(eligible_count),
            "settlements": _integer(settlement_count),
        },
        _date(first_date) or "",
        _date(last_date) or "",
    )


def _daily_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict("records"):
        currency = str(record["currency"])
        rows.append({
            "closeDate": _date(record["close_date"]),
            "analysisAsOfDate": _date(record["as_of_date"]),
            "currency": currency,
            "eligibleCount": _integer(record["eligible_count"]),
            "matchedCount": _integer(record["matched_count"]),
            "coverageBps": _basis_points(record["coverage_rate"]),
            "overdueValue": _money(currency, record["overdue_minor_units"]),
            "feeDelta": _money(currency, record["fee_delta_minor_units"]),
        })
    return rows


def _segment_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in frame.to_dict("records"):
        currency = str(record["currency"])
        rows.append({
            "merchantCategory": str(record["merchant_category"]),
            "currency": currency,
            "eligibleCount": _integer(record["eligible_count"]),
            "exceptionCount": _integer(record["exception_count"]),
            "exceptionRateBps": _basis_points(record["exception_rate"]),
            "primaryReason": str(record["primary_reason"]),
            "overdueValue": _money(currency, record["overdue_minor_units"]),
        })
    return rows


def _exception_summary(close_record: dict[str, Any]) -> list[dict[str, Any]]:
    currency = str(close_record["currency"])
    labels = {
        "missing": "Missing",
        "currency_mismatch": "Currency mismatch",
        "amount_mismatch": "Amount mismatch",
        "fee_mismatch": "Fee mismatch",
        "late": "Late",
        "disputed": "Disputed",
    }
    return [
        {
            "id": reason,
            "label": labels[reason],
            "count": _integer(close_record[f"{reason}_count"]),
            "affectedValue": _money(
                currency, close_record[f"{reason}_minor_units"]
            ),
        }
        for reason in PRIMARY_PRECEDENCE
    ]


def _trace_payload(record: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    currency = str(record["transaction_currency"])
    flags = [
        reason for reason in str(record.get("exception_reasons") or "").split(",")
        if reason
    ]
    days_overdue = _integer(record["days_overdue"])
    why = (
        f"The settlement arrived {days_overdue} calendar days after the effective "
        "merchant SLA. Currency, amount identity, and the applicable fee still "
        "match, so late remains the only flag."
    )
    return {
        "paymentId": str(_integer(record["payment_id"])),
        "scenarioId": scenario_id,
        "transactionDate": _date(record["transaction_date"]),
        "merchantCategory": str(record["merchant_category"]),
        "currency": currency,
        "status": str(record["transaction_status"]),
        "gross": _money(currency, record["gross_minor_units"]),
        "applicableTerm": {
            "validFrom": _date(record["term_valid_from"]),
            "validTo": _date(record["term_valid_to"]),
            "feeRateBps": _integer(record["fee_rate_bps"]),
            "settlementSlaDays": _integer(record["settlement_sla_days"]),
        },
        "expectedFee": _money(currency, record["expected_fee_minor_units"]),
        "recordedFee": _money(currency, record["recorded_fee_minor_units"]),
        "expectedSettlementDate": _date(record["expected_settlement_date"]),
        "recordedSettlementDate": _date(record["actual_settlement_date"]),
        "flags": flags,
        "primaryLabel": str(record["primary_reason"]),
        "whyFlagged": why,
        "queryId": "payment_trace",
        "model": "mart_payment_trace",
    }


def build_payload(*, build_sha: str = "development") -> dict[str, Any]:
    with AnalyticsEngine(build_sha=build_sha) as engine:
        manifest = engine._manifest  # one versioned repository contract
        scenarios = {
            item["scenarioId"]: item for item in manifest["scenarios"]
        }
        selected = scenarios[SELECTED_SCENARIO_ID]
        selected_date = dt.date.fromisoformat(selected["closeDate"])
        investigation_as_of = selected.get(
            "investigationAsOfDate", selected["closeDate"]
        )

        progression_dates = (
            selected_date,
            dt.date.fromisoformat(investigation_as_of),
            selected_date + dt.timedelta(days=6),
            dt.date.fromisoformat(manifest["asOfDate"]),
        )
        daily = pd.concat(
            [
                engine.query(
                    "close_summary",
                    {
                        "scenario": SELECTED_SCENARIO_ID,
                        "as_of_date": as_of,
                    },
                )
                for as_of in progression_dates
            ],
            ignore_index=True,
        )
        segments = engine.query(
            "segment_isolation", {"scenario": SELECTED_SCENARIO_ID}
        )
        close = engine.query(
            "close_summary", {"scenario": SELECTED_SCENARIO_ID}
        )
        queue = engine.query(
            "exception_queue", {"scenario": SELECTED_SCENARIO_ID}
        )
        if close.empty or queue.empty:
            raise RuntimeError("Selected scenario did not produce its expected evidence")
        trace_id = _integer(queue.iloc[0]["payment_id"])
        trace = engine.query(
            "payment_trace",
            {"scenario": SELECTED_SCENARIO_ID, "payment_id": trace_id},
        )
        if trace.empty:
            raise RuntimeError(f"No trace evidence for payment {trace_id}")

        quality = engine.query("quality_results")
        metrics = engine.query("catalog_metrics")
        record_counts, first_date, last_date = _record_counts(engine)
        close_record = close.iloc[0].to_dict()
        travel = next(
            row for row in segments.to_dict("records")
            if row["merchant_category"] == selected["focusCategory"]
        )
        investigation_incident = next(
            row for row in daily.to_dict("records")
            if _date(row["as_of_date"]) == investigation_as_of
        )
        incident_matched = _integer(investigation_incident["matched_count"])
        incident_eligible = _integer(investigation_incident["eligible_count"])
        late_count = _integer(close_record["late_count"])

        metric_definitions = []
        for row in metrics.to_dict("records"):
            query_id = {
                "settlement_coverage": "close_summary",
                "overdue_value": "close_summary",
                "fee_delta": "segment_isolation",
                "exception_count": "exception_queue",
            }[row["metric_id"]]
            metric = {
                "id": row["metric_id"],
                "label": row["name"],
                "definition": row["definition"],
                "population": row["population"],
                "grain": row["grain"],
                "currencyBoundary": row["currency_boundary"],
                "model": row["sql_model"],
                "queryId": query_id,
            }
            if row["metric_id"] == "settlement_coverage":
                metric["toleranceMinorUnits"] = 1
            metric_definitions.append(metric)

        payload: dict[str, Any] = {
            "schemaVersion": 2,
            "dataset": {
                "label": manifest["snapshotLabel"],
                "version": manifest["datasetVersion"],
                "asOfDate": manifest["asOfDate"],
                "window": {
                    "firstTransactionDate": first_date,
                    "lastTransactionDate": last_date,
                },
                "recordCounts": record_counts,
            },
            "build": {
                "commitSha": build_sha,
                "generatedAt": f"{manifest['asOfDate']}T00:00:00Z",
                "runtimeLabel": "Static payload generated from DuckDB SQL marts",
            },
            "navigation": [
                {"id": "question", "label": "Answer"},
                {"id": "contract", "label": "Contract"},
                {"id": "model", "label": "Model"},
                {"id": "baseline", "label": "Baseline"},
                {"id": "isolation", "label": "Root cause"},
                {"id": "classification", "label": "Queue"},
                {"id": "recommendation", "label": "Decision"},
                {"id": "validation", "label": "Validation"},
                {"id": "workbench", "label": "Workbench"},
            ],
            "question": {
                "stakeholder": (
                    "Why did completed Travel purchases stop reconciling to "
                    "recorded GBP settlement value?"
                ),
                "conciseAnswer": (
                    f"At the {investigation_as_of} checkpoint, only "
                    f"{incident_matched} of {incident_eligible} eligible GBP "
                    f"purchases from the {selected['closeDate']} close had matching "
                    f"settlement evidence. The {late_count}-payment synthetic Travel "
                    "batch later arrived three days beyond each applicable SLA; "
                    "coverage recovered to 100% and those payments became late exceptions."
                ),
                "operationalDecision": (
                    "Reconcile the late batch as one operational event, then route "
                    "any residual payment-level exceptions using the stable queue precedence."
                ),
            },
            "metricDefinitions": metric_definitions,
            "sourceModel": {
                "entities": [
                    {"name": "customers", "grain": "One customer", "key": "customer_id", "role": "Ownership context"},
                    {"name": "accounts", "grain": "One account", "key": "account_id", "role": "Currency boundary"},
                    {"name": "transactions", "grain": "One payment event", "key": "transaction_id", "role": "Event spine"},
                    {"name": "merchants", "grain": "One merchant", "key": "merchant_id", "role": "Operating segment"},
                    {"name": "merchant_terms", "grain": "One merchant and validity interval", "key": "merchant_id + valid_from", "role": "Expected fee and SLA"},
                    {"name": "settlements", "grain": "One settlement record", "key": "settlement_id", "role": "Recorded money evidence"},
                    {"name": "fraud_flags", "grain": "One review record", "key": "flag_id", "role": "Review context"},
                ],
                "relationships": [
                    {"from": "customers", "to": "accounts", "cardinality": "one to many", "note": "An account belongs to one customer."},
                    {"from": "accounts", "to": "transactions", "cardinality": "one to many", "note": "Every transaction retains its account currency."},
                    {"from": "transactions", "to": "merchants", "cardinality": "many to zero or one", "note": "Merchant is required for the flagship purchase population."},
                    {"from": "merchants", "to": "merchant_terms", "cardinality": "one to many over time", "note": "Validity dates select exactly one effective term."},
                    {"from": "transactions", "to": "settlements", "cardinality": "one to zero or one", "note": "A left join keeps missing evidence visible."},
                    {"from": "transactions", "to": "fraud_flags", "cardinality": "one to zero or one", "note": "Review context can coexist with settlement flags."},
                ],
            },
            "scenarios": [_scenario_copy(item) for item in manifest["scenarios"]],
            "selectedScenarioId": SELECTED_SCENARIO_ID,
            "investigationSteps": [
                {
                    "id": "baseline",
                    "label": "Baseline daily close",
                    "question": "Did settlement coverage break inside one currency close?",
                    "queryId": "close_summary",
                    "model": "mart_daily_close",
                    "sql": SQL_EXCERPTS["close_summary"],
                    "reading": (
                        f"At the {investigation_as_of} observation cut, the selected "
                        f"close was {incident_matched}/{incident_eligible} matched. "
                        "The final snapshot recovers the evidence and preserves the SLA breach."
                    ),
                },
                {
                    "id": "isolation",
                    "label": "Segment isolation",
                    "question": "Which merchant segment explains the GBP gap?",
                    "queryId": "segment_isolation",
                    "model": "mart_category_health",
                    "sql": SQL_EXCERPTS["segment_isolation"],
                    "reading": (
                        f"Travel contains {_integer(travel['exception_count'])} of "
                        f"{_integer(close_record['exception_count'])} final exceptions "
                        "for this GBP close; every one is late."
                    ),
                },
                {
                    "id": "classification",
                    "label": "Exception classification",
                    "question": "What should operations inspect first without losing secondary reasons?",
                    "queryId": "exception_queue",
                    "model": "mart_exception_queue",
                    "sql": SQL_EXCERPTS["exception_queue"],
                    "reading": (
                        "Independent Boolean flags retain every true reason. The "
                        "primary label exists only to make queue ordering stable."
                    ),
                },
            ],
            "dailyClose": _daily_rows(daily),
            "segmentFindings": _segment_rows(segments),
            "exceptionSummary": _exception_summary(close_record),
            "primaryLabelPrecedence": list(PRIMARY_PRECEDENCE),
            "trace": _trace_payload(trace.iloc[0].to_dict(), SELECTED_SCENARIO_ID),
            "recommendation": {
                "finding": (
                    f"All {_integer(travel['exception_count'])} flagged Travel / GBP "
                    "payments belong to the injected batch; amount identity, currency, "
                    "and effective fee terms still agree."
                ),
                "action": (
                    "Reconcile the batch once, preserve the payment-level late flags "
                    "for SLA reporting, and export only the filtered evidence needed by operations."
                ),
                "owner": "Settlement operations",
                "successMetricId": "settlement_coverage",
            },
            "validation": {
                "explainModel": "mart_exception_queue",
                "explainQueryId": "exception_queue",
                "explainSql": (
                    "EXPLAIN ANALYZE\n" + SQL_EXCERPTS["exception_queue"].replace(
                        ":scenario_date", "DATE '2024-10-08'"
                    ).replace(":currency", "'GBP'")
                ),
                "plan": [
                    "Filter completed merchant purchases at the expected-settlement grain.",
                    "Resolve the one merchant term effective on each purchase date.",
                    "Left join only settlement and review evidence visible at the as-of date.",
                    "Classify independent flags, then apply deterministic queue precedence.",
                ],
                "qualityResults": [
                    {
                        "checkId": row["check_id"],
                        "label": row["label"],
                        "status": row["status"],
                        "checkedRows": _integer(row["checked_rows"]),
                        "detail": row["detail"],
                    }
                    for row in quality.to_dict("records")
                ],
            },
            "models": [
                {"name": "int_expected_settlements", "grain": "Eligible purchase", "purpose": "Select the population and effective merchant term."},
                {"name": "int_settlement_reconciliation", "grain": "Eligible purchase", "purpose": "Compare expected and recorded evidence and retain every flag."},
                {"name": "mart_daily_close", "grain": "Close date and currency", "purpose": "Serve close health without mixed-currency totals."},
                {"name": "mart_exception_queue", "grain": "Payment", "purpose": "Prioritize exceptions while preserving multi-reason tags."},
                {"name": "mart_merchant_health", "grain": "Merchant, date, and currency", "purpose": "Isolate merchant-level concentration."},
                {"name": "mart_payment_trace", "grain": "Payment", "purpose": "Expose terms, money, settlement, flags, and lineage together."},
                {"name": "mart_category_health", "grain": "Category, date, and currency", "purpose": "Support the authored root-cause step."},
            ],
            "limitations": [
                "All records and scenarios are deterministic synthetic examples; they are not real incidents or business-impact estimates.",
                "The snapshot demonstrates batch analysis, not streaming ingestion, predictive fraud, chargeback management, or regulatory compliance.",
                "Money is compared only within its recorded currency. No foreign-exchange conversion or cross-currency total is produced.",
                "PostgreSQL compatibility is checked separately by scripts/check_sql_parity.py; this payload does not claim a parity result.",
            ],
            "workbench": {
                "views": [
                    {"id": "close", "label": "Close", "purpose": "Find the unhealthy currency close."},
                    {"id": "exceptions", "label": "Exceptions", "purpose": "Filter and export payment-level evidence."},
                    {"id": "trace", "label": "Trace", "purpose": "Inspect terms, money, settlement, flags, and SQL lineage."},
                    {"id": "catalog", "label": "Catalog", "purpose": "Verify metric contracts, grains, quality, and build identity."},
                ],
                "journey": [
                    "Identify the GBP close where evidence is incomplete.",
                    "Filter the exception queue to the delayed Travel batch.",
                    "Trace one payment and inspect the effective SQL rule.",
                    "Export the filtered evidence without changing the snapshot.",
                ],
                "sleepDisclosure": (
                    "The free Streamlit Community Cloud app may need to wake after "
                    "inactivity; that pause is normal for the public demo tier."
                ),
            },
            "reproduction": {
                "commands": [
                    "python data/generate_data.py",
                    "python scripts/generate_artifacts.py",
                    "python scripts/check_sql_parity.py",
                    "cd site && npm ci && npm run build",
                ],
                "compatibilityEngines": ["DuckDB", "PostgreSQL"],
            },
        }
        return payload


def _normalized_for_check(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    normalized["build"]["commitSha"] = "<build-sha>"
    normalized["build"]["generatedAt"] = "<generated-at>"
    return normalized


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def export_marts(engine: AnalyticsEngine, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for name in (
        "mart_daily_close",
        "mart_exception_queue",
        "mart_merchant_health",
        "mart_payment_trace",
    ):
        path = output_dir / f"{name}.csv"
        engine.connection.execute(f"SELECT * FROM {name}").df().to_csv(
            path, index=False
        )
        exported.append(path)
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--build-sha",
        help="Build identity for a deployment artifact (defaults to BUILD_SHA, GITHUB_SHA, then development).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Reject analytical drift without comparing build-only identity fields.",
    )
    parser.add_argument(
        "--export-marts",
        action="store_true",
        help="Also export the four canonical public marts as CSV files.",
    )
    parser.add_argument("--marts-dir", type=Path, default=DEFAULT_MART_DIR)
    args = parser.parse_args()

    build_sha = (
        args.build_sha
        or os.getenv("BUILD_SHA")
        or os.getenv("GITHUB_SHA")
        or "development"
    )
    payload = build_payload(build_sha=build_sha)

    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"Artifact check failed: missing {args.output}")
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        if _normalized_for_check(existing) != _normalized_for_check(payload):
            raise SystemExit(
                "Artifact check failed: analytical content is stale; run "
                "python scripts/generate_artifacts.py"
            )
        print(f"Artifact is current: {args.output}")
    else:
        _write_json(args.output, payload)
        print(f"Generated case-study payload: {args.output}")

    if args.export_marts:
        with AnalyticsEngine(build_sha=build_sha) as engine:
            paths = export_marts(engine, args.marts_dir)
        print("Exported marts: " + ", ".join(str(path) for path in paths))


if __name__ == "__main__":
    main()
