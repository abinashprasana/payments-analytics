"""Static and AppTest checks for the Settlement Operations Workbench UI."""

from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

from streamlit.testing.v1 import AppTest


PROJECT_DIR = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_DIR / "dashboard" / "app.py"
UI_PATH = PROJECT_DIR / "dashboard" / "workbench_ui.py"
BRAND_DIR = PROJECT_DIR / "dashboard" / "static" / "brand"


def new_app(**query_params: str) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=120)
    app.query_params.update(query_params)
    return app.run(timeout=120)


def by_label(elements: Any, label: str) -> Any:
    return next(element for element in elements if element.label == label)


class WorkbenchStaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app_source = APP_PATH.read_text(encoding="utf-8")
        cls.ui_source = UI_PATH.read_text(encoding="utf-8")

    def test_only_the_four_task_oriented_views_are_exposed(self) -> None:
        for view in ("close", "exceptions", "trace", "catalog"):
            self.assertIn(f'"{view}"', self.ui_source)
        for legacy in ('"overview"', '"risk"', '"retention"', '"model"'):
            self.assertNotIn(legacy, self.app_source)
            self.assertNotIn(legacy, self.ui_source)

    def test_application_has_no_pandas_business_logic_or_arbitrary_sql(self) -> None:
        for blocked in (
            ".merge(",
            "pd.merge(",
            ".groupby(",
            ".pivot(",
            ".pivot_table(",
            ".agg(",
            "SELECT *",
            "read_sql",
        ):
            self.assertNotIn(blocked, self.app_source)
            self.assertNotIn(blocked, self.ui_source)
        self.assertIn('run_query(engine, "close_summary"', self.app_source)
        self.assertIn('run_query(engine, "exception_queue"', self.app_source)
        self.assertGreaterEqual(self.app_source.count('"payment_trace"'), 3)

    def test_deep_link_session_and_export_contracts_are_visible(self) -> None:
        for marker in (
            "st.query_params",
            '{"view", "scenario", "payment_id"}',
            '"Session review status"',
            '"Session note"',
            '"Save session note"',
            '"Reset session-only reviews"',
            '"Export filtered evidence"',
            'mime="text/csv"',
            "update the repository snapshot or simulate a real payment operation",
        ):
            self.assertIn(marker, self.app_source)

    def test_compact_lifecycle_replaces_the_decorative_reactor(self) -> None:
        for step in (
            "Identify close",
            "Filter exceptions",
            "Trace payment",
            "Export evidence",
        ):
            self.assertIn(step, self.ui_source)
        combined = (self.app_source + self.ui_source).lower()
        self.assertNotIn("reactor", combined)
        self.assertNotIn("webgl", combined)
        self.assertNotIn("ogl", combined)

    def test_accessibility_and_responsive_guards_remain(self) -> None:
        for marker in (
            ":focus-visible",
            "min-height: 44px",
            "@media (max-width: 720px)",
            "prefers-reduced-motion: reduce",
            'aria-label="Snapshot metadata"',
            'aria-label="Investigation workflow"',
        ):
            self.assertIn(marker, self.ui_source)

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
            source = path.read_text(encoding="utf-8")
            root = ET.fromstring(source)
            self.assertEqual(root.attrib.get("viewBox"), "0 0 64 64")
            for element in root.iter():
                self.assertNotIn(element.tag.rsplit("}", 1)[-1], blocked_tags)
                for name, value in element.attrib.items():
                    self.assertNotIn("href", name.lower())
                    self.assertNotIn("javascript:", value.lower())


class WorkbenchAppTests(unittest.TestCase):
    def assert_clean_run(self, app: AppTest) -> None:
        self.assertEqual([str(item.value) for item in app.exception], [])
        self.assertEqual([item.value for item in app.error], [])

    def test_unknown_deep_link_falls_back_to_close_and_normal(self) -> None:
        app = new_app(view="unknown", scenario="not-a-scenario", payment_id="bad")
        self.assert_clean_run(app)
        self.assertEqual(app.radio[0].value, "close")
        self.assertEqual(app.query_params["view"], ["close"])
        self.assertEqual(app.query_params["scenario"], ["normal"])
        self.assertNotIn("payment_id", app.query_params)
        scenario = by_label(app.selectbox, "Synthetic scenario")
        self.assertEqual(scenario.value, "normal")

    def test_all_four_views_render_from_stable_deep_links(self) -> None:
        expected_headings = {
            "close": "Close health by currency",
            "exceptions": "Exception queue",
            "trace": "Payment trace",
            "catalog": "Metric and model catalog",
        }
        for view, heading in expected_headings.items():
            scenario = "normal" if view in {"close", "catalog"} else "delayed_travel_gbp"
            with self.subTest(view=view):
                app = new_app(view=view, scenario=scenario)
                self.assert_clean_run(app)
                self.assertEqual(app.radio[0].value, view)
                markdown = "\n".join(str(item.value) for item in app.markdown)
                self.assertIn(heading, markdown)

    def test_scenario_selector_updates_the_deep_link(self) -> None:
        app = new_app(view="close", scenario="normal")
        by_label(app.selectbox, "Synthetic scenario").select(
            "delayed_travel_gbp"
        ).run(timeout=120)
        self.assert_clean_run(app)
        self.assertEqual(app.query_params["scenario"], ["delayed_travel_gbp"])
        self.assertEqual(by_label(app.selectbox, "Currency").value, "GBP")
        self.assertEqual(by_label(app.date_input, "As-of date").value, date(2024, 10, 11))

        app.query_params["scenario"] = "missing_retail_cad"
        app.run(timeout=120)
        self.assert_clean_run(app)
        self.assertEqual(
            by_label(app.selectbox, "Synthetic scenario").value,
            "missing_retail_cad",
        )
        self.assertEqual(by_label(app.selectbox, "Currency").value, "CAD")

    def test_exception_filter_empty_state_and_csv_export(self) -> None:
        app = new_app(view="exceptions", scenario="delayed_travel_gbp")
        self.assert_clean_run(app)
        downloads = app.get("download_button")
        export = next(
            item for item in downloads if item.proto.label == "Export filtered evidence"
        )
        self.assertTrue(export.proto.url.endswith(".csv"))

        by_label(app.text_input, "Merchant or payment").input(
            "__no_matching_payment__"
        ).run(timeout=120)
        self.assert_clean_run(app)
        self.assertIn(
            "No queue rows match the display filters. Clear them to continue.",
            [item.value for item in app.info],
        )

    def test_invalid_trace_payment_falls_back_to_a_valid_payment(self) -> None:
        app = new_app(
            view="trace",
            scenario="delayed_travel_gbp",
            payment_id="not-an-id",
        )
        self.assert_clean_run(app)
        payment_id = app.query_params["payment_id"][0]
        self.assertTrue(payment_id.isdigit())
        self.assertIn(
            f"Payment `not-an-id` is not valid in this scenario. Showing `{payment_id}` instead.",
            [item.value for item in app.warning],
        )

    def test_review_notes_and_resolution_status_are_session_only_and_resettable(self) -> None:
        app = new_app(view="trace", scenario="delayed_travel_gbp")
        self.assert_clean_run(app)
        payment_id = app.query_params["payment_id"][0]

        by_label(app.selectbox, "Session review status").select("Investigating")
        by_label(app.text_area, "Session note").input("Checked settlement evidence")
        by_label(app.button, "Save session note").click().run(timeout=120)
        self.assert_clean_run(app)
        self.assertEqual(
            app.session_state["settlement_review_state"][payment_id],
            {
                "status": "Investigating",
                "notes": "Checked settlement evidence",
            },
        )
        self.assertIn("Saved for this session only.", [item.value for item in app.success])

        by_label(app.button, "Reset session-only reviews").click().run(timeout=120)
        self.assert_clean_run(app)
        self.assertEqual(app.session_state["settlement_review_state"], {})
        self.assertIn(
            "Session review state cleared.", [item.value for item in app.success]
        )

    def test_catalog_discloses_snapshot_build_runtime_and_hibernation(self) -> None:
        app = new_app(view="catalog", scenario="normal")
        self.assert_clean_run(app)
        page_text = "\n".join(
            str(item.value)
            for collection in (app.markdown, app.info, app.caption)
            for item in collection
        )
        for marker in (
            "Synthetic demo snapshot",
            "Streamlit Community Cloud may ask you to wake",
        ):
            self.assertIn(marker, page_text)
        build_table = app.dataframe[0].value
        self.assertEqual(
            build_table["Field"].tolist(),
            [
                "Dataset version",
                "As-of date",
                "Commit SHA",
                "Runtime mode",
                "Snapshot",
            ],
        )


if __name__ == "__main__":
    unittest.main()
