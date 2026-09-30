# questions results

- suite: questions
- mode: live
- provider: groq
- model: openai/gpt-oss-120b
- temperature: 0.0
- repeats: 3
- started_utc: 2026-09-30T18:07:10+00:00
- dataset: settlement-gap-v5.0.0
- git_sha: da597ef
- requests_used: 165
- tokens_used: 236024
- runs: ['2026-09-30T18:07:10+00:00']
- max_requests: 400
- trials_scored: 43
- trial_errors: 6
- stopped_early: provider daily limit reached

Scope: reviewed questions only

| Metric | Result (Wilson 95%) |
|---|---|
| tool selection | TODO (no scored items) |
| params given tool | TODO (no scored items) |
| end to end | TODO (no scored items) |
| execution | TODO (no scored items) |
| pass hat k | TODO (no scored items) |
| disagreement | TODO (no scored items) |
| currency boundary handled | TODO (no scored items) |

| Group | Metric | Result |
|---|---|---|

# questions (draft) results

- suite: questions (draft)
- mode: live
- provider: groq
- model: openai/gpt-oss-120b
- temperature: 0.0
- repeats: 3
- started_utc: 2026-09-30T18:07:10+00:00
- dataset: settlement-gap-v5.0.0
- git_sha: da597ef
- requests_used: 165
- tokens_used: 236024
- runs: ['2026-09-30T18:07:10+00:00']
- max_requests: 400
- trials_scored: 43
- trial_errors: 6
- stopped_early: provider daily limit reached

Scope: DRAFT: includes unreviewed questions

| Metric | Result (Wilson 95%) |
|---|---|
| tool selection | 80.0% (54.8 to 93.0), 12/15 |
| params given tool | 100.0% (75.8 to 100.0), 12/12 |
| end to end | 80.0% (54.8 to 93.0), 12/15 |
| execution | 100.0% (79.6 to 100.0), 15/15 |
| pass hat k | 73.3% (48.0 to 89.1), 11/15 |
| disagreement | 26.7% (10.9 to 51.9), 4/15 |
| currency boundary handled | TODO (no scored items) |

| Group | Metric | Result |
|---|---|---|
| close_kpi | end to end | 57.1% (25.1 to 84.2), 4/7 |
| close_kpi | executed ok | 100.0% (64.6 to 100.0), 7/7 |
| close_kpi | params given tool | 100.0% (51.0 to 100.0), 4/4 |
| close_kpi | tool ok | 57.1% (25.1 to 84.2), 4/7 |
| payment_trace | end to end | 100.0% (67.6 to 100.0), 8/8 |
| payment_trace | executed ok | 100.0% (67.6 to 100.0), 8/8 |
| payment_trace | params given tool | 100.0% (67.6 to 100.0), 8/8 |
| payment_trace | tool ok | 100.0% (67.6 to 100.0), 8/8 |
