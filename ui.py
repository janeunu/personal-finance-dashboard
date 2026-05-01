"""
ui.py
Everything related to visual presentation:
  - CSS stylesheet
  - Number/money formatters
  - HTML component builders (cards, banners, bars)

Rules:
  • No business logic.
  • No data processing.
  • No Plotly — charts live in charts.py.
  • Every HTML string uses double-quoted attributes so it
    can safely live inside Python single-quoted strings.
"""

from __future__ import annotations

import streamlit as st


# ══════════════════════════════════════════════════════════════════════════════
#  STYLESHEET
# ══════════════════════════════════════════════════════════════════════════════
STYLESHEET = """
<style>
/* ── Fonts ──────────────────────────────────────────────────────────────────
   Barlow Condensed: tall, narrow — purpose-built for big display numbers.
   DM Sans: neutral, screen-optimised body copy.                            */
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=DM+Sans:wght@400;500;600&display=swap');

/* ── Reset ────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] { font-family: "DM Sans", sans-serif; }

/* ── Canvas ──────────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] { background: #f0ebe4; }
.block-container { padding: 1.2rem 1.8rem 3.5rem; max-width: 1300px; }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: #16110d !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: #e0d5ca !important; }
[data-testid="stSidebar"] label {
    color: #7a6e64 !important; font-size: 10px !important;
    font-family: "DM Sans", sans-serif !important;
    text-transform: uppercase; letter-spacing: .06em; }
[data-testid="stSidebar"] .stButton > button {
    background: #e06d35 !important; border: none !important;
    color: #fff !important; border-radius: 10px !important; font-weight: 600 !important; }
[data-testid="stSidebar"] .stDownloadButton > button {
    background: #2a2018 !important; border: 1px solid #3a3025 !important;
    color: #c8bcb0 !important; border-radius: 10px !important; }

/* ── Verdict banner ──────────────────────────────────────────────────────── */
.verdict {
    border-radius: 24px; padding: 28px 36px; margin-bottom: 20px;
    position: relative; overflow: hidden;
    display: flex; align-items: center; gap: 32px; flex-wrap: wrap; }
.verdict::before {
    content: ""; position: absolute; right: -40px; top: -40px;
    width: 240px; height: 240px; border-radius: 50%;
    background: rgba(255,255,255,.05); pointer-events: none; }
.v-score {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 88px; font-weight: 700; line-height: 1;
    letter-spacing: -1px; flex-shrink: 0; }
.v-label {
    font-size: 11px; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; opacity: .65; margin-bottom: 5px; }
.v-title {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 24px; font-weight: 700; line-height: 1.3;
    color: #fff; margin-bottom: 6px; }
.v-sub { font-size: 13.5px; line-height: 1.55; opacity: .7; color: #fff; }

/* ── KPI cards ───────────────────────────────────────────────────────────── */
.kpi {
    background: #fff; border-radius: 18px; padding: 18px 20px 14px;
    box-shadow: 0 1px 0 rgba(0,0,0,.04), 0 4px 16px rgba(42,28,14,.07);
    margin-bottom: 14px; }
.kpi-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .06em; color: #b8a898; margin-bottom: 5px; }
.kpi-value {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 30px; font-weight: 700; line-height: 1.05; }
.kpi-delta { font-size: 11.5px; margin-top: 5px; font-weight: 500; }
.up   { color: #1a9e75; }
.down { color: #d94838; }
.neu  { color: #c0b6ae; }

/* ── Section divider ─────────────────────────────────────────────────────── */
.sec {
    font-family: "DM Sans", sans-serif;
    font-size: 11px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #a89880;
    margin: 4px 0 14px; display: flex; align-items: center; gap: 8px; }
.sec::after { content: ""; flex: 1; height: 1px; background: #ddd4c8; }

/* ── Chart card ──────────────────────────────────────────────────────────── */
.cc {
    background: #fff; border-radius: 20px; padding: 20px 20px 6px;
    box-shadow: 0 1px 0 rgba(0,0,0,.04), 0 4px 16px rgba(42,28,14,.07);
    margin-bottom: 14px; }
.cc-title {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 15px; font-weight: 700; color: #2a1c10;
    margin-bottom: 8px; letter-spacing: .01em; }

/* ── Insight / Action cards ──────────────────────────────────────────────── */
.ins {
    background: #faf6f1; border-left: 3px solid #e06d35;
    border-radius: 0 12px 12px 0;
    padding: 12px 16px; margin-bottom: 9px;
    font-size: 13.5px; color: #2a1c10; line-height: 1.6; }
.act {
    background: #fff; border-radius: 14px; padding: 13px 16px; margin-bottom: 9px;
    border: 1px solid #e8e0d6; box-shadow: 0 1px 4px rgba(42,28,14,.04);
    display: flex; gap: 11px; align-items: flex-start; }
.act-n {
    min-width: 22px; height: 22px; background: #fdeede; color: #c85a10;
    border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; font-family: "DM Sans", sans-serif;
    flex-shrink: 0; margin-top: 2px; }
.act-t { font-weight: 600; font-size: 13px; color: #1a1008; margin-bottom: 2px; }
.act-d { font-size: 12.5px; color: #8c7c6c; line-height: 1.5; }

/* ── Top-transaction callout ─────────────────────────────────────────────── */
.txn {
    background: #fff; border-radius: 16px; padding: 14px 18px; margin-bottom: 9px;
    border: 1px solid #e8e0d6; box-shadow: 0 1px 4px rgba(42,28,14,.04); }
.txn-amt {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 26px; font-weight: 700; color: #d94838; }
.txn-desc { font-size: 13px; font-weight: 600; color: #2a1c10; margin: 2px 0; }
.txn-meta { font-size: 11px; color: #b8a898; }

/* ── Subscription list ───────────────────────────────────────────────────── */
.sub-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 0; border-bottom: 1px solid #f0e8de; }
.sub-row:last-child { border-bottom: none; }
.sub-name { font-size: 13px; font-weight: 600; color: #2a1c10; }
.sub-amt  {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 16px; font-weight: 700; color: #d94838; }

/* ── Budget bars ─────────────────────────────────────────────────────────── */
.brow { margin-bottom: 13px; }
.brow-label {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 12.5px; color: #3a2c20; margin-bottom: 4px; font-weight: 600; }
.brow-badge { font-size: 10px; font-weight: 700; }
.brow-track { background: #ede4d8; border-radius: 99px; height: 5px; overflow: hidden; }
.brow-fill  { height: 100%; border-radius: 99px; }

/* ── AI panel ────────────────────────────────────────────────────────────── */
.ai-panel {
    background: linear-gradient(140deg, #f5f2ff, #f0f8ff);
    border: 1px solid #d8d0f4; border-radius: 18px; padding: 22px 24px; }
.ai-tag {
    background: #ece6fd; color: #5738c8; font-size: 10px; font-weight: 700;
    letter-spacing: .04em; padding: 3px 10px; border-radius: 99px;
    margin-bottom: 12px; display: inline-block; }
.ai-body { font-size: 14px; color: #1a1008; line-height: 1.8; white-space: pre-line; }

/* ── Notices ─────────────────────────────────────────────────────────────── */
.privacy {
    background: #e8e0d6; border-radius: 12px; padding: 10px 16px;
    margin-bottom: 20px; font-size: 12px; color: #7a6e64; line-height: 1.5; }
.parse-info {
    background: #f4ede4; border: 1px solid #ddd0c0; border-radius: 12px;
    padding: 10px 16px; font-size: 12px; color: #6a5e54;
    line-height: 1.65; margin-bottom: 16px; }
.badge-ai { display:inline-block; background:#ece6fd; color:#5738c8; font-size:10px;
    font-weight:700; padding:2px 9px; border-radius:99px; margin-left:6px; }
.badge-kw { display:inline-block; background:#fdeede; color:#c85a10; font-size:10px;
    font-weight:700; padding:2px 9px; border-radius:99px; margin-left:6px; }
.disclaimer {
    background: #e4dcd2; border-radius: 12px; padding: 11px 18px;
    font-size: 11px; color: #a09080; text-align: center;
    margin-top: 24px; line-height: 1.6; }

/* ── Onboarding tiles ────────────────────────────────────────────────────── */
.ob-card {
    background: #fff; border-radius: 20px; padding: 32px 24px; text-align: center;
    border: 1px solid #ddd4c8; box-shadow: 0 4px 16px rgba(42,28,14,.06); }
.ob-icon  { font-size: 36px; margin-bottom: 12px; }
.ob-title {
    font-family: "Barlow Condensed", sans-serif;
    font-size: 16px; font-weight: 700; color: #1a1008; margin-bottom: 7px; }
.ob-desc  { font-size: 13px; color: #9a8e82; line-height: 1.6; }

/* ── Streamlit overrides ─────────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"] {
    background: #fff !important;
    border: 2px dashed #d4cbbf !important;
    border-radius: 14px !important; }
div[data-testid="stHorizontalBlock"] { gap: 14px; }
</style>
"""


def inject_css() -> None:
    st.markdown(STYLESHEET, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  FORMATTERS
# ══════════════════════════════════════════════════════════════════════════════
def fmt_money(v: float, sym: str = "$", signed: bool = False) -> str:
    """
    Format a monetary value.
    Drops cents for values ≥ $1,000 to keep KPI cards compact.
    """
    abs_v = abs(v)
    body  = f"{abs_v:,.0f}" if abs_v >= 1000 else f"{abs_v:,.2f}"
    if signed:
        prefix = "+" if v >= 0 else "-"
        return f"{prefix}{sym}{body}"
    return f"{sym}{body}"


def fmt_pct(v: float, decimals: int = 1) -> str:
    return f"{v:.{decimals}f}%"


def delta_badge(current: float, previous: float, invert: bool = False) -> str:
    """Return an HTML <span> showing ▲/▼ change vs previous period."""
    if previous == 0:
        return '<span class="neu">—</span>'
    pct   = (current - previous) / abs(previous) * 100
    up    = pct > 0
    good  = up if not invert else not up
    cls   = "up" if good else "down"
    arrow = "▲" if up else "▼"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


# ══════════════════════════════════════════════════════════════════════════════
#  HTML COMPONENT BUILDERS
#  All attributes use double quotes — safe inside Python single-quoted strings.
# ══════════════════════════════════════════════════════════════════════════════
def section(label: str) -> None:
    st.markdown(f'<p class="sec">{label}</p>', unsafe_allow_html=True)


def verdict_banner(
    score:       int,
    score_label: str,
    score_color: str,
    score_bg:    str,
    headline:    str,
    sub:         str,
) -> None:
    st.markdown(
        f'<div class="verdict" style="background:{score_bg}">'
        f'  <div class="v-score" style="color:{score_color}">{score}</div>'
        f'  <div>'
        f'    <div class="v-label">Money Health Score &nbsp;&middot;&nbsp; {score_label}</div>'
        f'    <div class="v-title">{headline}</div>'
        f'    <div class="v-sub">{sub}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kpi_card(
    label:       str,
    value:       str,
    value_color: str,
    delta_html:  str,
) -> None:
    st.markdown(
        f'<div class="kpi">'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value" style="color:{value_color}">{value}</div>'
        f'  <div class="kpi-delta">{delta_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def chart_card_start(title: str = "") -> None:
    inner = f'<div class="cc-title">{title}</div>' if title else ""
    st.markdown(f'<div class="cc">{inner}', unsafe_allow_html=True)


def chart_card_end() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def insight_card(html_body: str) -> None:
    st.markdown(f'<div class="ins">{html_body}</div>', unsafe_allow_html=True)


def action_card(num: int, emoji: str, title: str, desc: str) -> None:
    st.markdown(
        f'<div class="act">'
        f'  <div class="act-n">{num}</div>'
        f'  <div>'
        f'    <div class="act-t">{emoji} {title}</div>'
        f'    <div class="act-d">{desc}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def transaction_card(amount: str, description: str, date: str, category: str) -> None:
    st.markdown(
        f'<div class="txn">'
        f'  <div class="txn-amt">{amount}</div>'
        f'  <div class="txn-desc">{description}</div>'
        f'  <div class="txn-meta">{date} &nbsp;&middot;&nbsp; {category}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def budget_bar(
    label:      str,
    amount_str: str,
    actual_pct: float,
    rec_pct:    int,
) -> None:
    bar_w = min(actual_pct / rec_pct * 100, 100) if rec_pct else 0.0
    if actual_pct > rec_pct:
        color  = "#e86858"
        badge  = f'<span class="brow-badge" style="color:#c03020">&#8593; {actual_pct:.0f}%&thinsp;/&thinsp;{rec_pct}%</span>'
    elif actual_pct > rec_pct * 0.8:
        color  = "#f0b85b"
        badge  = f'<span class="brow-badge" style="color:#8a6000">&#8599; {actual_pct:.0f}%&thinsp;/&thinsp;{rec_pct}%</span>'
    else:
        color  = "#2db88a"
        badge  = f'<span class="brow-badge" style="color:#1a7a50">&#10003; {actual_pct:.0f}%&thinsp;/&thinsp;{rec_pct}%</span>'

    st.markdown(
        f'<div class="brow">'
        f'  <div class="brow-label">'
        f'    <span>{label} <span style="color:#c0b0a0;font-weight:400;font-size:11px">{amount_str}</span></span>'
        f'    {badge}'
        f'  </div>'
        f'  <div class="brow-track">'
        f'    <div class="brow-fill" style="width:{bar_w:.1f}%;background:{color}"></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def subscription_list(rows_html: str, total_str: str) -> None:
    st.markdown(
        f'<div style="background:#fff;border-radius:18px;padding:16px 20px;'
        f'border:1px solid #e8e0d6;box-shadow:0 1px 4px rgba(42,28,14,.05)">'
        f'{rows_html}'
        f'<div style="display:flex;justify-content:space-between;padding:10px 0 2px;'
        f'font-weight:700;font-size:13px;color:#8c7c6c">'
        f'<span>Total</span>'
        f'<span class="sub-amt">{total_str}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def parse_info_bar(
    col_map:  dict[str, str],
    method:   str,
    currency: str,
    warnings: list[str],
) -> None:
    badge_cls  = "badge-ai" if method == "ai" else "badge-kw"
    badge_text = "✦ AI" if method == "ai" else "keyword rules"
    html = (
        f'<b>Columns detected</b>'
        f'<span class="{badge_cls}">{badge_text}</span>: '
        f'Date &rarr; <code>{col_map.get("date","?")}</code> &nbsp;&middot;&nbsp; '
        f'Description &rarr; <code>{col_map.get("description","?")}</code> &nbsp;&middot;&nbsp; '
        f'Amount &rarr; <code>{col_map.get("amount","?")}</code>'
    )
    if currency and currency != "$":
        html += f' &nbsp;&middot;&nbsp; Currency: <b>{currency}</b>'
    if warnings:
        html += "<br>&#9888; " + " &nbsp;|&nbsp; ".join(warnings)
    st.markdown(f'<div class="parse-info">{html}</div>', unsafe_allow_html=True)


def onboarding_tiles() -> None:
    tiles = [
        ("🌍", "Works with Any Bank",
         "Japanese, Arabic, German, Korean, Mongolian — any language, any column format, any currency."),
        ("🧠", "AI-Powered Detection",
         "Claude reads your CSV header and automatically finds date, description, and amount columns."),
        ("⚡", "Smart Categorisation",
         "Transactions in any language are understood and sorted into clear categories instantly."),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, tiles):
        with col:
            st.markdown(
                f'<div class="ob-card">'
                f'<div class="ob-icon">{icon}</div>'
                f'<div class="ob-title">{title}</div>'
                f'<div class="ob-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
