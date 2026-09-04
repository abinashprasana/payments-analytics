# Relational schema and model notes

Payments Analytics v2 keeps the original six synthetic source entities and adds an effective-dated merchant-terms table. Source constraints protect the transactional snapshot; SQL models derive the settlement investigation without changing source rows.

## Source entities

| Entity | Grain | Important constraints |
| --- | --- | --- |
| `customers` | one synthetic customer | unique email; accepted segment and active status |
| `accounts` | one account | required customer; accepted account type, currency, and status |
| `merchants` | one merchant | accepted category and risk tier |
| `merchant_terms` | one merchant-term validity interval | required merchant; non-overlapping effective dates; non-negative fee bps; positive SLA days |
| `transactions` | one payment event | required account; positive amount; accepted type/status/currency; merchant required for purchases/refunds and absent for transfers |
| `settlements` | at most one settlement per transaction | transaction uniqueness; accepted status/currency; non-negative net amount and fee |
| `fraud_flags` | at most one review record per transaction | non-null review reason; resolved date required exactly when resolved |

Deleting a parent in a local scratch database cascades where it avoids orphans. Merchants referenced by purchase or refund history are restricted from deletion so the transaction-type nullability contract remains valid.

## Effective terms

`merchant_terms` uses `(merchant_id, valid_from)` as its business key. A transaction joins to the one row where its transaction date is on or after `valid_from` and on or before `valid_to`; an open-ended term has a null `valid_to`. Tests reject overlapping intervals and missing term coverage for eligible purchases.

The recorded settlement fee is evidence, not the fee expectation. `int_expected_settlements` computes the expected fee from the effective term so a deliberately stale fee schedule can be detected.

## Analytical flow

```text
source CSVs
  -> typed/validated staging views
  -> int_expected_settlements
  -> int_settlement_reconciliation
  -> mart_daily_close
  -> mart_exception_queue
  -> mart_merchant_health
  -> mart_payment_trace
  -> mart_category_health (authored segment-isolation support)
```

The portable model files stay inside the shared PostgreSQL/DuckDB SQL subset. Both engines execute the same statements; parity checks compare grains, exception identities, classifications, and currency-specific decimal aggregates.

See [the metric catalogue](metric_catalog.md) for the population, match identity, SLA rule, multi-flag precedence, and public query IDs.
