"""Static checks for the optional visual runtime and its fallbacks."""

from __future__ import annotations

import gzip
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
UI_SOURCE = PROJECT_DIR / "dashboard" / "ui.py"
APP_SOURCE = PROJECT_DIR / "dashboard" / "app.py"
OGL_DIR = PROJECT_DIR / "dashboard" / "static" / "vendor" / "ogl"
BRAND_DIR = PROJECT_DIR / "dashboard" / "static" / "brand"
DESIGN_FILE = PROJECT_DIR / "DESIGN.md"


class VisualRuntimeTests(unittest.TestCase):
    def test_ogl_is_bundled_locally_within_the_asset_budget(self) -> None:
        runtime = OGL_DIR / "ogl.umd.js"
        licence = OGL_DIR / "LICENSE"
        manifest = OGL_DIR / "README.md"

        self.assertTrue(runtime.is_file())
        self.assertTrue(licence.is_file())
        self.assertIn("Version: 0.0.42", manifest.read_text(encoding="utf-8"))
        self.assertIn("MIT License", licence.read_text(encoding="utf-8"))
        self.assertLess(len(gzip.compress(runtime.read_bytes())), 50_000)

    def test_reactor_keeps_the_required_failure_guards(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        for guard in (
            'new URL("app/static/vendor/ogl/ogl.umd.js", document.baseURI)',
            "webglcontextlost",
            "webglcontextrestored",
            "prefers-reduced-motion",
            "navigator.connection?.saveData",
            "stage.clientWidth >= 680",
            "IntersectionObserver",
            "reactor?.destroy(true)",
        ):
            self.assertIn(guard, source)

        self.assertNotIn("https://", source)
        self.assertNotIn("http://", source)

    def test_static_payment_rail_remains_present(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        for node in (
            'data-node="customers"',
            'data-node="accounts"',
            'data-node="transactions"',
            'data-node="merchants"',
            'data-node="settlements"',
            'data-node="flags"',
        ):
            self.assertIn(node, source)

        self.assertIn('class="reactor-fallback"', source)
        self.assertIn('aria-hidden="true"', source)


class BrandIdentityTests(unittest.TestCase):
    def test_brand_assets_are_safe_local_vectors(self) -> None:
        assets = (
            "payment-observatory-mark.svg",
            "payment-observatory-mark-compact.svg",
            "payment-observatory-mark-mono.svg",
        )
        blocked_tags = {"script", "image", "text", "foreignObject"}

        for filename in assets:
            path = BRAND_DIR / filename
            self.assertTrue(path.is_file(), filename)
            self.assertLess(path.stat().st_size, 12_000, filename)

            source = path.read_text(encoding="utf-8")
            root = ET.fromstring(source)
            self.assertEqual(root.attrib.get("viewBox"), "0 0 64 64")
            asset_body = source.replace(
                'xmlns="http://www.w3.org/2000/svg"', ""
            )
            self.assertNotIn("http://", asset_body)
            self.assertNotIn("https://", asset_body)
            self.assertNotIn("data:image", asset_body)

            for element in root.iter():
                tag = element.tag.rsplit("}", 1)[-1]
                self.assertNotIn(tag, blocked_tags)
                for name, value in element.attrib.items():
                    self.assertNotIn("href", name.lower())
                    self.assertNotIn("javascript:", value.lower())

    def test_brand_mark_replaces_the_generic_css_badge_and_favicon(self) -> None:
        ui_source = UI_SOURCE.read_text(encoding="utf-8")
        app_source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("data-brand-mark", ui_source)
        self.assertIn("payment-observatory-mark.svg", ui_source)
        self.assertIn("payment-observatory-mark-compact.svg", app_source)
        self.assertIn("page_icon=BRAND_ICON", app_source)
        self.assertNotIn("conic-gradient(from 220deg", ui_source)
        self.assertNotIn(".pay-brand-mark::after", ui_source)

    def test_brand_motion_is_one_time_and_reduced_motion_safe(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        for guard in (
            "payment-observatory-brand-seen-v1",
            'sessionStorage.setItem("payment-observatory-brand-seen-v1", "1")',
            "pay-brand-signal-pass 620ms",
            "prefers-reduced-motion: no-preference",
            "brandMark?.classList.remove",
        ):
            self.assertIn(guard, source)


class PremiumConsistencyTests(unittest.TestCase):
    def test_design_contract_and_single_stylesheet_are_present(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        self.assertTrue(DESIGN_FILE.is_file())
        design = DESIGN_FILE.read_text(encoding="utf-8")
        self.assertIn("# Payment Observatory design system", design)
        self.assertIn("The hero owns ambient motion", design)
        self.assertNotIn("PREMIUM_CSS", source)
        self.assertEqual(
            source.count("st.markdown(APP_CSS, unsafe_allow_html=True)"),
            1,
        )

    def test_scope_composer_keeps_the_filter_contract(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        for marker in (
            'class="scope-composer"',
            'aria-expanded="false"',
            'id="date-start"',
            'id="date-end"',
            'id="currency-options"',
            'id="category-options"',
            'id="compare-previous"',
            'setStateValue("filters",payload())',
            'setStateValue("filters",defaults)',
            'event.key!=="Escape"',
        ):
            self.assertIn(marker, source)

    def test_secondary_metrics_and_measure_switch_use_local_components(self) -> None:
        ui_source = UI_SOURCE.read_text(encoding="utf-8")
        app_source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn("def render_metric_strip", ui_source)
        self.assertIn("def render_measure_switch", ui_source)
        self.assertIn("payments_measure_switch", ui_source)
        self.assertIn("st.segmented_control(", ui_source)
        self.assertNotIn("st.metric(", app_source)
        self.assertNotIn("st.segmented_control(", app_source)

    def test_cinematic_trace_is_one_time_replayable_and_bounded(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        for marker in (
            'id="replay-trace"',
            'id="trace-timeline"',
            'aria-valuemax="100"',
            "payment-observatory-trace-seen-v1",
            "runSystemTrace",
            "startSystemTrace",
            'setSequenceState("complete")',
            'sessionStorage.setItem("payment-observatory-trace-seen-v1","1")',
            "pauseForVisibility",
            "activeRouteId&&token&&routePaths.has(activeRouteId)",
        ):
            self.assertIn(marker, source)

        self.assertNotIn("while (canAnimate()", source)
        self.assertNotIn("startMotion()", source)

    def test_navigation_and_scope_labels_do_not_depend_on_generated_text(self) -> None:
        source = UI_SOURCE.read_text(encoding="utf-8")

        self.assertIn("@media(max-width:1120px)", source)
        self.assertIn(">Adjust scope</span>", source)
        self.assertNotIn('.scope-toggle span::after{content:"Edit"', source)

    def test_deep_links_sticky_controls_and_case_study_crosslink(self) -> None:
        ui_source = UI_SOURCE.read_text(encoding="utf-8")
        app_source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            'VALID_VIEWS = ("overview", "merchant", "risk", "retention", "model")',
            app_source,
        )
        self.assertIn("st.query_params", app_source)
        self.assertIn('CASE_STUDY_URL = os.getenv(', app_source)
        self.assertIn("Read case study", ui_source)
        self.assertIn(".st-key-pay_sticky_controls", ui_source)
        self.assertIn("overflow-x:auto", ui_source)

    def test_complex_charts_keep_semantic_table_alternatives(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8")

        self.assertIn('with st.expander("Open review-flow data table")', source)
        self.assertIn('with st.expander("Open retention data table")', source)
        self.assertGreaterEqual(source.count("st.table("), 2)

    def test_design_contract_records_trace_palette_and_art_direction(self) -> None:
        design = DESIGN_FILE.read_text(encoding="utf-8")

        for marker in (
            "### System trace storyboard",
            "About 7.55s",
            "### Responsive behavior",
            "## Component locks",
            "## Art-direction prompt",
            "#4E72FF",
            "#68DCFF",
            "#8AF6C7",
            "#FF756F",
        ):
            self.assertIn(marker, design)


if __name__ == "__main__":
    unittest.main()
