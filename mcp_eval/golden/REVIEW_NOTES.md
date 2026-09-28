# Golden set audit notes

Claude audited all 45 questions on 2026-09-28 against the v3 snapshot and the phase 1 surface. It fixed what it found and left every `reviewed` flag false. The owner sets `reviewed: true` in `questions.jsonl` for each question they accept. A rebuild keeps a flag only while the wording is unchanged.

## Changed during the audit

| ID | Change | Reason |
|---|---|---|
| q022 | `currency` moved from required to acceptable | The scenario already fixes GBP, so leaving the filter out is equally correct. |
| q042 | Reason text now allows adding the two EUR closes | A partial EUR subtotal is legitimate; only GBP and CAD must stay apart. |
| q045 | Removed "Both are EUR." from the question | The hint gave the answer away; the model should discover the shared currency. |

## Changed after the first live smoke run (2026-09-28)

| ID | Change | Reason |
|---|---|---|
| q011 | `exception_queue` accepted as an alternative to `close_summary` | q038 asks the same thing and already accepted both; the two records disagreed. Found when gpt-oss-120b answered q011 from the queue. |

## Changed with dataset v5 (2026-09-28)

Every payment and merchant ID moved to a real v5 row: 560942 and 561108 (lost CAD file), 536062 and 535555 (stale fee), 499930 and 500225 (partner outage), 476513 (clean payment on the normal close), merchant 391 in r005. Each was picked from the incident itself, not from the everyday exceptions that now appear on every close: the missing and late payments share a merchant with another hit on the same close, and the fee payments record exactly the old 40 bps rate. q025 and q027 now rank categories by the incident's reason (`late_count`, `fee_mismatch_count`) instead of by all exceptions, because every close now carries an everyday mix and a total would mix the two. q010 and q024 now expect the normal close's 23 everyday exceptions. All expected answers were re-derived from the snapshot.

## Changed with dataset v4 (2026-09-28)

Every payment and merchant ID moved to a real v4 row: 238833 and 238837 (lost CAD file), 231728 and 231729 (stale fee), 221416 and 221423 (partner outage), 214760 (clean payment on the normal close), merchant 243 in r005. Questions that named a scenario by one category now name it by its cause (for example "the CAD lost-file close"), because each incident now spans several categories. q010 and q024 now expect one exception on the normal close: a background currency mismatch, which the control is allowed to have. All expected answers were re-derived from the snapshot.

## Worth a second look before flagging

| ID | Point |
|---|---|
| q003, q004 | Same payment, different paths. `trace_payment` defaults to 2024-10-14 (missing, 1 day); `run_query` defaults to 2025-01-10 (late, 3 days). Both records are correct for their stated tool. |
| q007 | "Current terms" means the term in force on the payment date, which is the post change 110 bps term. |
| q009 | Payment 12 is real but outside every scenario close. The correct outcome is a `trace_payment` call that returns the not found error, reported plainly. |
| q016 | The model must map 2024-09-17 to the `normal` scenario on its own (via `scenario_options` or reasoning). |
| q030, q033 | A model may answer from general knowledge without a tool call. That scores as a tool miss, which is intended. |
| q043 | Refusal expected. Fetching the CAD amount first and then declining the conversion also passes. |

All other questions were checked for wording, expected call, and derived answer, with no issue found.
