"""Regression tests for the SQL-backed Settlement Operations Workbench."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd

from dashboard.workbench_ui import (
    PRIMARY_REASON_ORDER,
    default_scenario,
    display_frame,
    format_minor_units,
    format_percent,
    normalise_reasons,
    reason_tags,
    scenario_options,
    trace_money_table,
)
from scripts.analytics_engine import AnalyticsEngine


PROJECT_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_DIR / "data" / "scenarios.json"


class WorkbenchPresentationTests(unittest.TestCase):
    def test_money_uses_integer_minor_units_and_keeps_currency(self) -> None:
        self.assertEqual(format_minor_units(12_345, "GBP"), "GBP 123.45")
        self.assertEqual(format_minor_units(-105, "EUR"), "EUR -1.05")
        self.assertEqual(format_percent("0.925"), "92.5%")

    def test_trace_money_never_relabels_recorded_currency(self) -> None:
        result = trace_money_table(
            {
                "transaction_currency": "EUR",
                "settlement_currency": "GBP",
                "expected_gross_minor_units": 10_000,
                "recorded_gross_minor_units": 9_800,
                "expected_fee_minor_units": 200,
                "recorded_fee_minor_units": 200,
                "expected_settled_minor_units": 9_800,
                "recorded_settled_minor_units": 9_600,
            }
        )
        self.assertTrue(result["Expected"].str.startswith("EUR ").all())
        self.assertTrue(result["Recorded"].str.startswith("GBP ").all())

    def test_reason_tags_keep_sql_precedence_and_deduplicate(self) -> None:
        reasons = normalise_reasons(
            "disputed,late,missing,fee_mismatch,late,currency_mismatch"
        )
        self.assertEqual(
            reasons,
            [
                "missing",
                "currency_mismatch",
                "fee_mismatch",
                "late",
                "disputed",
            ],
        )
        tags = reason_tags(reasons)
        self.assertLess(tags.index("Missing settlement"), tags.index("Late settlement"))

    def test_reason_fallback_reads_independent_sql_flags(self) -> None:
        row = {
            "is_late": True,
            "is_missing": False,
            "is_amount_mismatch": True,
        }
        self.assertEqual(
            normalise_reasons(None, row),
            ["amount_mismatch", "late"],
        )

    def test_scenario_registry_has_a_stable_normal_default(self) -> None:
        frame = pd.DataFrame(
            [
                {"scenario_id": "incident", "name": "Incident"},
                {
                    "scenario_id": "normal",
                    "name": "Normal daily close",
                    "is_default": True,
                    "close_date": "2024-09-17",
                    "as_of_date": "2025-01-10",
                    "default_currency": "EUR",
                },
            ]
        )
        options = scenario_options(frame)
        self.assertEqual(default_scenario(options), "normal")
        normal = next(option for option in options if option.scenario_id == "normal")
        self.assertEqual(normal.default_currency, "EUR")
        self.assertEqual(normal.close_date.isoformat(), "2024-09-17")

    def test_display_frame_does_not_invent_analytical_columns(self) -> None:
        frame = pd.DataFrame({"payment_id": [1], "currency": ["CAD"]})
        result = display_frame(frame, ("payment_id", "gross", "currency"))
        self.assertEqual(result.columns.tolist(), ["payment_id", "currency"])


class AnalyticsEngineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.engine = AnalyticsEngine(repo_root=PROJECT_DIR, build_sha="test-build")
        cls.scenarios = {
            item["scenarioId"]: item for item in cls.manifest["scenarios"]
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.close()

    def scenario_params(self, scenario_id: str, **extra: object) -> dict[str, object]:
        scenario = self.scenarios[scenario_id]
        return {
            "scenario": scenario_id,
            "currency": scenario["defaultCurrency"],
            "start_date": scenario["closeDate"],
            "end_date": scenario["closeDate"],
            **extra,
        }

    def close_row(self, scenario_id: str, *, as_of: str | None = None) -> pd.Series:
        params = self.scenario_params(
            scenario_id,
            as_of_date=as_of or self.manifest["asOfDate"],
        )
        frame = self.engine.query("close_summary", params)
        self.assertEqual(len(frame), 1)
        return frame.iloc[0]

    def test_registry_exposes_only_the_four_versioned_scenarios(self) -> None:
        registry = self.engine.query("scenario_options")
        self.assertEqual(
            registry["scenario_id"].tolist(),
            [
                "normal",
                "delayed_travel_gbp",
                "stale_electronics_eur_fee",
                "missing_retail_cad",
            ],
        )
        self.assertEqual(default_scenario(scenario_options(registry)), "normal")
        delayed = registry.loc[
            registry["scenario_id"] == "delayed_travel_gbp"
        ].iloc[0]
        self.assertEqual(str(delayed["as_of_date"]), "2024-10-11")

    def test_query_registry_rejects_arbitrary_sql_and_invalid_parameters(self) -> None:
        invalid_calls = (
            ("select * from settlements", {}),
            ("close_summary", {}),
            ("close_summary", {"unexpected": "value"}),
            ("close_summary", {"scenario": "unknown"}),
            ("close_summary", {"currency": "USD"}),
            ("close_summary", {"as_of_date": "03/12/2024"}),
            ("payment_trace", {"payment_id": "1 OR 1=1"}),
            ("payment_trace", {"scenario": "normal"}),
            (
                "close_summary",
                {"start_date": "2024-12-31", "end_date": "2024-01-01"},
            ),
        )
        for query_id, params in invalid_calls:
            with self.subTest(query_id=query_id, params=params):
                with self.assertRaises(ValueError):
                    self.engine.query(query_id, params)

    def test_normal_close_is_a_clean_control(self) -> None:
        row = self.close_row("normal")
        self.assertEqual(int(row["exception_count"]), 0)
        self.assertEqual(int(row["eligible_count"]), int(row["matched_count"]))
        self.assertEqual(float(row["coverage_rate"]), 1.0)
        self.assertEqual(int(row["overdue_minor_units"]), 0)

    def test_delayed_batch_changes_from_open_gap_to_late_evidence(self) -> None:
        scenario = self.scenarios["delayed_travel_gbp"]
        early = self.close_row(
            "delayed_travel_gbp", as_of=scenario["closeDate"]
        )
        final = self.close_row("delayed_travel_gbp")
        expected = int(scenario["expectedSignal"]["affectedPayments"])

        self.assertEqual(int(early["missing_count"]), 0)
        self.assertLess(int(early["matched_count"]), int(final["matched_count"]))
        self.assertEqual(int(final["late_count"]), expected)
        self.assertEqual(int(final["matched_count"]), int(final["eligible_count"]))

    def test_fee_and_missing_scenarios_match_the_manifest_signals(self) -> None:
        fee = self.close_row("stale_electronics_eur_fee")
        missing = self.close_row("missing_retail_cad")
        self.assertEqual(
            int(fee["fee_mismatch_count"]),
            int(
                self.scenarios["stale_electronics_eur_fee"]["expectedSignal"][
                    "affectedPayments"
                ]
            ),
        )
        self.assertEqual(
            int(missing["missing_count"]),
            int(
                self.scenarios["missing_retail_cad"]["expectedSignal"][
                    "affectedPayments"
                ]
            ),
        )

    def test_scored_exceptions_are_flagged_more_anomalous_on_average_than_matches(
        self,
    ) -> None:
        scored = self.engine.query("exception_scoring")
        exceptions_mean = scored.loc[~scored["is_match"], "anomaly_score"].mean()
        matches_mean = scored.loc[scored["is_match"], "anomaly_score"].mean()
        self.assertGreater(exceptions_mean, matches_mean)

    def test_queue_keeps_all_flags_and_sql_primary_precedence(self) -> None:
        queue = self.engine.query(
            "exception_queue", self.scenario_params("delayed_travel_gbp")
        )
        self.assertFalse(queue.empty)
        for row in queue.to_dict(orient="records"):
            reasons = normalise_reasons(row["exception_reasons"], row)
            self.assertTrue(reasons)
            self.assertEqual(row["primary_reason"], reasons[0])
            ranks = [PRIMARY_REASON_ORDER.index(reason) for reason in reasons]
            self.assertEqual(ranks, sorted(ranks))

    def test_payment_trace_is_one_validated_currency_specific_row(self) -> None:
        params = self.scenario_params("delayed_travel_gbp")
        queue = self.engine.query("exception_queue", params)
        payment_id = str(int(queue.iloc[0]["payment_id"]))
        trace = self.engine.query(
            "payment_trace", {**params, "payment_id": payment_id}
        )
        self.assertEqual(len(trace), 1)
        self.assertEqual(str(int(trace.iloc[0]["payment_id"])), payment_id)
        self.assertEqual(trace.iloc[0]["transaction_currency"], "GBP")
        self.assertEqual(trace.iloc[0]["lineage_query_id"], "payment_trace")
        self.assertEqual(
            trace.iloc[0]["lineage_model"], "int_settlement_reconciliation"
        )


if __name__ == "__main__":
    unittest.main()
