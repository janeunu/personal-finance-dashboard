"""
ui.py — Money Health Agent UI system

Purpose:
- Design system
- Streamlit CSS
- Reusable dashboard components
- V7 manager-approved layout components

Important:
- No data logic here
- No metric calculations here
- No parser/categoriser logic here
- UI only
"""

from __future__ import annotations

import html as _html
import textwrap
from typing import Iterable

import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════

COLOR = {
    "navy": "#1A2332",
    "accent": "#6941C6",
    "income": "#12B76A",
    "expense": "#F04438",
    "warning": "#F79009",

    "page_bg": "#F7F8FA",
    "card_bg": "#FFFFFF",
    "surface": "#F9FAFB",
    "border": "#EAECF0",
    "border_sub": "#F2F4F7",

    "text_primary": "#101828",
    "text_secondary": "#475467",
    "text_muted": "#98A2B3",
    "text_on_dark": "#F9FAFB",
}


# ══════════════════════════════════════════════════════════════════════════════
# BASE CSS
# ══════════════════════════════════════════════════════════════════════════════

STYLESHEET = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

.stMainBlockContainer, .block-container {
    padding: 0.55rem 1.5rem 2rem !important;
    max-width: 1320px !important;
}

[data-testid="stAppViewContainer"] > section > div {
    background: #F7F8FA !important;
}

[data-testid="stVerticalBlock"] {
    gap: 0.35rem !important;
}

[data-testid="column"] {
    padding-left: 5px !important;
    padding-right: 5px !important;
}

[data-testid="stPlotlyChart"] {
    padding: 0 !important;
}

[data-testid="stPlotlyChart"] > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

[data-testid="stMarkdownContainer"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

[data-testid="stMarkdownContainer"] > * {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* Compact file uploader */
[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 5px 12px !important;
    min-height: 44px !important;
}

[data-testid="stFileUploaderDropzone"] > div {
    padding: 3px 0 !important;
    gap: 4px !important;
}

[data-testid="stFileUploader"] section p {
    font-size: 12px !important;
    margin: 0 !important;
}

[data-testid="stFileUploader"] {
    margin: 0 !important;
}

/* Compact inputs */
div[data-testid="stSelectbox"] div[role="combobox"],
div[data-testid="stTextInput"] input {
    min-height: 34px !important;
    font-size: 12.5px !important;
}

div[data-testid="stButton"] button,
div[data-testid="stDownloadButton"] button {
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    min-height: 34px !important;
    border-radius: 9px !important;
    font-size: 12.5px !important;
}

/* Navigation pills using st.radio */
div[data-testid="stRadio"] {
    margin-top: 3px !important;
    margin-bottom: 5px !important;
}

div[data-testid="stRadio"] > div:first-child {
    display: none !important;
}

div[data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
}

div[data-testid="stRadio"] label[data-baseweb="radio"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border: 1px solid #EAECF0 !important;
    border-radius: 999px !important;
    padding: 5px 15px !important;
    background: #FFFFFF !important;
    color: #475467 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    margin: 0 !important;
}

div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background: #6941C6 !important;
    border-color: #6941C6 !important;
    color: #FFFFFF !important;
}

/* Legacy / general components */
.mh-privacy {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 7px;
    padding: 5px 12px;
    margin-bottom: 5px;
    font-size: 11.5px;
    color: #64748B;
    line-height: 1.4;
}

.mh-card {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 12px;
    padding: 14px 16px;
}

.mh-card-title {
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #64748B;
    margin-bottom: 8px;
}

.mh-section {
    display: flex;
    align-items: center;
    gap: 7px;
    margin: 12px 0 7px;
}

.mh-section-dot {
    width: 4px;
    height: 15px;
    border-radius: 6px;
    background: #6941C6;
}

.mh-section-text {
    font-size: 10.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: #64748B;
}

.mh-verdict {
    background: #0F172A;
    border-radius: 13px;
    padding: 22px 28px;
    display: flex;
    align-items: center;
    gap: 24px;
}

.mh-verdict-score {
    font-size: 72px;
    line-height: 0.95;
    letter-spacing: -3px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    min-width: 108px;
}

.mh-verdict-tag {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .11em;
    text-transform: uppercase;
    color: #94A3B8;
    margin-bottom: 7px;
}

.mh-verdict-headline {
    color: #F8FAFC;
    font-size: 17.5px;
    font-weight: 700;
    line-height: 1.32;
    margin-bottom: 7px;
}

.mh-verdict-sub {
    font-size: 11.5px;
    color: #94A3B8;
    line-height: 1.5;
}

.mh-kpi {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 12px;
    padding: 12px 13px 10px;
    min-height: 78px;
}

.mh-kpi-label {
    font-size: 9.8px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #98A2B3;
    margin-bottom: 6px;
}

.mh-kpi-value {
    font-size: 21px;
    line-height: 1.1;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: #101828;
}

.mh-kpi-delta {
    font-size: 11px;
    color: #98A2B3;
    margin-top: 5px;
}

.pos { color: #12B76A !important; }
.neg { color: #F04438 !important; }
.neu { color: #98A2B3 !important; }

/* Transaction table */
.txn-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 12.5px;
}

.txn-table th {
    font-size: 9.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #98A2B3;
    padding: 7px 10px;
    text-align: left;
    border-bottom: 1px solid #EAECF0;
    background: #FAFAFA;
}

.txn-table td {
    padding: 8px 10px;
    border-bottom: 0.5px solid #F2F4F7;
    vertical-align: middle;
}

.txn-table tr:hover td {
    background: #FAFAFA;
}

.txn-num {
    color: #D0D5DD;
    font-size: 10.5px;
    width: 24px;
}

.txn-date {
    color: #98A2B3;
    white-space: nowrap;
    width: 86px;
}

.txn-desc {
    color: #374151;
    font-weight: 500;
}

.txn-amt-pos {
    color: #12B76A;
    font-weight: 600;
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.txn-amt-neg {
    color: #F04438;
    font-weight: 600;
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.cat-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 7px;
    border-radius: 99px;
    font-size: 10.5px;
    font-weight: 500;
    white-space: nowrap;
}

.cat-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
}

.conf-track {
    background: #EAECF0;
    border-radius: 3px;
    height: 3px;
    width: 56px;
    overflow: hidden;
}

.conf-fill {
    height: 100%;
    border-radius: 3px;
}

.disclaimer,
.mh-disclaimer {
    font-size: 11px;
    color: #98A2B3;
    text-align: center;
    margin-top: 24px;
    padding: 10px;
    border-top: 1px solid #EAECF0;
    line-height: 1.5;
}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# V7 CSS
# ══════════════════════════════════════════════════════════════════════════════

V7_STYLESHEET = """
<style>
:root {
    --v7-bg: #F7F8FA;
    --v7-card: #FFFFFF;
    --v7-border: #E6E8EC;
    --v7-border-soft: #F1F3F5;
    --v7-navy: #0F172A;
    --v7-purple: #6941C6;
    --v7-green: #12B76A;
    --v7-red: #F04438;
    --v7-amber: #F79009;
    --v7-text: #101828;
    --v7-muted: #667085;
    --v7-faint: #98A2B3;
}

.block-container {
    max-width: 1180px !important;
    padding-top: 0.55rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
    padding-bottom: 2rem !important;
}

.v7-top-note {
    background: #FFFFFF;
    border: 1px solid var(--v7-border);
    border-radius: 8px;
    padding: 5px 10px;
    font-size: 11.5px;
    color: var(--v7-muted);
    line-height: 1.35;
    margin-bottom: 4px;
}

.v7-section {
    display: flex;
    align-items: center;
    gap: 7px;
    margin: 12px 0 6px;
}

.v7-section-dot {
    width: 4px;
    height: 15px;
    border-radius: 6px;
    background: var(--v7-purple);
}

.v7-section-label {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: #64748B;
}

.v7-section-helper {
    font-size: 12.2px;
    color: var(--v7-faint);
    margin: -3px 0 8px 11px;
}

.v7-card {
    background: var(--v7-card);
    border: 1px solid var(--v7-border);
    border-radius: 12px;
    padding: 13px 15px;
}

.v7-hero {
    background: var(--v7-navy);
    border-radius: 13px;
    padding: 22px 28px;
    min-height: 124px;
    display: flex;
    align-items: center;
    gap: 24px;
}

.v7-score {
    font-size: 72px;
    line-height: 0.95;
    letter-spacing: -3px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--v7-green);
    min-width: 108px;
}

.v7-score-meta {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: .11em;
    text-transform: uppercase;
    color: #94A3B8;
    margin-bottom: 7px;
}

.v7-score-headline {
    color: #F8FAFC;
    font-size: 17.5px;
    font-weight: 700;
    line-height: 1.32;
    margin-bottom: 7px;
}

.v7-score-summary {
    font-size: 11.5px;
    color: #94A3B8;
    line-height: 1.5;
}

.v7-kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
}

.v7-kpi {
    background: white;
    border: 1px solid var(--v7-border);
    border-radius: 12px;
    padding: 12px 13px 10px;
    min-height: 78px;
}

.v7-kpi-label {
    font-size: 9.8px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--v7-faint);
    margin-bottom: 6px;
}

.v7-kpi-value {
    font-size: 21px;
    line-height: 1.1;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--v7-text);
}

.v7-kpi-sub {
    font-size: 11px;
    color: var(--v7-faint);
    margin-top: 5px;
}

.v7-pos { color: var(--v7-green) !important; }
.v7-neg { color: var(--v7-red) !important; }
.v7-warn { color: var(--v7-amber) !important; }
.v7-purple { color: var(--v7-purple) !important; }

.v7-mini-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid var(--v7-border-soft);
}

.v7-mini-row:last-child {
    border-bottom: 0;
}

.v7-mini-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--v7-text);
}

.v7-mini-sub {
    font-size: 10.8px;
    color: var(--v7-faint);
    margin-top: 1px;
}

.v7-mini-value {
    font-size: 12.5px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.v7-progress-track {
    width: 100%;
    height: 6px;
    background: #EEF2F6;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 6px;
}

.v7-progress-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--v7-green);
}

.v7-progress-fill.warn {
    background: var(--v7-amber);
}

.v7-progress-fill.danger {
    background: var(--v7-red);
}

.v7-insight {
    background: #FFFCF5;
    border: 1px solid #FDECC8;
    border-radius: 11px;
    padding: 12px 14px;
    min-height: 76px;
}

.v7-insight-title {
    font-size: 12.5px;
    font-weight: 700;
    color: var(--v7-text);
    margin-bottom: 4px;
}

.v7-insight-body {
    font-size: 11.8px;
    color: var(--v7-muted);
    line-height: 1.45;
}

.v7-txn-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    background: white;
}

.v7-txn-table th {
    text-align: left;
    padding: 8px 9px;
    font-size: 9.5px;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--v7-faint);
    background: #FAFAFA;
    border-bottom: 1px solid var(--v7-border);
}

.v7-txn-table td {
    padding: 8px 9px;
    border-bottom: 1px solid var(--v7-border-soft);
    color: var(--v7-text);
    vertical-align: middle;
}

.v7-txn-table tr:hover td {
    background: #FAFAFA;
}

.v7-amount {
    text-align: right;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.v7-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 10.5px;
    font-weight: 600;
    background: #F3F4F6;
    color: #374151;
    white-space: nowrap;
}

.v7-conf {
    width: 48px;
    height: 4px;
    background: #E5E7EB;
    border-radius: 999px;
    overflow: hidden;
}

.v7-conf-fill {
    height: 100%;
    border-radius: 999px;
}

.v7-muted {
    color: var(--v7-faint);
}
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# CSS INJECTION
# ══════════════════════════════════════════════════════════════════════════════

def inject_css() -> None:
    """Inject base design system stylesheet."""
    st.markdown(STYLESHEET, unsafe_allow_html=True)


def inject_v7_css() -> None:
    """Inject V7 manager-approved dashboard styles."""
    st.markdown(V7_STYLESHEET, unsafe_allow_html=True)


def v7_render_html(html: str) -> None:
    """
    Safely render V7 HTML.

    textwrap.dedent prevents Streamlit Markdown from interpreting indented
    multi-line HTML as a code block.
    """
    st.markdown(
        textwrap.dedent(html).strip(),
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════

def _safe(value: object) -> str:
    """HTML-safe text."""
    return _html.escape("" if value is None else str(value))


def fmt_money(value: float, sym: str = "$", signed: bool = False) -> str:
    """Standard money formatter."""
    try:
        value = float(value)
    except Exception:
        value = 0.0

    abs_v = abs(value)
    body = f"{abs_v:,.0f}" if abs_v >= 1_000 else f"{abs_v:,.2f}"

    if signed:
        return f"+{sym}{body}" if value >= 0 else f"-{sym}{body}"

    return f"{sym}{body}"


def fmt_money_kpi(value: float, sym: str = "$", signed: bool = False) -> str:
    """Abbreviated KPI money formatter."""
    try:
        value = float(value)
    except Exception:
        value = 0.0

    abs_v = abs(value)

    if abs_v >= 1_000_000_000:
        body = f"{abs_v / 1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        body = f"{abs_v / 1_000_000:.2f}M"
    elif abs_v >= 100_000:
        body = f"{abs_v / 1_000:.1f}K"
    elif abs_v >= 1_000:
        body = f"{abs_v:,.0f}"
    else:
        body = f"{abs_v:,.2f}"

    if signed:
        return f"+{sym}{body}" if value >= 0 else f"-{sym}{body}"

    return f"{sym}{body}"


def v7_money(value: float, sym: str = "$", signed: bool = False) -> str:
    """Compact V7 money formatter."""
    try:
        value = float(value)
    except Exception:
        value = 0.0

    sign = ""
    if signed:
        sign = "+" if value >= 0 else "-"

    abs_v = abs(value)

    if abs_v >= 1_000_000:
        body = f"{abs_v / 1_000_000:.1f}M"
    elif abs_v >= 100_000:
        body = f"{abs_v / 1_000:.0f}K"
    elif abs_v >= 10_000:
        body = f"{abs_v / 1_000:.1f}K"
    elif abs_v >= 1_000:
        body = f"{abs_v:,.0f}"
    else:
        body = f"{abs_v:,.2f}"

    return f"{sign}{sym}{body}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return f"{0:.{decimals}f}%"


def v7_pct(value: float, decimals: int = 0) -> str:
    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return "0%"


def delta_badge(current: float, previous: float, invert: bool = False) -> str:
    """HTML span showing percent change."""
    if previous == 0:
        return '<span class="neu">—</span>'

    pct = (current - previous) / abs(previous) * 100
    up = pct > 0
    good = up if not invert else not up
    cls = "pos" if good else "neg"
    arrow = "▲" if up else "▼"

    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


def _score_color(score: int) -> str:
    if score >= 80:
        return "#34D399"
    if score >= 65:
        return "#60A5FA"
    if score >= 45:
        return "#FBBF24"
    return "#F87171"


def v7_score_color(score: int) -> str:
    if score >= 80:
        return "#34D399"
    if score >= 65:
        return "#A78BFA"
    if score >= 45:
        return "#FBBF24"
    return "#F87171"


# ══════════════════════════════════════════════════════════════════════════════
# GENERAL / LEGACY COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def privacy_notice() -> None:
    st.markdown(
        """
        <div class="mh-privacy">
            Your file is processed only in this session — never stored or shared.
            For personal tracking only, not financial advice.
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(label: str, helper: str = "") -> None:
    helper_html = (
        f'<div style="font-size:13px;color:{COLOR["text_muted"]};margin:-4px 0 10px;font-weight:400">'
        f'{_safe(helper)}</div>'
        if helper else ""
    )

    st.markdown(
        f"""
        <div class="mh-section">
            <div class="mh-section-dot"></div>
            <div class="mh-section-text">{_safe(label)}</div>
        </div>
        {helper_html}
        """,
        unsafe_allow_html=True,
    )


def verdict_banner(
    score: int,
    score_label: str,
    headline: str,
    sub_html: str,
) -> None:
    color = _score_color(score)

    st.markdown(
        f"""
        <div class="mh-verdict">
            <div class="mh-verdict-score" style="color:{color}">{int(score)}</div>
            <div>
                <div class="mh-verdict-tag">Money health score &nbsp;·&nbsp; {_safe(score_label)}</div>
                <div class="mh-verdict-headline">{_safe(headline)}</div>
                <div class="mh-verdict-sub">{sub_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(
    label: str,
    value: str,
    value_color: str,
    delta_html: str,
    delta_context: str = "",
) -> None:
    ctx = f' <span class="neu">{_safe(delta_context)}</span>' if delta_context else ""

    st.markdown(
        f"""
        <div class="mh-kpi">
            <div class="mh-kpi-label">{_safe(label)}</div>
            <div class="mh-kpi-value" style="color:{value_color}">{_safe(value)}</div>
            <div class="mh-kpi-delta">{delta_html}{ctx}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_start(title: str = "") -> None:
    title_html = f'<div class="mh-card-title">{_safe(title)}</div>' if title else ""
    st.markdown(f'<div class="mh-card">{title_html}', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def spend_item(
    name: str,
    rank_label: str,
    amount: float,
    sym: str = "$",
    color: str = "",
) -> None:
    c = color or COLOR["expense"]

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
        padding:11px 0;border-bottom:1px solid #F1F5F9">
            <div>
                <div style="font-size:13.5px;font-weight:400;color:#374151">{_safe(name)}</div>
                <div style="font-size:11px;color:#94A3B8;margin-top:1px">{_safe(rank_label)}</div>
            </div>
            <div style="font-size:17px;font-weight:600;font-variant-numeric:tabular-nums;
            color:{c};letter-spacing:-0.3px">{fmt_money(amount, sym)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def budget_bar(
    category: str,
    amount_str: str,
    actual_pct: float,
    rec_pct: int,
) -> None:
    bar_w = min(actual_pct / rec_pct * 100, 108) if rec_pct else 0.0

    if actual_pct > rec_pct:
        color, status, status_color = "#E11D48", "Over budget", "#E11D48"
    elif actual_pct > rec_pct * 0.85:
        color, status, status_color = "#D97706", "Near limit", "#D97706"
    else:
        color, status, status_color = "#059669", "On track", "#059669"

    st.markdown(
        f"""
        <div style="margin-bottom:13px">
            <div style="display:flex;justify-content:space-between;font-size:12px;font-weight:600;color:#374151">
                <span>{_safe(category)}
                    <span style="color:#94A3B8;font-weight:400;font-size:11.5px">{_safe(amount_str)}</span>
                </span>
                <span style="color:{status_color}">{status}</span>
            </div>
            <div style="width:100%;height:6px;background:#EEF2F6;border-radius:999px;overflow:hidden;margin-top:6px;">
                <div style="height:100%;width:{bar_w:.1f}%;background:{color};border-radius:999px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(html_body: str) -> None:
    st.markdown(f'<div class="mh-card">{html_body}</div>', unsafe_allow_html=True)


def action_card(num: int, emoji: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="mh-card" style="display:flex;gap:12px;align-items:flex-start;">
            <div style="width:26px;height:26px;border-radius:50%;background:#F4EBFF;
            color:#6941C6;display:flex;align-items:center;justify-content:center;
            font-size:12px;font-weight:700;">{num}</div>
            <div>
                <div style="font-size:13px;font-weight:700;color:#101828">{_safe(title)}</div>
                <div style="font-size:12px;color:#667085;line-height:1.45">{_safe(description)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def transaction_card(
    amount: str,
    description: str,
    date: str,
    category: str,
) -> None:
    st.markdown(
        f"""
        <div class="mh-card">
            <div style="font-size:16px;font-weight:700;color:#F04438">{_safe(amount)}</div>
            <div style="font-size:13px;font-weight:600;color:#101828">{_safe(description)}</div>
            <div style="font-size:11px;color:#98A2B3">{_safe(date)} · {_safe(category)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def subscription_list(rows_html: str, total_str: str) -> None:
    total_row = (
        f"""
        <div style="display:flex;justify-content:space-between;padding:10px 0 2px;
        font-size:12.5px;color:#94A3B8;font-weight:500;border-top:1px solid #F1F5F9;
        margin-top:2px">
            <span>Total</span>
            <span style="font-size:15px;font-weight:600;font-variant-numeric:tabular-nums;
            color:#E11D48">{_safe(total_str)}</span>
        </div>
        """
    )

    st.markdown(
        f'<div class="mh-card" style="padding:14px 18px">{rows_html}{total_row}</div>',
        unsafe_allow_html=True,
    )


def ai_panel(text: str) -> None:
    st.markdown(
        f"""
        <div class="mh-card" style="background:#F8FAFC;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;
            color:#6941C6;letter-spacing:.08em;margin-bottom:6px;">AI insights</div>
            <div style="font-size:13px;color:#475467;line-height:1.55">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ai_empty_state() -> None:
    st.markdown(
        """
        <div style="padding:28px;text-align:center;color:#94A3B8;font-size:13.5px">
            Enter your API key and click <strong>Generate insights</strong>
            for personalised coaching.
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_info_bar(
    col_map: dict[str, str],
    method: str,
    currency: str,
    warnings: list[str],
) -> None:
    badge = (
        '<span style="background:#F4EBFF;color:#6941C6;padding:2px 6px;border-radius:99px;font-size:10px;">AI</span>'
        if method == "ai"
        else '<span style="background:#ECFDF3;color:#027A48;padding:2px 6px;border-radius:99px;font-size:10px;">keyword</span>'
    )

    html = (
        f'Columns detected {badge}: '
        f'Date → <code>{_safe(col_map.get("date", "?"))}</code> · '
        f'Description → <code>{_safe(col_map.get("description", "?"))}</code> · '
        f'Amount → <code>{_safe(col_map.get("amount", "?"))}</code>'
    )

    if currency and currency != "$":
        html += f" · Currency: <strong>{_safe(currency)}</strong>"

    if warnings:
        html += "<br>" + " | ".join(_safe(w) for w in warnings)

    st.markdown(
        f"""
        <div class="mh-card" style="font-size:11.5px;color:#667085;padding:8px 12px;">
            {html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def onboarding_tiles() -> None:
    tiles = [
        ("🌍", "Works with many banks", "Upload CSV or Excel statements and let the app detect the structure."),
        ("🧠", "Smart categorisation", "Transactions are cleaned, categorised, scored, and flagged for review."),
        ("⚡", "Plain-English results", "See your money position clearly without finance knowledge."),
    ]

    cols = st.columns(3)

    for col, (icon, title, desc) in zip(cols, tiles):
        with col:
            st.markdown(
                f"""
                <div class="mh-card" style="text-align:center;height:100%;">
                    <div style="font-size:24px;margin-bottom:8px">{icon}</div>
                    <div style="font-size:13.5px;font-weight:700;color:#101828;margin-bottom:4px">
                        {_safe(title)}
                    </div>
                    <div style="font-size:12px;color:#667085;line-height:1.5">
                        {_safe(desc)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def disclaimer() -> None:
    st.markdown(
        """
        <div class="mh-disclaimer">
            Money Health is for personal education and spending awareness only.
            It does not constitute financial, tax, investment, or credit advice.
        </div>
        """,
        unsafe_allow_html=True,
    )


def category_badge(category: str) -> str:
    """Return HTML category badge."""
    try:
        from config import category_badge_colors
        bg, text = category_badge_colors(category)
    except Exception:
        bg, text = "#F3F4F6", "#374151"

    return (
        f'<span class="cat-badge" style="background:{bg};color:{text}">'
        f'<span class="cat-dot" style="background:{text}"></span>'
        f'{_safe(category)}'
        f'</span>'
    )


def confidence_bar(confidence: str) -> str:
    widths = {"High": 100, "Medium": 60, "Low": 25}
    colors = {"High": "#12B76A", "Medium": "#F79009", "Low": "#F04438"}

    w = widths.get(confidence, 25)
    c = colors.get(confidence, "#F04438")

    return (
        f'<div style="display:flex;align-items:center;gap:5px">'
        f'<div class="conf-track"><div class="conf-fill" style="width:{w}%;background:{c}"></div></div>'
        f'<span style="font-size:10px;color:#98A2B3">{_safe(confidence or "Low")}</span>'
        f'</div>'
    )


def styled_transaction_table(
    df,
    sym: str = "$",
    max_rows: int = 12,
    page: int = 0,
) -> tuple[str, int]:
    """Return styled transaction table HTML and total pages."""
    if df is None or df.empty:
        return '<div class="mh-card">No transactions found.</div>', 1

    start = page * max_rows
    page_df = df.iloc[start : start + max_rows]
    total_pages = max(1, -(-len(df) // max_rows))

    rows_html = ""

    for i, (_, row) in enumerate(page_df.iterrows()):
        num = start + i + 1

        date = row.get("Date", "")
        if hasattr(date, "strftime"):
            date = date.strftime("%d %b %Y")
        else:
            date = str(date)

        desc = str(row.get("Description", ""))[:42]
        cat = str(row.get("Category", "Other Expense"))
        conf = str(row.get("Confidence", ""))
        flag = str(row.get("Flag", ""))

        try:
            amt = float(row.get("Amount", 0))
        except Exception:
            amt = 0.0

        amt_str = f"+{sym}{abs(amt):,.2f}" if amt >= 0 else f"-{sym}{abs(amt):,.2f}"
        amt_class = "txn-amt-pos" if amt >= 0 else "txn-amt-neg"
        flag_note = '<span style="color:#F79009;font-size:10px"> ⚑</span>' if flag else ""

        rows_html += (
            f"<tr>"
            f'<td class="txn-num">{num}</td>'
            f'<td class="txn-date">{_safe(date)}</td>'
            f'<td class="txn-desc">{_safe(desc)}{flag_note}</td>'
            f"<td>{category_badge(cat)}</td>"
            f"<td>{confidence_bar(conf)}</td>"
            f'<td class="{amt_class}">{amt_str}</td>'
            f"</tr>"
        )

    header = (
        "<tr>"
        "<th>#</th><th>Date</th><th>Description</th>"
        "<th>Category</th><th>Confidence</th><th style='text-align:right'>Amount</th>"
        "</tr>"
    )

    table_html = f'<table class="txn-table">{header}{rows_html}</table>'
    return table_html, total_pages


# ══════════════════════════════════════════════════════════════════════════════
# V7 COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def v7_top_privacy_note() -> None:
    v7_render_html(
        """
        <div class="v7-top-note">
            🔒 Your file stays in this session — never stored or shared.
        </div>
        """
    )


def v7_section_header(label: str, helper: str = "") -> None:
    helper_html = (
        f'<div class="v7-section-helper">{_safe(helper)}</div>'
        if helper else ""
    )

    v7_render_html(
        f"""
        <div class="v7-section">
            <div class="v7-section-dot"></div>
            <div class="v7-section-label">{_safe(label)}</div>
        </div>
        {helper_html}
        """
    )


def v7_hero_score_card(
    score: int,
    score_label: str,
    headline: str,
    earned: float,
    spent: float,
    saved: float,
    savings_rate: float,
    sym: str = "$",
) -> None:
    score_color = v7_score_color(score)

    v7_render_html(
        f"""
        <div class="v7-hero">
            <div class="v7-score" style="color:{score_color};">{int(score)}</div>
            <div>
                <div class="v7-score-meta">
                    Money Health Score &nbsp;·&nbsp; {_safe(score_label)}
                </div>
                <div class="v7-score-headline">
                    {_safe(headline)}
                </div>
                <div class="v7-score-summary">
                    Earned <b>{v7_money(earned, sym)}</b>
                    &nbsp;·&nbsp; Spent <b>{v7_money(spent, sym)}</b>
                    &nbsp;·&nbsp; Saved <b>{v7_money(saved, sym, signed=True)}</b>
                    &nbsp;·&nbsp; Savings rate <b>{v7_pct(savings_rate, 1)}</b>
                </div>
            </div>
        </div>
        """
    )


def v7_kpi_card(label: str, value: str, sub: str = "", tone: str = "default") -> str:
    tone_class = {
        "positive": "v7-pos",
        "negative": "v7-neg",
        "warning": "v7-warn",
        "purple": "v7-purple",
    }.get(tone, "")

    return f"""
    <div class="v7-kpi">
        <div class="v7-kpi-label">{_safe(label)}</div>
        <div class="v7-kpi-value {tone_class}">{_safe(value)}</div>
        <div class="v7-kpi-sub">{_safe(sub)}</div>
    </div>
    """


def v7_kpi_grid(
    money_left: float,
    savings_rate: float,
    daily_spend: float,
    review_count: int,
    sym: str = "$",
) -> None:
    left_tone = "positive" if money_left >= 0 else "negative"
    savings_tone = "positive" if savings_rate >= 20 else "warning" if savings_rate >= 0 else "negative"
    review_tone = "warning" if review_count > 0 else "positive"

    html = f"""
    <div class="v7-kpi-grid">
        {v7_kpi_card("Money left over", v7_money(money_left, sym, signed=True), "after spending", left_tone)}
        {v7_kpi_card("% of income saved", v7_pct(savings_rate, 0), "goal: 20%+", savings_tone)}
        {v7_kpi_card("Daily spend avg", v7_money(daily_spend, sym), "across spending days", "default")}
        {v7_kpi_card("Check these", str(int(review_count)), "transactions to double-check", review_tone)}
    </div>
    """

    v7_render_html(html)


def v7_card_html(content: str) -> str:
    return f'<div class="v7-card">{content}</div>'


def v7_spending_split_card(
    fixed_total: float,
    flex_total: float,
    sym: str = "$",
    fixed_hint: str = "Rent, utilities, insurance",
    flex_hint: str = "Groceries, dining, shopping",
) -> None:
    html = f"""
    <div class="v7-card">
        <div class="v7-kpi-label">Your spending split</div>

        <div class="v7-mini-row">
            <div>
                <div class="v7-mini-label">Fixed bills</div>
                <div class="v7-mini-sub">{_safe(fixed_hint)}</div>
            </div>
            <div class="v7-mini-value">{v7_money(fixed_total, sym)}</div>
        </div>

        <div class="v7-mini-row">
            <div>
                <div class="v7-mini-label">Cuttable spend</div>
                <div class="v7-mini-sub">{_safe(flex_hint)}</div>
            </div>
            <div class="v7-mini-value v7-purple">{v7_money(flex_total, sym)}</div>
        </div>
    </div>
    """

    v7_render_html(html)


def v7_budget_check_card(rows: list[dict], sym: str = "$") -> None:
    row_html = ""

    for row in rows:
        label = _safe(row.get("label", "Category"))
        amount = float(row.get("amount", 0) or 0)
        limit = float(row.get("limit", 0) or 0)
        status = _safe(row.get("status", "On track"))

        pct = min(amount / limit, 1.25) if limit > 0 else 0
        width = min(pct * 100, 100)

        fill_class = ""
        status_class = "v7-pos"

        if pct >= 1:
            fill_class = "danger"
            status_class = "v7-neg"
        elif pct >= 0.8:
            fill_class = "warn"
            status_class = "v7-warn"

        row_html += f"""
        <div style="margin-bottom:9px;">
            <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:10px;">
                <div>
                    <div class="v7-mini-label">{label}</div>
                    <div class="v7-mini-sub">{v7_money(amount, sym)} used</div>
                </div>
                <div class="v7-mini-sub {status_class}">{status}</div>
            </div>
            <div class="v7-progress-track">
                <div class="v7-progress-fill {fill_class}" style="width:{width:.0f}%"></div>
            </div>
        </div>
        """

    content = row_html if row_html else '<div class="v7-muted">No budget rows available yet.</div>'

    v7_render_html(
        f"""
        <div class="v7-card">
            <div class="v7-kpi-label">Budget check</div>
            {content}
        </div>
        """
    )


def v7_top_categories_card(rows: list[dict], sym: str = "$") -> None:
    html = ""

    for row in rows:
        category = _safe(row.get("category", "Category"))
        amount = float(row.get("amount", 0) or 0)
        pct = max(0, min(float(row.get("pct", 0) or 0), 1))

        html += f"""
        <div style="margin-bottom:9px;">
            <div style="display:flex;justify-content:space-between;gap:10px;">
                <div class="v7-mini-label">{category}</div>
                <div class="v7-mini-value v7-purple">{v7_money(amount, sym)}</div>
            </div>
            <div class="v7-progress-track">
                <div class="v7-progress-fill" style="width:{pct * 100:.0f}%"></div>
            </div>
        </div>
        """

    content = html if html else '<div class="v7-muted">No spending categories found.</div>'

    v7_render_html(
        f"""
        <div class="v7-card">
            <div class="v7-kpi-label">Top categories</div>
            {content}
        </div>
        """
    )


def v7_big_spends_card(rows: list[dict], sym: str = "$") -> None:
    html = ""

    for row in rows:
        desc = _safe(row.get("description", "Transaction"))
        date = _safe(row.get("date", ""))
        cat = _safe(row.get("category", ""))
        amount = float(row.get("amount", 0) or 0)

        html += f"""
        <div class="v7-mini-row">
            <div>
                <div class="v7-mini-label">{desc}</div>
                <div class="v7-mini-sub">{date} · {cat}</div>
            </div>
            <div class="v7-mini-value v7-neg">{v7_money(amount, sym)}</div>
        </div>
        """

    content = html if html else '<div class="v7-muted">No large expenses found.</div>'

    v7_render_html(
        f"""
        <div class="v7-card">
            <div class="v7-kpi-label">Biggest single spends</div>
            {content}
        </div>
        """
    )


def v7_insight_cards(insights: Iterable[dict]) -> None:
    cards = ""

    for item in insights:
        title = _safe(item.get("title", "Insight"))
        body = _safe(item.get("body", ""))

        cards += f"""
        <div class="v7-insight">
            <div class="v7-insight-title">{title}</div>
            <div class="v7-insight-body">{body}</div>
        </div>
        """

    v7_render_html(
        f"""
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;">
            {cards}
        </div>
        """
    )


def _confidence_width(confidence: str) -> int:
    confidence = str(confidence or "").lower()

    if confidence == "high":
        return 100
    if confidence == "medium":
        return 65
    if confidence == "low":
        return 35

    return 50


def _confidence_color(confidence: str) -> str:
    confidence = str(confidence or "").lower()

    if confidence == "high":
        return "#12B76A"
    if confidence == "medium":
        return "#F79009"
    if confidence == "low":
        return "#F04438"

    return "#D0D5DD"


def v7_transaction_explorer_table(
    df,
    sym: str = "$",
    max_rows: int = 12,
) -> None:
    if df is None or df.empty:
        v7_render_html(
            """
            <div class="v7-card v7-muted">
                No transactions found for this view.
            </div>
            """
        )
        return

    show = df.head(max_rows).copy()

    rows = ""

    for n, (_, row) in enumerate(show.iterrows(), start=1):
        date = row.get("Date", "")

        if hasattr(date, "strftime"):
            date = date.strftime("%d %b %Y")
        else:
            date = str(date)

        desc = _safe(row.get("Description", ""))
        category = _safe(row.get("Category", "Other"))
        confidence = _safe(row.get("Confidence", ""))
        amount = float(row.get("Amount", 0) or 0)

        amount_class = "v7-pos" if amount > 0 else "v7-neg" if amount < 0 else ""

        conf_width = _confidence_width(confidence)
        conf_color = _confidence_color(confidence)

        rows += f"""
        <tr>
            <td>{n}</td>
            <td>{_safe(date)}</td>
            <td>{desc}</td>
            <td><span class="v7-badge">{category}</span></td>
            <td>
                <div class="v7-conf">
                    <div class="v7-conf-fill" style="width:{conf_width}%;background:{conf_color};"></div>
                </div>
            </td>
            <td class="v7-amount {amount_class}">{v7_money(amount, sym, signed=True)}</td>
        </tr>
        """

    more = ""

    if len(df) > max_rows:
        more = f"""
        <div style="font-size:11.5px;color:#98A2B3;text-align:center;padding:8px 0 0;">
            Showing {max_rows} of {len(df)} transactions.
        </div>
        """

    html = f"""
    <div class="v7-card" style="padding:0;overflow:hidden;">
        <table class="v7-txn-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Confidence</th>
                    <th style="text-align:right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        {more}
    </div>
    """

    v7_render_html(html)


def score_band_card(
    score: int,
    score_label: str,
    score_color: str,
    description: str,
    tip: str,
) -> None:
    bgs = {
        "Excellent": "#ECFDF3",
        "Healthy": "#F4EBFF",
        "Needs attention": "#FFFAEB",
        "At risk": "#FEF3F2",
    }

    bg = bgs.get(score_label, "#F9FAFB")

    st.markdown(
        f"""
        <div class="mh-card" style="background:{bg};display:flex;gap:14px;align-items:center;">
            <div style="font-size:36px;font-weight:700;color:{score_color};">{score}</div>
            <div>
                <div style="font-size:14px;font-weight:700;color:{score_color};">
                    {_safe(score_label)} — {_safe(description)}
                </div>
                <div style="font-size:12px;color:#667085;line-height:1.45;">
                    💡 {_safe(tip)}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def review_table(review_df, sym: str = "$") -> None:
    if review_df is None or review_df.empty:
        st.markdown(
            """
            <div class="mh-card" style="padding:20px;text-align:center;color:#98A2B3;font-size:13.5px">
                ✅ No transactions need review — all categorised with high confidence.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    rows_html = ""

    for _, row in review_df.iterrows():
        date_value = row.get("Date", "")
        date_str = date_value.strftime("%d %b %Y") if hasattr(date_value, "strftime") else str(date_value)

        try:
            amt = float(row.get("Amount", 0))
        except Exception:
            amt = 0.0

        amt_str = fmt_money(amt, sym)
        amt_color = COLOR["expense"] if amt < 0 else COLOR["income"]

        desc = str(row.get("Description", ""))[:50]
        flag = str(row.get("Flag", ""))
        conf = str(row.get("Confidence", ""))

        conf_color = _confidence_color(conf)

        rows_html += f"""
        <div style="display:grid;grid-template-columns:90px 1fr 80px 180px 70px;
        gap:8px;align-items:center;padding:9px 0;border-bottom:0.5px solid #F2F4F7;
        font-size:12.5px">
            <div style="color:#98A2B3">{_safe(date_str)}</div>
            <div style="color:#374151;font-weight:500">{_safe(desc)}</div>
            <div style="text-align:right;font-weight:600;color:{amt_color};font-variant-numeric:tabular-nums">
                {amt_str}
            </div>
            <div style="color:#F79009;font-size:11px">{_safe(flag)}</div>
            <div style="color:{conf_color};font-size:11px;font-weight:700">{_safe(conf or "Low")}</div>
        </div>
        """

    header = """
    <div style="display:grid;grid-template-columns:90px 1fr 80px 180px 70px;
    gap:8px;padding:0 0 6px;border-bottom:1px solid #EAECF0;
    font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#98A2B3">
        <div>Date</div>
        <div>Description</div>
        <div style="text-align:right">Amount</div>
        <div>Why flagged</div>
        <div>Confidence</div>
    </div>
    """

    st.markdown(
        f'<div class="mh-card">{header}{rows_html}</div>',
        unsafe_allow_html=True,
    )