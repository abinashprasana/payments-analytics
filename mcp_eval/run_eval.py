"""Drive the golden or refusal set through the real MCP tools and score it.

Live runs need GROQ_API_KEY in the environment and the MCP server's
dependencies plus the eval extras, for example from the repository root:

    uv run --project mcp_server --with-requirements requirements-eval.txt \
        python -m mcp_eval.run_eval --suite questions

--dry-run replaces the model with a scripted oracle that makes the expected
calls. It needs no key and no network, and checks the tool path and scoring
end to end. Its output is written with a dryrun_ prefix and is never a result.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import anyio

from mcp_eval import agent_stub, golden, metrics, refusals, scoring

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def oracle_turns(record: dict[str, Any], suite: str) -> list[Any]:
    """The calls and answer a perfectly behaved model would give."""
    if suite == "refusal":
        behavior = record["expected_behavior"]
        substantive = [c for c in record["safe_calls"]
                       if (c["tool"], c.get("query_id")) not in scoring.DISCOVERY]
        if behavior == "refuse":
            return ["I can't do that: it is not supported by the registered queries."]
        chosen = substantive if behavior == "split_by_currency" else substantive[:1]
        return [[_as_call(c) for c in chosen], "Each figure is reported in its own currency."]
    if record["category"] == "currency_boundary":
        if record["expected_behavior"] == "refuse":
            return ["I can't convert currencies: the snapshot has no exchange rates."]
        return [[_as_call(c) for c in record["expected_calls"]],
                "Each close is reported in its own currency."]
    if record["expected_tool"] == "list_queries":
        return [[("list_queries", {})], "Here are the registered queries."]
    if isinstance(record["expected_query_id"], list):
        return [[_as_call(record["alternatives"][0])], "Answered from the registry."]
    if record["expected_tool"] == "trace_payment":
        return [[("trace_payment", record["expected_params"])], "Answered from the trace."]
    return [[("run_query", {"query_id": record["expected_query_id"],
                            "params": record["expected_params"]})], "Answered from the registry."]


def _as_call(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if call["tool"] == "run_query":
        return "run_query", {"query_id": call["query_id"], "params": call.get("params") or {}}
    return call["tool"], call.get("params") or {}


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, check=True, cwd=golden.PROJECT_ROOT).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MCP natural language evaluation.")
    parser.add_argument("--suite", choices=("questions", "refusal"), required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-requests", type=int, default=400)
    parser.add_argument("--model", default=agent_stub.DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--pace", type=float, default=2.1, help="seconds between model requests")
    parser.add_argument("--only", help="comma separated record IDs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.dry_run and not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set. Set it in your environment (never in a file) "
              "and rerun. No results were written; README figures stay TODO.")
        return 2

    records = golden.load() if args.suite == "questions" else refusals.load(refusals.REFUSALS_PATH)
    if args.only:
        wanted = set(args.only.split(","))
        records = [r for r in records if r["id"] in wanted]
    started = dt.datetime.now(dt.timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = RESULTS_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SETTLEMENT_GAP_AUDIT_LOG"] = str(raw_dir / f"audit_{args.suite}_{stamp}.jsonl")
    budget = None if args.dry_run else agent_stub.Budget(args.max_requests, args.pace)
    live_model = None if args.dry_run else agent_stub.GroqModel(args.model, args.temperature)
    tools = agent_stub.load_tools()

    scored: list[dict[str, Any]] = []
    transcripts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    stopped = None
    for record in records:
        prompt = record["question"] if args.suite == "questions" else record["prompt"]
        for repeat in range(1, args.repeats + 1):
            model = agent_stub.ScriptedModel(oracle_turns(record, args.suite)) if args.dry_run else live_model
            try:
                trial = anyio.run(agent_stub.run_trial, model, prompt, budget, tools)
            except agent_stub.BudgetExhausted as exc:
                stopped = str(exc)
                break
            except Exception as exc:  # provider failure after the client's own retries
                errors.append({"id": record["id"], "repeat": repeat, "error": f"{type(exc).__name__}: {exc}"})
                if "401" in str(exc) or "invalid_api_key" in str(exc):
                    stopped = "authentication failed"
                    break
                continue
            score = (scoring.score_question(record, trial) if args.suite == "questions"
                     else scoring.score_refusal(record, trial))
            scored.append({"id": record["id"], "repeat": repeat, **score})
            transcripts.append({"id": record["id"], "repeat": repeat, **trial})
            print(f"{record['id']} r{repeat}: " + ", ".join(
                f"{k}={v}" for k, v in score.items() if k not in ("signature", "chosen")))
        if stopped:
            break

    summarize = metrics.summarize_questions if args.suite == "questions" else metrics.summarize_refusals
    meta = {
        "suite": args.suite,
        "mode": "dry run (scripted oracle, not a result)" if args.dry_run else "live",
        "provider": "scripted" if args.dry_run else "groq",
        "model": "scripted" if args.dry_run else args.model,
        "temperature": args.temperature,
        "repeats": args.repeats,
        "started_utc": started.isoformat(timespec="seconds"),
        "dataset": json.loads(
            (golden.PROJECT_ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))["datasetVersion"],
        "git_sha": _git_sha(),
        "requests_used": None if budget is None else budget.used,
        "max_requests": args.max_requests,
        "trials_scored": len(scored),
        "trial_errors": len(errors),
        "stopped_early": stopped,
    }
    output = {
        "meta": meta,
        "reviewed": summarize(scored, records, reviewed_only=True),
        "draft": summarize(scored, records, reviewed_only=False),
        "errors": errors,
    }
    prefix = "dryrun_" if args.dry_run else ""
    slug = re.sub(r"[^a-z0-9]+", "-", meta["model"].lower()).strip("-")
    base = RESULTS_DIR / f"{prefix}{args.suite}_{slug}_{started:%Y%m%d}"
    base.with_suffix(".json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    base.with_suffix(".md").write_text(
        metrics.render_markdown(output["reviewed"], meta) + "\n"
        + metrics.render_markdown(output["draft"], {**meta, "suite": f"{args.suite} (draft)"}),
        encoding="utf-8",
    )
    (raw_dir / f"{prefix}{args.suite}_{stamp}.jsonl").write_text(
        "".join(json.dumps(t, default=str) + "\n" for t in transcripts), encoding="utf-8")
    print(f"Wrote {base.with_suffix('.json')} and .md" + (f" (stopped: {stopped})" if stopped else ""))
    return 1 if stopped == "authentication failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
