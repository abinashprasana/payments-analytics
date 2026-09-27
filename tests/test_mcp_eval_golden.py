"""Offline checks for the MCP evaluation golden set. No model or network calls."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from mcp_eval import golden
from scripts.analytics_engine import AnalyticsEngine


class GoldenQuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = AnalyticsEngine(build_sha="test-mcp-eval")
        cls.records = golden.load()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.close()

    def test_golden_file_matches_specs_and_snapshot(self) -> None:
        self.assertEqual(golden.check(self.engine), [])

    def test_size_and_category_coverage(self) -> None:
        self.assertGreaterEqual(len(self.records), 40)
        self.assertLessEqual(len(self.records), 50)
        counts = Counter(record["category"] for record in self.records)
        self.assertEqual(set(counts), set(golden.CATEGORIES))
        self.assertGreaterEqual(counts["currency_boundary"], 4)
        self.assertGreaterEqual(counts["ambiguous"], 3)

    def test_ids_are_unique_and_sequential(self) -> None:
        ids = [record["id"] for record in self.records]
        self.assertEqual(ids, [f"q{index:03d}" for index in range(1, len(ids) + 1)])

    def test_screens_are_left_out(self) -> None:
        text = json.dumps(self.records)
        for query_id in ("benford_conformity", "exception_rate_screen", "exception_scoring"):
            self.assertNotIn(query_id, text)

    def test_every_expected_call_is_valid_for_the_engine(self) -> None:
        calls = []
        for record in self.records:
            if record["expected_tool"] == "run_query" and record["expected_params"] is not None:
                calls.append((record["expected_query_id"], record["expected_params"]))
            calls.extend(
                (alt["query_id"], alt["params"]) for alt in record["alternatives"]
            )
            calls.extend(
                (call["query_id"], call["params"]) for call in record["expected_calls"] or []
            )
        for query_id, params in calls:
            query_id = query_id[0] if isinstance(query_id, list) else query_id
            with self.subTest(query_id=query_id, params=params):
                self.engine._validated_params(query_id, params)

    def test_trace_payment_ids_are_real_scenario_payments(self) -> None:
        for record in self.records:
            if record["expected_tool"] != "trace_payment":
                continue
            with self.subTest(record=record["id"]):
                found = golden.derive_answer(
                    self.engine,
                    {"op": "trace_absent", "payment_id": record["expected_params"]["payment_id"]},
                )["found"]
                self.assertEqual(found, record["expected_answer"] != {"found": False})

    def test_validator_rejects_broken_records(self) -> None:
        base = next(r for r in self.records if r["category"] == "ambiguous")
        self.assertEqual(golden.validate_record(base), [])
        broken = copy.deepcopy(base)
        broken["why"] = None
        self.assertTrue(golden.validate_record(broken))
        boundary = copy.deepcopy(
            next(r for r in self.records if r["category"] == "currency_boundary")
        )
        boundary["expected_behavior"] = "sum_anyway"
        self.assertTrue(golden.validate_record(boundary))
        screen = copy.deepcopy(base)
        screen["expected_query_id"] = ["benford_conformity", "close_summary"]
        self.assertTrue(golden.validate_record(screen))

    def test_build_keeps_reviews_only_for_unchanged_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "questions.jsonl"
            rows = copy.deepcopy(self.records)
            rows[0]["reviewed"] = True
            rows[1]["reviewed"] = True
            rows[1]["question"] = "An older wording"
            path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            rebuilt = golden.build(self.engine, path)
            self.assertTrue(rebuilt[0]["reviewed"])
            self.assertFalse(rebuilt[1]["reviewed"])
            self.assertFalse(any(r["reviewed"] for r in rebuilt[2:]))


if __name__ == "__main__":
    unittest.main()
