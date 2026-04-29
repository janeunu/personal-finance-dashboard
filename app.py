import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Money Health Dashboard",
    layout="wide"
)

# ---------------- CUSTOM STYLE ----------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

.kpi-card {
    background: white;
    padding: 20px;
    border-radius: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    border: 1px solid #eef2f7;
}

.kpi-label {
    font-size: 14px;
    color: #6b7280;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 28px;
    font-weight: 800;
    color: #111827;
}

.status-card {
    background: #f8fafc;
    padding: 22px;
    border-radius: 18px;
    border: 1px solid #e5e7eb;
    margin-top: 10px;
    margin-bottom: 20px;
}

.insight-card {
    background: white;
    padding: 18px;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.title("💰 Money Health Dashboard")
st.write(
    "A one-page personal finance dashboard that helps everyday people understand "
    "their income, expenses, savings, and financial position clearly."
)

# ---------------- LOAD RULES ----------------
rules = pd.read_csv("category_rules.csv")
rules["keyword"] = rules["keyword"].astype(str).str.lower()

# ---------------- FUNCTIONS ----------------
def categorise_transaction(description, amount):
    description = str(description).lower()

    for _, rule in rules.iterrows():
        if rule["keyword"] in description:
            return rule["category"], rule["type"]

    if amount > 0:
        return "Other Income", "Income"
    return "Other Expense", "Expense"


def money_health_status(savings_rate, net_cashflow):
    if net_cashflow < 0:
        return "🔴 Overspending", "You spent more than you earned. This needs attention."
    elif savings_rate >= 20:
        return "🟢 Healthy", "You are saving a strong portion of your income."
    elif savings_rate >= 10:
        return "🟡 Stable", "You are saving money, but there is room to improve."
    else:
        return "🟠 Tight", "You are saving only a small amount. Watch your flexible spending."


def format_money(value):
    return f"${value:,.2f}"


# ---------------- UPLOAD ----------------
uploaded_file = st.file_uploader("Upload your bank statement CSV", type=["csv"])

if uploaded_file is None:
    st.info("Upload `sample_bank_statement.csv` to view the dashboard.")
    st.stop()

# ---------------- DATA CLEANING ----------------
df = pd.read_csv(uploaded_file)
df.columns = df.columns.str.strip()

required_columns = ["Date", "Description", "Amount"]

if not all(col in df.columns for col in required_columns):
    st.error("Your CSV must include these exact columns: Date, Description, Amount")
    st.write("Detected columns:", df.columns.tolist())
    st.stop()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
df = df.dropna(subset=["Date", "Amount"])

df[["Category", "Type"]] = df.apply(
    lambda row: pd.Series(
        categorise_transaction(row["Description"], row["Amount"])
    ),
    axis=1
)

df["Month"] = df["Date"].dt.to_period("M").astype(str)

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("Dashboard Filters")

month_options = ["All"] + sorted(df["Month"].unique())
selected_month = st.sidebar.selectbox("Month", month_options)

category_options = ["All"] + sorted(df["Category"].unique())
selected_category = st.sidebar.selectbox("Category", category_options)

filtered_df = df.copy()

if selected_month != "All":
    filtered_df = filtered_df[filtered_df["Month"] == selected_month]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

income_df = filtered_df[filtered_df["Type"] == "Income"]
expense_df = filtered_df[filtered_df["Type"] == "Expense"]

total_income = income_df["Amount"].sum()
total_expenses = abs(expense_df["Amount"].sum())
net_cashflow = total_income - total_expenses
savings_rate = (net_cashflow / total_income * 100) if total_income > 0 else 0

status, status_message = money_health_status(savings_rate, net_cashflow)

# ---------------- KPI CARDS ----------------
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Income</div>
        <div class="kpi-value">{format_money(total_income)}</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Expenses</div>
        <div class="kpi-value">{format_money(total_expenses)}</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Money Left</div>
        <div class="kpi-value">{format_money(net_cashflow)}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Savings Rate</div>
        <div class="kpi-value">{savings_rate:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Money Status</div>
        <div class="kpi-value">{status}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- STATUS EXPLANATION ----------------
st.markdown(f"""
<div class="status-card">
    <h3>{status}</h3>
    <p>{status_message}</p>
    <p>
        You earned <b>{format_money(total_income)}</b>, spent 
        <b>{format_money(total_expenses)}</b>, and had 
        <b>{format_money(net_cashflow)}</b> left.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------- DASHBOARD CHARTS ----------------
left, right = st.columns([1.25, 1])

with left:
    st.subheader("📅 Income vs Expenses Over Time")

    monthly_summary = (
        df.groupby(["Month", "Type"])["Amount"]
        .sum()
        .reset_index()
    )

    monthly_summary["Amount"] = monthly_summary.apply(
        lambda row: abs(row["Amount"]) if row["Type"] == "Expense" else row["Amount"],
        axis=1
    )

    fig_monthly = px.bar(
        monthly_summary,
        x="Month",
        y="Amount",
        color="Type",
        barmode="group",
        text_auto=".2s"
    )

    fig_monthly.update_layout(
        height=420,
        xaxis_title="Month",
        yaxis_title="Amount",
        legend_title=""
    )

    st.plotly_chart(fig_monthly, use_container_width=True)

with right:
    st.subheader("🍩 Expense Breakdown")

    expense_summary = (
        expense_df.groupby("Category")["Amount"]
        .sum()
        .abs()
        .reset_index()
        .sort_values("Amount", ascending=False)
    )

    if not expense_summary.empty:
        fig_donut = px.pie(
            expense_summary,
            names="Category",
            values="Amount",
            hole=0.45
        )

        fig_donut.update_layout(height=420)

        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("No expenses found for this selection.")

# ---------------- SECOND ROW ----------------
left2, right2 = st.columns([1, 1])

with left2:
    st.subheader("🏆 Top Spending Categories")

    if not expense_summary.empty:
        fig_top = px.bar(
            expense_summary.head(8),
            x="Amount",
            y="Category",
            orientation="h",
            text_auto=".2s"
        )

        fig_top.update_layout(
            height=420,
            yaxis={"categoryorder": "total ascending"},
            xaxis_title="Amount",
            yaxis_title=""
        )

        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.info("No spending categories to show.")

with right2:
    st.subheader("🔁 Bills, Subscriptions & Fixed Costs")

    fixed_categories = [
        "Rent",
        "Subscriptions",
        "Subscription",
        "Utilities",
        "Insurance",
        "Childcare",
        "Phone",
        "Internet"
    ]

    fixed_df = expense_df[expense_df["Category"].isin(fixed_categories)]

    if not fixed_df.empty:
        fixed_summary = (
            fixed_df.groupby("Category")["Amount"]
            .sum()
            .abs()
            .reset_index()
            .sort_values("Amount", ascending=False)
        )

        fig_fixed = px.bar(
            fixed_summary,
            x="Category",
            y="Amount",
            text_auto=".2s"
        )

        fig_fixed.update_layout(
            height=420,
            xaxis_title="Fixed Cost Type",
            yaxis_title="Amount"
        )

        st.plotly_chart(fig_fixed, use_container_width=True)
    else:
        st.info("No fixed bills detected yet.")

# ---------------- INSIGHTS ----------------
st.subheader("🧠 Plain-English Money Insights")

insights = []

if total_income > 0:
    insights.append(
        f"Your total income for this view is **{format_money(total_income)}**."
    )

if total_expenses > 0:
    insights.append(
        f"You spent **{format_money(total_expenses)}**, which is **{(total_expenses / total_income * 100):.1f}%** of your income."
        if total_income > 0 else
        f"You spent **{format_money(total_expenses)}**."
    )

if not expense_summary.empty:
    biggest_category = expense_summary.iloc[0]
    biggest_percent = biggest_category["Amount"] / total_expenses * 100 if total_expenses > 0 else 0
    insights.append(
        f"Your biggest spending area is **{biggest_category['Category']}**, "
        f"costing **{format_money(biggest_category['Amount'])}** "
        f"({biggest_percent:.1f}% of expenses)."
    )

subscription_total = expense_df[
    expense_df["Category"].isin(["Subscription", "Subscriptions"])
]["Amount"].abs().sum()

if subscription_total > 0:
    insights.append(
        f"Your subscriptions cost **{format_money(subscription_total)}** in this period."
    )

if net_cashflow > 0:
    insights.append(
        f"You had **{format_money(net_cashflow)}** left after expenses."
    )
else:
    insights.append(
        f"You overspent by **{format_money(abs(net_cashflow))}** in this period."
    )

if savings_rate >= 20:
    insights.append("Your savings rate is strong. This is a healthy money position.")
elif savings_rate >= 10:
    insights.append("Your savings rate is stable, but improving it slightly would make your finances stronger.")
elif net_cashflow >= 0:
    insights.append("You are not overspending, but your leftover money is low.")
else:
    insights.append("Your spending is higher than your income. Start by reviewing the top spending categories.")

for insight in insights:
    st.markdown(f"""
    <div class="insight-card">
        {insight}
    </div>
    """, unsafe_allow_html=True)

# ---------------- TRANSACTION TABLE ----------------
st.subheader("📋 Transaction Explorer")

st.dataframe(
    filtered_df.sort_values("Date", ascending=False),
    use_container_width=True,
    height=420
)

# ---------------- FOOTER ----------------
st.caption(
    "Disclaimer: This dashboard is for educational and personal tracking purposes only. "
    "It is not financial advice."
)