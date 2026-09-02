"""Regression tests for dashboard filtering and metric rules."""

from __future__ import annotations

import os
import unittest
from datetime import date

import pandas as pd

from dashboard.analytics import (
    DashboardFilters,
    apply_filters,
    cohort_retention,
    dataset_scope,
    enrich_transactions,
    normalise_tables,
    previous_period_filters,
    risk_metrics,
    settlement_statuses,
)


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(PROJECT_DIR, "data", "raw")


class DashboardFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.accounts = pd.DataFrame(
            {
                "account_id": [1, 2],
                "customer_id": [10, 20],
            }
        )
        self.merchants = pd.DataFrame(
            {
                "merchant_id": [100],
                "merchant_name": ["Example Merchant"],
                "category": ["Retail"],
                "country": ["Ireland"],
                "risk_tier": ["low"],
            }
        )
        self.transactions = pd.DataFrame(
            {
                "transaction_id": [1, 2],
                "account_id": [1, 2],
                "merchant_id": [100, pd.NA],
                "amount": [50.0, 75.0],
                "currency": ["EUR", "EUR"],
                "transaction_date": pd.to_datetime(
                    ["2024-02-10", "2024-02-11"]
                ),
                "transaction_type": ["purchase", "transfer"],
                "status": ["completed", "completed"],
            }
        )
        self.enriched = enrich_transactions(
            self.transactions,
            self.accounts,
            self.merchants,
        )

    def test_all_categories_keep_merchantless_transfers(self) -> None:
        filters = DashboardFilters(
            date(2024, 2, 1),
            date(2024, 2, 29),
            ("EUR",),
            ("Retail",),
        )
        result = apply_filters(self.enriched, filters, ("Retail",))
        self.assertEqual(set(result["transaction_id"]), {1, 2})

    def test_category_subset_excludes_merchantless_transfers(self) -> None:
        filters = DashboardFilters(
            date(2024, 2, 1),
            date(2024, 2, 29),
            ("EUR",),
            tuple(),
        )
        result = apply_filters(self.enriched, filters, ("Retail",))
        self.assertTrue(result.empty)

    def test_dates_are_inclusive_and_currency_is_exact(self) -> None:
        extra = self.enriched.copy()
        extra.loc[extra["transaction_id"].eq(2), "currency"] = "GBP"
        filters = DashboardFilters(
            date(2024, 2, 10),
            date(2024, 2, 10),
            ("EUR",),
            ("Retail",),
        )
        result = apply_filters(extra, filters, ("Retail",))
        self.assertEqual(result["transaction_id"].tolist(), [1])

    def test_previous_period_has_equal_inclusive_length(self) -> None:
        filters = DashboardFilters(
            date(2024, 4, 10),
            date(2024, 4, 19),
            ("EUR",),
            ("Retail",),
            True,
        )
        previous = previous_period_filters(filters, date(2024, 1, 1))
        self.assertIsNotNone(previous)
        self.assertEqual(previous.start_date, date(2024, 3, 31))
        self.assertEqual(previous.end_date, date(2024, 4, 9))

    def test_previous_period_requires_complete_history(self) -> None:
        filters = DashboardFilters(
            date(2024, 1, 1),
            date(2024, 1, 10),
            ("EUR",),
            ("Retail",),
            True,
        )
        self.assertIsNone(previous_period_filters(filters, date(2024, 1, 1)))


class RetentionTests(unittest.TestCase):
    def test_observed_zero_is_not_confused_with_future_month(self) -> None:
        customers = pd.DataFrame(
            {
                "customer_id": [10, 20],
                "join_date": pd.to_datetime(["2024-01-03", "2024-03-02"]),
            }
        )
        accounts = pd.DataFrame(
            {
                "account_id": [1, 2],
                "customer_id": [10, 20],
            }
        )
        transactions = pd.DataFrame(
            {
                "transaction_id": [1, 2],
                "account_id": [1, 2],
                "transaction_date": pd.to_datetime(
                    ["2024-01-12", "2024-03-12"]
                ),
                "status": ["completed", "completed"],
            }
        )
        result = cohort_retention(
            customers,
            accounts,
            transactions,
            date(2024, 1, 1),
            date(2024, 3, 31),
        )
        january = result[result["cohort_month"].eq(pd.Timestamp("2024-01-01"))]
        observed_month_one = january[january["months_active_offset"].eq(1)].iloc[0]
        future_month_three = january[january["months_active_offset"].eq(3)].iloc[0]
        self.assertTrue(observed_month_one["observable"])
        self.assertEqual(observed_month_one["retention_rate"], 0.0)
        self.assertFalse(future_month_three["observable"])
        self.assertTrue(pd.isna(future_month_three["retention_rate"]))


class SourceParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.customers = pd.read_csv(os.path.join(RAW_DATA_DIR, "customers.csv"))
        cls.accounts = pd.read_csv(os.path.join(RAW_DATA_DIR, "accounts.csv"))
        cls.merchants = pd.read_csv(os.path.join(RAW_DATA_DIR, "merchants.csv"))
        cls.transactions = pd.read_csv(
            os.path.join(RAW_DATA_DIR, "transactions.csv")
        )
        cls.settlements = pd.read_csv(
            os.path.join(RAW_DATA_DIR, "settlements.csv")
        )
        cls.flags = pd.read_csv(os.path.join(RAW_DATA_DIR, "fraud_flags.csv"))
        (
            cls.customers,
            cls.accounts,
            cls.merchants,
            cls.transactions,
            cls.settlements,
            cls.flags,
        ) = normalise_tables(
            cls.customers,
            cls.accounts,
            cls.merchants,
            cls.transactions,
            cls.settlements,
            cls.flags,
        )

    def test_source_record_counts(self) -> None:
        self.assertEqual(len(self.customers), 5_000)
        self.assertEqual(len(self.accounts), 6_000)
        self.assertEqual(len(self.merchants), 800)
        self.assertEqual(len(self.transactions), 80_000)
        self.assertEqual(len(self.settlements), 61_124)
        self.assertEqual(len(self.flags), 2_500)

    def test_dataset_scope_includes_merchantless_transactions(self) -> None:
        scope = dataset_scope(
            self.customers,
            self.accounts,
            self.merchants,
            self.transactions,
            self.settlements,
            self.flags,
        )
        self.assertEqual(scope["merchantless_transaction_count"], 11_934)
        self.assertEqual(
            scope["first_transaction_date"],
            date(2022, 2, 7),
        )
        self.assertEqual(
            scope["last_transaction_date"],
            date(2024, 12, 31),
        )

    def test_settlement_outcomes(self) -> None:
        outcomes = settlement_statuses(self.settlements).set_index("status")
        self.assertEqual(int(outcomes.loc["settled", "count"]), 57_381)
        self.assertEqual(int(outcomes.loc["delayed", "count"]), 3_117)
        self.assertEqual(int(outcomes.loc["disputed", "count"]), 626)

    def test_flag_resolution_outcomes(self) -> None:
        metrics = risk_metrics(self.transactions, self.flags)
        self.assertEqual(int(metrics["resolved_count"]), 2_014)
        self.assertEqual(int(metrics["unresolved_count"]), 486)


if __name__ == "__main__":
    unittest.main()
