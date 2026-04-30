"""
app.py — Money Health Agent
Requires: categoriser.py in the same folder
Compatible with pandas 3.x, Python 3.10+
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

from categoriser import parse_statement, STANDARD_CATEGORIES

st.set_page_config(page_title="Money Health", page_icon="💰", layout="wide")

# ══════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════
FIXED_CATS   = {"Rent","Mortgage","Childcare","Insurance","Utilities",
                "Phone","Internet","Car Expenses"}
BUDGET_GUIDE = {
    "Rent": 30, "Groceries": 12, "Eating Out": 5, "Transport": 5,
    "Subscriptions": 3, "Shopping": 5, "Health & Medical": 5, "Utilities": 6,
}
TREEMAP_SCALE = ["#fef0eb","#f5c4ab","#ec996b","#e06d35","#c8501a","#8c300a"]
DAY_ORDER     = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ══════════════════════════════════════════════════════════
#  STYLES
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Fonts ──
   Barlow Condensed: purpose-built narrow display font — no horizontal stretch
   DM Sans: clean, neutral body copy                                          */
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=DM+Sans:wght@400;500;600&display=swap');

/* ── Reset ── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── Canvas ── */
[data-testid="stAppViewContainer"] { background: #f0ebe4; }
.block-container { padding: 1.2rem 1.8rem 3.5rem; max-width: 1300px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: #16110d !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: #e0d5ca !important; }
[data-testid="stSidebar"] label {
    color: #7a6e64 !important; font-size: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    text-transform: uppercase; letter-spacing: .06em; }
[data-testid="stSidebar"] .stButton > button {
    background: #e06d35 !important; border: none !important;
    color: #fff !important; border-radius: 10px !important; font-weight: 600 !important; }
[data-testid="stSidebar"] .stDownloadButton > button {
    background: #2a2018 !important; border: 1px solid #3a3025 !important;
    color: #c8bcb0 !important; border-radius: 10px !important; }

/* ── Verdict banner ── */
.verdict {
    border-radius: 24px; padding: 28px 36px; margin-bottom: 20px;
    position: relative; overflow: hidden;
    display: flex; align-items: center; gap: 32px; flex-wrap: wrap; }
.verdict::before {
    content: ''; position: absolute; right: -40px; top: -40px;
    width: 240px; height: 240px; border-radius: 50%;
    background: rgba(255,255,255,.05); }
/* Barlow Condensed keeps the big score tall and narrow — not wide */
.v-score {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 88px; font-weight: 700; line-height: 1;
    letter-spacing: -1px; flex-shrink: 0; }
.v-label {
    font-size: 11px; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; opacity: .65; margin-bottom: 5px; }
.v-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 24px; font-weight: 700; line-height: 1.3;
    color: #fff; margin-bottom: 6px; }
.v-sub { font-size: 13.5px; line-height: 1.55; opacity: .7; color: #fff; }

/* ── KPI cards ── */
.kpi {
    background: #fff; border-radius: 18px; padding: 18px 20px 14px;
    box-shadow: 0 1px 0 rgba(0,0,0,.04), 0 4px 16px rgba(42,28,14,.07);
    margin-bottom: 14px; }
.kpi-label {
    font-size: 10px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .06em; color: #b8a898; margin-bottom: 5px; }
/* Barlow Condensed is narrow by design — "+" $16,896 fits cleanly */
.kpi-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 30px; font-weight: 700; line-height: 1.05;
    letter-spacing: 0; }
.kpi-delta { font-size: 11.5px; margin-top: 5px; font-weight: 500; }
.up  { color: #1a9e75; }
.down{ color: #d94838; }
.neu { color: #c0b6ae; }

/* ── Section dividers ── */
.sec {
    font-family: 'DM Sans', sans-serif;
    font-size: 11px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #a89880;
    margin: 4px 0 14px; display: flex; align-items: center; gap: 8px; }
.sec::after { content: ''; flex: 1; height: 1px; background: #ddd4c8; }

/* ── Chart card ── */
.cc {
    background: #fff; border-radius: 20px; padding: 20px 20px 6px;
    box-shadow: 0 1px 0 rgba(0,0,0,.04), 0 4px 16px rgba(42,28,14,.07);
    margin-bottom: 14px; }
.cc-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 15px; font-weight: 700; color: #2a1c10; margin-bottom: 6px; }

/* ── Insight / Action cards ── */
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
    font-size: 11px; font-weight: 700; font-family: 'DM Sans', sans-serif;
    flex-shrink: 0; margin-top: 2px; }
.act-t { font-weight: 600; font-size: 13px; color: #1a1008; margin-bottom: 2px; }
.act-d { font-size: 12.5px; color: #8c7c6c; line-height: 1.5; }

/* ── Top-transaction callout ── */
.txn {
    background: #fff; border-radius: 16px; padding: 14px 18px; margin-bottom: 9px;
    border: 1px solid #e8e0d6; box-shadow: 0 1px 4px rgba(42,28,14,.04); }
.txn-amt {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 26px; font-weight: 700; color: #d94838; }
.txn-desc { font-size: 13px; font-weight: 600; color: #2a1c10; margin: 2px 0; }
.txn-meta { font-size: 11px; color: #b8a898; }

/* ── Subscription list ── */
.sub-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 0; border-bottom: 1px solid #f0e8de; }
.sub-row:last-child { border-bottom: none; }
.sub-name { font-size: 13px; font-weight: 600; color: #2a1c10; }
.sub-amt  {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 16px; font-weight: 700; color: #d94838; }

/* ── Notices ── */
.privacy {
    background: #e8e0d6; border-radius: 12px; padding: 10px 16px;
    margin-bottom: 20px; font-size: 12px; color: #7a6e64; line-height: 1.5; }
.disclaimer {
    background: #e4dcd2; border-radius: 12px; padding: 11px 18px;
    font-size: 11px; color: #a09080; text-align: center;
    margin-top: 24px; line-height: 1.6; }
.parse-info {
    background: #f4ede4; border: 1px solid #ddd0c0; border-radius: 12px;
    padding: 10px 16px; font-size: 12px; color: #6a5e54;
    line-height: 1.65; margin-bottom: 16px; }
.mb-ai {
    display: inline-block; background: #ece6fd; color: #5738c8;
    font-size: 10px; font-weight: 700; letter-spacing: .04em;
    padding: 2px 9px; border-radius: 99px; margin-left: 6px; }
.mb-kw {
    display: inline-block; background: #fdeede; color: #c85a10;
    font-size: 10px; font-weight: 700; letter-spacing: .04em;
    padding: 2px 9px; border-radius: 99px; margin-left: 6px; }

/* ── Streamlit overrides ── */
[data-testid="stFileUploaderDropzone"] {
    background: #fff !important; border: 2px dashed #d4cbbf !important;
    border-radius: 14px !important; }
div[data-testid="stHorizontalBlock"] { gap: 14px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════
def fmt(v: float, sym: str = "$", signed: bool = False) -> str:
    """Format a dollar amount. Drop cents for values ≥ $1,000 to keep KPI cards clean."""
    abs_v = abs(v)
    dec   = ".00" if abs_v < 1000 else ""
    if signed:
        return f"+{sym}{v:,.0f}{dec}" if v >= 0 else f"-{sym}{abs_v:,.0f}{dec}"
    return f"{sym}{abs_v:,.0f}{dec}" if abs_v >= 1000 else f"{sym}{abs_v:,.2f}"

def delta_html(curr: float, prev: float, invert: bool = False) -> str:
    if prev == 0:
        return '<span class="neu">—</span>'
    d     = (curr - prev) / abs(prev) * 100
    cls   = ("down" if d > 0 else "up") if invert else ("up" if d > 0 else "down")
    arrow = "▲" if d > 0 else "▼"
    return f'<span class="{cls}">{arrow} {abs(d):.1f}%</span>'

def score_color(s: int) -> str:
    if s >= 80: return "#2db88a"
    if s >= 65: return "#5b7cf0"
    if s >= 45: return "#e09a2e"
    return "#e05c4e"

def score_bg(s: int) -> str:
    if s >= 80: return "#082b1a"
    if s >= 65: return "#0a1830"
    if s >= 45: return "#28180a"
    return "#280a08"

def score_label(s: int) -> str:
    if s >= 80: return "Excellent"
    if s >= 65: return "Healthy"
    if s >= 45: return "Needs Attention"
    return "At Risk"

def verdict(s: int, net: float, sr: float, top_cat: str | None) -> str:
    tc = top_cat or "spending"
    if s >= 80: return f"You're in great financial shape — saving {sr:.0f}% of income."
    if s >= 65: return f"Your finances are healthy. Keeping an eye on {tc} will push you further."
    if s >= 45: return f"A few things need attention. Focusing on {tc} will have the most impact."
    return "Spending is outpacing income right now — let's find where to start." \
           if net < 0 else "Some areas are under pressure. Small changes make a real difference."

def calc_score(income: float, expense: float, net: float, sr: float, sub: float) -> int:
    s = 0
    if income > 0:   s += 20
    if net > 0:      s += 25
    if sr >= 20:     s += 25
    elif sr >= 10:   s += 15
    elif sr > 0:     s += 8
    r = expense / income if income > 0 else 1
    if r <= 0.75:    s += 15
    elif r <= 0.90:  s += 8
    r2 = sub / income if income > 0 else 0
    if r2 <= 0.03:   s += 15
    elif r2 <= 0.06: s += 8
    return min(s, 100)

def ai_coach_call(api_key: str, summary: str) -> str | None:
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "content-type": "application/json",
                     "anthropic-version": "2023-06-01"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 600,
                  "messages": [{"role": "user", "content": (
                      "You are a warm, plain-English personal finance coach.\n"
                      "Write exactly 4 short insights from the summary below.\n"
                      "Rules: start each with one emoji · max 2 sentences · "
                      "reference real numbers · honest and encouraging · no intro/outro.\n\n"
                      f"Summary:\n{summary}"
                  )}]},
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
    except Exception:
        pass
    return None

def base_layout(h: int = 360, mt: int = 14, mb: int = 28, ml: int = 4, mr: int = 4, **kw) -> dict:
    """Single source of truth for chart layout. margin is built here — never pass margin separately."""
    return dict(
        height=h,
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font={"family": "'DM Sans',sans-serif", "color": "#5a4e42"},
        margin=dict(t=mt, b=mb, l=ml, r=mr),
        **kw,
    )

def xax(grid: bool = False) -> dict:
    d = dict(title="", zeroline=False, linecolor="#ddd4c8", showgrid=grid)
    if grid: d.update(gridcolor="#f4ede4", gridwidth=1)
    return d

def yax() -> dict:
    return dict(title="", zeroline=False, linecolor="#ddd4c8",
                showgrid=True, gridcolor="#f4ede4", gridwidth=1)

# ── pandas-3.x safe savings-rate calculation ──────────────────────────────────
def _month_savings_rate(df: pd.DataFrame) -> pd.Series:
    """Return a Series indexed by Month with the savings rate for each month."""
    months = sorted(df["Month"].unique())
    rates  = {}
    for m in months:
        g   = df[df["Month"] == m]
        inc = g[g["Type"] == "Income"]["Amount"].sum()
        exp = g[g["Type"] == "Expense"]["Amount"].abs().sum()
        rates[m] = (inc - exp) / inc * 100 if inc > 0 else 0.0
    return pd.Series(rates, name="SavingsRate")


# ══════════════════════════════════════════════════════════
#  SIDEBAR (placeholders filled after data loads)
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Filters")
    _ph_month  = st.empty()
    _ph_cat    = st.empty()
    st.markdown("---")
    st.markdown("### API Key")
    st.caption("Powers AI column detection and smart categorisation in any language.")
    api_key = st.text_input(
        "Anthropic API Key", type="password",
        placeholder="sk-ant-…",
        help="Optional but recommended. Get one free at console.anthropic.com",
    )
    st.markdown("---")
    st.markdown("### AI Coach")
    run_ai = st.button("✦ Generate Insights", use_container_width=True)
    st.markdown("---")
    st.markdown("### Export")
    _ph_export = st.empty()


# ══════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="privacy">
  🔒 <b>Privacy:</b> Your file is processed only in this browser session — never stored or shared.
  For personal tracking only, not financial advice.
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Upload your bank statement — any language, any bank",
    type=["csv"],
    help="CSV with at least a date column, description column, and amount column.",
)

if uploaded is None:
    c1, c2, c3 = st.columns(3)
    for col, (icon, title, desc) in zip([c1, c2, c3], [
        ("🌍", "Works with Any Bank",
         "Japanese, Arabic, German, Korean, Mongolian — any language, any column format, any currency."),
        ("🧠", "AI-Powered Detection",
         "Claude reads your CSV header and automatically finds the date, description, and amount columns."),
        ("⚡", "Smart Categorisation",
         "Transactions in any language are understood and sorted into clear categories instantly."),
    ]):
        with col:
            st.markdown(f"""
            <div style="background:#fff;border-radius:22px;padding:34px 26px;text-align:center;
                        border:1px solid #ddd4c8;box-shadow:0 6px 20px rgba(42,28,14,.07)">
              <div style="font-size:38px;margin-bottom:14px">{icon}</div>
              <div style="font-family:'Barlow Condensed',sans-serif;font-size:16px;font-weight:700;
                          color:#1a1008;margin-bottom:8px">{title}</div>
              <div style="font-size:13px;color:#9a8e82;line-height:1.6">{desc}</div>
            </div>""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════
#  PARSE
# ══════════════════════════════════════════════════════════
raw_bytes  = uploaded.read()
api_to_use = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")


@st.cache_data(show_spinner=False)
def run_parse(b: bytes, k: str) -> tuple:
    return parse_statement(b, k or None)


with st.spinner("Reading and categorising your transactions…"):
    try:
        df, meta = run_parse(raw_bytes, api_to_use)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        st.stop()

# ── Parse info bar ────────────────────────────────────────
cu   = meta["columns_used"]
sym  = meta.get("currency_symbol") or "$"
meth = meta["method"]
badge_html = f'<span class="{"mb-ai" if meth=="ai" else "mb-kw"}">{"✦ AI" if meth=="ai" else "keyword rules"}</span>'
info  = (
    f'<b>Columns detected</b>{badge_html}: '
    f'Date → <code>{cu.get("date","?")}</code> &nbsp;·&nbsp; '
    f'Description → <code>{cu.get("description","?")}</code> &nbsp;·&nbsp; '
    f'Amount → <code>{cu.get("amount","?")}</code>'
)
if sym and sym != "$":
    info += f' &nbsp;·&nbsp; Currency: <b>{sym}</b>'
if meta.get("warnings"):
    info += "<br>⚠ " + " | ".join(meta["warnings"])
st.markdown(f'<div class="parse-info">{info}</div>', unsafe_allow_html=True)

# ── Sidebar filters ───────────────────────────────────────
sel_month = _ph_month.selectbox("Month", ["All"] + sorted(df["Month"].unique()))
sel_cat   = _ph_cat.selectbox("Category", ["All"] + sorted(df["Category"].unique()))
_ph_export.download_button(
    "⬇ Download Categorised CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="money_health_transactions.csv",
    mime="text/csv",
    use_container_width=True,
)


# ══════════════════════════════════════════════════════════
#  FILTER & METRICS
# ══════════════════════════════════════════════════════════
fdf = df.copy()
if sel_month != "All": fdf = fdf[fdf["Month"] == sel_month]
if sel_cat   != "All": fdf = fdf[fdf["Category"] == sel_cat]

inc_df = fdf[fdf["Type"] == "Income"]
exp_df = fdf[fdf["Type"] == "Expense"]

total_income  = float(inc_df["Amount"].sum())
total_expense = float(exp_df["Amount"].abs().sum())
net           = total_income - total_expense
savings_rate  = (net / total_income * 100) if total_income > 0 else 0.0

exp_summary = (
    exp_df.groupby("Category", as_index=False)["Amount"]
    .apply(lambda x: x.abs().sum())
    .rename(columns={"Amount": "Total"})
    .sort_values("Total", ascending=False)
    .reset_index(drop=True)
)

sub_total    = float(exp_df[exp_df["Category"].isin(["Subscriptions","Streaming"])]["Amount"].abs().sum())
fixed_total  = float(exp_df[exp_df["Category"].isin(FIXED_CATS)]["Amount"].abs().sum())
flex_total   = total_expense - fixed_total
avg_daily    = total_expense / max(int(exp_df["Day"].nunique()), 1)
health_score = calc_score(total_income, total_expense, net, savings_rate, sub_total)
s_label      = score_label(health_score)
top_cat      = exp_summary.iloc[0]["Category"] if not exp_summary.empty else None

# Previous period deltas
all_months = sorted(df["Month"].unique())
prev_df    = pd.DataFrame()
if sel_month != "All" and sel_month in all_months:
    idx = all_months.index(sel_month)
    if idx > 0:
        prev_df = df[df["Month"] == all_months[idx - 1]]

prev_inc = float(prev_df[prev_df["Type"] == "Income"]["Amount"].sum()) if not prev_df.empty else 0.0
prev_exp = float(prev_df[prev_df["Type"] == "Expense"]["Amount"].abs().sum()) if not prev_df.empty else 0.0
prev_net = prev_inc - prev_exp


# ══════════════════════════════════════════════════════════
#  VERDICT BANNER
# ══════════════════════════════════════════════════════════
sc = score_color(health_score)
bg = score_bg(health_score)
st.markdown(f"""
<div class="verdict" style="background:{bg}">
  <div class="v-score" style="color:{sc}">{health_score}</div>
  <div>
    <div class="v-label">Money Health Score &nbsp;·&nbsp; {s_label}</div>
    <div class="v-title">{verdict(health_score, net, savings_rate, top_cat)}</div>
    <div class="v-sub">
      Income <b>{fmt(total_income, sym)}</b> &nbsp;·&nbsp;
      Expenses <b>{fmt(total_expense, sym)}</b> &nbsp;·&nbsp;
      Saved <b>{fmt(net, sym, signed=True)}</b>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  KPI STRIP
# ══════════════════════════════════════════════════════════
flex_pct = (flex_total / total_expense * 100) if total_expense > 0 else 0.0

k1, k2, k3, k4 = st.columns(4)

with k1:
    nc = "#1a9e75" if net >= 0 else "#d94838"
    st.markdown(f"""<div class="kpi">
      <div class="kpi-label">Money Left Over</div>
      <div class="kpi-value" style="color:{nc}">{fmt(net, sym, signed=True)}</div>
      <div class="kpi-delta">{delta_html(net, prev_net)} vs last period</div>
    </div>""", unsafe_allow_html=True)

with k2:
    src = "#1a9e75" if savings_rate >= 20 else "#e09a2e" if savings_rate >= 10 else "#d94838"
    st.markdown(f"""<div class="kpi">
      <div class="kpi-label">Savings Rate</div>
      <div class="kpi-value" style="color:{src}">{savings_rate:.1f}%</div>
      <div class="kpi-delta"><span class="neu">Goal: 20% &nbsp;·&nbsp; You're at {savings_rate:.0f}%</span></div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""<div class="kpi">
      <div class="kpi-label">Avg Daily Spend</div>
      <div class="kpi-value" style="color:#2a1c10">{fmt(avg_daily, sym)}</div>
      <div class="kpi-delta"><span class="neu">Across {exp_df['Day'].nunique()} spending days</span></div>
    </div>""", unsafe_allow_html=True)

with k4:
    fc = "#d94838" if flex_pct > 50 else "#e09a2e" if flex_pct > 35 else "#1a9e75"
    st.markdown(f"""<div class="kpi">
      <div class="kpi-label">Flexible Spending</div>
      <div class="kpi-value" style="color:{fc}">{flex_pct:.0f}%</div>
      <div class="kpi-delta"><span class="neu">{fmt(flex_total, sym)} of {fmt(total_expense, sym)} is cuttable</span></div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  WATERFALL  +  FIXED vs FLEXIBLE  +  BUDGET CHECK
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">💧 Where Did the Money Go?</p>', unsafe_allow_html=True)
w1, w2 = st.columns([1.6, 1])

with w1:
    cats  = exp_summary["Category"].head(9).tolist()
    vals  = (-exp_summary["Total"].head(9)).tolist()
    other = -(total_expense - exp_summary["Total"].head(9).sum())
    if abs(other) > 0.5:
        cats.append("Other"); vals.append(other)

    wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute"] + ["relative"] * len(cats) + ["total"],
        x=["Income"] + cats + ["Net"],
        y=[total_income] + vals + [0],
        text=[fmt(total_income, sym)]
             + [f"-{fmt(abs(v), sym)}" for v in vals]
             + [fmt(net, sym, signed=True)],
        textposition="outside",
        textfont={"size": 10, "family": "'DM Sans',sans-serif"},
        connector={"line": {"color": "#e8ddd2", "width": 1}},
        increasing={"marker": {"color": "#2db88a", "line": {"width": 0}}},
        decreasing={"marker": {"color": "#e86858", "line": {"width": 0}}},
        totals={"marker":   {"color": "#5b7cf0", "line": {"width": 0}}},
    ))
    wf.update_layout(
        **base_layout(h=400), showlegend=False,
        xaxis={**xax(), "tickfont": {"size": 11}},
        yaxis={**yax(), "tickprefix": sym},
    )
    st.markdown('<div class="cc">', unsafe_allow_html=True)
    st.plotly_chart(wf, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with w2:
    # Fixed vs Flexible donut
    if total_expense > 0:
        fvf = px.pie(
            pd.DataFrame({"Type": ["Fixed Bills", "Flexible Spending"],
                          "Amount": [fixed_total, flex_total]}),
            names="Type", values="Amount", hole=0.58,
            color_discrete_sequence=["#5b7cf0", "#e86858"],
        )
        fvf.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_size=12, pull=[0, 0.03])
        fvf.update_layout(
            **base_layout(h=230, mb=10, ml=0, mr=0), showlegend=False,
            annotations=[dict(
                text=f"<b>{fmt(total_expense, sym)}</b><br>"
                     f"<span style='font-size:10px'>total spend</span>",
                x=0.5, y=0.5, font_size=13, showarrow=False,
                font={"family": "'DM Sans',sans-serif", "color": "#2a1c10"},
            )],
        )
        st.markdown(
            '<div class="cc"><div class="cc-title">Fixed vs Flexible</div>',
            unsafe_allow_html=True)
        st.plotly_chart(fvf, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Budget check bars
    st.markdown(
        '<div class="cc"><div class="cc-title" style="margin-bottom:14px">Budget Check</div>',
        unsafe_allow_html=True)
    for cat, rec in list(BUDGET_GUIDE.items())[:5]:
        act = float(exp_summary[exp_summary["Category"] == cat]["Total"].sum())
        ap  = (act / total_income * 100) if total_income > 0 else 0.0
        bw  = min(ap / rec * 100, 100) if rec > 0 else 0.0
        fill = "#e86858" if ap > rec else "#f0b85b" if ap > rec * 0.8 else "#2db88a"
        badge = (
            f'<span style="color:#c03020;font-size:10px;font-weight:700">↑ {ap:.0f}%/{rec}%</span>'
            if ap > rec else
            f'<span style="color:#8a6000;font-size:10px;font-weight:700">↗ {ap:.0f}%/{rec}%</span>'
            if ap > rec * 0.8 else
            f'<span style="color:#1a7a50;font-size:10px;font-weight:700">✓ {ap:.0f}%/{rec}%</span>'
        )
        st.markdown(f"""
        <div style="margin-bottom:13px">
          <div style="display:flex;justify-content:space-between;font-size:12.5px;
                      color:#3a2c20;margin-bottom:4px;font-weight:600">
            <span>{cat} <span style="color:#c0b0a0;font-weight:400;font-size:11px">{fmt(act,sym)}</span></span>
            {badge}
          </div>
          <div style="background:#ede4d8;border-radius:99px;height:5px;overflow:hidden">
            <div style="width:{bw:.1f}%;height:100%;background:{fill};border-radius:99px"></div>
          </div>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  TREEMAP  +  TOP TRANSACTIONS  +  SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">🗂 Spending Breakdown</p>', unsafe_allow_html=True)
t1, t2 = st.columns([1.5, 1])

with t1:
    if not exp_summary.empty:
        tree = px.treemap(
            exp_summary, path=["Category"], values="Total",
            color="Total", color_continuous_scale=TREEMAP_SCALE,
        )
        tree.update_traces(
            texttemplate=f"<b>%{{label}}</b><br>{sym}%{{value:,.0f}}",
            textfont={"size": 13, "family": "'DM Sans',sans-serif"},
            hovertemplate=f"<b>%{{label}}</b><br>{sym}%{{value:,.2f}}<extra></extra>",
        )
        tree.update_layout(
            **base_layout(h=400, mb=8), coloraxis_showscale=False,
        )
        st.markdown('<div class="cc">', unsafe_allow_html=True)
        st.plotly_chart(tree, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.markdown(
        '<div class="cc-title" style="margin-bottom:10px">Biggest Single Spends</div>',
        unsafe_allow_html=True)
    top3 = (exp_df.nsmallest(3, "Amount")
            [["Date", "Description", "Amount", "Category"]]
            .reset_index(drop=True))
    for _, row in top3.iterrows():
        st.markdown(f"""
        <div class="txn">
          <div class="txn-amt">{fmt(abs(row['Amount']), sym)}</div>
          <div class="txn-desc">{row['Description']}</div>
          <div class="txn-meta">{row['Date'].strftime('%d %b %Y')} &nbsp;·&nbsp; {row['Category']}</div>
        </div>""", unsafe_allow_html=True)

    subs_df = (
        exp_df[exp_df["Category"].isin(["Subscriptions", "Streaming"])]
        .groupby("Description", as_index=False)["Amount"]
        .apply(lambda x: x.abs().sum())
        .sort_values("Amount", ascending=False)
        .reset_index(drop=True)
    )
    if not subs_df.empty:
        st.markdown(
            '<div class="cc-title" style="margin:16px 0 10px">Subscriptions</div>',
            unsafe_allow_html=True)
        rows = "".join(
            f'<div class="sub-row">'
            f'<div class="sub-name">{r["Description"]}</div>'
            f'<div class="sub-amt">{fmt(r["Amount"], sym)}</div>'
            f'</div>'
            for _, r in subs_df.iterrows()
        )
        st.markdown(
            f'<div style="background:#fff;border-radius:18px;padding:16px 20px;'
            f'border:1px solid #e8e0d6;box-shadow:0 1px 4px rgba(42,28,14,.05)">'
            f'{rows}'
            f'<div style="display:flex;justify-content:space-between;padding:10px 0 2px;'
            f'font-weight:700;font-size:13px;color:#8c7c6c">'
            f'<span>Total</span>'
            f'<span class="sub-amt">{fmt(sub_total, sym)}</span>'
            f'</div></div>',
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  PATTERNS — Day of Week  +  Savings Rate Trend
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">📅 Spending Patterns</p>', unsafe_allow_html=True)
p1, p2 = st.columns(2)

with p1:
    dow = (
        exp_df.groupby("DOW", as_index=True)["Amount"]
        .apply(lambda x: x.abs().sum())
        .reindex(DAY_ORDER, fill_value=0)
        .reset_index()
    )
    dow.columns = ["DOW", "Amount"]
    peak = dow.loc[dow["Amount"].idxmax(), "DOW"]

    fig_dow = go.Figure(go.Bar(
        x=dow["DOW"], y=dow["Amount"],
        marker_color=["#e06d35" if d == peak else "#d4c4b4" for d in dow["DOW"]],
        marker_line_width=0,
        text=[f"{sym}{v:,.0f}" for v in dow["Amount"]],
        textposition="outside",
        textfont={"size": 10},
    ))
    fig_dow.update_layout(
        **base_layout(h=320),
        xaxis={**xax(), "tickfont": {"size": 12}},
        yaxis={**yax(), "tickprefix": sym},
        annotations=[dict(
            text=f"Most spending on <b>{peak}s</b>",
            x=0.01, y=1.06, xref="paper", yref="paper", showarrow=False,
            font={"size": 12, "color": "#8c7c6c", "family": "'DM Sans',sans-serif"},
        )],
    )
    st.markdown(
        '<div class="cc"><div class="cc-title">When Do You Spend?</div>',
        unsafe_allow_html=True)
    st.plotly_chart(fig_dow, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with p2:
    sr_series = _month_savings_rate(df)
    sr_df     = sr_series.reset_index()
    sr_df.columns = ["Month", "SR"]
    sr_df["Color"] = sr_df["SR"].apply(
        lambda v: "#1a9e75" if v >= 20 else "#e09a2e" if v >= 10 else "#d94838"
    )

    fig_sr = go.Figure()
    fig_sr.add_hline(y=20, line_dash="dot", line_color="#c0d8c0", line_width=1.5,
                     annotation_text="20% goal", annotation_position="right",
                     annotation_font={"size": 10, "color": "#8ca88c"})
    fig_sr.add_trace(go.Scatter(
        x=sr_df["Month"], y=sr_df["SR"],
        mode="lines+markers+text",
        line=dict(color="#5b7cf0", width=2.5),
        marker=dict(size=10, color=sr_df["Color"], line=dict(color="#fff", width=2)),
        text=[f"{v:.0f}%" for v in sr_df["SR"]],
        textposition="top center",
        textfont={"size": 10, "family": "'DM Sans',sans-serif"},
        fill="tozeroy", fillcolor="rgba(91,124,240,.07)",
    ))
    fig_sr.update_layout(
        **base_layout(h=320),
        xaxis={**xax(), "tickfont": {"size": 11}},
        yaxis={**yax(), "ticksuffix": "%"},
    )
    st.markdown(
        '<div class="cc"><div class="cc-title">Savings Rate Over Time</div>',
        unsafe_allow_html=True)
    st.plotly_chart(fig_sr, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  INSIGHTS  +  ACTIONS  +  AI COACH  (tabbed)
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">💡 Insights & Actions</p>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["📖 What happened", "🚀 What to do", "✦ AI Coach"])

with tab1:
    story = [
        f"You earned <b>{fmt(total_income,sym)}</b> and spent <b>{fmt(total_expense,sym)}</b>. "
        + (f"You came out <b>{fmt(net,sym)} ahead</b>." if net >= 0
           else f"You overspent by <b>{fmt(abs(net),sym)}</b>."),
    ]
    if not exp_summary.empty:
        t   = exp_summary.iloc[0]
        pct = t["Total"] / total_expense * 100 if total_expense > 0 else 0
        story.append(
            f"<b>{t['Category']}</b> was your biggest cost at {fmt(t['Total'],sym)} ({pct:.0f}% of all spending)."
        )
    story.append(
        f"<b>{flex_pct:.0f}%</b> of your expenses are flexible ({fmt(flex_total,sym)}) — "
        f"that's what's actually cuttable. The remaining {100-flex_pct:.0f}% ({fmt(fixed_total,sym)}) are fixed bills."
    )
    if sub_total > 0:
        story.append(f"Subscriptions and streaming cost <b>{fmt(sub_total,sym)}</b> this period.")
    if savings_rate >= 20:
        story.append(
            f"Your savings rate of <b>{savings_rate:.1f}%</b> is excellent — you're genuinely building a cushion."
        )
    elif savings_rate < 10 and total_income > 0:
        story.append(
            f"A savings rate of <b>{savings_rate:.1f}%</b> is below the 10–20% target. "
            "Even small automated transfers help build the habit."
        )
    ca, cb = st.columns(2)
    for i, item in enumerate(story):
        (ca if i % 2 == 0 else cb).markdown(
            f'<div class="ins">{item}</div>', unsafe_allow_html=True
        )

with tab2:
    actions = []
    if net < 0:
        actions.append(("🔴", "Spending exceeds income",
            f"You're over by {fmt(abs(net),sym)}. Eating out and shopping are usually the fastest wins."))
    elif savings_rate < 10:
        actions.append(("🟡", "Boost your savings rate",
            f"At {savings_rate:.1f}% you're below the 10% floor. Automate a transfer on payday — even {fmt(50,sym)} builds the habit."))
    else:
        actions.append(("🟢", "Put your surplus to work",
            f"You're saving {savings_rate:.1f}%. A high-interest account or index fund will compound that over time."))

    if flex_pct > 40 and flex_total > 200:
        actions.append(("✂️", "Cut flexible spending",
            f"{fmt(flex_total,sym)} of your spending is discretionary. Pick two categories to reduce this month."))

    if not exp_summary.empty:
        t = exp_summary.iloc[0]
        actions.append(("📌", f"Dig into {t['Category']}",
            f"At {fmt(t['Total'],sym)} this is your biggest category — one focused review here has the most leverage."))

    if sub_total > 80:
        actions.append(("📺", "Review subscriptions",
            f"You're paying {fmt(sub_total,sym)}. Cancel anything you haven't actively used this month."))

    actions.append(("📅", "Upload next month",
        "Month-over-month tracking is the single most effective financial habit you can build."))

    ca, cb = st.columns(2)
    for i, (em, ti, de) in enumerate(actions[:4]):
        (ca if i % 2 == 0 else cb).markdown(f"""
        <div class="act">
          <div class="act-n">{i+1}</div>
          <div>
            <div class="act-t">{em} {ti}</div>
            <div class="act-d">{de}</div>
          </div>
        </div>""", unsafe_allow_html=True)

with tab3:
    ai_text = None
    if run_ai:
        k = api_to_use
        if k:
            tc = exp_summary.iloc[0]["Category"] if not exp_summary.empty else "N/A"
            ta = fmt(exp_summary.iloc[0]["Total"], sym) if not exp_summary.empty else "N/A"
            with st.spinner("Thinking…"):
                ai_text = ai_coach_call(k, (
                    f"Income: {fmt(total_income,sym)}\n"
                    f"Expenses: {fmt(total_expense,sym)}\n"
                    f"Net: {fmt(net,sym,signed=True)}\n"
                    f"Savings Rate: {savings_rate:.1f}%\n"
                    f"Health Score: {health_score}/100 ({s_label})\n"
                    f"Biggest expense: {tc} ({ta})\n"
                    f"Fixed bills: {fmt(fixed_total,sym)}\n"
                    f"Flexible spend: {fmt(flex_total,sym)}\n"
                    f"Subscriptions: {fmt(sub_total,sym)}\n"
                    f"Avg daily spend: {fmt(avg_daily,sym)}"
                ))
            if not ai_text:
                st.warning("Couldn't reach the AI. Check your API key and internet connection.")
        else:
            st.info("Add your Anthropic API key in the sidebar to unlock AI coaching.")

    if ai_text:
        st.markdown(
            f'<div style="background:linear-gradient(140deg,#f5f2ff,#f0f8ff);'
            f'border:1px solid #d8d0f4;border-radius:18px;padding:22px 24px">'
            f'<div style="background:#ece6fd;color:#5738c8;font-size:10px;font-weight:800;'
            f'text-transform:uppercase;letter-spacing:.1em;padding:3px 10px;border-radius:99px;'
            f'margin-bottom:12px;display:inline-block">✦ Claude AI</div>'
            f'<div style="font-size:14px;color:#1a1008;line-height:1.8;white-space:pre-line">'
            f'{ai_text}</div></div>',
            unsafe_allow_html=True)
    elif not run_ai:
        st.markdown(
            '<div style="padding:28px;text-align:center;color:#b8a898;font-size:14px">'
            'Enter your Anthropic API key in the sidebar and click '
            '<b>Generate Insights</b> for personalised coaching.</div>',
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  TRANSACTION TABLE
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">🔎 Transaction Explorer</p>', unsafe_allow_html=True)

disp = fdf[["Date","Description","Amount","Category","Type","Month"]].copy()
disp["Date"] = disp["Date"].dt.strftime("%d %b %Y")
disp = disp.sort_values("Date", ascending=False).reset_index(drop=True)

st.dataframe(
    disp, use_container_width=True, height=420,
    column_config={
        "Amount":   st.column_config.NumberColumn("Amount", format=f"{sym}%.2f"),
        "Category": st.column_config.TextColumn("Category"),
        "Type":     st.column_config.TextColumn("Type"),
    },
)

st.markdown("""
<div class="disclaimer">
  Money Health Agent is for personal education and spending awareness only.
  It does not constitute financial, tax, investment, or credit advice.
  Consult a licensed financial adviser for professional guidance.
</div>
""", unsafe_allow_html=True)
