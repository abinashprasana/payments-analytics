"""Re-score a live run from its saved transcripts, without calling the model again.

Use it when the scorer changes after a run (for example a bug fix). The model's
calls and answers are read from the raw transcripts the run saved, scored with
the current scoring code, and the results file is rewritten in place.

    python -m mcp_eval.rescore mcp_eval/results/refusal_<model>_<date>.json \
        mcp_eval/results/raw/refusal_<stamp>.jsonl [more transcript files]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcp_eval import golden, metrics, refusals, scoring


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results", type=Path)
    parser.add_argument("transcripts", type=Path, nargs="+")
    args = parser.parse_args(argv)

    output = json.loads(args.results.read_text(encoding="utf-8"))
    meta = output["meta"]
    suite = meta["suite"]
    if suite.startswith("freeform_"):
        return _rescore_freeform(args, output)
    records = golden.load() if suite == "questions" else refusals.load(refusals.REFUSALS_PATH)
    by_id = {record["id"]: record for record in records}
    score = scoring.score_question if suite == "questions" else scoring.score_refusal

    wanted = {(t["id"], t["repeat"]) for t in output["trials"]}
    trials = {}
    for path in args.transcripts:
        for line in path.read_text(encoding="utf-8").splitlines():
            trial = json.loads(line)
            key = (trial["id"], trial["repeat"])
            if key in wanted:
                trials[key] = trial
    missing = wanted - set(trials)
    if missing:
        parser.error(f"no transcript for {sorted(missing)}")

    scored = []
    for key in sorted(wanted, key=lambda k: (k[0], k[1])):
        result = score(by_id[key[0]], trials[key])
        result["signature"] = json.dumps(result["signature"], default=str)
        scored.append({"id": key[0], "repeat": key[1], **result})

    summarize = metrics.summarize_questions if suite == "questions" else metrics.summarize_refusals
    meta["rescored"] = True
    output.update(
        reviewed=summarize(scored, records, reviewed_only=True),
        draft=summarize(scored, records, reviewed_only=False),
        trials=scored,
    )
    args.results.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    args.results.with_suffix(".md").write_text(
        metrics.render_markdown(output["reviewed"], meta) + "\n"
        + metrics.render_markdown(output["draft"], {**meta, "suite": f"{suite} (draft)"}),
        encoding="utf-8",
    )
    print(f"Re-scored {len(scored)} trials into {args.results}")
    return 0


def _rescore_freeform(args: argparse.Namespace, output: dict) -> int:
    """Free-form runs keep each query's SQL, so the safety flags are recomputed
    from it. Execution and answer matching depend on the run itself and are kept."""
    from mcp_eval import freeform_sql

    suite = output["meta"]["suite"].removeprefix("freeform_")
    records = golden.load() if suite == "questions" else refusals.load(refusals.REFUSALS_PATH)
    scored = []
    for path in args.transcripts:
        for line in path.read_text(encoding="utf-8").splitlines():
            trial = json.loads(line)
            flags = freeform_sql.safety_flags(trial["sql"])
            scored.append({**trial, "flags": flags, "unsafe": bool(set(flags) - {"unparsed"})})
    output["meta"]["rescored"] = True
    output.update(
        reviewed=freeform_sql.summarize(scored, records, reviewed_only=True),
        draft=freeform_sql.summarize(scored, records, reviewed_only=False),
    )
    args.results.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Re-scored {len(scored)} free-form trials into {args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
