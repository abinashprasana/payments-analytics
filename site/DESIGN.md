# The Settlement Gap — editorial case-study contract

This file governs the static Next.js case study in `site/`. The repository-level `../DESIGN.md` governs the relationship between the case study and the Settlement Operations Workbench.

## Product role

The case study is an authored SQL investigation for data-analytics and BI reviewers. It answers one question: why can completed merchant purchases fail to reconcile to recorded settlement value?

It is not a tour of application views. It explains the metric contract, follows evidence through the canonical SQL model chain, reaches an operational recommendation, and then hands one payment to the workbench. The workbench owns repeatable exploration and transaction-level triage.

## Narrative order

The route has nine anchored chapters:

1. Stakeholder question and concise answer.
2. Metric contract: population, grain, currency boundary, and tolerance.
3. Relational model and synthetic-scenario disclosure.
4. Baseline daily-close SQL.
5. Segment isolation and root-cause SQL.
6. Exception classification and payment evidence.
7. Finding and operational recommendation.
8. Validation, `EXPLAIN ANALYZE` inspection target, limitations, and reproduction.
9. One workbench preview and one payment-trace deep link.

Chapter navigation follows that argument. Do not add the workbench’s four views as parallel case-study chapters.

## Evidence contract

`src/data/project-data.json` is generated from the canonical SQL marts and is typed as `CaseStudyDataV2` in `src/lib/project-data.ts`.

- Every displayed count, percentage, money value, table row, bar width, SQL excerpt, query ID, dataset version, as-of date, quality result, and build identifier must come from that payload.
- Money is represented as `{ currency, minorUnits }` and formatted only at presentation time.
- Query IDs must be registered engine IDs: `close_summary`, `segment_isolation`, `exception_queue`, and `payment_trace` where applicable.
- Scenario IDs must match `data/scenarios.json` exactly.
- Do not publish invented timings, benchmark language, parity results, or operational impact.
- Qualitative connective copy may live in the component, but it must not introduce unsupported facts or figures.
- The snapshot and all incidents must be labelled synthetic. They are never described as real customers, real incidents, real-time processing, predictive fraud, compliance, or business impact.
- Monetary findings remain within one currency. Never display a combined EUR/GBP/AUD/CAD total.

## Art direction

The page should feel like a restrained analytical dossier: editorial, evidence-led, and materially connected to SQL work.

- Visual variance: 6/10. Use asymmetry, captions, ruled ledgers, and dense evidence blocks to create character.
- Motion: 3/10. Motion exists only for focus, navigation, or state acknowledgement.
- Density: 5/10. Preserve a readable long-form rhythm while allowing result tables and SQL to feel technical.
- Keep the mineral midnight canvas, pale paper sections, copper emphasis, and sea-glass analytical signals.
- Avoid generic fintech gradients, glass panels, floating card mosaics, oversized ornamental KPIs, stock banking imagery, coins, fake browser chrome, and decorative dashboards.

The hero leads with the question and answer, not an illustration or a screenshot. The workbench preview is rendered from payload evidence; it is not a second dashboard.

## Canonical tokens

### Colour

| Token | Value | Role |
| --- | --- | --- |
| Midnight mineral | `#141C22` | Main editorial canvas |
| Primary ink | `#F1EEE8` | Headings and high-emphasis copy |
| Supporting ink | `#A3B2B8` | Secondary copy and captions |
| Paper | `#EEE9DF` | Contract and evidence sections |
| Paper ink | `#172026` | Copy on paper sections |
| Burnished copper | `#E4876D` | Identity, primary action, incident emphasis |
| Sea glass | `#79C1C7` | Analytical route and query emphasis |
| Settled | `#74CFAF` | Passing or settled state |
| Delayed | `#E0AE68` | SLA and delay state |
| Review | `#E8849A` | Disputed or failed state |

Status colour is always paired with text. All combinations must pass WCAG AA.

### Typography

- Display: locally hosted Source Serif 4 Variable.
- Reading and navigation: locally hosted IBM Plex Sans Variable.
- SQL, IDs, and compact evidence labels: locally hosted IBM Plex Mono.
- Use sentence case. Keep display copy editorial rather than slogan-like.
- Use tabular numerals for analytical values.
- No remote font or asset CDN is permitted.

### Shape and spacing

- Prefer alignment, spacing, and rules over card containers.
- Keep radii modest and reserve them for interactive controls or contained evidence.
- Maintain generous separation between arguments and tighter grouping within one query/result pair.
- Tables may scroll inside a labelled container; the page itself must never overflow horizontally.

## Components

### Metric ledger

Each public metric exposes its definition, population, grain, currency boundary, SQL model, and query ID. The displayed match tolerance is formatted from payload minor units.

### Relational diagram

Render every payload entity and relationship in semantic HTML. Merchant terms remain separate effective-dated evidence. Missing settlement rows must remain conceptually visible through the left-join explanation.

### SQL and results

Pair each query excerpt with its payload query ID and model. Keep code keyboard-scrollable. Result charts must have an adjacent table or equivalent exact labels; no charting library is necessary.

### Exception evidence

Show every true reason while explaining that primary-label precedence is only a stable queue sort. Never imply that the primary label erases secondary evidence.

### Workbench handoff

The final preview may reuse only payload evidence and journey text. The single primary action opens a deep link in the form:

`?view=trace&scenario=<scenario_id>&payment_id=<id>`

Session review actions are described as session-only and non-mutating. The free-tier wake disclosure remains visible.

## Accessibility

- Preserve one `h1`, logical heading order, semantic landmarks, and the skip link.
- Keep visible focus for all controls and links.
- Navigation and buttons have at least a 44px target.
- Diagrams expose relationships through text, not colour or position alone.
- SQL and tables are keyboard-scrollable and labelled.
- Every status includes a word, not colour alone.
- Reduced-motion mode must remove smooth scrolling and transitions without hiding information.
- The page remains fully usable at 200% zoom.

## Responsive behaviour

The required review widths are 1440, 1024, 768, and 390 CSS pixels.

- Desktop may use asymmetric query/result pairings.
- Tablet collapses before evidence labels crowd.
- Mobile uses one reading column, a horizontally scrollable chapter nav, full-width actions, and contained table/code overflow.
- No evidence, limitation, query identity, or diagram description may be hidden at narrow widths.

## Performance and static delivery

- Next.js uses `output: "export"`, `images.unoptimized: true`, `trailingSlash: true`, and the `/payments-analytics` base path.
- The build artifact is `site/out` and includes `public/.nojekyll`.
- The route stays server-rendered with authored inline behaviour only. `scripts/strip-next-runtime.mjs` removes unused hydration code; introducing a client component requires revisiting that post-processing contract.
- Runtime response headers, server actions, API routes, middleware, and other server-only features are out of scope.
- Do not add Tailwind, a UI kit, analytics, a charting library, animation dependencies, or WebGL.
- Target mobile Lighthouse performance and accessibility scores of at least 90, LCP below 2.5 seconds, and CLS below 0.1 under the repository profile.

## Review checklist

Before the case-study UI is complete:

1. Generate or verify `CaseStudyDataV2` from the canonical SQL marts; do not hand-edit it.
2. Confirm all public query IDs and scenario IDs match the engine registry and manifest.
3. Run lint, type checking, static build, local Playwright tests, and Lighthouse.
4. Inspect 1440, 1024, 768, and 390px for overflow, hierarchy, code/table containment, and navigation.
5. Check keyboard focus, heading order, skip navigation, reduced motion, text-labelled statuses, and touch targets.
6. Confirm the case study does not mirror workbench navigation and contains at most one current application screenshot.
7. Confirm there are no Vercel URLs, external asset requests, invented metrics, fabricated timing, or mixed-currency totals.
8. Verify canonical Pages URLs, the payment-trace deep link, repository links, dataset version, and commit SHA.
