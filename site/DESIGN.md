# Payment Observatory editorial design system

This file is the visual and content contract for the Next.js case study in `site/`. The page should feel like a carefully edited analytical dossier: cool, quiet, specific, and materially connected to the product. Its midnight slate is intentionally lighter than the Streamlit lab’s carbon shell and must not imitate a reference project’s warm-paper identity.

The shared product and lab rules remain in `../DESIGN.md`.

## Product role

The case study is the primary introduction for reviewers and first-time visitors. It must answer four questions in order:

1. What payment system was analysed?
2. What evidence supports the work?
3. What can the interactive lab reveal?
4. What methodological limits govern the interpretation?

It is one long-form route, not a marketing-site hierarchy. Static content remains server-rendered. Client JavaScript is reserved for chapter navigation and the SVG payment trace.

## Art direction

The editorial surface takes its character from mineral paper, observatory registration marks, annotated system diagrams, and restrained technical publishing. Variance is 7/10, motion 5/10, and density 4/10. Use asymmetry, captions, rules, and figure framing to create rhythm; do not manufacture interest with gradients, glass panels, or invented statistics.

The hero is a dossier, not a conventional split marketing hero: a wide editorial statement and compact observation brief come first, followed by the verified evidence register and a full-width observed product artifact.

Dark product screenshots are evidence figures. Give them stable dimensions, quiet borders, useful captions, and enough light space to remain legible as distinct objects.

## Canonical tokens

### Colour

| Token | Value | Use |
| --- | --- | --- |
| Midnight mineral canvas | `#141C22` | Editorial page background; lighter than the lab |
| Primary ink | `#F1EEE8` | Headings, body emphasis, structural rules |
| Supporting ink | `#A3B2B8` | Secondary copy and captions |
| Burnished copper | `#E4876D` | Identity, primary actions, and editorial emphasis |
| Sea-glass signal | `#79C1C7` | Transaction routes and analytical diagrams |
| Signal light | `#A7D5D8` | Route highlights and secondary transaction marks |
| Settled | `#74CFAF` | Completed and settled outcomes |
| Delayed | `#E0AE68` | Delayed settlement outcomes |
| Review | `#E8849A` | Disputed, unresolved, and review outcomes |
| Retention | `#B1A3DD` | Retention chapter only |

Avoid fintech-purple gradients, full-page dark theme changes, translucent glass stacks, broad glows, and colours without an analytical role. All combinations must pass WCAG AA. Status colour always appears with a written state or symbol.

### Typography

- Display: locally hosted Source Serif 4 variable.
- Reading and navigation: locally hosted IBM Plex Sans variable.
- Evidence labels and small technical annotations: locally hosted IBM Plex Mono.
- Use sentence case. Keep display lines editorial rather than slogan-like.
- Evidence labels may use uppercase sparingly; body copy should not.
- Use tabular alignment for figures and avoid decorative oversized numbers without context.

No font may be requested from a remote CDN.

### Shape, rules, and spacing

- Use midnight solid surfaces, pale graphite rules, and occasional mineral-slate offsets.
- Keep radii modest. Figures may be softly framed; text sections should not become card grids.
- Default to generous vertical separation between arguments, with tighter spacing inside a figure or evidence group.
- Use the page grid and alignment changes to create hierarchy. Extra shadows and borders are not substitutes for structure.
- Preserve explicit width and height for raster media to prevent layout shift.

## Information architecture

The page order is locked unless the narrative itself changes:

1. Hero and verified evidence strip.
2. Payment-system problem and lifecycle.
3. Customer → Account → Transaction → Merchant/Settlement/Review flow.
4. Overview.
5. Merchant flow.
6. Risk monitor.
7. Retention.
8. Data model.
9. Relational ER diagram and source continuity.
10. Methodology and limitations.
11. Project artifacts, technology, tests, repository, and final lab CTA.

The chapter navigation must expose all five analytical chapters and retain visible keyboard focus. Anchor offsets must account for sticky navigation.

## Evidence and copy

- Import numerical claims from the typed `ProjectData` payload.
- Treat `schemaVersion` as a public contract boundary.
- Keep synthetic-data boundaries, nominal-currency aggregation, and generated fraud-flag interpretation plainly visible.
- Never claim real customers, commercial activity, real-time processing, fraud prediction, currency conversion, or production risk scoring.
- Describe what each view helps a reader inspect, then show the real product view. Do not narrate a feature list around a fake mockup.
- Use payment, settlement, review, cohort, record, source, and relationship consistently across both surfaces.

## Diagrams

### Payment flow

The responsive SVG must show Customer → Account → Transaction as the event spine, then branch to Merchant, Settlement, and Review with truthful relationship language. The trace is an explanatory interaction, not ambient decoration.

- Keep all labels in accessible SVG text or equivalent HTML.
- Provide a concise description for assistive technology.
- Preserve meaning without animation.
- Reduce or remove line travel for `prefers-reduced-motion`.
- Do not add particles, canvas rendering, or a second WebGL context.

### Entity-relationship diagram

Show all six entities, keys, and cardinalities. Merchant links are nullable; a transaction may have zero or one settlement and zero or one review flag. Keep the diagram usable at narrow widths through responsive layout and description, not by shrinking text below a readable size.

### Source continuity

Present PostgreSQL and the repository CSV snapshot as two inputs to the same normalization and analytical logic. The diagram must not imply different calculations or feature coverage between sources.

## Product imagery

The approved media set is generated from the real running lab:

```text
public/media/reactor-poster.png
public/media/overview.png
public/media/merchant-flow.png
public/media/risk-monitor.png
public/media/retention.png
public/media/data-model.png
public/media/overview-mobile.png
```

Do not replace these with browser-chrome mockups, stock banking photography, generic coins, or fabricated chart images. Recapture a figure when the underlying lab view materially changes, and review its desktop and mobile crop before committing it.

## Motion and interaction

- Motion explains navigation or payment flow; it does not decorate scrolling.
- Target roughly 180–240ms for controls and 500–900ms for the deliberate SVG trace.
- Prefer opacity and transforms. Avoid layout-affecting animation.
- Do not auto-loop the SVG trace.
- The trace control must expose its state in text.
- Reduced-motion mode must remain complete and understandable.
- Touch targets are at least 44 by 44 CSS pixels.

## Responsive behavior

The page must be deliberately checked at 1440, 1024, 768, and 390 CSS pixels.

- Desktop may use editorial asymmetry and text/figure pairings.
- Tablet collapses compositions before captions or evidence labels become crowded.
- Mobile uses one reading column, horizontally usable chapter navigation, full-width figures, and no page-level horizontal overflow.
- Do not hide evidence, methodology, or diagram descriptions on small screens.
- Heading order and chapter order remain consistent across widths.

## Accessibility

- Maintain one `h1` and a logical heading hierarchy.
- Keep the skip link, visible focus, and semantic landmarks.
- Give every meaningful image useful alternative text; decorative marks use empty alternatives where appropriate.
- Pair Sankey and heatmap screenshots or discussions with the lab’s semantic table alternatives.
- Ensure diagram descriptions communicate relationships without relying on spatial position or colour.
- Verify keyboard chapter navigation, the trace control, repository links, and final lab CTA.

## Performance and delivery

- No external font or asset CDN requests.
- No analytics scripts or UI kits.
- No charting library and no WebGL library in the case study.
- Keep client components limited to navigation and SVG interaction.
- Target mobile Lighthouse performance and accessibility scores of at least 90 under the agreed profile.
- Target LCP below 2.5 seconds and CLS below 0.1.
- Keep canonical metadata, sitemap, robots metadata, favicon, Open Graph image, structured project metadata, and security headers operational.

## Component locks

- Keep the page on the midnight editorial canvas throughout; do not collapse into the lab’s near-black carbon treatment.
- Keep the existing Payment Observatory mark and name unchanged.
- Keep the verified evidence strip near the hero.
- Keep five analytical chapters and their deep links to the corresponding lab views.
- Keep one final, unambiguous “Open interactive lab” action.
- Keep real screenshots as contained figures.
- Keep the static reactor poster as the no-WebGL case-study representation.

## Do not add

- A dark marketing section that imitates the lab shell.
- Tailwind, a UI kit, an animation dependency, a charting library, or another WebGL runtime.
- Remote fonts, stock photography, generic banking icons, coins, credit-card hero art, or fake device frames.
- Fintech-purple gradients, glass-heavy cards, parallax, scroll hijacking, custom cursors, or continuous motion.
- Decorative data claims, testimonials, customer logos, or production assurances not supported by the project.

## Review checklist

Before an editorial UI change is complete:

1. Regenerate public data when appropriate and run `python scripts/export_site_data.py --check`.
2. Run lint, type checking, the production build, browser smoke tests, and the mobile Lighthouse profile.
3. Check 1440, 1024, 768, and 390px widths for overflow, crop quality, and chapter navigation.
4. Check keyboard focus, heading order, SVG descriptions, non-colour status labels, touch targets, and reduced motion.
5. Confirm all displayed figures come from `project-data.json` or are clearly qualitative.
6. Confirm screenshots show the current lab and have stable dimensions.
7. Confirm there are no external font/CDN requests, second WebGL contexts, browser errors, or cross-link regressions.
8. Compare the result with the approved desktop and mobile captures in `../outputs/screenshots/`.
