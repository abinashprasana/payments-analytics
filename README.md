# The Settlement Gap

Payments Analytics v2 is one executable SQL investigation and one operational companion tool, built on a wholly synthetic payments snapshot.

1. **Case study release URL:** [The Settlement Gap](https://abinashprasana.github.io/payments-analytics/)
2. **Workbench release URL:** [Settlement Operations Workbench](https://abinashprasana-payments-analytics-dashboardapp-mrsz1m.streamlit.app/?view=close&scenario=normal)
3. **Inspect the SQL:** [`sql/models`](sql/models) and the [metric catalogue](docs/metric_catalog.md)
4. **Reproduce it:** `python scripts/generate_artifacts.py --check`

> **Synthetic demo snapshot.** No rows describe real customers, merchants, incidents, payment credentials, or business impact. Monetary results are always separated by EUR, GBP, AUD, or CAD; no FX conversion is implied. The free Streamlit deployment may take a moment to wake after inactivity.

> **Deployment status.** Moving a local branch—including local `main`—does not update either URL. The existing public versions remain untouched until the repository owner explicitly approves and pushes a release commit to remote `main`; GitHub Pages then publishes only after CI succeeds.

## The question

Why can completed merchant purchases fail to reconcile to recorded settlement value?

The repository answers that question through four documented scenarios: a normal daily close, a delayed Travel/GBP batch, a stale Electronics/EUR fee schedule, and a missing Retail/CAD batch. Each scenario is injected deterministically and recorded in [`data/scenarios.json`](data/scenarios.json); none is presented as a real incident.

## What runs where

| Surface | Role | Runtime |
| --- | --- | --- |
| Case study | Authored investigation with generated SQL evidence | Static Next.js export on GitHub Pages |
| Workbench | Daily-close triage, exception filtering, payment trace, and CSV evidence export | Streamlit Community Cloud + cached in-memory DuckDB |
| Compatibility test | Proves the same model chain runs without result drift | Ephemeral PostgreSQL in GitHub Actions |
| Power BI v1 | Historical appendix only | [`archive/power-bi-v1`](archive/power-bi-v1/README.md) |

The release contract requires both public surfaces to show the dataset version, as-of date, synthetic-data label, and the same build SHA. All services used for the public project have a free tier; no hosted database is required.

## SQL is the analytical core

The flagship population contains completed merchant purchases only. Refunds and transfers are deliberately outside the settlement KPI. A match requires:

- a settlement record;
- the same payment and settlement currency; and
- `ABS(gross - settled_amount - processing_fee) <= 0.01`.

Effective-dated merchant terms define the expected fee and settlement SLA. One payment can carry several exception flags—missing, late, currency mismatch, amount mismatch, fee mismatch, and disputed—while the queue uses a stable precedence only for its primary label.

```text
typed staging models
  -> int_expected_settlements
  -> int_settlement_reconciliation
     |-> mart_daily_close
     |-> mart_exception_queue
     |-> mart_merchant_health
     |-> mart_payment_trace
     `-> mart_category_health (supporting segment-isolation evidence)
```

Streamlit and Plotly only format returned rows. Joins, grains, monetary identities, flags, and KPI definitions live in the portable PostgreSQL/DuckDB SQL chain. The internal `AnalyticsEngine.query(query_id, params)` registry validates query IDs and parameters; it does not provide a public arbitrary-SQL editor.

## Repository map

| Path | Purpose |
| --- | --- |
| [`data/generate_data.py`](data/generate_data.py) | Repeatable synthetic snapshot and scenario injection |
| [`data/scenarios.json`](data/scenarios.json) | Versioned scenario dates, scope, and expected signals |
| [`schema`](schema) | PostgreSQL source schema and indexes |
| [`sql/models`](sql/models) | Portable staging, intermediate, and mart definitions |
| [`scripts/analytics_engine.py`](scripts/analytics_engine.py) | Strict query registry and in-memory DuckDB runtime |
| [`dashboard/app.py`](dashboard/app.py) | Four-view Settlement Operations Workbench |
| [`site`](site) | Static authored case study |
| [`tests`](tests) | Generator, SQL, parity, engine, UI, and payload contracts |
| [`docs/metric_catalog.md`](docs/metric_catalog.md) | Population, metric definitions, grains, and query IDs |
| [`docs/deployment.md`](docs/deployment.md) | Free hosting, verification, release, and rollback |

## Run locally

Prerequisites: Python 3.12 and Node.js 24. PostgreSQL 15+ is optional unless you are running parity checks.

```bash
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements-dev.txt
python scripts/generate_artifacts.py --check
streamlit run dashboard/app.py
```

Run the full Python suite:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

With local PostgreSQL credentials configured, run the cross-engine parity check:

```bash
python scripts/check_sql_parity.py
```

Build the static case study:

```bash
cd site
npm ci
npm run lint
npm run typecheck
npm run build
```

To load the production-shaped PostgreSQL runtime, copy `.env.example` to `.env`, create the database from [`schema/create_tables.sql`](schema/create_tables.sql), and run `python scripts/load_data.py`. The loader validates the snapshot and commits all seven source tables atomically.

See the [release acceptance checklist](docs/acceptance.md) before any push. Publication is intentionally a separate, owner-approved step; the post-deployment workflow is read-only and verifies the two free public surfaces after Pages finishes.

## Guardrails

- Synthetic scenarios demonstrate reconciliation techniques; they do not establish causal business findings.
- Exception flags are operational evidence, not fraud predictions or compliance decisions.
- Workbench notes and review status exist only in the browser session and never mutate the source snapshot.
- Public money is represented with an explicit currency; the case-study payload serializes it as `{ currency, minorUnits }`.
- The v1 Power BI report is archived because its independently defined DAX and mixed-currency measures do not satisfy the v2 metric contract.

## Author

Abinash Prasana Selvanathan
