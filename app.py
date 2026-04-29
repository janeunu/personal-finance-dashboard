import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import io
import os

st.set_page_config(
    page_title="Money Health Agent",
    page_icon="💰",
    layout="wide"
)

# ══════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════
CATEGORY_COLORS = [
    "#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626",
    "#0891b2", "#db2777", "#65a30d", "#ea580c", "#6366f1",
    "#0d9488", "#9333ea",
]

BUDGET_GUIDE = {           # recommended % of income
    "Rent":          30,
    "Groceries":     12,
    "Eating Out":     5,
    "Transport":      5,
    "Subscriptions":  3,
    "Shopping":       5,
    "Health":         5,
    "Utilities":      6,
}

# ══════════════════════════════════════════════════════════
#  STYLES
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stAppViewContainer"] { background: #f0f4f8; }
[data-testid="stSidebar"]          { background: #0f172a !important; }
[data-testid="stSidebar"] *        { color: #e2e8f0 !important; }
[data-testid="stSidebar"] label    { color:#94a3b8 !important; font-size:11px !important;
                                     text-transform:uppercase; letter-spacing:.06em; }

.block-container { padding-top:1.4rem; padding-bottom:3rem; max-width:1440px; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
    padding: 38px 44px; border-radius: 24px; color: white;
    margin-bottom: 22px; position: relative; overflow: hidden;
}
.hero::before {
    content:""; position:absolute; top:-80px; right:-80px;
    width:320px; height:320px; border-radius:50%;
    background:rgba(255,255,255,.05);
}
.hero::after {
    content:""; position:absolute; bottom:-40px; right:160px;
    width:180px; height:180px; border-radius:50%;
    background:rgba(255,255,255,.03);
}
.hero h1  { font-size:36px; font-weight:800; margin:0 0 6px; }
.hero p   { font-size:15px; color:#bfdbfe; margin:0 0 4px; }
.hero-tag {
    display:inline-block; background:rgba(255,255,255,.12);
    border:1px solid rgba(255,255,255,.2); color:#e0f2fe;
    padding:4px 14px; border-radius:99px; font-size:12px;
    font-weight:600; margin-top:12px;
}

/* ── Cards ── */
.card {
    background:#fff; padding:22px; border-radius:20px;
    border:1px solid #e5e7eb;
    box-shadow:0 2px 8px rgba(0,0,0,.05);
    margin-bottom:14px;
}
.kpi-card {
    background:#fff; padding:20px 22px; border-radius:18px;
    border:1px solid #e5e7eb;
    box-shadow:0 2px 8px rgba(0,0,0,.05); margin-bottom:14px;
}
.kpi-label { color:#6b7280; font-size:11px; font-weight:600;
             text-transform:uppercase; letter-spacing:.06em; margin-bottom:4px; }
.kpi-value { color:#111827; font-size:28px; font-weight:800; line-height:1.1; }
.kpi-delta { font-size:12px; margin-top:5px; }
.delta-up   { color:#059669; font-weight:600; }
.delta-down { color:#dc2626; font-weight:600; }
.delta-neu  { color:#9ca3af; }

/* ── Section headers ── */
.sh { font-size:17px; font-weight:700; color:#111827; margin:4px 0 14px; }

/* ── Score badge ── */
.badge {
    display:inline-block; padding:4px 14px; border-radius:99px;
    font-size:13px; font-weight:700; margin-top:2px;
}
.badge-excellent { background:#d1fae5; color:#065f46; }
.badge-healthy   { background:#dbeafe; color:#1e40af; }
.badge-attention { background:#fef3c7; color:#92400e; }
.badge-risk      { background:#fee2e2; color:#991b1b; }

/* ── Insight / Action cards ── */
.insight-card {
    background:#f8fafc; padding:14px 16px; border-radius:14px;
    border-left:4px solid #2563eb; margin-bottom:10px;
    font-size:14px; color:#1e293b; line-height:1.6;
}
.action-card {
    background:#fff; padding:14px 16px; border-radius:14px;
    border:1px solid #e5e7eb; border-left:4px solid #7c3aed;
    margin-bottom:10px; box-shadow:0 1px 4px rgba(0,0,0,.04);
}
.action-num {
    background:#7c3aed; color:#fff; width:22px; height:22px;
    border-radius:50%; display:inline-flex;
    align-items:center; justify-content:center;
    font-size:11px; font-weight:800; margin-right:8px;
}

/* ── Budget bars ── */
.brow { margin-bottom:13px; }
.blabel { display:flex; justify-content:space-between;
          font-size:13px; color:#374151; margin-bottom:4px; }
.bbar-bg  { background:#e5e7eb; border-radius:99px; height:7px; overflow:hidden; }
.bbar-fill{ height:100%; border-radius:99px; }

/* ── AI panel ── */
.ai-card {
    background:linear-gradient(135deg,#f0f4ff,#faf5ff);
    border:1px solid #c7d2fe; padding:20px;
    border-radius:18px; margin-bottom:10px;
}
.ai-tag {
    background:#e0e7ff; color:#4338ca; font-size:10px;
    font-weight:800; text-transform:uppercase; letter-spacing:.1em;
    padding:3px 10px; border-radius:99px; margin-bottom:12px;
    display:inline-block;
}

/* ── Privacy / Disclaimer ── */
.privacy {
    background:#ecfdf5; border:1px solid #a7f3d0;
    padding:12px 16px; border-radius:14px;
    margin-bottom:20px; font-size:13px; color:#065f46;
}
.disclaimer {
    background:#f8fafc; border:1px solid #e2e8f0;
    padding:12px 16px; border-radius:10px;
    font-size:11px; color:#9ca3af; text-align:center; margin-top:24px;
}

/* ── Onboarding tiles ── */
.onboard {
    text-align:center; padding:32px 20px;
}
.onboard .icon { font-size:38px; margin-bottom:10px; }
.onboard .title{ font-weight:700; font-size:16px; margin-bottom:6px; }
.onboard .desc { color:#6b7280; font-size:13px; line-height:1.5; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════
def money(v, signed=False):
    if signed:
        return f"+${v:,.2f}" if v >= 0 else f"-${abs(v):,.2f}"
    return f"${v:,.2f}"


def delta_html(curr, prev, invert=False):
    if prev == 0:
        return '<span class="delta-neu">—</span>'
    d = (curr - prev) / abs(prev) * 100
    if invert:
        cls = "delta-down" if d > 0 else "delta-up"
        arrow = "▲" if d > 0 else "▼"
    else:
        cls = "delta-up" if d > 0 else "delta-down"
        arrow = "▲" if d > 0 else "▼"
    return f'<span class="{cls}">{arrow} {abs(d):.1f}% vs prev period</span>'


@st.cache_data
def load_rules():
    path = os.path.join(os.path.dirname(__file__), "category_rules.csv")
    rules = pd.read_csv(path)
    rules["keyword"] = rules["keyword"].astype(str).str.lower().str.strip()
    return rules


def categorise(description, amount, rules):
    desc = str(description).lower()
    for _, r in rules.iterrows():
        if r["keyword"] in desc:
            return r["category"], r["type"]
    return ("Other Income", "Income") if amount > 0 else ("Other Expense", "Expense")


def score_color(s):
    return "#059669" if s >= 80 else "#2563eb" if s >= 65 else "#d97706" if s >= 45 else "#dc2626"


def score_meta(s):
    if s >= 80: return "Excellent",   "badge-excellent"
    if s >= 65: return "Healthy",     "badge-healthy"
    if s >= 45: return "Needs Attention", "badge-attention"
    return "At Risk", "badge-risk"


def calc_score(income, expense, net, savings_rate, sub_total):
    s = 0
    if income > 0:    s += 20
    if net > 0:       s += 25
    if savings_rate >= 20: s += 25
    elif savings_rate >= 10: s += 15
    elif savings_rate > 0:   s += 8
    ratio = expense / income if income > 0 else 1
    if ratio <= 0.75: s += 15
    elif ratio <= 0.90: s += 8
    sub_r = sub_total / income if income > 0 else 0
    if sub_r <= 0.03: s += 15
    elif sub_r <= 0.06: s += 8
    return min(s, 100)


def get_ai_insights(api_key: str, summary: str) -> str | None:
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 600,
                "messages": [{
                    "role": "user",
                    "content": (
                        "You are a friendly, plain-English personal finance coach helping everyday people — "
                        "not finance experts — understand their money.\n\n"
                        "Based on the financial summary below, write exactly 4 short, specific, actionable insights. "
                        "Rules:\n"
                        "- Each starts with a relevant emoji\n"
                        "- 1–2 sentences max in simple language\n"
                        "- Reference actual dollar amounts or percentages where helpful\n"
                        "- Be encouraging but honest\n"
                        "- No intro sentence, no outro — just the 4 bullet points\n\n"
                        f"Financial Summary:\n{summary}"
                    ),
                }],
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"]
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════
#  HERO
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="hero">
  <h1>💰 Money Health Agent</h1>
  <p>Upload your bank statement and instantly see where your money goes,
     how healthy your finances are, and exactly what to do next.</p>
  <p style="color:#93c5fd;font-size:13px">Built for everyday people — no finance background needed.</p>
  <span class="hero-tag">✨ Powered by AI insights</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="privacy">
  🔒 <b>Your data stays private.</b> Your file is processed only within your browser session —
  never stored, never shared. This tool is for personal education and tracking, not financial advice.
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════
uploaded_file = st.file_uploader(
    "Upload your bank statement (CSV)",
    type=["csv"],
    help="CSV must have columns: Date, Description, Amount",
)

if uploaded_file is None:
    c1, c2, c3 = st.columns(3)
    tiles = [
        ("📂", "Upload Your CSV", "Export a CSV from your bank's app or internet banking portal."),
        ("⚡", "Instant Categorisation", "Every transaction is labelled in seconds — groceries, rent, transport, and more."),
        ("🎯", "Actionable Insights", "Get a plain-English summary and personalised steps to improve your finances."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3], tiles):
        with col:
            st.markdown(f"""
            <div class="card onboard">
              <div class="icon">{icon}</div>
              <div class="title">{title}</div>
              <div class="desc">{desc}</div>
            </div>""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════
#  LOAD & CLEAN DATA
# ══════════════════════════════════════════════════════════
rules = load_rules()

try:
    raw = uploaded_file.read()
    df  = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
except Exception:
    st.error("Could not read your file. Please make sure it is a valid UTF-8 CSV.")
    st.stop()

df.columns = df.columns.str.strip()

# Flexible column detection
col_map = {}
for col in df.columns:
    cl = col.lower().strip()
    if cl in ["date", "transaction date", "trans date", "value date", "posting date"]:
        col_map["Date"] = col
    elif cl in ["description", "details", "narration", "narrative", "memo", "reference", "particulars"]:
        col_map["Description"] = col
    elif cl in ["amount", "debit/credit", "value", "net amount", "transaction amount"]:
        col_map["Amount"] = col

if len(col_map) < 3:
    st.error(
        f"Couldn't detect required columns. Need: **Date, Description, Amount**. "
        f"Your columns: {df.columns.tolist()}"
    )
    st.stop()

df = df.rename(columns={v: k for k, v in col_map.items()})
keep = ["Date", "Description", "Amount"]
extra = [c for c in df.columns if c not in keep]
df = df[keep + extra]

df["Date"]   = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
df["Amount"] = (
    df["Amount"].astype(str)
    .str.replace(r"[\$,\s]",    "",    regex=True)
    .str.replace(r"\((.+?)\)", r"-\1", regex=True)
    .pipe(pd.to_numeric, errors="coerce")
)
df = df.dropna(subset=["Date", "Amount"]).sort_values("Date")

df[["Category", "Type"]] = df.apply(
    lambda r: pd.Series(categorise(r["Description"], r["Amount"], rules)), axis=1
)
df["Month"] = df["Date"].dt.to_period("M").astype(str)
df["Day"]   = df["Date"].dt.date


# ══════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔍 Filters")
    month_opts = ["All"] + sorted(df["Month"].unique())
    sel_month  = st.selectbox("Month", month_opts)

    cat_opts  = ["All"] + sorted(df["Category"].unique())
    sel_cat   = st.selectbox("Category", cat_opts)

    st.markdown("---")
    st.markdown("### ✨ AI Insights (optional)")
    api_key_input = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get a key at console.anthropic.com. Never stored.",
    )
    run_ai = st.button("Generate AI Insights", use_container_width=True)

    st.markdown("---")
    st.markdown("### 📥 Export")
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Categorised CSV",
        data=csv_bytes,
        file_name="money_health_categorised.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ══════════════════════════════════════════════════════════
#  FILTER
# ══════════════════════════════════════════════════════════
fdf = df.copy()
if sel_month != "All": fdf = fdf[fdf["Month"] == sel_month]
if sel_cat   != "All": fdf = fdf[fdf["Category"] == sel_cat]

inc_df = fdf[fdf["Type"] == "Income"]
exp_df = fdf[fdf["Type"] == "Expense"]

total_income  = inc_df["Amount"].sum()
total_expense = abs(exp_df["Amount"].sum())
net           = total_income - total_expense
savings_rate  = (net / total_income * 100) if total_income > 0 else 0

exp_summary = (
    exp_df.groupby("Category")["Amount"].sum().abs()
    .reset_index().rename(columns={"Amount": "Total"})
    .sort_values("Total", ascending=False)
)
sub_total    = exp_df[exp_df["Category"].isin(["Subscription", "Subscriptions"])]["Amount"].abs().sum()
health_score = calc_score(total_income, total_expense, net, savings_rate, sub_total)
s_label, s_class = score_meta(health_score)

# Previous period for deltas
all_months = sorted(df["Month"].unique())
if sel_month != "All" and sel_month in all_months:
    idx  = all_months.index(sel_month)
    prev = df[df["Month"] == all_months[idx - 1]] if idx > 0 else pd.DataFrame()
else:
    prev = pd.DataFrame()

prev_inc = prev[prev["Type"] == "Income"]["Amount"].sum() if not prev.empty else 0
prev_exp = abs(prev[prev["Type"] == "Expense"]["Amount"].sum()) if not prev.empty else 0
prev_net = prev_inc - prev_exp


# ══════════════════════════════════════════════════════════
#  ROW 1 — KPI CARDS
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sh">📊 Financial Overview</p>', unsafe_allow_html=True)
c0, c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1, 1])

with c0:
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_score,
        domain={"x": [0, 1], "y": [0, 1]},
        number={"suffix": "/100", "font": {"size": 28, "color": "#111827", "family": "Inter"}},
        gauge={
            "axis": {"range": [0, 100], "tickfont": {"size": 9}, "tickwidth": 1, "tickcolor": "#d1d5db"},
            "bar":  {"color": score_color(health_score), "thickness": 0.28},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 45],   "color": "#fef2f2"},
                {"range": [45, 65],  "color": "#fffbeb"},
                {"range": [65, 80],  "color": "#eff6ff"},
                {"range": [80, 100], "color": "#f0fdf4"},
            ],
        }
    ))
    gauge.update_layout(
        height=170, margin=dict(t=16, b=6, l=14, r=14),
        paper_bgcolor="white", font={"family": "Inter"},
    )
    st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label">Money Health Score</div>', unsafe_allow_html=True)
    st.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f'<span class="badge {s_class}">{s_label}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">💵 Total Income</div>
      <div class="kpi-value" style="color:#059669">{money(total_income)}</div>
      <div class="kpi-delta">{delta_html(total_income, prev_inc)}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">💸 Total Expenses</div>
      <div class="kpi-value" style="color:#dc2626">{money(total_expense)}</div>
      <div class="kpi-delta">{delta_html(total_expense, prev_exp, invert=True)}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    nc = "#059669" if net >= 0 else "#dc2626"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">🏦 Money Left</div>
      <div class="kpi-value" style="color:{nc}">{money(net, signed=True)}</div>
      <div class="kpi-delta">{delta_html(net, prev_net)}</div>
    </div>""", unsafe_allow_html=True)

with c4:
    src = "#059669" if savings_rate >= 20 else "#d97706" if savings_rate >= 10 else "#dc2626"
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-label">🎯 Savings Rate</div>
      <div class="kpi-value" style="color:{src}">{savings_rate:.1f}%</div>
      <div class="kpi-delta"><span class="delta-neu">Target ≥ 20%</span></div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  ROW 2 — TREND + DONUT
# ══════════════════════════════════════════════════════════
st.markdown("---")
left, right = st.columns([1.45, 1])

with left:
    st.markdown('<p class="sh">📈 Income vs Expenses Over Time</p>', unsafe_allow_html=True)
    monthly = df.groupby(["Month", "Type"])["Amount"].sum().reset_index()
    monthly["Display"] = monthly.apply(
        lambda r: abs(r["Amount"]) if r["Type"] == "Expense" else r["Amount"], axis=1
    )
    fig_bar = px.bar(
        monthly, x="Month", y="Display", color="Type",
        barmode="group", text_auto=".2s",
        color_discrete_map={"Income": "#059669", "Expense": "#ef4444"},
    )
    fig_bar.update_traces(textfont_size=10, textposition="outside", marker_line_width=0, opacity=.88)
    fig_bar.update_layout(
        height=370, legend_title="",
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=16, b=40, l=0, r=0),
        font={"family": "Inter"},
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6", title=""),
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

with right:
    st.markdown('<p class="sh">🍩 Spending by Category</p>', unsafe_allow_html=True)
    if not exp_summary.empty:
        fig_pie = px.pie(
            exp_summary, names="Category", values="Total",
            hole=.5, color_discrete_sequence=CATEGORY_COLORS,
        )
        fig_pie.update_traces(
            textposition="inside", textinfo="percent+label",
            textfont_size=11, pull=[.03] * len(exp_summary),
        )
        fig_pie.update_layout(
            height=370, showlegend=False,
            paper_bgcolor="white",
            margin=dict(t=16, b=16, l=0, r=0),
            font={"family": "Inter"},
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No expense data to display.")


# ══════════════════════════════════════════════════════════
#  ROW 3 — TOP SPENDING + BUDGET CHECK
# ══════════════════════════════════════════════════════════
left2, right2 = st.columns([1, 1])

with left2:
    st.markdown('<p class="sh">🔝 Top Spending Categories</p>', unsafe_allow_html=True)
    if not exp_summary.empty:
        fig_h = px.bar(
            exp_summary.head(8), x="Total", y="Category",
            orientation="h", text_auto=".2s",
            color="Total", color_continuous_scale=["#dbeafe", "#1e40af"],
        )
        fig_h.update_traces(textfont_size=10, textposition="outside", marker_line_width=0)
        fig_h.update_layout(
            height=370, coloraxis_showscale=False,
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(t=10, b=10, l=0, r=50),
            font={"family": "Inter"},
            xaxis=dict(showgrid=True, gridcolor="#f3f4f6", title=""),
            yaxis=dict(categoryorder="total ascending", title=""),
        )
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

with right2:
    st.markdown('<p class="sh">📋 Budget Health Check</p>', unsafe_allow_html=True)
    html_rows = ""
    for cat, rec_pct in BUDGET_GUIDE.items():
        actual = float(exp_summary[exp_summary["Category"] == cat]["Total"].sum())
        act_pct = (actual / total_income * 100) if total_income > 0 else 0
        bar_w   = min(act_pct / rec_pct * 100, 100) if rec_pct > 0 else 0
        if act_pct > rec_pct:
            color   = "#ef4444"
            status  = f"<span style='color:#dc2626;font-size:11px'>⚠ Over ({act_pct:.0f}% / rec {rec_pct}%)</span>"
        elif act_pct > rec_pct * 0.8:
            color   = "#f59e0b"
            status  = f"<span style='color:#d97706;font-size:11px'>⚡ Near limit ({act_pct:.0f}% / rec {rec_pct}%)</span>"
        else:
            color   = "#10b981"
            status  = f"<span style='color:#059669;font-size:11px'>✓ On track ({act_pct:.0f}% / rec {rec_pct}%)</span>"

        html_rows += f"""
        <div class="brow">
          <div class="blabel">
            <span><b>{cat}</b> &mdash; {money(actual)}</span>{status}
          </div>
          <div class="bbar-bg">
            <div class="bbar-fill" style="width:{bar_w:.1f}%;background:{color}"></div>
          </div>
        </div>"""
    st.markdown(f'<div class="card">{html_rows}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  ROW 4 — INSIGHTS + ACTIONS
# ══════════════════════════════════════════════════════════
st.markdown("---")
left3, right3 = st.columns([1, 1])

with left3:
    st.markdown('<p class="sh">💡 Plain-English Insights</p>', unsafe_allow_html=True)

    ai_text = None
    if run_ai:
        key = api_key_input.strip() or os.environ.get("ANTHROPIC_API_KEY", "")
        if key:
            top_cat = exp_summary.iloc[0]["Category"] if not exp_summary.empty else "N/A"
            top_amt = money(exp_summary.iloc[0]["Total"]) if not exp_summary.empty else "N/A"
            summary = (
                f"- Total Income:         {money(total_income)}\n"
                f"- Total Expenses:       {money(total_expense)}\n"
                f"- Net Cashflow:         {money(net, signed=True)}\n"
                f"- Savings Rate:         {savings_rate:.1f}%\n"
                f"- Health Score:         {health_score}/100 ({s_label})\n"
                f"- Largest Expense:      {top_cat} ({top_amt})\n"
                f"- Subscriptions Total:  {money(sub_total)}\n"
                f"- Transactions:         {len(fdf)}\n"
            )
            with st.spinner("Generating AI insights…"):
                ai_text = get_ai_insights(key, summary)
            if ai_text is None:
                st.warning("AI insights unavailable — check your API key and connection.")
        else:
            st.warning("Enter your Anthropic API key in the sidebar to use AI insights.")

    if ai_text:
        st.markdown(f"""
        <div class="ai-card">
          <span class="ai-tag">✨ Claude AI</span>
          <div style="font-size:14px;color:#1e293b;line-height:1.75;white-space:pre-line">{ai_text}</div>
        </div>""", unsafe_allow_html=True)
    else:
        # Rule-based fallback insights
        insights = [
            f"You earned <b>{money(total_income)}</b> and spent <b>{money(total_expense)}</b> in this period.",
        ]
        if net >= 0:
            insights.append(f"You had <b>{money(net)}</b> left over — great work keeping expenses below income!")
        else:
            insights.append(f"You overspent by <b>{money(abs(net))}</b>. Focus on cutting flexible spending first.")

        if not exp_summary.empty:
            top = exp_summary.iloc[0]
            pct = top["Total"] / total_expense * 100 if total_expense > 0 else 0
            insights.append(f"<b>{top['Category']}</b> is your largest cost at {money(top['Total'])} — {pct:.0f}% of total expenses.")

        if sub_total > 0:
            insights.append(f"Subscriptions are costing you <b>{money(sub_total)}</b>. Are you using all of them?")

        if savings_rate >= 20:
            insights.append(f"Your savings rate of <b>{savings_rate:.1f}%</b> is excellent — consider investing the surplus.")
        elif savings_rate < 10 and total_income > 0:
            insights.append(f"A savings rate of <b>{savings_rate:.1f}%</b> is below the 10–20% target. Small cuts add up fast.")

        for ins in insights:
            st.markdown(f'<div class="insight-card">{ins}</div>', unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:12px;color:#9ca3af;margin-top:6px">'
            '💡 Add your Anthropic API key in the sidebar for personalised AI coaching.</div>',
            unsafe_allow_html=True,
        )

with right3:
    st.markdown('<p class="sh">🚀 Next Best Actions</p>', unsafe_allow_html=True)

    actions: list[tuple[str, str, str]] = []

    if net < 0:
        actions.append(("🔴", "Spending exceeds income",
                        f"Cut discretionary spend — you're over budget by {money(abs(net))} this period."))
    elif savings_rate < 10:
        actions.append(("🟡", "Boost your savings rate",
                        f"At {savings_rate:.1f}% you're below the 10% floor. Try auto-transferring a fixed amount on payday."))
    else:
        actions.append(("🟢", "Great cashflow — invest the surplus",
                        f"You're saving {savings_rate:.1f}%. Consider a high-interest account or index fund for the extra."))

    if not exp_summary.empty:
        t = exp_summary.iloc[0]
        actions.append(("📌", f"Review {t['Category']}",
                        f"At {money(t['Total'])} this is your biggest category. Look for one or two easy cuts here."))

    if sub_total > 100:
        actions.append(("📺", "Audit subscriptions",
                        f"You're spending {money(sub_total)} on subscriptions. Cancel anything you haven't used in 30 days."))

    if savings_rate >= 20 and net > 0:
        actions.append(("📈", "Start investing",
                        "You have healthy cashflow. Even $50/week in an index fund compounds significantly over time."))

    actions.append(("📅", "Track next month",
                    "Upload next month's statement to see your progress and catch bad habits early."))

    for i, (emoji, title, desc) in enumerate(actions[:4], 1):
        st.markdown(f"""
        <div class="action-card">
          <span class="action-num">{i}</span><b>{emoji} {title}</b><br>
          <span style="font-size:13px;color:#4b5563;margin-left:30px;display:block;margin-top:4px">{desc}</span>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  ROW 5 — DAILY SPENDING TREND
# ══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<p class="sh">📉 Daily Spending Trend</p>', unsafe_allow_html=True)

daily = (
    exp_df.groupby("Day")["Amount"].sum().abs()
    .reset_index().rename(columns={"Amount": "Spent"})
)
daily["Day"] = pd.to_datetime(daily["Day"])

if not daily.empty:
    fig_area = px.area(daily, x="Day", y="Spent", color_discrete_sequence=["#2563eb"])
    fig_area.update_traces(
        fill="tozeroy", fillcolor="rgba(37,99,235,.08)",
        line=dict(color="#2563eb", width=2),
    )
    fig_area.update_layout(
        height=240, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=10, b=30, l=0, r=0),
        font={"family": "Inter"},
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6", title="Daily Spend ($)"),
    )
    st.plotly_chart(fig_area, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No daily expense data available for the selected filters.")


# ══════════════════════════════════════════════════════════
#  ROW 6 — RECURRING BILLS
# ══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<p class="sh">🔁 Bills & Recurring Costs</p>', unsafe_allow_html=True)

RECURRING_CATS = ["Rent", "Subscriptions", "Subscription", "Utilities", "Insurance",
                  "Childcare", "Phone", "Internet", "Fuel"]
fixed_df = exp_df[exp_df["Category"].isin(RECURRING_CATS)]

if not fixed_df.empty:
    fixed_sum = (
        fixed_df.groupby("Category")["Amount"].sum().abs()
        .reset_index().sort_values("Amount", ascending=False)
    )
    fig_rec = px.bar(
        fixed_sum, x="Category", y="Amount",
        text_auto=".2s", color_discrete_sequence=["#7c3aed"],
    )
    fig_rec.update_traces(textfont_size=10, textposition="outside", marker_line_width=0, opacity=.85)
    fig_rec.update_layout(
        height=300, paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=16, b=30, l=0, r=0),
        font={"family": "Inter"},
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#f3f4f6", title="Amount ($)"),
    )
    st.plotly_chart(fig_rec, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No recurring costs detected for this period.")


# ══════════════════════════════════════════════════════════
#  ROW 7 — TRANSACTION TABLE
# ══════════════════════════════════════════════════════════
st.markdown("---")
st.markdown('<p class="sh">🔎 Transaction Explorer</p>', unsafe_allow_html=True)

disp = fdf[["Date", "Description", "Amount", "Category", "Type", "Month"]].copy()
disp["Date"] = disp["Date"].dt.strftime("%d %b %Y")
disp = disp.sort_values("Date", ascending=False)

st.dataframe(
    disp,
    use_container_width=True,
    height=420,
    column_config={
        "Amount":   st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
        "Category": st.column_config.TextColumn("Category"),
        "Type":     st.column_config.TextColumn("Type"),
    },
)

# ══════════════════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="disclaimer">
  ⚠️ <b>Disclaimer:</b> Money Health Agent is for personal education and spending awareness only.
  It does not constitute financial, tax, investment, or credit advice.
  Consult a licensed financial adviser for professional guidance.
</div>
""", unsafe_allow_html=True)
