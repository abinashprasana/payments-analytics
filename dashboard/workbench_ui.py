"""Presentation helpers for the Settlement Operations Workbench.

This module deliberately contains no analytical joins or aggregations.  It only
normalises values already returned by the canonical SQL query registry and
renders compact, accessible Streamlit components.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any, Iterable, Mapping

import pandas as pd
import streamlit as st


VIEW_LABELS: dict[str, str] = {
    "close": "Daily close",
    "exceptions": "Exceptions",
    "trace": "Payment trace",
    "catalog": "Metric catalog",
}
VALID_VIEWS = tuple(VIEW_LABELS)
DEFAULT_VIEW = "close"

PRIMARY_REASON_ORDER = (
    "missing",
    "currency_mismatch",
    "amount_mismatch",
    "fee_mismatch",
    "late",
    "disputed",
)

REASON_LABELS = {
    "missing": "Missing settlement",
    "late": "Late settlement",
    "currency_mismatch": "Currency mismatch",
    "amount_mismatch": "Amount mismatch",
    "fee_mismatch": "Fee mismatch",
    "disputed": "Disputed",
}

APP_CSS = """
<style>
  :root {
    --wb-bg: #050607;
    --wb-panel: #101923;
    --wb-panel-2: #15212d;
    --wb-ink: #f2f6f7;
    --wb-muted: #a9b7c2;
    --wb-line: rgba(185, 209, 220, 0.18);
    --wb-cyan: #68dcff;
    --wb-green: #80dfb4;
    --wb-amber: #f2c670;
    --wb-red: #ff887d;
  }

  .stApp {
    background:
      radial-gradient(circle at 78% -8%, rgba(69, 140, 166, .16), transparent 31rem),
      linear-gradient(180deg, #050607 0%, #0b131b 70%, #050607 100%);
    color: var(--wb-ink);
  }

  .block-container {
    max-width: 1240px;
    padding-top: 1.2rem;
    padding-bottom: 4rem;
  }

  h1, h2, h3 { letter-spacing: -0.025em; }
  p, li, label { line-height: 1.55; }

  a { color: var(--wb-cyan); }
  a:focus-visible, button:focus-visible, [role="button"]:focus-visible,
  input:focus-visible, textarea:focus-visible {
    outline: 3px solid var(--wb-cyan) !important;
    outline-offset: 2px !important;
  }

  [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
  [data-testid="stMain"] div[role="radiogroup"] label p {
    color: #c7d4da !important;
  }

  [data-testid="stSidebar"] .wb-disclosure {
    color: #674b16;
    background: #fff7e3;
    border-left-color: #b77a0c;
  }

  .wb-kicker {
    color: var(--wb-cyan);
    font-size: .74rem;
    font-weight: 750;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-bottom: .55rem;
  }

  .wb-hero {
    border: 1px solid var(--wb-line);
    border-radius: 18px;
    background: linear-gradient(145deg, rgba(19, 31, 42, .96), rgba(10, 17, 24, .94));
    padding: 1.35rem 1.45rem 1.15rem;
    margin-bottom: 1rem;
    box-shadow: 0 24px 80px rgba(0, 0, 0, .18);
  }

  .wb-hero h1 { margin: 0; font-size: clamp(1.8rem, 4vw, 3.15rem); }
  .wb-hero p { color: var(--wb-muted); max-width: 72ch; margin: .7rem 0 0; }

  .wb-meta-row, .wb-tag-row, .wb-lifecycle {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: .45rem;
  }

  .wb-meta-row { margin-top: 1rem; }
  .wb-pill, .wb-reason {
    display: inline-flex;
    align-items: center;
    min-height: 1.75rem;
    padding: .22rem .58rem;
    border: 1px solid var(--wb-line);
    border-radius: 999px;
    color: #d9e5ea;
    background: rgba(117, 151, 166, .08);
    font-size: .74rem;
    font-weight: 650;
  }

  .wb-reason[data-tone="critical"] { color: #ffd4cf; border-color: rgba(255, 136, 125, .5); }
  .wb-reason[data-tone="warning"] { color: #ffe7b1; border-color: rgba(242, 198, 112, .48); }
  .wb-reason[data-tone="info"] { color: #cdeefa; border-color: rgba(115, 215, 242, .44); }

  .wb-lifecycle {
    padding: .72rem .85rem;
    border-block: 1px solid var(--wb-line);
    margin: .45rem 0 1.1rem;
  }
  .wb-step { color: var(--wb-muted); font-size: .82rem; font-weight: 650; }
  .wb-step strong { color: var(--wb-ink); }
  .wb-arrow { color: #627785; }

  .wb-section-intro { margin-bottom: .8rem; }
  .wb-section-intro p { color: var(--wb-muted); max-width: 76ch; margin-top: -.35rem; }

  .wb-card {
    height: 100%;
    min-height: 126px;
    border: 1px solid var(--wb-line);
    border-radius: 14px;
    background: rgba(16, 25, 35, .88);
    padding: .9rem 1rem;
  }
  .wb-card-label { color: var(--wb-muted); font-size: .76rem; font-weight: 650; }
  .wb-card-value { color: var(--wb-ink); font-size: clamp(1.35rem, 2.6vw, 2rem); font-weight: 760; margin: .18rem 0; }
  .wb-card-note { color: var(--wb-muted); font-size: .74rem; }
  .wb-card[data-tone="good"] { border-top: 2px solid var(--wb-green); }
  .wb-card[data-tone="warning"] { border-top: 2px solid var(--wb-amber); }
  .wb-card[data-tone="critical"] { border-top: 2px solid var(--wb-red); }
  .wb-card[data-tone="info"] { border-top: 2px solid var(--wb-cyan); }

  .wb-disclosure {
    border-left: 3px solid var(--wb-amber);
    background: rgba(242, 198, 112, .075);
    color: #e8dcc0;
    padding: .85rem 1rem;
    border-radius: 0 10px 10px 0;
    margin: .85rem 0;
    font-size: .84rem;
    line-height: 1.6;
  }

  .wb-lineage {
    display: flex;
    align-items: stretch;
    flex-wrap: wrap;
    gap: .6rem;
    margin: .9rem 0 1.3rem;
  }
  .wb-lineage__stage {
    flex: 1 1 160px;
    min-width: 140px;
    border: 1px solid var(--wb-line);
    border-top: 2px solid var(--wb-cyan);
    border-radius: 12px;
    background: rgba(16, 25, 35, .82);
    padding: .7rem .8rem;
  }
  .wb-lineage__stage[data-tone="critical"] { border-top-color: var(--wb-red); }
  .wb-lineage__stage[data-tone="warning"] { border-top-color: var(--wb-amber); }
  .wb-lineage__stage[data-tone="good"] { border-top-color: var(--wb-green); }
  .wb-lineage__label {
    color: var(--wb-muted);
    font-size: .68rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .wb-lineage__value { color: var(--wb-ink); font-size: .92rem; font-weight: 650; margin-top: .3rem; }
  .wb-lineage__detail { color: var(--wb-muted); font-size: .76rem; margin-top: .2rem; }
  .wb-lineage__arrow {
    display: flex;
    align-items: center;
    color: var(--wb-cyan);
    font-size: 1.1rem;
  }

  .wb-query {
    border: 1px solid var(--wb-line);
    background: #0c141c;
    border-radius: 12px;
    padding: .85rem .95rem;
    color: var(--wb-muted);
    font-size: .82rem;
  }

  div[data-testid="stDataFrame"] {
    border: 1px solid var(--wb-line);
    border-radius: 12px;
    overflow: hidden;
  }

  div[data-testid="stMetric"] {
    border: 1px solid var(--wb-line);
    border-radius: 12px;
    background: rgba(16, 25, 35, .82);
    padding: .7rem .8rem;
  }

  .stButton > button, .stDownloadButton > button, .stLinkButton > a {
    min-height: 44px;
  }

  @media (max-width: 720px) {
    .block-container { padding-inline: .8rem; padding-top: .7rem; }
    .wb-hero { padding: 1rem; border-radius: 14px; }
    .wb-lifecycle { align-items: flex-start; }
    .wb-arrow { display: none; }
    .wb-step { flex: 1 0 44%; }
    .wb-lineage__arrow { display: none; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      scroll-behavior: auto !important;
      animation-duration: .01ms !important;
      transition-duration: .01ms !important;
    }
  }
</style>
"""


@dataclass(frozen=True)
class ScenarioOption:
    """Scenario metadata returned by the canonical scenario registry."""

    scenario_id: str
    name: str
    description: str
    close_date: date | None = None
    as_of_date: date | None = None
    default_currency: str | None = None
    is_default: bool = False


def apply_workbench_theme() -> None:
    """Mount the small CSS layer used by the workbench."""

    st.markdown(APP_CSS, unsafe_allow_html=True)


def scalar(value: Any, default: Any = None) -> Any:
    """Return a display-safe scalar from nullable dataframe values."""

    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return value


def first_present(
    row: Mapping[str, Any], names: Iterable[str], default: Any = None
) -> Any:
    """Read the first populated alias in a SQL result row."""

    for name in names:
        if name in row:
            value = scalar(row[name])
            if value is not None:
                return value
    return default


def parse_date(value: Any) -> date | None:
    value = scalar(value)
    if value is None:
        return None
    try:
        return pd.Timestamp(value).date()
    except (TypeError, ValueError):
        return None


def to_decimal(value: Any) -> Decimal:
    value = scalar(value, 0)
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(0)


def format_minor_units(value: Any, currency: str | None) -> str:
    """Format integer minor units without using floats."""

    minor_units = to_decimal(value).quantize(Decimal("1"))
    major_units = minor_units / Decimal(100)
    prefix = f"{currency} " if currency else ""
    return f"{prefix}{major_units:,.2f}"


def format_percent(value: Any) -> str:
    percent = to_decimal(value)
    if abs(percent) <= 1:
        percent *= Decimal(100)
    return f"{percent:.1f}%"


def format_count(value: Any) -> str:
    return f"{int(to_decimal(value)):,}"


def normalise_reasons(value: Any, row: Mapping[str, Any] | None = None) -> list[str]:
    """Return stable exception tags without changing their SQL-defined meaning."""

    raw = scalar(value, "")
    if isinstance(raw, (list, tuple, set)):
        candidates = [str(item).strip() for item in raw]
    else:
        text = str(raw).replace("|", ",").replace(";", ",")
        candidates = [item.strip() for item in text.split(",")]

    reasons = [item for item in candidates if item]
    if not reasons and row is not None:
        for reason in PRIMARY_REASON_ORDER:
            flag_names = (f"is_{reason}", f"{reason}_flag", reason)
            if any(bool(first_present(row, (name,), False)) for name in flag_names):
                reasons.append(reason)

    # SQL owns the classification.  Sorting only keeps its display deterministic.
    order = {reason: index for index, reason in enumerate(PRIMARY_REASON_ORDER)}
    return sorted(dict.fromkeys(reasons), key=lambda reason: order.get(reason, 99))


def reason_label(reason: str) -> str:
    return REASON_LABELS.get(reason, reason.replace("_", " ").title())


def reason_tone(reason: str) -> str:
    if reason in {"missing", "currency_mismatch", "amount_mismatch"}:
        return "critical"
    if reason in {"fee_mismatch", "late", "disputed"}:
        return "warning"
    return "info"


def reason_tags(reasons: Iterable[str]) -> str:
    tags = "".join(
        (
            f'<span class="wb-reason" data-tone="{reason_tone(reason)}">'
            f"{escape(reason_label(reason))}</span>"
        )
        for reason in reasons
    )
    return f'<div class="wb-tag-row">{tags}</div>'


def render_header(metadata: Mapping[str, Any]) -> None:
    dataset_version = first_present(
        metadata, ("dataset_version", "version"), "version unavailable"
    )
    as_of = first_present(metadata, ("as_of_date", "as_of"), "as-of unavailable")
    build_sha = str(
        first_present(metadata, ("build_sha", "commit_sha", "sha"), "local")
    )
    runtime = first_present(metadata, ("runtime_mode", "runtime"), "DuckDB snapshot")
    short_sha = build_sha[:8] if build_sha else "local"
    st.markdown(
        f"""
        <header class="wb-hero">
          <div class="wb-kicker">Settlement operations workbench</div>
          <h1>Find the close that did not close.</h1>
          <p>Trace completed merchant purchases from gross value to settlement evidence,
          using the same tested SQL models shown in the case study.</p>
          <div class="wb-meta-row" aria-label="Snapshot metadata">
            <span class="wb-pill">Synthetic demo snapshot</span>
            <span class="wb-pill">{escape(str(dataset_version))}</span>
            <span class="wb-pill">As of {escape(str(as_of))}</span>
            <span class="wb-pill">Build {escape(short_sha)}</span>
            <span class="wb-pill">{escape(str(runtime))}</span>
          </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_lifecycle() -> None:
    st.markdown(
        """
        <div class="wb-lifecycle" aria-label="Investigation workflow">
          <span class="wb-step"><strong>1.</strong> Identify close</span>
          <span class="wb-arrow" aria-hidden="true">→</span>
          <span class="wb-step"><strong>2.</strong> Filter exceptions</span>
          <span class="wb-arrow" aria-hidden="true">→</span>
          <span class="wb-step"><strong>3.</strong> Trace payment</span>
          <span class="wb-arrow" aria-hidden="true">→</span>
          <span class="wb-step"><strong>4.</strong> Export evidence</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_lineage_diagram(row: Mapping[str, Any]) -> None:
    """Show one payment's transaction -> term -> settlement -> exception chain."""

    currency = str(first_present(row, ("transaction_currency", "currency"), ""))
    settlement_currency = str(first_present(row, ("settlement_currency",), currency))
    primary = str(first_present(row, ("primary_reason",), "matched"))
    settled = first_present(row, ("actual_settlement_date", "settlement_date"))

    stages = (
        (
            "Transaction",
            format_minor_units(first_present(row, ("gross_minor_units",)), currency),
            str(first_present(row, ("transaction_date",), "Unknown date")),
            "info",
        ),
        (
            "Term",
            f"{to_decimal(first_present(row, ('fee_rate_bps',), 0)) / 100:.2f}% fee",
            f"{first_present(row, ('settlement_sla_days',), '—')}-day SLA",
            "info",
        ),
        (
            "Settlement",
            (
                format_minor_units(
                    first_present(row, ("recorded_settled_minor_units",)),
                    settlement_currency,
                )
                if settled is not None
                else "Not yet settled"
            ),
            str(settled) if settled is not None else "No settlement recorded",
            "good" if settled is not None else "warning",
        ),
        (
            "Exception",
            reason_label(primary),
            "Rule-flagged" if primary != "matched" else "Matched clean",
            reason_tone(primary) if primary != "matched" else "good",
        ),
    )

    parts = ['<div class="wb-lineage" aria-label="Transaction to exception lineage">']
    for index, (label, value, detail, tone) in enumerate(stages):
        if index:
            parts.append('<div class="wb-lineage__arrow" aria-hidden="true">→</div>')
        parts.append(
            f'<div class="wb-lineage__stage" data-tone="{escape(tone)}">'
            f'<div class="wb-lineage__label">{escape(label)}</div>'
            f'<div class="wb-lineage__value">{escape(value)}</div>'
            f'<div class="wb-lineage__detail">{escape(detail)}</div>'
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_section(title: str, description: str, kicker: str) -> None:
    st.markdown(
        f"""
        <section class="wb-section-intro">
          <div class="wb-kicker">{escape(kicker)}</div>
          <h2>{escape(title)}</h2>
          <p>{escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_kpi(
    label: str,
    value: str,
    note: str,
    tone: str = "info",
) -> None:
    st.markdown(
        f"""
        <div class="wb-card" data-tone="{escape(tone)}">
          <div class="wb-card-label">{escape(label)}</div>
          <div class="wb-card-value">{escape(value)}</div>
          <div class="wb-card-note">{escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def scenario_options(frame: pd.DataFrame) -> list[ScenarioOption]:
    """Convert the engine registry into typed presentation options."""

    options: list[ScenarioOption] = []
    for record in frame.to_dict(orient="records"):
        scenario_id = str(
            first_present(record, ("scenario_id", "id", "scenario"), "")
        ).strip()
        if not scenario_id:
            continue
        options.append(
            ScenarioOption(
                scenario_id=scenario_id,
                name=str(first_present(record, ("name", "label"), scenario_id)),
                description=str(
                    first_present(record, ("description", "summary"), "")
                ),
                close_date=parse_date(
                    first_present(record, ("close_date", "scenario_date", "date"))
                ),
                as_of_date=parse_date(
                    first_present(record, ("as_of_date", "snapshot_date"))
                ),
                default_currency=(
                    str(first_present(record, ("default_currency",), "")).strip()
                    or None
                ),
                is_default=bool(first_present(record, ("is_default", "default"), False)),
            )
        )
    return options


def default_scenario(options: Iterable[ScenarioOption]) -> str:
    materialised = list(options)
    selected = next((option for option in materialised if option.is_default), None)
    if selected:
        return selected.scenario_id
    normal = next(
        (
            option
            for option in materialised
            if "normal" in option.scenario_id.lower()
            or "normal" in option.name.lower()
        ),
        None,
    )
    return normal.scenario_id if normal else materialised[0].scenario_id


def render_disclosure(text: str) -> None:
    st.markdown(
        f'<div class="wb-disclosure">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def display_frame(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Select requested columns without inventing missing analytical values."""

    available = [column for column in columns if column in frame.columns]
    return frame.loc[:, available].copy()


def trace_money_table(row: Mapping[str, Any]) -> pd.DataFrame:
    """Format SQL-returned trace money without crossing currency boundaries."""

    expected_currency = str(
        first_present(row, ("transaction_currency", "currency"), "")
    )
    recorded_currency = str(first_present(row, ("settlement_currency",), ""))
    fields = (
        (
            "Gross identity",
            (
                "expected_gross_minor_units",
                "gross_minor_units",
                "transaction_minor_units",
            ),
            ("recorded_gross_minor_units",),
        ),
        (
            "Processing fee",
            ("expected_fee_minor_units", "term_fee_minor_units"),
            (
                "recorded_fee_minor_units",
                "processing_fee_minor_units",
                "processing_fee",
            ),
        ),
        (
            "Net settlement",
            ("expected_settled_minor_units", "expected_net_minor_units"),
            (
                "recorded_settled_minor_units",
                "settled_minor_units",
                "settled_amount_minor_units",
            ),
        ),
    )
    records: list[dict[str, str]] = []
    for label, expected_aliases, recorded_aliases in fields:
        expected = first_present(row, expected_aliases)
        recorded = first_present(row, recorded_aliases)
        if expected is None and recorded is None:
            continue
        records.append(
            {
                "Measure": label,
                "Expected": (
                    format_minor_units(expected, expected_currency)
                    if expected is not None
                    else "Not available"
                ),
                "Recorded": (
                    format_minor_units(recorded, recorded_currency)
                    if recorded is not None
                    else "Missing"
                ),
            }
        )
    return pd.DataFrame.from_records(records)
