"""Interactive payments intelligence dashboard."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import date
from typing import Mapping

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(PROJECT_DIR, "data", "raw")
BRAND_ICON = os.path.join(
    PROJECT_DIR,
    "dashboard",
    "static",
    "brand",
    "payment-observatory-mark-compact.svg",
)
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

from dashboard.analytics import (  # noqa: E402
    DashboardFilters,
    apply_filters,
    cohort_retention,
    dataset_scope,
    enrich_transactions,
    filtered_flags,
    filtered_settlements,
    merchant_performance,
    monthly_trends,
    normalise_tables,
    overview_metrics,
    previous_period_filters,
    risk_by_category,
    risk_metrics,
    risk_review_flow,
    settlement_metrics,
    settlement_statuses,
    transaction_statuses,
)
from dashboard.ui import (  # noqa: E402
    apply_theme,
    data_note,
    mount_page_motion,
    render_data_model,
    render_empty_state,
    render_filter_controls,
    render_filter_note,
    render_footer,
    render_hero,
    render_kpi_grid,
    render_measure_switch,
    render_metric_strip,
    render_method_cards,
    render_navigation,
    render_settlement_corridor,
    render_status_rail,
    render_topbar,
    section_header,
)

try:
    from scripts.db_connection import get_read_engine

    DB_IMPORT_OK = True
except Exception:
    DB_IMPORT_OK = False


st.set_page_config(
    page_title="Payment Observatory | Payments Intelligence",
    page_icon=BRAND_ICON,
    layout="wide",
    initial_sidebar_state="collapsed",
)


INK = "#F1F3EF"
MUTED = "#8D99A5"
CYAN = "#68DCFF"
TEAL = "#8AF6C7"
AMBER = "#F5BB62"
CORAL = "#FF756F"
VIOLET = "#A58CFF"
GRID = "rgba(203, 219, 233, 0.09)"
PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}
CATEGORY_COLORS = {
    "Retail": "#68DCFF",
    "Food & Beverage": "#8AF6C7",
    "Travel": "#A58CFF",
    "Entertainment": "#F5BB62",
    "Healthcare": "#7EA4FF",
    "Utilities": "#71C8C8",
    "Services": "#C083FF",
    "Electronics": "#FF8F6B",
}
VALID_VIEWS = ("overview", "merchant", "risk", "retention", "model")
DEFAULT_VIEW = VALID_VIEWS[0]
CASE_STUDY_URL = os.getenv(
    "CASE_STUDY_URL",
    "https://payment-observatory.vercel.app/",
).strip()


@dataclass(frozen=True)
class DashboardUIState:
    """Persistent presentation state shared by the operational views."""

    active_view: str
    filters: DashboardFilters
    trend_mode: str = "Transaction count"


def chart_layout(title: str, height: int = 430) -> dict[str, object]:
    return {
        "title": {
            "text": title,
            "font": {"size": 16, "color": INK},
            "x": 0.025,
            "xanchor": "left",
        },
        "height": height,
        "margin": {"l": 42, "r": 24, "t": 64, "b": 42},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": "Source Sans, Segoe UI, sans-serif",
            "color": MUTED,
            "size": 12,
        },
        "hoverlabel": {
            "bgcolor": "#0D1116",
            "bordercolor": "rgba(203,219,233,0.22)",
            "font": {
                "color": INK,
                "family": "Source Sans, Segoe UI, sans-serif",
                "size": 12,
            },
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    }


def style_axes(figure: go.Figure) -> go.Figure:
    figure.update_xaxes(
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickfont={"color": MUTED, "size": 11},
        title_font={"color": MUTED, "size": 12},
    )
    figure.update_yaxes(
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickfont={"color": MUTED, "size": 11},
        title_font={"color": MUTED, "size": 12},
    )
    return figure


@st.cache_data(show_spinner=False)
def load_csvs() -> tuple[pd.DataFrame, ...]:
    tables = (
        pd.read_csv(os.path.join(RAW_DATA_DIR, "customers.csv")),
        pd.read_csv(os.path.join(RAW_DATA_DIR, "accounts.csv")),
        pd.read_csv(os.path.join(RAW_DATA_DIR, "merchants.csv")),
        pd.read_csv(os.path.join(RAW_DATA_DIR, "transactions.csv")),
        pd.read_csv(os.path.join(RAW_DATA_DIR, "settlements.csv")),
        pd.read_csv(os.path.join(RAW_DATA_DIR, "fraud_flags.csv")),
    )
    return normalise_tables(*tables)


def load_database_tables() -> tuple[pd.DataFrame, ...]:
    engine = get_read_engine()
    try:
        table_names = [
            "customers",
            "accounts",
            "merchants",
            "transactions",
            "settlements",
            "fraud_flags",
        ]
        tables = tuple(
            pd.read_sql_query(f"SELECT * FROM {table_name};", engine)
            for table_name in table_names
        )
    finally:
        engine.dispose()
    return normalise_tables(*tables)


@st.cache_data(ttl=600, show_spinner=False)
def load_payment_data() -> tuple[pd.DataFrame, ...]:
    if DB_IMPORT_OK:
        try:
            return (*load_database_tables(), True)
        except Exception:
            pass
    return (*load_csvs(), False)


def format_date_window(start: date, end: date) -> str:
    return f"{start.strftime('%d %b %Y')} to {end.strftime('%d %b %Y')}"


def canonical_query_view() -> str:
    """Return a supported deep-link view and repair missing or invalid URLs."""

    raw_view = st.query_params.get("view", DEFAULT_VIEW)
    if isinstance(raw_view, list):
        raw_view = raw_view[-1] if raw_view else DEFAULT_VIEW
    selected = str(raw_view).strip().lower()
    if selected not in VALID_VIEWS:
        selected = DEFAULT_VIEW
    if "view" not in st.query_params or raw_view != selected:
        st.query_params["view"] = selected
    return selected


def compact_amount(value: float) -> tuple[float, int, str]:
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return value / 1_000_000_000, 2, "B"
    if magnitude >= 1_000_000:
        return value / 1_000_000, 2, "M"
    if magnitude >= 1_000:
        return value / 1_000, 1, "K"
    return value, 2, ""


def display_amount(value: float, currency_prefix: str = "") -> str:
    scaled, decimals, suffix = compact_amount(value)
    return f"{currency_prefix}{scaled:,.{decimals}f}{suffix}"


def comparison_badge(
    current: float,
    previous: float | None,
    *,
    percentage_points: bool = False,
) -> tuple[str, str]:
    if previous is None:
        return "N/A · prior period unavailable", ""
    if percentage_points:
        change = current - previous
        text = f"{change:+.2f} pp vs previous"
    elif previous == 0:
        return "N/A · previous value was zero", ""
    else:
        change = (current - previous) / abs(previous) * 100
        text = f"{change:+.1f}% vs previous"
    tone = "up" if change > 0 else "down" if change < 0 else ""
    return text, tone


def reset_dashboard_filters(
    dataset_start: date,
    dataset_end: date,
    currencies: tuple[str, ...],
    categories: tuple[str, ...],
) -> None:
    payload = {
        "startDate": dataset_start.isoformat(),
        "endDate": dataset_end.isoformat(),
        "currencies": list(currencies),
        "categories": list(categories),
        "comparePrevious": False,
    }
    st.session_state["pay_filter_state"] = payload
    component_state = st.session_state.get("pay_filter_deck")
    if isinstance(component_state, dict):
        component_state["filters"] = payload


def build_kpi_cards(
    metrics: Mapping[str, float],
    previous: Mapping[str, float] | None,
    filters: DashboardFilters,
) -> list[dict[str, object]]:
    one_currency = len(filters.currencies) == 1
    currency_prefix = f"{filters.currencies[0]} " if one_currency else ""
    scaled_value, value_decimals, value_suffix = compact_amount(
        metrics["completed_value"]
    )

    comparisons: dict[str, tuple[str, str]] = {}
    if filters.compare_previous_period:
        for key in ["transaction_count", "active_customers", "completed_value"]:
            comparisons[key] = comparison_badge(
                metrics[key],
                previous[key] if previous else None,
            )
        comparisons["completion_rate"] = comparison_badge(
            metrics["completion_rate"],
            previous["completion_rate"] if previous else None,
            percentage_points=True,
        )

    value_label = (
        f"Completed value ({filters.currencies[0]})"
        if one_currency
        else "Nominal completed value"
    )
    value_note = (
        "One source currency in view"
        if one_currency
        else "Selected currencies are not FX-converted"
    )

    definitions = [
        {
            "key": "transaction_count",
            "label": "Transactions in view",
            "number": metrics["transaction_count"],
            "decimals": 0,
            "prefix": "",
            "suffix": "",
            "value": f"{int(metrics['transaction_count']):,}",
            "note": "All statuses within the active filters",
            "tone": "cyan",
        },
        {
            "key": "completion_rate",
            "label": "Completion rate",
            "number": metrics["completion_rate"],
            "decimals": 2,
            "prefix": "",
            "suffix": "%",
            "value": f"{metrics['completion_rate']:.2f}%",
            "note": f"{int(metrics['completed_count']):,} completed payments",
            "tone": "teal",
        },
        {
            "key": "active_customers",
            "label": "Active customers",
            "number": metrics["active_customers"],
            "decimals": 0,
            "prefix": "",
            "suffix": "",
            "value": f"{int(metrics['active_customers']):,}",
            "note": "Customers with a completed payment",
            "tone": "violet",
        },
        {
            "key": "completed_value",
            "label": value_label,
            "number": scaled_value,
            "decimals": value_decimals,
            "prefix": currency_prefix,
            "suffix": value_suffix,
            "value": display_amount(
                metrics["completed_value"],
                currency_prefix=currency_prefix,
            ),
            "note": value_note,
            "tone": "amber",
        },
    ]
    for definition in definitions:
        comparison, tone = comparisons.get(definition["key"], ("", ""))
        definition["comparison"] = comparison
        definition["comparison_tone"] = tone
    return definitions


apply_theme()

with st.spinner("Loading payment records"):
    (
        customers,
        accounts,
        merchants,
        transactions,
        settlements,
        fraud_flags,
        using_database,
    ) = load_payment_data()

scope = dataset_scope(
    customers,
    accounts,
    merchants,
    transactions,
    settlements,
    fraud_flags,
)
dataset_start = scope["first_transaction_date"]
dataset_end = scope["last_transaction_date"]
source_label = (
    "PostgreSQL connected" if using_database else "Repository CSV snapshot"
)
first_date_label = pd.Timestamp(dataset_start).strftime("%b %Y")
last_date_label = pd.Timestamp(dataset_end).strftime("%b %Y")

render_topbar(
    source_label,
    first_date_label,
    last_date_label,
    case_study_url=CASE_STUDY_URL,
)
render_hero(scope, source_label)

enriched_transactions = enrich_transactions(transactions, accounts, merchants)
all_currencies = tuple(
    sorted(enriched_transactions["currency"].dropna().astype(str).unique())
)
all_categories = tuple(sorted(merchants["category"].dropna().astype(str).unique()))

query_view = canonical_query_view()
last_query_view = st.session_state.get("pay_last_query_view")
query_changed = last_query_view is None or query_view != last_query_view
if query_changed:
    component_state = st.session_state.get("pay_view_rail")
    if isinstance(component_state, dict):
        component_state["view"] = query_view
navigation_seed = (
    query_view
    if query_changed
    else str(st.session_state.get("pay_active_view", query_view))
)

sticky_controls = st.container(key="pay_sticky_controls")
with sticky_controls:
    active_view = render_navigation(navigation_seed)
if active_view not in VALID_VIEWS:
    active_view = DEFAULT_VIEW
st.session_state["pay_active_view"] = active_view
st.session_state["pay_last_query_view"] = active_view
if st.query_params.get("view") != active_view:
    st.query_params["view"] = active_view

default_filter_state = {
    "startDate": dataset_start.isoformat(),
    "endDate": dataset_end.isoformat(),
    "currencies": list(all_currencies),
    "categories": list(all_categories),
    "comparePrevious": False,
}
current_filter_state = st.session_state.get(
    "pay_filter_state",
    default_filter_state,
)
with sticky_controls:
    control_state = render_filter_controls(
        dataset_start=dataset_start.isoformat(),
        dataset_end=dataset_end.isoformat(),
        currencies=all_currencies,
        categories=all_categories,
        current=current_filter_state,
    )

if control_state is None:
    with st.form("native_filter_fallback", border=True):
        filter_columns = st.columns([1.2, 1.0, 1.35, 0.85])
        with filter_columns[0]:
            selected_dates = st.date_input(
                "Transaction dates",
                value=(dataset_start, dataset_end),
                min_value=dataset_start,
                max_value=dataset_end,
                key="pay_native_date_range",
            )
        with filter_columns[1]:
            selected_currencies = st.multiselect(
                "Currencies",
                options=list(all_currencies),
                default=list(all_currencies),
                key="pay_native_currencies",
            )
        with filter_columns[2]:
            selected_categories = st.multiselect(
                "Merchant categories",
                options=list(all_categories),
                default=list(all_categories),
                key="pay_native_categories",
            )
        with filter_columns[3]:
            compare_previous = st.toggle(
                "Compare previous",
                value=False,
                key="pay_native_compare",
                help="Uses the immediately preceding date range of equal length.",
            )
        st.form_submit_button("Apply scope", use_container_width=True)
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        selected_start, selected_end = selected_dates
    elif isinstance(selected_dates, (date, pd.Timestamp)):
        selected_start = selected_end = selected_dates
    else:
        selected_start, selected_end = dataset_start, dataset_end
else:
    st.session_state["pay_filter_state"] = control_state
    selected_start = pd.Timestamp(
        control_state.get("startDate", dataset_start)
    ).date()
    selected_end = pd.Timestamp(
        control_state.get("endDate", dataset_end)
    ).date()
    selected_currencies = list(
        control_state.get("currencies", all_currencies)
    )
    selected_categories = list(
        control_state.get("categories", all_categories)
    )
    compare_previous = bool(
        control_state.get("comparePrevious", False)
    )

filters = DashboardFilters(
    start_date=pd.Timestamp(selected_start).date(),
    end_date=pd.Timestamp(selected_end).date(),
    currencies=tuple(selected_currencies),
    merchant_categories=tuple(selected_categories),
    compare_previous_period=bool(compare_previous),
)
filtered_transactions = apply_filters(
    enriched_transactions,
    filters,
    all_categories,
)

filter_explanation = (
    f"Showing {len(filtered_transactions):,} of {len(transactions):,} transactions "
    f"for {format_date_window(filters.start_date, filters.end_date)}."
)
if set(filters.merchant_categories) != set(all_categories):
    filter_explanation += (
        " The merchant category filter excludes transfers because those records "
        "do not have a merchant."
    )
if len(filters.currencies) != 1:
    filter_explanation += " Value totals are nominal; currencies are not converted."
render_filter_note(filter_explanation)

if filtered_transactions.empty:
    render_empty_state()
    st.button(
        "Reset filters",
        on_click=reset_dashboard_filters,
        args=(dataset_start, dataset_end, all_currencies, all_categories),
    )
    render_footer()
    mount_page_motion()
    st.stop()

current_metrics = overview_metrics(filtered_transactions)
previous_metrics = None
if filters.compare_previous_period:
    comparison_filters = previous_period_filters(filters, dataset_start)
    if comparison_filters:
        previous_transactions = apply_filters(
            enriched_transactions,
            comparison_filters,
            all_categories,
        )
        previous_metrics = overview_metrics(previous_transactions)

settlement_records = filtered_settlements(settlements, filtered_transactions)
flag_records = filtered_flags(fraud_flags, filtered_transactions)
ui_state = DashboardUIState(
    active_view=active_view,
    filters=filters,
    trend_mode=str(
        st.session_state.get("pay_trend_measure", "Transaction count")
    ),
)


if ui_state.active_view == "overview":
    section_header(
        "Read the payment system in one pass",
        "Activity, completion, customer reach, nominal value and status stay close enough to scan as one operational picture.",
        "System overview",
    )
    render_kpi_grid(
        build_kpi_cards(current_metrics, previous_metrics, filters)
    )

    status_frame = transaction_statuses(filtered_transactions)
    render_status_rail(
        "Transaction status",
        f"{len(filtered_transactions):,} records in the current view",
        status_frame,
        {
            "completed": TEAL,
            "pending": AMBER,
            "failed": CORAL,
        },
    )

    trend_choice = render_measure_switch(ui_state.trend_mode)
    st.session_state["pay_trend_measure"] = trend_choice
    trend_frame = monthly_trends(filtered_transactions)
    trend_field = (
        "transaction_count"
        if trend_choice == "Transaction count"
        else "completed_value"
    )
    trend_color = CYAN if trend_field == "transaction_count" else AMBER
    trend_title = (
        "Completed payments by month"
        if trend_field == "transaction_count"
        else "Nominal completed value by month"
    )
    trend_figure = go.Figure()
    trend_figure.add_trace(
        go.Scatter(
            x=trend_frame["transaction_month"],
            y=trend_frame[trend_field],
            mode="lines+markers",
            line={"color": trend_color, "width": 2.5, "shape": "spline"},
            marker={
                "size": 6,
                "color": trend_color,
                "line": {"color": "#07111A", "width": 1},
            },
            fill="tozeroy",
            fillcolor=(
                "rgba(75,216,255,0.07)"
                if trend_field == "transaction_count"
                else "rgba(244,200,106,0.07)"
            ),
            hovertemplate=(
                "%{x|%b %Y}<br>%{y:,.0f} completed payments<extra></extra>"
                if trend_field == "transaction_count"
                else "%{x|%b %Y}<br>%{y:,.2f} nominal value<extra></extra>"
            ),
        )
    )
    trend_layout = chart_layout(trend_title, 450)
    trend_layout["margin"]["r"] = 86
    trend_figure.update_layout(**trend_layout)
    trend_figure.update_xaxes(title=None)
    trend_figure.update_yaxes(
        title="Payments" if trend_field == "transaction_count" else "Nominal value"
    )
    style_axes(trend_figure)
    if not trend_frame.empty:
        last_point = trend_frame.iloc[-1]
        direct_label = (
            f"{int(last_point[trend_field]):,}"
            if trend_field == "transaction_count"
            else display_amount(float(last_point[trend_field]))
        )
        trend_figure.add_annotation(
            x=last_point["transaction_month"],
            y=last_point[trend_field],
            text=direct_label,
            showarrow=False,
            xanchor="left",
            xshift=10,
            font={"color": trend_color, "size": 12},
        )
    st.plotly_chart(
        trend_figure,
        width="stretch",
        config=PLOT_CONFIG,
        key=f"overview_{trend_field}",
    )
    if len(filters.currencies) != 1:
        data_note(
            "The value view adds EUR, GBP, AUD, and CAD as recorded. It supports aggregation analysis, but it is not a converted system value."
        )


if ui_state.active_view == "merchant":
    section_header(
        "Track merchant value through settlement",
        "Settlement records are tied back to the filtered transactions, so the ranking and status rail use the same date, currency, and category scope.",
        "Merchant flow",
    )
    settlement_summary = settlement_metrics(settlement_records)
    one_currency = len(filters.currencies) == 1
    amount_prefix = f"{filters.currencies[0]} " if one_currency else ""
    render_metric_strip(
        [
            {
                "label": "Settlement records",
                "value": f"{int(settlement_summary['settlement_count']):,}",
                "note": "Linked payout records",
                "tone": "cyan",
            },
            {
                "label": "Settled amount",
                "value": display_amount(
                    settlement_summary["settled_amount"],
                    currency_prefix=amount_prefix,
                ),
                "note": "Completed settlement value",
                "tone": "teal",
            },
            {
                "label": "Processing fees",
                "value": display_amount(
                    settlement_summary["processing_fees"],
                    currency_prefix=amount_prefix,
                ),
                "note": "Recorded processing fees",
                "tone": "amber",
            },
            {
                "label": "Delayed",
                "value": f"{int(settlement_summary['delayed_count']):,}",
                "note": "Awaiting completion",
                "tone": "coral",
            },
        ]
    )

    if settlement_records.empty:
        render_empty_state(
            "No settlements match this view.",
            "The selected transactions do not have linked settlement records.",
        )
    else:
        render_settlement_corridor(settlement_statuses(settlement_records))
        merchant_frame = merchant_performance(settlement_records)
        top_merchants = merchant_frame.head(12).sort_values(
            "settled_amount", ascending=True
        )
        merchant_figure = px.bar(
            top_merchants,
            x="settled_amount",
            y="merchant_name",
            orientation="h",
            color="category",
            color_discrete_map=CATEGORY_COLORS,
            custom_data=["category", "risk_tier", "settlement_count"],
        )
        merchant_figure.update_traces(
            marker_line_width=0,
            texttemplate="%{x:,.3s}",
            textposition="outside",
            textfont={"color": INK, "size": 11},
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>%{customdata[0]} · %{customdata[1]} risk"
                "<br>%{x:,.2f} nominal settled amount"
                "<br>%{customdata[2]:,.0f} settlements<extra></extra>"
            ),
        )
        merchant_layout = chart_layout(
            "Leading merchants by settled amount", 520
        )
        merchant_layout["margin"]["r"] = 78
        merchant_figure.update_layout(
            **merchant_layout,
            xaxis_title="Nominal settled amount",
            yaxis_title=None,
            bargap=0.28,
        )
        style_axes(merchant_figure)
        st.plotly_chart(
            merchant_figure,
            width="stretch",
            config=PLOT_CONFIG,
            key="merchant_ranking",
        )

        with st.expander("Open merchant settlement detail"):
            merchant_table = merchant_frame[
                [
                    "merchant_name",
                    "category",
                    "risk_tier",
                    "settlement_count",
                    "settled_amount",
                    "processing_fees",
                ]
            ].rename(
                columns={
                    "merchant_name": "Merchant",
                    "category": "Category",
                    "risk_tier": "Risk tier",
                    "settlement_count": "Settlements",
                    "settled_amount": "Settled amount",
                    "processing_fees": "Processing fees",
                }
            )
            st.dataframe(
                merchant_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Settled amount": st.column_config.NumberColumn(format="%.2f"),
                    "Processing fees": st.column_config.NumberColumn(format="%.2f"),
                },
            )
        if not one_currency:
            data_note(
                "Merchant and settlement values are ranked in nominal source-currency units. No exchange rate is applied."
            )


if ui_state.active_view == "risk":
    section_header(
        "See what entered review and what cleared",
        "Category rates show where flags appear in the generated records. The review flow then separates the recorded reasons into resolved and unresolved outcomes.",
        "Risk monitor",
    )
    risk_summary = risk_metrics(filtered_transactions, flag_records)
    render_metric_strip(
        [
            {
                "label": "Flags in view",
                "value": f"{int(risk_summary['flag_count']):,}",
                "note": "Review records in scope",
                "tone": "cyan",
            },
            {
                "label": "Resolved",
                "value": f"{int(risk_summary['resolved_count']):,}",
                "note": "Marked complete",
                "tone": "teal",
            },
            {
                "label": "Unresolved",
                "value": f"{int(risk_summary['unresolved_count']):,}",
                "note": "Still open",
                "tone": "coral",
            },
            {
                "label": "Resolution rate",
                "value": f"{risk_summary['resolution_rate']:.2f}%",
                "note": "Share of flags resolved",
                "tone": "amber",
            },
        ]
    )

    category_risk = risk_by_category(filtered_transactions, flag_records)
    if category_risk.empty:
        render_empty_state(
            "No merchant risk rates are available.",
            "This view needs transactions with a linked merchant category.",
        )
    else:
        risk_plot = category_risk.sort_values("flag_rate", ascending=True)
        risk_figure = px.bar(
            risk_plot,
            x="flag_rate",
            y="category",
            orientation="h",
            color="flag_rate",
            color_continuous_scale=[
                [0, "#1B5966"],
                [0.55, "#F4C86A"],
                [1, "#FF7E8F"],
            ],
            custom_data=["flagged_transactions", "total_transactions"],
        )
        risk_figure.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>%{x:.2f}% observed flag rate"
                "<br>%{customdata[0]:,.0f} flags across "
                "%{customdata[1]:,.0f} transactions<extra></extra>"
            ),
            marker_line_width=0,
            texttemplate="%{x:.2f}%",
            textposition="outside",
            textfont={"color": INK, "size": 11},
            cliponaxis=False,
        )
        risk_layout = chart_layout(
            "Observed flag rate by merchant category", 460
        )
        risk_layout["margin"]["r"] = 74
        risk_figure.update_layout(
            **risk_layout,
            xaxis_title="Flagged transactions (%)",
            yaxis_title=None,
            coloraxis_showscale=False,
        )
        style_axes(risk_figure)
        st.plotly_chart(
            risk_figure,
            width="stretch",
            config=PLOT_CONFIG,
            key="risk_category_rate",
        )

    review_flow = risk_review_flow(flag_records)
    if review_flow.empty:
        render_empty_state(
            "No fraud flags match this view.",
            "Widen the active filters to restore the review flow.",
        )
    else:
        reasons = sorted(review_flow["flag_reason"].unique().tolist())
        outcomes = ["Resolved", "Unresolved"]
        labels = reasons + outcomes
        label_index = {label: index for index, label in enumerate(labels)}
        source_indices = [
            label_index[row.flag_reason]
            for row in review_flow.itertuples(index=False)
        ]
        target_indices = [
            label_index[row.outcome]
            for row in review_flow.itertuples(index=False)
        ]
        values = [int(row.count) for row in review_flow.itertuples(index=False)]
        link_colors = [
            "rgba(66,232,180,0.20)"
            if row.outcome == "Resolved"
            else "rgba(255,126,143,0.24)"
            for row in review_flow.itertuples(index=False)
        ]
        link_hover_colors = [
            "rgba(138,246,199,0.62)"
            if row.outcome == "Resolved"
            else "rgba(255,117,111,0.66)"
            for row in review_flow.itertuples(index=False)
        ]
        sankey_figure = go.Figure(
            go.Sankey(
                arrangement="snap",
                node={
                    "pad": 18,
                    "thickness": 16,
                    "line": {"color": "rgba(145,183,207,0.25)", "width": 1},
                    "label": labels,
                    "color": [
                        "rgba(75,216,255,0.72)" for _ in reasons
                    ]
                    + [TEAL, CORAL],
                    "hovertemplate": "%{label}<br>%{value:,.0f} flags<extra></extra>",
                },
                link={
                    "source": source_indices,
                    "target": target_indices,
                    "value": values,
                    "color": link_colors,
                    "hovercolor": link_hover_colors,
                    "hovertemplate": (
                        "%{source.label} → %{target.label}"
                        "<br>%{value:,.0f} flags<extra></extra>"
                    ),
                },
            )
        )
        sankey_layout = chart_layout("Flag reason to review outcome", 500)
        sankey_layout["hoverlabel"] = {
            "bgcolor": "#0B1118",
            "bordercolor": "#68DCFF",
            "font": {"color": INK, "size": 12},
        }
        sankey_figure.update_layout(**sankey_layout)
        st.plotly_chart(
            sankey_figure,
            width="stretch",
            config=PLOT_CONFIG,
            key="risk_review_flow",
        )

        with st.expander("Open review-flow data table"):
            review_flow_table = review_flow.rename(
                columns={
                    "flag_reason": "Flag reason",
                    "outcome": "Review outcome",
                    "count": "Flags",
                }
            )
            st.table(
                review_flow_table,
                width="stretch",
                hide_index=True,
                border="horizontal",
            )

        with st.expander("Open category risk detail"):
            risk_table = category_risk.rename(
                columns={
                    "category": "Merchant category",
                    "total_transactions": "Transactions",
                    "flagged_transactions": "Flags",
                    "flag_rate": "Observed flag rate",
                }
            )
            st.dataframe(
                risk_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Observed flag rate": st.column_config.NumberColumn(
                        format="%.2f%%"
                    )
                },
            )

    data_note(
        "Fraud flags were randomly sampled when the synthetic dataset was generated. These rates describe the sample; they are not a fraud model or a production risk score.",
        "coral",
    )


if ui_state.active_view == "retention":
    section_header(
        "Read customer return patterns without filling the future",
        "Each cell is the share of a joining cohort with at least one completed payment in that month. Periods beyond the dataset window stay blank.",
        "Customer retention",
    )
    cohort_min = customers["join_date"].min().date()
    cohort_max = customers["join_date"].max().date()
    cohort_dates = st.date_input(
        "Cohort join window",
        value=(cohort_min, cohort_max),
        min_value=cohort_min,
        max_value=cohort_max,
        key="pay_cohort_range",
    )
    if isinstance(cohort_dates, tuple) and len(cohort_dates) == 2:
        cohort_start, cohort_end = cohort_dates
    else:
        cohort_start = cohort_end = cohort_dates
    retention_frame = cohort_retention(
        customers,
        accounts,
        transactions,
        pd.Timestamp(cohort_start).date(),
        pd.Timestamp(cohort_end).date(),
    )

    if retention_frame.empty:
        render_empty_state(
            "No customer cohorts match this window.",
            "Choose a wider join-date range to restore the heatmap.",
        )
    else:
        cohort_count = retention_frame["cohort_month"].nunique()
        cohort_customers = (
            retention_frame[["cohort_month", "cohort_size"]]
            .drop_duplicates()["cohort_size"]
            .sum()
        )
        month_one = retention_frame[
            retention_frame["months_active_offset"].eq(1)
            & retention_frame["observable"]
        ]["retention_rate"]
        median_month_one = float(month_one.median()) if not month_one.empty else 0.0

        render_metric_strip(
            [
                {
                    "label": "Cohorts observed",
                    "value": f"{cohort_count:,}",
                    "note": "Monthly join cohorts",
                    "tone": "violet",
                },
                {
                    "label": "Customers in cohorts",
                    "value": f"{int(cohort_customers):,}",
                    "note": "Customers inside the selected join window",
                    "tone": "cyan",
                },
                {
                    "label": "Median month 1 return",
                    "value": f"{median_month_one:.1f}%",
                    "note": "Median observed return rate",
                    "tone": "teal",
                },
            ]
        )

        retention_frame = retention_frame.copy()
        retention_frame["cohort_label"] = retention_frame[
            "cohort_month"
        ].dt.strftime("%b %Y")
        heatmap_values = retention_frame.pivot(
            index="cohort_label",
            columns="months_active_offset",
            values="retention_rate",
        )
        heatmap_values = heatmap_values.reindex(
            retention_frame[
                ["cohort_month", "cohort_label"]
            ]
            .drop_duplicates()
            .sort_values("cohort_month")["cohort_label"]
        )
        show_cell_text = cohort_count <= 20
        heatmap = go.Figure(
            go.Heatmap(
                z=heatmap_values.values,
                x=[f"Month {int(column)}" for column in heatmap_values.columns],
                y=heatmap_values.index,
                colorscale=[
                    [0.0, "#101824"],
                    [0.22, "#25234A"],
                    [0.48, "#5546A3"],
                    [0.72, "#4B9FC0"],
                    [1.0, "#42E8B4"],
                ],
                zmin=0,
                zmax=100,
                colorbar={
                    "title": {"text": "Return %", "side": "right"},
                    "thickness": 10,
                    "outlinewidth": 0,
                    "tickfont": {"color": MUTED},
                },
                text=heatmap_values.values if show_cell_text else None,
                texttemplate="%{text:.0f}%" if show_cell_text else None,
                textfont={"size": 11, "color": "#F5F9FC"},
                hovertemplate=(
                    "<b>%{y}</b><br>%{x}<br>%{z:.2f}% active<extra></extra>"
                ),
                hoverongaps=False,
                xgap=2,
                ygap=2,
            )
        )
        heatmap_height = max(500, min(840, cohort_count * 22 + 190))
        heatmap_layout = chart_layout("Cohort activity retention", heatmap_height)
        heatmap_layout["hoverlabel"] = {
            "bgcolor": "#0B1118",
            "bordercolor": "#A390FF",
            "font": {"color": INK, "size": 12},
        }
        heatmap.update_layout(
            **heatmap_layout,
            xaxis_title=None,
            yaxis_title="Joining cohort",
        )
        heatmap.update_xaxes(
            side="top",
            gridcolor="rgba(145,183,207,0.08)",
            tickangle=0,
        )
        heatmap.update_yaxes(
            autorange="reversed",
            gridcolor="rgba(145,183,207,0.08)",
        )
        st.plotly_chart(
            heatmap,
            width="stretch",
            config=PLOT_CONFIG,
            key="retention_heatmap",
        )
        with st.expander("Open retention data table"):
            retention_table = retention_frame[
                [
                    "cohort_label",
                    "months_active_offset",
                    "cohort_size",
                    "active_customers",
                    "retention_rate",
                    "observable",
                ]
            ].rename(
                columns={
                    "cohort_label": "Joining cohort",
                    "months_active_offset": "Active month",
                    "cohort_size": "Cohort size",
                    "active_customers": "Active customers",
                    "retention_rate": "Retention rate",
                    "observable": "Observable",
                }
            )
            retention_table["Retention rate"] = retention_table[
                "Retention rate"
            ].map(
                lambda value: (
                    "Not observable"
                    if pd.isna(value)
                    else f"{float(value):.2f}%"
                )
            )
            retention_table["Observable"] = retention_table[
                "Observable"
            ].map({True: "Yes", False: "No"})
            st.table(
                retention_table,
                width="stretch",
                height=560,
                hide_index=True,
                border="horizontal",
            )
        data_note(
            "Blank cells are outside the observable dataset window. A visible 0% cell is an observed month in which no customer from that cohort completed a payment."
        )


if ui_state.active_view == "model":
    section_header(
        "Trace the data before reading the metrics",
        "The model view shows the relationships used by the dashboard and keeps the important limitations close to the analysis.",
        "Data model and method",
    )
    render_data_model(scope)
    with st.expander("Read data and calculation notes"):
        render_method_cards()
        data_note(
            f"The transaction window runs from {first_date_label} to {last_date_label}. "
            f"The current source is {source_label.lower()}, and the dashboard cache can retain a loaded source for up to ten minutes."
        )


render_footer()
mount_page_motion()
