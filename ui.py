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

/* ════════════════════════════════════════════════════════════════
   GLOBAL RESET — kill Streamlit default spacing completely
   ════════════════════════════════════════════════════════════════ */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

/* Main container — tight padding, capped width */
.stMainBlockContainer, .block-container {
    padding: 0.5rem 1.75rem 2rem !important;
    max-width: 1320px !important;
}

/* Kill gap between ALL block-level Streamlit elements */
[data-testid="stVerticalBlock"] {
    gap: 0.3rem !important;
}

/* Kill column padding — we control it manually */
[data-testid="column"] {
    padding-left: 5px !important;
    padding-right: 5px !important;
}

/* Kill Plotly chart container padding */
[data-testid="stPlotlyChart"] {
    padding: 0 !important;
}
[data-testid="stPlotlyChart"] > div {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* Kill markdown container built-in margin */
[data-testid="stMarkdownContainer"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
[data-testid="stMarkdownContainer"] > * {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}

/* Page background */
[data-testid="stAppViewContainer"] > section > div {
    background: #F7F8FA !important;
}

/* ════════════════════════════════════════════════════════════════
   SECTION NAVIGATION — st.radio as pills
   ════════════════════════════════════════════════════════════════ */
div[data-testid="stRadio"] {
    margin-top: 3px !important;
    margin-bottom: 3px !important;
}
div[data-testid="stRadio"] > div:first-child { display: none !important; }
div[data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 4px !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    display: inline-flex !important;
    align-items: center !important;
    border: 1px solid #EAECF0 !important;
    border-radius: 99px !important;
    padding: 4px 13px !important;
    background: #FFFFFF !important;
    color: #475467 !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
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

/* ════════════════════════════════════════════════════════════════
   PRIVACY NOTICE
   ════════════════════════════════════════════════════════════════ */
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

/* ════════════════════════════════════════════════════════════════
   FILE UPLOADER — compressed
   ════════════════════════════════════════════════════════════════ */
[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #CBD5E1 !important;
    border-radius: 8px !important;
    padding: 5px 12px !important;
    min-height: 46px !important;
}
[data-testid="stFileUploaderDropzone"] > div {
    padding: 3px 0 !important;
    gap: 4px !important;
}
[data-testid="stFileUploader"] section p {
    font-size: 12px !important;
    margin: 0 !important;
}
[data-testid="stFileUploader"] { margin: 0 !important; }

/* ════════════════════════════════════════════════════════════════
   SELECTBOX — compact
   ════════════════════════════════════════════════════════════════ */
div[data-testid="stSelectbox"] label { display: none !important; }
div[data-testid="stSelectbox"] div[role="combobox"] {
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    min-height: 34px !important;
}

/* ════════════════════════════════════════════════════════════════
   BUTTONS — compact
   ════════════════════════════════════════════════════════════════ */
div[data-testid="stButton"] button {
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    min-height: 34px !important;
}

/* ════════════════════════════════════════════════════════════════
   TABS (insights section)
   ════════════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 10px !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    border-bottom: 2px solid #EAECF0 !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #F04438 !important;
}

/* ════════════════════════════════════════════════════════════════
   TRANSACTION EXPLORER TABLE
   ════════════════════════════════════════════════════════════════ */
.txn-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 12.5px;
}
.txn-table th {
    font-size: 9.5px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: #98A2B3;
    padding: 6px 10px;
    text-align: left;
    border-bottom: 1px solid #EAECF0;
    background: #FAFAFA;
}
.txn-table td {
    padding: 8px 10px;
    border-bottom: 0.5px solid #F2F4F7;
    vertical-align: middle;
}
.txn-table tr:hover td { background: #FAFAFA; }
.txn-num  { color: #D0D5DD; font-size: 10.5px; width: 24px; }
.txn-date { color: #98A2B3; white-space: nowrap; width: 86px; }
.txn-desc { color: #374151; font-weight: 500; }
.txn-amt-pos { color: #12B76A; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
.txn-amt-neg { color: #F04438; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }
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
.cat-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.conf-track { background: #EAECF0; border-radius: 3px; height: 3px; width: 56px; overflow: hidden; }
.conf-fill  { height: 100%; border-radius: 3px; }

/* ════════════════════════════════════════════════════════════════
   ONBOARDING TILES
   ════════════════════════════════════════════════════════════════ */
.mh-tile {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 18px 20px;
    text-align: center;
    height: 100%;
}
.mh-tile-icon { font-size: 24px; margin-bottom: 8px; }
.mh-tile-title { font-size: 13.5px; font-weight: 600; color: #101828; margin-bottom: 4px; }
.mh-tile-desc  { font-size: 12px; color: #667085; line-height: 1.5; }

/* ════════════════════════════════════════════════════════════════
   DISCLAIMER
   ════════════════════════════════════════════════════════════════ */
.disclaimer {
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


def category_badge(category: str) -> str:
    """Return an HTML badge string for a category."""
    from config import category_badge_colors
    bg, text = category_badge_colors(category)
    # Dot colour matches text
    return (
        f'<span class="cat-badge" style="background:{bg};color:{text}">'
        f'<span class="cat-dot" style="background:{text}"></span>'
        f'{category}'
        f'</span>'
    )


def confidence_bar(confidence: str) -> str:
    """Return an HTML confidence progress bar."""
    widths = {"High": 100, "Medium": 60, "Low": 25}
    colors = {"High": "#12B76A", "Medium": "#F79009", "Low": "#F04438"}
    w = widths.get(confidence, 25)
    c = colors.get(confidence, "#F04438")
    return (
        f'<div style="display:flex;align-items:center;gap:5px">'
        f'<div class="conf-track"><div class="conf-fill" style="width:{w}%;background:{c}"></div></div>'
        f'<span style="font-size:10px;color:#98A2B3">{confidence or "Low"}</span>'
        f'</div>'
    )


def styled_transaction_table(
    df: "pd.DataFrame",
    sym: str = "$",
    max_rows: int = 12,
    page: int = 0,
) -> tuple[str, int]:
    """
    Render a styled transaction table with:
      - Colour-coded category badges
      - Confidence progress bars
      - Positive amounts in green, negative in red
    Returns (html_string, total_pages).
    """
    start = page * max_rows
    page_df = df.iloc[start : start + max_rows]
    total_pages = max(1, -(-len(df) // max_rows))

    rows_html = ""
    for i, (_, row) in enumerate(page_df.iterrows()):
        num  = start + i + 1
        date = row["Date"].strftime("%d %b %Y") if hasattr(row["Date"], "strftime") else str(row["Date"])
        desc = str(row.get("Description", ""))[:42]
        cat  = str(row.get("Category", "Other Expense"))
        conf = str(row.get("Confidence", ""))
        flag = str(row.get("Flag", ""))
        amt  = float(row.get("Amount", 0))
        amt_str   = f"+{sym}{abs(amt):,.2f}" if amt >= 0 else f"-{sym}{abs(amt):,.2f}"
        amt_class = "txn-amt-pos" if amt >= 0 else "txn-amt-neg"
        flag_note = f'<span style="color:#F79009;font-size:10px"> ⚑</span>' if flag else ""

        rows_html += (
            f'<tr>'
            f'<td class="txn-num">{num}</td>'
            f'<td class="txn-date">{date}</td>'
            f'<td class="txn-desc">{desc}{flag_note}</td>'
            f'<td>{category_badge(cat)}</td>'
            f'<td>{confidence_bar(conf)}</td>'
            f'<td class="{amt_class}">{amt_str}</td>'
            f'</tr>'
        )

    header = (
        '<tr>'
        '<th>#</th><th>Date</th><th>Description</th>'
        '<th>Category</th><th>Confidence</th><th style="text-align:right">Amount</th>'
        '</tr>'
    )
    table_html = f'<table class="txn-table">{header}{rows_html}</table>'
    return table_html, total_pages
