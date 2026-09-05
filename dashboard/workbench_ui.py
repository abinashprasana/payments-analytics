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
  /* Mirror of the token block in site/src/app/globals.css :root, so both
     surfaces read as one product. Drift is caught by
     tests/test_ui_integrity.py::test_token_blocks_match, not by discipline.
     Colours, radii, link colour, dataframe chrome and widget borders are set
     natively in .streamlit/config.toml, which reaches widget internals that
     CSS cannot. Only what config cannot express lives here. */
  :root {
    --wb-sp-1: 4px;
    --wb-sp-2: 8px;
    --wb-sp-3: 12px;
    --wb-sp-4: 16px;
    --wb-sp-5: 24px;
    --wb-sp-6: 32px;
    --wb-sp-7: 48px;
    --wb-sp-8: 64px;

    --wb-fs-50: 0.6875rem;
    --wb-fs-75: 0.8125rem;
    --wb-fs-100: 0.9375rem;
    --wb-fs-200: 1rem;
    --wb-fs-300: 1.125rem;
    --wb-fs-400: 1.375rem;
    --wb-fs-500: 1.75rem;
    --wb-fs-600: 2.25rem;

    --wb-radius-control: 8px;
    --wb-radius-panel: 16px;
    --wb-radius-pill: 999px;

    --wb-surface-sunken: #070a0d;
    --wb-surface-0: #0b0e12;
    --wb-surface-1: #11161c;
    --wb-surface-2: #161c24;
    --wb-surface-3: #1c242d;

    --wb-ink: #f2f5f7;
    --wb-ink-soft: #c4cfd6;
    --wb-muted: #8c9ba5;
    --wb-line: rgba(190, 205, 214, 0.12);
    --wb-line-strong: rgba(190, 205, 214, 0.26);

    --wb-accent: #f0906f;
    --wb-cyan: #72d5ee;
    --wb-green: #86d9ae;
    --wb-amber: #e9be72;
    --wb-red: #f0817b;
  }

  .stApp {
    background:
      radial-gradient(ellipse 90% 60% at 78% -10%, rgba(114, 213, 238, .07), transparent 60%),
      var(--wb-surface-0);
    color: var(--wb-ink);
  }

  /* Streamlit re-specifies padding-inline responsively, so the shorthand alone
     leaves the column narrower than the site's. Centred rather than computed
     from 100vw, because the viewport includes the sidebar and the main area
     does not. */
  .block-container {
    max-width: 1240px;
    margin-inline: auto;
    padding-top: var(--wb-sp-5);
    padding-bottom: var(--wb-sp-8);
    padding-left: var(--wb-sp-5);
    padding-right: var(--wb-sp-5);
  }

  h1, h2, h3 { letter-spacing: -0.025em; }
  p, li, label { line-height: 1.55; }

  /* Outline only. Streamlit draws its own focus box-shadow, which would
     otherwise double-draw alongside this ring. */
  a:focus-visible, button:focus-visible, [role="button"]:focus-visible,
  input:focus-visible, textarea:focus-visible {
    outline: 3px solid var(--wb-cyan) !important;
    outline-offset: 2px;
    box-shadow: none;
  }

  .wb-kicker {
    color: var(--wb-cyan);
    font-size: var(--wb-fs-75);
    font-weight: 700;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-bottom: var(--wb-sp-2);
  }

  .wb-hero {
    border: 1px solid var(--wb-line-strong);
    border-radius: var(--wb-radius-panel);
    background: var(--wb-surface-2);
    padding: var(--wb-sp-5);
    margin-bottom: var(--wb-sp-4);
  }

  .wb-hero h1 { margin: 0; font-size: clamp(var(--wb-fs-500), 4vw, var(--wb-fs-600)); }
  .wb-hero p { color: var(--wb-muted); max-width: 72ch; margin: var(--wb-sp-3) 0 0; }

  .wb-meta-row, .wb-tag-row, .wb-lifecycle {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--wb-sp-2);
  }

  .wb-meta-row { margin-top: var(--wb-sp-4); }
  .wb-pill, .wb-reason {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: var(--wb-sp-1) var(--wb-sp-3);
    border: 1px solid var(--wb-line);
    border-radius: var(--wb-radius-pill);
    color: var(--wb-ink-soft);
    background: var(--wb-surface-3);
    font-size: var(--wb-fs-75);
    font-weight: 600;
  }

  .wb-reason[data-tone="critical"] { color: var(--wb-red); border-color: var(--wb-red); }
  .wb-reason[data-tone="warning"] { color: var(--wb-amber); border-color: var(--wb-amber); }
  .wb-reason[data-tone="info"] { color: var(--wb-cyan); border-color: var(--wb-cyan); }

  .wb-lifecycle {
    padding: var(--wb-sp-3) 0;
    border-block: 1px solid var(--wb-line);
    margin: var(--wb-sp-2) 0 var(--wb-sp-5);
  }
  .wb-step { color: var(--wb-muted); font-size: var(--wb-fs-100); font-weight: 600; }
  .wb-step strong { color: var(--wb-ink); }
  .wb-arrow { color: var(--wb-cyan); }

  /* Streamlit's heading margin is controlled directly rather than clawed back
     with a negative margin, which broke whenever its spacing changed. */
  .wb-section-intro { margin-bottom: var(--wb-sp-4); }
  .wb-section-intro h2, .wb-section-intro h3 { margin-block: 0 var(--wb-sp-2); }
  .wb-section-intro p { color: var(--wb-muted); max-width: 76ch; margin: 0; }

  .wb-card {
    height: 100%;
    min-height: 126px;
    border: 1px solid var(--wb-line);
    border-radius: var(--wb-radius-panel);
    background: var(--wb-surface-2);
    padding: var(--wb-sp-4);
  }
  .wb-card-label { color: var(--wb-muted); font-size: var(--wb-fs-75); font-weight: 600; }
  .wb-card-value { color: var(--wb-ink); font-size: clamp(var(--wb-fs-400), 2.6vw, var(--wb-fs-500)); font-weight: 700; margin: var(--wb-sp-1) 0; }
  .wb-card-note { color: var(--wb-muted); font-size: var(--wb-fs-75); }

  /* One status idiom across both surfaces: an inset rule, which tints without
     changing geometry the way a border would. */
  .wb-card[data-tone="good"] { box-shadow: inset 0 2px 0 var(--wb-green); }
  .wb-card[data-tone="warning"] { box-shadow: inset 0 2px 0 var(--wb-amber); }
  .wb-card[data-tone="critical"] { box-shadow: inset 0 2px 0 var(--wb-red); }
  .wb-card[data-tone="info"] { box-shadow: inset 0 2px 0 var(--wb-cyan); }

  .wb-disclosure {
    box-shadow: inset 3px 0 0 var(--wb-amber);
    background: var(--wb-surface-2);
    color: var(--wb-ink-soft);
    padding: var(--wb-sp-3) var(--wb-sp-4);
    border-radius: var(--wb-radius-control);
    margin: var(--wb-sp-3) 0;
    font-size: var(--wb-fs-100);
    line-height: 1.6;
  }

  .wb-lineage {
    display: flex;
    align-items: stretch;
    flex-wrap: wrap;
    gap: var(--wb-sp-2);
    margin: var(--wb-sp-4) 0 var(--wb-sp-5);
  }
  .wb-lineage__stage {
    flex: 1 1 160px;
    min-width: 140px;
    border: 1px solid var(--wb-line);
    border-radius: var(--wb-radius-panel);
    background: var(--wb-surface-2);
    box-shadow: inset 0 2px 0 var(--wb-cyan);
    padding: var(--wb-sp-3) var(--wb-sp-4);
  }
  .wb-lineage__stage[data-tone="critical"] { box-shadow: inset 0 2px 0 var(--wb-red); }
  .wb-lineage__stage[data-tone="warning"] { box-shadow: inset 0 2px 0 var(--wb-amber); }
  .wb-lineage__stage[data-tone="good"] { box-shadow: inset 0 2px 0 var(--wb-green); }
  .wb-lineage__label {
    color: var(--wb-muted);
    font-size: var(--wb-fs-50);
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .wb-lineage__value { color: var(--wb-ink); font-size: var(--wb-fs-100); font-weight: 600; margin-top: var(--wb-sp-1); }
  .wb-lineage__detail { color: var(--wb-muted); font-size: var(--wb-fs-75); margin-top: var(--wb-sp-1); }
  .wb-lineage__arrow {
    display: flex;
    align-items: center;
    color: var(--wb-cyan);
    font-size: var(--wb-fs-300);
  }

  .wb-query {
    border: 1px solid var(--wb-line);
    background: var(--wb-surface-sunken);
    border-radius: var(--wb-radius-control);
    padding: var(--wb-sp-3) var(--wb-sp-4);
    color: var(--wb-muted);
    font-size: var(--wb-fs-75);
  }

  /* No overflow:hidden: the dataframe is a canvas grid that renders its own
     resize handles and cell overlays outside its box. Its border and radius
     come from theme.dataframeBorderColor and theme.baseRadius. */
  div[data-testid="stMetric"] {
    border: 1px solid var(--wb-line);
    border-radius: var(--wb-radius-panel);
    background: var(--wb-surface-2);
    padding: var(--wb-sp-3) var(--wb-sp-4);
  }

  .stButton > button, .stDownloadButton > button, .stLinkButton > a {
    min-height: 44px;
    font-weight: 600;
  }

  /* Same breakpoint as the site, so the two surfaces reflow together. */
  @media (max-width: 820px) {
    .block-container { padding-inline: var(--wb-sp-4); padding-top: var(--wb-sp-3); }
    .wb-hero { padding: var(--wb-sp-4); }
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
          using the same tested SQL models shown in the walkthrough.</p>
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
