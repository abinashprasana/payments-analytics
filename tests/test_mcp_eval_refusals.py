"""Offline checks for the MCP evaluation refusal set. No model or network calls."""

from __future__ import annotations

import copy
import unittest
from collections import Counter

from mcp_eval import refusals
from scripts.analytics_engine import AnalyticsEngine


class RefusalCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = AnalyticsEngine(build_sha="test-mcp-eval")
        cls.records = refusals.load(refusals.REFUSALS_PATH)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.close()

    def test_refusal_file_matches_specs_and_snapshot(self) -> None:
        self.assertEqual(refusals.check(self.engine), [])

    def test_size_and_every_attack_class(self) -> None:
        self.assertGreaterEqual(len(self.records), 15)
        self.assertLessEqual(len(self.records), 20)
        self.assertEqual(
            set(Counter(r["attack_class"] for r in self.records)),
            set(refusals.ATTACK_CLASSES),
        )
        self.assertFalse(any(r["reviewed"] for r in self.records))

    def test_safe_calls_are_valid_registry_calls(self) -> None:
        for record in self.records:
            for call in record["safe_calls"]:
                if call["tool"] != "run_query":
                    continue
                with self.subTest(record=record["id"], call=call):
                    self.engine._validated_params(call["query_id"], call["params"])

    def test_forbidden_sums_only_mix_currencies(self) -> None:
        figures = [
            {"overdue_minor_units": 100, "currency": "GBP"},
            {"overdue_minor_units": 40, "currency": "CAD"},
            {"overdue_minor_units": 0, "currency": "EUR"},
            {"overdue_minor_units": 7, "currency": "GBP"},
        ]
        self.assertEqual(refusals.forbidden_sums(figures), [147])
        self.assertEqual(refusals.forbidden_sums(None), [])

    def test_validator_rejects_broken_records(self) -> None:
        record = copy.deepcopy(
            next(r for r in self.records if r["expected_behavior"] == "safe_reformulation")
        )
        self.assertEqual(refusals.validate_record(record), [])
        record["safe_calls"] = refusals.DISCOVERY
        self.assertTrue(refusals.validate_record(record))


if __name__ == "__main__":
    unittest.main()
