"""Aggregate scored trials into proportions with Wilson 95% intervals.

The unit is the question. Each question is repeated R times; its reported
outcome is the modal outcome across repeats, with ties broken toward failure.
Disagreement is the share of questions whose repeats did not all make the same
calls. pass^k (Yao et al., tau-bench) is the share of questions whose every
repeat was fully correct.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

Z95 = 1.959963984540054


def wilson(successes: int, total: int, z: float = Z95) -> tuple[float, float] | None:
    if total == 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def proportion(successes: int, total: int) -> dict[str, Any]:
    interval = wilson(successes, total)
    return {
        "successes": successes,
        "total": total,
        "rate": None if total == 0 else round(successes / total, 4),
        "wilson95": None if interval is None else [round(interval[0], 4), round(interval[1], 4)],
    }


def modal(outcomes: list[tuple]) -> tuple:
    """Most common outcome; on a tie, the one with the fewest successes."""
    counts = Counter(outcomes)
    best = max(counts.values())
    return min((o for o, c in counts.items() if c == best), key=lambda o: (sum(map(bool, o)), o))


def _by_question(scored: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in scored:
        grouped[row["id"]].append(row)
    return grouped


def summarize_questions(scored: list[Mapping[str, Any]], records: list[Mapping[str, Any]],
                        *, reviewed_only: bool) -> dict[str, Any]:
    """Tool, parameter, and end-to-end accuracy plus the currency boundary line."""
    by_id = {r["id"]: r for r in records}
    grouped = _by_question(scored)
    keep = [qid for qid in grouped if not reviewed_only or by_id[qid]["reviewed"]]
    categories: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    disagree = passk = selection_total = 0
    boundary_ok = boundary_total = 0
    for qid in keep:
        trials = grouped[qid]
        category = by_id[qid]["category"]
        if len({t["signature"] for t in trials}) > 1:
            disagree += 1
        if category == "currency_boundary":
            boundary_total += 1
            ok = modal([(t["behavior_ok"],) for t in trials])[0]
            boundary_ok += ok
            categories[category]["behavior_ok"].append(ok)
            continue
        selection_total += 1
        tool_ok, params_ok, executed_ok = modal(
            [(t["tool_ok"], t["params_ok"], t["executed_ok"]) for t in trials]
        )
        passk += all(t["end_to_end"] for t in trials)
        for name, value in (("tool_ok", tool_ok), ("end_to_end", tool_ok and params_ok),
                            ("executed_ok", executed_ok)):
            categories[category][name].append(value)
        if tool_ok:
            categories[category]["params_given_tool"].append(params_ok)

    def pooled(name: str) -> dict[str, Any]:
        values = [v for cat in categories.values() for v in cat.get(name, [])]
        return proportion(sum(values), len(values))

    repeats = sorted({len(grouped[qid]) for qid in keep})
    return {
        "scope": "reviewed questions only" if reviewed_only else "DRAFT: includes unreviewed questions",
        "questions": len(keep),
        "repeats": repeats,
        "overall": {
            "tool_selection": pooled("tool_ok"),
            "params_given_tool": pooled("params_given_tool"),
            "end_to_end": pooled("end_to_end"),
            "execution": pooled("executed_ok"),
            "pass_hat_k": proportion(passk, selection_total),
            "disagreement": proportion(disagree, sum(len(grouped[q]) > 1 for q in keep)),
        },
        "currency_boundary": proportion(boundary_ok, boundary_total),
        "per_category": {
            category: {name: proportion(sum(v), len(v)) for name, v in sorted(values.items())}
            for category, values in sorted(categories.items())
        },
    }


def summarize_refusals(scored: list[Mapping[str, Any]], records: list[Mapping[str, Any]],
                       *, reviewed_only: bool) -> dict[str, Any]:
    by_id = {r["id"]: r for r in records}
    grouped = _by_question(scored)
    keep = [cid for cid in grouped if not reviewed_only or by_id[cid]["reviewed"]]
    classes: dict[str, list[bool]] = defaultdict(list)
    behaviors: Counter[str] = Counter()
    disagree = blocked = 0
    for cid in keep:
        trials = grouped[cid]
        ok = modal([(t["behavior_ok"],) for t in trials])[0]
        classes[by_id[cid]["attack_class"]].append(ok)
        behaviors.update(t["behavior"] for t in trials)
        blocked += sum(t["server_blocked"] for t in trials)
        disagree += len({t["signature"] for t in trials}) > 1
    passed = [v for values in classes.values() for v in values]
    return {
        "scope": "reviewed cases only" if reviewed_only else "DRAFT: includes unreviewed cases",
        "cases": len(keep),
        "pass_rate": proportion(sum(passed), len(passed)),
        # Only items asked more than once can disagree with themselves.
        "disagreement": proportion(disagree, sum(len(grouped[c]) > 1 for c in keep)),
        "server_blocked_attempts": blocked,
        "behaviors_across_trials": dict(sorted(behaviors.items())),
        "per_attack_class": {
            name: proportion(sum(v), len(v)) for name, v in sorted(classes.items())
        },
    }


def _pct(p: Mapping[str, Any]) -> str:
    if not p["total"]:
        return "TODO (no scored items)"
    low, high = p["wilson95"]
    return f"{p['rate'] * 100:.1f}% ({low * 100:.1f} to {high * 100:.1f}), {p['successes']}/{p['total']}"


def render_markdown(summary: Mapping[str, Any], meta: Mapping[str, Any]) -> str:
    lines = [f"# {meta['suite']} results", ""]
    lines += [f"- {key}: {value}" for key, value in meta.items()]
    lines += ["", f"Scope: {summary['scope']}", ""]
    if "overall" in summary:
        lines += ["| Metric | Result (Wilson 95%) |", "|---|---|"]
        lines += [f"| {name.replace('_', ' ')} | {_pct(value)} |" for name, value in summary["overall"].items()]
        lines += [f"| currency boundary handled | {_pct(summary['currency_boundary'])} |", ""]
        groups = summary["per_category"]
    else:
        lines += ["| Metric | Result (Wilson 95%) |", "|---|---|",
                  f"| pass rate | {_pct(summary['pass_rate'])} |",
                  f"| disagreement | {_pct(summary['disagreement'])} |", "",
                  f"Server blocked attempts across all trials: {summary['server_blocked_attempts']}", ""]
        groups = {name: {"pass": value} for name, value in summary["per_attack_class"].items()}
    lines += ["| Group | Metric | Result |", "|---|---|---|"]
    for group, values in groups.items():
        lines += [f"| {group} | {name.replace('_', ' ')} | {_pct(value)} |" for name, value in values.items()]
    return "\n".join(lines) + "\n"
