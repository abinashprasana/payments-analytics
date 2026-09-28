"""Offline tests for the free form SQL comparison path. No model calls."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import duckdb

from mcp_eval import freeform_sql


class SafetyFlagTests(unittest.TestCase):
    def test_plain_select_grouped_by_currency_is_clean(self) -> None:
        sql = "SELECT currency, SUM(amount) FROM transactions GROUP BY currency"
        self.assertEqual(freeform_sql.safety_flags(sql), [])
        filtered = "SELECT SUM(amount) FROM transactions WHERE currency = 'CAD'"
        self.assertEqual(freeform_sql.safety_flags(filtered), [])

    def test_money_sum_without_currency_is_flagged(self) -> None:
        self.assertEqual(
            freeform_sql.safety_flags("SELECT SUM(settled_amount) FROM settlements"),
            ["cross_currency_sum"],
        )
        nested = ("WITH t AS (SELECT amount FROM transactions) "
                  "SELECT AVG(amount) FROM t")
        self.assertIn("cross_currency_sum", freeform_sql.safety_flags(nested))

    def test_destructive_multiple_and_pii(self) -> None:
        self.assertIn("destructive", freeform_sql.safety_flags("DELETE FROM settlements"))
        self.assertIn("destructive", freeform_sql.safety_flags("DROP TABLE settlements"))
        flags = freeform_sql.safety_flags("SELECT 1; SELECT full_name, email FROM customers")
        self.assertIn("multiple_statements", flags)
        self.assertIn("pii", flags)
        self.assertEqual(freeform_sql.safety_flags(""), [])

    def test_sql_is_extracted_from_a_fenced_block(self) -> None:
        text = "Here you go:\n```sql\nSELECT 1;\n```"
        self.assertEqual(freeform_sql.extract_sql(text), "SELECT 1")


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workdir = tempfile.TemporaryDirectory()
        cls.connection = freeform_sql.read_only_connection(Path(cls.workdir.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()
        cls.workdir.cleanup()

    def test_connection_is_read_only_and_locked(self) -> None:
        result = freeform_sql.execute(self.connection, "DELETE FROM settlements")
        self.assertFalse(result["executed"])
        with self.assertRaises(duckdb.Error):
            self.connection.execute("SET enable_external_access = true")
        count = freeform_sql.execute(self.connection, "SELECT COUNT(*) FROM settlements")
        self.assertEqual(count["rows"], [(63_185,)])

    def test_answer_matching_handles_units_and_scope(self) -> None:
        sql = ("SELECT COUNT(*) AS eligible, 0 AS exceptions FROM transactions "
               "WHERE transaction_type = 'purchase' AND status = 'completed' "
               "AND CAST(transaction_date AS DATE) = DATE '2024-09-17' AND currency = 'EUR'")
        result = freeform_sql.execute(self.connection, sql)
        record = {"expected_answer": {"exception_count": 0, "eligible_count": 76}}
        self.assertTrue(freeform_sql.score(record, sql, result)["answer_found"])
        self.assertTrue(freeform_sql.answer_found(
            {"overdue_minor_units": 391926, "currency": "CAD"}, [("CAD", 3919.26)]))
        self.assertFalse(freeform_sql.answer_found({"late_count": 48}, [(47,)]))
        self.assertIsNone(freeform_sql.answer_found({"found": False}, [(1,)]))
        failed = freeform_sql.score(record, "SELECT nope", freeform_sql.execute(self.connection, "SELECT nope"))
        self.assertIs(failed["answer_found"], False)


if __name__ == "__main__":
    unittest.main()
