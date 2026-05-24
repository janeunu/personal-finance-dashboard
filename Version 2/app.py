
import streamlit as st
import pandas as pd
import plotly.express as px


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Money Health Agent",
    page_icon="💰",
    layout="wide"
)


# ============================================================
# DESIGN SYSTEM — V7 WARM PREMIUM THEME
# UI-only change. No backend logic changed.
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --page-bg: #F5F1E8;
        --card-bg: #FFFCF5;
        --card-bg-2: #F8F2E7;
        --border: #E7DDCC;
        --border-soft: #EFE6D6;
        --shadow: 0 8px 24px rgba(60, 45, 25, 0.06);

        --accent: #0F9F6E;
        --accent-dark: #087A55;
        --accent-soft: #E6F5EE;

        --positive: #079455;
        --negative: #D92D20;
        --warning: #B54708;

        --text-primary: #2B2A27;
        --text-secondary: #6B6258;
        --text-muted: #9A8F82;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
        color: var(--text-primary);
    }

    .block-container {
        max-width: 100% !important;
        padding-top: 0.75rem;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-bottom: 2rem;
    }

    [data-testid="stAppViewContainer"] {
        background: var(--page-bg);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stVerticalBlock"] {
        gap: 0.45rem;
    }

    [data-testid="column"] {
        padding-left: 5px !important;
        padding-right: 5px !important;
    }

    /* Streamlit controls */
    div[data-testid="stSelectbox"] div[role="combobox"],
    div[data-testid="stTextInput"] input {
        background: var(--card-bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        min-height: 38px !important;
        color: var(--text-primary) !important;
        font-size: 12.5px !important;
        box-shadow: none !important;
    }

    div[data-testid="stFileUploaderDropzone"] {
        background: var(--card-bg) !important;
        border: 1px dashed var(--border) !important;
        border-radius: 14px !important;
        min-height: 46px !important;
        padding: 6px 12px !important;
    }

    div[data-testid="stFileUploaderDropzone"] p {
        font-size: 12px !important;
        color: var(--text-secondary) !important;
    }

    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button {
        background: var(--card-bg) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        min-height: 38px !important;
        font-size: 12.5px !important;
        font-weight: 700 !important;
        box-shadow: var(--shadow) !important;
    }

    div[data-testid="stButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        border-color: var(--accent) !important;
        color: var(--accent-dark) !important;
        background: var(--accent-soft) !important;
    }

    .top-note {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 9px 14px;
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 10px;
        box-shadow: var(--shadow);
    }

    /* Money Health Score hero — dark navy (approved design) */
    .hero {
        background: #0F172A;
        color: #F1F5F9;
        border: none;
        border-radius: 20px;
        padding: 26px 30px;
        min-height: 160px;
        display: flex;
        align-items: center;
        gap: 28px;
        box-shadow: 0 20px 40px rgba(15,23,42,0.25);
    }

    .score {
        font-size: 80px;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -4px;
        font-variant-numeric: tabular-nums;
        flex-shrink: 0;
    }

    .score-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: .13em;
        color: #64748B;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .score-title {
        font-size: 20px;
        font-weight: 700;
        line-height: 1.35;
        color: #F1F5F9;
        margin-bottom: 12px;
    }

    .score-stats {
        display: flex;
        gap: 0;
        margin-top: 4px;
    }

    .score-stat {
        padding-right: 18px;
        margin-right: 18px;
        border-right: 1px solid #1E293B;
    }

    .score-stat:last-child {
        border-right: none;
        padding-right: 0;
        margin-right: 0;
    }

    .score-stat-label {
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .1em;
        color: #475569;
        font-weight: 700;
        margin-bottom: 3px;
    }

    .score-stat-value {
        font-size: 13px;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        color: #CBD5E1;
    }

    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
    }

    .kpi {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 16px 17px;
        min-height: 92px;
        box-shadow: var(--shadow);
    }

    .kpi-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: var(--text-muted);
        font-weight: 800;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 23px;
        line-height: 1.1;
        font-weight: 800;
        color: var(--text-primary);
        font-variant-numeric: tabular-nums;
    }

    .kpi-sub {
        font-size: 11.5px;
        color: var(--text-muted);
        margin-top: 6px;
    }

    .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 18px 0 9px;
    }

    .section-dot {
        width: 5px;
        height: 18px;
        border-radius: 10px;
        background: var(--accent);
    }

    .section-text {
        font-size: 11px;
        color: var(--text-secondary);
        font-weight: 800;
        letter-spacing: .09em;
        text-transform: uppercase;
    }

    .card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 16px 18px;
        box-shadow: var(--shadow);
    }

    .mini-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        padding: 9px 0;
        border-bottom: 1px solid var(--border-soft);
    }

    .mini-row:last-child {
        border-bottom: 0;
    }

    .mini-label {
        font-size: 13px;
        font-weight: 800;
        color: var(--text-primary);
    }

    .mini-sub {
        font-size: 11.5px;
        color: var(--text-muted);
        margin-top: 2px;
    }

    .mini-value {
        font-size: 13px;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
        color: var(--text-primary);
    }

    .progress-track {
        width: 100%;
        height: 7px;
        background: #EFE6D6;
        border-radius: 999px;
        overflow: hidden;
        margin-top: 7px;
    }

    .progress-fill {
        height: 100%;
        border-radius: 999px;
        background: var(--accent);
    }

    .progress-fill.warn {
        background: var(--warning);
    }

    .progress-fill.danger {
        background: var(--negative);
    }

    .insight {
        background: #FFF8EA;
        border: 1px solid #EAD9B7;
        border-radius: 16px;
        padding: 15px 16px;
        min-height: 95px;
        box-shadow: var(--shadow);
    }

    .insight-title {
        font-size: 13.5px;
        font-weight: 800;
        color: var(--text-primary);
        margin-bottom: 6px;
    }

    .insight-body {
        font-size: 12.5px;
        color: var(--text-secondary);
        line-height: 1.55;
    }

    .good { color: var(--positive) !important; }
    .bad { color: var(--negative) !important; }
    .warn { color: var(--warning) !important; }
    .purple { color: var(--accent) !important; }

    /* Dataframe wrapper tone */
    [data-testid="stDataFrame"] {
        background: var(--card-bg) !important;
        border-radius: 18px !important;
        border: 1px solid var(--border) !important;
        box-shadow: var(--shadow) !important;
        overflow: hidden !important;
    }

    .footer {
        margin-top: 22px;
        padding-top: 14px;
        border-top: 1px solid var(--border);
        text-align: center;
        font-size: 11.5px;
        color: var(--text-muted);
    }

    /* ── Navigation pill tabs ── */
    div[data-testid="stRadio"] { margin: 6px 0 10px; }
    div[data-testid="stRadio"] > div:first-child { display: none !important; }
    div[data-testid="stRadio"] [role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        gap: 5px !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        display: inline-flex !important;
        align-items: center !important;
        border: 1px solid #E7DDCC !important;
        border-radius: 99px !important;
        padding: 5px 16px !important;
        background: #FFFCF5 !important;
        color: #6B6258 !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        margin: 0 !important;
        font-family: "Inter", sans-serif !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background: #0F9F6E !important;
        border-color: #0F9F6E !important;
        color: #FFFFFF !important;
    }

    /* ── Selectbox label hidden ── */
    div[data-testid="stSelectbox"] label { display: none !important; }
    div[data-testid="stPlotlyChart"] { padding: 0 !important; }
    [data-testid="stVerticalBlock"] { gap: 0.35rem !important; }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def money(value: float, signed: bool = False) -> str:
    try:
        value = float(value)
    except Exception:
        value = 0.0

    sign = ""
    if signed:
        sign = "+" if value >= 0 else "-"

    value_abs = abs(value)

    if value_abs >= 1_000_000:
        formatted = f"{value_abs / 1_000_000:.1f}M"
    elif value_abs >= 100_000:
        formatted = f"{value_abs / 1_000:.0f}K"
    elif value_abs >= 10_000:
        formatted = f"{value_abs / 1_000:.1f}K"
    elif value_abs >= 1_000:
        formatted = f"{value_abs:,.0f}"
    else:
        formatted = f"{value_abs:,.2f}"

    return f"{sign}${formatted}"


def pct(value: float, decimals: int = 0) -> str:
    try:
        return f"{float(value):.{decimals}f}%"
    except Exception:
        return "0%"


def section(title: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:9px;margin:16px 0 8px">
            <div style="width:5px;height:18px;border-radius:10px;background:#0F9F6E;flex-shrink:0"></div>
            <div style="font-size:11px;color:#6B6258;font-weight:800;
                        letter-spacing:.09em;text-transform:uppercase">{title}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def kpi(label: str, value: str, sub: str = "", tone: str = "") -> str:
    color_map = {
        "good":   "#079455",
        "bad":    "#D92D20",
        "warn":   "#B54708",
        "purple": "#0F9F6E",
    }
    value_color = color_map.get(tone, "#2B2A27")
    return (
        f'<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:16px;padding:16px 17px;min-height:92px;box-shadow:0 8px 24px rgba(60,45,25,0.06);">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#9A8F82;font-weight:800;margin-bottom:8px;">{label}</div>'
        f'<div style="font-size:23px;line-height:1.1;font-weight:800;font-variant-numeric:tabular-nums;color:{value_color};">{value}</div>'
        f'<div style="font-size:11.5px;color:#9A8F82;margin-top:6px;">{sub}</div>'
        f'</div>'
    )


def categorise(description: str, amount: float) -> tuple[str, str]:
    desc = str(description).lower()

    rules = [
        ("salary|payroll|wages", "Salary", "Income"),
        ("refund|ato", "Refund", "Income"),
        ("family transfer received", "Family Support", "Income"),
        ("transfer to savings", "Savings Transfer", "Transfer"),
        ("rent", "Rent", "Expense"),
        ("coles|woolworths|aldi|supermarket|groceries", "Groceries", "Expense"),
        ("netflix|spotify|subscription", "Subscriptions", "Expense"),
        ("myki|uber trip|train|bus|tram", "Transport", "Expense"),
        ("bp|shell|fuel|petrol", "Fuel", "Expense"),
        ("childcare|child care|daycare", "Childcare", "Expense"),
        ("coffee|cafe", "Coffee", "Expense"),
        ("restaurant|dinner|lunch|uber eats|takeaway", "Eating Out", "Expense"),
        ("kmart|target|amazon|shopping", "Shopping", "Expense"),
        ("phone|mobile|telstra|optus", "Phone", "Expense"),
        ("electricity|gas|water|utility", "Utilities", "Expense"),
        ("medical|pharmacy|dental|chemist", "Health", "Expense"),
    ]

    import re

    for pattern, category, txn_type in rules:
        if re.search(pattern, desc):
            return category, txn_type

    if amount > 0:
        return "Other Income", "Income"

    return "Other Expense", "Expense"


def clean_data(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    required = ["Date", "Description", "Amount"]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}. Your CSV needs Date, Description, Amount.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Description"] = df["Description"].astype(str)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    df = df.dropna(subset=["Date", "Amount"])

    df[["Category", "Type"]] = df.apply(
        lambda row: pd.Series(categorise(row["Description"], row["Amount"])),
        axis=1
    )

    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    return df


def compute_health_score(income: float, expense: float, net: float, savings_rate: float, subs_total: float) -> int:
    score = 0

    if income > 0:
        score += 20

    if net > 0:
        score += 25

    if savings_rate >= 25:
        score += 25
    elif savings_rate >= 15:
        score += 18
    elif savings_rate >= 5:
        score += 10

    expense_ratio = expense / income if income > 0 else 1

    if expense_ratio <= 0.70:
        score += 20
    elif expense_ratio <= 0.90:
        score += 10

    subs_ratio = subs_total / income if income > 0 else 0

    if subs_ratio <= 0.03:
        score += 10
    elif subs_ratio <= 0.06:
        score += 5

    return min(score, 100)


def score_label(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 65:
        return "Healthy"
    if score >= 45:
        return "Needs attention"
    return "At risk"


def score_color(score: int) -> str:
    if score >= 80:
        return "#0F9F6E"
    if score >= 65:
        return "#2E7D68"
    if score >= 45:
        return "#B54708"
    return "#D92D20"


def build_insights(total_income, total_expense, net, savings_rate, expense_summary, subs_total):
    insights = []

    if net >= 0:
        insights.append({
            "title": "Money position",
            "body": f"You had {money(net)} left after expenses. This means your income is covering your spending."
        })
    else:
        insights.append({
            "title": "Money position",
            "body": f"You spent {money(abs(net))} more than you earned. Start by checking your biggest spending areas."
        })

    if not expense_summary.empty:
        top = expense_summary.iloc[0]
        share = top["Amount"] / total_expense * 100 if total_expense > 0 else 0
        insights.append({
            "title": "Biggest spending area",
            "body": f"{top['Category']} is your largest category, taking {share:.0f}% of your spending."
        })

    if subs_total > 0:
        insights.append({
            "title": "Subscriptions",
            "body": f"Subscriptions cost {money(subs_total)} in this view. Review whether each one is still useful."
        })
    else:
        insights.append({
            "title": "Subscriptions",
            "body": "No major subscription spending was detected in this selected period."
        })

    return insights


# ============================================================
# TOP AREA
# ============================================================

st.markdown(
    """
    <div class="top-note">
        🔒 Your file is processed only in this app session. Upload a CSV statement to understand your money clearly.
    </div>
    """,
    unsafe_allow_html=True
)

top_left, top_right = st.columns([3, 1])

with top_left:
    uploaded = st.file_uploader(
        "Upload your bank statement CSV",
        type=["csv"],
        label_visibility="collapsed"
    )

with top_right:
    st.download_button(
        "Download sample CSV",
        data=open("sample_bank_statement.csv", "rb").read(),
        file_name="sample_bank_statement.csv",
        mime="text/csv",
        use_container_width=True
    )

if uploaded is None:
    st.markdown(
        """
        <div class="card" style="padding:28px;margin-top:10px;">
            <div style="font-size:28px;font-weight:800;color:#101828;margin-bottom:8px;">
                Money Health Agent
            </div>
            <div style="font-size:14px;color:#667085;line-height:1.7;max-width:760px;">
                Upload a bank statement to see your income, expenses, savings,
                spending categories, money health score, and simple actions to check next.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    section("What this dashboard helps you understand")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="insight">
                <div class="insight-title">Am I okay financially?</div>
                <div class="insight-body">See your Money Health Score and whether income is ahead of spending.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div class="insight">
                <div class="insight-title">Where did my money go?</div>
                <div class="insight-body">Understand your biggest spending categories without reading every transaction.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div class="insight">
                <div class="insight-title">What should I check?</div>
                <div class="insight-body">Get plain-English insights that point to what matters most.</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.stop()


# ============================================================
# LOAD DATA
# ============================================================

try:
    df = clean_data(uploaded)
except Exception as e:
    st.error(str(e))
    st.stop()


# ============================================================
# FILTERS
# ============================================================

f1, f2, f3 = st.columns(3)

with f1:
    month_filter = st.selectbox("Month", ["All months"] + sorted(df["Month"].unique()))

with f2:
    category_filter = st.selectbox("Category", ["All categories"] + sorted(df["Category"].unique()))

with f3:
    type_filter = st.selectbox("Type", ["All types", "Income", "Expense", "Transfer"])

filtered = df.copy()

if month_filter != "All months":
    filtered = filtered[filtered["Month"] == month_filter]

if category_filter != "All categories":
    filtered = filtered[filtered["Category"] == category_filter]

if type_filter != "All types":
    filtered = filtered[filtered["Type"] == type_filter]


# ── Navigation pill tabs ──────────────────────────────────────────────────────
st.radio(
    "nav",
    ["Overview", "Spending", "Income", "Subscriptions", "Bills"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_tab",
)

# ============================================================
# CALCULATIONS
# ============================================================

income_df = filtered[filtered["Type"] == "Income"]
expense_df = filtered[filtered["Type"] == "Expense"]
transfer_df = filtered[filtered["Type"] == "Transfer"]

total_income = income_df["Amount"].sum()
total_expense = abs(expense_df["Amount"].sum())
net = total_income - total_expense
savings_rate = (net / total_income * 100) if total_income > 0 else 0

days = max((filtered["Date"].max() - filtered["Date"].min()).days + 1, 1)
daily_spend = total_expense / days

subs_total = abs(expense_df[expense_df["Category"] == "Subscriptions"]["Amount"].sum())

health_score = compute_health_score(
    total_income,
    total_expense,
    net,
    savings_rate,
    subs_total
)

label = score_label(health_score)

expense_summary = (
    expense_df.groupby("Category")["Amount"]
    .sum()
    .abs()
    .reset_index(name="Amount")
    .sort_values("Amount", ascending=False)
)

monthly = (
    df.groupby(["Month", "Type"])["Amount"]
    .sum()
    .reset_index()
)

monthly["Amount"] = monthly.apply(
    lambda row: abs(row["Amount"]) if row["Type"] == "Expense" else row["Amount"],
    axis=1
)


# ============================================================
# HERO + KPI SECTION
# ============================================================

hero_col, kpi_col = st.columns([1.65, 1])

with hero_col:
    if net >= 0:
        headline = f"{label} — you're saving {savings_rate:.0f}% of your income"
    else:
        headline = f"{label} — spending is higher than income"

    st.markdown(
        f"""
        <div class="hero">
            <div class="score" style="color:{score_color(health_score)};">{health_score}</div>
            <div style="flex:1">
                <div class="score-label">✦ Money Health · {label}</div>
                <div class="score-title">{headline}</div>
                <div class="score-stats">
                    <div class="score-stat">
                        <div class="score-stat-label">Earned</div>
                        <div class="score-stat-value" style="color:#34D399">{money(total_income)}</div>
                    </div>
                    <div class="score-stat">
                        <div class="score-stat-label">Spent</div>
                        <div class="score-stat-value" style="color:#F87171">{money(total_expense)}</div>
                    </div>
                    <div class="score-stat">
                        <div class="score-stat-label">Saved</div>
                        <div class="score-stat-value" style="color:#34D399">{money(net, signed=True)}</div>
                    </div>
                    <div class="score-stat">
                        <div class="score-stat-label">Savings Rate</div>
                        <div class="score-stat-value">{pct(savings_rate, 1)}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with kpi_col:
    kpi_tone = "good" if net >= 0 else "bad"
    sr_tone = "good" if savings_rate >= 20 else "warn" if savings_rate >= 0 else "bad"

    kpi_html = (
        '<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;">'
        + kpi("Money left", money(net, signed=True), "after expenses", kpi_tone)
        + kpi("Saved income", pct(savings_rate, 0), "goal: 20%+", sr_tone)
        + kpi("Daily spend", money(daily_spend), "average per day", "")
        + kpi("Transactions", str(len(filtered)), "in selected view", "purple")
        + '</div>'
    )
    st.markdown(kpi_html, unsafe_allow_html=True)


# ============================================================
# MAIN DASHBOARD
# ============================================================

section("Where did the money go?")

left, right = st.columns([1.4, 1])

with left:
    chart1, chart2 = st.columns(2)

    with chart1:
        if not expense_summary.empty:
            fig_donut = px.pie(
                expense_summary,
                names="Category",
                values="Amount",
                hole=0.55,
                color_discrete_sequence=[
                    "#0F9F6E", "#7CBFA5", "#D96C5F", "#D9A441",
                    "#6AAE9F", "#A7C957", "#C9895B"
                ],
            )
            fig_donut.update_layout(
                height=310,
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="#FFFCF5",
                plot_bgcolor="#FFFCF5",
                font=dict(family="Inter", size=11),
                showlegend=True,
                legend=dict(orientation="h", y=-0.1)
            )
            # ← fig_monthly calls removed from here
            st.markdown('<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;padding:12px 14px 4px;box-shadow:0 8px 24px rgba(60,45,25,0.06);"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#9A8F82;font-weight:800;margin-bottom:4px;">Spending breakdown</div>', unsafe_allow_html=True)
            st.plotly_chart(fig_donut, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card">No expenses found.</div>', unsafe_allow_html=True)

    with chart2:
        fig_monthly = px.bar(                          # ← created here first
            monthly[monthly["Type"].isin(["Income", "Expense"])],
            x="Month",
            y="Amount",
            color="Type",
            barmode="group",
            color_discrete_map={"Income": "#0F9F6E", "Expense": "#D96C5F"},
        )
        # ← now safe to call update methods
        fig_monthly.update_xaxes(
            showgrid=False,
            linecolor="#E7DDCC",
            tickfont=dict(color="#6B6258")
        )
        fig_monthly.update_yaxes(
            showgrid=True,
            gridcolor="#EFE6D6",
            linecolor="#E7DDCC",
            tickfont=dict(color="#6B6258")
        )
        fig_monthly.update_layout(
            height=310,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="#FFFCF5",
            plot_bgcolor="#FFFCF5",
            font=dict(family="Inter", size=11, color="#6B6258"),
            legend=dict(orientation="h", y=-0.1),
            xaxis_title="",
            yaxis_title="",
        )
        st.markdown('<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;padding:12px 14px 4px;box-shadow:0 8px 24px rgba(60,45,25,0.06);"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#9A8F82;font-weight:800;margin-bottom:4px;">Income vs spending</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_monthly, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with right:
    fixed_categories = ["Rent", "Childcare", "Utilities", "Phone", "Fuel"]
    fixed_total = abs(expense_df[expense_df["Category"].isin(fixed_categories)]["Amount"].sum())
    cuttable_total = max(total_expense - fixed_total, 0)

    st.markdown(
        f'<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;padding:16px 18px;box-shadow:0 8px 24px rgba(60,45,25,0.06);">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#9A8F82;font-weight:800;margin-bottom:12px;">Your spending split</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #EFE6D6;">'
        f'<div>'
        f'<div style="font-size:13px;font-weight:800;color:#2B2A27;">Fixed bills</div>'
        f'<div style="font-size:11.5px;color:#9A8F82;margin-top:2px;">rent, childcare, phone, utilities</div>'
        f'</div>'
        f'<div style="font-size:13px;font-weight:800;color:#2B2A27;">{money(fixed_total)}</div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;padding:9px 0;">'
        f'<div>'
        f'<div style="font-size:13px;font-weight:800;color:#2B2A27;">Cuttable spend</div>'
        f'<div style="font-size:11.5px;color:#9A8F82;margin-top:2px;">groceries, dining, shopping</div>'
        f'</div>'
        f'<div style="font-size:13px;font-weight:800;color:#0F9F6E;">{money(cuttable_total)}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    budget_items = [
        ("Rent", 30),
        ("Groceries", 12),
        ("Eating Out", 5),
    ]

    budget_html = (
        '<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;' 
        'padding:16px 18px;box-shadow:0 8px 24px rgba(60,45,25,0.06);margin-top:10px;">' 
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;' 
        'color:#9A8F82;font-weight:800;margin-bottom:14px;">Budget check</div>'
    )

    for category, recommended_pct in budget_items:
        amount = 0
        match = expense_summary[expense_summary["Category"] == category]
        if not match.empty:
            amount = match.iloc[0]["Amount"]

        actual_pct = (amount / total_income * 100) if total_income > 0 else 0
        width = min((actual_pct / recommended_pct * 100), 100) if recommended_pct > 0 else 0

        if actual_pct > recommended_pct:
            status, bar_color = "Over", "#D92D20"
        elif actual_pct > recommended_pct * 0.8:
            status, bar_color = "Watch", "#B54708"
        else:
            status, bar_color = "On track", "#0F9F6E"

        budget_html += (
            f'<div style="margin-bottom:13px;">' 
            f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:5px;">' 
            f'<div><div style="font-size:13px;font-weight:700;color:#2B2A27">{category}</div>' 
            f'<div style="font-size:11px;color:#9A8F82;margin-top:1px">{money(amount)} used</div></div>' 
            f'<div style="font-size:11px;font-weight:700;color:{bar_color}">{status}</div></div>' 
            f'<div style="width:100%;height:6px;background:#EFE6D6;border-radius:99px;overflow:hidden;">' 
            f'<div style="width:{width:.0f}%;height:100%;background:{bar_color};border-radius:99px;"></div>' 
            f'</div></div>'
        )

    budget_html += "</div>"
    st.markdown(budget_html, unsafe_allow_html=True)


# ============================================================
# TOP SPENDING + INSIGHTS
# ============================================================

section("Top spending and insights")

spend_col, insight_col = st.columns([1, 1])

with spend_col:
    cat_rows = ""
    if not expense_summary.empty:
        max_amt = expense_summary.iloc[0]["Amount"] if not expense_summary.empty else 1
        for _, row in expense_summary.head(6).iterrows():
            bar_w = row["Amount"] / max_amt * 100 if max_amt > 0 else 0
            cat_rows += (
                f'<div style="margin-bottom:11px;">' 
                f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">' 
                f'<div style="font-size:13px;font-weight:700;color:#2B2A27">{row["Category"]}</div>' 
                f'<div style="font-size:13px;font-weight:700;color:#0F9F6E;font-variant-numeric:tabular-nums">{money(row["Amount"])}</div>' 
                f'</div>' 
                f'<div style="width:100%;height:6px;background:#EFE6D6;border-radius:99px;overflow:hidden;">' 
                f'<div style="width:{bar_w:.0f}%;height:100%;background:#0F9F6E;border-radius:99px;"></div>' 
                f'</div></div>'
            )
    empty_msg = '<div style="font-size:12px;color:#9A8F82">No spending categories found.</div>'
    st.markdown(
        '<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;' 
        'padding:16px 18px;box-shadow:0 8px 24px rgba(60,45,25,0.06);">' 
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;' 
        'color:#9A8F82;font-weight:800;margin-bottom:14px;">Top categories</div>' 
        + (cat_rows if cat_rows else empty_msg) + '</div>',
        unsafe_allow_html=True
    )

with insight_col:
    insights = build_insights(
        total_income, total_expense, net, savings_rate, expense_summary, subs_total
    )
    insight_html = '<div style="display:flex;flex-direction:column;gap:9px;">'
    for item in insights:
        insight_html += (
            f'<div style="background:#FFF8EA;border:1px solid #EAD9B7;border-radius:16px;' 
            f'padding:14px 16px;box-shadow:0 8px 24px rgba(60,45,25,0.06);">' 
            f'<div style="font-size:13.5px;font-weight:800;color:#2B2A27;margin-bottom:5px">{item["title"]}</div>' 
            f'<div style="font-size:12.5px;color:#6B6258;line-height:1.55">{item["body"]}</div>' 
            f'</div>'
        )
    insight_html += '</div>'
    st.markdown(insight_html, unsafe_allow_html=True)


# ============================================================
# SUBSCRIPTIONS SECTION
# ============================================================

section("Subscriptions")

subs_df = expense_df[expense_df["Category"] == "Subscriptions"].copy()
subs_df = subs_df.sort_values("Amount")

if subs_df.empty:
    st.markdown(
        '<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;' 
        'padding:14px 18px;box-shadow:0 8px 24px rgba(60,45,25,0.06);' 
        'font-size:13px;color:#9A8F82">No subscriptions detected in this period.</div>',
        unsafe_allow_html=True
    )
else:
    subs_col, _ = st.columns([1, 1])
    with subs_col:
        sub_rows = ""
        for _, row in subs_df.iterrows():
            desc = str(row["Description"])[:40]
            sub_rows += (
                f'<div style="display:flex;justify-content:space-between;align-items:center;' 
                f'padding:9px 0;border-bottom:0.5px solid #EFE6D6;">' 
                f'<span style="font-size:13px;font-weight:600;color:#2B2A27">{desc}</span>' 
                f'<span style="font-size:13px;font-weight:700;color:#D92D20;' 
                f'font-variant-numeric:tabular-nums">{money(abs(row["Amount"]))}</span>' 
                f'</div>'
            )
        total_sub_line = (
            f'<div style="display:flex;justify-content:space-between;align-items:center;' 
            f'padding:10px 0 2px;">' 
            f'<span style="font-size:12px;font-weight:700;color:#9A8F82;text-transform:uppercase;' 
            f'letter-spacing:.06em">Total / period</span>' 
            f'<span style="font-size:14px;font-weight:800;color:#D92D20;' 
            f'font-variant-numeric:tabular-nums">{money(subs_total)}</span></div>'
        )
        st.markdown(
            '<div style="background:#FFFCF5;border:1px solid #E7DDCC;border-radius:18px;' 
            'padding:16px 18px;box-shadow:0 8px 24px rgba(60,45,25,0.06);">' 
            '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;' 
            'color:#9A8F82;font-weight:800;margin-bottom:8px;">Active subscriptions</div>' 
            + sub_rows + total_sub_line + '</div>',
            unsafe_allow_html=True
        )


# ============================================================
# TRANSACTION EXPLORER
# ============================================================

section("Transaction explorer")

search = st.text_input(
    "Search transactions",
    placeholder="Search description or category..."
)

table_df = filtered.copy()

if search:
    query = search.lower().strip()
    table_df = table_df[
        table_df["Description"].str.lower().str.contains(query, na=False)
        | table_df["Category"].str.lower().str.contains(query, na=False)
        | table_df["Type"].str.lower().str.contains(query, na=False)
    ]

display_df = table_df[["Date", "Description", "Category", "Type", "Amount"]].copy()
display_df = display_df.sort_values("Date", ascending=False).reset_index(drop=True)
display_df["Date"] = display_df["Date"].dt.strftime("%d %b %Y")
display_df["Amount"] = display_df["Amount"].map(lambda x: money(x, signed=True))

st.markdown(
    f'<div style="font-size:12px;color:#9A8F82;margin-bottom:6px;">' 
    f'Showing {len(display_df)} transaction{"s" if len(display_df) != 1 else ""}</div>',
    unsafe_allow_html=True
)
st.dataframe(display_df, use_container_width=True, height=360)

st.download_button(
    "⬇ Download filtered CSV",
    data=table_df.to_csv(index=False).encode("utf-8"),
    file_name="transactions_filtered.csv",
    mime="text/csv",
)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer">
        Money Health Agent is for personal tracking and education only.
        It is not financial, tax, investment, or credit advice.
    </div>
    """,
    unsafe_allow_html=True
)