"""Presentation system for the Payment Observatory dashboard."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd
import streamlit as st


BRAND_DIR = Path(__file__).resolve().parent / "static" / "brand"
BRAND_MARK_PATH = BRAND_DIR / "payment-observatory-mark.svg"
BRAND_MARK_FALLBACK = """
<svg viewBox="0 0 64 64" fill="none">
  <path d="M12 48C5 38 7 24 16 16C25 8 39 8 48 16" stroke="#68DCFF" stroke-width="4" stroke-linecap="round"/>
  <path d="M5 32H22M42 32H59" stroke="#68DCFF" stroke-width="3" stroke-linecap="round"/>
  <path d="M32 18L44 25V39L32 46L20 39V25L32 18Z" fill="#08111A" stroke="#68DCFF" stroke-width="2"/>
  <circle cx="32" cy="32" r="5" fill="#E7FCFF"/>
</svg>
""".strip()


def _load_brand_mark() -> str:
    """Read the trusted local mark without making the product header fragile."""

    try:
        return BRAND_MARK_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return BRAND_MARK_FALLBACK


APP_CSS = """
<style>
:root {
    color-scheme: dark;
    --pay-canvas: #050607;
    --pay-canvas-soft: #080a0d;
    --pay-surface: #0c0f13;
    --pay-surface-raised: #11151b;
    --pay-line: rgba(203, 219, 233, 0.11);
    --pay-line-strong: rgba(203, 219, 233, 0.22);
    --pay-ink: #f1f3ef;
    --pay-muted: #8d99a5;
    --pay-cyan: #68dcff;
    --pay-blue: #4e72ff;
    --pay-teal: #8af6c7;
    --pay-amber: #f5bb62;
    --pay-coral: #ff756f;
    --pay-violet: #a58cff;
    --pay-snap: 120ms;
    --pay-ui: 200ms;
    --pay-reveal: 480ms;
    --pay-ambient: 4.8s;
    --pay-radius-sm: 10px;
    --pay-radius-md: 16px;
    --pay-radius-lg: 26px;
    --pay-edge-light: rgba(203, 219, 233, 0.16);
    --pay-depth-low: 0 14px 28px rgba(0, 0, 0, 0.2);
    --pay-depth-panel: 0 28px 68px rgba(0, 0, 0, 0.28);
    --pay-depth-focus: 0 22px 48px rgba(0, 0, 0, 0.34), 0 0 0 3px rgba(75, 216, 255, 0.055);
    --pay-font: "Source Sans", "Segoe UI Variable", "Segoe UI", sans-serif;
    --pay-display: "space-grotesk", "Source Sans", "Segoe UI Variable", sans-serif;
    --pay-mono: "Source Code Pro", "Cascadia Code", Consolas, monospace;
}

html {
    background: var(--pay-canvas);
    scroll-behavior: smooth;
}

body,
[class*="css"],
.stApp {
    font-family: var(--pay-font);
}

body {
    background: var(--pay-canvas);
}

.stApp {
    color: var(--pay-ink);
    background:
        radial-gradient(circle at 9% -8%, rgba(75, 216, 255, 0.13), transparent 28rem),
        radial-gradient(circle at 92% 8%, rgba(66, 232, 180, 0.075), transparent 30rem),
        linear-gradient(155deg, #06111a 0%, #050b11 48%, #03070b 100%);
}

.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.2;
    background-image:
        linear-gradient(rgba(132, 177, 203, 0.045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(132, 177, 203, 0.045) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: linear-gradient(to bottom, #000 0%, transparent 78%);
}

header[data-testid="stHeader"] {
    height: 3.25rem;
    background: rgba(4, 9, 14, 0.9);
    border-bottom: 1px solid var(--pay-line);
    backdrop-filter: blur(18px);
}

header[data-testid="stHeader"] [data-testid="stToolbar"] {
    right: 0.75rem;
}

.stMainBlockContainer,
.block-container {
    position: relative;
    z-index: 1;
    max-width: 1280px;
    padding-top: 5.2rem;
    padding-bottom: 3.5rem;
}

#MainMenu,
footer {
    visibility: hidden;
}

.pay-progress {
    position: fixed;
    top: 3.22rem;
    left: 0;
    right: 0;
    height: 2px;
    z-index: 1001;
    background: rgba(255, 255, 255, 0.035);
}

.pay-progress-fill {
    display: block;
    width: 100%;
    height: 100%;
    transform: scaleX(0);
    transform-origin: left center;
    background: linear-gradient(90deg, var(--pay-cyan), var(--pay-teal));
    box-shadow: 0 0 16px rgba(75, 216, 255, 0.7);
}

.pay-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 24px;
}

.pay-brand {
    display: inline-flex;
    align-items: center;
    gap: 13px;
    min-width: 0;
}

.pay-brand-mark {
    position: relative;
    display: inline-grid;
    flex: 0 0 auto;
    width: 42px;
    height: 42px;
    place-items: center;
    isolation: isolate;
    filter: drop-shadow(0 9px 18px rgba(0, 0, 0, 0.38));
}

.pay-brand-mark::before {
    content: "";
    position: absolute;
    inset: 8px;
    z-index: -1;
    border-radius: 999px;
    background: rgba(78, 114, 255, 0.14);
    box-shadow: 0 0 22px rgba(78, 114, 255, 0.18);
}

.pay-brand-mark svg {
    display: block;
    width: 100%;
    height: 100%;
    overflow: visible;
}

.pay-brand-mark .po-brand-core,
.pay-brand-mark .po-brand-orbits,
.pay-brand-mark .po-brand-node {
    transform-box: fill-box;
    transform-origin: center;
}

.pay-brand-mark .po-brand-signal {
    opacity: 0;
    offset-path: path("M 4.5 32 H 32");
    offset-anchor: center;
    offset-distance: 0%;
    filter: drop-shadow(0 0 4px rgba(231, 252, 255, 0.92));
}

.pay-brand-mark .po-brand-node-merchant { color: #68dcff; }
.pay-brand-mark .po-brand-node-settlement { color: #8af6c7; }
.pay-brand-mark .po-brand-node-review { color: #ff756f; }

@keyframes pay-brand-core-in {
    0% { opacity: 0.52; transform: scale(0.78) rotate(-8deg); }
    68% { opacity: 1; transform: scale(1.06) rotate(1deg); }
    100% { opacity: 1; transform: scale(1) rotate(0); }
}

@keyframes pay-brand-orbit-in {
    from { opacity: 0.3; transform: rotate(-7deg) scale(0.92); }
    to { opacity: 1; transform: rotate(0) scale(1); }
}

@keyframes pay-brand-signal-pass {
    0% { opacity: 0; offset-distance: 0%; }
    14% { opacity: 1; }
    82% { opacity: 1; }
    100% { opacity: 0; offset-distance: 100%; }
}

@keyframes pay-brand-node-light {
    0%, 100% { transform: scale(1); filter: none; }
    48% { transform: scale(1.48); filter: drop-shadow(0 0 5px currentColor); }
}

@media (prefers-reduced-motion: no-preference) {
    .pay-brand-mark.is-intro .po-brand-core {
        animation: pay-brand-core-in 420ms cubic-bezier(0.2, 0.82, 0.2, 1) both;
    }
    .pay-brand-mark.is-intro .po-brand-orbits {
        animation: pay-brand-orbit-in 520ms cubic-bezier(0.2, 0.82, 0.2, 1) both;
    }
    .pay-brand-mark.is-intro .po-brand-signal,
    .pay-brand:hover .po-brand-signal {
        animation: pay-brand-signal-pass 620ms 80ms cubic-bezier(0.24, 0.72, 0.28, 1) both;
    }
    .pay-brand-mark.is-intro .po-brand-node-merchant,
    .pay-brand:hover .po-brand-node-merchant {
        animation: pay-brand-node-light 230ms 430ms ease-out both;
    }
    .pay-brand-mark.is-intro .po-brand-node-settlement,
    .pay-brand:hover .po-brand-node-settlement {
        animation: pay-brand-node-light 230ms 520ms ease-out both;
    }
    .pay-brand-mark.is-intro .po-brand-node-review,
    .pay-brand:hover .po-brand-node-review {
        animation: pay-brand-node-light 230ms 610ms ease-out both;
    }
}

.pay-brand-name {
    color: var(--pay-ink);
    font-size: 14px;
    font-weight: 750;
    letter-spacing: -0.01em;
    white-space: nowrap;
}

.pay-brand-sub {
    margin-top: 2px;
    color: var(--pay-muted);
    font-family: var(--pay-mono);
    font-size: 11px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

.pay-top-meta {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 8px;
}

.pay-case-study {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 31px;
    padding: 6px 10px;
    border: 1px solid rgba(104, 220, 255, 0.24);
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(78, 114, 255, 0.14), rgba(104, 220, 255, 0.04));
    color: #dff7ff !important;
    font-family: var(--pay-mono);
    font-size: 11px;
    font-weight: 600;
    text-decoration: none !important;
    transition: border-color var(--pay-ui) ease, background var(--pay-ui) ease, transform var(--pay-snap) ease;
}

.pay-case-study svg {
    width: 13px;
    height: 13px;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.5;
}

.pay-case-study:hover {
    border-color: rgba(104, 220, 255, 0.5);
    background: linear-gradient(135deg, rgba(78, 114, 255, 0.22), rgba(104, 220, 255, 0.07));
    transform: translateY(-1px);
}

.pay-case-study:focus-visible {
    outline: 2px solid rgba(104, 220, 255, 0.54);
    outline-offset: 3px;
}

.pay-chip,
.pay-source {
    display: inline-flex;
    align-items: center;
    min-height: 30px;
    padding: 6px 10px;
    border: 1px solid var(--pay-line);
    border-radius: 999px;
    background: rgba(9, 21, 30, 0.78);
    color: var(--pay-muted);
    font-family: var(--pay-mono);
    font-size: 11px;
    letter-spacing: 0.02em;
}

.pay-source {
    color: #c8f9e9;
    border-color: rgba(66, 232, 180, 0.26);
}

.pay-source::before {
    content: "";
    width: 6px;
    height: 6px;
    margin-right: 7px;
    border-radius: 50%;
    background: var(--pay-teal);
    box-shadow: 0 0 10px rgba(66, 232, 180, 0.7);
}

.pay-section-kicker,
.pay-card-label {
    color: var(--pay-cyan);
    font-family: var(--pay-mono);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

div[data-testid="stForm"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.pay-filter-anchor) {
    border: 1px solid var(--pay-line);
    border-radius: var(--pay-radius-lg);
    background:
        linear-gradient(135deg, rgba(75, 216, 255, 0.035), transparent 42%),
        rgba(7, 16, 24, 0.9);
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.2);
}

div[data-testid="stForm"] {
    padding: 8px 14px 4px;
}

div[data-testid="stForm"] label,
div[data-testid="stWidgetLabel"] p {
    color: #b8c7d2;
    font-family: var(--pay-mono);
    font-size: 11px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-testid="stDateInput"] > div > div {
    border-color: var(--pay-line-strong);
    border-radius: 11px;
    background: rgba(5, 13, 19, 0.78);
}

div[data-testid="stFormSubmitButton"] button,
.stButton button {
    min-height: 40px;
    border: 1px solid rgba(75, 216, 255, 0.28);
    border-radius: 11px;
    background: rgba(75, 216, 255, 0.08);
    color: #dff7ff;
    font-weight: 650;
    transition:
        border-color var(--pay-ui) ease,
        background var(--pay-ui) ease,
        transform var(--pay-snap) ease;
}

div[data-testid="stFormSubmitButton"] button:hover,
.stButton button:hover {
    border-color: rgba(75, 216, 255, 0.58);
    background: rgba(75, 216, 255, 0.13);
    transform: translateY(-1px);
}

.pay-filter-note {
    margin: 8px 2px 22px;
    color: #71899a;
    font-size: 12px;
}

.pay-filter-note strong {
    color: #a9bbc7;
    font-weight: 600;
}

div[data-testid="stTabs"] {
    margin-top: 16px;
}

div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 5px;
    padding: 5px;
    border: 1px solid var(--pay-line);
    border-radius: 14px;
    background: rgba(6, 14, 21, 0.86);
}

div[data-testid="stTabs"] button[data-baseweb="tab"] {
    min-height: 42px;
    padding: 0 16px;
    border-radius: 9px;
    color: var(--pay-muted);
    font-size: 13px;
    font-weight: 650;
    transition:
        color var(--pay-ui) ease,
        background var(--pay-ui) ease;
}

div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #eaf9ff;
    background: rgba(75, 216, 255, 0.1);
}

div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, var(--pay-cyan), var(--pay-teal));
}

.pay-section-heading {
    display: grid;
    grid-template-columns: minmax(0, 0.85fr) minmax(280px, 1fr);
    align-items: end;
    gap: 40px;
    margin: 48px 0 22px;
}

.pay-section-heading h2 {
    max-width: 720px;
    margin: 8px 0 0;
    color: var(--pay-ink);
    font-size: clamp(25px, 3.2vw, 42px);
    font-weight: 730;
    letter-spacing: -0.045em;
    line-height: 1.03;
}

.pay-section-heading p {
    max-width: 620px;
    margin: 0;
    color: var(--pay-muted);
    font-size: 13px;
    line-height: 1.65;
}

.pay-kpi-grid {
    display: grid;
    grid-template-columns: 1.25fr 0.85fr 0.85fr 1.05fr;
    gap: 12px;
}

.pay-kpi-card {
    position: relative;
    min-height: 176px;
    overflow: hidden;
    padding: 20px;
    border: 1px solid var(--pay-line);
    border-radius: var(--pay-radius-md);
    background:
        radial-gradient(circle at 88% 6%, rgba(75, 216, 255, 0.08), transparent 42%),
        linear-gradient(155deg, rgba(14, 30, 42, 0.95), rgba(7, 16, 23, 0.96));
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.16);
    transition:
        transform var(--pay-ui) ease,
        border-color var(--pay-ui) ease,
        background var(--pay-ui) ease;
}

.pay-kpi-card::after {
    content: "";
    position: absolute;
    left: 20px;
    right: 20px;
    bottom: 0;
    height: 2px;
    opacity: 0.7;
    background: linear-gradient(90deg, var(--tone), transparent);
}

.pay-kpi-card:hover {
    transform: translateY(-2px);
    border-color: rgba(75, 216, 255, 0.3);
}

.pay-kpi-card.cyan { --tone: var(--pay-cyan); }
.pay-kpi-card.teal { --tone: var(--pay-teal); }
.pay-kpi-card.amber { --tone: var(--pay-amber); }
.pay-kpi-card.violet { --tone: var(--pay-violet); }

.pay-kpi-value {
    display: block;
    margin-top: 23px;
    color: var(--pay-ink);
    font-family: var(--pay-mono);
    font-size: clamp(26px, 3vw, 42px);
    font-weight: 620;
    letter-spacing: -0.055em;
    line-height: 1;
}

.pay-kpi-card p {
    margin: 12px 0 0;
    color: var(--pay-muted);
    font-size: 12px;
    line-height: 1.45;
}

.pay-variance {
    display: inline-flex;
    margin-top: 12px;
    padding: 4px 7px;
    border-radius: 999px;
    color: #c5d4de;
    background: rgba(255, 255, 255, 0.045);
    font-family: var(--pay-mono);
    font-size: 11px;
}

.pay-variance.up {
    color: #baf6df;
    background: rgba(66, 232, 180, 0.08);
}

.pay-variance.down {
    color: #ffc1c9;
    background: rgba(255, 126, 143, 0.08);
}

.pay-status-card {
    margin: 12px 0 4px;
    padding: 18px 20px 17px;
    border: 1px solid var(--pay-line);
    border-radius: var(--pay-radius-md);
    background: rgba(8, 18, 26, 0.82);
}

.pay-status-head,
.pay-status-legend {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
}

.pay-status-head strong {
    color: #dce9f1;
    font-size: 14px;
}

.pay-status-head span {
    color: var(--pay-muted);
    font-family: var(--pay-mono);
    font-size: 11px;
}

.pay-status-track {
    display: flex;
    gap: 3px;
    height: 10px;
    margin: 14px 0 13px;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.05);
}

.pay-status-segment {
    min-width: 0;
    border-radius: 999px;
    background: var(--segment);
    box-shadow: 0 0 15px color-mix(in srgb, var(--segment) 26%, transparent);
}

.pay-status-legend {
    justify-content: flex-start;
    flex-wrap: wrap;
}

.pay-legend-item {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: var(--pay-muted);
    font-size: 12px;
}

.pay-legend-item::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--segment);
}

.pay-legend-item strong {
    color: #d9e4eb;
    font-family: var(--pay-mono);
    font-weight: 550;
}

.pay-chart-note,
.pay-data-note,
.pay-empty-state {
    margin: 12px 0;
    padding: 13px 15px;
    border: 1px solid var(--pay-line);
    border-radius: 12px;
    background: rgba(8, 18, 26, 0.72);
    color: var(--pay-muted);
    font-size: 12px;
    line-height: 1.55;
}

.pay-data-note.coral {
    border-color: rgba(255, 126, 143, 0.2);
    background: rgba(255, 126, 143, 0.045);
    color: #d8aab1;
}

.pay-empty-state {
    padding: 34px;
    text-align: center;
    background:
        radial-gradient(circle at 50% 0%, rgba(75, 216, 255, 0.08), transparent 46%),
        rgba(7, 16, 23, 0.84);
}

.pay-empty-state strong {
    display: block;
    margin-bottom: 7px;
    color: var(--pay-ink);
    font-size: 18px;
}

.pay-method-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.pay-method-card {
    min-height: 164px;
    padding: 19px;
    border: 1px solid var(--pay-line);
    border-radius: var(--pay-radius-md);
    background: rgba(8, 18, 26, 0.76);
}

.pay-method-card strong {
    display: block;
    margin-top: 20px;
    color: var(--pay-ink);
    font-size: 16px;
}

.pay-method-card p {
    margin: 9px 0 0;
    color: var(--pay-muted);
    font-size: 12px;
    line-height: 1.55;
}

div[data-testid="stMetric"] {
    min-height: 116px;
    padding: 16px 17px;
    border: 1px solid var(--pay-line);
    border-radius: 14px;
    background: rgba(8, 18, 26, 0.76);
}

div[data-testid="stMetricLabel"] {
    color: var(--pay-muted);
    font-family: var(--pay-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

div[data-testid="stMetricValue"] {
    color: var(--pay-ink);
    font-family: var(--pay-mono);
    font-size: clamp(22px, 2.5vw, 34px);
}

div[data-testid="stPlotlyChart"] {
    overflow: hidden;
    border: 1px solid var(--pay-line);
    border-radius: var(--pay-radius-md);
    background: rgba(5, 13, 20, 0.62);
}

div[data-testid="stDataFrame"],
div[data-testid="stTable"] {
    border: 1px solid var(--pay-line);
    border-radius: 13px;
    overflow: hidden;
}

details[data-testid="stExpander"] {
    border: 1px solid var(--pay-line);
    border-radius: 14px;
    background: rgba(7, 16, 23, 0.72);
}

details[data-testid="stExpander"] summary {
    color: #d9e7ef;
    font-size: 13px;
    font-weight: 650;
}

.pay-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-top: 54px;
    padding-top: 19px;
    border-top: 1px solid var(--pay-line);
    color: #647a8a;
    font-family: var(--pay-mono);
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.pay-motion-ready .pay-reveal {
    opacity: 0;
    transform: translateY(16px);
}

.pay-motion-ready .pay-reveal.pay-visible {
    opacity: 1;
    transform: translateY(0);
    transition:
        opacity var(--pay-reveal) cubic-bezier(0.2, 0.75, 0.2, 1),
        transform var(--pay-reveal) cubic-bezier(0.2, 0.75, 0.2, 1);
}

@media (max-width: 980px) {
    .pay-kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .pay-section-heading {
        grid-template-columns: 1fr;
        gap: 12px;
    }

}

@media (max-width: 700px) {
    .stMainBlockContainer,
    .block-container {
        padding-top: 4.6rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .pay-topbar {
        align-items: flex-start;
        flex-direction: column;
    }

    .pay-top-meta {
        justify-content: flex-start;
    }

    .pay-kpi-grid,
    .pay-method-grid {
        grid-template-columns: 1fr;
    }

    .pay-kpi-card {
        min-height: 148px;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-list"] {
        overflow-x: auto;
        justify-content: flex-start;
    }

    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        flex: 0 0 auto;
        padding: 0 12px;
    }

    .pay-status-head,
    .pay-footer {
        align-items: flex-start;
        flex-direction: column;
    }
}

@media (prefers-reduced-motion: reduce) {
    html {
        scroll-behavior: auto;
    }

    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }

    .pay-reveal,
    .pay-motion-ready .pay-reveal {
        opacity: 1 !important;
        transform: none !important;
    }
}
"""

APP_CSS += """

/* Product component refinements. These rules share the canonical tokens above. */

html,
body,
.stApp {
    background: var(--pay-canvas);
}

body,
[class*="css"],
.stApp {
    font-family: var(--pay-font);
}

.stApp {
    background:
        radial-gradient(circle at 76% -10%, rgba(78, 114, 255, 0.12), transparent 36rem),
        radial-gradient(circle at 0% 24%, rgba(104, 220, 255, 0.055), transparent 31rem),
        linear-gradient(180deg, #080a0d 0%, #050607 38%, #050607 100%);
}

.stApp::before {
    opacity: .18;
    background-image:
        linear-gradient(rgba(177, 201, 219, .035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(177, 201, 219, .035) 1px, transparent 1px);
    background-size: 72px 72px;
    mask-image: linear-gradient(to bottom, #000 0%, transparent 62%);
}

header[data-testid="stHeader"] {
    height: 0;
    min-height: 0;
    background: transparent;
    border: 0;
}

header[data-testid="stHeader"] [data-testid="stToolbar"],
div[data-testid="stDecoration"] {
    display: none;
}

.stMainBlockContainer,
.block-container {
    max-width: 1380px;
    padding-top: 2rem;
}

.pay-progress {
    top: 0;
    background: rgba(255, 255, 255, .02);
}

.pay-progress-fill {
    background: linear-gradient(90deg, #4e72ff, #68dcff 52%, #8af6c7);
}

.pay-topbar {
    flex-wrap: wrap;
    margin-bottom: 18px;
}

.st-key-pay_sticky_controls {
    position: sticky;
    top: 10px;
    z-index: 990;
    margin: 12px -7px 0;
    padding: 6px;
    border: 1px solid rgba(203, 219, 233, .08);
    border-radius: 20px;
    background: rgba(5, 6, 7, .84);
    box-shadow: 0 18px 46px rgba(0, 0, 0, .3);
    backdrop-filter: blur(18px) saturate(118%);
}

.st-key-pay_sticky_controls > div[data-testid="stVerticalBlock"] {
    gap: .45rem;
}

.pay-brand-name {
    font-size: 15px;
    letter-spacing: -.02em;
}

.pay-brand-sub,
.pay-chip,
.pay-source,
.pay-section-kicker,
.pay-card-label {
    font-family: var(--pay-mono);
}

.pay-chip,
.pay-source {
    min-height: 31px;
    border-radius: 8px;
    background: rgba(12, 15, 19, .76);
}

.pay-source {
    color: #c9fae5;
    border-color: rgba(138, 246, 199, .22);
}

.pay-source::before {
    background: var(--pay-teal);
}

.pay-filter-note {
    margin: 4px 0 6px;
    border-color: rgba(203, 219, 233, .09);
    background: rgba(255, 255, 255, .018);
}

.pay-section-heading {
    grid-template-columns: minmax(0, 1.25fr) minmax(300px, .75fr);
    gap: 32px;
    margin-top: 16px;
    padding-top: 10px;
    border-top: 1px solid rgba(203, 219, 233, .08);
}

.pay-section-heading h2 {
    max-width: 710px;
    font-family: var(--pay-display);
    font-size: clamp(32px, 3.7vw, 48px);
    font-weight: 520;
    letter-spacing: -.045em;
    line-height: .98;
}

.pay-section-heading p {
    max-width: 470px;
    color: #8d99a5;
    font-size: 13px;
}

.pay-kpi-grid {
    grid-template-columns: 1.28fr .82fr .82fr;
    grid-template-areas:
        "primary second third"
        "primary fourth fourth";
    gap: 10px;
    perspective: 1200px;
}

.pay-kpi-card {
    --light-x: 88%;
    --light-y: 8%;
    min-height: 144px;
    border-radius: 16px;
    border-color: rgba(203, 219, 233, .1);
    background:
        linear-gradient(145deg, rgba(255, 255, 255, .025), transparent 54%),
        #0b0e12;
    box-shadow:var(--pay-depth-low),inset 0 1px rgba(255,255,255,.025),inset -8px -10px 24px rgba(0,0,0,.2);
    transform-style:preserve-3d;
    isolation:isolate;
}

.pay-kpi-card::before {
    content:"";
    position:absolute;
    inset:1px;
    z-index:0;
    border-radius:15px;
    pointer-events:none;
    opacity:.76;
    background:radial-gradient(circle at var(--light-x) var(--light-y),color-mix(in srgb,var(--tone) 15%,transparent),transparent 34%);
    border-right:1px solid rgba(203,219,233,.035);
    border-bottom:1px solid rgba(203,219,233,.04);
    transition:opacity var(--pay-ui) ease;
}

.pay-kpi-card>*{position:relative;z-index:1;transform:translateZ(8px)}

.pay-kpi-card:nth-child(1) {
    grid-area: primary;
    min-height: 298px;
    justify-content: flex-end;
    background:
        radial-gradient(circle at 90% 10%, rgba(78, 114, 255, .2), transparent 20rem),
        linear-gradient(145deg, rgba(104, 220, 255, .055), transparent 52%),
        #0b0e12;
}

.pay-kpi-card:nth-child(2) { grid-area: second; }
.pay-kpi-card:nth-child(3) { grid-area: third; }
.pay-kpi-card:nth-child(4) { grid-area: fourth; }

.pay-kpi-card::after {
    height: 2px;
    background: linear-gradient(90deg, var(--tone), transparent 74%);
}

.pay-kpi-value {
    font-family: var(--pay-display);
    font-weight: 520;
    letter-spacing: -.055em;
}

.pay-kpi-card:nth-child(1) .pay-kpi-value {
    font-size: clamp(62px, 7vw, 96px);
}

.pay-kpi-card p {
    max-width: 340px;
}

.pay-status-card,
div[data-testid="stMetric"],
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"],
details {
    border-color: rgba(203, 219, 233, .1) !important;
    background: #0b0e12 !important;
    box-shadow: none !important;
}

div[data-testid="stMetric"] {
    --light-x:88%;
    --light-y:8%;
    min-height: 124px;
    padding: 18px !important;
    border: 1px solid rgba(203, 219, 233, .1);
    border-radius: 14px;
    background:radial-gradient(circle at var(--light-x) var(--light-y),rgba(104,220,255,.07),transparent 38%),#0b0e12!important;
    box-shadow:var(--pay-depth-low),inset 0 1px rgba(255,255,255,.025)!important;
    transition:transform var(--pay-ui) ease,border-color var(--pay-ui) ease!important;
}

div[data-testid="stMetric"]:hover{transform:translateY(-2px);border-color:rgba(104,220,255,.25)!important}

div[data-testid="stMetricLabel"] {
    color: #8d99a5;
    font-family: var(--pay-mono);
    font-size: 11px;
    letter-spacing: .07em;
    text-transform: uppercase;
}

div[data-testid="stMetricValue"] {
    color: #f1f3ef;
    font-family: var(--pay-display);
    font-weight: 520;
    letter-spacing: -.04em;
}

.pay-metric-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 8px;
    margin: 18px 0 22px;
}

.pay-readout {
    --tone: var(--pay-cyan);
    position: relative;
    min-width: 0;
    min-height: 126px;
    overflow: hidden;
    padding: 17px;
    border: 1px solid rgba(203, 219, 233, .095);
    border-radius: 13px;
    background:
        linear-gradient(145deg, rgba(255, 255, 255, .022), transparent 56%),
        #0b0e12;
    box-shadow: inset 0 1px rgba(255, 255, 255, .022);
}

.pay-readout::before {
    content: "";
    position: absolute;
    top: 0;
    left: 17px;
    width: 42px;
    height: 1px;
    background: var(--tone);
    box-shadow: 0 0 9px color-mix(in srgb, var(--tone) 45%, transparent);
}

.pay-readout.cyan { --tone: var(--pay-cyan); }
.pay-readout.teal { --tone: var(--pay-teal); }
.pay-readout.amber { --tone: var(--pay-amber); }
.pay-readout.coral { --tone: var(--pay-coral); }
.pay-readout.violet { --tone: var(--pay-violet); }

.pay-readout-label {
    display: block;
    color: #7d8993;
    font-family: var(--pay-mono);
    font-size: 10px;
    letter-spacing: .075em;
    text-transform: uppercase;
}

.pay-readout strong {
    display: block;
    margin-top: 18px;
    overflow-wrap: anywhere;
    color: var(--pay-ink);
    font-family: var(--pay-display);
    font-size: clamp(28px, 3vw, 40px);
    font-weight: 520;
    letter-spacing: -.045em;
    line-height: 1;
}

.pay-readout p {
    margin: 10px 0 0;
    color: #7c8993;
    font-size: 11px;
    line-height: 1.4;
}

div[data-testid="stPlotlyChart"] {
    overflow: hidden;
    padding: 8px;
    border: 1px solid rgba(203, 219, 233, .1);
    border-radius: 18px;
    box-shadow:var(--pay-depth-panel),inset 0 1px rgba(255,255,255,.025)!important;
}

.pay-status-card {
    border-radius: 16px;
}

.pay-status-track {
    height: 13px;
    border-radius: 4px;
    background: rgba(255, 255, 255, .035);
}

.pay-status-segment {
    border-radius: 3px;
}

.pay-settlement-corridor {
    position:relative;
    overflow:hidden;
    margin:18px 0 22px;
    padding:20px;
    border:1px solid rgba(203,219,233,.11);
    border-radius:18px;
    background:linear-gradient(150deg,rgba(14,18,24,.98),rgba(7,9,12,.99));
    box-shadow:var(--pay-depth-panel),inset 0 1px rgba(255,255,255,.025);
}

.pay-settlement-corridor::before {
    content:"";
    position:absolute;
    inset:0;
    pointer-events:none;
    opacity:.18;
    background-image:linear-gradient(rgba(104,220,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(104,220,255,.05) 1px,transparent 1px);
    background-size:34px 34px;
    mask-image:linear-gradient(90deg,#000,transparent 76%);
}

.pay-corridor-head,.pay-corridor-lanes{position:relative;z-index:1}
.pay-corridor-head{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:14px}
.pay-corridor-head strong{font-family:var(--pay-display);font-size:18px;font-weight:560}
.pay-corridor-head span{color:var(--pay-muted);font-family:var(--pay-mono);font-size:10px;letter-spacing:.07em;text-transform:uppercase}
.pay-corridor-lanes{display:grid;grid-template-columns:1.4fr .8fr .64fr;gap:8px}
.pay-corridor-lane{
    --lane:#68dcff;
    position:relative;
    min-height:146px;
    overflow:hidden;
    padding:15px;
    border:1px solid rgba(203,219,233,.1);
    border-radius:13px;
    background:linear-gradient(145deg,rgba(255,255,255,.026),transparent 58%),rgba(6,9,12,.88);
    outline:none;
    transition:transform var(--pay-ui) ease,border-color var(--pay-ui) ease,box-shadow var(--pay-ui) ease;
}
.pay-corridor-lane::before{
    content:"";position:absolute;inset:0;pointer-events:none;opacity:0;
    background:linear-gradient(105deg,transparent 22%,color-mix(in srgb,var(--lane) 14%,transparent),transparent 70%);
    transform:translateX(-90%);transition:transform 520ms ease,opacity var(--pay-ui) ease;
}
.pay-corridor-lane:hover,.pay-corridor-lane:focus-visible{
    transform:translateY(-3px);border-color:color-mix(in srgb,var(--lane) 48%,transparent);
    box-shadow:var(--pay-depth-focus);
}
.pay-corridor-lane:hover::before,.pay-corridor-lane:focus-visible::before{opacity:1;transform:translateX(82%)}
.pay-lane-index{display:block;color:#71808b;font-family:var(--pay-mono);font-size:10px;letter-spacing:.08em}
.pay-lane-main{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-top:19px}
.pay-lane-main b{color:#e9efed;font-family:var(--pay-display);font-size:28px;font-weight:540;letter-spacing:-.04em}
.pay-lane-main strong{color:var(--lane);font-family:var(--pay-mono);font-size:10px;font-weight:560;letter-spacing:.08em;text-transform:uppercase}
.pay-lane-track{display:block;height:3px;margin:15px 0 10px;background:rgba(255,255,255,.04)}
.pay-lane-track i{display:block;height:100%;width:var(--share);max-width:100%;background:var(--lane);box-shadow:0 0 12px color-mix(in srgb,var(--lane) 48%,transparent)}
.pay-corridor-lane p{margin:0;color:#84919b;font-size:11px}

@media(max-width:700px){
    .pay-corridor-head{align-items:flex-start;flex-direction:column;gap:5px}
    .pay-corridor-lanes{grid-template-columns:1fr}
    .pay-corridor-lane{min-height:126px}
}

.pay-method-grid {
    gap: 10px;
}

.pay-method-card {
    border-radius: 14px;
    background: #0b0e12;
}

.pay-footer {
    border-color: rgba(203, 219, 233, .08);
    font-family: var(--pay-mono);
}

div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stMultiSelect"] > div > div,
button[kind="secondary"],
button[kind="primary"] {
    border-radius: 10px !important;
}

div[data-testid="stSegmentedControl"] {
    max-width: 420px;
    margin-top: 18px;
}

@media (max-width: 900px) {
    .pay-top-meta {
        width: 100%;
        justify-content: flex-start;
    }
    .pay-kpi-grid {
        grid-template-columns: 1fr 1fr;
        grid-template-areas:
            "primary primary"
            "second third"
            "fourth fourth";
    }
    .pay-kpi-card:nth-child(1) { min-height: 220px; }
}

@media (max-width: 640px) {
    .stMainBlockContainer,
    .block-container {
        padding-top: 4.1rem;
        padding-left: 14px;
        padding-right: 14px;
    }
    .pay-topbar {
        align-items: center;
        flex-direction: row;
        gap: 10px;
    }
    .pay-top-meta {
        width: auto;
        margin-left: auto;
    }
    .st-key-pay_sticky_controls {
        top: 6px;
        margin-inline: -5px;
        padding: 4px;
        border-radius: 16px;
    }
    .pay-top-meta .pay-chip {
        display: none;
    }
    .pay-brand-sub {
        display: none;
    }
    .pay-brand-mark {
        width: 38px;
        height: 38px;
    }
    .pay-kpi-grid {
        grid-template-columns: 1fr;
        grid-template-areas: "primary" "second" "third" "fourth";
    }
    .pay-kpi-card:nth-child(1) { min-height: 190px; }
    .pay-section-heading h2 { font-size: 38px; }
    .pay-metric-strip { grid-template-columns: 1fr 1fr; }
    .pay-readout { min-height: 116px; padding: 15px; }
    .pay-readout strong { font-size: 29px; }
}

@media (max-width: 430px) {
    .pay-metric-strip { grid-template-columns: 1fr; }
    .pay-readout { min-height: 108px; }
}
</style>
"""


PAGE_MOTION_JS = """
export default function() {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;
  const reveals = [...document.querySelectorAll(".pay-reveal")];
  const brandMark = document.querySelector("[data-brand-mark]");
  let observer = null;
  let revealWatcher = null;
  let brandTimer = null;

  let brandSeen = false;
  try { brandSeen = sessionStorage.getItem("payment-observatory-brand-seen-v1") === "1"; } catch (_) {}
  if (brandMark && !reduced && !brandSeen) {
    requestAnimationFrame(() => brandMark.classList.add("is-intro"));
    brandTimer = window.setTimeout(() => brandMark.classList.remove("is-intro"), 820);
    try { sessionStorage.setItem("payment-observatory-brand-seen-v1", "1"); } catch (_) {}
  }

  if (!reduced && "IntersectionObserver" in window) {
    root.classList.add("pay-motion-ready");
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("pay-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -5% 0px" });
    const track = element => {
      if (!element.classList.contains("pay-visible")) observer.observe(element);
    };
    reveals.forEach(track);
    // A rerun (switching view, changing scope) replaces these nodes, so the
    // observer must pick up the blocks Streamlit mounts after this point.
    // Without it they keep the hidden reveal state and hold empty space.
    revealWatcher = new MutationObserver(records => {
      records.forEach(record => {
        record.addedNodes.forEach(node => {
          if (node.nodeType !== 1) return;
          if (node.classList.contains("pay-reveal")) track(node);
          node.querySelectorAll?.(".pay-reveal").forEach(track);
        });
      });
    });
    revealWatcher.observe(document.body, { childList: true, subtree: true });
  } else {
    reveals.forEach(element => element.classList.add("pay-visible"));
  }

  const progress = document.querySelector(".pay-progress-fill");
  // Streamlit scrolls the main section, not the app view container, so the
  // progress rail has to bind to whichever ancestor actually overflows.
  const scrollCandidates = [
    document.querySelector('[data-testid="stMain"]'),
    document.querySelector('[data-testid="stAppViewContainer"]'),
  ];
  const scrollTarget =
    scrollCandidates.find(el => el && el.scrollHeight > el.clientHeight) || window;
  function updateProgress() {
    if (!progress) return;
    const scrolling = scrollTarget === window ? document.documentElement : scrollTarget;
    const maximum = Math.max(1, scrolling.scrollHeight - scrolling.clientHeight);
    progress.style.transform = `scaleX(${Math.min(1, Math.max(0, scrolling.scrollTop / maximum))})`;
  }
  scrollTarget.addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();

  let counted = false;
  try { counted = sessionStorage.getItem("pay-kpis-counted") === "1"; } catch (_) {}
  const numberNodes = [...document.querySelectorAll(".pay-kpi-value[data-number]")];
  if (!reduced && !counted) {
    const start = performance.now();
    const duration = 760;
    function frame(now) {
      const progressValue = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progressValue, 3);
      numberNodes.forEach(node => {
        const value = Number(node.dataset.number || 0) * eased;
        const decimals = Number(node.dataset.decimals || 0);
        const prefix = node.dataset.prefix || "";
        const suffix = node.dataset.suffix || "";
        node.textContent = prefix + new Intl.NumberFormat("en-IE", {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals
        }).format(value) + suffix;
      });
      if (progressValue < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    try { sessionStorage.setItem("pay-kpis-counted", "1"); } catch (_) {}
  }

  const lightHandlers = new Map();
  if (!reduced && window.matchMedia("(pointer: fine)").matches) {
    document.querySelectorAll('.pay-kpi-card,div[data-testid="stMetric"]').forEach(card => {
      const move = event => {
        const rect=card.getBoundingClientRect();
        const x=Math.max(0,Math.min(100,(event.clientX-rect.left)/rect.width*100));
        const y=Math.max(0,Math.min(100,(event.clientY-rect.top)/rect.height*100));
        card.style.setProperty("--light-x",`${x.toFixed(1)}%`);
        card.style.setProperty("--light-y",`${y.toFixed(1)}%`);
      };
      const leave = () => {
        card.style.setProperty("--light-x","88%");
        card.style.setProperty("--light-y","8%");
      };
      card.addEventListener("pointermove",move,{passive:true});
      card.addEventListener("pointerleave",leave);
      lightHandlers.set(card,{move,leave});
    });
  }

  return () => {
    observer?.disconnect();
    revealWatcher?.disconnect();
    if (brandTimer) window.clearTimeout(brandTimer);
    brandMark?.classList.remove("is-intro");
    scrollTarget.removeEventListener("scroll", updateProgress);
    lightHandlers.forEach(({move,leave},card) => {
      card.removeEventListener("pointermove",move);
      card.removeEventListener("pointerleave",leave);
    });
    root.classList.remove("pay-motion-ready");
  };
}
"""


OBSERVATORY_RAIL_HTML = """
<section class="observatory" aria-labelledby="observatory-title" data-sequence="idle" data-phase="idle">
  <header class="hero-band">
    <div class="hero-copy">
      <div class="eyebrow"><span></span> Payment system / 2022&mdash;2024</div>
      <h1 id="observatory-title">See the system behind <em>80,000 payments</em></h1>
      <p>Trace volume, settlement, review and retention across the payment lifecycle.</p>
    </div>
    <div class="hero-status" aria-label="System status">
      <span class="source-pill"><i></i><b data-value="source">Repository CSV snapshot</b></span>
      <span><small>Observed window</small><b data-value="window">Feb 2022 to Dec 2024</b></span>
      <span><small>Data model</small><b>6 linked tables</b></span>
    </div>
  </header>

  <div class="rail-shell">
    <div class="rail-head">
      <div>
        <small>Payment lifecycle</small>
        <strong>Follow the links behind each transaction</strong>
      </div>
      <div class="trace-controls">
        <span class="trace-state"><i></i><span id="trace-status" aria-live="polite">System trace ready</span></span>
        <button class="trace-replay" id="replay-trace" type="button" aria-label="Replay system trace">
          <svg viewBox="0 0 18 18" aria-hidden="true"><path d="M14.5 6.2A6 6 0 1 0 15 10M14.5 2.8v3.7h-3.7"/></svg>
          <span>Replay system trace</span>
        </button>
      </div>
    </div>

    <div class="rail-stage" id="payment-rail" tabindex="-1">
      <div class="scene-plane">
        <div class="perspective-field" aria-hidden="true"></div>
        <div class="scan-light" aria-hidden="true"></div>
        <div class="calibration-frame" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
        <svg class="route-map" viewBox="0 0 1000 520" role="img" aria-label="Payment lifecycle routes">
          <defs>
            <linearGradient id="route-cool" x1="0" x2="1">
              <stop offset="0" stop-color="#4e72ff"/>
              <stop offset=".55" stop-color="#68dcff"/>
              <stop offset="1" stop-color="#8af6c7"/>
            </linearGradient>
            <linearGradient id="route-mint" x1="0" x2="1">
              <stop offset="0" stop-color="#68dcff"/>
              <stop offset="1" stop-color="#8af6c7"/>
            </linearGradient>
            <linearGradient id="route-coral" x1="0" x2="1">
              <stop offset="0" stop-color="#68dcff"/>
              <stop offset="1" stop-color="#ff756f"/>
            </linearGradient>
            <filter id="route-glow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="3" result="blur"/>
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <marker id="arrow-cool" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0 L8 4 L0 8 Z" fill="#68dcff"/>
            </marker>
            <marker id="arrow-mint" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0 L8 4 L0 8 Z" fill="#8af6c7"/>
            </marker>
            <marker id="arrow-coral" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0 L8 4 L0 8 Z" fill="#ff756f"/>
            </marker>
          </defs>
          <path id="route-customers-accounts" class="route route-in" data-from="customers" data-to="accounts" d="M155 260 C215 260 240 260 300 260"/>
          <path id="route-accounts-transactions" class="route route-in" data-from="accounts" data-to="transactions" d="M350 260 C410 260 440 260 490 260"/>
          <path id="route-transactions-merchants" class="route route-out" data-from="transactions" data-to="merchants" d="M610 260 C680 260 700 120 790 120"/>
          <path id="route-transactions-settlements" class="route route-settlement" data-from="transactions" data-to="settlements" d="M610 260 C690 260 710 260 790 260"/>
          <path id="route-transactions-flags" class="route route-risk" data-from="transactions" data-to="flags" d="M610 260 C680 260 700 400 790 400"/>
        </svg>
        <div class="payment-token" aria-hidden="true"><span></span></div>

        <div class="rail-layout">
          <div class="node-group inbound-stack">
            <span class="group-label">Inbound records</span>
            <button class="rail-node customers" data-node="customers" type="button" aria-pressed="false">
              <span class="node-index">01</span><small>Customers</small>
              <strong data-value="customers">5,000</strong><span class="node-note">Customer records</span>
            </button>
            <button class="rail-node accounts" data-node="accounts" type="button" aria-pressed="false">
              <span class="node-index">02</span><small>Accounts</small>
              <strong data-value="accounts">6,000</strong><span class="node-note">Account records</span>
            </button>
          </div>

          <button class="rail-node transactions core" data-node="transactions" type="button" aria-pressed="false">
            <span class="reactor-visual" aria-hidden="true">
              <canvas class="reactor-canvas" id="transaction-reactor"></canvas>
              <span class="reactor-fallback"><i></i><i></i><i></i></span>
            </span>
            <span class="core-orbits" aria-hidden="true"><i></i><i></i><i></i></span>
            <span class="core-scan" aria-hidden="true"></span>
            <span class="node-index">03</span><small>Transactions</small>
            <strong data-value="transactions">80,000</strong>
            <span class="node-note">Purchases, refunds and transfers</span>
          </button>

          <div class="node-group outcome-stack">
            <span class="group-label">Linked outcomes</span>
            <button class="rail-node merchants" data-node="merchants" type="button" aria-pressed="false">
              <span class="node-index">04</span><small>Merchants</small>
              <strong data-value="merchants">800</strong><span class="node-note">Optional on transfers</span>
            </button>
            <button class="rail-node settlements" data-node="settlements" type="button" aria-pressed="false">
              <span class="node-index">05</span><small>Settlements</small>
              <strong data-value="settlements">61,124</strong><span class="node-note">Unique when present</span>
            </button>
            <button class="rail-node flags" data-node="flags" type="button" aria-pressed="false">
              <span class="node-index">06</span><small>Fraud flags</small>
              <strong data-value="flags">2,500</strong><span class="node-note">Unique when present</span>
            </button>
          </div>
        </div>
      </div>
      <span class="stage-coordinate coordinate-left" aria-hidden="true">SYS / 80K</span>
      <span class="stage-coordinate coordinate-right" aria-hidden="true">REL / 05</span>
    </div>

    <div class="trace-timeline" id="trace-timeline" role="progressbar" aria-label="Payment system trace" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
      <span data-trace-phase="inbound"><i></i><b>Inbound</b><small>Customer to account</small></span>
      <span data-trace-phase="core"><i></i><b>Core</b><small>Transaction event</small></span>
      <span data-trace-phase="outcomes"><i></i><b>Outcomes</b><small>Merchant, settlement and review</small></span>
      <em aria-hidden="true"><i id="trace-progress"></i></em>
    </div>

  </div>

  <div class="proof-strip" aria-label="System profile">
    <span><small>Event volume</small><strong data-proof="transactions">80,000 transactions</strong></span>
    <span><small>Settlements</small><strong data-value="settlements">61,124</strong></span>
    <span><small>Review records</small><strong data-value="flags">2,500</strong></span>
    <span><small>Runtime</small><strong>PostgreSQL + Python</strong></span>
    <span><small>Continuity</small><strong>Repository CSV fallback</strong></span>
  </div>
</section>
"""


OBSERVATORY_RAIL_CSS = """
:host {
  --canvas:#050607;--surface:#0b0e12;--line:rgba(203,219,233,.13);
  --ink:#f1f3ef;--muted:#8d99a5;--blue:#4e72ff;--cyan:#68dcff;
  --mint:#8af6c7;--coral:#ff756f;
  color:var(--ink);
  font-family:"Source Sans","Segoe UI Variable","Segoe UI",sans-serif;
}
*{box-sizing:border-box}
button{font:inherit}
.observatory{
  position:relative;container-type:inline-size;display:grid;gap:16px;
  overflow:hidden;padding:clamp(24px,2.35vw,30px);border:1px solid var(--line);border-radius:28px;
  background:
    radial-gradient(circle at 86% 4%,rgba(78,114,255,.2),transparent 34rem),
    radial-gradient(circle at 4% 66%,rgba(104,220,255,.07),transparent 30rem),
    linear-gradient(150deg,rgba(15,19,25,.985),rgba(5,7,9,.998));
  box-shadow:0 38px 110px rgba(0,0,0,.38);isolation:isolate;
}
.observatory::before{
  content:"";position:absolute;inset:0;pointer-events:none;opacity:.2;
  background-image:linear-gradient(rgba(190,212,228,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(190,212,228,.04) 1px,transparent 1px);
  background-size:64px 64px;mask-image:linear-gradient(105deg,#000 0%,transparent 76%);
}
.observatory::after{
  content:"";position:absolute;width:560px;height:560px;top:-430px;right:-210px;
  border:1px solid rgba(104,220,255,.13);border-radius:50%;
  box-shadow:0 0 0 54px rgba(104,220,255,.018),0 0 0 112px rgba(104,220,255,.012);
}
.hero-band,.rail-shell,.proof-strip{position:relative;z-index:1}
.hero-band{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,auto);align-items:end;gap:clamp(26px,4vw,70px)}
.hero-copy{max-width:950px}
.eyebrow{display:flex;align-items:center;gap:10px;color:#9cb0ff;font-family:"Source Code Pro",Consolas,monospace;font-size:11px;font-weight:620;letter-spacing:.13em;text-transform:uppercase}
.eyebrow span{width:32px;height:1px;background:linear-gradient(90deg,var(--blue),var(--cyan));box-shadow:0 0 10px rgba(104,220,255,.5)}
h1{
  max-width:840px;margin:12px 0 10px;font-family:"space-grotesk","Source Sans","Segoe UI Variable",sans-serif;
  font-size:clamp(46px,5.1vw,64px);font-size:clamp(46px,5.6cqi,64px);font-weight:520;
  letter-spacing:-.06em;line-height:.94;text-wrap:balance;
}
h1 em{
  color:transparent;font-style:normal;background:linear-gradient(92deg,#a9bcff 4%,#68dcff 52%,#8af6c7);
  background-clip:text;-webkit-background-clip:text;filter:drop-shadow(0 0 22px rgba(104,220,255,.1));
}
.hero-copy>p{max-width:650px;margin:0;color:#9ba6af;font-size:clamp(14px,1.3vw,17px);line-height:1.65}
.hero-status{display:grid;min-width:220px;border-top:1px solid var(--line)}
.hero-status>span{display:grid;grid-template-columns:1fr;gap:4px;min-height:52px;padding:10px 2px;border-bottom:1px solid var(--line)}
.hero-status small{color:#77848f;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.09em;text-transform:uppercase}
.hero-status b{color:#d3dadb;font-family:"Source Code Pro",Consolas,monospace;font-size:11px;font-weight:520}
.hero-status .source-pill{display:flex;align-items:center;grid-template-columns:auto 1fr;gap:9px}
.source-pill i{width:6px;height:6px;border-radius:50%;background:var(--mint);box-shadow:0 0 12px rgba(138,246,199,.8)}
.source-pill b{color:#d7f9e9}
.rail-shell{min-width:0;padding:12px;border:1px solid rgba(203,219,233,.15);border-radius:22px;background:rgba(4,6,8,.66);box-shadow:inset 0 1px rgba(255,255,255,.025),0 28px 70px rgba(0,0,0,.28)}
.rail-head{display:flex;align-items:flex-end;justify-content:space-between;gap:18px;padding:4px 8px 9px}
.rail-head small{display:block;color:#8ca6ff;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.11em;text-transform:uppercase}
.rail-head strong{display:block;margin-top:4px;color:#dfe5e6;font-family:"space-grotesk","Source Sans",sans-serif;font-size:15px;font-weight:560}
.trace-controls{display:flex;align-items:center;justify-content:flex-end;gap:12px}
.trace-state{display:flex;align-items:center;gap:7px;color:#7f8c96;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;white-space:nowrap}
.trace-state i{width:5px;height:5px;border-radius:50%;background:var(--cyan);box-shadow:0 0 9px rgba(104,220,255,.8);transition:background 190ms ease,box-shadow 190ms ease}
.trace-replay{display:flex;align-items:center;gap:7px;min-height:36px;padding:7px 10px;border:1px solid rgba(104,220,255,.18);border-radius:8px;background:linear-gradient(135deg,rgba(78,114,255,.11),rgba(104,220,255,.035));color:#cbd9dc;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;letter-spacing:.035em;cursor:pointer;transition:transform 120ms ease,border-color 190ms ease,background 190ms ease,color 190ms ease}
.trace-replay svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.35;stroke-linecap:round;stroke-linejoin:round}
.trace-replay:hover{border-color:rgba(104,220,255,.36);background:linear-gradient(135deg,rgba(78,114,255,.18),rgba(104,220,255,.055));color:#eef6f5}
.trace-replay:active{transform:scale(.98)}
.trace-replay:focus-visible{border-color:rgba(104,220,255,.56);outline:2px solid rgba(78,114,255,.22);outline-offset:2px}
.observatory[data-sequence="playing"] .trace-state i{background:var(--mint);box-shadow:0 0 12px rgba(138,246,199,.8)}
.observatory[data-sequence="paused"] .trace-state i{background:#f5bb62;box-shadow:0 0 10px rgba(245,187,98,.55)}
.rail-stage{
  --tilt-x:0deg;--tilt-y:0deg;position:relative;min-height:330px;overflow:hidden;
  border:1px solid rgba(203,219,233,.085);border-radius:16px;
  background:radial-gradient(circle at 53% 50%,rgba(78,114,255,.15),transparent 26%),linear-gradient(180deg,#080b10 0%,#05070a 100%);
  perspective:1400px;outline:none;
}
.rail-stage::before{
  content:"";position:absolute;inset:0;z-index:0;pointer-events:none;
  background:linear-gradient(90deg,rgba(104,220,255,.04),transparent 25%,transparent 75%,rgba(138,246,199,.025)),repeating-linear-gradient(90deg,transparent 0 118px,rgba(177,201,219,.035) 119px 120px);
}
.scene-plane{
  position:absolute;inset:0;transform:perspective(1400px) rotateX(var(--tilt-x)) rotateY(var(--tilt-y));
  transform-style:preserve-3d;transition:transform 190ms cubic-bezier(.2,.8,.2,1);will-change:transform;
}
.perspective-field{
  position:absolute;z-index:0;width:120%;height:105%;left:-10%;top:36%;opacity:.2;
  background-image:linear-gradient(rgba(104,220,255,.11) 1px,transparent 1px),linear-gradient(90deg,rgba(104,220,255,.11) 1px,transparent 1px);
  background-size:56px 34px;transform:rotateX(68deg) translateZ(-80px);transform-origin:center top;
  mask-image:linear-gradient(to bottom,transparent,#000 18%,#000 68%,transparent 96%);animation:grid-drift 18s linear infinite;pointer-events:none;transition:opacity 460ms ease;
}
@keyframes grid-drift{from{background-position:0 0}to{background-position:0 68px}}
.scan-light{
  position:absolute;z-index:1;width:18%;height:100%;left:-22%;top:0;opacity:0;
  background:linear-gradient(90deg,transparent,rgba(104,220,255,.14),rgba(255,255,255,.025),transparent);filter:blur(5px);
  transform:skewX(-10deg) translateZ(-20px);pointer-events:none;
}
@keyframes scan-pass{
  0%{transform:skewX(-10deg) translate3d(0,0,-20px);opacity:0}
  18%,72%{opacity:.24}
  100%{transform:skewX(-10deg) translate3d(690%,0,-20px);opacity:0}
}
.observatory[data-sequence="playing"] .perspective-field{opacity:.34}
.observatory[data-sequence="playing"] .scan-light{animation:scan-pass 2.6s cubic-bezier(.45,0,.2,1) 1 both}
.calibration-frame{position:absolute;z-index:1;inset:13px;pointer-events:none;opacity:.34}
.calibration-frame::before,.calibration-frame::after,.calibration-frame i{content:"";position:absolute;width:24px;height:24px;border-color:rgba(104,220,255,.35);opacity:.42}
.calibration-frame::before{left:0;top:0;border-left:1px solid;border-top:1px solid}
.calibration-frame::after{right:0;bottom:0;border-right:1px solid;border-bottom:1px solid}
.calibration-frame i:nth-child(1){right:0;top:0;border-right:1px solid;border-top:1px solid}
.calibration-frame i:nth-child(2){left:0;bottom:0;border-left:1px solid;border-bottom:1px solid}
.calibration-frame i:nth-child(3){left:50%;top:0;width:1px;height:8px;background:rgba(104,220,255,.3)}
.calibration-frame i:nth-child(4){left:50%;bottom:0;width:1px;height:8px;background:rgba(104,220,255,.3)}
.observatory[data-sequence="playing"] .calibration-frame{animation:calibrate-frame 700ms ease-out both}
@keyframes calibrate-frame{from{opacity:0;transform:scale(.985)}to{opacity:.5;transform:none}}
.route-map{position:absolute;inset:0;z-index:2;width:100%;height:100%;overflow:visible;pointer-events:none;transform:translateZ(6px)}
.route{fill:none;vector-effect:non-scaling-stroke;stroke:url(#route-cool);stroke-width:1.35;stroke-opacity:.38;marker-end:url(#arrow-cool);transition:opacity 190ms ease,stroke 190ms ease,stroke-width 190ms ease}
.route.route-settlement{stroke:url(#route-mint);marker-end:url(#arrow-mint)}
.route.route-risk{stroke:url(#route-coral);marker-end:url(#arrow-coral)}
.route.is-active{stroke-width:2.4;stroke-opacity:1;filter:url(#route-glow)}
.route.is-muted{opacity:.08}
.payment-token{
  position:absolute;z-index:5;width:9px;height:9px;left:0;top:0;offset-anchor:50% 50%;offset-rotate:0deg;opacity:0;
  border:1px solid rgba(255,255,255,.8);border-radius:50%;background:var(--cyan);box-shadow:0 0 5px #fff,0 0 16px rgba(104,220,255,.9);
}
.payment-token span{position:absolute;inset:-9px;border:1px solid rgba(104,220,255,.2);border-radius:50%}
.rail-layout{
  position:absolute;inset:34px 34px 30px;z-index:3;display:grid;
  grid-template-columns:minmax(310px,1.35fr) minmax(210px,.8fr) minmax(230px,1fr);
  align-items:center;gap:clamp(22px,3.5vw,52px);transform-style:preserve-3d;
}
.node-group{position:relative;display:grid;align-content:center;gap:10px;transform-style:preserve-3d}
.inbound-stack{grid-template-columns:repeat(2,minmax(130px,1fr));gap:16px}
.outcome-stack{grid-template-columns:1fr;gap:8px}
.group-label{grid-column:1/-1;color:#75838e;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase}
.rail-node{
  position:relative;z-index:3;width:100%;min-height:74px;padding:9px 12px;transform:translateZ(18px);transform-style:preserve-3d;
  border:1px solid rgba(203,219,233,.16);border-radius:14px;
  background:linear-gradient(145deg,rgba(255,255,255,.035),transparent 42%),linear-gradient(155deg,rgba(19,25,33,.97),rgba(7,10,13,.99));
  color:var(--ink);text-align:left;cursor:pointer;
  box-shadow:0 20px 40px rgba(0,0,0,.3),inset 0 1px rgba(255,255,255,.025);
  transition:opacity 190ms ease,transform 190ms ease,border-color 190ms ease,box-shadow 190ms ease;
}
.rail-node:hover,.rail-node:focus-visible,.rail-node.is-active{
  z-index:6;transform:translate3d(0,-4px,34px);border-color:rgba(104,220,255,.6);
  box-shadow:0 0 0 3px rgba(78,114,255,.08),0 24px 48px rgba(0,0,0,.38),0 0 30px rgba(78,114,255,.09);outline:none;
}
.rail-node.is-muted{opacity:.19}
.rail-node .node-index{position:absolute;top:10px;right:11px;color:#6f7c87;font-family:"Source Code Pro",Consolas,monospace;font-size:10px}
.rail-node small,.node-note{display:block;color:#9aa6af;font-size:11px;line-height:1.25}
.rail-node small{font-family:"Source Code Pro",Consolas,monospace;letter-spacing:.1em;text-transform:uppercase}
.rail-node strong{display:block;margin:5px 0 2px;color:#edf2f0;font-family:"space-grotesk","Source Sans",sans-serif;font-size:21px;font-weight:540;letter-spacing:-.045em;line-height:1}
.rail-node.core{
  justify-self:center;width:150px;height:150px;min-height:150px;padding:22px 16px;transform:translateZ(42px);
  border-color:rgba(104,220,255,.42);border-radius:50%;
  background:radial-gradient(circle at 50% 35%,rgba(104,220,255,.16),transparent 35%),radial-gradient(circle at 50% 60%,rgba(78,114,255,.28),transparent 68%),#090e15;
  text-align:center;box-shadow:0 0 0 12px rgba(78,114,255,.035),0 0 64px rgba(78,114,255,.18),inset 0 0 34px rgba(104,220,255,.055);
}
.rail-node.core:hover,.rail-node.core:focus-visible,.rail-node.core.is-active{transform:translate3d(0,-4px,56px)}
.rail-node.core>small,.rail-node.core>strong,.rail-node.core>.node-note{position:relative;z-index:5}
.rail-node.core .node-index{display:none}
.rail-node.core strong{font-size:25px}
.rail-node.core .node-note{max-width:130px;margin:0 auto;line-height:1.35}
.reactor-visual{
  position:absolute;z-index:1;inset:-48px;display:grid;place-items:center;pointer-events:none;
  border-radius:50%;opacity:.78;transform:translateZ(-4px);
  mask-image:radial-gradient(circle,#000 0 55%,rgba(0,0,0,.84) 68%,transparent 82%);
}
.reactor-canvas{
  position:absolute;inset:0;width:100%;height:100%;opacity:0;filter:drop-shadow(0 0 18px rgba(104,220,255,.22));
  transition:opacity 460ms ease;
}
.reactor-fallback,.reactor-fallback i{position:absolute;border-radius:50%}
.reactor-fallback{
  width:132px;height:132px;border:1px solid rgba(104,220,255,.2);
  background:radial-gradient(circle at 38% 31%,rgba(104,220,255,.18),transparent 24%),radial-gradient(circle,rgba(78,114,255,.19),rgba(6,10,16,.14) 58%,transparent 62%);
  box-shadow:inset -12px -14px 32px rgba(0,0,0,.42),0 0 34px rgba(78,114,255,.14);
  transition:opacity 460ms ease;
}
.reactor-fallback::before,.reactor-fallback::after{
  content:"";position:absolute;inset:-18px;border:1px solid rgba(104,220,255,.18);border-radius:50%;transform:rotateX(66deg) rotateZ(14deg);
}
.reactor-fallback::after{inset:-32px;border-color:rgba(138,246,199,.11);transform:rotateY(62deg) rotateZ(-18deg)}
.reactor-fallback i{inset:22px;border-top:1px solid rgba(156,176,255,.34);transform:rotate(35deg)}
.reactor-fallback i:nth-child(2){inset:38px;border-color:rgba(104,220,255,.25);transform:rotate(-24deg)}
.reactor-fallback i:nth-child(3){inset:55px;background:rgba(104,220,255,.08);box-shadow:0 0 24px rgba(104,220,255,.22)}
.observatory[data-reactor="ready"] .reactor-canvas{opacity:.9}
.observatory[data-reactor="ready"] .reactor-fallback{opacity:.08}
.observatory[data-reactor="fallback"] .reactor-fallback{opacity:.9}
.observatory[data-reactor="loading"] .reactor-fallback{opacity:.62}
.core-orbits,.core-orbits i,.core-scan{position:absolute;border-radius:50%;pointer-events:none}
.core-orbits{inset:-34px}
.core-orbits i{inset:0;border:1px dashed rgba(104,220,255,.18);animation:core-orbit 18s linear infinite}
.core-orbits i:nth-child(2){inset:12px;border-color:rgba(78,114,255,.24);animation-duration:13s;animation-direction:reverse}
.core-orbits i:nth-child(3){inset:25px;border-style:solid;border-color:rgba(138,246,199,.11);animation-duration:24s}
@keyframes core-orbit{to{transform:rotate(360deg)}}
.core-scan{inset:10px;overflow:hidden;border:1px solid rgba(104,220,255,.07)}
.core-scan::after{
  content:"";position:absolute;width:70%;height:1px;left:15%;top:50%;
  background:linear-gradient(90deg,transparent,var(--cyan),transparent);box-shadow:0 0 14px rgba(104,220,255,.7);
  animation:core-scan 4.8s ease-in-out infinite;
}
@keyframes core-scan{0%,100%{transform:translateY(-42px);opacity:.15}50%{transform:translateY(42px);opacity:.75}}
.stage-coordinate{position:absolute;z-index:5;bottom:12px;color:#65737e;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.11em;pointer-events:none}
.coordinate-left{left:14px}.coordinate-right{right:14px}
.trace-timeline{position:relative;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin:10px 8px 0;padding-bottom:5px;background:rgba(203,219,233,.06)}
.trace-timeline>span{position:relative;z-index:2;display:grid;grid-template-columns:auto 1fr;grid-template-rows:auto auto;column-gap:8px;min-height:42px;padding:6px 10px;background:#07090c;color:#687681;transition:background 190ms ease,color 190ms ease}
.trace-timeline>span>i{grid-row:1/3;align-self:center;width:7px;height:7px;border:1px solid rgba(203,219,233,.2);border-radius:50%;background:#11151b;transition:background 190ms ease,border-color 190ms ease,box-shadow 190ms ease}
.trace-timeline b{font-family:"Source Code Pro",Consolas,monospace;font-size:9px;font-weight:560;letter-spacing:.08em;text-transform:uppercase}
.trace-timeline small{font-size:10px}
.trace-timeline>span.is-active{background:linear-gradient(135deg,rgba(78,114,255,.09),rgba(104,220,255,.025));color:#bdc9ce}
.trace-timeline>span.is-active>i{border-color:var(--cyan);background:var(--cyan);box-shadow:0 0 10px rgba(104,220,255,.6)}
.trace-timeline>span.is-complete{color:#8ba29a}
.trace-timeline>span.is-complete>i{border-color:var(--mint);background:var(--mint)}
.trace-timeline>em{position:absolute;z-index:3;left:0;right:0;bottom:0;height:1px;background:rgba(203,219,233,.07);overflow:hidden}
.trace-timeline>em i{display:block;width:100%;height:100%;background:linear-gradient(90deg,var(--blue),var(--cyan),var(--mint));box-shadow:0 0 8px rgba(104,220,255,.55);transform:scaleX(0);transform-origin:left;transition:transform 190ms linear}
.relationship-console{padding:0 8px 3px}
.rail-readout{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:18px;min-height:64px;padding:10px 0}
.readout-signal{color:#95a1aa;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase}
.readout-signal i{display:inline-block;width:5px;height:5px;margin-right:6px;border-radius:50%;background:var(--cyan);box-shadow:0 0 8px rgba(104,220,255,.7)}
.rail-readout div strong{display:block;color:#e0e5e5;font-family:"space-grotesk","Source Sans",sans-serif;font-size:15px;font-weight:560}
.rail-readout p{margin:5px 0 0;color:#8f9ba4;font-size:11px;line-height:1.5}
.rail-readout>b{color:#c8d0d2;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;font-weight:520;white-space:nowrap}
.relation-ledger{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;padding-top:1px;background:rgba(203,219,233,.07)}
.relation-ledger span{min-height:88px;padding:16px 15px;background:#07090c;color:#89959e;font-size:11px;line-height:1.5;transition:opacity 190ms ease,background 190ms ease,color 190ms ease}
.relation-ledger b{display:block;margin-bottom:7px;color:#c3cbcd;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;font-weight:540;letter-spacing:.015em}
.relation-ledger span.is-active{background:rgba(78,114,255,.08);color:#aeb9c0}
.relation-ledger span.is-active b{color:#cceffc}
.relation-ledger span.is-muted{opacity:.2}
.proof-strip{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));border-top:1px solid var(--line)}
.proof-strip>span{padding:14px 14px 0;border-left:1px solid var(--line)}
.proof-strip>span:first-child{padding-left:0;border-left:0}
.proof-strip small,.proof-strip strong{display:block}
.proof-strip small{color:#7c8993;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase}
.proof-strip strong{margin-top:7px;color:#d8dddd;font-size:14px;font-weight:560}

@container (max-width:959px){
  .hero-band{grid-template-columns:1fr}
  .hero-status{grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--line)}
  .hero-status>span{padding:10px 12px;border-right:1px solid var(--line)}
  .hero-status>span:last-child{border-right:0}
  h1{max-width:820px}
  .rail-stage{min-height:390px}
  .rail-layout{inset:46px 28px 38px;grid-template-columns:minmax(150px,.8fr) minmax(170px,1fr) minmax(165px,.86fr);gap:24px}
  .inbound-stack{grid-template-columns:1fr;gap:10px}
  .rail-node.core{width:160px;height:160px;min-height:160px}
  .relation-ledger{grid-template-columns:repeat(2,minmax(0,1fr))}
  .relation-ledger span:last-child{grid-column:1/-1}
}
@container (max-width:679px){
  .observatory{gap:20px;padding:24px 18px;border-radius:20px}
  .hero-band{gap:18px}
  h1{margin-top:16px;font-size:clamp(42px,13.2cqi,58px);line-height:.95}
  .hero-copy>p{font-size:14px}
  .hero-status{grid-template-columns:1fr 1fr}
  .hero-status>span:first-child{grid-column:1/-1}
  .hero-status>span:nth-child(2){border-left:0}
  .rail-head{align-items:flex-start;flex-direction:column;gap:12px;padding-bottom:13px}
  .trace-controls{width:100%;justify-content:space-between}
  .trace-replay span{display:none}
  .rail-stage{min-height:0;overflow:visible}
  .scene-plane{position:relative;inset:auto;transform:none!important;will-change:auto}
  .perspective-field,.scan-light,.calibration-frame,.route-map,.payment-token,.stage-coordinate{display:none}
  .rail-layout{position:relative;inset:auto;display:grid;grid-template-columns:1fr;gap:16px;padding:22px 16px}
  .rail-layout::before{
    content:"";position:absolute;top:54px;bottom:54px;left:35px;width:1px;
    background:linear-gradient(var(--blue),var(--cyan),var(--mint),var(--coral));opacity:.55;box-shadow:0 0 9px rgba(104,220,255,.25);
  }
  .node-group{gap:14px}
  .inbound-stack,.outcome-stack{grid-template-columns:1fr}
  .group-label{padding-left:28px}
  .rail-node,.rail-node.core{position:relative;width:auto;height:auto;min-height:90px;padding:15px 14px 15px 42px;transform:none;border-radius:14px;text-align:left}
  .rail-node::before{
    content:"";position:absolute;left:14px;top:50%;width:7px;height:7px;transform:translateY(-50%);
    border:2px solid #07090c;border-radius:50%;background:var(--cyan);box-shadow:0 0 0 1px rgba(104,220,255,.45),0 0 10px rgba(104,220,255,.5);
  }
  .rail-node:hover,.rail-node:focus-visible,.rail-node.is-active,
  .rail-node.core:hover,.rail-node.core:focus-visible,.rail-node.core.is-active{transform:translateY(-2px)}
  .rail-node.core{justify-self:stretch;border-color:rgba(104,220,255,.42)}
  .rail-node.core{padding-left:76px}
  .rail-node.core::before{display:none}
  .rail-node.core strong{font-size:28px}
  .rail-node.core .node-note{max-width:none;margin:0}
  .core-orbits,.core-scan{display:none}
  .reactor-visual{inset:auto auto auto 8px;width:56px;height:56px;opacity:.72;transform:translateZ(0)}
  .reactor-canvas{display:none}
  .reactor-fallback{width:42px;height:42px}
  .reactor-fallback::before{inset:-5px}.reactor-fallback::after{inset:-10px}
  .reactor-fallback i{inset:7px}.reactor-fallback i:nth-child(2){inset:12px}.reactor-fallback i:nth-child(3){inset:17px}
  .rail-node .node-index{display:block;left:auto;right:12px;top:12px;color:#70808d}
  .observatory[data-sequence="playing"] .rail-layout::before{box-shadow:0 0 14px rgba(104,220,255,.42)}
  .trace-timeline{grid-template-columns:1fr;margin:9px 3px 0}
  .trace-timeline>span{min-height:47px}
  .rail-readout{grid-template-columns:1fr;gap:8px;align-items:start}
  .rail-readout>b{white-space:normal}
  .readout-signal{padding-top:2px}
  .relation-ledger{grid-template-columns:1fr}
  .relation-ledger span:last-child{grid-column:auto}
  .proof-strip{grid-template-columns:1fr 1fr}
  .proof-strip>span{padding:14px 10px;border-left:0;border-top:1px solid var(--line)}
  .proof-strip>span:nth-child(odd){padding-left:0}
}
@container (max-width:420px){
  .hero-status{grid-template-columns:1fr}
  .hero-status>span:first-child{grid-column:auto}
  .hero-status>span{border-right:0}
}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}
  .payment-token,.reactor-canvas,.scan-light{display:none}.scene-plane{transform:none!important}
  .reactor-fallback{opacity:.82!important}
}
.rail-stage.motion-paused .perspective-field,
.rail-stage.motion-paused .scan-light,
.rail-stage.motion-paused .core-orbits i,
.rail-stage.motion-paused .core-scan::after{animation-play-state:paused}
"""


OBSERVATORY_RAIL_JS = """
const OGL_ASSET = new URL("app/static/vendor/ogl/ogl.umd.js", document.baseURI).href;

function loadOGL() {
  if (window.ogl?.Renderer) return Promise.resolve(window.ogl);
  if (window.__paymentObservatoryOGL) return window.__paymentObservatoryOGL;
  window.__paymentObservatoryOGL = new Promise((resolve,reject) => {
    const script = document.createElement("script");
    script.src = OGL_ASSET;
    script.async = true;
    script.dataset.paymentObservatoryOgl = "0.0.42";
    script.onload = () => window.ogl?.Renderer ? resolve(window.ogl) : reject(new Error("OGL did not initialise"));
    script.onerror = () => reject(new Error("Local OGL asset unavailable"));
    document.head.appendChild(script);
  });
  return window.__paymentObservatoryOGL;
}

function icosahedronGeometry(gl,Geometry,radius=1) {
  const golden = (1 + Math.sqrt(5)) / 2;
  const source = [
    [-1,golden,0],[1,golden,0],[-1,-golden,0],[1,-golden,0],
    [0,-1,golden],[0,1,golden],[0,-1,-golden],[0,1,-golden],
    [golden,0,-1],[golden,0,1],[-golden,0,-1],[-golden,0,1]
  ].map(vertex => {
    const length = Math.hypot(...vertex);
    return vertex.map(value => value / length * radius);
  });
  const faces = [
    [0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],
    [1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],
    [3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],
    [4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]
  ];
  const positions = new Float32Array(faces.length * 9);
  const normals = new Float32Array(faces.length * 9);
  faces.forEach((face,faceIndex) => {
    const a=source[face[0]],b=source[face[1]],c=source[face[2]];
    const ab=[b[0]-a[0],b[1]-a[1],b[2]-a[2]];
    const ac=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];
    const normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];
    const normalLength=Math.hypot(...normal)||1;
    normal.forEach((value,index)=>normal[index]=value/normalLength);
    [a,b,c].forEach((vertex,vertexIndex) => {
      const offset=faceIndex*9+vertexIndex*3;
      positions.set(vertex,offset);normals.set(normal,offset);
    });
  });
  return new Geometry(gl,{position:{size:3,data:positions},normal:{size:3,data:normals}});
}

function circleGeometry(gl,Geometry,segments=96) {
  const positions = new Float32Array(segments * 3);
  for (let index=0; index<segments; index+=1) {
    const angle=index/segments*Math.PI*2;
    positions[index*3]=Math.cos(angle)*1.42;
    positions[index*3+1]=Math.sin(angle)*1.42;
  }
  return new Geometry(gl,{position:{size:3,data:positions}});
}

function createPaymentReactor(canvas,container,ogl,compact=false) {
  const {Renderer,Camera,Transform,Geometry,Program,Mesh}=ogl;
  const renderer = new Renderer({
    canvas,width:300,height:300,dpr:compact?1:Math.min(window.devicePixelRatio||1,1.25),
    alpha:true,depth:true,antialias:!compact,premultipliedAlpha:true,powerPreference:"low-power"
  });
  const gl=renderer.gl;
  if (!gl) throw new Error("WebGL unavailable");
  gl.clearColor(0,0,0,0);
  const camera=new Camera(gl,{fov:34,near:.1,far:40});
  camera.position.set(0,0,5.1);
  const scene=new Transform();
  const reactor=new Transform();
  reactor.setParent(scene);
  const colors={
    customers:[.31,.45,1],accounts:[.36,.76,1],transactions:[.40,.86,1],
    merchants:[.42,.82,1],settlements:[.54,.96,.78],flags:[1,.46,.44]
  };
  const rotations={
    customers:[-.12,-.3],accounts:[-.06,-.18],transactions:[0,0],
    merchants:[-.18,.32],settlements:[0,.34],flags:[.2,.32]
  };
  const currentColor=new Float32Array(colors.transactions);
  let targetColor=colors.transactions.slice();
  let focusKey=null;
  let focusRotation=[0,0];
  let pointerRotation=[0,0];
  let pulseEnergy=0;
  let pulseScale=-1;
  let pulseTimer=null;
  let running=false;
  let destroyed=false;
  let frameId=null;
  let previousFrame=0;

  const vertex=`
    attribute vec3 position;
    attribute vec3 normal;
    uniform mat4 modelViewMatrix;
    uniform mat4 projectionMatrix;
    uniform mat3 normalMatrix;
    varying vec3 vNormal;
    varying vec3 vView;
    varying vec3 vPosition;
    void main(){
      vec4 viewPosition=modelViewMatrix*vec4(position,1.0);
      vNormal=normalize(normalMatrix*normal);
      vView=normalize(-viewPosition.xyz);
      vPosition=position;
      gl_Position=projectionMatrix*viewPosition;
    }
  `;
  const fragment=`
    precision highp float;
    uniform vec3 uColor;
    uniform float uTime;
    uniform float uPulse;
    varying vec3 vNormal;
    varying vec3 vView;
    varying vec3 vPosition;
    void main(){
      float rim=pow(1.0-max(dot(normalize(vNormal),normalize(vView)),0.0),2.15);
      float signal=.5+.5*sin((vPosition.x-vPosition.y+vPosition.z)*7.0+uTime*.42);
      vec3 graphite=vec3(.018,.035,.055);
      vec3 colour=mix(graphite,uColor,.2+rim*.74+signal*.06+uPulse*.12);
      float alpha=.34+rim*.48+uPulse*.12;
      gl_FragColor=vec4(colour,alpha);
    }
  `;
  const sphereProgram=new Program(gl,{vertex,fragment,transparent:true,depthWrite:false,uniforms:{
    uColor:{value:currentColor},uTime:{value:0},uPulse:{value:0}
  }});
  const sphereGeometry=icosahedronGeometry(gl,Geometry,1.03);
  const sphere=new Mesh(gl,{geometry:sphereGeometry,program:sphereProgram});
  sphere.setParent(reactor);

  const lineVertex=`
    attribute vec3 position;
    uniform mat4 modelViewMatrix;
    uniform mat4 projectionMatrix;
    void main(){gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}
  `;
  const lineFragment=`
    precision mediump float;
    uniform vec3 uColor;
    uniform float uAlpha;
    void main(){gl_FragColor=vec4(uColor,uAlpha);}
  `;
  const ringGeometry=circleGeometry(gl,Geometry,compact?64:96);
  const ringPrograms=[.46,.3,.2].map(alpha=>new Program(gl,{
    vertex:lineVertex,fragment:lineFragment,transparent:true,depthWrite:false,cullFace:null,
    uniforms:{uColor:{value:new Float32Array(colors.transactions)},uAlpha:{value:alpha}}
  }));
  const rings=ringPrograms.map((program,index)=>{
    const ring=new Mesh(gl,{geometry:ringGeometry,program,mode:gl.LINE_LOOP,frustumCulled:false});
    ring.rotation.x=[1.08,.34,.72][index];
    ring.rotation.y=[.18,1.12,-.74][index];
    ring.rotation.z=[.08,.62,-.42][index];
    ring.setParent(reactor);
    return ring;
  });
  rings[2].visible=!compact;

  function applyColour(key) {
    targetColor=(colors[key]||colors.transactions).slice();
    focusRotation=rotations[key]||rotations.transactions;
  }
  function resize(isCompact=compact) {
    compact=isCompact;
    const rect=container.getBoundingClientRect();
    if (!rect.width||!rect.height) return;
    renderer.dpr=compact?1:Math.min(window.devicePixelRatio||1,1.25);
    renderer.setSize(Math.round(rect.width),Math.round(rect.height));
    camera.perspective({aspect:rect.width/rect.height});
    rings[2].visible=!compact;
  }
  function renderFrame(time) {
    if (!running||destroyed) return;
    frameId=requestAnimationFrame(renderFrame);
    if (time-previousFrame<33) return;
    previousFrame=time;
    currentColor.forEach((value,index)=>currentColor[index]=value+(targetColor[index]-value)*.075);
    ringPrograms.forEach((program,index)=>{
      const colour=program.uniforms.uColor.value;
      colour.forEach((value,channel)=>colour[channel]=value+(targetColor[channel]-value)*(.055+index*.01));
      program.uniforms.uAlpha.value=(compact?[.42,.25,0][index]:[.48,.31,.2][index])+pulseEnergy*.12;
    });
    reactor.rotation.x+=(focusRotation[0]+pointerRotation[0]-reactor.rotation.x)*.06;
    reactor.rotation.y+=(focusRotation[1]+pointerRotation[1]-reactor.rotation.y)*.06;
    reactor.rotation.z+=compact?.0012:.0021;
    rings[0].rotation.z+=.0032;rings[1].rotation.z-=.0024;rings[2].rotation.z+=.0017;
    pulseEnergy*=.9;
    const scale=1+pulseEnergy*.055*pulseScale;
    reactor.scale.set(scale,scale,scale);
    sphereProgram.uniforms.uTime.value=time*.001;
    sphereProgram.uniforms.uPulse.value=pulseEnergy;
    renderer.render({scene,camera});
  }
  function setRunning(next) {
    running=Boolean(next)&&!destroyed;
    if (running&&!frameId) frameId=requestAnimationFrame(renderFrame);
    if (!running&&frameId) {cancelAnimationFrame(frameId);frameId=null;}
  }
  function setFocus(key) {focusKey=key;applyColour(key);}
  function clearFocus(){focusKey=null;applyColour("transactions");}
  function setPointer(x,y){pointerRotation=[y*.08,x*.1];}
  function pulse(key){
    pulseEnergy=1;pulseScale=key==="transactions"?-1:.45;applyColour(key);
    if (pulseTimer) clearTimeout(pulseTimer);
    pulseTimer=setTimeout(()=>applyColour(focusKey||"transactions"),520);
  }
  function destroy(loseContext=false) {
    if (destroyed) return;
    destroyed=true;setRunning(false);
    if (pulseTimer) clearTimeout(pulseTimer);
    try{sphereGeometry.remove();ringGeometry.remove();sphereProgram.remove();ringPrograms.forEach(program=>program.remove());}catch(_){}
    if (loseContext) {try{gl.getExtension("WEBGL_lose_context")?.loseContext();}catch(_){}}
  }
  resize(compact);
  return {setRunning,setFocus,clearFocus,setPointer,pulse,resize,destroy};
}

export default function({ parentElement, data }) {
  const format = value => new Intl.NumberFormat("en-IE").format(Number(value || 0));
  const values = {
    customers:data.customers,accounts:data.accounts,transactions:data.transactions,
    merchants:data.merchants,settlements:data.settlements,flags:data.flags
  };
  Object.entries(values).forEach(([key,value]) => {
    parentElement.querySelectorAll(`[data-value="${key}"]`).forEach(el => el.textContent = format(value));
  });
  const source = parentElement.querySelector('[data-value="source"]');
  const windowLabel = parentElement.querySelector('[data-value="window"]');
  const proof = parentElement.querySelector('[data-proof="transactions"]');
  const merchantlessProof = parentElement.querySelector('[data-proof="merchantless"]');
  if (source) source.textContent = data.source;
  if (windowLabel) windowLabel.textContent = data.window;
  if (proof) proof.textContent = `${format(data.transactions)} transactions`;
  if (merchantlessProof) merchantlessProof.textContent = `${format(data.merchantless)} optional links`;

  const detail = {
    customers:["Customers","A customer can own more than one account.",`${format(data.customers)} customer records`],
    accounts:["Accounts","Every transaction originates from one account. One account can originate many transactions.",`${format(data.accounts)} account records`],
    transactions:["Transactions","Purchases, refunds and transfers connect account activity to merchant, settlement and review records.",`${format(data.transactions)} payment records`],
    merchants:["Merchants",`Merchant links are optional. ${format(data.merchantless)} transactions have no merchant because transfers do not require one.`,`${format(data.merchants)} merchant records`],
    settlements:["Settlements","A transaction can have at most one linked settlement record.",`${format(data.settlements)} settlement records`],
    flags:["Fraud flags","A transaction can have at most one linked review flag.",`${format(data.flags)} review records`]
  };
  const nodes = [...parentElement.querySelectorAll("[data-node]")];
  const routes = [...parentElement.querySelectorAll(".route[data-from]")];
  const ledger = [...parentElement.querySelectorAll(".relation-ledger [data-rel]")];
  const title = parentElement.querySelector("#relationship-title");
  const copy = parentElement.querySelector("#relationship-copy");
  const count = parentElement.querySelector("#relationship-count");
  const stage = parentElement.querySelector("#payment-rail");
  const svg = parentElement.querySelector(".route-map");
  const token = parentElement.querySelector(".payment-token");
  const observatory = parentElement.querySelector(".observatory");
  const replayButton = parentElement.querySelector("#replay-trace");
  const replayLabel = replayButton?.querySelector("span");
  const traceStatus = parentElement.querySelector("#trace-status");
  const traceTimeline = parentElement.querySelector("#trace-timeline");
  const traceProgress = parentElement.querySelector("#trace-progress");
  const tracePhases = [...parentElement.querySelectorAll("[data-trace-phase]")];
  const reactorCanvas = parentElement.querySelector("#transaction-reactor");
  const reactorContainer = parentElement.querySelector(".reactor-visual");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(pointer: fine)");
  const saveData = Boolean(navigator.connection?.saveData);
  let pinned = null;
  let componentActive = true;
  let reactor = null;
  let reactorLoading = false;
  let staticOnly = false;
  let contextLosses = 0;

  const setReactorState = state => {
    if (observatory) observatory.dataset.reactor = state;
  };
  const wantsReactor = () => Boolean(
    componentActive && reactorCanvas && reactorContainer && stage &&
    stage.clientWidth >= 680 && !reduced.matches && !saveData && !staticOnly
  );
  async function ensureReactor() {
    if (!wantsReactor()) {
      if (reactor) {reactor.destroy(false);reactor=null;}
      setReactorState("fallback");
      return;
    }
    const compact=stage.clientWidth<960;
    if (reactor) {
      reactor.resize(compact);
      reactor.setRunning(visible&&!document.hidden);
      return;
    }
    if (reactorLoading) return;
    reactorLoading=true;setReactorState("loading");
    try {
      const ogl=await loadOGL();
      if (!wantsReactor()) return;
      reactor=createPaymentReactor(reactorCanvas,reactorContainer,ogl,compact);
      setReactorState("ready");
      reactor.setRunning(visible&&!document.hidden);
    } catch (_) {
      staticOnly=true;setReactorState("fallback");
    } finally {
      reactorLoading=false;
    }
  }
  const onContextLost = event => {
    event.preventDefault();contextLosses+=1;
    reactor?.destroy(false);reactor=null;
    if (contextLosses>=2) staticOnly=true;
    setReactorState("fallback");
  };
  const onContextRestored = () => {
    if (contextLosses>=2||!componentActive) return;
    staticOnly=false;ensureReactor();
  };
  reactorCanvas?.addEventListener("webglcontextlost",onContextLost);
  reactorCanvas?.addEventListener("webglcontextrestored",onContextRestored);

  const relationKeys = element => (
    element.dataset.rel || `${element.dataset.from},${element.dataset.to}`
  ).split(",");
  const connected = (key,nodeKey) => nodeKey === key || routes.some(route =>
    (route.dataset.from === key && route.dataset.to === nodeKey) ||
    (route.dataset.to === key && route.dataset.from === nodeKey)
  );
  function activate(key) {
    reactor?.setFocus(key);
    nodes.forEach(node => {
      node.classList.toggle("is-active",node.dataset.node === key);
      node.classList.toggle("is-muted",!connected(key,node.dataset.node));
      node.setAttribute("aria-pressed",String(pinned === node.dataset.node));
    });
    routes.forEach(route => {
      const active = route.dataset.from === key || route.dataset.to === key;
      route.classList.toggle("is-active",active);
      route.classList.toggle("is-muted",!active);
    });
    ledger.forEach(item => {
      const active = relationKeys(item).includes(key);
      item.classList.toggle("is-active",active);
      item.classList.toggle("is-muted",!active);
    });
    if (title) title.textContent = detail[key][0];
    if (copy) copy.textContent = detail[key][1];
    if (count) count.textContent = detail[key][2];
  }
  function clear() {
    reactor?.clearFocus();
    nodes.forEach(node => {
      node.classList.remove("is-active","is-muted");
      node.setAttribute("aria-pressed","false");
    });
    routes.forEach(route => route.classList.remove("is-active","is-muted"));
    ledger.forEach(item => item.classList.remove("is-active","is-muted"));
    if (title) title.textContent = "Select any stage to see how its records connect";
    if (copy) copy.textContent = "Trace lifecycle direction here; open Data Model for keys and cardinality.";
    if (count) count.textContent = "6 connected entities";
  }
  function togglePin(node) {
    pinned = pinned === node.dataset.node ? null : node.dataset.node;
    if (pinned) activate(pinned); else clear();
  }
  nodes.forEach(node => {
    node.onpointerenter = () => { stopTraceForInteraction(); if (!pinned) activate(node.dataset.node); };
    node.onpointerleave = () => { if (!pinned) clear(); };
    node.onfocus = () => { stopTraceForInteraction(); if (!pinned) activate(node.dataset.node); };
    node.onblur = () => { if (!pinned) clear(); };
    node.onclick = () => { stopTraceForInteraction(); togglePin(node); };
    node.onkeydown = event => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();stopTraceForInteraction();
      togglePin(node);
    };
  });
  const onKeyDown = event => {
    if (event.key !== "Escape") return;
    stopTraceForInteraction();
    pinned = null;
    clear();
    stage?.focus({preventScroll:true});
  };
  stage?.addEventListener("keydown",onKeyDown);

  const routeDefinitions = [
    ["route-customers-accounts","customers","accounts"],
    ["route-accounts-transactions","accounts","transactions"],
    ["route-transactions-merchants","transactions","merchants"],
    ["route-transactions-settlements","transactions","settlements"],
    ["route-transactions-flags","transactions","flags"]
  ];
  const routePaths = new Map();
  const clamp = (value,minimum,maximum) => Math.min(maximum,Math.max(minimum,value));
  function anchor(rect,target,stageRect) {
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const targetX = target.left + target.width / 2;
    const targetY = target.top + target.height / 2;
    const dx = targetX - centerX;
    const dy = targetY - centerY;
    if (Math.abs(dx) >= Math.abs(dy) * .78) {
      return {x:(dx >= 0 ? rect.right : rect.left) - stageRect.left,y:centerY - stageRect.top};
    }
    return {x:centerX - stageRect.left,y:(dy >= 0 ? rect.bottom : rect.top) - stageRect.top};
  }
  function curve(start,end) {
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    if (Math.abs(dx) >= Math.abs(dy) * .78) {
      const bend = clamp(Math.abs(dx) * .46,34,180) * Math.sign(dx || 1);
      return `M ${start.x.toFixed(1)} ${start.y.toFixed(1)} C ${(start.x + bend).toFixed(1)} ${start.y.toFixed(1)}, ${(end.x - bend).toFixed(1)} ${end.y.toFixed(1)}, ${end.x.toFixed(1)} ${end.y.toFixed(1)}`;
    }
    const bend = clamp(Math.abs(dy) * .46,30,140) * Math.sign(dy || 1);
    return `M ${start.x.toFixed(1)} ${start.y.toFixed(1)} C ${start.x.toFixed(1)} ${(start.y + bend).toFixed(1)}, ${end.x.toFixed(1)} ${(end.y - bend).toFixed(1)}, ${end.x.toFixed(1)} ${end.y.toFixed(1)}`;
  }
  function layoutRoutes() {
    if (!stage || !svg) return;
    const stageRect = stage.getBoundingClientRect();
    if (!stageRect.width || !stageRect.height) return;
    svg.setAttribute("viewBox",`0 0 ${stageRect.width} ${stageRect.height}`);
    svg.setAttribute("width",stageRect.width);
    svg.setAttribute("height",stageRect.height);
    routeDefinitions.forEach(([id,fromKey,toKey]) => {
      const path = parentElement.querySelector(`#${id}`);
      const from = parentElement.querySelector(`[data-node="${fromKey}"]`);
      const to = parentElement.querySelector(`[data-node="${toKey}"]`);
      if (!path || !from || !to) return;
      const fromRect = from.getBoundingClientRect();
      const toRect = to.getBoundingClientRect();
      const d = curve(anchor(fromRect,toRect,stageRect),anchor(toRect,fromRect,stageRect));
      path.setAttribute("d",d);
      routePaths.set(id,d);
    });
  }

  let visible = true;
  let timer = null;
  let timerResolve = null;
  let animation = null;
  let activeRouteId = null;
  let sequenceGeneration = 0;
  let sequenceState = "idle";
  let autoplayTimer = null;
  let traceSeen = false;
  try { traceSeen = sessionStorage.getItem("payment-observatory-trace-seen-v1") === "1"; } catch (_) {}
  let autoplayPending = !traceSeen;

  const phaseOrder = ["inbound","core","outcomes"];
  const statusCopy = {
    idle:"System trace ready",
    playing:"Tracing payment lifecycle",
    paused:"Trace paused",
    complete:"System trace complete"
  };
  function setSequenceState(next) {
    sequenceState=next;
    if (observatory) observatory.dataset.sequence=next;
    if (traceStatus) traceStatus.textContent=statusCopy[next]||statusCopy.idle;
    if (replayLabel) replayLabel.textContent=next==="playing"?"Restart system trace":"Replay system trace";
  }
  function setPhase(phase,progress=0) {
    if (observatory) observatory.dataset.phase=phase;
    const activeIndex=phaseOrder.indexOf(phase);
    tracePhases.forEach((item,index)=>{
      item.classList.toggle("is-active",index===activeIndex);
      item.classList.toggle("is-complete",phase==="complete"||index<activeIndex);
    });
    if (traceProgress) traceProgress.style.transform=`scaleX(${clamp(progress,0,1)})`;
    traceTimeline?.setAttribute("aria-valuenow",String(Math.round(clamp(progress,0,1)*100)));
  }
  function wait(milliseconds,generation) {
    return new Promise(resolve => {
      if (generation!==sequenceGeneration) return resolve();
      timerResolve=resolve;
      timer=window.setTimeout(()=>{
        timer=null;timerResolve=null;resolve();
      },milliseconds);
    });
  }
  function clearPendingMotion() {
    sequenceGeneration+=1;
    if (timer) window.clearTimeout(timer);
    timer=null;
    if (timerResolve) timerResolve();
    timerResolve=null;
    if (animation) animation.cancel();
    animation=null;
    activeRouteId=null;
    if (token) token.style.opacity="0";
  }
  function stopTraceForInteraction() {
    if (sequenceState!=="playing") return;
    clearPendingMotion();
    setSequenceState("paused");
  }
  function canTravel(generation) {
    return Boolean(
      generation===sequenceGeneration && sequenceState==="playing" && token && stage &&
      visible && !document.hidden && !reduced.matches && !saveData && stage.clientWidth>=680
    );
  }
  function animateRoute(id,duration,generation) {
    if (!canTravel(generation)) return wait(duration,generation);
    return new Promise(resolve => {
      const d=routePaths.get(id);
      if (!d) return resolve();
      activeRouteId=id;
      token.style.offsetPath=`path("${d}")`;
      animation=token.animate(
        [
          {offsetDistance:"0%",opacity:0,transform:"scale(.66)"},
          {offsetDistance:"8%",opacity:1,transform:"scale(1)"},
          {offsetDistance:"88%",opacity:1,transform:"scale(1)"},
          {offsetDistance:"100%",opacity:0,transform:"scale(.68)"}
        ],
        {duration,easing:"cubic-bezier(.44,.02,.22,1)",fill:"forwards"}
      );
      animation.onfinish=()=>{animation=null;activeRouteId=null;resolve();};
      animation.oncancel=()=>{animation=null;activeRouteId=null;resolve();};
    });
  }
  function focusRoute(routeId,key) {
    activate(key);
    const selected=routes.find(route=>route.id===routeId);
    routes.forEach(route=>{
      const active=route.id===routeId;
      route.classList.toggle("is-active",active);
      route.classList.toggle("is-muted",!active);
    });
    if (!selected) return;
    ledger.forEach(item=>{
      const keys=relationKeys(item);
      const active=keys.includes(selected.dataset.from)&&keys.includes(selected.dataset.to);
      item.classList.toggle("is-active",active);
      item.classList.toggle("is-muted",!active);
    });
  }
  async function traceStep({route,key,phase,progress,duration},generation,pace) {
    if (generation!==sequenceGeneration) return;
    setPhase(phase,progress);
    focusRoute(route,key);
    reactor?.pulse(key);
    await animateRoute(route,Math.round(duration*pace),generation);
  }
  async function runSystemTrace(generation) {
    const pace=(reduced.matches||saveData) ? .24 : (stage&&stage.clientWidth<680 ? .48 : 1);
    setPhase("inbound",.04);
    await wait(Math.round(700*pace),generation);
    await traceStep({route:"route-customers-accounts",key:"customers",phase:"inbound",progress:.16,duration:850},generation,pace);
    await traceStep({route:"route-accounts-transactions",key:"accounts",phase:"inbound",progress:.31,duration:950},generation,pace);
    if (generation!==sequenceGeneration) return;
    setPhase("core",.42);activate("transactions");reactor?.pulse("transactions");
    await wait(Math.round(700*pace),generation);
    await traceStep({route:"route-transactions-merchants",key:"merchants",phase:"outcomes",progress:.58,duration:950},generation,pace);
    await wait(Math.round(300*pace),generation);
    await traceStep({route:"route-transactions-settlements",key:"settlements",phase:"outcomes",progress:.76,duration:950},generation,pace);
    await wait(Math.round(300*pace),generation);
    await traceStep({route:"route-transactions-flags",key:"flags",phase:"outcomes",progress:.92,duration:950},generation,pace);
    await wait(Math.round(900*pace),generation);
    if (generation!==sequenceGeneration) return;
    clear();setPhase("complete",1);setSequenceState("complete");
  }
  function startSystemTrace() {
    if (!stage||!visible||document.hidden) return;
    autoplayPending=false;
    if (autoplayTimer) window.clearTimeout(autoplayTimer);
    autoplayTimer=null;
    clearPendingMotion();
    pinned=null;clear();layoutRoutes();
    stage.classList.toggle("motion-paused",reduced.matches||saveData);
    setSequenceState("playing");setPhase("inbound",0);
    reactor?.setRunning(!reduced.matches&&!saveData);
    try { sessionStorage.setItem("payment-observatory-trace-seen-v1","1"); } catch (_) {}
    const generation=sequenceGeneration;
    runSystemTrace(generation);
  }
  function pauseForVisibility() {
    if (sequenceState==="playing") {
      clearPendingMotion();setSequenceState("paused");
    }
    reactor?.setRunning(false);
    stage?.classList.add("motion-paused");
  }
  function restoreVisibleState() {
    stage?.classList.toggle("motion-paused",reduced.matches||saveData);
    ensureReactor();
    reactor?.setRunning(!reduced.matches&&!saveData);
    scheduleAutoplay();
  }
  function scheduleAutoplay() {
    if (!autoplayPending||autoplayTimer||!visible||document.hidden) return;
    autoplayTimer=window.setTimeout(()=>{
      autoplayTimer=null;
      if (autoplayPending&&visible&&!document.hidden) startSystemTrace();
    },520);
  }
  replayButton?.addEventListener("click",startSystemTrace);

  const observer = new IntersectionObserver(entries => {
    visible=Boolean(entries[0]?.isIntersecting);
    if (visible) restoreVisibleState(); else pauseForVisibility();
  },{threshold:.08});
  if (stage) observer.observe(stage);
  const visibility=()=>document.hidden?pauseForVisibility():restoreVisibleState();
  document.addEventListener("visibilitychange",visibility);
  const onMotionPreference=()=>{
    ensureReactor();
    stage?.classList.toggle("motion-paused",reduced.matches||saveData||!visible||document.hidden);
    if (sequenceState==="playing") startSystemTrace();
  };
  reduced.addEventListener?.("change",onMotionPreference);

  let resizeFrame=null;
  const scheduleLayout=()=>{
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    resizeFrame=requestAnimationFrame(()=>{
      layoutRoutes();
      if (activeRouteId&&token&&routePaths.has(activeRouteId)) token.style.offsetPath=`path("${routePaths.get(activeRouteId)}")`;
      ensureReactor();
    });
  };
  const resizeObserver=new ResizeObserver(scheduleLayout);
  if (stage) resizeObserver.observe(stage);
  window.addEventListener("resize",scheduleLayout);

  const resetTilt = () => {
    stage?.style.setProperty("--tilt-x","0deg");
    stage?.style.setProperty("--tilt-y","0deg");
    reactor?.setPointer(0,0);
  };
  const tilt = event => {
    if (!stage || reduced.matches || !finePointer.matches || stage.clientWidth < 960) return resetTilt();
    const rect = stage.getBoundingClientRect();
    const x = clamp((event.clientX - rect.left) / rect.width,0,1);
    const y = clamp((event.clientY - rect.top) / rect.height,0,1);
    stage.style.setProperty("--tilt-x",`${((.5 - y) * 4).toFixed(2)}deg`);
    stage.style.setProperty("--tilt-y",`${((x - .5) * 4).toFixed(2)}deg`);
    reactor?.setPointer((x-.5)*2,(.5-y)*2);
  };
  stage?.addEventListener("pointermove",tilt);
  stage?.addEventListener("pointerleave",resetTilt);

  if (traceSeen) {setSequenceState("complete");setPhase("complete",1);}
  else {setSequenceState("idle");setPhase("idle",0);}
  requestAnimationFrame(()=>{
    layoutRoutes();
    requestAnimationFrame(()=>{
      ensureReactor();
      scheduleAutoplay();
    });
  });
  return () => {
    componentActive=false;
    clearPendingMotion();
    if (autoplayTimer) window.clearTimeout(autoplayTimer);
    observer.disconnect();
    resizeObserver.disconnect();
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    document.removeEventListener("visibilitychange",visibility);
    reduced.removeEventListener?.("change",onMotionPreference);
    window.removeEventListener("resize",scheduleLayout);
    stage?.removeEventListener("keydown",onKeyDown);
    stage?.removeEventListener("pointermove",tilt);
    stage?.removeEventListener("pointerleave",resetTilt);
    replayButton?.removeEventListener("click",startSystemTrace);
    reactorCanvas?.removeEventListener("webglcontextlost",onContextLost);
    reactorCanvas?.removeEventListener("webglcontextrestored",onContextRestored);
    reactor?.destroy(true);reactor=null;
  };
}
"""


NAV_HTML = """
<nav class="view-rail" aria-label="Dashboard views">
  <div class="rail-label"><small>Operational views</small><strong>Select analysis</strong></div>
  <div class="rail-tabs">
    <button type="button" data-view="overview"><i>01</i><span>Overview</span></button>
    <button type="button" data-view="merchant"><i>02</i><span>Merchant flow</span></button>
    <button type="button" data-view="risk"><i>03</i><span>Risk monitor</span></button>
    <button type="button" data-view="retention"><i>04</i><span>Retention</span></button>
    <button type="button" data-view="model"><i>05</i><span>Data model</span></button>
  </div>
  <span class="rail-state"><i></i> System ready</span>
</nav>
"""


NAV_CSS = """
:host{color:#f1f3ef;font-family:"Source Sans","Segoe UI",sans-serif}
*{box-sizing:border-box}
.view-rail{
  display:grid;
  grid-template-columns:auto 1fr auto;
  align-items:center;
  gap:22px;
  padding:6px;
  border:1px solid rgba(203,219,233,.11);
  border-radius:14px;
  background:rgba(10,12,15,.94);
}
.rail-label{padding:0 10px}
.rail-label small,.rail-label strong{display:block}
.rail-label small{color:#7c8993;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.09em;text-transform:uppercase}
.rail-label strong{margin-top:4px;font-size:13px;font-weight:580}
.rail-tabs{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}
button{
  position:relative;
  display:flex;
  align-items:center;
  gap:9px;
  min-height:44px;
  padding:7px 11px;
  border:1px solid transparent;
  border-radius:9px;
  background:transparent;
  color:#7e8a94;
  text-align:left;
  cursor:pointer;
  transition:background 190ms ease,color 190ms ease,border-color 190ms ease,transform 120ms ease;
}
button:hover,button:focus-visible{color:#dfe5e5;background:rgba(255,255,255,.025);outline:none}
button:active{transform:scale(.985)}
button.active{color:#f1f3ef;border-color:rgba(104,220,255,.22);background:linear-gradient(135deg,rgba(78,114,255,.13),rgba(104,220,255,.045))}
button.active::after{content:"";position:absolute;left:12px;right:12px;bottom:-1px;height:2px;background:linear-gradient(90deg,#4e72ff,#68dcff);box-shadow:0 0 9px rgba(104,220,255,.55)}
button i{color:#6e7a84;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;font-style:normal}
button.active i{color:#8ca6ff}
button span{font-size:13px;font-weight:570;white-space:nowrap}
.rail-state{display:flex;align-items:center;padding:0 10px;color:#7b8791;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;white-space:nowrap;text-transform:uppercase}
.rail-state i{width:5px;height:5px;margin-right:7px;border-radius:50%;background:#8af6c7;box-shadow:0 0 9px rgba(138,246,199,.65)}
@media(max-width:1120px){.view-rail{grid-template-columns:1fr}.rail-label,.rail-state{display:none}.rail-tabs{overflow-x:auto;scrollbar-width:thin;scrollbar-color:rgba(104,220,255,.2) transparent}.rail-tabs button{min-width:122px}}
@media(max-width:560px){.view-rail{padding:7px}.rail-tabs{display:flex}.rail-tabs button{flex:0 0 auto;min-width:116px}}
@media(prefers-reduced-motion:reduce){*{transition-duration:.01ms!important}}
"""


NAV_JS = """
export default function({ parentElement, data, setStateValue }) {
  const current = data.view || "overview";
  const buttons = [...parentElement.querySelectorAll("[data-view]")];
  buttons.forEach(button => {
    const active = button.dataset.view === current;
    button.classList.toggle("active", active);
    button.setAttribute("aria-current", active ? "page" : "false");
    button.onclick = () => {
      if (button.dataset.view !== current) setStateValue("view", button.dataset.view);
    };
  });
}
"""


FILTER_HTML = """
<form class="scope-composer" id="control-deck">
  <div class="scope-summary">
    <div class="scope-title">
      <small>Operational scope</small>
      <strong>Current analysis window</strong>
    </div>
    <div class="scope-pills" aria-label="Active dashboard filters" aria-live="polite">
      <span class="scope-pill scope-pill-date" id="summary-dates"></span>
      <span class="scope-pill" id="summary-currencies"></span>
      <span class="scope-pill" id="summary-categories"></span>
      <span class="scope-pill scope-pill-compare" id="summary-comparison" hidden>Previous period</span>
    </div>
    <div class="scope-commands">
      <button class="scope-reset" type="button" id="quick-reset" hidden>Reset</button>
      <button class="scope-toggle" type="button" id="scope-toggle" aria-expanded="false" aria-controls="scope-editor">
        <span>Adjust scope</span>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>
      </button>
    </div>
  </div>
  <section class="scope-editor" id="scope-editor" aria-labelledby="scope-editor-title" hidden>
    <div class="scope-editor-head">
      <div>
        <small>Scope composer</small>
        <strong id="scope-editor-title">Choose the records to analyse</strong>
      </div>
      <p>Shared by Overview, Merchant flow and Risk monitor. Retention keeps its own cohort window.</p>
    </div>
    <div class="deck-grid">
      <fieldset class="date-field">
        <legend>Date range</legend>
        <label><span>From</span><input id="date-start" type="date"></label>
        <label><span>To</span><input id="date-end" type="date"></label>
      </fieldset>
      <fieldset>
        <legend>Currencies</legend>
        <div class="chip-group" id="currency-options"></div>
      </fieldset>
      <fieldset class="category-field">
        <legend>Merchant categories</legend>
        <div class="chip-group" id="category-options"></div>
        <p>All categories retain transfers. A category subset excludes records without a merchant.</p>
      </fieldset>
      <fieldset class="compare-field">
        <legend>Comparison</legend>
        <label class="switch-row">
          <input id="compare-previous" type="checkbox">
          <span class="switch"><i></i></span>
          <b>Previous period</b>
        </label>
        <p>Uses the immediately preceding range of equal length.</p>
      </fieldset>
    </div>
    <div class="deck-actions">
      <button class="reset" type="button" id="reset-filters">Reset scope</button>
      <button class="apply" type="submit">Apply scope <span aria-hidden="true">&#8599;</span></button>
    </div>
  </section>
</form>
"""


FILTER_CSS = """
:host{
  --canvas:#0a0c0f;--surface:#0d1116;--raised:#11161c;--line:rgba(203,219,233,.11);
  --ink:#f1f3ef;--muted:#84919b;--cyan:#68dcff;--blue:#4e72ff;--teal:#8af6c7;
  color:var(--ink);font-family:"Source Sans","Segoe UI",sans-serif;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
.scope-composer{overflow:hidden;border:1px solid var(--line);border-radius:16px;background:linear-gradient(130deg,rgba(78,114,255,.038),transparent 42%),var(--canvas);box-shadow:0 18px 42px rgba(0,0,0,.18),inset 0 1px rgba(255,255,255,.02)}
.scope-summary{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:16px;min-height:64px;padding:9px 12px 9px 15px}
.scope-title small,.scope-title strong,.scope-editor-head small,.scope-editor-head strong{display:block}
.scope-title small,.scope-editor-head small{color:#8ca6ff;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;letter-spacing:.12em;text-transform:uppercase}
.scope-title strong{margin-top:4px;font-size:14px;font-weight:590;white-space:nowrap}
.scope-pills{display:flex;min-width:0;align-items:center;flex-wrap:wrap;gap:6px}
.scope-pill{display:inline-flex;align-items:center;min-height:30px;padding:6px 9px;border:1px solid rgba(203,219,233,.095);border-radius:7px;background:rgba(255,255,255,.016);color:#99a5ae;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;letter-spacing:.025em;white-space:nowrap}
.scope-pill::before{content:"";width:4px;height:4px;margin-right:7px;border-radius:50%;background:#65727d}
.scope-pill-date::before{background:var(--cyan);box-shadow:0 0 7px rgba(104,220,255,.45)}
.scope-pill-compare{color:#d5e5de;border-color:rgba(138,246,199,.16)}
.scope-pill-compare::before{background:var(--teal)}
.scope-commands{display:flex;align-items:center;gap:6px}
button{min-height:38px;padding:8px 12px;border-radius:8px;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;letter-spacing:.045em;cursor:pointer;transition:transform 120ms ease,background 190ms ease,border-color 190ms ease,color 190ms ease}
button:active{transform:scale(.98)}
button:focus-visible,input:focus-visible{border-color:rgba(104,220,255,.58)!important;outline:2px solid rgba(78,114,255,.22);outline-offset:2px}
.scope-toggle{display:flex;align-items:center;gap:9px;border:1px solid rgba(104,220,255,.2);background:linear-gradient(135deg,rgba(78,114,255,.16),rgba(104,220,255,.04));color:#dce8ea}
.scope-toggle:hover{border-color:rgba(104,220,255,.34);background:linear-gradient(135deg,rgba(78,114,255,.22),rgba(104,220,255,.07))}
.scope-toggle svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.5;transition:transform 190ms ease}
.scope-toggle[aria-expanded="true"] svg{transform:rotate(180deg)}
.scope-reset{border:1px solid transparent;background:transparent;color:#74818b}
.scope-reset:hover{color:#b8c2c6;background:rgba(255,255,255,.025)}
.scope-editor{padding:17px;border-top:1px solid rgba(203,219,233,.085);background:linear-gradient(180deg,rgba(255,255,255,.012),transparent 52%);animation:scope-enter 190ms ease-out both}
.scope-editor-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:15px}
.scope-editor-head strong{margin-top:5px;font-size:15px;font-weight:590}
.scope-editor-head p{max-width:530px;margin:0;color:#78858f;font-size:10px;line-height:1.55;text-align:right}
.deck-grid{display:grid;grid-template-columns:1.05fr .72fr 1.65fr .75fr;gap:10px}
fieldset{min-width:0;margin:0;padding:14px;border:1px solid rgba(203,219,233,.09);border-radius:11px;background:rgba(255,255,255,.012)}
legend{padding:0 6px;color:#8a97a1;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;letter-spacing:.07em;text-transform:uppercase}
.date-field{display:grid;grid-template-columns:1fr 1fr;gap:8px}
label>span{display:block;margin-bottom:6px;color:#7d8993;font-size:9px;letter-spacing:.04em;text-transform:uppercase}
input[type=date]{width:100%;min-height:42px;padding:9px 10px;border:1px solid rgba(203,219,233,.13);border-radius:8px;background:var(--surface);color:#dfe5e5;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;color-scheme:dark}
.chip-group{display:flex;flex-wrap:wrap;gap:5px}
.chip{position:relative}
.chip input{position:absolute;opacity:0;pointer-events:none}
.chip span{display:block;margin:0;padding:8px 10px;border:1px solid rgba(203,219,233,.105);border-radius:7px;background:var(--surface);color:#8a97a1;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;cursor:pointer;transition:background 190ms ease,border-color 190ms ease,color 190ms ease,transform 120ms ease}
.chip input:checked+span{border-color:rgba(104,220,255,.29);background:linear-gradient(135deg,rgba(78,114,255,.16),rgba(104,220,255,.05));color:#d8e7eb}
.chip input:focus-visible+span{outline:2px solid rgba(78,114,255,.28);outline-offset:2px}
.chip span:active{transform:scale(.97)}
fieldset p{margin:9px 0 0;color:#75828c;font-size:9px;line-height:1.5}
.switch-row{display:flex;align-items:center;gap:10px;min-height:42px;cursor:pointer}
.switch-row>input{position:absolute;opacity:0}
.switch{position:relative;display:block;width:34px;height:19px;margin:0;border:1px solid rgba(203,219,233,.17);border-radius:999px;background:var(--raised)}
.switch i{position:absolute;width:13px;height:13px;left:2px;top:2px;border-radius:50%;background:#6c7882;transition:transform 190ms ease,background 190ms ease}
.switch-row input:checked+.switch{border-color:rgba(104,220,255,.35);background:rgba(78,114,255,.2)}
.switch-row input:checked+.switch i{transform:translateX(15px);background:var(--cyan);box-shadow:0 0 9px rgba(104,220,255,.55)}
.switch-row input:focus-visible+.switch{outline:2px solid rgba(78,114,255,.28);outline-offset:2px}
.switch-row b{font-size:10px;font-weight:580;color:#c3cbcd}
.deck-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:13px}
.reset{border:1px solid rgba(203,219,233,.11);background:transparent;color:#7c8993}
.apply{border:1px solid rgba(104,220,255,.28);background:linear-gradient(135deg,#435eda,#397f9d);color:#fff}
.apply span{margin-left:12px}
@keyframes scope-enter{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
@media(max-width:1050px){.scope-summary{grid-template-columns:auto 1fr}.scope-commands{grid-column:2;grid-row:1;justify-self:end}.scope-pills{grid-column:1/-1}.deck-grid{grid-template-columns:1fr 1fr}.category-field{grid-column:1/-1}}
@media(max-width:680px){.scope-summary{grid-template-columns:1fr auto;gap:10px;padding:13px}.scope-title strong{white-space:normal}.scope-pills{grid-column:1/-1;flex-wrap:nowrap;overflow-x:auto;padding-bottom:2px;scrollbar-width:thin;scrollbar-color:rgba(104,220,255,.2) transparent;overscroll-behavior-inline:contain}.scope-pill{flex:0 0 auto;white-space:nowrap}.scope-reset{display:none}.scope-editor{padding:13px}.scope-editor-head{align-items:flex-start;flex-direction:column;gap:6px}.scope-editor-head p{text-align:left}.deck-grid{grid-template-columns:1fr}.category-field{grid-column:auto}.date-field{grid-template-columns:1fr 1fr}.deck-actions button{flex:1}}
@media(max-width:430px){.date-field{grid-template-columns:1fr}.scope-toggle{padding-inline:10px}.scope-toggle span{font-size:9px}.scope-title strong{font-size:13px}}
@media(prefers-reduced-motion:reduce){*{animation-duration:.01ms!important;transition-duration:.01ms!important}}
"""


FILTER_JS = """
export default function({ parentElement, data, setStateValue }) {
  const current = data.current || data.defaults;
  const defaults = data.defaults;
  const start = parentElement.querySelector("#date-start");
  const end = parentElement.querySelector("#date-end");
  const compare = parentElement.querySelector("#compare-previous");
  const editor = parentElement.querySelector("#scope-editor");
  const toggle = parentElement.querySelector("#scope-toggle");
  const quickReset = parentElement.querySelector("#quick-reset");
  [start,end].forEach(input => { input.min=data.minDate; input.max=data.maxDate; });

  function mountChips(containerId, options, selected, name) {
    const container = parentElement.querySelector(containerId);
    container.replaceChildren();
    options.forEach(option => {
      const label=document.createElement("label"); label.className="chip";
      const input=document.createElement("input"); input.type="checkbox"; input.name=name; input.value=option; input.checked=selected.includes(option);
      const span=document.createElement("span"); span.textContent=option;
      label.append(input,span); container.append(label);
    });
  }

  function writeControls(value) {
    start.value = value.startDate;
    end.value = value.endDate;
    compare.checked = Boolean(value.comparePrevious);
    mountChips("#currency-options",data.currencies,value.currencies,"currency");
    mountChips("#category-options",data.categories,value.categories,"category");
  }

  function shortDate(value) {
    const parsed = new Date(`${value}T00:00:00`);
    return new Intl.DateTimeFormat("en-IE",{month:"short",year:"numeric"}).format(parsed);
  }

  function sameList(left,right) {
    const sortedLeft=[...left].sort();
    const sortedRight=[...right].sort();
    return sortedLeft.length===sortedRight.length && sortedLeft.every((value,index)=>value===sortedRight[index]);
  }

  function isDefault(value) {
    return value.startDate===defaults.startDate && value.endDate===defaults.endDate &&
      sameList(value.currencies,defaults.currencies) && sameList(value.categories,defaults.categories) &&
      Boolean(value.comparePrevious)===Boolean(defaults.comparePrevious);
  }

  function renderSummary(value) {
    parentElement.querySelector("#summary-dates").textContent=`${shortDate(value.startDate)} to ${shortDate(value.endDate)}`;
    parentElement.querySelector("#summary-currencies").textContent=value.currencies.length===data.currencies.length
      ? `${data.currencies.length} currencies`
      : value.currencies.length===1 ? value.currencies[0] : `${value.currencies.length} currencies`;
    parentElement.querySelector("#summary-categories").textContent=value.categories.length===data.categories.length
      ? "All merchant categories"
      : value.categories.length===1 ? value.categories[0] : `${value.categories.length} categories`;
    parentElement.querySelector("#summary-comparison").hidden=!value.comparePrevious;
    quickReset.hidden=isDefault(value);
  }

  writeControls(current);
  renderSummary(current);

  function payload() {
    return {
      startDate:start.value,
      endDate:end.value,
      currencies:[...parentElement.querySelectorAll('input[name="currency"]:checked')].map(el=>el.value),
      categories:[...parentElement.querySelectorAll('input[name="category"]:checked')].map(el=>el.value),
      comparePrevious:compare.checked
    };
  }

  function closeEditor(restore) {
    if (restore) writeControls(current);
    editor.hidden=true;
    toggle.setAttribute("aria-expanded","false");
    toggle.querySelector("span").textContent="Adjust scope";
  }

  function openEditor() {
    editor.hidden=false;
    toggle.setAttribute("aria-expanded","true");
    toggle.querySelector("span").textContent="Close scope";
    requestAnimationFrame(()=>start.focus());
  }

  toggle.onclick=()=>editor.hidden?openEditor():closeEditor(true);
  parentElement.querySelector("#control-deck").onsubmit = event => {
    event.preventDefault();
    if (start.value>end.value) { end.setCustomValidity("End date must be on or after the start date."); end.reportValidity(); return; }
    end.setCustomValidity("");
    closeEditor(false);
    setStateValue("filters",payload());
  };
  const reset=()=>setStateValue("filters",defaults);
  parentElement.querySelector("#reset-filters").onclick=reset;
  quickReset.onclick=reset;
  const handleKeydown=event=>{
    if(event.key!=="Escape"||editor.hidden)return;
    event.preventDefault();closeEditor(true);toggle.focus();
  };
  parentElement.addEventListener("keydown",handleKeydown);
  return()=>parentElement.removeEventListener("keydown",handleKeydown);
}
"""


MEASURE_HTML = """
<div class="measure-control" role="group" aria-label="Trend measure">
  <span>Trend measure</span>
  <div class="measure-options" id="measure-options"></div>
</div>
"""


MEASURE_CSS = """
:host{color:#f1f3ef;font-family:"Source Sans","Segoe UI",sans-serif}
*{box-sizing:border-box}
.measure-control{display:inline-flex;align-items:center;gap:10px;margin:18px 0 2px;padding:5px 5px 5px 12px;border:1px solid rgba(203,219,233,.1);border-radius:10px;background:#0a0c0f;box-shadow:inset 0 1px rgba(255,255,255,.02)}
.measure-control>span{color:#7e8a94;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
.measure-options{display:flex;gap:3px}
button{min-height:34px;padding:7px 11px;border:1px solid transparent;border-radius:7px;background:transparent;color:#7f8b94;font-family:"Source Code Pro",Consolas,monospace;font-size:9px;cursor:pointer;transition:background 190ms ease,border-color 190ms ease,color 190ms ease,transform 120ms ease}
button:hover{color:#cfd7d9;background:rgba(255,255,255,.025)}
button:active{transform:scale(.98)}
button:focus-visible{outline:2px solid rgba(78,114,255,.3);outline-offset:1px}
button[aria-pressed="true"]{border-color:rgba(104,220,255,.24);background:linear-gradient(135deg,rgba(78,114,255,.17),rgba(104,220,255,.045));color:#eef5f4;box-shadow:inset 0 -1px rgba(104,220,255,.22)}
@media(max-width:480px){.measure-control{display:flex;align-items:flex-start;flex-direction:column;padding:9px}.measure-options{width:100%}.measure-options button{flex:1}}
@media(prefers-reduced-motion:reduce){*{transition-duration:.01ms!important}}
"""


MEASURE_JS = """
export default function({ parentElement, data, setStateValue }) {
  const current=data.current || data.options[0];
  const container=parentElement.querySelector("#measure-options");
  container.replaceChildren();
  data.options.forEach(option=>{
    const button=document.createElement("button");
    button.type="button";
    button.textContent=option;
    button.setAttribute("aria-pressed",option===current?"true":"false");
    button.onclick=()=>{if(option!==current)setStateValue("value",option)};
    container.append(button);
  });
}
"""


SCHEMA_HTML = """
<section class="schema" aria-labelledby="schema-title">
  <header>
    <div><small>Relational model / six entities</small><h3 id="schema-title">Inspect the payment data spine.</h3></div>
    <span><i></i> Select an entity to isolate its joins</span>
  </header>
  <div class="schema-map">
    <div class="entity-column source-column">
      <button type="button" data-entity="customers">
        <span class="entity-type">Identity / 01</span><strong>customers</strong><b data-count="customers"></b>
        <code>PK customer_id</code><code>join_date · segment · country</code>
      </button>
      <span class="join-label" data-rel="customers,accounts">1 customer : many accounts</span>
      <button type="button" data-entity="accounts">
        <span class="entity-type">Funding / 02</span><strong>accounts</strong><b data-count="accounts"></b>
        <code>PK account_id</code><code>FK customer_id · currency</code>
      </button>
    </div>
    <div class="spine-column">
      <span class="spine-caption">Event spine</span>
      <button type="button" class="event-entity" data-entity="transactions">
        <span class="entity-type">Payment event / 03</span><strong>transactions</strong><b data-count="transactions"></b>
        <code>PK transaction_id</code><code>FK account_id · merchant_id?</code><code>amount · currency · status</code>
      </button>
      <span class="spine-rule">Every analytical view begins here.</span>
    </div>
    <div class="entity-column outcome-column">
      <button type="button" data-entity="merchants">
        <span class="entity-type">Commercial / 04</span><strong>merchants</strong><b data-count="merchants"></b>
        <code>PK merchant_id</code><code>category · risk_tier</code>
      </button>
      <button type="button" data-entity="settlements">
        <span class="entity-type">Outcome / 05</span><strong>settlements</strong><b data-count="settlements"></b>
        <code>PK settlement_id</code><code>UNIQUE FK transaction_id</code>
      </button>
      <button type="button" data-entity="flags">
        <span class="entity-type">Review / 06</span><strong>fraud_flags</strong><b data-count="flags"></b>
        <code>PK flag_id</code><code>UNIQUE FK transaction_id</code>
      </button>
    </div>
    <svg viewBox="0 0 1000 540" preserveAspectRatio="none" aria-hidden="true">
      <path data-rel="customers,accounts" d="M170 160 C170 190 170 245 170 275"/>
      <path data-rel="accounts,transactions" d="M245 355 C330 355 350 280 425 280"/>
      <path data-rel="transactions,merchants" d="M575 250 C650 250 660 120 755 120"/>
      <path data-rel="transactions,settlements" d="M575 270 C660 270 670 275 755 275"/>
      <path data-rel="transactions,flags" d="M575 290 C650 290 660 430 755 430"/>
    </svg>
  </div>
  <div class="relation-ledger">
    <span data-rel="accounts,transactions"><b>accounts 1:M transactions</b> Every transaction starts from one account.</span>
    <span data-rel="transactions,merchants"><b>merchants 1:M transactions</b> Merchant is nullable for transfers.</span>
    <span data-rel="transactions,settlements"><b>transactions 0:1 settlements</b> A linked settlement is unique.</span>
    <span data-rel="transactions,flags"><b>transactions 0:1 fraud_flags</b> A linked review record is unique.</span>
  </div>
</section>
"""


SCHEMA_CSS = """
:host{color:#f1f3ef;font-family:"Source Sans","Segoe UI",sans-serif}
*{box-sizing:border-box}
.schema{padding:clamp(22px,3.5vw,38px);border:1px solid rgba(203,219,233,.11);border-radius:18px;background:radial-gradient(circle at 50% 35%,rgba(78,114,255,.09),transparent 34%),#090c0f}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:24px}
header small{color:#8ca6ff;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.11em;text-transform:uppercase}
h3{margin:9px 0 0;font-family:"space-grotesk","Source Sans",sans-serif;font-size:clamp(34px,4.5vw,58px);font-weight:520;letter-spacing:-.055em;line-height:.95}
header>span{color:#8a96a0;font-family:"Source Code Pro",Consolas,monospace;font-size:10px}
header i{display:inline-block;width:5px;height:5px;margin-right:7px;border-radius:50%;background:#68dcff;box-shadow:0 0 8px rgba(104,220,255,.65)}
.schema-map{position:relative;display:grid;grid-template-columns:1fr .95fr 1fr;gap:12%;min-height:540px;margin-top:30px;padding:16px;perspective:1100px;transform-style:preserve-3d}
.schema-map svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.schema-map path{fill:none;stroke:rgba(104,220,255,.24);stroke-width:1;vector-effect:non-scaling-stroke;transition:opacity 190ms ease,stroke 190ms ease,stroke-width 190ms ease}
.schema-map path.active{stroke:#68dcff;stroke-width:2;filter:drop-shadow(0 0 5px rgba(104,220,255,.55))}
.schema-map path.muted{opacity:.1}
.entity-column,.spine-column{position:relative;z-index:2;display:flex;flex-direction:column;justify-content:center;gap:18px;transform-style:preserve-3d}
.source-column{justify-content:space-around}.outcome-column{justify-content:space-between}
button{position:relative;min-height:126px;padding:16px;border:1px solid rgba(203,219,233,.13);border-radius:12px;background:linear-gradient(145deg,rgba(20,25,31,.97),rgba(9,12,15,.98));color:#f1f3ef;text-align:left;cursor:pointer;box-shadow:0 14px 32px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.025);transform:translateZ(0);transform-style:preserve-3d;transition:opacity 190ms ease,transform 190ms ease,border-color 190ms ease,box-shadow 190ms ease}
button::after{content:"";position:absolute;left:12px;right:12px;bottom:0;height:1px;background:linear-gradient(90deg,rgba(104,220,255,.52),transparent);opacity:.18;transition:opacity 190ms ease}
button:hover,button:focus-visible,button.active{transform:translate3d(0,-4px,28px);border-color:rgba(104,220,255,.55);box-shadow:0 22px 42px rgba(0,0,0,.32),0 0 24px rgba(78,114,255,.08);outline:none}
button.connected{transform:translate3d(0,-2px,11px);border-color:rgba(104,220,255,.28)}
button.active::after,button.connected::after{opacity:.82}
button.muted,.relation-ledger span.muted{opacity:.18}
.entity-type{display:block;color:#87939d;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase}
button strong{display:block;margin:11px 0 5px;font-family:"space-grotesk","Source Sans",sans-serif;font-size:23px;font-weight:520}
button b{position:absolute;top:15px;right:15px;color:#aebfff;font-family:"Source Code Pro",Consolas,monospace;font-size:11px;font-weight:520}
button code{display:block;margin-top:6px;color:#89959e;font-family:"Source Code Pro",Consolas,monospace;font-size:10px}
.event-entity{min-height:210px;border-color:rgba(104,220,255,.32);background:radial-gradient(circle at 50% 18%,rgba(78,114,255,.2),transparent 70%),#0c1117}
.spine-caption,.spine-rule,.join-label{color:#7a8791;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;text-align:center;text-transform:uppercase}
.join-label{position:absolute;left:0;right:0;top:50%;z-index:3;padding:4px;background:#090c0f}
.relation-ledger{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}
.relation-ledger span{padding:14px 15px;border-left:1px solid rgba(104,220,255,.35);background:rgba(255,255,255,.018);color:#8d99a2;font-size:11px;line-height:1.5;transition:opacity 190ms ease}
.relation-ledger b{display:block;margin-bottom:5px;color:#d1d7d8;font-family:"Source Code Pro",Consolas,monospace;font-size:10px;font-weight:520}
@media(max-width:760px){
  header{align-items:flex-start;flex-direction:column}.schema-map{grid-template-columns:1fr;gap:9px;min-height:0;padding:10px}.schema-map svg,.join-label{display:none}
  .entity-column,.spine-column{gap:9px}.source-column,.outcome-column{justify-content:flex-start}button,.event-entity{min-height:116px}
  button:hover,button:focus-visible,button.active{transform:translateY(-2px)}button.connected{transform:none}
  .relation-ledger{grid-template-columns:1fr}
}
@media(prefers-reduced-motion:reduce){*{transition-duration:.01ms!important}}
"""


SCHEMA_JS = """
export default function({ parentElement, data }) {
  const format=value=>new Intl.NumberFormat("en-IE").format(Number(value||0));
  ["customers","accounts","transactions","merchants","settlements","flags"].forEach(key=>{
    const el=parentElement.querySelector(`[data-count="${key}"]`);if(el)el.textContent=format(data[key]);
  });
  const buttons=[...parentElement.querySelectorAll("[data-entity]")];
  const relations=[...parentElement.querySelectorAll("[data-rel]")];
  let pinned=null;
  function keys(el){return (el.dataset.rel||"").split(",")}
  function activate(key){
    const linked=new Set([key]);
    relations.forEach(rel=>{const pair=keys(rel);if(pair.includes(key))pair.forEach(item=>linked.add(item))});
    buttons.forEach(button=>{
      const selected=button.dataset.entity===key;
      button.classList.toggle("active",selected);
      button.classList.toggle("connected",linked.has(button.dataset.entity)&&!selected);
      button.classList.toggle("muted",!linked.has(button.dataset.entity));
      button.setAttribute("aria-pressed",String(pinned===button.dataset.entity));
    });
    relations.forEach(rel=>{const active=keys(rel).includes(key);rel.classList.toggle("active",active);rel.classList.toggle("muted",!active)});
  }
  function clear(){buttons.forEach(el=>{el.classList.remove("active","connected","muted");el.setAttribute("aria-pressed","false")});relations.forEach(el=>el.classList.remove("active","muted"))}
  function toggle(button){pinned=pinned===button.dataset.entity?null:button.dataset.entity;if(pinned)activate(pinned);else clear()}
  buttons.forEach(button=>{
    button.setAttribute("aria-pressed","false");
    button.onpointerenter=()=>{if(!pinned)activate(button.dataset.entity)};button.onpointerleave=()=>{if(!pinned)clear()};
    button.onfocus=()=>{if(!pinned)activate(button.dataset.entity)};button.onblur=()=>{if(!pinned)clear()};button.onclick=()=>toggle(button);
    button.onkeydown=event=>{if(event.key!=="Enter"&&event.key!==" ")return;event.preventDefault();toggle(button)};
  });
  const escape=event=>{if(event.key!=="Escape")return;pinned=null;clear()};
  parentElement.addEventListener("keydown",escape);
  return()=>parentElement.removeEventListener("keydown",escape);
}
"""


HERO_COMPONENT = st.components.v2.component(
    "payments_topology",
    html=OBSERVATORY_RAIL_HTML,
    css=OBSERVATORY_RAIL_CSS,
    js=OBSERVATORY_RAIL_JS,
)

ER_COMPONENT = st.components.v2.component(
    "payments_data_model",
    html=SCHEMA_HTML,
    css=SCHEMA_CSS,
    js=SCHEMA_JS,
)

NAV_COMPONENT = st.components.v2.component(
    "payments_view_rail",
    html=NAV_HTML,
    css=NAV_CSS,
    js=NAV_JS,
)

FILTER_COMPONENT = st.components.v2.component(
    "payments_control_deck",
    html=FILTER_HTML,
    css=FILTER_CSS,
    js=FILTER_JS,
)

MEASURE_COMPONENT = st.components.v2.component(
    "payments_measure_switch",
    html=MEASURE_HTML,
    css=MEASURE_CSS,
    js=MEASURE_JS,
)

PAGE_MOTION_COMPONENT = st.components.v2.component(
    "payments_page_motion",
    html='<span class="pay-motion-hook" aria-hidden="true"></span>',
    css=".pay-motion-hook { display: none; height: 0; }",
    js=PAGE_MOTION_JS,
    isolate_styles=False,
)


def apply_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="pay-progress" aria-hidden="true"><span class="pay-progress-fill"></span></div>',
        unsafe_allow_html=True,
    )


def render_topbar(
    source: str,
    first_date: str,
    last_date: str,
    *,
    case_study_url: str,
) -> None:
    brand_mark = _load_brand_mark()
    st.markdown(
        f"""
        <div class="pay-topbar">
          <div class="pay-brand">
            <span class="pay-brand-mark" data-brand-mark aria-hidden="true">{brand_mark}</span>
            <div>
              <div class="pay-brand-name">Payment Observatory</div>
              <div class="pay-brand-sub">Payments intelligence</div>
            </div>
          </div>
          <div class="pay-top-meta">
            <a class="pay-case-study" href="{escape(case_study_url, quote=True)}" target="_blank" rel="noopener noreferrer">
              Read case study
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3h7v7M13 3 5 11M11 9v4H3V5h4"/></svg>
            </a>
            <span class="pay-chip">{escape(first_date)} to {escape(last_date)}</span>
            <span class="pay-chip">6 linked tables</span>
            <span class="pay-source">{escape(source)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_navigation(active_view: str) -> str:
    """Render the custom view rail and return its active route."""

    saved_component_state = st.session_state.get("pay_view_rail", {})
    if isinstance(saved_component_state, Mapping):
        saved_view = saved_component_state.get("view")
        if saved_view in {"overview", "merchant", "risk", "retention", "model"}:
            active_view = str(saved_view)
    try:
        result = NAV_COMPONENT(
            key="pay_view_rail",
            data={"view": active_view},
            default={"view": active_view},
            on_view_change=lambda: None,
            height="content",
        )
        selected = getattr(result, "view", None)
        if selected in {"overview", "merchant", "risk", "retention", "model"}:
            return str(selected)
    except Exception:
        pass
    return active_view


def render_filter_controls(
    *,
    dataset_start: str,
    dataset_end: str,
    currencies: Iterable[str],
    categories: Iterable[str],
    current: Mapping[str, object],
) -> dict[str, object] | None:
    """Render the bidirectional filter deck with a safe Python fallback."""

    currency_options = list(currencies)
    category_options = list(categories)
    defaults = {
        "startDate": dataset_start,
        "endDate": dataset_end,
        "currencies": currency_options,
        "categories": category_options,
        "comparePrevious": False,
    }
    current_payload = {
        "startDate": str(current.get("startDate", dataset_start)),
        "endDate": str(current.get("endDate", dataset_end)),
        "currencies": list(current.get("currencies", currency_options)),
        "categories": list(current.get("categories", category_options)),
        "comparePrevious": bool(current.get("comparePrevious", False)),
    }
    saved_component_state = st.session_state.get("pay_filter_deck", {})
    if isinstance(saved_component_state, Mapping):
        saved_filters = saved_component_state.get("filters")
        if isinstance(saved_filters, Mapping):
            current_payload = {
                "startDate": str(saved_filters.get("startDate", dataset_start)),
                "endDate": str(saved_filters.get("endDate", dataset_end)),
                "currencies": list(
                    saved_filters.get("currencies", currency_options)
                ),
                "categories": list(
                    saved_filters.get("categories", category_options)
                ),
                "comparePrevious": bool(
                    saved_filters.get("comparePrevious", False)
                ),
            }
    try:
        result = FILTER_COMPONENT(
            key="pay_filter_deck",
            data={
                "minDate": dataset_start,
                "maxDate": dataset_end,
                "currencies": currency_options,
                "categories": category_options,
                "current": current_payload,
                "defaults": defaults,
            },
            default={"filters": current_payload},
            on_filters_change=lambda: None,
            height="content",
        )
        selected = getattr(result, "filters", None)
        if isinstance(selected, Mapping):
            return dict(selected)
        return current_payload
    except Exception:
        return None


def render_measure_switch(current: str) -> str:
    """Render the local trend switch and retain a native fallback."""

    options = ["Transaction count", "Completed value"]
    if current not in options:
        current = options[0]
    saved_component_state = st.session_state.get(
        "pay_trend_measure_component", {}
    )
    if isinstance(saved_component_state, Mapping):
        saved_value = saved_component_state.get("value")
        if saved_value in options:
            current = str(saved_value)
    try:
        result = MEASURE_COMPONENT(
            key="pay_trend_measure_component",
            data={"options": options, "current": current},
            default={"value": current},
            on_value_change=lambda: None,
            height="content",
        )
        selected = getattr(result, "value", None)
        return str(selected) if selected in options else current
    except Exception:
        fallback = st.segmented_control(
            "Trend measure",
            options=options,
            default=current,
            key="pay_trend_measure_fallback",
        )
        return str(fallback) if fallback in options else current


def render_hero(scope: Mapping[str, object], source: str) -> None:
    first_date = pd.Timestamp(scope["first_transaction_date"]).strftime("%b %Y")
    last_date = pd.Timestamp(scope["last_transaction_date"]).strftime("%b %Y")
    HERO_COMPONENT(
        key="payment_topology",
        data={
            "customers": int(scope["customer_count"]),
            "accounts": int(scope["account_count"]),
            "merchants": int(scope["merchant_count"]),
            "transactions": int(scope["transaction_count"]),
            "settlements": int(scope["settlement_count"]),
            "flags": int(scope["fraud_flag_count"]),
            "merchantless": int(scope["merchantless_transaction_count"]),
            "source": source,
            "window": f"{first_date} to {last_date}",
        },
        height="content",
    )


def render_filter_note(text: str) -> None:
    st.markdown(
        f'<div class="pay-filter-note">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, body: str, kicker: str = "Analysis") -> None:
    st.markdown(
        f"""
        <div class="pay-section-heading pay-reveal">
          <div>
            <span class="pay-section-kicker">{escape(kicker)}</span>
            <h2>{escape(title)}</h2>
          </div>
          <p>{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_grid(cards: Iterable[Mapping[str, object]]) -> None:
    html = []
    for card in cards:
        comparison = str(card.get("comparison", ""))
        comparison_tone = str(card.get("comparison_tone", ""))
        comparison_html = (
            f'<span class="pay-variance {escape(comparison_tone)}">{escape(comparison)}</span>'
            if comparison
            else ""
        )
        html.append(
            f'<article class="pay-kpi-card {escape(str(card.get("tone", "cyan")))}">'
            f'<span class="pay-card-label">{escape(str(card["label"]))}</span>'
            f'<strong class="pay-kpi-value" data-number="{float(card["number"])}" '
            f'data-decimals="{int(card.get("decimals", 0))}" '
            f'data-prefix="{escape(str(card.get("prefix", "")))}" '
            f'data-suffix="{escape(str(card.get("suffix", "")))}">'
            f'{escape(str(card["value"]))}</strong>'
            f'<p>{escape(str(card["note"]))}</p>'
            f'{comparison_html}</article>'
        )
    st.markdown(
        f'<div class="pay-kpi-grid pay-reveal">{"".join(html)}</div>',
        unsafe_allow_html=True,
    )


def render_metric_strip(cards: Iterable[Mapping[str, object]]) -> None:
    """Render compact analytical readouts with a consistent visual hierarchy."""

    items = []
    for card in cards:
        tone = escape(str(card.get("tone", "cyan")))
        items.append(
            f'<article class="pay-readout {tone}">'
            f'<span class="pay-readout-label">{escape(str(card["label"]))}</span>'
            f'<strong>{escape(str(card["value"]))}</strong>'
            f'<p>{escape(str(card.get("note", "")))}</p>'
            "</article>"
        )
    st.markdown(
        f'<section class="pay-metric-strip pay-reveal" '
        f'aria-label="Key metrics">{"".join(items)}</section>',
        unsafe_allow_html=True,
    )


def render_status_rail(
    title: str,
    subtitle: str,
    rows: pd.DataFrame,
    colors: Mapping[str, str],
) -> None:
    segments = []
    legend = []
    for row in rows.itertuples(index=False):
        status = str(row.status)
        share = float(row.share)
        count = int(row.count)
        color = colors.get(status, "#8fa5b5")
        segments.append(
            f'<span class="pay-status-segment" style="width:{share:.4f}%;--segment:{escape(color)}" title="{escape(status.title())}: {count:,}"></span>'
        )
        legend.append(
            f'<span class="pay-legend-item" style="--segment:{escape(color)}">{escape(status.title())} <strong>{count:,}</strong></span>'
        )
    st.markdown(
        f"""
        <div class="pay-status-card pay-reveal">
          <div class="pay-status-head"><strong>{escape(title)}</strong><span>{escape(subtitle)}</span></div>
          <div class="pay-status-track">{"".join(segments)}</div>
          <div class="pay-status-legend">{"".join(legend)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settlement_corridor(rows: pd.DataFrame) -> None:
    colors = {
        "settled": "#8AF6C7",
        "delayed": "#F4C86A",
        "disputed": "#FF756F",
    }
    descriptions = {
        "settled": "Recorded as settled",
        "delayed": "Recorded as delayed",
        "disputed": "Recorded as disputed",
    }
    lanes = []
    total = int(rows["count"].sum()) if not rows.empty else 0
    for index, row in enumerate(rows.itertuples(index=False), start=1):
        status = str(row.status)
        count = int(row.count)
        share = float(row.share)
        color = colors.get(status, "#8FA5B5")
        label = status.title()
        lanes.append(
            f'<div class="pay-corridor-lane" tabindex="0" role="listitem" '
            f'aria-label="{escape(label)}: {count:,} records, {share:.2f} percent" '
            f'style="--lane:{escape(color)};--share:{share:.4f}%">'
            f'<span class="pay-lane-index">0{index} / {share:.1f}%</span>'
            f'<span class="pay-lane-main"><strong>{escape(label)}</strong><b>{count:,}</b></span>'
            f'<span class="pay-lane-track"><i></i></span>'
            f'<p>{escape(descriptions.get(status, "Recorded settlement outcome"))}</p>'
            "</div>"
        )
    st.markdown(
        f"""
        <section class="pay-settlement-corridor pay-reveal" aria-label="Settlement processing corridor">
          <div class="pay-corridor-head">
            <strong>Settlement processing corridor</strong>
            <span>{total:,} linked records / active scope</span>
          </div>
          <div class="pay-corridor-lanes" role="list">{"".join(lanes)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(
    title: str = "No records match these filters.",
    body: str = "Widen the date range or restore a currency or merchant category.",
) -> None:
    st.markdown(
        f"""
        <div class="pay-empty-state">
          <strong>{escape(title)}</strong>
          <span>{escape(body)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_note(text: str, tone: str = "") -> None:
    st.markdown(
        f'<div class="pay-data-note {escape(tone)}">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def render_method_cards() -> None:
    cards = [
        (
            "Source continuity",
            "The app tries PostgreSQL first. If the connection is unavailable, it rebuilds the same views from the six repository CSV files.",
        ),
        (
            "Nominal values",
            "Amounts remain in their recorded currencies. A mixed selection is nominal and is never presented as an FX-converted total.",
        ),
        (
            "Review interpretation",
            "Fraud flags were sampled during data generation. They are useful for SQL and reporting practice, not for predictive risk decisions.",
        ),
        (
            "Retention method",
            "A customer is active in a cohort month when at least one linked account has a completed transaction. Future months remain blank.",
        ),
        (
            "Analytical preparation",
            "Pandas normalises source types and applies the same filter rules to PostgreSQL and CSV records before any metric is rendered.",
        ),
        (
            "Synthetic data",
            "All people, merchants and payment activity are generated records. They model commercial relationships without representing real customers.",
        ),
    ]
    html = "".join(
        f'<article class="pay-method-card">'
        f'<span class="pay-card-label">Method note</span>'
        f'<strong>{escape(title)}</strong>'
        f'<p>{escape(body)}</p>'
        f'</article>'
        for title, body in cards
    )
    st.markdown(
        f'<div class="pay-method-grid pay-reveal">{html}</div>',
        unsafe_allow_html=True,
    )


def render_data_model(scope: Mapping[str, object]) -> None:
    ER_COMPONENT(
        key="relational_model",
        data={
            "customers": int(scope["customer_count"]),
            "accounts": int(scope["account_count"]),
            "merchants": int(scope["merchant_count"]),
            "transactions": int(scope["transaction_count"]),
            "settlements": int(scope["settlement_count"]),
            "flags": int(scope["fraud_flag_count"]),
        },
        height="content",
    )


def mount_page_motion() -> None:
    PAGE_MOTION_COMPONENT(key="page_motion", height=0)


def render_footer() -> None:
    st.markdown(
        """
        <div class="pay-footer">
          <span>Payment Observatory / Payments Intelligence</span>
          <span>PostgreSQL · Python · Streamlit · Plotly</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
