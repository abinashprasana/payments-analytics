"""Pure data preparation for the payments intelligence dashboard.

The functions in this module do not depend on Streamlit. Keeping filters and
metric calculations here makes the PostgreSQL and CSV paths behave the same and
allows the analytical rules to be tested without starting the user interface.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class DashboardFilters:
    """The transaction filters shared by the operational dashboard views."""

    start_date: date
    end_date: date
    currencies: tuple[str, ...]
    merchant_categories: tuple[str, ...]
    compare_previous_period: bool = False


def normalise_tables(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    merchants: pd.DataFrame,
    transactions: pd.DataFrame,
    settlements: pd.DataFrame,
    fraud_flags: pd.DataFrame,
) -> tuple[pd.DataFrame, ...]:
    """Return defensive copies with predictable dates, numbers, and booleans."""

    customers = customers.copy()
    accounts = accounts.copy()
    merchants = merchants.copy()
    transactions = transactions.copy()
    settlements = settlements.copy()
    fraud_flags = fraud_flags.copy()

    customers["join_date"] = pd.to_datetime(customers["join_date"], errors="coerce")
    merchants["registration_date"] = pd.to_datetime(
        merchants["registration_date"], errors="coerce"
    )
    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"], errors="coerce"
    )
    transactions["amount"] = pd.to_numeric(transactions["amount"], errors="coerce")
    settlements["settlement_date"] = pd.to_datetime(
        settlements["settlement_date"], errors="coerce"
    )
    settlements["settled_amount"] = pd.to_numeric(
        settlements["settled_amount"], errors="coerce"
    )
    settlements["processing_fee"] = pd.to_numeric(
        settlements["processing_fee"], errors="coerce"
    )
    fraud_flags["flagged_date"] = pd.to_datetime(
        fraud_flags["flagged_date"], errors="coerce"
    )
    fraud_flags["resolved_date"] = pd.to_datetime(
        fraud_flags["resolved_date"], errors="coerce"
    )
    if not pd.api.types.is_bool_dtype(fraud_flags["is_resolved"]):
        fraud_flags["is_resolved"] = (
            fraud_flags["is_resolved"]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("true")
        )
    fraud_flags["is_resolved"] = fraud_flags["is_resolved"].fillna(False)

    return customers, accounts, merchants, transactions, settlements, fraud_flags


def dataset_scope(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    merchants: pd.DataFrame,
    transactions: pd.DataFrame,
    settlements: pd.DataFrame,
    fraud_flags: pd.DataFrame,
) -> dict[str, object]:
    return {
        "customer_count": len(customers),
        "account_count": len(accounts),
        "merchant_count": len(merchants),
        "transaction_count": len(transactions),
        "settlement_count": len(settlements),
        "fraud_flag_count": len(fraud_flags),
        "merchantless_transaction_count": int(
            transactions["merchant_id"].isna().sum()
        ),
        "first_transaction_date": transactions["transaction_date"].min().date(),
        "last_transaction_date": transactions["transaction_date"].max().date(),
    }


def enrich_transactions(
    transactions: pd.DataFrame,
    accounts: pd.DataFrame,
    merchants: pd.DataFrame,
) -> pd.DataFrame:
    """Attach customer and merchant context while retaining transfers."""

    account_columns = ["account_id", "customer_id"]
    merchant_columns = [
        "merchant_id",
        "merchant_name",
        "category",
        "country",
        "risk_tier",
    ]
    enriched = transactions.merge(
        accounts[account_columns],
        on="account_id",
        how="left",
        validate="many_to_one",
    )
    return enriched.merge(
        merchants[merchant_columns],
        on="merchant_id",
        how="left",
        validate="many_to_one",
    )


def apply_filters(
    enriched_transactions: pd.DataFrame,
    filters: DashboardFilters,
    all_categories: Iterable[str],
) -> pd.DataFrame:
    """Apply inclusive dates and the shared currency/category rules."""

    start = pd.Timestamp(filters.start_date)
    end_exclusive = pd.Timestamp(filters.end_date) + pd.Timedelta(days=1)
    mask = enriched_transactions["transaction_date"].ge(start)
    mask &= enriched_transactions["transaction_date"].lt(end_exclusive)

    if filters.currencies:
        mask &= enriched_transactions["currency"].isin(filters.currencies)
    else:
        mask &= False

    selected_categories = set(filters.merchant_categories)
    available_categories = set(all_categories)
    if selected_categories != available_categories:
        if selected_categories:
            mask &= enriched_transactions["category"].isin(selected_categories)
        else:
            mask &= False

    return enriched_transactions.loc[mask].copy()


def previous_period_filters(
    filters: DashboardFilters,
    dataset_start: date,
) -> DashboardFilters | None:
    """Return the immediately preceding inclusive period when fully observable."""

    period_days = (filters.end_date - filters.start_date).days + 1
    previous_end = filters.start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_days - 1)
    if previous_start < dataset_start:
        return None
    return replace(
        filters,
        start_date=previous_start,
        end_date=previous_end,
        compare_previous_period=False,
    )


def overview_metrics(transactions: pd.DataFrame) -> dict[str, float]:
    completed = transactions[transactions["status"].eq("completed")]
    total_count = len(transactions)
    completed_count = len(completed)
    return {
        "transaction_count": float(total_count),
        "completed_count": float(completed_count),
        "completion_rate": (
            completed_count / total_count * 100 if total_count else 0.0
        ),
        "active_customers": float(completed["customer_id"].nunique()),
        "completed_value": float(completed["amount"].sum()),
        "average_value": (
            float(completed["amount"].mean()) if completed_count else 0.0
        ),
    }


def monthly_trends(transactions: pd.DataFrame) -> pd.DataFrame:
    completed = transactions[transactions["status"].eq("completed")].copy()
    if completed.empty:
        return pd.DataFrame(
            columns=["transaction_month", "transaction_count", "completed_value"]
        )
    completed["transaction_month"] = (
        completed["transaction_date"].dt.to_period("M").dt.to_timestamp()
    )
    return (
        completed.groupby("transaction_month", as_index=False)
        .agg(
            transaction_count=("transaction_id", "count"),
            completed_value=("amount", "sum"),
        )
        .sort_values("transaction_month")
    )


def transaction_statuses(transactions: pd.DataFrame) -> pd.DataFrame:
    order = ["completed", "pending", "failed"]
    result = (
        transactions.groupby("status", as_index=False)
        .agg(count=("transaction_id", "count"))
        .set_index("status")
        .reindex(order, fill_value=0)
        .reset_index()
    )
    total = result["count"].sum()
    result["share"] = result["count"] / total * 100 if total else 0.0
    return result


def filtered_settlements(
    settlements: pd.DataFrame,
    filtered_transactions: pd.DataFrame,
) -> pd.DataFrame:
    context_columns = [
        "transaction_id",
        "currency",
        "transaction_date",
        "merchant_id",
        "merchant_name",
        "category",
        "risk_tier",
    ]
    return settlements.merge(
        filtered_transactions[context_columns],
        on="transaction_id",
        how="inner",
        validate="one_to_one",
    )


def settlement_statuses(settlements: pd.DataFrame) -> pd.DataFrame:
    order = ["settled", "delayed", "disputed"]
    result = (
        settlements.groupby("status", as_index=False)
        .agg(count=("settlement_id", "count"))
        .set_index("status")
        .reindex(order, fill_value=0)
        .reset_index()
    )
    total = result["count"].sum()
    result["share"] = result["count"] / total * 100 if total else 0.0
    return result


def settlement_metrics(settlements: pd.DataFrame) -> dict[str, float]:
    return {
        "settlement_count": float(len(settlements)),
        "settled_amount": float(settlements["settled_amount"].sum()),
        "processing_fees": float(settlements["processing_fee"].sum()),
        "delayed_count": float(settlements["status"].eq("delayed").sum()),
    }


def merchant_performance(settlements: pd.DataFrame) -> pd.DataFrame:
    if settlements.empty:
        return pd.DataFrame(
            columns=[
                "merchant_name",
                "category",
                "risk_tier",
                "settlement_count",
                "settled_amount",
                "processing_fees",
            ]
        )
    return (
        settlements.dropna(subset=["merchant_id"])
        .groupby(
            ["merchant_id", "merchant_name", "category", "risk_tier"],
            as_index=False,
        )
        .agg(
            settlement_count=("settlement_id", "count"),
            settled_amount=("settled_amount", "sum"),
            processing_fees=("processing_fee", "sum"),
        )
        .sort_values("settled_amount", ascending=False)
        .reset_index(drop=True)
    )


def filtered_flags(
    fraud_flags: pd.DataFrame,
    filtered_transactions: pd.DataFrame,
) -> pd.DataFrame:
    context_columns = [
        "transaction_id",
        "currency",
        "transaction_date",
        "merchant_id",
        "merchant_name",
        "category",
    ]
    return fraud_flags.merge(
        filtered_transactions[context_columns],
        on="transaction_id",
        how="inner",
        validate="one_to_one",
    )


def risk_metrics(
    transactions: pd.DataFrame,
    flags: pd.DataFrame,
) -> dict[str, float]:
    resolved_count = int(flags["is_resolved"].sum()) if not flags.empty else 0
    flag_count = len(flags)
    return {
        "flag_count": float(flag_count),
        "resolved_count": float(resolved_count),
        "unresolved_count": float(flag_count - resolved_count),
        "resolution_rate": resolved_count / flag_count * 100 if flag_count else 0.0,
        "flag_rate": (
            flag_count / len(transactions) * 100 if len(transactions) else 0.0
        ),
    }


def risk_by_category(
    transactions: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    merchant_transactions = transactions.dropna(subset=["category"]).copy()
    if merchant_transactions.empty:
        return pd.DataFrame(
            columns=[
                "category",
                "total_transactions",
                "flagged_transactions",
                "flag_rate",
            ]
        )
    flagged_ids = set(flags["transaction_id"].tolist())
    merchant_transactions["is_flagged"] = merchant_transactions[
        "transaction_id"
    ].isin(flagged_ids)
    result = (
        merchant_transactions.groupby("category", as_index=False)
        .agg(
            total_transactions=("transaction_id", "count"),
            flagged_transactions=("is_flagged", "sum"),
        )
        .sort_values("category")
    )
    result["flag_rate"] = (
        result["flagged_transactions"] / result["total_transactions"] * 100
    )
    return result.sort_values("flag_rate", ascending=False).reset_index(drop=True)


def risk_review_flow(flags: pd.DataFrame) -> pd.DataFrame:
    if flags.empty:
        return pd.DataFrame(columns=["flag_reason", "outcome", "count"])
    flow = flags.copy()
    flow["outcome"] = flow["is_resolved"].map(
        {True: "Resolved", False: "Unresolved"}
    )
    return (
        flow.groupby(["flag_reason", "outcome"], as_index=False)
        .agg(count=("flag_id", "count"))
        .sort_values(["flag_reason", "outcome"])
    )


def cohort_retention(
    customers: pd.DataFrame,
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    cohort_start: date,
    cohort_end: date,
    max_offset: int = 12,
) -> pd.DataFrame:
    """Build an observable cohort grid, distinguishing zero from future periods."""

    cohorts = customers[["customer_id", "join_date"]].dropna().copy()
    cohort_start_ts = pd.Timestamp(cohort_start)
    cohort_end_exclusive = pd.Timestamp(cohort_end) + pd.Timedelta(days=1)
    cohorts = cohorts[
        cohorts["join_date"].ge(cohort_start_ts)
        & cohorts["join_date"].lt(cohort_end_exclusive)
    ]
    if cohorts.empty:
        return pd.DataFrame(
            columns=[
                "cohort_month",
                "cohort_size",
                "months_active_offset",
                "active_customers",
                "retention_rate",
                "observable",
            ]
        )

    cohorts["cohort_month"] = (
        cohorts["join_date"].dt.to_period("M").dt.to_timestamp()
    )
    cohort_sizes = (
        cohorts.groupby("cohort_month", as_index=False)
        .agg(cohort_size=("customer_id", "nunique"))
    )

    completed = transactions[transactions["status"].eq("completed")].copy()
    completed["activity_month"] = (
        completed["transaction_date"].dt.to_period("M").dt.to_timestamp()
    )
    activity = (
        completed.merge(
            accounts[["account_id", "customer_id"]],
            on="account_id",
            how="inner",
            validate="many_to_one",
        )
        .merge(
            cohorts[["customer_id", "cohort_month"]],
            on="customer_id",
            how="inner",
            validate="many_to_one",
        )
        [["customer_id", "cohort_month", "activity_month"]]
        .drop_duplicates()
    )
    activity["months_active_offset"] = (
        (activity["activity_month"].dt.year - activity["cohort_month"].dt.year)
        * 12
        + activity["activity_month"].dt.month
        - activity["cohort_month"].dt.month
    )
    activity = activity[
        activity["months_active_offset"].between(0, max_offset, inclusive="both")
    ]
    active_counts = (
        activity.groupby(
            ["cohort_month", "months_active_offset"], as_index=False
        )
        .agg(active_customers=("customer_id", "nunique"))
    )

    grid = pd.MultiIndex.from_product(
        [
            cohort_sizes["cohort_month"].tolist(),
            list(range(max_offset + 1)),
        ],
        names=["cohort_month", "months_active_offset"],
    ).to_frame(index=False)
    grid = grid.merge(cohort_sizes, on="cohort_month", how="left")
    grid = grid.merge(
        active_counts,
        on=["cohort_month", "months_active_offset"],
        how="left",
    )

    latest_activity_month = (
        transactions["transaction_date"].max().to_period("M").to_timestamp()
    )
    grid["period_month"] = grid.apply(
        lambda row: row["cohort_month"]
        + pd.DateOffset(months=int(row["months_active_offset"])),
        axis=1,
    )
    grid["observable"] = grid["period_month"].le(latest_activity_month)
    grid.loc[grid["observable"], "active_customers"] = grid.loc[
        grid["observable"], "active_customers"
    ].fillna(0)
    grid["retention_rate"] = (
        grid["active_customers"] / grid["cohort_size"] * 100
    ).round(2)
    return grid.sort_values(["cohort_month", "months_active_offset"])
