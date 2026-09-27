# Golden set audit notes

Claude audited all 45 questions on 2026-09-28 against the v3 snapshot and the phase 1 surface. It fixed what it found and left every `reviewed` flag false. The owner sets `reviewed: true` in `questions.jsonl` for each question they accept. A rebuild keeps a flag only while the wording is unchanged.

## Changed during the audit

| ID | Change | Reason |
|---|---|---|
| q022 | `currency` moved from required to acceptable | The scenario already fixes GBP, so leaving the filter out is equally correct. |
| q042 | Reason text now allows adding the two EUR closes | A partial EUR subtotal is legitimate; only GBP and CAD must stay apart. |
| q045 | Removed "Both are EUR." from the question | The hint gave the answer away; the model should discover the shared currency. |

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
