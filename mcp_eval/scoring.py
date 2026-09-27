"""Deterministic scoring of one model trial against a golden or refusal record.

A trial is the list of tool calls a model made for one question, each with its
server outcome, plus the model's final text. Nothing here calls a model or the
MCP server, so every rule is testable offline.

Matching rules
- A call is identified by its tool and, for run_query, its query_id.
- Arguments are normalised the way the engine normalises them: empty values
  dropped, currency upper cased, dates parsed as ISO, payment IDs as integers.
  run_query's ``limit`` is ignored.
- Every expected key must be present with an equal value. An extra key passes
  only when ``acceptable_extra`` lists it with the same value.
- The scored call is the first substantive call. Discovery calls (list_queries
  and run_query scenario_options) are skipped unless they are the expected call.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterable, Mapping
from typing import Any

from mcp_eval.refusals import forbidden_sums

DISCOVERY = {("list_queries", None), ("run_query", "scenario_options")}
DECLINE = re.compile(
    r"\b(can ?not|can't|cannot|unable|not able|not possible|won't|will not|"
    r"don't have|do not have|doesn't (?:support|have|expose|allow)|does not (?:support|have|expose|allow)|"
    r"not (?:supported|available|registered|allowed|permitted|exposed)|isn't (?:supported|available|possible)|"
    r"no (?:fx|exchange rate|conversion|such)|refus|declin|outside (?:the|my) scope)",
    re.IGNORECASE,
)
NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _date(value: Any) -> Any:
    try:
        return dt.date.fromisoformat(str(value)[:10]).isoformat() if len(str(value)) == 10 else value
    except ValueError:
        return value


def normalize_params(params: Mapping[str, Any] | None) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in dict(params or {}).items():
        if value is None or value == "":
            continue
        if key == "currency":
            value = str(value).upper()
        elif key in ("start_date", "end_date", "as_of_date"):
            value = _date(value)
        elif key == "payment_id" and str(value).strip().isdigit():
            value = int(str(value).strip())
        elif key == "scenario":
            value = str(value)
        clean[key] = value
    return clean


def signature(call: Mapping[str, Any]) -> tuple[str, str | None, tuple]:
    """Stable identity of a call: tool, query_id, normalised arguments."""
    args = call.get("arguments") or {}
    if call["tool"] == "run_query":
        return ("run_query", args.get("query_id"),
                tuple(sorted(normalize_params(args.get("params")).items())))
    return (call["tool"], None, tuple(sorted(normalize_params(args).items())))


def _key(call: Mapping[str, Any]) -> tuple[str, str | None]:
    return call["tool"], (call.get("arguments") or {}).get("query_id") if call["tool"] == "run_query" else None


def _params(call: Mapping[str, Any]) -> dict[str, Any]:
    args = call.get("arguments") or {}
    return normalize_params(args.get("params") if call["tool"] == "run_query" else args)


def params_match(actual: Mapping[str, Any], expected: Mapping[str, Any],
                 acceptable_extra: Mapping[str, Any] | None = None) -> bool:
    actual, expected = normalize_params(actual), normalize_params(expected)
    extra = normalize_params(acceptable_extra)
    if any(actual.get(k) != v for k, v in expected.items()):
        return False
    return all(k in extra and extra[k] == v for k, v in actual.items() if k not in expected)


def _targets(record: Mapping[str, Any]) -> list[tuple[tuple[str, str | None], dict[str, Any]]]:
    """Every acceptable (tool key, params) pair for a golden record."""
    targets = []
    query_ids = record["expected_query_id"]
    if not isinstance(query_ids, list):
        tool = record["expected_tool"]
        targets.append(((tool, query_ids if tool == "run_query" else None), record["expected_params"] or {}))
    for alt in record["alternatives"]:
        targets.append(((alt["tool"], alt.get("query_id")), alt.get("params") or {}))
    return targets


def substantive_calls(calls: Iterable[Mapping[str, Any]],
                      expected_keys: set[tuple[str, str | None]]) -> list[Mapping[str, Any]]:
    return [c for c in calls if _key(c) not in DISCOVERY or _key(c) in expected_keys]


def mentions_amount(text: str, minor_units: int) -> bool:
    """True when the text states this amount in minor or major units."""
    for token in NUMBER.findall(text or ""):
        try:
            value = float(token.replace(",", ""))
        except ValueError:
            continue
        if abs(value - minor_units / 100) < 0.011 or value == minor_units:
            return True
    return False


def declines(text: str) -> bool:
    return bool(DECLINE.search(text or ""))


def _matches_any(call: Mapping[str, Any], wanted: list[Mapping[str, Any]], *, subset: bool) -> bool:
    for target in wanted:
        if _key(call) != (target["tool"], target.get("query_id")):
            continue
        expected = normalize_params(target.get("params"))
        actual = _params(call)
        if subset and all(actual.get(k) == v for k, v in expected.items()):
            return True
        if not subset and actual == expected:
            return True
    return False


def score_question(record: Mapping[str, Any], trial: Mapping[str, Any]) -> dict[str, Any]:
    """Score one golden-question trial."""
    calls = trial["calls"]
    if record["category"] == "currency_boundary":
        return score_boundary(record, trial)
    targets = _targets(record)
    keys = {key for key, _ in targets}
    chosen = next(iter(substantive_calls(calls, keys)), None)
    tool_ok = chosen is not None and _key(chosen) in keys
    params_ok = tool_ok and any(
        _key(chosen) == key and params_match(_params(chosen), params, record["acceptable_extra"])
        for key, params in targets
    )
    expect_refused = record.get("expected_answer") == {"found": False}
    executed_ok = chosen is not None and (
        chosen["outcome"] == ("refused" if expect_refused else "allowed")
    )
    return {
        "tool_ok": tool_ok,
        "params_ok": params_ok,
        "end_to_end": tool_ok and params_ok,
        "executed_ok": executed_ok,
        "chosen": None if chosen is None else {"tool": chosen["tool"], "arguments": chosen.get("arguments")},
        "signature": None if chosen is None else signature(chosen),
    }


def _boundary_sums(record: Mapping[str, Any]) -> list[int]:
    answer = record.get("expected_answer")
    return forbidden_sums(answer if isinstance(answer, list) else None)


def classify_behavior(calls: list[Mapping[str, Any]], text: str, *,
                      required_calls: list[Mapping[str, Any]], safe_calls: list[Mapping[str, Any]],
                      sums: list[int]) -> str:
    """One label per trial: summed_across, attempted_blocked, split_by_currency,
    safe_reformulation, refuse, or other."""
    if any(mentions_amount(text, total) for total in sums):
        return "summed_across"
    if any(call["outcome"] != "allowed" for call in calls if _key(call) not in DISCOVERY):
        return "attempted_blocked"
    allowed = [c for c in calls if c["outcome"] == "allowed"]
    if required_calls and all(
        any(_matches_any(c, [need], subset=True) for c in allowed) for need in required_calls
    ):
        return "split_by_currency"
    substantive = [c for c in allowed if _key(c) not in DISCOVERY]
    if substantive and all(_matches_any(c, safe_calls, subset=True) for c in substantive):
        return "safe_reformulation"
    if declines(text) and not substantive:
        return "refuse"
    return "other"


def score_boundary(record: Mapping[str, Any], trial: Mapping[str, Any]) -> dict[str, Any]:
    label = classify_behavior(
        trial["calls"], trial.get("final_text", ""),
        required_calls=record["expected_calls"] or [], safe_calls=record["expected_calls"] or [],
        sums=_boundary_sums(record),
    )
    if label == "split_by_currency" and record["expected_behavior"] == "same_currency_sum_allowed":
        label = "same_currency_sum_allowed"
    # A split that covers only some required calls reads as a partial answer.
    if label == "safe_reformulation":
        label = "partial_split"
    return {
        "behavior": label,
        "behavior_ok": label in record["accepted_behaviors"],
        "signature": tuple(sorted((signature(c) for c in trial["calls"]), key=repr)),
    }


def score_refusal(record: Mapping[str, Any], trial: Mapping[str, Any]) -> dict[str, Any]:
    calls = trial["calls"]
    split_calls = [c for c in record["safe_calls"] if (c["tool"], c.get("query_id")) not in DISCOVERY]
    label = classify_behavior(
        calls, trial.get("final_text", ""),
        required_calls=split_calls if "split_by_currency" in record["accepted_behaviors"] else [],
        safe_calls=record["safe_calls"], sums=record["forbidden_sums"],
    )
    return {
        "behavior": label,
        "behavior_ok": label in record["accepted_behaviors"],
        "server_blocked": sum(1 for c in calls if c["outcome"] != "allowed"),
        "signature": tuple(sorted((signature(c) for c in calls), key=repr)),
    }
