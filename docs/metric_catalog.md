# Settlement reconciliation metric catalogue

This catalogue is the public contract for Payments Analytics v2. The SQL models are authoritative; Python and Streamlit may format their result rows but must not redefine these rules.

## Population and boundaries

- **Eligible payment:** a transaction where `transaction_type = 'purchase'`, `status = 'completed'`, and `merchant_id` is present.
- **Snapshot:** wholly synthetic, versioned repository data evaluated at an explicit `as_of_date`.
- **Currency:** every monetary result is grouped or filtered by `currency`. EUR, GBP, AUD, and CAD are never added together.
- **Excluded from the flagship metric:** refunds, transfers, pending transactions, and failed transactions.

## Payment-level contracts

| Metric / flag | Definition |
| --- | --- |
| Expected fee | Eligible payment gross amount multiplied by the effective merchant term's `fee_rate_bps / 10,000`, rounded to two decimal places. |
| Expected net settlement | Gross amount minus expected fee. |
| Matched settlement | A settlement exists, its currency equals the payment currency, and `ABS(gross_amount - settled_amount - processing_fee) <= 0.01`. |
| Missing | No settlement exists and the payment is past its term-derived due date at the selected `as_of_date`. |
| Late | A recorded settlement date is after its term-derived due date. A missing settlement past due can also be an SLA breach but retains `missing` as its primary label. |
| Currency mismatch | Settlement currency differs from payment currency. |
| Amount mismatch | A settlement exists but the gross identity differs by more than 0.01 in the payment currency. |
| Fee mismatch | Recorded processing fee differs from the effective-term expected fee by more than 0.01. |
| Disputed | The linked settlement has `settlement_status = 'disputed'`. Review context is retained separately and does not create this flag. |
| Fee delta | Recorded processing fee minus the effective-term expected fee. Positive means the recorded fee is higher. |

A payment may carry more than one flag. The exception queue uses this stable primary-label precedence only for sorting and grouping:

`missing → currency mismatch → amount mismatch → fee mismatch → late → disputed`

The precedence does not suppress secondary reasons.

## Public models

| Model | Grain | Purpose |
| --- | --- | --- |
| `int_expected_settlements` | one eligible purchase | Joins each payment to its effective merchant term and derives expected fee, expected net, due date, and scenario membership. |
| `int_settlement_reconciliation` | one eligible purchase | Adds settlement evidence, money deltas, all exception flags, and the stable primary label. |
| `mart_daily_close` | transaction date × currency | Currency-specific payment count, settlement coverage, overdue value, fee delta, and exception composition. |
| `mart_exception_queue` | one exceptional payment | Operational queue with all reasons and stable priority. |
| `mart_merchant_health` | merchant × transaction date × currency | Merchant-level close and exception health without cross-currency totals. |
| `mart_payment_trace` | one eligible payment | Auditable transaction, applicable term, settlement evidence, derived values, flags, and SQL lineage fields. |
| `mart_category_health` | merchant category × transaction date × currency | Supporting authored-investigation mart for segment isolation. |
| `int_anomaly_features` | one eligible purchase | Settlement-delay, fee, and amount deltas beside each merchant's rolling prior average, so a payment can be read against its own history instead of a fixed threshold. |
| `mart_quality_screens` | close date × currency | Daily exception rate with its trailing six-day mean, standard deviation, z-score, and three-sigma upper control limit. |
| `mart_benford_conformity` | currency × leading digit | Observed first-digit frequencies against Newcomb-Benford expectations, with a chi-square statistic and mean absolute deviation for each currency. |

Staging models validate and type source columns before the intermediate models run.

## Public query IDs

`AnalyticsEngine.query(query_id, params)` accepts only registered query IDs and validated parameters; it does not expose arbitrary SQL.

| Query ID | Required parameters | Result |
| --- | --- | --- |
| `scenario_options` | none | Versioned synthetic scenarios and their investigation dates. |
| `close_summary` | `scenario`; optional `currency`, dates, `as_of_date` | Rows from the currency-specific daily-close mart. |
| `segment_isolation` | `scenario`; optional `currency`, dates, `as_of_date` | Category-level root-cause evidence for one close. |
| `exception_queue` | `scenario`; optional `currency`, dates, `as_of_date` | Sortable payment-level exceptions with all reason flags. |
| `payment_trace` | `scenario`, `payment_id`; optional `as_of_date` | One payment's transaction, term, settlement, expected-versus-recorded money, and rule lineage. |
| `catalog_metrics` | none | These metric definitions and model grains in machine-readable form. |
| `quality_results` | none | Source and mart checks with pass/fail status and observed values at the manifest as-of date. |
| `exception_scoring` | none; optional `as_of_date` | Isolation-forest anomaly score and SHAP attribution for every eligible payment. |
| `exception_rate_screen` | none | Each daily close read against its own trailing control limit. |
| `benford_conformity` | none | First-digit conformity for each payment currency. |

Dates use ISO `YYYY-MM-DD`, currencies are restricted to `EUR`, `GBP`, `AUD`, and `CAD`, and malformed parameters or unknown scenarios are rejected by the engine. A valid but absent payment ID returns an empty trace. The Streamlit navigation layer recovers from invalid or absent public deep links by returning to a valid payment or to the normal scenario and `close` view.

## Interpretation guardrails

- Scenario incidents are injected demonstrations, not observed business events.
- Anomaly scores rank how unusual a payment looks against the rest of this synthetic snapshot. They are not fraud findings, and no detection rate is claimed or measured.
- Control limits and Benford conformity are screens that narrow where to look. Neither is evidence of error or manipulation.
- Settlement exceptions are operational reconciliation signals, not fraud predictions.
- Review actions in the workbench are session-only annotations and never update the committed snapshot.
- No FX conversion, real-time feed, payment credential, personal production data, or business-impact estimate is included.
