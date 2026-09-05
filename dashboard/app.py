"""Settlement Operations Workbench.

The application is a task-oriented reader for the repository's canonical SQL
marts. Business rules stay in SQL; Pandas only formats and presents returned
rows.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from html import escape
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode

import pandas as pd
import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from dashboard.workbench_ui import (  # noqa: E402
    DEFAULT_VIEW,
    PRIMARY_REASON_ORDER,
    VALID_VIEWS,
    VIEW_LABELS,
    apply_workbench_theme,
    default_scenario,
    display_frame,
    first_present,
    format_count,
    format_minor_units,
    format_percent,
    normalise_reasons,
    parse_date,
    reason_label,
    reason_tags,
    render_disclosure,
    render_header,
    render_kpi,
    render_lifecycle,
    render_lineage_diagram,
    render_section,
    scalar,
    scenario_options,
    trace_money_table,
)

try:
    from scripts.analytics_engine import AnalyticsEngine

    ENGINE_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - actionable runtime state
    AnalyticsEngine = None  # type: ignore[assignment,misc]
    ENGINE_IMPORT_ERROR = exc


BRAND_ICON = str(
    PROJECT_DIR
    / "dashboard"
    / "static"
    / "brand"
    / "payment-observatory-mark-compact.svg"
)
CASE_STUDY_URL = os.getenv(
    "CASE_STUDY_URL",
    "https://abinashprasana.github.io/payments-analytics/",
).strip()
REPOSITORY_URL = os.getenv(
    "REPOSITORY_URL",
    "https://github.com/abinashprasana/payments-analytics",
).strip()

st.set_page_config(
    page_title="Settlement Operations Workbench",
    page_icon=BRAND_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_workbench_theme()


def query_value(name: str, default: str = "") -> str:
    """Read one query-string value across Streamlit representations."""

    value = st.query_params.get(name, default)
    if isinstance(value, list):
        value = value[-1] if value else default
    return str(value).strip()


def update_location(**changes: str | None) -> None:
    """Update only the documented workbench deep-link parameters."""

    for name, value in changes.items():
        if name not in {"view", "scenario", "payment_id"}:
            continue
        if value is None or value == "":
            if name in st.query_params:
                del st.query_params[name]
        else:
            st.query_params[name] = value


def navigate_to_view(view: str, payment_id: str | None = None) -> None:
    """Keep the navigation widget and documented deep link in sync."""

    st.session_state["workbench_navigation"] = view
    update_location(view=view, payment_id=payment_id)


def navigation_changed() -> None:
    """Mirror a user-selected radio view into the deep-link contract."""

    view = str(st.session_state.get("workbench_navigation", DEFAULT_VIEW))
    payment_id = query_value("payment_id") if view == "trace" else None
    update_location(view=view, payment_id=payment_id)


def scenario_changed() -> None:
    """Make the scenario selector update the documented deep link."""

    scenario = str(st.session_state.get("workbench_scenario", ""))
    update_location(scenario=scenario, payment_id=None)


@st.cache_resource(show_spinner=False)
def get_engine() -> Any:
    """Build the cached in-memory snapshot and canonical SQL marts."""

    if AnalyticsEngine is None:
        raise RuntimeError("The canonical analytics engine could not be imported.")
    return AnalyticsEngine(repo_root=None)


def engine_metadata(engine: Any) -> dict[str, Any]:
    """Read non-analytical build metadata exposed by the engine."""

    metadata: dict[str, Any] = {}
    for attribute_name in ("build_metadata", "metadata"):
        attribute = getattr(engine, attribute_name, None)
        if callable(attribute):
            try:
                attribute = attribute()
            except Exception:
                attribute = None
        if isinstance(attribute, Mapping):
            metadata.update(attribute)

    metadata.setdefault("dataset_version", os.getenv("DATASET_VERSION", "v2"))
    metadata.setdefault(
        "build_sha", os.getenv("GITHUB_SHA", os.getenv("BUILD_SHA", "local"))
    )
    metadata.setdefault("runtime_mode", "DuckDB · in-memory repository snapshot")
    return metadata


def run_query(
    engine: Any,
    query_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    show_error: bool = True,
) -> pd.DataFrame:
    """Execute a registered query and expose a safe, useful error state."""

    clean_params = {
        key: value
        for key, value in dict(params or {}).items()
        if value is not None and value != ""
    }
    try:
        result = engine.query(query_id, clean_params)
    except Exception as exc:  # pragma: no cover - environment-dependent
        if show_error:
            st.error(
                f"The `{query_id}` SQL result is unavailable. "
                "The source snapshot was not changed."
            )
            with st.expander("Technical detail"):
                st.code(f"{type(exc).__name__}: {exc}", language="text")
        return pd.DataFrame()
    if not isinstance(result, pd.DataFrame):
        if show_error:
            st.error(f"The `{query_id}` query returned an unsupported result type.")
        return pd.DataFrame()
    return result.copy()


def canonical_view() -> str:
    requested = query_value("view", DEFAULT_VIEW).lower()
    selected = requested if requested in VALID_VIEWS else DEFAULT_VIEW
    if requested != selected or query_value("view") != selected:
        update_location(view=selected, payment_id=None)
    return selected


def frame_date_bounds(frame: pd.DataFrame) -> tuple[date | None, date | None]:
    date_column = next(
        (
            name
            for name in ("close_date", "transaction_date", "date")
            if name in frame.columns
        ),
        None,
    )
    if date_column is None or frame.empty:
        return None, None
    values = pd.to_datetime(frame[date_column], errors="coerce").dropna()
    if values.empty:
        return None, None
    return values.min().date(), values.max().date()


def frame_currencies(frame: pd.DataFrame) -> list[str]:
    if "currency" not in frame.columns:
        return []
    return sorted(frame["currency"].dropna().astype(str).unique().tolist())


def filter_params(
    scenario: str,
    currency: str | None,
    start_date: date | None,
    end_date: date | None,
    *,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "currency": currency,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "as_of_date": as_of_date.isoformat() if as_of_date else None,
    }


def latest_close_row(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    if "close_date" in frame.columns:
        ordered = frame.assign(
            _display_date=pd.to_datetime(frame["close_date"], errors="coerce")
        ).sort_values("_display_date", kind="stable")
        return ordered.drop(columns="_display_date").iloc[-1].to_dict()
    return frame.iloc[-1].to_dict()


def render_close_view(
    engine: Any,
    params: Mapping[str, Any],
    selected_currency: str | None,
) -> None:
    render_section(
        "Close health by currency",
        "Start with the unhealthy processing date. Coverage, overdue value, fee "
        "delta, and reasons all come from mart_daily_close.",
        "Step 1 · Identify",
    )
    close_frame = run_query(engine, "close_summary", params)
    if close_frame.empty:
        st.info("No daily-close rows match this scenario and scope.")
        return

    if "close_date" in close_frame.columns:
        close_frame = close_frame.sort_values("close_date", kind="stable")
    row = latest_close_row(close_frame)
    currency = str(first_present(row, ("currency",), selected_currency or ""))
    close_date_value = first_present(row, ("close_date", "date"), "selected scope")
    parsed_close_date = parse_date(close_date_value)
    close_date = (
        parsed_close_date.isoformat() if parsed_close_date else str(close_date_value)
    )
    exception_count = int(first_present(row, ("exception_count",), 0))
    matched_count = first_present(row, ("matched_count", "reconciled_count"), 0)
    eligible_count = first_present(row, ("eligible_count", "purchase_count"), 0)
    coverage = first_present(
        row, ("coverage_rate", "settlement_coverage_rate"), 0
    )
    overdue = first_present(
        row, ("overdue_minor_units", "overdue_value_minor_units"), 0
    )
    fee_delta = first_present(row, ("fee_delta_minor_units",), 0)

    st.caption(f"Closing row: {close_date} · {currency or 'currency not returned'}")
    columns = st.columns(4)
    with columns[0]:
        render_kpi(
            "Settlement coverage",
            format_percent(coverage),
            f"{format_count(matched_count)} of {format_count(eligible_count)} eligible purchases",
            "good" if exception_count == 0 else "warning",
        )
    with columns[1]:
        render_kpi(
            "Exceptions",
            format_count(exception_count),
            "Payments with one or more SQL exception flags",
            "good" if exception_count == 0 else "critical",
        )
    with columns[2]:
        render_kpi(
            "Overdue value",
            format_minor_units(overdue, currency),
            "Expected gross value past the applicable SLA",
            "good" if int(overdue or 0) == 0 else "critical",
        )
    with columns[3]:
        render_kpi(
            "Fee delta",
            format_minor_units(fee_delta, currency),
            "Recorded fee minus the effective merchant term",
            "good" if int(fee_delta or 0) == 0 else "warning",
        )

    if exception_count:
        st.warning(
            "This close needs investigation. Open Exceptions to isolate the "
            "payments behind the SQL flags."
        )
    else:
        st.success("No exception flags were returned for this closing row.")

    composition_columns = {
        "missing_count": "Missing",
        "currency_mismatch_count": "Currency",
        "amount_mismatch_count": "Amount",
        "fee_mismatch_count": "Fee",
        "late_count": "Late",
        "disputed_count": "Disputed",
    }
    composition = pd.DataFrame(
        {
            "Reason": [
                label
                for column, label in composition_columns.items()
                if column in row
            ],
            "Payments": [
                int(scalar(row.get(column), 0))
                for column in composition_columns
                if column in row
            ],
        }
    )
    history_column, reason_column = st.columns([1.45, 1])
    with history_column:
        st.subheader("Daily coverage history")
        if {"close_date", "coverage_rate"}.issubset(close_frame.columns):
            history = close_frame[["close_date", "coverage_rate"]].copy()
            history["close_date"] = pd.to_datetime(
                history["close_date"], errors="coerce"
            )
            values = pd.to_numeric(history["coverage_rate"], errors="coerce")
            history["coverage_rate"] = values.where(
                values.abs() > 1, values * 100
            )
            st.line_chart(
                history.set_index("close_date"),
                y="coverage_rate",
                y_label="Coverage (%)",
                x_label="Processing date",
                color="#73d7f2",
            )
        else:
            st.info("Coverage history is not present in this query result.")
    with reason_column:
        st.subheader("Exception composition")
        if not composition.empty:
            st.bar_chart(
                composition.set_index("Reason"),
                y="Payments",
                y_label="Payments",
                x_label="Reason",
                color="#f2c670",
            )
        else:
            st.info("Exception count columns are not present in this result.")

    with st.expander("Open daily-close evidence table"):
        st.dataframe(close_frame, width="stretch", hide_index=True)
    with st.expander("Open metric contract and SQL lineage"):
        st.markdown(
            "**Query ID:** `close_summary`  \n"
            "**Source model:** `mart_daily_close`  \n"
            "**Grain:** processing date × currency"
        )
        st.code(
            "population = completed merchant purchases\n"
            "match = settlement present\n"
            "        AND settlement.currency = payment.currency\n"
            "        AND abs(gross - settled_amount - processing_fee) <= 0.01\n"
            "sla_breach = missing past SLA OR actual settlement later than SLA",
            language="text",
        )

    st.button(
        "Investigate this close",
        type="primary",
        width="stretch",
        on_click=navigate_to_view,
        args=("exceptions",),
        key="investigate_close",
    )


def queue_reason_set(frame: pd.DataFrame) -> list[str]:
    reasons: set[str] = set()
    if "exception_reasons" in frame.columns:
        for value in frame["exception_reasons"].tolist():
            reasons.update(normalise_reasons(value))
    elif "primary_reason" in frame.columns:
        reasons.update(frame["primary_reason"].dropna().astype(str).tolist())
    order = {reason: index for index, reason in enumerate(PRIMARY_REASON_ORDER)}
    return sorted(reasons, key=lambda reason: order.get(reason, 99))


def session_reviews() -> dict[str, dict[str, str]]:
    if "settlement_review_state" not in st.session_state:
        st.session_state["settlement_review_state"] = {}
    return st.session_state["settlement_review_state"]


def clear_session_review(payment_id: str) -> None:
    """Clear one review and its widget drafts before the app reruns."""

    session_reviews().pop(payment_id, None)
    for widget_key in list(st.session_state):
        if (
            widget_key.startswith(("review_status_", "review_note_"))
            and widget_key.endswith(f"_{payment_id}")
        ):
            del st.session_state[widget_key]


def reset_session_reviews() -> None:
    """Reset all browser-session review data and draft widgets."""

    st.session_state["settlement_review_state"] = {}
    for widget_key in list(st.session_state):
        if widget_key.startswith(("review_status_", "review_note_")):
            del st.session_state[widget_key]
    # A fresh widget identity prevents the browser from replaying the old form
    # value into the rerun after the session data has been cleared.
    st.session_state["review_widget_generation"] = (
        int(st.session_state.get("review_widget_generation", 0)) + 1
    )
    st.session_state["review_reset_notice"] = True


def render_review_panel(payment_id: str) -> None:
    reviews = session_reviews()
    existing = reviews.get(payment_id, {})
    generation = int(st.session_state.get("review_widget_generation", 0))
    status_key = f"review_status_{generation}_{payment_id}"
    note_key = f"review_note_{generation}_{payment_id}"
    render_disclosure(
        "Review status and notes live only in this browser session. They never "
        "update the repository snapshot or simulate a real payment operation."
    )
    with st.form(f"review_{payment_id}", border=True):
        status_options = [
            "Unreviewed",
            "Investigating",
            "Needs evidence",
            "Resolved in demo",
        ]
        current_status = existing.get("status", status_options[0])
        status = st.selectbox(
            "Session review status",
            status_options,
            index=(
                status_options.index(current_status)
                if current_status in status_options
                else 0
            ),
            key=status_key,
        )
        notes = st.text_area(
            "Session note",
            value=existing.get("notes", ""),
            placeholder="Record what you checked; this clears when the session resets.",
            max_chars=600,
            key=note_key,
        )
        if st.form_submit_button("Save session note", type="primary"):
            reviews[payment_id] = {"status": status, "notes": notes.strip()}
            st.success("Saved for this session only.")
    if payment_id in reviews:
        st.button(
            "Clear this session review",
            key=f"clear_{payment_id}",
            on_click=clear_session_review,
            args=(payment_id,),
        )


def apply_queue_display_filters(
    frame: pd.DataFrame,
    reasons: list[str],
    merchant_search: str,
) -> pd.DataFrame:
    """Apply presentation filters to already classified SQL rows."""

    filtered = frame.copy()
    if reasons:
        selected = set(reasons)
        if "exception_reasons" in filtered.columns:
            mask = filtered["exception_reasons"].map(
                lambda value: bool(selected.intersection(normalise_reasons(value)))
            )
            filtered = filtered.loc[mask]
        elif "primary_reason" in filtered.columns:
            filtered = filtered.loc[filtered["primary_reason"].isin(reasons)]
    search = merchant_search.strip().casefold()
    if search:
        search_columns = [
            column
            for column in ("merchant_name", "merchant_category", "payment_id")
            if column in filtered.columns
        ]
        if search_columns:
            mask = pd.Series(False, index=filtered.index)
            for column in search_columns:
                mask |= filtered[column].astype(str).str.casefold().str.contains(
                    search, regex=False
                )
            filtered = filtered.loc[mask]
    return filtered


def sort_queue_for_display(frame: pd.DataFrame, choice: str) -> pd.DataFrame:
    """Sort rows already classified by SQL without recomputing priority."""

    sort_contract = {
        "Oldest purchase first": ("transaction_date", True),
        "Most overdue first": ("days_overdue", False),
        "Largest gross first": ("gross_minor_units", False),
    }
    column_and_direction = sort_contract.get(choice)
    if column_and_direction is None:
        return frame
    column, ascending = column_and_direction
    if column not in frame.columns:
        return frame
    return frame.sort_values(
        column,
        ascending=ascending,
        kind="stable",
        na_position="last",
    )


def render_exceptions_view(
    engine: Any,
    params: Mapping[str, Any],
    scenario_id: str,
) -> None:
    render_section(
        "Exception queue",
        "Narrow SQL-classified exceptions, inspect every reason attached to a "
        "payment, and export the evidence without altering the snapshot.",
        "Step 2 · Isolate",
    )
    queue = run_query(engine, "exception_queue", params)
    if queue.empty:
        st.success("No exception rows match this scenario and scope.")
        return

    all_reasons = queue_reason_set(queue)
    reason_filter_key = f"exception_reason_filter_{scenario_id}"
    stored_reasons = st.session_state.get(reason_filter_key, [])
    if any(reason not in all_reasons for reason in stored_reasons):
        st.session_state[reason_filter_key] = [
            reason for reason in stored_reasons if reason in all_reasons
        ]
    filter_columns = st.columns([1.2, 1, 1])
    with filter_columns[0]:
        selected_reasons = st.multiselect(
            "Exception reasons",
            options=all_reasons,
            format_func=reason_label,
            placeholder="All reasons",
            key=reason_filter_key,
        )
    with filter_columns[1]:
        merchant_search = st.text_input(
            "Merchant or payment",
            placeholder="Search returned rows",
            key=f"exception_text_filter_{scenario_id}",
        )
    with filter_columns[2]:
        sort_choice = st.selectbox(
            "Sort queue by",
            (
                "SQL priority",
                "Oldest purchase first",
                "Most overdue first",
                "Largest gross first",
            ),
            key=f"exception_sort_{scenario_id}",
        )
    filtered = apply_queue_display_filters(
        queue, selected_reasons, merchant_search
    )
    filtered = sort_queue_for_display(filtered, sort_choice)
    st.caption(
        f"Showing {len(filtered):,} of {len(queue):,} SQL-classified payments."
    )

    if filtered.empty:
        st.info("No queue rows match the display filters. Clear them to continue.")
        return

    evidence = filtered.copy()
    if "exception_reasons" in evidence.columns:
        evidence["exception_reasons"] = evidence["exception_reasons"].map(
            lambda value: " · ".join(
                reason_label(reason) for reason in normalise_reasons(value)
            )
        )
    if "primary_reason" in evidence.columns:
        evidence["primary_reason"] = evidence["primary_reason"].map(
            lambda value: reason_label(str(scalar(value, "")))
        )
    if "gross_minor_units" in evidence.columns:
        evidence["gross"] = evidence.apply(
            lambda row: format_minor_units(
                row["gross_minor_units"], scalar(row.get("currency"), "")
            ),
            axis=1,
        )

    shown = display_frame(
        evidence,
        (
            "payment_id",
            "transaction_date",
            "currency",
            "gross",
            "merchant_name",
            "merchant_category",
            "primary_reason",
            "exception_reasons",
            "days_overdue",
            "expected_settlement_date",
        ),
    )
    st.dataframe(
        shown,
        width="stretch",
        hide_index=True,
        column_config={
            "payment_id": st.column_config.TextColumn("Payment ID"),
            "transaction_date": st.column_config.DateColumn("Purchase date"),
            "gross": st.column_config.TextColumn("Gross"),
            "merchant_name": st.column_config.TextColumn("Merchant"),
            "merchant_category": st.column_config.TextColumn("Category"),
            "primary_reason": st.column_config.TextColumn("Primary reason"),
            "exception_reasons": st.column_config.TextColumn(
                "All reasons", width="large"
            ),
            "days_overdue": st.column_config.NumberColumn(
                "Days overdue", format="%d"
            ),
            "expected_settlement_date": st.column_config.DateColumn(
                "Expected by"
            ),
        },
    )

    if "payment_id" not in filtered.columns:
        st.error("The exception queue did not return a payment_id column.")
        return
    payment_ids = filtered["payment_id"].dropna().astype(str).tolist()
    payment_selector_key = f"queue_payment_to_inspect_{scenario_id}"
    if st.session_state.get(payment_selector_key) not in payment_ids:
        st.session_state[payment_selector_key] = payment_ids[0]
    action_columns = st.columns([1.25, 1, 1])
    with action_columns[0]:
        chosen_payment = st.selectbox(
            "Payment to inspect",
            payment_ids,
            key=payment_selector_key,
        )
    with action_columns[1]:
        st.write("")
        st.write("")
        st.button(
            "Open payment trace",
            type="primary",
            width="stretch",
            on_click=navigate_to_view,
            args=("trace", chosen_payment),
            key=f"open_payment_trace_{scenario_id}",
        )
    with action_columns[2]:
        st.write("")
        st.write("")
        st.download_button(
            "Export filtered evidence",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"settlement-exceptions-{scenario_id}.csv",
            mime="text/csv",
            width="stretch",
            key=f"export_exception_evidence_{scenario_id}",
        )

    with st.expander("Session-only review controls"):
        render_review_panel(chosen_payment)

    with st.expander("Open queue contract and SQL lineage"):
        st.markdown(
            "**Query ID:** `exception_queue`  \n"
            "**Source model:** `mart_exception_queue`  \n"
            "**Grain:** one completed merchant purchase with at least one flag"
        )
        st.code(
            "independent flags = missing, currency, amount, fee, late, disputed\n"
            "primary order = missing > currency > amount > fee > late > disputed",
            language="text",
        )


def trace_payment_id(
    engine: Any,
    params: Mapping[str, Any],
    requested: str,
) -> tuple[str, pd.DataFrame]:
    if requested:
        trace = run_query(
            engine,
            "payment_trace",
            {**params, "payment_id": requested},
            show_error=False,
        )
        if not trace.empty:
            return requested, trace

    queue = run_query(engine, "exception_queue", params, show_error=False)
    if queue.empty or "payment_id" not in queue.columns:
        return requested, pd.DataFrame()
    fallback = str(queue["payment_id"].dropna().astype(str).iloc[0])
    trace = run_query(
        engine,
        "payment_trace",
        {**params, "payment_id": fallback},
        show_error=False,
    )
    return fallback, trace


def flag_explanations(reasons: list[str]) -> list[str]:
    explanations = {
        "missing": "No settlement evidence exists after the term-based expected date.",
        "currency_mismatch": "Settlement and purchase currencies differ.",
        "amount_mismatch": "Gross does not equal settled amount plus recorded fee within 0.01.",
        "fee_mismatch": "Recorded fee differs from the effective merchant fee term.",
        "late": "Actual settlement date exceeds the effective merchant SLA.",
        "disputed": "The purchase has linked dispute evidence in the source snapshot.",
    }
    return [explanations.get(reason, reason_label(reason)) for reason in reasons]


def render_trace_view(
    engine: Any,
    params: Mapping[str, Any],
    requested_payment_id: str,
) -> None:
    render_section(
        "Payment trace",
        "Follow one completed merchant purchase through its effective term, "
        "expected settlement, recorded evidence, and every SQL flag.",
        "Step 3 · Explain",
    )
    payment_id, trace = trace_payment_id(engine, params, requested_payment_id)
    if trace.empty:
        st.info("No traceable exception is available for this scenario and scope.")
        return
    if payment_id != requested_payment_id:
        if requested_payment_id:
            st.warning(
                f"Payment `{requested_payment_id}` is not valid in this scenario. "
                f"Showing `{payment_id}` instead."
            )
        update_location(payment_id=payment_id)

    row = trace.iloc[0].to_dict()
    reasons = normalise_reasons(
        first_present(row, ("exception_reasons",)), row
    )
    primary = str(
        first_present(
            row, ("primary_reason",), reasons[0] if reasons else "matched"
        )
    )

    st.markdown(f"### `{escape(payment_id)}`")
    st.markdown(reason_tags(reasons or [primary]), unsafe_allow_html=True)
    render_lineage_diagram(row)
    identity = st.columns(4)
    identity[0].metric(
        "Merchant", str(first_present(row, ("merchant_name",), "Not linked"))
    )
    identity[1].metric(
        "Category",
        str(first_present(row, ("merchant_category", "category"), "Not linked")),
    )
    identity[2].metric(
        "Purchase date",
        str(first_present(row, ("transaction_date", "purchase_date"), "Unknown")),
    )
    identity[3].metric("Primary label", reason_label(primary))

    money_column, term_column = st.columns([1.15, 1])
    with money_column:
        st.subheader("Expected versus recorded")
        money = trace_money_table(row)
        if money.empty:
            st.info("Money fields are not present in the trace result.")
        else:
            st.table(money)
        transaction_currency = first_present(
            row, ("transaction_currency", "currency"), "—"
        )
        settlement_currency = first_present(
            row, ("settlement_currency",), "Missing"
        )
        st.caption(
            f"Purchase currency: {transaction_currency} · "
            f"Settlement currency: {settlement_currency}"
        )
    with term_column:
        st.subheader("Applicable merchant term")
        term_rows = {
            "Effective from": first_present(
                row,
                ("term_valid_from", "valid_from", "effective_from"),
                "—",
            ),
            "Effective to": first_present(
                row,
                ("term_valid_to", "valid_to", "effective_to"),
                "Open-ended",
            ),
            "Fee rate": f"{first_present(row, ('fee_rate_bps',), '—')} bps",
            "Settlement SLA": (
                f"{first_present(row, ('settlement_sla_days', 'sla_days'), '—')} days"
            ),
            "Expected by": first_present(
                row, ("expected_settlement_date",), "—"
            ),
            "Actually settled": first_present(
                row,
                ("actual_settlement_date", "settlement_date"),
                "Missing",
            ),
        }
        st.dataframe(
            pd.DataFrame(
                {
                    "Field": term_rows.keys(),
                    "Value": [str(value) for value in term_rows.values()],
                }
            ),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Recorded evidence")
    evidence_rows = {
        "Transaction ID": first_present(row, ("transaction_id",), "—"),
        "Account ID": first_present(row, ("account_id",), "—"),
        "Settlement ID": first_present(row, ("settlement_id",), "Missing"),
        "Settlement status": first_present(
            row, ("settlement_status",), "Missing"
        ),
        "Settlement currency": first_present(
            row, ("settlement_currency",), "Missing"
        ),
        "Linked review reason": first_present(
            row, ("fraud_reason",), "None linked"
        ),
    }
    st.dataframe(
        pd.DataFrame(
            {
                "Field": evidence_rows.keys(),
                "Value": [str(value) for value in evidence_rows.values()],
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Why SQL flagged it")
    if reasons:
        for explanation in flag_explanations(reasons):
            st.markdown(f"- {explanation}")
    else:
        st.success("This payment satisfies the settlement match contract.")
    lineage_query = first_present(
        row,
        ("lineage_query_id", "query_id", "model_query_id"),
        "payment_trace",
    )
    lineage_model = first_present(
        row,
        ("lineage_model", "sql_model"),
        "int_settlement_reconciliation",
    )
    st.markdown(
        f'<div class="wb-query"><strong>Query ID:</strong> '
        f"<code>{escape(str(lineage_query))}</code><br>"
        f'<strong>Rule model:</strong> <code>{escape(str(lineage_model))}</code><br>'
        "Flags are independent booleans. The primary label only supplies stable "
        "queue order: missing → currency → amount → fee → late → disputed.</div>",
        unsafe_allow_html=True,
    )

    with st.expander("Open complete trace row"):
        st.dataframe(trace, width="stretch", hide_index=True)
    with st.expander("Session-only review controls", expanded=True):
        render_review_panel(payment_id)

    navigation = st.columns(2)
    with navigation[0]:
        st.button(
            "Back to exception queue",
            width="stretch",
            on_click=navigate_to_view,
            args=("exceptions",),
        )
    with navigation[1]:
        st.link_button(
            "Read the walkthrough",
            CASE_STUDY_URL,
            width="stretch",
        )


def render_catalog_view(engine: Any, metadata: Mapping[str, Any]) -> None:
    render_section(
        "Metric and model catalog",
        "Audit the contract behind every public number: population, grain, "
        "currency boundary, SQL model, quality status, and build identity.",
        "Reference · Verify",
    )
    render_disclosure(
        "This is a wholly synthetic demonstration snapshot. It contains no real "
        "payments, credentials, personal data, operational write path, fraud model, "
        "or business-impact claim."
    )

    st.subheader("Build identity")
    metadata_rows = pd.DataFrame(
        {
            "Field": [
                "Dataset version",
                "As-of date",
                "Commit SHA",
                "Runtime mode",
                "Snapshot",
            ],
            "Value": [
                first_present(
                    metadata, ("dataset_version", "version"), "Unavailable"
                ),
                first_present(metadata, ("as_of_date", "as_of"), "Unavailable"),
                first_present(
                    metadata,
                    ("build_sha", "commit_sha", "sha"),
                    "local",
                ),
                first_present(
                    metadata,
                    ("runtime_mode", "runtime"),
                    "DuckDB in-memory",
                ),
                "Synthetic demo snapshot",
            ],
        }
    )
    st.dataframe(metadata_rows, width="stretch", hide_index=True)

    st.subheader("Metric contracts")
    metrics = run_query(engine, "catalog_metrics", {})
    if metrics.empty:
        st.info("Metric catalog rows are unavailable.")
    else:
        st.dataframe(metrics, width="stretch", hide_index=True)

    st.subheader("Canonical model chain")
    grains = pd.DataFrame(
        [
            ("int_expected_settlements", "one eligible completed merchant purchase"),
            (
                "int_settlement_reconciliation",
                "one eligible purchase with independent flags",
            ),
            ("mart_daily_close", "processing date × currency"),
            ("mart_exception_queue", "payment"),
            ("mart_merchant_health", "merchant × date × currency"),
            ("mart_payment_trace", "payment"),
        ],
        columns=["SQL model", "Grain"],
    )
    st.table(grains)

    st.subheader("Data-quality results")
    quality = run_query(engine, "quality_results", {})
    if quality.empty:
        st.info("Data-quality result rows are unavailable.")
    else:
        st.dataframe(quality, width="stretch", hide_index=True)

    st.info(
        "Streamlit Community Cloud may ask you to wake this free application after "
        "inactivity. Waking restores the same repository snapshot; it is not an incident."
    )
    links = st.columns(2)
    links[0].link_button("Read the walkthrough", CASE_STUDY_URL, width="stretch")
    links[1].link_button(
        "Inspect the SQL repository", REPOSITORY_URL, width="stretch"
    )


if ENGINE_IMPORT_ERROR is not None:
    st.error(
        "The workbench cannot start because the canonical analytics engine is unavailable."
    )
    st.code(
        f"{type(ENGINE_IMPORT_ERROR).__name__}: {ENGINE_IMPORT_ERROR}",
        language="text",
    )
    st.stop()

try:
    with st.spinner("Building the synthetic settlement snapshot"):
        analytics = get_engine()
except Exception as exc:  # pragma: no cover - deployment-dependent
    st.error(
        "The workbench could not build its in-memory SQL snapshot. "
        "No source data was changed."
    )
    st.code(f"{type(exc).__name__}: {exc}", language="text")
    st.stop()

registry = run_query(analytics, "scenario_options", {})
options = scenario_options(registry)
if not options:
    st.error("The versioned scenario registry did not return any supported scenarios.")
    st.stop()

default_scenario_id = default_scenario(options)
valid_scenario_ids = {option.scenario_id for option in options}
requested_scenario = query_value("scenario", default_scenario_id)
selected_scenario_id = (
    requested_scenario
    if requested_scenario in valid_scenario_ids
    else default_scenario_id
)
if (
    requested_scenario != selected_scenario_id
    or query_value("scenario") != selected_scenario_id
):
    update_location(scenario=selected_scenario_id, payment_id=None)

option_by_id = {option.scenario_id: option for option in options}
selected_scenario = option_by_id[selected_scenario_id]
metadata = engine_metadata(analytics)
default_as_of_date = (
    selected_scenario.as_of_date
    or parse_date(first_present(metadata, ("as_of_date", "as_of")))
    or selected_scenario.close_date
    or date.today()
)
as_of_state_key = f"workbench_as_of_{selected_scenario_id}"
if as_of_state_key not in st.session_state:
    st.session_state[as_of_state_key] = default_as_of_date
selected_as_of = parse_date(
    st.session_state[as_of_state_key]
) or default_as_of_date
metadata["as_of_date"] = selected_as_of.isoformat()

render_header(metadata)
render_lifecycle()

active_view = canonical_view()
if st.session_state.get("workbench_navigation") != active_view:
    st.session_state["workbench_navigation"] = active_view
st.radio(
    "Workbench view",
    options=list(VALID_VIEWS),
    format_func=lambda view: VIEW_LABELS[view],
    horizontal=True,
    label_visibility="collapsed",
    key="workbench_navigation",
    on_change=navigation_changed,
)

with st.sidebar:
    st.markdown("## Investigation scope")
    if st.session_state.get("workbench_scenario") != selected_scenario_id:
        st.session_state["workbench_scenario"] = selected_scenario_id
    st.selectbox(
        "Synthetic scenario",
        options=list(option_by_id),
        format_func=lambda scenario_id: option_by_id[scenario_id].name,
        help="Each scenario is deterministic and documented in the repository manifest.",
        key="workbench_scenario",
        on_change=scenario_changed,
    )
    st.caption(selected_scenario.description)
    render_disclosure("Synthetic scenario—not a real incident.")

    selected_as_of = st.date_input(
        "As-of date",
        key=as_of_state_key,
        help=(
            "Re-evaluate missing and overdue rules at this date. "
            "The source snapshot remains unchanged."
        ),
    )

    seed = run_query(
        analytics,
        "close_summary",
        {
            "scenario": selected_scenario_id,
            "as_of_date": selected_as_of.isoformat(),
        },
        show_error=False,
    )
    currency_options = frame_currencies(seed)
    if currency_options:
        default_currency_index = (
            currency_options.index(selected_scenario.default_currency)
            if selected_scenario.default_currency in currency_options
            else 0
        )
        selected_currency = st.selectbox(
            "Currency",
            currency_options,
            index=default_currency_index,
            key=f"workbench_currency_{selected_scenario_id}",
        )
    else:
        selected_currency = None
        st.caption("Currency options unavailable")

    dataset_start, dataset_end = frame_date_bounds(seed)
    if dataset_start and dataset_end:
        selected_dates = st.date_input(
            "Processing dates",
            value=(dataset_start, dataset_end),
            min_value=dataset_start,
            max_value=dataset_end,
            key=f"workbench_dates_{selected_scenario_id}",
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            selected_start, selected_end = selected_dates
        elif isinstance(selected_dates, date):
            selected_start = selected_end = selected_dates
        else:
            selected_start, selected_end = dataset_start, dataset_end
    else:
        selected_start = selected_end = selected_scenario.close_date
        st.caption("Processing-date bounds unavailable")

    st.divider()
    st.link_button("Read the walkthrough", CASE_STUDY_URL, width="stretch")
    st.button(
        "Reset session-only reviews",
        width="stretch",
        on_click=reset_session_reviews,
        key="reset_session_reviews",
    )
    if st.session_state.pop("review_reset_notice", False):
        st.success("Session review state cleared.")

params = filter_params(
    selected_scenario_id,
    selected_currency,
    selected_start,
    selected_end,
    as_of_date=selected_as_of,
)

if active_view == "close":
    render_close_view(analytics, params, selected_currency)
elif active_view == "exceptions":
    render_exceptions_view(analytics, params, selected_scenario_id)
elif active_view == "trace":
    render_trace_view(analytics, params, query_value("payment_id"))
elif active_view == "catalog":
    render_catalog_view(analytics, metadata)

st.divider()
deep_link = urlencode(
    {
        "view": active_view,
        "scenario": selected_scenario_id,
        **(
            {"payment_id": query_value("payment_id")}
            if active_view == "trace" and query_value("payment_id")
            else {}
        ),
    }
)
st.caption(
    "Synthetic demo snapshot · Session actions never mutate source data · "
    f"Deep-link contract: `?{deep_link}`"
)
