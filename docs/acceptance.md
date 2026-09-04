# Release acceptance checklist

Verification has two explicit phases. The local release-candidate phase may be completed without changing GitHub or either public deployment. The published-release phase begins only after the repository owner approves a push to remote `main`.

Unchecked boxes are deliberate release gates, not claims of failure. Record automated output or a reproducible manual review before checking an item; never infer public deployment success from a local build.

## Phase A — local release candidate

### Data and SQL

- [x] Generator output is byte-stable for the same seed and manifest version.
- [x] All source primary/foreign keys, accepted values, merchant-nullability, and resolved-date rules pass.
- [x] All four injected scenarios occur on their documented dates and produce their expected signal.
- [x] Every eligible purchase has exactly one expected-settlement and reconciliation row.
- [x] Effective merchant terms join once and cover every eligible purchase.
- [x] Match identity, missing, late, currency, amount, fee, and disputed flags pass focused tests.
- [x] Money remains partitioned by currency in every public mart and query.
- [x] DuckDB and PostgreSQL execute the same model files and return parity within decimal-safe tolerances.

### Case-study evidence

- [x] Every KPI, alert, result table, and SQL excerpt names its metric contract and query ID.
- [x] `CaseStudyDataV2` is generated from canonical SQL marts and has no handwritten analytical values.
- [x] Pandas and artifact scripts do not duplicate joins, aggregations, or business rules.
- [x] The case study follows one settlement investigation and does not mirror workbench navigation.
- [x] The case study contains at most one real workbench screenshot.

### Workbench journey

- [x] A reviewer can identify an unhealthy currency close, filter the exception queue, open a trace, understand its SQL rule, and export evidence in under 90 seconds.
- [x] `close`, `exceptions`, `trace`, and `catalog` deep links are stable; unknown values fall back safely.
- [x] Multi-reason tags remain visible even though a stable primary label controls queue order.
- [x] Review status, notes, resolution, and reset are clearly session-only and do not mutate source data.
- [x] Empty filters, zero denominators, invalid payment IDs, and engine failures have useful states.

### Local quality gates

- [x] Python tests, site lint, TypeScript check, static build, and generated-artifact drift checks pass.
- [x] Browser checks pass at 1440, 1024, 768, and 390px, including keyboard and reduced motion.
- [x] Lighthouse budgets and accessible table alternatives remain green.
- [x] The release-candidate commit is on local `main`; remote `main` and both public deployments remain unchanged pending owner approval.
- [x] A local annotated v2 release tag is created without deleting the prior rollback tag.

The principal reproducible checks are:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/generate_artifacts.py --check
python scripts/check_sql_parity.py

cd site
npm run lint
npm run typecheck
npm run build
npm run test:e2e
npm run test:lighthouse
```

The PostgreSQL parity command requires the local database settings documented in `.env.example`. CI runs the same parity check against an ephemeral PostgreSQL 16 service.

Recorded local verification for the v2 candidate: 52 Python tests passed; SQL parity covered 4 as-of dates, 28 model counts, 272 exception rows, 9,672 daily aggregates, 42,016 category aggregates, and 183 public-query rows; Playwright passed 17 applicable checks across the four target widths with 19 intentional project/scope skips; Lighthouse scored 98 performance and 100 accessibility with 2.10 s LCP and 0.0021 CLS.

## Phase B — owner-approved publication

- [ ] The repository owner explicitly approves pushing the verified local release commit and tags.
- [ ] The approved commit is pushed to remote `main`; Streamlit Community Cloud begins rebuilding that same revision.
- [ ] GitHub Pages publishes only after the `CI` workflow succeeds for that `main` revision.
- [ ] The read-only `Verify public deployment` workflow passes for the deployed SHA.
- [ ] GitHub Pages canonical URL and Streamlit cross-links are correct; no unrelated Vercel URL remains.
- [ ] Both public outputs show `Synthetic demo snapshot`, dataset version, as-of date, and the same commit SHA.
- [ ] Streamlit health/wake behavior and GitHub Pages are verified on free services only.
- [ ] The v2 release tag and prior rollback tag are both present on the remote.
