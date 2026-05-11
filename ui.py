"""
ui.py  —  Design system & component library
Stage 1 of the Money Health dashboard redesign.

Single source of truth for every visual decision:
  TOKENS      —  colours, spacing, typography (Python constants)
  STYLESHEET  —  one CSS string, injected once at app startup
  FORMATTERS  —  money, percentage, delta badge
  COMPONENTS  —  every HTML block the app ever renders

Rules enforced here:
  - All CSS uses double-quoted attributes (safe inside Python strings)
  - No inline styles scattered across app.py
  - No font weights above 600 (prevents the "stretched" look on Windows)
  - All display numbers go through fmt_money() or fmt_pct() — no raw floats
  - Component functions accept plain Python values, return nothing (call st.markdown)
"""

from __future__ import annotations
import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS  (change here → changes everywhere)
# ══════════════════════════════════════════════════════════════════════════════

# ── Semantic colours ──────────────────────────────────────────────────────────
COLOR = {
    # Meaning-bearing (used only for their semantic role)
    "income":          "#16A34A",   # green  — money coming in
    "income_tint":     "#F0FDF4",   # light green background
    "income_border":   "#BBF7D0",

    "expense":         "#DC2626",   # red    — money going out
    "expense_tint":    "#FEF2F2",
    "expense_border":  "#FECACA",

    "warning":         "#D97706",   # amber  — near budget limit
    "warning_tint":    "#FFFBEB",
    "warning_border":  "#FDE68A",

    "accent":          "#2563EB",   # blue   — primary interactive
    "accent_tint":     "#EEF2FF",
    "accent_border":   "#C7D2FE",

    # Structural
    "page_bg":         "#F8F7F4",   # warm off-white canvas
    "card_bg":         "#FFFFFF",
    "surface":         "#F9FAFB",   # subtle inside-card surface
    "border":          "#E5E7EB",   # default 0.5px border
    "border_light":    "#F3F4F6",   # dividers inside cards

    "verdict_bg":      "#0F172A",   # dark slate for hero banner
    "verdict_score_ok":  "#34D399", # emerald  — excellent / healthy
    "verdict_score_warn":"#FBBF24", # amber    — needs attention
    "verdict_score_bad": "#F87171", # coral    — at risk

    # Text
    "text_primary":    "#111827",
    "text_secondary":  "#6B7280",
    "text_muted":      "#9CA3AF",
    "text_on_dark":    "#F9FAFB",
}

# ── Spacing (px) ─────────────────────────────────────────────────────────────
SP = {
    "xs":  "4px",
    "sm":  "8px",
    "md":  "12px",
    "lg":  "16px",
    "xl":  "24px",
    "2xl": "32px",
    "3xl": "48px",
}

# ── Border radius ─────────────────────────────────────────────────────────────
RADIUS = {
    "sm":   "8px",
    "md":   "12px",
    "lg":   "16px",
    "pill": "99px",
}

# ── Typography ────────────────────────────────────────────────────────────────
# Plus Jakarta Sans: headings, KPI values, scores — friendly, not stretched
# Inter: body, labels, descriptions — most readable screen font
FONT_HEADING = "'Plus Jakarta Sans', sans-serif"
FONT_BODY    = "'Inter', sans-serif"


# ══════════════════════════════════════════════════════════════════════════════
#  STYLESHEET  (injected once via inject_css())
# ══════════════════════════════════════════════════════════════════════════════
# Written entirely with double-quoted attributes so it never conflicts with
# Python string delimiters, regardless of where it appears.
STYLESHEET = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased;
}

[data-testid="stAppViewContainer"] {
    background: #F8F7F4;
}

.block-container {
    padding: 1.4rem 2rem 4rem;
    max-width: 1280px;
}

[data-testid="stSidebar"] {
    background: #0F172A !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * {
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] label {
    color: #64748B !important;
    font-size: 10px !important;
    font-family: 'Inter', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: .07em;
}
[data-testid="stSidebar"] .stButton > button {
    background: #2563EB !important;
    border: none !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    letter-spacing: .01em;
}
[data-testid="stSidebar"] .stDownloadButton > button {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #CBD5E1 !important;
    border-radius: 10px !important;
}

.mh-verdict {
    background: #0F172A;
    border-radius: 18px;
    padding: 28px 36px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 32px;
    flex-wrap: wrap;
}
.mh-verdict-score {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 80px;
    font-weight: 600;
    line-height: 1;
    letter-spacing: -2px;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
}
.mh-verdict-tag {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 6px;
}
.mh-verdict-headline {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 20px;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 6px;
    line-height: 1.3;
}
.mh-verdict-sub {
    font-size: 13px;
    color: #94A3B8;
    line-height: 1.5;
}

.mh-kpi {
    background: #FFFFFF;
    border: 0.5px solid #E5E7EB;
    border-radius: 16px;
    padding: 18px 20px 14px;
    margin-bottom: 14px;
}
.mh-kpi-label {
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .07em;
    color: #9CA3AF;
    margin-bottom: 6px;
}
.mh-kpi-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 28px;
    font-weight: 500;
    line-height: 1.1;
    letter-spacing: -0.3px;
    font-variant-numeric: tabular-nums;
}
.mh-kpi-delta {
    font-size: 12px;
    margin-top: 6px;
    color: #9CA3AF;
}
.mh-kpi-delta .pos { color: #16A34A; font-weight: 500; }
.mh-kpi-delta .neg { color: #DC2626; font-weight: 500; }
.mh-kpi-delta .neu { color: #9CA3AF; }

.mh-section {
    font-size: 12px;
    font-weight: 500;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: #6B7280;
    margin: 32px 0 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.mh-section::after {
    content: "";
    flex: 1;
    height: 0.5px;
    background: #E5E7EB;
}

.mh-card {
    background: #FFFFFF;
    border: 0.5px solid #E5E7EB;
    border-radius: 16px;
    padding: 20px 22px;
    margin-bottom: 14px;
}
.mh-card-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 14px;
}

.mh-spend-item {
    background: #FFFFFF;
    border: 0.5px solid #E5E7EB;
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.mh-spend-name {
    font-size: 14px;
    font-weight: 500;
    color: #374151;
}
.mh-spend-rank {
    font-size: 11.5px;
    color: #9CA3AF;
    margin-top: 2px;
}
.mh-spend-amount {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 18px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
}

.mh-budget-label-row {
    display: flex;
    justify-content: space-between;
    font-size: 12.5px;
    color: #374151;
    font-weight: 500;
    margin-bottom: 4px;
}
.mh-budget-status {
    font-size: 11.5px;
    font-weight: 500;
}
.mh-budget-track {
    background: #F3F4F6;
    border-radius: 99px;
    height: 5px;
    overflow: hidden;
    margin-bottom: 13px;
}
.mh-budget-fill {
    height: 100%;
    border-radius: 99px;
}

.mh-insight {
    background: #F9FAFB;
    border-left: 3px solid #2563EB;
    border-radius: 0 10px 10px 0;
    padding: 12px 16px;
    margin-bottom: 9px;
    font-size: 13.5px;
    color: #374151;
    line-height: 1.65;
}

.mh-action {
    background: #FFFFFF;
    border: 0.5px solid #E5E7EB;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}
.mh-action-num {
    min-width: 22px;
    height: 22px;
    background: #EEF2FF;
    color: #4F46E5;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 600;
    flex-shrink: 0;
    margin-top: 1px;
}
.mh-action-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 13.5px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 3px;
}
.mh-action-desc {
    font-size: 12.5px;
    color: #6B7280;
    line-height: 1.5;
}

.mh-txn {
    background: #FFFFFF;
    border: 0.5px solid #E5E7EB;
    border-radius: 12px;
    padding: 13px 16px;
    margin-bottom: 8px;
}
.mh-txn-amount {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 22px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: #DC2626;
}
.mh-txn-desc {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    margin: 3px 0 2px;
}
.mh-txn-meta {
    font-size: 11px;
    color: #9CA3AF;
}

.mh-sub-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 0.5px solid #F3F4F6;
}
.mh-sub-row:last-child { border-bottom: none; }
.mh-sub-name {
    font-size: 13.5px;
    font-weight: 500;
    color: #374151;
}
.mh-sub-amount {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    font-weight: 500;
    font-variant-numeric: tabular-nums;
    color: #DC2626;
}

.mh-ai-panel {
    background: #F5F3FF;
    border: 0.5px solid #DDD6FE;
    border-radius: 14px;
    padding: 20px 22px;
}
.mh-ai-tag {
    background: #EDE9FE;
    color: #5B21B6;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 99px;
    display: inline-block;
    margin-bottom: 12px;
}
.mh-ai-body {
    font-size: 14px;
    color: #1F2937;
    line-height: 1.75;
    white-space: pre-line;
}

.mh-privacy {
    background: #EFF6FF;
    border: 0.5px solid #BFDBFE;
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 20px;
    font-size: 12px;
    color: #1D4ED8;
    line-height: 1.5;
}

.mh-parse-info {
    background: #F9FAFB;
    border: 0.5px solid #E5E7EB;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 12px;
    color: #6B7280;
    line-height: 1.65;
    margin-bottom: 18px;
}
.mh-badge-ai {
    display: inline-block;
    background: #EDE9FE;
    color: #5B21B6;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 99px;
    margin-left: 6px;
}
.mh-badge-kw {
    display: inline-block;
    background: #FEF9C3;
    color: #854D0E;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 99px;
    margin-left: 6px;
}

.mh-ob-card {
    background: #FFFFFF;
    border: 0.5px solid #E5E7EB;
    border-radius: 18px;
    padding: 30px 22px;
    text-align: center;
}
.mh-ob-icon {
    font-size: 32px;
    margin-bottom: 12px;
    line-height: 1;
}
.mh-ob-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 7px;
}
.mh-ob-desc {
    font-size: 13px;
    color: #9CA3AF;
    line-height: 1.6;
}

.mh-disclaimer {
    background: #F3F4F6;
    border-radius: 10px;
    padding: 12px 18px;
    font-size: 11px;
    color: #9CA3AF;
    text-align: center;
    margin-top: 28px;
    line-height: 1.6;
}

[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #D1D5DB !important;
    border-radius: 12px !important;
}
div[data-testid="stHorizontalBlock"] { gap: 14px; }
</style>
"""


def inject_css() -> None:
    """Call once at the top of app.py — injects the full design system."""
    st.markdown(STYLESHEET, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTERS
#  All numbers that reach the screen must pass through one of these.
# ══════════════════════════════════════════════════════════════════════════════

def fmt_money(value: float, sym: str = "$", signed: bool = False) -> str:
    """
    Format a monetary amount for display.
    Drops cents for values >= 1,000 to keep KPI cards compact.

    Examples:
        fmt_money(16896.94)            → "$16,897"
        fmt_money(238.35)              → "$238.35"
        fmt_money(1700, signed=True)   → "+$1,700"
        fmt_money(-500, signed=True)   → "-$500.00"
    """
    abs_v = abs(value)
    body  = f"{abs_v:,.0f}" if abs_v >= 1_000 else f"{abs_v:,.2f}"
    if signed:
        prefix = "+" if value >= 0 else "-"
        return f"{prefix}{sym}{body}"
    return f"{sym}{body}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a percentage. fmt_pct(43.5) → '43.5%'"""
    return f"{value:.{decimals}f}%"


def delta_badge(current: float, previous: float, invert: bool = False) -> str:
    """
    Return an HTML <span> showing percentage change vs previous period.
    invert=True: a decrease is shown as green (e.g. expenses going down is good).
    """
    if previous == 0:
        return '<span class="neu">—</span>'
    pct   = (current - previous) / abs(previous) * 100
    up    = pct > 0
    good  = up if not invert else not up
    cls   = "pos" if good else "neg"
    arrow = "▲" if up else "▼"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


def _score_color(score: int) -> str:
    """Map health score to its display colour."""
    if score >= 80: return COLOR["verdict_score_ok"]
    if score >= 65: return COLOR["verdict_score_ok"]
    if score >= 45: return COLOR["verdict_score_warn"]
    return COLOR["verdict_score_bad"]


def _spend_color(actual_pct: float, rec_pct: int) -> str:
    """Traffic-light colour for a budget category."""
    if actual_pct > rec_pct:            return COLOR["expense"]
    if actual_pct > rec_pct * 0.85:    return COLOR["warning"]
    return COLOR["income"]


def _spend_status_text(actual_pct: float, rec_pct: int) -> str:
    if actual_pct > rec_pct:            return "Over budget"
    if actual_pct > rec_pct * 0.85:    return "Almost there"
    return "On track"


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENTS
#  Each function renders exactly one UI block using st.markdown.
#  Arguments are plain Python values — no HTML leaks into app.py.
# ══════════════════════════════════════════════════════════════════════════════

def section_header(label: str) -> None:
    """Uppercase section divider with a horizontal rule."""
    st.markdown(f'<div class="mh-section">{label}</div>', unsafe_allow_html=True)


# ── Verdict banner ────────────────────────────────────────────────────────────
def verdict_banner(
    score:       int,
    score_label: str,
    headline:    str,
    sub_html:    str,          # pre-formatted "Earned $X · Spent $Y · Saved $Z"
) -> None:
    color = _score_color(score)
    st.markdown(
        f'<div class="mh-verdict">'
        f'  <div class="mh-verdict-score" style="color:{color}">{score}</div>'
        f'  <div>'
        f'    <div class="mh-verdict-tag">Money health score &nbsp;&middot;&nbsp; {score_label}</div>'
        f'    <div class="mh-verdict-headline">{headline}</div>'
        f'    <div class="mh-verdict-sub">{sub_html}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── KPI card ──────────────────────────────────────────────────────────────────
def kpi_card(
    label:         str,
    value:         str,          # pre-formatted by fmt_money / fmt_pct
    value_color:   str,
    delta_html:    str,          # output of delta_badge()
    delta_context: str = "",     # e.g. "vs last month"
) -> None:
    context = f' <span class="neu">{delta_context}</span>' if delta_context else ""
    st.markdown(
        f'<div class="mh-kpi">'
        f'  <div class="mh-kpi-label">{label}</div>'
        f'  <div class="mh-kpi-value" style="color:{value_color}">{value}</div>'
        f'  <div class="mh-kpi-delta">{delta_html}{context}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Card wrappers ─────────────────────────────────────────────────────────────
def card_start(title: str = "") -> None:
    title_html = f'<div class="mh-card-title">{title}</div>' if title else ""
    st.markdown(f'<div class="mh-card">{title_html}', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


# ── Top spending items ────────────────────────────────────────────────────────
def spend_item(
    name:       str,
    rank_label: str,      # e.g. "Biggest cost", "2nd largest"
    amount:     float,
    sym:        str = "$",
    color:      str = "",
) -> None:
    c = color or COLOR["expense"]
    st.markdown(
        f'<div class="mh-spend-item">'
        f'  <div>'
        f'    <div class="mh-spend-name">{name}</div>'
        f'    <div class="mh-spend-rank">{rank_label}</div>'
        f'  </div>'
        f'  <div class="mh-spend-amount" style="color:{c}">{fmt_money(amount, sym)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Budget bar ────────────────────────────────────────────────────────────────
def budget_bar(
    category:   str,
    amount_str: str,    # pre-formatted display amount e.g. "$1,200"
    actual_pct: float,  # pre-computed percentage of income
    rec_pct:    int,    # recommended % from BUDGET_GUIDE
) -> None:
    bar_w  = min(actual_pct / rec_pct * 100, 108) if rec_pct else 0.0
    color  = _spend_color(actual_pct, rec_pct)
    status = _spend_status_text(actual_pct, rec_pct)

    st.markdown(
        f'<div>'
        f'  <div class="mh-budget-label-row">'
        f'    <span>{category} <span style="color:#9CA3AF;font-weight:400;font-size:11px">{amount_str}</span></span>'
        f'    <span class="mh-budget-status" style="color:{color}">{status}</span>'
        f'  </div>'
        f'  <div class="mh-budget-track">'
        f'    <div class="mh-budget-fill" style="width:{bar_w:.1f}%;background:{color}"></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Insight card ──────────────────────────────────────────────────────────────
def insight_card(html_body: str) -> None:
    """Blue-left-border card. html_body may contain <b> tags."""
    st.markdown(
        f'<div class="mh-insight">{html_body}</div>',
        unsafe_allow_html=True,
    )


# ── Action card ───────────────────────────────────────────────────────────────
def action_card(num: int, emoji: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="mh-action">'
        f'  <div class="mh-action-num">{num}</div>'
        f'  <div>'
        f'    <div class="mh-action-title">{emoji} {title}</div>'
        f'    <div class="mh-action-desc">{description}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Top transaction card ──────────────────────────────────────────────────────
def transaction_card(
    amount:      str,   # pre-formatted e.g. "$1,200"
    description: str,
    date:        str,   # pre-formatted e.g. "14 Jan 2026"
    category:    str,
) -> None:
    st.markdown(
        f'<div class="mh-txn">'
        f'  <div class="mh-txn-amount">{amount}</div>'
        f'  <div class="mh-txn-desc">{description}</div>'
        f'  <div class="mh-txn-meta">{date} &nbsp;&middot;&nbsp; {category}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Subscription list ─────────────────────────────────────────────────────────
def subscription_list(
    rows_html:  str,   # pre-built HTML rows from app.py
    total_str:  str,   # pre-formatted total e.g. "$89.00"
) -> None:
    total_row = (
        f'<div style="display:flex;justify-content:space-between;'
        f'padding:10px 0 2px;font-size:12.5px;color:{COLOR["text_muted"]};font-weight:500">'
        f'<span>Total</span>'
        f'<span style="font-family:\'Plus Jakarta Sans\',sans-serif;color:{COLOR["expense"]};'
        f'font-size:15px;font-weight:500;font-variant-numeric:tabular-nums">'
        f'{total_str}</span>'
        f'</div>'
    )
    st.markdown(
        f'<div class="mh-card" style="padding:14px 18px">{rows_html}{total_row}</div>',
        unsafe_allow_html=True,
    )
def ai_panel(text: str) -> None:
    st.markdown(
        f'<div class="mh-ai-panel">'
        f'<span class="mh-ai-tag">AI insights</span>'
        f'<div class="mh-ai-body">{text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def ai_empty_state() -> None:
    st.markdown(
        f'<div style="padding:28px;text-align:center;color:{COLOR["text_muted"]};font-size:14px">'
        f'Add your Anthropic API key in the sidebar and click <b>Generate insights</b>.'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Parse info bar ────────────────────────────────────────────────────────────
def parse_info_bar(
    col_map:  dict[str, str],
    method:   str,
    currency: str,
    warnings: list[str],
) -> None:
    badge = (
        f'<span class="mh-badge-ai">AI detected</span>'
        if method == "ai" else
        f'<span class="mh-badge-kw">keyword rules</span>'
    )
    html = (
        f'Columns detected {badge}: '
        f'Date &rarr; <code>{col_map.get("date", "?")}</code> &nbsp;&middot;&nbsp; '
        f'Description &rarr; <code>{col_map.get("description", "?")}</code> &nbsp;&middot;&nbsp; '
        f'Amount &rarr; <code>{col_map.get("amount", "?")}</code>'
    )
    if currency and currency != "$":
        html += f' &nbsp;&middot;&nbsp; Currency: <b>{currency}</b>'
    if warnings:
        html += "<br>" + " &nbsp;|&nbsp; ".join(warnings)
    st.markdown(f'<div class="mh-parse-info">{html}</div>', unsafe_allow_html=True)


# ── Privacy notice ────────────────────────────────────────────────────────────
def privacy_notice() -> None:
    st.markdown(
        '<div class="mh-privacy">'
        "Your file is processed only in this browser session — "
        "never stored or shared. For personal tracking only, not financial advice."
        '</div>',
        unsafe_allow_html=True,
    )


# ── Onboarding (pre-upload) ───────────────────────────────────────────────────
def onboarding_tiles() -> None:
    tiles = [
        ("🌍", "Works with any bank",
         "Japanese, Arabic, German, Korean — any language, any column format, any currency."),
        ("🧠", "Smart detection",
         "Reads your CSV header and automatically finds the date, description, and amount."),
        ("⚡", "Plain-English results",
         "See where your money went in seconds. No finance background needed."),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, tiles):
        with col:
            st.markdown(
                f'<div class="mh-ob-card">'
                f'<div class="mh-ob-icon">{icon}</div>'
                f'<div class="mh-ob-title">{title}</div>'
                f'<div class="mh-ob-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Footer disclaimer ─────────────────────────────────────────────────────────
def disclaimer() -> None:
    st.markdown(
        '<div class="mh-disclaimer">'
        "Money Health is for personal education and spending awareness only. "
        "It does not constitute financial, tax, investment, or credit advice. "
        "Consult a licensed financial adviser for professional guidance."
        '</div>',
        unsafe_allow_html=True,
    )
