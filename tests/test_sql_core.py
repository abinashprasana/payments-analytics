"""Contract tests for the deterministic settlement reconciliation core."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import data.generate_data as generator
from scripts.analytics_engine import AnalyticsEngine, QUERY_REQUIRED
from scripts.generate_artifacts import build_payload, export_marts


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SettlementCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = AnalyticsEngine(build_sha="test")
        cls.manifest = json.loads(
            (PROJECT_ROOT / "data" / "scenarios.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.close()

    def test_strict_query_registry_requires_scope(self) -> None:
        self.assertEqual(QUERY_REQUIRED["close_summary"], {"scenario"})
        self.assertEqual(
            QUERY_REQUIRED["payment_trace"], {"scenario", "payment_id"}
        )
        with self.assertRaisesRegex(ValueError, "Missing required parameters"):
            self.engine.query("close_summary")
        with self.assertRaisesRegex(ValueError, "Missing required parameters"):
            self.engine.query("payment_trace", {"scenario": "normal"})
        with self.assertRaisesRegex(ValueError, "Unknown query_id"):
            self.engine.query("select_anything")
        with self.assertRaisesRegex(ValueError, "Unsupported currency"):
            self.engine.query("close_summary", {"scenario": "normal", "currency": "USD"})

    def test_guided_scenarios_have_exact_final_signals(self) -> None:
        expected = {
            "normal": ("exception_count", 0),
            "delayed_travel_gbp": ("late_count", 48),
            "stale_electronics_eur_fee": ("fee_mismatch_count", 48),
            "missing_retail_cad": ("missing_count", 48),
        }
        for scenario_id, (column, count) in expected.items():
            with self.subTest(scenario=scenario_id):
                result = self.engine.query("close_summary", {"scenario": scenario_id})
                self.assertEqual(len(result), 1)
                self.assertEqual(int(result.iloc[0][column]), count)

        normal = self.engine.query("close_summary", {"scenario": "normal"}).iloc[0]
        for column in (
            "missing_count", "currency_mismatch_count", "amount_mismatch_count",
            "fee_mismatch_count", "late_count", "disputed_count",
        ):
            self.assertEqual(int(normal[column]), 0, column)

    def test_delayed_batch_progresses_from_gap_to_late_recovery(self) -> None:
        checkpoints = {
            "2024-10-08": (0, 0, 0),
            "2024-10-11": (48, 32, 0),
            "2024-10-14": (94, 2, 46),
            "2025-01-10": (96, 0, 48),
        }
        for as_of, (matched, missing, late) in checkpoints.items():
            with self.subTest(as_of=as_of):
                row = self.engine.query(
                    "close_summary",
                    {"scenario": "delayed_travel_gbp", "as_of_date": as_of},
                ).iloc[0]
                self.assertEqual(int(row["eligible_count"]), 96)
                self.assertEqual(int(row["matched_count"]), matched)
                self.assertEqual(int(row["missing_count"]), missing)
                self.assertEqual(int(row["late_count"]), late)

    def test_manifest_reasons_are_canonical(self) -> None:
        allowed = {
            "matched", "missing", "currency_mismatch", "amount_mismatch",
            "fee_mismatch", "late", "disputed",
        }
        reasons = {
            item["expectedSignal"]["primaryReason"]
            for item in self.manifest["scenarios"]
        }
        self.assertTrue(reasons <= allowed)
        self.assertIn("fee_mismatch", reasons)
        self.assertNotIn("fee", reasons)

    def test_ancillary_controls_do_not_touch_guided_dates(self) -> None:
        guided_dates = {
            item["closeDate"] for item in self.manifest["scenarios"]
        }
        rows = self.engine.connection.execute(
            """
            SELECT CAST(transaction_date AS DATE), primary_reason
            FROM int_settlement_reconciliation
            WHERE is_currency_mismatch OR is_amount_mismatch OR is_disputed
            """
        ).fetchall()
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(str(row[0]) not in guided_dates for row in rows))

    def test_flags_are_independent_and_precedence_is_stable(self) -> None:
        payment_id = self.engine.connection.execute(
            """
            SELECT payment_id FROM int_settlement_reconciliation
            WHERE primary_reason = 'amount_mismatch'
            ORDER BY payment_id LIMIT 1
            """
        ).fetchone()[0]
        self.engine.connection.execute(
            "UPDATE settlements SET status = 'disputed' WHERE transaction_id = ?",
            [payment_id],
        )
        try:
            row = self.engine.connection.execute(
                """
                SELECT primary_reason, exception_reasons, priority_rank
                FROM mart_exception_queue WHERE payment_id = ?
                """,
                [payment_id],
            ).fetchone()
            self.assertEqual(row[0], "amount_mismatch")
            self.assertEqual(row[1], "amount_mismatch,disputed")
            self.assertEqual(row[2], 3)
        finally:
            self.engine.connection.execute(
                "UPDATE settlements SET status = 'settled' WHERE transaction_id = ?",
                [payment_id],
            )

    def test_empty_filter_and_unknown_payment_return_empty_frames(self) -> None:
        empty = self.engine.query(
            "close_summary",
            {
                "scenario": "normal",
                "start_date": "2025-01-01",
                "end_date": "2025-01-02",
            },
        )
        self.assertTrue(empty.empty)
        trace = self.engine.query(
            "payment_trace", {"scenario": "normal", "payment_id": 999_999_999}
        )
        self.assertTrue(trace.empty)

    def test_quality_checks_pass_at_snapshot_as_of(self) -> None:
        quality = self.engine.query("quality_results")
        self.assertFalse(quality.empty)
        self.assertEqual(set(quality["status"]), {"pass"})
        self.assertEqual(int(quality["failing_rows"].sum()), 0)

    def test_generator_reproduces_checked_snapshot(self) -> None:
        checked_raw = PROJECT_ROOT / "data" / "raw"
        previous_output = generator.OUTPUT_DIR
        with tempfile.TemporaryDirectory() as temporary:
            generated = Path(temporary)
            generator.OUTPUT_DIR = generated
            try:
                generator.main()
            finally:
                generator.OUTPUT_DIR = previous_output
            for name in generator.TABLE_NAMES if hasattr(generator, "TABLE_NAMES") else (
                "customers", "accounts", "merchants", "merchant_terms",
                "transactions", "settlements", "fraud_flags",
            ):
                expected = hashlib.sha256(
                    (checked_raw / f"{name}.csv").read_bytes()
                ).hexdigest()
                actual = hashlib.sha256(
                    (generated / f"{name}.csv").read_bytes()
                ).hexdigest()
                self.assertEqual(actual, expected, name)

    def test_generated_payload_uses_sql_evidence_and_money_objects(self) -> None:
        payload = build_payload(build_sha="test-sha")
        self.assertEqual(payload["build"]["commitSha"], "test-sha")
        self.assertEqual(payload["selectedScenarioId"], "delayed_travel_gbp")
        self.assertEqual(
            [row["analysisAsOfDate"] for row in payload["dailyClose"]],
            ["2024-10-08", "2024-10-11", "2024-10-14", "2025-01-10"],
        )
        self.assertEqual(payload["dailyClose"][-1]["coverageBps"], 10_000)
        self.assertEqual(payload["exceptionSummary"][4]["count"], 48)
        for row in payload["dailyClose"]:
            self.assertEqual(row["overdueValue"]["currency"], row["currency"])
            self.assertIsInstance(row["overdueValue"]["minorUnits"], int)
        self.assertNotIn("executionTimeMs", payload["validation"])

    def test_optional_mart_export_writes_canonical_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = export_marts(self.engine, Path(temporary))
            self.assertEqual(len(paths), 4)
            daily = next(path for path in paths if path.name == "mart_daily_close.csv")
            with daily.open(newline="", encoding="utf-8") as handle:
                header = next(csv.reader(handle))
            self.assertIn("currency", header)
            self.assertIn("overdue_minor_units", header)


if __name__ == "__main__":
    unittest.main()
