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

SELECTED_SCENARIO_ID = "stale_electronics_eur_fee"
PRIMARY_PRECEDENCE = (
    "missing",
    "currency_mismatch",
    "amount_mismatch",
    "fee_mismatch",
    "late",
    "disputed",
)

# Narrative fragments that differ by which exception a scenario injects. The
# earlier version of this payload hardcoded the "late settlement" story
# regardless of which scenario was selected, so switching scenarios produced
# copy that named the wrong currency, category and outcome. Keyed by
# expectedSignal.primaryReason from data/scenarios.json.
REASON_NARRATIVE = {
    "late": {
        "count_field": "late_count",
        "reason_noun": "late-settlement",
        "reason_label": "late payments",
        "outcome": (
            "{count} of them settled after their deadline and are flagged "
            "as late exceptions."
        ),
        "finding_lede": (
            "went through the settlement partner that stopped processing, and "
            "the rest are everyday holds. Amounts, currency and fees still "
            "agree; only the timing broke"
        ),
        "action": (
            "Chase the partner for the stalled batch, keep the late flags for "
            "SLA reporting, and export the filtered evidence for operations."
        ),
    },
    "fee_mismatch": {
        "count_field": "fee_mismatch_count",
        "reason_noun": "fee-mismatch",
        "reason_label": "fee mismatches",
        "outcome": (
            "{count} of them still carry fee-mismatch exceptions, most because "
            "the recorded fee kept the old schedule after the merchant's new "
            "contract began."
        ),
        "finding_lede": (
            "belong to merchants repriced on 1 Oct whose new rate never reached "
            "the processor's fee table, and the rest are everyday cross-border "
            "fee pass-throughs. Amounts and currency still agree"
        ),
        "action": (
            "Update the processor's fee table, recompute the fee on every "
            "repriced merchant's payments since the repricing, and export the "
            "filtered evidence for operations."
        ),
    },
    "missing": {
        "count_field": "missing_count",
        "reason_noun": "missing-settlement",
        "reason_label": "missing settlements",
        "outcome": (
            "{count} of them never settled within their deadline and are "
            "flagged as missing exceptions."
        ),
        "finding_lede": (
            "were in one acquirer's settlement file, and that file never "
            "arrived; the rest are everyday compliance holds"
        ),
        "action": (
            "Ask the acquirer to resend the file, confirm whether the money is "
            "delayed or lost, and export the filtered evidence for operations."
        ),
    },
}

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
            f"{count} payments on this {item['defaultCurrency']} close classify "
            f"as {readable_reason}, most of them from the incident, spread "
            f"across categories and led by {item['focusCategory']}."
        )
    else:
        expected = (
            "No incident. The close still carries the everyday mix of "
            "exceptions any day has."
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
            "Scripted incidents from data/scenarios.json, applied to "
            "generated traffic. None of them is a real incident."
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


ASK_RULE_SENTENCES = {
    "missing": "No settlement exists {days} days after the expected settlement date, so missing fired.",
    "currency_mismatch": "The settlement was recorded in a different currency from the purchase, so currency_mismatch fired.",
    "amount_mismatch": "Gross does not equal the settled amount plus the recorded fee, so amount_mismatch fired.",
    "fee_mismatch": (
        "The settlement arrived on {settled}, but the recorded fee was {recorded} against "
        "{expected} under the {bps} bps term, a {delta} difference, so fee_mismatch fired."
    ),
    "late": "The settlement arrived on {settled}, {days} days after the SLA date of {expected_date}, so late fired.",
    "disputed": "The settlement carries a disputed status, so disputed fired.",
}


def _display_money(currency: str, minor_units: Any) -> str:
    return f"{currency} {abs(_integer(minor_units)) / 100:,.2f}"


def _ask_payload(record: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    """The MCP chapter's replay: the fields trace_payment returns for the traced payment.

    mcp_server/tests/test_payload_parity.py calls the real tool and asserts equality,
    so the site never shows a tool result the server would not produce.
    """
    currency = str(record["transaction_currency"])
    payment_id = _integer(record["payment_id"])
    reasons = [r for r in str(record.get("exception_reasons") or "").split(",") if r]
    primary = str(record["primary_reason"])
    detail = ASK_RULE_SENTENCES.get(primary, "{primary} fired.").format(
        primary=primary,
        days=_integer(record["days_overdue"]),
        settled=_date(record["actual_settlement_date"]),
        expected_date=_date(record["expected_settlement_date"]),
        recorded=_display_money(currency, record["recorded_fee_minor_units"]),
        expected=_display_money(currency, record["expected_fee_minor_units"]),
        bps=_integer(record["fee_rate_bps"]),
        delta=_display_money(currency, record["fee_delta_minor_units"]),
    )
    others = "No other rule applies." if len(reasons) == 1 else f"It also carries {', '.join(r for r in reasons if r != primary)}."
    return {
        "question": f"Why was payment {payment_id} flagged?",
        "call": {"tool": "trace_payment", "arguments": {"payment_id": payment_id}},
        "result": {
            "scenario": scenario_id,
            "as_of_date": _date(record["as_of_date"]),
            "primary_reason": primary,
            "exception_reasons": reasons,
            "days_overdue": _integer(record["days_overdue"]),
            "settlement_status": None if _missing(record["settlement_status"]) else str(record["settlement_status"]),
            "fee_delta_minor_units": None if _missing(record["fee_delta_minor_units"]) else _integer(record["fee_delta_minor_units"]),
        },
        "answer": (
            f"Payment {payment_id} is a {_display_money(currency, record['gross_minor_units'])} "
            f"{record['merchant_category']} purchase from the {_date(record['close_date'])} close. "
            f"{detail} {others}"
        ),
        "tools": [
            {"name": "list_queries", "purpose": "Lists the registered queries and the parameters each accepts."},
            {"name": "run_query", "purpose": "Runs one registered query with validated parameters, at most 200 rows."},
            {"name": "trace_payment", "purpose": "Explains one payment: terms, settlement, and every rule with whether it fired."},
        ],
    }


def _evaluation_payload() -> dict[str, Any] | None:
    """Headline of the latest live MCP evaluation, read from its committed results.

    The tool path and the free-form SQL path answer the same golden questions,
    so the two accuracies are directly comparable. Dry runs are never results.
    """
    results = PROJECT_ROOT / "mcp_eval" / "results"
    questions = sorted(results.glob("questions_*.json"))
    freeform = sorted(results.glob("freeform_questions_*.json"))
    if not questions or not freeform:
        return None
    tool = json.loads(questions[-1].read_text(encoding="utf-8"))
    sql = json.loads(freeform[-1].read_text(encoding="utf-8"))
    tool_path = tool["draft"]["overall"]["end_to_end"]
    sql_path = sql["draft"]["answer_accuracy"]
    return {
        "model": tool["meta"]["model"],
        "toolPath": {"correct": tool_path["successes"], "total": tool_path["total"]},
        "ownSql": {"correct": sql_path["successes"], "total": sql_path["total"]},
    }


def _trace_payload(record: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    currency = str(record["transaction_currency"])
    flags = [
        reason for reason in str(record.get("exception_reasons") or "").split(",")
        if reason
    ]
    days_overdue = _integer(record["days_overdue"])

    def money(minor_units: Any) -> str:
        return f"{currency} {_integer(minor_units) / 100:,.2f}"

    # Written from the payment's own trace fields, per primary reason, so the
    # sentence can never describe a different failure than the flags show.
    primary = str(record["primary_reason"])
    if primary == "fee_mismatch":
        why = (
            f"The recorded fee was {money(record['recorded_fee_minor_units'])}. The "
            f"contract in force that day sets {_integer(record['fee_rate_bps'])} bps, "
            f"an expected fee of {money(record['expected_fee_minor_units'])}. Amount "
            "and currency still match."
        )
    elif primary == "late":
        why = (
            f"The settlement arrived {days_overdue} calendar days after its "
            "deadline. Amount, currency and fee still match."
        )
    elif primary == "missing":
        why = (
            "No settlement has arrived. It was due on "
            f"{_date(record['expected_settlement_date'])}, {days_overdue} days "
            "before the as-of date."
        )
    else:
        why = f"The {primary.replace('_', ' ')} rule fired for this payment."
    others = [flag.replace("_", " ") for flag in flags if flag != primary]
    why += (
        f" Other flags: {', '.join(others)}." if others
        else f" {primary.replace('_', ' ').capitalize()} is the only flag."
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
        # Falling back to the close date itself shows a pre-settlement moment
        # where nothing has arrived yet (0 matched, 0 exceptions) for any
        # scenario that doesn't define an explicit mid-story checkpoint. Three
        # days out is where delayed_travel_gbp's own investigationAsOfDate
        # sits, and it must stay strictly between the close date and
        # close date + 6 below so the four-point progression stays monotonic.
        investigation_as_of = selected.get(
            "investigationAsOfDate",
            (selected_date + dt.timedelta(days=3)).isoformat(),
        )
        narrative = REASON_NARRATIVE[selected["expectedSignal"]["primaryReason"]]

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
        expected_reason = selected["expectedSignal"]["primaryReason"]
        incident_rows = queue[queue["primary_reason"] == expected_reason]
        trace_id = _integer((incident_rows if not incident_rows.empty else queue).iloc[0]["payment_id"])
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
        count_field = narrative["count_field"]
        hit_segments = sorted(
            (row for row in segments.to_dict("records") if _integer(row[count_field])),
            key=lambda row: (-_integer(row[count_field]), str(row["merchant_category"])),
        )
        with_everyday = sum(
            1 for row in segments.to_dict("records")
            if _integer(row["exception_count"]) > _integer(row[count_field])
        )
        leader, *runners = hit_segments
        spread = (
            f"{leader['merchant_category']} carries {_integer(leader[count_field])} "
            f"of the {_integer(close_record[count_field])} {narrative['reason_label']}"
            + (
                ", then " + ", ".join(
                    f"{row['merchant_category']} ({_integer(row[count_field])})"
                    for row in runners[:3]
                )
                if runners else ""
            )
            + "."
        )
        everyday = [
            (reason, _integer(close_record[f"{reason}_count"]))
            for reason in PRIMARY_PRECEDENCE
            if reason != expected_reason and _integer(close_record[f"{reason}_count"])
        ]
        everyday_text = ", ".join(
            f"{reason.replace('_', ' ')} ({count})" for reason, count in everyday
        )
        investigation_incident = next(
            row for row in daily.to_dict("records")
            if _date(row["as_of_date"]) == investigation_as_of
        )
        incident_matched = _integer(investigation_incident["matched_count"])
        incident_eligible = _integer(investigation_incident["eligible_count"])
        exception_count = _integer(close_record[narrative["count_field"]])

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
                {"id": "model", "label": "Data"},
                {"id": "baseline", "label": "Investigation"},
                {"id": "validation", "label": "Proof"},
                {"id": "ask", "label": "Use it"},
            ],
            "question": {
                "stakeholder": (
                    f"Why do so many {selected['defaultCurrency']} purchases from the "
                    f"{selected['closeDate']} close still carry a "
                    f"{narrative['reason_noun']} exception?"
                ),
                "conciseAnswer": (
                    f"By {investigation_as_of}, {incident_matched} of "
                    f"{incident_eligible} {selected['defaultCurrency']} purchases "
                    f"from the {selected['closeDate']} close had settled for the "
                    "right gross amount. "
                    + narrative["outcome"].format(count=exception_count)
                ),
                "operationalDecision": (
                    "Fix the cause once, for every merchant it reached. Anything "
                    "left over goes through the exception queue in its usual order."
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
                    "question": "Did the close balance inside its own currency?",
                    "queryId": "close_summary",
                    "model": "mart_daily_close",
                    "sql": SQL_EXCERPTS["close_summary"],
                    "reading": (
                        f"At the {investigation_as_of} observation cut, the selected "
                        f"close was {incident_matched}/{incident_eligible} matched. "
                        "Coverage recovers, yet the exceptions stay in the final snapshot."
                    ),
                },
                {
                    "id": "isolation",
                    "label": "Segment isolation",
                    "question": (
                        f"Which merchant segment explains the "
                        f"{selected['defaultCurrency']} gap?"
                    ),
                    "queryId": "segment_isolation",
                    "model": "mart_category_health",
                    "sql": SQL_EXCERPTS["segment_isolation"],
                    "reading": (
                        f"{spread} The {narrative['reason_label']} reach "
                        f"{len(hit_segments)} of {len(segments)} categories, so this is "
                        "one cause reaching many merchants, and no category is at fault. "
                        f"{with_everyday} of {len(segments)} categories also carry "
                        "everyday exceptions of other kinds."
                    ),
                },
                {
                    "id": "classification",
                    "label": "Exception classification",
                    "question": "What does operations look at first?",
                    "queryId": "exception_queue",
                    "model": "mart_exception_queue",
                    "sql": SQL_EXCERPTS["exception_queue"],
                    "reading": (
                        f"{_integer(close_record[count_field])} "
                        f"{narrative['reason_label']} lead the close. The rest is the "
                        f"everyday mix any close carries: {everyday_text}. Each payment "
                        "keeps every flag that fired; the primary label only decides "
                        "where it sits in the queue."
                    ),
                },
            ],
            "dailyClose": _daily_rows(daily),
            "segmentFindings": _segment_rows(segments),
            "exceptionSummary": _exception_summary(close_record),
            "primaryLabelPrecedence": list(PRIMARY_PRECEDENCE),
            "trace": _trace_payload(trace.iloc[0].to_dict(), SELECTED_SCENARIO_ID),
            "ask": _ask_payload(trace.iloc[0].to_dict(), SELECTED_SCENARIO_ID),
            "evaluation": _evaluation_payload(),
            "recommendation": {
                "finding": (
                    f"{exception_count} {selected['defaultCurrency']} payments on the "
                    f"{selected['closeDate']} close carry {narrative['reason_noun']} "
                    f"exceptions, across {len(hit_segments)} categories. Most "
                    + narrative["finding_lede"] + "."
                ),
                "action": narrative["action"],
                "owner": "Settlement operations",
                "successMetricId": "settlement_coverage",
            },
            "validation": {
                "explainModel": "mart_exception_queue",
                "explainQueryId": "exception_queue",
                "explainSql": (
                    "EXPLAIN ANALYZE\n" + SQL_EXCERPTS["exception_queue"].replace(
                        ":scenario_date", f"DATE '{selected['closeDate']}'"
                    ).replace(":currency", f"'{selected['defaultCurrency']}'")
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
                    f"Open the {selected['defaultCurrency']} close on {selected['closeDate']}.",
                    "Filter the exception queue by reason and category.",
                    "Trace one payment and read the SQL rule that flagged it.",
                    "Export the filtered evidence. The snapshot never changes.",
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
