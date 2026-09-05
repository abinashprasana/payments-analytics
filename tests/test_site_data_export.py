"""Contract and drift tests for the generated CaseStudyDataV2 artifact."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analytics_engine import AnalyticsEngine
from scripts.generate_artifacts import (
    DEFAULT_OUTPUT,
    PRIMARY_PRECEDENCE,
    SELECTED_SCENARIO_ID,
    _normalized_for_check,
    build_payload,
    export_marts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CaseStudyArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_payload(build_sha="test-build")
        cls.checked_in = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    def test_v2_schema_and_verified_source_counts(self) -> None:
        self.assertEqual(self.payload["schemaVersion"], 2)
        self.assertEqual(
            set(self.payload),
            {
                "schemaVersion",
                "dataset",
                "build",
                "navigation",
                "question",
                "metricDefinitions",
                "sourceModel",
                "scenarios",
                "selectedScenarioId",
                "investigationSteps",
                "dailyClose",
                "segmentFindings",
                "exceptionSummary",
                "primaryLabelPrecedence",
                "trace",
                "recommendation",
                "validation",
                "models",
                "limitations",
                "workbench",
                "reproduction",
            },
        )
        self.assertEqual(
            self.payload["dataset"]["window"],
            {
                "firstTransactionDate": "2022-02-07",
                "lastTransactionDate": "2024-12-31",
            },
        )
        self.assertEqual(
            self.payload["dataset"]["recordCounts"],
            {
                "sourceTables": 7,
                "transactions": 80_000,
                "eligiblePurchases": 57_629,
                "settlements": 61_124,
            },
        )

    def test_manifest_scenarios_and_primary_precedence_are_canonical(self) -> None:
        self.assertEqual(self.payload["selectedScenarioId"], SELECTED_SCENARIO_ID)
        self.assertEqual(
            [item["id"] for item in self.payload["scenarios"]],
            [
                "normal",
                "delayed_travel_gbp",
                "stale_electronics_eur_fee",
                "missing_retail_cad",
            ],
        )
        self.assertEqual(
            self.payload["primaryLabelPrecedence"],
            list(PRIMARY_PRECEDENCE),
        )
        self.assertIn(
            "Exactly 48 guided payments classify as late",
            next(
                item["expectedSignal"]
                for item in self.payload["scenarios"]
                if item["id"] == "delayed_travel_gbp"
            ),
        )

    def test_daily_close_is_one_close_observed_across_real_as_of_states(self) -> None:
        rows = self.payload["dailyClose"]
        self.assertEqual(
            [row["analysisAsOfDate"] for row in rows],
            ["2024-11-12", "2024-11-15", "2024-11-18", "2025-01-10"],
        )
        self.assertEqual({row["closeDate"] for row in rows}, {"2024-11-12"})
        self.assertEqual({row["currency"] for row in rows}, {"EUR"})
        self.assertEqual(
            [row["matchedCount"] for row in rows],
            [0, 190, 190, 190],
        )
        self.assertEqual(
            [row["coverageBps"] for row in rows],
            [0, 10_000, 10_000, 10_000],
        )
        self.assertIn("190 of 190", self.payload["question"]["conciseAnswer"])
        self.assertIn(
            "fee-mismatch exceptions",
            self.payload["question"]["conciseAnswer"],
        )

    def test_every_public_money_value_carries_its_currency_in_minor_units(self) -> None:
        money_values: list[tuple[dict[str, object], str]] = []
        for row in self.payload["dailyClose"]:
            money_values.extend(
                [(row["overdueValue"], row["currency"]), (row["feeDelta"], row["currency"])]
            )
        for row in self.payload["segmentFindings"]:
            money_values.append((row["overdueValue"], row["currency"]))
        for row in self.payload["exceptionSummary"]:
            money_values.append((row["affectedValue"], row["affectedValue"]["currency"]))
        trace = self.payload["trace"]
        for field in ("gross", "expectedFee", "recordedFee"):
            money_values.append((trace[field], trace["currency"]))

        self.assertTrue(money_values)
        for money, expected_currency in money_values:
            with self.subTest(money=money):
                self.assertEqual(set(money), {"currency", "minorUnits"})
                self.assertEqual(money["currency"], expected_currency)
                self.assertIsInstance(money["minorUnits"], int)

    def test_sql_evidence_uses_only_registered_query_ids(self) -> None:
        with AnalyticsEngine(repo_root=PROJECT_ROOT, build_sha="test") as engine:
            allowed = set(engine.query_ids)
        evidence_ids = {
            step["queryId"] for step in self.payload["investigationSteps"]
        } | {
            self.payload["trace"]["queryId"],
            self.payload["validation"]["explainQueryId"],
        }
        metric_ids = {
            metric["queryId"] for metric in self.payload["metricDefinitions"]
        }
        self.assertTrue(evidence_ids <= allowed)
        self.assertTrue(metric_ids <= allowed)
        for step in self.payload["investigationSteps"]:
            self.assertTrue(step["sql"].strip())
            self.assertIn(step["model"], {model["name"] for model in self.payload["models"]})

    def test_quality_results_are_real_duckdb_checks_not_a_parity_claim(self) -> None:
        results = self.payload["validation"]["qualityResults"]
        self.assertGreaterEqual(len(results), 8)
        self.assertEqual({row["status"] for row in results}, {"pass"})
        self.assertTrue(all(row["checkedRows"] > 0 for row in results))
        self.assertTrue(
            any("does not claim a parity result" in text for text in self.payload["limitations"])
        )

    def test_checked_in_analytical_content_has_not_drifted(self) -> None:
        self.assertEqual(
            _normalized_for_check(self.checked_in),
            _normalized_for_check(self.payload),
        )

    def test_drift_normalization_ignores_only_build_identity(self) -> None:
        changed_build = copy.deepcopy(self.payload)
        changed_build["build"]["commitSha"] = "release-sha"
        changed_build["build"]["generatedAt"] = "2099-01-01T00:00:00Z"
        self.assertEqual(
            _normalized_for_check(changed_build),
            _normalized_for_check(self.payload),
        )

        changed_metric = copy.deepcopy(self.payload)
        changed_metric["dailyClose"][-1]["matchedCount"] -= 1
        self.assertNotEqual(
            _normalized_for_check(changed_metric),
            _normalized_for_check(self.payload),
        )

    def test_single_generator_can_export_all_canonical_public_marts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            with AnalyticsEngine(repo_root=PROJECT_ROOT, build_sha="test") as engine:
                paths = export_marts(engine, output_dir)
            self.assertEqual(
                {path.name for path in paths},
                {
                    "mart_daily_close.csv",
                    "mart_exception_queue.csv",
                    "mart_merchant_health.csv",
                    "mart_payment_trace.csv",
                },
            )
            for path in paths:
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 100)


if __name__ == "__main__":
    unittest.main()
