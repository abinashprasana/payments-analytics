"""Contract and drift tests for the case-study project-data export."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.export_site_data import (
    DEFAULT_OUTPUT,
    RAW_DATA_DIR,
    build_project_data,
    render_project_data,
)


class SiteDataExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_project_data(RAW_DATA_DIR)

    def test_public_schema_and_verified_counts(self) -> None:
        self.assertEqual(self.payload["schemaVersion"], 1)
        self.assertEqual(
            set(self.payload),
            {
                "schemaVersion",
                "datasetWindow",
                "recordCounts",
                "relationships",
                "settlementOutcomes",
                "reviewOutcomes",
                "technology",
                "limitations",
            },
        )
        self.assertEqual(
            self.payload["datasetWindow"],
            {
                "firstTransactionDate": "2022-02-07",
                "lastTransactionDate": "2024-12-31",
            },
        )
        self.assertEqual(self.payload["recordCounts"]["transactions"], 80_000)
        self.assertEqual(self.payload["recordCounts"]["settlements"], 61_124)
        self.assertEqual(self.payload["recordCounts"]["fraudFlags"], 2_500)
        self.assertEqual(
            self.payload["recordCounts"]["merchantlessTransactions"], 11_934
        )

    def test_outcomes_remain_analytics_derived(self) -> None:
        settlements = {
            row["status"]: row for row in self.payload["settlementOutcomes"]
        }
        self.assertEqual(settlements["settled"]["count"], 57_381)
        self.assertEqual(settlements["delayed"]["count"], 3_117)
        self.assertEqual(settlements["disputed"]["count"], 626)
        self.assertEqual(
            self.payload["reviewOutcomes"],
            {
                "total": 2_500,
                "resolved": 2_014,
                "unresolved": 486,
                "resolutionRate": 80.56,
                "flagRate": 3.12,
            },
        )

    def test_checked_in_payload_has_not_drifted(self) -> None:
        self.assertTrue(DEFAULT_OUTPUT.is_file())
        self.assertEqual(
            DEFAULT_OUTPUT.read_text(encoding="utf-8"),
            render_project_data(self.payload),
        )

    def test_export_paths_are_repository_relative(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        self.assertTrue(DEFAULT_OUTPUT.is_relative_to(project_root))
        self.assertTrue(RAW_DATA_DIR.is_relative_to(project_root))


if __name__ == "__main__":
    unittest.main()
