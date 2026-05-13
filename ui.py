"""
ui.py  —  Design system & component library
Professional redesign: clean, minimal, business-ready.

Design decisions:
  FONT      Inter only — one typeface, two weights (400/600), strict hierarchy
  COLOUR    5 semantic tokens (navy, blue, emerald, rose, amber) + slate neutrals
  CARDS     1px solid border, no shadow — modern flat approach (Notion/Linear/Stripe)
  SECTIONS  Blue 4px dot + small uppercase label — clear but not heavy
  NUMBERS   font-variant-numeric: tabular-nums everywhere — professional alignment
  SPACING   8px base unit — consistent rhythm throughout
"""

from __future__ import annotations
import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
COLOR = {
    # Semantic — meaning-bearing
    "navy":        "#1A2332",   # softer charcoal — header, verdict bg
    "accent":      "#6941C6",   # soft purple — distinctive, calm, non-corporate
    "income":      "#12B76A",   # softer green — income, positive, on track
    "expense":     "#F04438",   # soft rose — expenses, over budget
    "warning":     "#F79009",   # warm amber — near limit, caution

    # Structural
    "page_bg":     "#F7F8FA",   # near-white, easy on the eyes
    "card_bg":     "#FFFFFF",
    "surface":     "#F9FAFB",   # slightly off-white nested surfaces
    "border":      "#EAECF0",   # very subtle card borders
    "border_sub":  "#F2F4F7",   # intra-card dividers

    # Text
    "text_primary":   "#101828",   # near-black
    "text_secondary": "#475467",   # medium grey
    "text_muted":     "#98A2B3",   # muted grey
    "text_on_dark":   "#F9FAFB",   # for dark backgrounds
}


# ══════════════════════════════════════════════════════════════════════════════
#  STYLESHEET
#  One CSS block injected once. Every component uses these classes.
#  No inline styles outside this file — all visual decisions live here.
# ══════════════════════════════════════════════════════════════════════════════
STYLESHEET = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

[data-testid="stAppViewContainer"] {
    background: #F7F8FA;
}

.block-container {
    padding: 1.5rem 2.2rem 4rem;
    max-width: 1320px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1A2332 !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}
[data-testid="stSidebar"] label {
    color: #475569 !important;
    font-size: 10px !important;
    font-family: 'Inter', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: .07em;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #6941C6 !important;
    border: none !important;
    color: #fff !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1D4ED8 !important;
}
[data-testid="stSidebar"] .stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #1E293B !important;
    color: #64748B !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] .stDownloadButton > button:hover {
    border-color: #334155 !important;
    color: #94A3B8 !important;
}

/* ── Verdict banner ── */
.mh-verdict {
    background: #0F172A;
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 32px;
    flex-wrap: wrap;
}
.mh-verdict-score {
    font-family: 'Inter', sans-serif;
    font-size: 72px;
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
    color: #334155;
    margin-bottom: 7px;
}
.mh-verdict-headline {
    font-size: 18px;
    font-weight: 600;
    color: #F1F5F9;
    margin-bottom: 6px;
    line-height: 1.35;
}
.mh-verdict-sub {
    font-size: 13px;
    color: #475569;
    line-height: 1.5;
}
.mh-verdict-sub b {
    color: #64748B;
    font-weight: 500;
}

/* ── KPI cards ── */
.mh-kpi {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 14px 18px 12px;
    margin-bottom: 14px;
}
.mh-kpi-label {
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .07em;
    color: #94A3B8;
    margin-bottom: 8px;
}
.mh-kpi-value {
    font-size: 24px;
    font-weight: 500;
    line-height: 1;
    letter-spacing: -0.5px;
    font-variant-numeric: tabular-nums;
}
.mh-kpi-delta {
    font-size: 12px;
    margin-top: 7px;
    color: #94A3B8;
}
.mh-kpi-delta .pos { color: #059669; font-weight: 500; }
.mh-kpi-delta .neg { color: #E11D48; font-weight: 500; }
.mh-kpi-delta .neu { color: #94A3B8; }

/* ── Section header ── */
.mh-section {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 18px 0 10px;
}
.mh-section-dot {
    width: 4px;
    height: 16px;
    background: #6941C6;
    border-radius: 2px;
    flex-shrink: 0;
}
.mh-section-text {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: #64748B;
}

/* ── Card ── */
.mh-card {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.mh-card-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #64748B;
    margin-bottom: 14px;
}

/* ── Insight card ── */
.mh-insight {
    border-left: 2px solid #6941C6;
    border-radius: 0 6px 6px 0;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 13.5px;
    color: #374151;
    line-height: 1.65;
    background: #F8FAFC;
}

/* ── Action card ── */
.mh-action {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    display: flex;
    gap: 10px;
    align-items: flex-start;
}
.mh-action-num {
    min-width: 20px;
    height: 20px;
    background: #F4EBFF;
    color: #6941C6;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 600;
    flex-shrink: 0;
    margin-top: 1px;
    font-family: 'Inter', sans-serif;
}
.mh-action-title {
    font-size: 13px;
    font-weight: 600;
    color: #0F172A;
    margin-bottom: 3px;
}
.mh-action-desc {
    font-size: 12.5px;
    color: #64748B;
    line-height: 1.55;
}

/* ── Top transaction card ── */
.mh-txn {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.mh-txn-amount {
    font-size: 20px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: #E11D48;
    letter-spacing: -0.3px;
}
.mh-txn-desc {
    font-size: 13px;
    font-weight: 500;
    color: #374151;
    margin: 3px 0 2px;
}
.mh-txn-meta {
    font-size: 11px;
    color: #94A3B8;
}

/* ── Budget bars ── */
.mh-budget-label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12.5px;
    color: #374151;
    font-weight: 500;
    margin-bottom: 5px;
}
.mh-budget-status {
    font-size: 11px;
    font-weight: 500;
}
.mh-budget-track {
    background: #F1F5F9;
    border-radius: 3px;
    height: 4px;
    overflow: hidden;
    margin-bottom: 13px;
}
.mh-budget-fill {
    height: 100%;
    border-radius: 3px;
}

/* ── Subscription list ── */
.mh-sub-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #F1F5F9;
}
.mh-sub-row:last-child { border-bottom: none; }
.mh-sub-name {
    font-size: 13px;
    font-weight: 400;
    color: #374151;
}
.mh-sub-amount {
    font-size: 14px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    color: #E11D48;
}

/* ── AI panel ── */
.mh-ai-panel {
    background: #F8FAFC;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 18px 20px;
}
.mh-ai-tag {
    background: #F4EBFF;
    color: #6941C6;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 12px;
}
.mh-ai-body {
    font-size: 13.5px;
    color: #374151;
    line-height: 1.75;
    white-space: pre-line;
}

/* ── Parse info bar ── */
.mh-parse-info {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 12px;
    color: #64748B;
    line-height: 1.6;
    margin-bottom: 18px;
}
.mh-badge-ai {
    display: inline-block;
    background: #F4EBFF;
    color: #6941C6;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
    text-transform: uppercase;
    letter-spacing: .04em;
}
.mh-badge-kw {
    display: inline-block;
    background: #FEF9C3;
    color: #854D0E;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
    text-transform: uppercase;
    letter-spacing: .04em;
}

/* ── Privacy notice ── */
.mh-privacy {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 9px 14px;
    margin-bottom: 18px;
    font-size: 12px;
    color: #64748B;
    line-height: 1.5;
}

/* ── Onboarding tiles ── */
.mh-ob-card {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 28px 22px;
    text-align: center;
}
.mh-ob-icon {
    font-size: 28px;
    margin-bottom: 12px;
    line-height: 1;
}
.mh-ob-title {
    font-size: 14px;
    font-weight: 600;
    color: #0F172A;
    margin-bottom: 7px;
}
.mh-ob-desc {
    font-size: 12.5px;
    color: #64748B;
    line-height: 1.6;
}

/* ── Disclaimer ── */
.mh-disclaimer {
    background: #F8FAFC;
    border-radius: 8px;
    padding: 11px 16px;
    font-size: 11px;
    color: #94A3B8;
    text-align: center;
    margin-top: 24px;
    line-height: 1.6;
}



/* ── Score band card ── */
.mh-score-band {
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 12px;
    display: flex;
    align-items: flex-start;
    gap: 14px;
}
.mh-score-band-num {
    font-size: 40px;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
}
.mh-score-band-title {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 4px;
}
.mh-score-band-desc {
    font-size: 13px;
    line-height: 1.6;
    opacity: .85;
}

/* ── Review badge ── */
.mh-review-badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 99px;
    white-space: nowrap;
}
.mh-conf-high  { background: #ECFDF3; color: #027A48; }
.mh-conf-med   { background: #FFFAEB; color: #B54708; }
.mh-conf-low   { background: #FEF3F2; color: #B42318; }
.mh-flag-badge { background: #F4EBFF; color: #5925DC; border: 0.5px solid #D9D6FE; }

/* ── Top filter bar ── */
.mh-filter-bar {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}
.mh-filter-label {
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .07em;
    color: #98A2B3;
    margin-right: 4px;
}

/* ── Score breakdown tooltip ── */
.mh-score-detail {
    background: #F9FAFB;
    border: 1px solid #EAECF0;
    border-radius: 8px;
    padding: 12px 14px;
    margin-top: 8px;
    font-size: 12px;
    color: #475467;
    line-height: 1.7;
}
.mh-score-bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 5px;
}
.mh-score-bar-label {
    min-width: 130px;
    font-size: 12px;
    color: #475467;
}
.mh-score-bar-track {
    flex: 1;
    background: #EAECF0;
    border-radius: 99px;
    height: 6px;
    overflow: hidden;
}
.mh-score-bar-fill {
    height: 100%;
    border-radius: 99px;
    background: #6941C6;
}
.mh-score-bar-pts {
    font-size: 11px;
    color: #98A2B3;
    min-width: 50px;
    text-align: right;
}

/* ── Flag badges ── */
.mh-flag {
    display: inline-block;
    background: #FFFAEB;
    border: 0.5px solid #FEC84B;
    color: #B54708;
    font-size: 10px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 99px;
    margin: 2px;
}

/* ── Streamlit overrides ── */
[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #CBD5E1 !important;
    border-radius: 10px !important;
}
div[data-testid="stHorizontalBlock"] { gap: 14px; }

[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] table { font-family: 'Inter', sans-serif !important; font-size: 13px !important; }
[data-testid="stDataFrame"] th { background: #F8FAFC !important; color: #64748B !important; font-weight: 500 !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: .05em !important; }
[data-testid="stDataFrame"] tr:nth-child(even) td { background: #F8FAFC; }

[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
</style>
"""


def inject_css() -> None:
    """Inject the design system stylesheet. Call once at app startup."""
    st.markdown(STYLESHEET, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt_money(value: float, sym: str = "$", signed: bool = False) -> str:
    """
    Format money for display. Drops cents for values >= $1,000.
    fmt_money(16896.94)           -> "$16,897"
    fmt_money(238.35)             -> "$238.35"
    fmt_money(1700, signed=True)  -> "+$1,700"
    """
    abs_v = abs(value)
    body  = f"{abs_v:,.0f}" if abs_v >= 1_000 else f"{abs_v:,.2f}"
    if signed:
        return f"+{sym}{body}" if value >= 0 else f"-{sym}{body}"
    return f"{sym}{body}"


def fmt_money_kpi(value: float, sym: str = "$", signed: bool = False) -> str:
    """
    Abbreviated money formatter for KPI cards.
    Prevents long numbers from overflowing the card layout.
    $1,874,413,489 → +$1.87B
    $104,677       → $104.7K
    $16,897        → $16,897
    $238.35        → $238.35
    """
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        body = f"{abs_v/1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        body = f"{abs_v/1_000_000:.2f}M"
    elif abs_v >= 100_000:
        body = f"{abs_v/1_000:.1f}K"
    elif abs_v >= 1_000:
        body = f"{abs_v:,.0f}"
    else:
        body = f"{abs_v:,.2f}"
    if signed:
        return f"+{sym}{body}" if value >= 0 else f"-{sym}{body}"
    return f"{sym}{body}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def delta_badge(current: float, previous: float, invert: bool = False) -> str:
    """HTML span showing % change. invert=True means a decrease is good."""
    if previous == 0:
        return '<span class="neu">—</span>'
    pct   = (current - previous) / abs(previous) * 100
    up    = pct > 0
    good  = up if not invert else not up
    cls   = "pos" if good else "neg"
    arrow = "▲" if up else "▼"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


def _score_color(score: int) -> str:
    """Verdict banner score number colour."""
    if score >= 80: return "#34D399"   # emerald-400 — great on dark bg
    if score >= 65: return "#60A5FA"   # blue-400
    if score >= 45: return "#FBBF24"   # amber-400
    return "#F87171"                   # red-400


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def section_header(label: str, helper: str = "") -> None:
    """Blue dot + uppercase label. Optional plain-English helper sentence."""
    helper_html = (
        f'<div style="font-size:13px;color:{COLOR["text_muted"]};margin:-4px 0 10px;font-weight:400">'
        f'{helper}</div>'
    ) if helper else ""
    st.markdown(
        f'<div class="mh-section">'
        f'<div class="mh-section-dot"></div>'
        f'<div class="mh-section-text">{label}</div>'
        f'</div>{helper_html}',
        unsafe_allow_html=True,
    )


def verdict_banner(
    score:        int,
    score_label:  str,
    headline:     str,
    sub_html:     str,
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


def kpi_card(
    label:         str,
    value:         str,
    value_color:   str,
    delta_html:    str,
    delta_context: str = "",
) -> None:
    ctx = f' <span class="neu">{delta_context}</span>' if delta_context else ""
    st.markdown(
        f'<div class="mh-kpi">'
        f'  <div class="mh-kpi-label">{label}</div>'
        f'  <div class="mh-kpi-value" style="color:{value_color}">{value}</div>'
        f'  <div class="mh-kpi-delta">{delta_html}{ctx}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def card_start(title: str = "") -> None:
    title_html = f'<div class="mh-card-title">{title}</div>' if title else ""
    st.markdown(f'<div class="mh-card">{title_html}', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def spend_item(
    name:       str,
    rank_label: str,
    amount:     float,
    sym:        str = "$",
    color:      str = "",
) -> None:
    c = color or COLOR["expense"]
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:11px 0;border-bottom:1px solid #F1F5F9">'
        f'  <div>'
        f'    <div style="font-size:13.5px;font-weight:400;color:#374151">{name}</div>'
        f'    <div style="font-size:11px;color:#94A3B8;margin-top:1px">{rank_label}</div>'
        f'  </div>'
        f'  <div style="font-size:17px;font-weight:600;font-variant-numeric:tabular-nums;'
        f'color:{c};letter-spacing:-0.3px">{fmt_money(amount, sym)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def budget_bar(
    category:   str,
    amount_str: str,
    actual_pct: float,
    rec_pct:    int,
) -> None:
    bar_w = min(actual_pct / rec_pct * 100, 108) if rec_pct else 0.0
    if actual_pct > rec_pct:
        color, status, status_color = "#E11D48", "Over budget", "#E11D48"
    elif actual_pct > rec_pct * 0.85:
        color, status, status_color = "#D97706", "Near limit", "#D97706"
    else:
        color, status, status_color = "#059669", "On track", "#059669"
    st.markdown(
        f'<div style="margin-bottom:13px">'
        f'  <div class="mh-budget-label-row">'
        f'    <span>{category} '
        f'<span style="color:#94A3B8;font-weight:400;font-size:11.5px">{amount_str}</span>'
        f'    </span>'
        f'    <span class="mh-budget-status" style="color:{status_color}">{status}</span>'
        f'  </div>'
        f'  <div class="mh-budget-track">'
        f'    <div class="mh-budget-fill" style="width:{bar_w:.1f}%;background:{color}"></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def insight_card(html_body: str) -> None:
    st.markdown(f'<div class="mh-insight">{html_body}</div>', unsafe_allow_html=True)


def action_card(num: int, emoji: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="mh-action">'
        f'  <div class="mh-action-num">{num}</div>'
        f'  <div>'
        f'    <div class="mh-action-title">{title}</div>'
        f'    <div class="mh-action-desc">{description}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def transaction_card(
    amount:      str,
    description: str,
    date:        str,
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


def subscription_list(rows_html: str, total_str: str) -> None:
    total_row = (
        f'<div style="display:flex;justify-content:space-between;padding:10px 0 2px;'
        f'font-size:12.5px;color:#94A3B8;font-weight:500;border-top:1px solid #F1F5F9;'
        f'margin-top:2px">'
        f'<span>Total</span>'
        f'<span style="font-size:15px;font-weight:600;font-variant-numeric:tabular-nums;'
        f'color:#E11D48">{total_str}</span>'
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
        f'<div style="padding:28px;text-align:center;color:#94A3B8;font-size:13.5px">'
        f'Enter your Anthropic API key in the sidebar and click '
        f'<strong>Generate insights</strong> for personalised coaching.'
        f'</div>',
        unsafe_allow_html=True,
    )


def parse_info_bar(
    col_map:  dict[str, str],
    method:   str,
    currency: str,
    warnings: list[str],
) -> None:
    badge = (
        f'<span class="mh-badge-ai">AI</span>'
        if method == "ai" else
        f'<span class="mh-badge-kw">keyword</span>'
    )
    html = (
        f'Columns detected {badge}: '
        f'Date &rarr; <code>{col_map.get("date","?")}</code> &nbsp;&middot;&nbsp; '
        f'Description &rarr; <code>{col_map.get("description","?")}</code> &nbsp;&middot;&nbsp; '
        f'Amount &rarr; <code>{col_map.get("amount","?")}</code>'
    )
    if currency and currency != "$":
        html += f' &nbsp;&middot;&nbsp; Currency: <strong>{currency}</strong>'
    if warnings:
        html += "<br>" + " &nbsp;|&nbsp; ".join(warnings)
    st.markdown(f'<div class="mh-parse-info">{html}</div>', unsafe_allow_html=True)


def privacy_notice() -> None:
    st.markdown(
        '<div class="mh-privacy">'
        "Your file is processed only in this session — never stored or shared. "
        "For personal tracking only, not financial advice."
        '</div>',
        unsafe_allow_html=True,
    )


def onboarding_tiles() -> None:
    tiles = [
        ("🌍", "Works with any bank",
         "Any language, any column format, any currency. CSV from any bank worldwide."),
        ("🧠", "Smart column detection",
         "Automatically identifies date, description, and amount columns."),
        ("⚡", "Plain-English results",
         "Understand your finances in seconds — no background needed."),
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


def disclaimer() -> None:
    st.markdown(
        '<div class="mh-disclaimer">'
        "Money Health is for personal education and spending awareness only. "
        "It does not constitute financial, tax, investment, or credit advice."
        '</div>',
        unsafe_allow_html=True,
    )


def score_band_card(
    score: int,
    score_label: str,
    score_color: str,
    description: str,
    tip: str,
) -> None:
    """Plain-English explanation of what the score means and how to improve it."""
    bgs = {
        "Excellent": "#ECFDF3", "Healthy": "#F4EBFF",
        "Needs attention": "#FFFAEB", "At risk": "#FEF3F2",
    }
    bg = bgs.get(score_label, "#F9FAFB")
    st.markdown(
        f'<div class="mh-score-band" style="background:{bg}">'
        f'  <div class="mh-score-band-num" style="color:{score_color}">{score}</div>'
        f'  <div>'
        f'    <div class="mh-score-band-title" style="color:{score_color}">{score_label} — {description}</div>'
        f'    <div class="mh-score-band-desc">💡 {tip}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def review_table(review_df: "pd.DataFrame", sym: str = "$") -> None:
    """
    Styled transaction review table with plain-English reasons and badges.
    Shows: date, description, amount, flag reason, confidence.
    """
    if review_df.empty:
        st.markdown(
            '<div style="padding:20px;text-align:center;color:#98A2B3;font-size:13.5px">'
            '✅ No transactions need review — all categorised with high confidence.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for _, row in review_df.iterrows():
        date_str = row["Date"].strftime("%d %b %Y") if hasattr(row["Date"], "strftime") else str(row["Date"])
        amt      = float(row["Amount"])
        amt_str  = fmt_money(amt, sym)
        amt_color = COLOR["expense"] if amt < 0 else COLOR["income"]
        desc     = str(row.get("Description", ""))[:50]
        cat      = str(row.get("Category", "Unknown"))
        flag     = str(row.get("Flag", ""))
        conf     = str(row.get("Confidence", ""))

        conf_cls = {"High": "mh-conf-high", "Medium": "mh-conf-med", "Low": "mh-conf-low"}.get(conf, "mh-conf-low")
        conf_html = f'<span class="mh-review-badge {conf_cls}">{conf or "Low"}</span>'

        flag_badges = ""
        if flag:
            for f in flag.split(" | ")[:2]:
                flag_badges += f'<span class="mh-review-badge mh-flag-badge">{f}</span> '

        rows_html += (
            f'<div style="display:grid;grid-template-columns:90px 1fr 80px 180px 70px;'
            f'gap:8px;align-items:center;padding:9px 0;border-bottom:0.5px solid #F2F4F7;'
            f'font-size:12.5px">'
            f'<div style="color:#98A2B3">{date_str}</div>'
            f'<div style="color:#374151;font-weight:500">{desc}</div>'
            f'<div style="text-align:right;font-weight:600;color:{amt_color};font-variant-numeric:tabular-nums">{amt_str}</div>'
            f'<div>{flag_badges}</div>'
            f'<div>{conf_html}</div>'
            f'</div>'
        )

    # Header row
    header = (
        '<div style="display:grid;grid-template-columns:90px 1fr 80px 180px 70px;'
        'gap:8px;padding:0 0 6px;border-bottom:1px solid #EAECF0;'
        'font-size:10px;font-weight:500;text-transform:uppercase;letter-spacing:.06em;color:#98A2B3">'
        '<div>Date</div><div>Description</div><div style="text-align:right">Amount</div>'
        '<div>Why flagged</div><div>Confidence</div></div>'
    )
    st.markdown(
        f'<div class="mh-card">{header}{rows_html}</div>',
        unsafe_allow_html=True,
    )
