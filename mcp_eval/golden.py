"""Golden question set for the MCP evaluation.

Question wording and the expected tool call are written by hand below. Every
expected answer is derived from the snapshot through ``AnalyticsEngine.query``
using the recorded ``answer_source``, so ``check`` can prove the golden file
still matches the data. ``build`` keeps any ``reviewed`` flag already set.

    python -m mcp_eval.golden build
    python -m mcp_eval.golden check
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.analytics_engine import AnalyticsEngine  # noqa: E402

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
QUESTIONS_PATH = GOLDEN_DIR / "questions.jsonl"

TOOLS = ("list_queries", "run_query", "trace_payment")
CATEGORIES = (
    "payment_trace", "close_kpi", "exception_queue", "segment_isolation",
    "metadata", "ambiguous", "currency_boundary",
)
EVALUATED_QUERY_IDS = (
    "scenario_options", "close_summary", "segment_isolation", "exception_queue",
    "payment_trace", "catalog_metrics", "quality_results",
)
BEHAVIORS = ("refuse", "split_by_currency", "same_currency_sum_allowed")
RECORD_KEYS = (
    "id", "question", "category", "expected_tool", "expected_query_id",
    "expected_params", "expected_calls", "alternatives", "acceptable_extra",
    "expected_answer", "answer_source", "expected_behavior",
    "accepted_behaviors", "why", "reviewed",
)
SCENARIO_CURRENCY = {
    "normal": "EUR",
    "delayed_travel_gbp": "GBP",
    "stale_electronics_eur_fee": "EUR",
    "missing_retail_cad": "CAD",
}
# trace_payment reads each scenario at its own investigation date.
TRACE_AS_OF = {
    "normal": "2025-01-10",
    "delayed_travel_gbp": "2024-10-14",
    "stale_electronics_eur_fee": "2025-01-10",
    "missing_retail_cad": "2025-01-10",
}
SNAPSHOT_AS_OF = "2025-01-10"


def _run(query_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"tool": "run_query", "query_id": query_id, "params": params or {}}


def _source(query_id: str, params: dict[str, Any], op: str, **extra: Any) -> dict[str, Any]:
    return {"query_id": query_id, "params": params, "op": op, **extra}


def _trace(qid: str, question: str, payment_id: int, scenario: str, fields: list[str],
           as_of: str | None = None) -> dict[str, Any]:
    params = {"payment_id": payment_id}
    if as_of:
        params["as_of_date"] = as_of
    run_params = {"scenario": scenario, "payment_id": payment_id}
    if as_of:
        run_params["as_of_date"] = as_of
    return {
        "id": qid,
        "question": question,
        "category": "payment_trace",
        "expected_tool": "trace_payment",
        "expected_query_id": None,
        "expected_params": params,
        "alternatives": [_run("payment_trace", run_params)],
        "acceptable_extra": {"scenario": scenario, **({} if as_of else {"as_of_date": TRACE_AS_OF[scenario]})},
        "answer_source": _source(
            "payment_trace",
            {**run_params, "as_of_date": as_of or TRACE_AS_OF[scenario]},
            "row", fields=fields,
        ),
    }


def _query(qid: str, question: str, category: str, query_id: str,
           params: dict[str, Any], source: dict[str, Any] | None) -> dict[str, Any]:
    extra = {}
    if "scenario" in params:
        extra["currency"] = SCENARIO_CURRENCY[params["scenario"]]
        extra.setdefault("as_of_date", params.get("as_of_date", SNAPSHOT_AS_OF))
    return {
        "id": qid,
        "question": question,
        "category": category,
        "expected_tool": "run_query",
        "expected_query_id": query_id,
        "expected_params": params,
        "alternatives": [],
        "acceptable_extra": {k: v for k, v in extra.items() if k not in params},
        "answer_source": source,
    }


def _ambiguous(qid: str, question: str, options: list[tuple[str, dict[str, Any]]],
               source: dict[str, Any], why: str) -> dict[str, Any]:
    record = _query(qid, question, "ambiguous", options[0][0], options[0][1], source)
    record["expected_query_id"] = [query_id for query_id, _ in options]
    record["alternatives"] = [_run(query_id, params) for query_id, params in options]
    record["why"] = why
    return record


def _boundary(qid: str, question: str, calls: list[dict[str, Any]], behavior: str,
              accepted: list[str], sources: list[dict[str, Any]], why: str) -> dict[str, Any]:
    return {
        "id": qid,
        "question": question,
        "category": "currency_boundary",
        "expected_tool": "run_query" if calls else None,
        "expected_query_id": calls[0]["query_id"] if calls else None,
        "expected_params": None,
        "expected_calls": calls,
        "alternatives": [],
        "acceptable_extra": {},
        "answer_source": {"op": "each", "sources": sources} if sources else None,
        "expected_behavior": behavior,
        "accepted_behaviors": accepted,
        "why": why,
    }


def _close(scenario: str, fields: list[str], as_of: str | None = None) -> dict[str, Any]:
    params = {"scenario": scenario}
    if as_of:
        params["as_of_date"] = as_of
    return _source("close_summary", params, "row", fields=fields)


D, S, M, N = "delayed_travel_gbp", "stale_electronics_eur_fee", "missing_retail_cad", "normal"

SPECS: list[dict[str, Any]] = [
    # payment_trace
    _trace("q001", "Why was payment 238833 flagged?", 238833, M,
           ["primary_reason", "days_overdue", "transaction_currency", "gross_minor_units"]),
    _trace("q002", "Explain what happened with payment 231728.", 231728, S,
           ["primary_reason", "fee_rate_bps", "expected_fee_minor_units",
            "recorded_fee_minor_units", "fee_delta_minor_units"]),
    _trace("q003", "What is the status of payment 221416?", 221416, D,
           ["primary_reason", "days_overdue", "expected_settlement_date"]),
    _trace("q004", "As of 2025-01-10, how did payment 221416 end up being classified?", 221416, D,
           ["primary_reason", "days_overdue", "actual_settlement_date"], as_of="2025-01-10"),
    _trace("q005", "Did payment 214760 reconcile cleanly?", 214760, N,
           ["primary_reason", "is_match", "exception_reasons"]),
    _trace("q006", "Which merchant was payment 238837 made at, and when was it due to settle?", 238837, M,
           ["merchant_id", "merchant_name", "expected_settlement_date"]),
    _trace("q007", "What fee should have been charged on payment 231729 under the merchant's current terms?",
           231729, S, ["fee_rate_bps", "expected_fee_minor_units", "transaction_currency"]),
    _trace("q008", "Payment 221423: was it late, and by how many days, as of 2024-10-16?", 221423, D,
           ["primary_reason", "is_late", "days_overdue"], as_of="2024-10-16"),
    {
        "id": "q009",
        "question": "Why was payment 12 flagged?",
        "category": "payment_trace",
        "expected_tool": "trace_payment",
        "expected_query_id": None,
        "expected_params": {"payment_id": 12},
        "alternatives": [],
        "acceptable_extra": {},
        "answer_source": {"op": "trace_absent", "payment_id": 12},
        "why": "Payment 12 exists but is in no scenario close, so the correct outcome is "
               "to call trace_payment and report that it is outside the traced closes.",
    },
    # close_kpi
    _query("q010", "How many exceptions did the normal close have?", "close_kpi",
           "close_summary", {"scenario": N}, _close(N, ["exception_count", "eligible_count"])),
    {**_query("q011", "How many payments settled late in the GBP partner outage close?", "close_kpi",
              "close_summary", {"scenario": D}, _close(D, ["late_count", "eligible_count"])),
     "alternatives": [_run("exception_queue", {"scenario": D})],
     "why": "Counting late rows in the exception queue gives the same number, as q038 already accepts."},
    _query("q012", "As of 2024-10-14, how many payments in the GBP partner outage close were still missing a settlement?",
           "close_kpi", "close_summary", {"scenario": D, "as_of_date": "2024-10-14"},
           _close(D, ["missing_count", "matched_count"], as_of="2024-10-14")),
    _query("q013", "What was the total fee delta on the stale fee EUR close?", "close_kpi",
           "close_summary", {"scenario": S}, _close(S, ["fee_delta_minor_units", "currency"])),
    _query("q014", "What was settlement coverage on the CAD lost-file close?", "close_kpi",
           "close_summary", {"scenario": M}, _close(M, ["coverage_rate", "matched_count", "eligible_count"])),
    _query("q015", "How much value is overdue on the CAD lost-file close?", "close_kpi",
           "close_summary", {"scenario": M}, _close(M, ["overdue_minor_units", "currency"])),
    _query("q016", "What was the gross value of the 2024-09-17 EUR close?", "close_kpi",
           "close_summary", {"scenario": N}, _close(N, ["gross_minor_units", "currency"])),
    _query("q017", "How many fee mismatches were on the stale fee close?", "close_kpi",
           "close_summary", {"scenario": S}, _close(S, ["fee_mismatch_count"])),
    # exception_queue
    _query("q018", "Which merchant has the most exceptions in the CAD lost-file close?", "exception_queue",
           "exception_queue", {"scenario": M},
           _source("exception_queue", {"scenario": M}, "top", by=["merchant_id", "merchant_name"])),
    _query("q019", "Which merchant accounts for most of the stale fee exceptions?", "exception_queue",
           "exception_queue", {"scenario": S},
           _source("exception_queue", {"scenario": S}, "top", by=["merchant_id", "merchant_name"])),
    _query("q020", "How many different merchants are affected by the GBP partner outage?", "exception_queue",
           "exception_queue", {"scenario": D},
           _source("exception_queue", {"scenario": D}, "nunique", column="merchant_id")),
    _query("q021", "What is the longest overdue period in the CAD lost-file exception queue?",
           "exception_queue", "exception_queue", {"scenario": M},
           _source("exception_queue", {"scenario": M}, "max", column="days_overdue")),
    _query("q022", "List the GBP exceptions from the partner outage close.", "exception_queue",
           "exception_queue", {"scenario": D},
           _source("exception_queue", {"scenario": D, "currency": "GBP"}, "count")),
    _query("q023", "How many payments are in the exception queue for the stale fee scenario?",
           "exception_queue", "exception_queue", {"scenario": S},
           _source("exception_queue", {"scenario": S}, "count")),
    _query("q024", "Are there any exceptions in the normal EUR close?", "exception_queue",
           "exception_queue", {"scenario": N},
           _source("exception_queue", {"scenario": N}, "count")),
    # segment_isolation
    _query("q025", "Which merchant category is behind the delayed GBP close?", "segment_isolation",
           "segment_isolation", {"scenario": D},
           _source("segment_isolation", {"scenario": D}, "top_by",
                   column="exception_count", fields=["merchant_category", "exception_count", "eligible_count"])),
    _query("q026", "Break down the missing CAD close by merchant category.", "segment_isolation",
           "segment_isolation", {"scenario": M},
           _source("segment_isolation", {"scenario": M}, "count")),
    _query("q027", "Which category has the most fee mismatches on 2024-11-12?", "segment_isolation",
           "segment_isolation", {"scenario": S},
           _source("segment_isolation", {"scenario": S}, "top_by",
                   column="exception_count", fields=["merchant_category", "exception_count"])),
    _query("q028", "In the normal close, how many Services payments were there?", "segment_isolation",
           "segment_isolation", {"scenario": N},
           _source("segment_isolation", {"scenario": N}, "row_where",
                   where={"merchant_category": "Services"}, fields=["eligible_count", "exception_count"])),
    _query("q029", "In the CAD lost-file close, how many Retail payments were there, and how many were exceptions?",
           "segment_isolation", "segment_isolation", {"scenario": M},
           _source("segment_isolation", {"scenario": M}, "row_where",
                   where={"merchant_category": "Retail"}, fields=["eligible_count", "exception_count"])),
    # metadata
    {
        "id": "q030",
        "question": "What questions can you answer about this payments data?",
        "category": "metadata",
        "expected_tool": "list_queries",
        "expected_query_id": None,
        "expected_params": {},
        "alternatives": [],
        "acceptable_extra": {},
        "answer_source": None,
    },
    _query("q031", "Which scenarios are available?", "metadata", "scenario_options", {},
           _source("scenario_options", {}, "count")),
    _query("q032", "What investigation date does the GBP partner outage scenario use?", "metadata",
           "scenario_options", {},
           _source("scenario_options", {}, "row_where",
                   where={"scenario_id": D}, fields=["as_of_date", "close_date"])),
    _query("q033", "How is settlement coverage defined?", "metadata", "catalog_metrics", {},
           _source("catalog_metrics", {}, "row_where",
                   where={"metric_id": "settlement_coverage"}, fields=["name", "grain"])),
    _query("q034", "Do all the data quality checks pass?", "metadata", "quality_results", {},
           _source("quality_results", {}, "count_where", where={"status": "pass"})),
    # ambiguous
    _ambiguous("q035", "How bad was the CAD lost-file close?",
               [("close_summary", {"scenario": M}), ("exception_queue", {"scenario": M}),
                ("segment_isolation", {"scenario": M})],
               _close(M, ["exception_count", "missing_count"]),
               "Severity can be read from the KPI row, the queue, or the category breakdown; all three are scoped to the same close."),
    _ambiguous("q036", "What went wrong on 2024-11-12?",
               [("close_summary", {"scenario": S}), ("segment_isolation", {"scenario": S}),
                ("exception_queue", {"scenario": S})],
               _close(S, ["fee_mismatch_count", "exception_count"]),
               "The date identifies the stale fee close; the summary, category, and queue views each show the fee mismatch."),
    _ambiguous("q037", "Which part of the business did the GBP partner outage hit?",
               [("segment_isolation", {"scenario": D}), ("exception_queue", {"scenario": D})],
               _source("segment_isolation", {"scenario": D}, "top_by",
                       column="exception_count", fields=["merchant_category", "exception_count"]),
               "The hit can be read by merchant category (segment isolation) or by specific merchants (exception queue)."),
    _ambiguous("q038", "How many late payments were there in the GBP partner outage close?",
               [("close_summary", {"scenario": D}), ("exception_queue", {"scenario": D})],
               _close(D, ["late_count"]),
               "The close summary gives the count directly; counting queue rows gives the same number."),
    _ambiguous("q039", "Was anything wrong with the normal close?",
               [("close_summary", {"scenario": N}), ("exception_queue", {"scenario": N})],
               _close(N, ["exception_count"]),
               "Zero exceptions shows in the summary row and as an empty queue."),
    # currency_boundary
    _boundary("q040", "What is the combined gross value of the normal EUR close and the CAD lost-file close?",
              [_run("close_summary", {"scenario": N}), _run("close_summary", {"scenario": M})],
              "split_by_currency", ["split_by_currency", "refuse"],
              [_close(N, ["gross_minor_units", "currency"]), _close(M, ["gross_minor_units", "currency"])],
              "EUR and CAD must not be added; report each close in its own currency or decline the sum."),
    _boundary("q041", "Add up the overdue value of the CAD lost-file close and the GBP partner outage close.",
              [_run("close_summary", {"scenario": M}), _run("close_summary", {"scenario": D})],
              "split_by_currency", ["split_by_currency", "refuse"],
              [_close(M, ["overdue_minor_units", "currency"]), _close(D, ["overdue_minor_units", "currency"])],
              "CAD and GBP amounts stay separate; the correct answer lists two figures."),
    _boundary("q042", "What is the total fee delta across all four scenario closes, in euros?",
              [_run("close_summary", {"scenario": s}) for s in (N, D, S, M)],
              "split_by_currency", ["split_by_currency", "refuse"],
              [_close(s, ["fee_delta_minor_units", "currency"]) for s in (N, D, S, M)],
              "There is no FX data, so a single euro total is impossible. Adding the two EUR closes together is "
              "allowed; GBP and CAD must stay separate. Per currency figures or a refusal are correct."),
    _boundary("q043", "Convert the overdue CAD amount on the lost-file close into EUR.",
              [], "refuse", ["refuse"], [],
              "The snapshot has no exchange rates and the guardrails forbid FX conversion."),
    _boundary("q044", "Compare the overdue value of the GBP partner outage close with the CAD lost-file close.",
              [_run("close_summary", {"scenario": D}), _run("close_summary", {"scenario": M})],
              "split_by_currency", ["split_by_currency"],
              [_close(D, ["overdue_minor_units", "currency"]), _close(M, ["overdue_minor_units", "currency"])],
              "A comparison is fine as long as each figure keeps its own currency and nothing is summed or converted."),
    _boundary("q045", "What is the combined gross value of the normal close and the stale fee close?",
              [_run("close_summary", {"scenario": N}), _run("close_summary", {"scenario": S})],
              "same_currency_sum_allowed", ["same_currency_sum_allowed", "split_by_currency"],
              [_close(N, ["gross_minor_units", "currency"]), _close(S, ["gross_minor_units", "currency"])],
              "Control case: both closes are EUR, which the model has to find out, so adding them is allowed "
              "and refusing is over-refusal."),
]


def _plain(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value) if value.is_integer() else round(value, 4)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()[:10]
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return value


def derive_answer(engine: AnalyticsEngine, source: dict[str, Any] | None) -> Any:
    """Replay one answer_source against the snapshot."""
    if source is None:
        return None
    op = source["op"]
    if op == "each":
        return [derive_answer(engine, item) for item in source["sources"]]
    if op == "trace_absent":
        found = any(
            not engine.query("payment_trace", {"scenario": s, "payment_id": source["payment_id"]}).empty
            for s in SCENARIO_CURRENCY
        )
        return {"found": found}
    frame = engine.query(source["query_id"], source["params"])
    if op == "count":
        return {"row_count": len(frame)}
    if op == "count_where":
        mask = (frame[list(source["where"])] == list(source["where"].values())).all(axis=1)
        return {"row_count": int(mask.sum()), "total_rows": len(frame)}
    if op == "nunique":
        return {f"distinct_{source['column']}": int(frame[source["column"]].nunique())}
    if op == "max":
        return {f"max_{source['column']}": _plain(frame[source["column"]].max())}
    if op == "top":
        counts = frame.groupby(source["by"]).size().sort_values(ascending=False, kind="stable")
        key = counts.index[0]
        key = key if isinstance(key, tuple) else (key,)
        return {**{c: _plain(v) for c, v in zip(source["by"], key)}, "row_count": int(counts.iloc[0])}
    if op == "top_by":
        row = frame.sort_values(source["column"], ascending=False, kind="stable").iloc[0]
        return {field: _plain(row[field]) for field in source["fields"]}
    if op == "row_where":
        mask = (frame[list(source["where"])] == list(source["where"].values())).all(axis=1)
        row = frame[mask].iloc[0]
        return {field: _plain(row[field]) for field in source["fields"]}
    if op == "row":
        if len(frame) != 1:
            raise ValueError(f"Expected one row for {source}, got {len(frame)}")
        return {field: _plain(frame.iloc[0][field]) for field in source["fields"]}
    raise ValueError(f"Unknown answer op {op!r}")


def _record(spec: dict[str, Any], answer: Any, reviewed: bool) -> dict[str, Any]:
    record = {key: None for key in RECORD_KEYS}
    record.update({"expected_calls": None, "alternatives": [], "acceptable_extra": {}})
    record.update(spec)
    record["expected_answer"] = answer
    record["reviewed"] = reviewed
    return {key: record[key] for key in RECORD_KEYS}


def load(path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build(engine: AnalyticsEngine | None = None, path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    previous = {row["id"]: row for row in load(path)}
    engine = engine or AnalyticsEngine(build_sha="mcp-eval")
    records = []
    for spec in SPECS:
        earlier = previous.get(spec["id"])
        # A review only carries over while the question itself is unchanged.
        reviewed = bool(earlier and earlier.get("reviewed") and earlier["question"] == spec["question"])
        records.append(_record(spec, derive_answer(engine, spec.get("answer_source")), reviewed))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8", newline="\n",
    )
    return records


def validate_record(record: dict[str, Any]) -> list[str]:
    """Structural problems with one golden record (empty list when valid)."""
    problems = []
    if tuple(record) != RECORD_KEYS:
        problems.append("keys differ from RECORD_KEYS")
    if record.get("category") not in CATEGORIES:
        problems.append(f"unknown category {record.get('category')!r}")
    if not isinstance(record.get("reviewed"), bool):
        problems.append("reviewed must be a boolean")
    tool = record.get("expected_tool")
    query_ids = record.get("expected_query_id")
    ids = query_ids if isinstance(query_ids, list) else [query_ids] if query_ids else []
    if any(query_id not in EVALUATED_QUERY_IDS for query_id in ids):
        problems.append("expected_query_id outside the evaluated registry")
    if record["category"] == "currency_boundary":
        if record.get("expected_behavior") not in BEHAVIORS:
            problems.append("currency_boundary needs expected_behavior")
        if record["expected_behavior"] not in (record.get("accepted_behaviors") or []):
            problems.append("expected_behavior must be one of accepted_behaviors")
        if record["expected_behavior"] != "refuse" and not record.get("expected_calls"):
            problems.append("non refusal boundary record needs expected_calls")
        if not record.get("why"):
            problems.append("currency_boundary needs why")
    else:
        if tool not in TOOLS:
            problems.append(f"unknown expected_tool {tool!r}")
        if not isinstance(record.get("expected_params"), dict):
            problems.append("expected_params must be an object")
        if tool == "run_query" and not ids:
            problems.append("run_query record needs expected_query_id")
        if tool != "run_query" and query_ids is not None:
            problems.append("only run_query records carry expected_query_id")
    if isinstance(query_ids, list):
        if len(query_ids) < 2 or not record.get("why"):
            problems.append("list expected_query_id needs two or more IDs and a why")
        if [alt["query_id"] for alt in record["alternatives"]] != query_ids:
            problems.append("alternatives must list each acceptable query ID in order")
    return problems


def check(engine: AnalyticsEngine | None = None, path: Path = QUESTIONS_PATH) -> list[str]:
    """Every problem found: schema, drift from SPECS, or answers that no longer match."""
    records = load(path)
    problems = []
    if [r["id"] for r in records] != [s["id"] for s in SPECS]:
        problems.append("question IDs differ from SPECS; run build")
    engine = engine or AnalyticsEngine(build_sha="mcp-eval")
    for record in records:
        problems.extend(f"{record.get('id')}: {p}" for p in validate_record(record))
        actual = derive_answer(engine, record.get("answer_source"))
        if actual != record.get("expected_answer"):
            problems.append(f"{record['id']}: answer drifted {record['expected_answer']} != {actual}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("build", "check"))
    args = parser.parse_args()
    if args.command == "build":
        records = build()
        print(f"Wrote {len(records)} questions to {QUESTIONS_PATH}")
        return
    problems = check()
    for problem in problems:
        print(problem)
    print("Golden set matches the snapshot." if not problems else f"{len(problems)} problems.")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
