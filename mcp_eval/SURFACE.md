# MCP query surface (phase 1)

This file records what a model can actually reach through the three MCP tools, read from the code on branch `mcp-eval` (dataset `settlement-gap-v3.0.0`). The golden questions in phase 2 are written against this list and nothing else.

## Sources read

`scripts/analytics_engine.py` (`QUERY_PARAMETERS`, `QUERY_REQUIRED`, `_validated_params`, `_scope`, `query`), `mcp_server/settlement_gap_mcp/server.py` (`QUERY_INFO`, `UNAVAILABLE`, the three tools, `AuditedServer.call_tool`), `mcp_server/settlement_gap_mcp/audit.py`, `mcp_server/tests/tool_manifest.json`, `docs/metric_catalog.md`, `data/scenarios.json`.

## Registered query IDs

| Query ID | Required | Optional | Served by `run_query` | In the eval |
|---|---|---|---|---|
| `scenario_options` | none | none | yes | yes |
| `close_summary` | `scenario` | `currency`, `start_date`, `end_date`, `as_of_date` | yes | yes |
| `segment_isolation` | `scenario` | `currency`, `start_date`, `end_date`, `as_of_date` | yes | yes |
| `exception_queue` | `scenario` | `currency`, `start_date`, `end_date`, `as_of_date` | yes | yes |
| `payment_trace` | `scenario`, `payment_id` | `currency`, `start_date`, `end_date`, `as_of_date` | yes | yes |
| `catalog_metrics` | none | none | yes | yes |
| `quality_results` | none | none | yes | yes |
| `exception_scoring` | none | `as_of_date` | refused (`UNAVAILABLE`) | refusal set only |
| `exception_rate_screen` | none | none | yes | excluded by decision |
| `benford_conformity` | none | none | yes | excluded by decision |

`run_query` also accepts `limit` (integer, 1 to 200, default 200).

## Parameter validation (engine)

| Parameter | Type sent over MCP | Rule |
|---|---|---|
| `scenario` | string | must be one of the four manifest IDs below |
| `currency` | string | upper cased, then must be `EUR`, `GBP`, `AUD` or `CAD` |
| `start_date`, `end_date`, `as_of_date` | string | ISO `YYYY-MM-DD`; `start_date` may not be after `end_date` |
| `payment_id` | string or integer | positive integer |
| any other key | | refused with `Unsupported parameters` |
| empty string or null value | | dropped before the required check |

`run_query` declares `params` as a map of string or integer values, so the JSON schema itself allows any key. The key allow list lives in the engine.

## Scenarios

| Scenario ID | Close date | Currency | Category | Default as-of | Signal |
|---|---|---|---|---|---|
| `normal` | 2024-09-17 | EUR | Services | 2025-01-10 | 0 exceptions, 76 payments |
| `delayed_travel_gbp` | 2024-10-10 | GBP | Travel | 2024-10-14 | 48 late, 64 payments |
| `stale_electronics_eur_fee` | 2024-11-12 | EUR | Electronics | 2025-01-10 | 48 fee mismatch, 80 payments |
| `missing_retail_cad` | 2024-12-03 | CAD | Retail | 2025-01-10 | 48 missing, 66 payments |

The `run_query` path uses the manifest `asOfDate` (2025-01-10) when `as_of_date` is omitted. `trace_payment` uses each scenario's own investigation date instead, so the delayed scenario reads as of 2024-10-14 there.

## The three tools as pinned in `tool_manifest.json`

| Tool | Arguments | Notes |
|---|---|---|
| `list_queries` | none | returns the served IDs with their parameters |
| `run_query` | `query_id` (required string), `params` (map or null), `limit` (1 to 200) | refuses unknown and unavailable IDs itself, then calls the engine |
| `trace_payment` | `payment_id` (required, greater than 0), `scenario` (string or null), `as_of_date` (string or null) | loops over scenarios, calling `payment_trace` for each; raises an error if the payment is in no scenario close |

`AuditedServer.call_tool` refuses any argument name missing from the tool's schema before the tool runs. Every call writes one audit line to the path in `SETTLEMENT_GAP_AUDIT_LOG`, so the eval can point it at a temporary file without touching server code.

## Which path reaches what

`payment_trace` is reachable two ways. `trace_payment` needs only a payment ID and finds the scenario itself. `run_query("payment_trace", ...)` needs both `scenario` and `payment_id`. For a question that names only a payment, `trace_payment` is the expected tool and `run_query` with the correct scenario is accepted as an alternative. Every other query ID is reachable only through `run_query`.

## Where the code differs from the brief

1. Benford and control limit screens are already exposed. `benford_conformity` and `exception_rate_screen` are served through `run_query` today. Only `exception_scoring` is withheld. Following your decision, the golden set leaves both out and the README will say they are served and were not evaluated.
2. There is no merchant health or category health query ID. The marts exist in SQL, but the registry does not expose them. Category questions map to `segment_isolation`. Merchant questions can only map to `exception_queue`, which lists merchant ID and name per exceptional payment.
3. Every data query covers one close. A scenario fixes both the close date and the currency, so a "per currency" question has exactly four reachable answers, and AUD has no scenario at all. `start_date` and `end_date` can only narrow that single date.
4. A conflicting filter used to return an empty result with no error. `close_summary` with `scenario=delayed_travel_gbp, currency=EUR` returned 0 rows, and so did a date range that excluded the close date, which a model could read as "nothing happened". With the owner's approval (2026-09-28) the engine now rejects both with an error that names the scenario's currency or close date. The tool schemas and `tool_manifest.json` did not change.
5. `trace_payment` covers only payments in the four scenario closes (286 payments). Any other valid payment ID is refused with a message naming the scenario closes.
6. The README example previously used payment 240. On v3 the equivalent missing CAD payment is 76330, and the README was updated in the data commit.

## Golden record schema (proposed for phase 2)

```json
{
  "id": "q001",
  "question": "Why was payment 76330 flagged?",
  "category": "payment_trace",
  "expected_tool": "trace_payment",
  "expected_query_id": null,
  "expected_params": {"payment_id": 76330},
  "alternatives": [
    {"tool": "run_query", "query_id": "payment_trace",
     "params": {"scenario": "missing_retail_cad", "payment_id": 76330}}
  ],
  "acceptable_extra": {"scenario": "missing_retail_cad"},
  "expected_answer": {"primary_reason": "missing", "days_overdue": 35},
  "expected_behavior": null,
  "why": null,
  "reviewed": false
}
```

`expected_query_id` is a string, a list for ambiguous questions (with `why` saying why each is acceptable), or null for `trace_payment` and `list_queries`. For `run_query`, `expected_params` is the `params` map. For `trace_payment`, it is the tool arguments. `expected_behavior` is set only for `currency_boundary` records, to `refuse` or `split_by_currency`.

Parameter match rule: every required key must be present with an equal value after the engine's own normalisation (currency upper cased, dates parsed as ISO, payment IDs as integers). An optional key the question does not state must be absent unless it appears in `acceptable_extra` with the same value. A value equal to the tool default counts as absent (`limit` 200, `trace_payment.scenario` null). List valued `expected_query_id` passes when the chosen ID is any member and its params match that member's entry in `alternatives`.

## Provider proposal

Groq through its OpenAI compatible endpoint. The default model is `openai/gpt-oss-120b`: `llama-3.3-70b-versatile` was no longer offered when the live runs started (2026-09-28), and gpt-oss-120b was the strongest tool calling model available to the key. `--model` selects another. Groq's free tier allows roughly 30 requests a minute and 1,000 a day (confirm in the Groq console), so the runner paces at one request every 2.1 seconds.

One question usually needs two or three model requests (tool choice, then the answer after the tool result). About 45 questions repeated 3 times is therefore around 300 to 400 requests. Confirmed on 2026-09-28: the runner defaults to `--max-requests 400`, which fits inside one day's free quota.

## Golden set (phase 2)

`mcp_eval/golden.py` holds the question wording and expected calls. `python -m mcp_eval.golden build` derives every expected answer from the snapshot and writes `golden/questions.jsonl`. `python -m mcp_eval.golden check` replays each answer source and fails on any drift. A rebuild keeps `reviewed: true` only on questions whose wording did not change. Multi call records use `expected_calls` with `expected_params` set to null.

Note for review: `trace_payment` reads the delayed scenario at 2024-10-14, while `run_query` defaults to 2025-01-10. Payment 70652 is therefore `missing` through the first path (q003) and `late` through the second unless `as_of_date` is passed (q004). Scoring compares tools and parameters, so this does not change a score, but a model's prose answer can differ by path.
