# Payments Analytics v2 design contract

Payments Analytics v2 has two complementary surfaces with one data contract:

- **The Settlement Gap** is an authored walkthrough that explains one SQL investigation and hands the reader to the workbench.
- **Settlement Operations Workbench** is a compact product surface for daily-close triage and payment tracing.

They share metric definitions, scenario IDs, dataset metadata, query IDs, status language, and deep links. They do not repeat each other's navigation or charts.

## Design read

The audience is data analyst and BI hiring managers. The visual direction is a refinement of the existing mineral-slate identity: technically credible, calm, specific, and evidence-led. The walkthrough uses variance 7/10, motion 5/10, and density 4/10. The repeated-use workbench is denser and more conventional by design.

Motion is ambient and scroll-linked, never attention-seeking. Every effect has a defined static state under `prefers-reduced-motion`, and no effect may animate a displayed figure through values the data never held.

## Shared foundations

- Space comes from the named scale only: `--sp-1` 4px, `--sp-2` 8, `--sp-3` 12, `--sp-4` 16, `--sp-5` 24, `--sp-6` 32, `--sp-7` 48, `--sp-8` 64, `--sp-9` 96, `--sp-10` 128. `--gutter` is the single width for columns separated by a rule. Literal spacing values do not belong in component CSS.
- Type comes from the named scale only, ten steps from `--fs-50` (11px) to `--fs-800`. Nothing renders below 11px. Weights are 400, 500, 600, 700 — nothing else, and nothing above 700.
- One cool cobalt/cyan accent system identifies links and selection; mint means reconciled, amber means late or attention, and coral means mismatch or missing evidence.
- Surfaces use tinted off-black and off-white values rather than pure black or white.
- Cards exist only when they group a real unit such as a metric contract, close, queue record, or trace stage. Avoid cards nested inside cards.
- Radius comes from four tokens: `--radius-bar` 2px for chart bars, `--radius-control` 8px for buttons and inputs, `--radius-panel` 16px for cards and panels, `--radius-pill` for status tags. A single shared radius is not a system.
- Depth is expressed through surface elevation steps (`--surface-sunken` through `--surface-3`), CSS and SVG gradients, blur, and grain. Not through drop shadows on near-black, which are invisible, and not through perspective transforms on content.
- Text and icons must carry every status meaning; colour is never the sole signal.
- Local fonts and assets only. No tracking scripts, remote font CDNs, paid assets, WebGL runtime, particles, fake application screenshots, or decorative 3D charts.
- Scroll-driven CSS animation is permitted where it is wrapped in `@supports (animation-timeline: view())` and the unsupported path is the plain static layout. The universal reveal stays on the existing IntersectionObserver, because scroll-driven CSS is not yet Baseline.
- The workbench's `:root` block in `dashboard/workbench_ui.py` is a hand-synced mirror of the token block in `site/src/app/globals.css`. Drift is caught by `tests/test_ui_integrity.py::test_token_blocks_match`, not by discipline.

## Case study

- Treat the page as a long-form investigation, not a dashboard catalogue.
- Keep the stakeholder answer and primary actions in the initial viewport.
- Use readable prose measures, asymmetric evidence layouts, relational diagrams with drawn connectors, and generated result tables.
- At most one full SQL excerpt, plus one- or two-line inline excerpts where a single predicate carries the point. Deeper SQL is linked to the repository at file and line, which is stronger evidence than a truncated block because it cannot have been trimmed to fit the page.
- At most one real workbench preview may appear.
- Every displayed number, chart series, result row, SQL excerpt, query ID, scenario label, dataset version, and limitation comes from `CaseStudyDataV2`.
- Section motion is limited to purposeful opacity/transform reveal and must become static under `prefers-reduced-motion`.
- The layout collapses to one column at narrow widths without turning evidence tables into unreadable screenshots.

## Workbench

- Follow a 90-second task path: identify an unhealthy currency close, filter exceptions, open one payment, understand the SQL rule, export evidence.
- Stable views are `close`, `exceptions`, `trace`, and `catalog`.
- Keep navigation, scenario, currency, and as-of context continuously visible without consuming the page with a decorative hero.
- Use a compact HTML lifecycle diagram only where it clarifies transaction → term → settlement → exception lineage.
- Tables prioritize sticky headers, scan-friendly numeric alignment, keyboard access, explicit empty states, and native download behavior.
- Review status, notes, and resolution actions are visibly marked “session only” and never imply a source write.

## Copy and evidence

- Prefer payment, gross, expected fee, recorded fee, net settlement, due date, exception, and source snapshot.
- Never call mixed-currency totals revenue, gross spend customer lifetime value, or a random flag confirmed fraud.
- Always state “Synthetic demo snapshot,” dataset version, as-of date, runtime mode, and commit SHA.
- Never imply real-time operations, predictive fraud, compliance assurance, customer impact, or real incidents.

## Accessibility and quality bar

- WCAG AA contrast, visible focus, semantic heading order, ≥44px primary touch targets, reduced-motion support, and text/table alternatives for complex charts.
- Verify 1440, 1024, 768, and 390px widths, keyboard-only use, empty filters, invalid deep links, long exception labels, and Streamlit wake states.
- Motion must explain hierarchy, feedback, or state change. No bounce or elastic easing.
- Preserve the existing Lighthouse budgets and reserve dimensions for images to avoid layout shift.
