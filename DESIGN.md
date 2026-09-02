# Payment Observatory design system

This file is the shared visual contract and the detailed contract for the interactive lab. The product has two deliberately different dark surfaces: a midnight-slate editorial case study for orientation and evidence, and a deeper carbon operational lab for exploration. They share a name, mark, factual language, data contract, and semantic outcomes without pretending to be one continuous application screen.

The editorial rules live in `site/DESIGN.md`. Changes should extend the appropriate surface rather than blend their palettes or introduce a third style language.

## Two-surface model

| Property | Editorial case study | Interactive lab |
| --- | --- | --- |
| Primary task | Explain the system and establish evidence | Explore and compare the analytical views |
| Canvas | Midnight mineral slate, `#141C22` | Carbon black, `#050607` |
| Density | 4/10 | 7/10 |
| Motion | 5/10, limited to navigation and SVG trace | 4/10 after the hero |
| Depth | Contained real screenshots and flat diagrams | One 2.5D transaction reactor |
| Primary URL role | Portfolio and review entry point | Secondary interactive lab |

### Cross-surface locks

- Keep the Payment Observatory name, logo, entity names, relationship meanings, dataset window, and public numerical claims consistent.
- Generate public claims from `site/src/data/project-data.json`; do not transcribe or round new claims by hand.
- Keep outcome meaning stable even when the editorial and operational palettes use different shades: settled is green, delayed is amber, review is coral, and retention is violet.
- Pair every status colour with text, an icon, or both. Colour cannot be the only carrier of meaning.
- Keep both cross-links visible: “Open interactive lab” in the case study and “Read case study” in the lab.
- The case study may show the reactor only as a static real capture. The single live WebGL context belongs to the lab.
- Both surfaces use locally hosted fonts and assets. No font CDN, analytics script, or second WebGL runtime is permitted.

## Product character

Payment Observatory is an operational payments interface. It should feel precise, calm and technically credible. The observatory metaphor appears through measured routes, instrument labels, narrow edge light and controlled depth. It should never become a science-fiction illustration.

The hero, payment lifecycle rail, transaction reactor and payment orrery logo are stable product anchors. Changes elsewhere should not rebuild or restyle them unless the task specifically targets one of those areas.

## Canonical tokens

### Colour

| Token | Value | Use |
| --- | --- | --- |
| Canvas | `#050607` | Page background |
| Canvas soft | `#080A0D` | Background variation |
| Surface | `#0C0F13` | Standard panels |
| Raised surface | `#11151B` | Inputs and elevated controls |
| Ink | `#F1F3EF` | Primary text |
| Muted | `#8D99A5` | Supporting text |
| Cobalt | `#4E72FF` | Primary action and inbound signal |
| Cyan | `#68DCFF` | Transaction and general information |
| Mint | `#8AF6C7` | Completed and settled outcomes |
| Amber | `#F5BB62` | Delay and nominal value |
| Coral | `#FF756F` | Review and unresolved outcomes |
| Violet | `#A58CFF` | Cohort analysis only |

Use thin translucent borders rather than bright outlines. Broad neon glows, rainbow gradients and unrelated accent colours do not belong in the product.

### Type

- Display: locally hosted Space Grotesk, weights 480–560.
- Interface: Streamlit's bundled Source Sans, with Segoe UI as fallback.
- Technical labels: Source Code Pro or a local monospace fallback.
- Headings use sentence case and no terminal punctuation.
- Numerical readouts use tabular-looking spacing and short factual labels.

### Shape and spacing

- Spacing follows an 8px base rhythm, with 5–6px used only inside compact controls.
- Small radius: 8–10px.
- Panel radius: 13–18px.
- Hero radius: 26px.
- Use one main border and one stronger focus border. Do not invent local border colours.
- Prefer negative space to extra dividers.

### Depth

- Standard cards use a dark matte surface and a narrow top or side light.
- Large analytical panels may use a soft shadow for separation.
- Only interactive diagrams and primary KPI cards may move in depth.
- Glass blur is limited to the application shell. Data cards remain opaque enough to read quickly.

### Motion

| Token | Duration | Use |
| --- | --- | --- |
| Snap | 120ms | Press and focus feedback |
| UI | 190–220ms | Control and selection changes |
| Reveal | 460–520ms | One-time section entrances |
| Route | 850–950ms | One measured connection between lifecycle stages |
| System trace | About 7.55s | One complete customer-to-outcome sequence |

The hero owns ambient motion. Everything below it moves only when revealed, focused, selected or updated. The complete system trace plays once per browser session and can be replayed from the hero. Reduced motion removes route travel, tilt, counting and large transforms while keeping state changes clear.

### System trace storyboard

1. The calibration frame and perspective grid resolve.
2. One signal follows Customers to Accounts and then enters Transactions.
3. The transaction reactor compresses briefly while the ledger identifies the event spine.
4. The signal visits Merchants, Settlements and Fraud flags in sequence. Each route uses its established colour and factual relationship text.
5. The progress instrument completes and the hero returns to its quiet idle state.

The desktop sequence lasts about 7.55 seconds. Mobile uses the same order as a vertical focus sequence without WebGL or route travel. Reduced-motion and data-saving modes use the shorter focus sequence. Leaving the hero or hiding the browser pauses the sequence; returning does not restart it automatically.

### Responsive behavior

- At 960px and above, the lifecycle uses the full observatory plane and reactor.
- Between 680px and 959px, the same three-column structure remains, with reduced reactor detail and no pointer tilt.
- Below 680px, the lifecycle becomes a vertical transaction trace. Relationship text stays outside the route area.
- The five-view navigation begins horizontal overflow handling at 1120px, before labels can collide.

## Component rules

### Product shell

Keep the payment orrery, product name, observed window, entity count and source state legible at every width. Do not repeat the logo inside charts or cards.

### Navigation

The five analytical views use one numbered rail. The selected view has a restrained cobalt-to-cyan signal; inactive views remain quiet. Horizontal scrolling is acceptable on narrow screens.

### Operational scope

The default state is a compact summary of the applied date, currencies, categories and comparison mode. Editing expands inline. Applying or resetting is explicit; changing a draft control must not silently alter the analysis.

### Metrics

The Overview uses the asymmetric KPI bento. Merchant, risk and retention views use the shallower metric strip. Metric colour signals meaning, not decoration.

### Charts and records

Charts stay two-dimensional. Direct labels, stable category colours and honest units take priority over visual effects. Detailed records remain available through accessible expanders and tables.

### Empty and failure states

Explain what the current scope removed and provide a clear reset path. A failed optional component must reveal the native Streamlit fallback without blocking data or charts.

## Copy rules

- Use operational language: payment, settlement, review, cohort, record and source.
- State synthetic-data and mixed-currency limitations accurately, but keep them inside concise methodology or data notes.
- Do not claim real-time, predictive or converted values.
- Avoid student, portfolio, demonstration, CV or recruitment language.
- Keep headings short and natural. Avoid marketing filler and inflated claims.

## Do not add

- Additional WebGL canvases, particles, 3D charts or decorative models.
- Remote fonts, CDNs, analytics scripts or paid visual services.
- Custom cursors, scroll hijacking or continuous card motion.
- A second component library or a parallel colour and spacing system.
- Raw visual experiments in stable product areas without a screenshot comparison.

## Component locks

- Keep the payment orrery logo, product name and hero copy unchanged unless product positioning changes.
- Keep one OGL context behind Transactions. A graphical failure must leave the HTML nodes, SVG routes and relationship ledger intact.
- Keep colour meaning stable: cobalt for inbound flow, cyan for the transaction spine, mint for settlement, coral for review and violet for retention.
- Keep charts and tables two-dimensional. Depth belongs to the hero, KPI cards and interactive relationship maps.

## Art-direction prompt

> Design a production payments observatory on a carbon-black canvas. Centre the experience on one measured 2.5D transaction reactor connected to customer, account, merchant, settlement and review records. Use narrow cobalt and cyan signal routes, mint settlement light and coral review light. Surfaces are matte graphite with crisp hairlines, restrained depth and precise technical labels. Motion follows the payment lifecycle once, then becomes quiet. Charts remain flat, readable and evidence-led. Avoid particles, glass-heavy cards, 3D charts, marketing claims and generic neon decoration.

## Review checklist

Before a UI change is complete:

1. Run the analytical and UI-integrity tests.
2. Check 1440, 1024, 768 and 390px widths.
3. Test keyboard focus, Escape behaviour and reduced motion.
4. Compare screenshots with the last approved desktop and mobile captures.
5. Confirm there are no new external requests, browser errors or data changes.
