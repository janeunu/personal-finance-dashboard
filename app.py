import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Money Health Agent", layout="wide")

# ---------- STYLE ----------
st.markdown("""
<style>
.main {
    background-color: #f7f9fc;
}
.big-card {
    padding: 22px;
    border-radius: 18px;
    background-color: white;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    margin-bottom: 15px;
}
.metric-title {
    font-size: 15px;
    color: #6b7280;
}
.metric-value {
    font-size: 30px;
    font-weight: 700;
    color: #111827;
}
.good {
    color: #15803d;
    font-weight: 700;
}
.warning {
    color: #ca8a04;
    font-weight: 700;
}
.danger {
    color: #dc2626;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

st.title("💰 Money Health Agent")
st.write("A simple personal finance dashboard for people who want to understand their money without finance knowledge.")

uploaded_file = st.file_uploader("Upload your bank statement CSV", type=["csv"])

rules = pd.read_csv("category_rules.csv")


def categorise(desc, amount):
    desc = str(desc).lower()
    for _, row in rules.iterrows():
        if str(row["keyword"]).lower() in desc:
            return row["category"], row["type"]
    return ("Other Income", "Income") if amount > 0 else ("Other Expense", "Expense")


def money_status(savings_rate, net):
    if net < 0:
        return "🔴 Overspending", "danger", "You spent more than you earned. Focus on reducing flexible spending."
    elif savings_rate >= 20:
        return "🟢 Healthy", "good", "You are saving a strong portion of your income."
    elif savings_rate >= 10:
        return "🟡 Stable", "warning", "You are saving, but there is room to improve."
    else:
        return "🟠 Tight", "warning", "You are saving a small amount. Watch your expenses carefully."


if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    required = ["Date", "Description", "Amount"]

    if not all(col in df.columns for col in required):
        st.error("Your CSV must contain Date, Description, and Amount columns.")
        st.write("Detected columns:", df.columns.tolist())
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df = df.dropna(subset=["Date", "Amount"])

        df[["Category", "Type"]] = df.apply(
            lambda row: pd.Series(categorise(row["Description"], row["Amount"])),
            axis=1
        )

        df["Month"] = df["Date"].dt.to_period("M").astype(str)

        # Sidebar filters
        st.sidebar.header("Filters")
        months = sorted(df["Month"].unique())
        selected_month = st.sidebar.selectbox("Select month", ["All"] + months)

        if selected_month != "All":
            filtered = df[df["Month"] == selected_month]
        else:
            filtered = df.copy()

        income_df = filtered[filtered["Type"] == "Income"]
        expense_df = filtered[filtered["Type"] == "Expense"]

        total_income = income_df["Amount"].sum()
        total_expense = abs(expense_df["Amount"].sum())
        net = total_income - total_expense
        savings_rate = (net / total_income * 100) if total_income > 0 else 0

        status, status_class, status_message = money_status(savings_rate, net)

        # ---------- TOP SUMMARY ----------
        st.subheader("Your Money Health Snapshot")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.markdown(f"""
            <div class="big-card">
                <div class="metric-title">Income</div>
                <div class="metric-value">${total_income:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="big-card">
                <div class="metric-title">Expenses</div>
                <div class="metric-value">${total_expense:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="big-card">
                <div class="metric-title">Money Left</div>
                <div class="metric-value">${net:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="big-card">
                <div class="metric-title">Savings Rate</div>
                <div class="metric-value">{savings_rate:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="big-card">
            <h3>{status}</h3>
            <p class="{status_class}">{status_message}</p>
            <p>You earned <b>${total_income:,.2f}</b>, spent <b>${total_expense:,.2f}</b>, and had <b>${net:,.2f}</b> left.</p>
        </div>
        """, unsafe_allow_html=True)

        # ---------- CHARTS ----------
        left, right = st.columns([1.1, 1])

        with left:
            st.subheader("Where Your Money Goes")

            expense_summary = (
                expense_df.groupby("Category")["Amount"]
                .sum()
                .abs()
                .reset_index()
                .sort_values("Amount", ascending=False)
            )

            if not expense_summary.empty:
                fig = px.bar(
                    expense_summary,
                    x="Amount",
                    y="Category",
                    orientation="h",
                    title="Spending by Category",
                    text_auto=".2s"
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expenses found.")

        with right:
            st.subheader("Spending Share")

            if not expense_summary.empty:
                fig2 = px.pie(
                    expense_summary,
                    names="Category",
                    values="Amount",
                    hole=0.45,
                    title="Expense Breakdown"
                )
                st.plotly_chart(fig2, use_container_width=True)

        # ---------- MONTHLY TREND ----------
        st.subheader("Monthly Money Movement")

        monthly = df.groupby(["Month", "Type"])["Amount"].sum().reset_index()
        monthly["Amount"] = monthly.apply(
            lambda r: abs(r["Amount"]) if r["Type"] == "Expense" else r["Amount"],
            axis=1
        )

        fig3 = px.bar(
            monthly,
            x="Month",
            y="Amount",
            color="Type",
            barmode="group",
            title="Income vs Expenses Over Time"
        )
        st.plotly_chart(fig3, use_container_width=True)

        # ---------- TOP SPENDING ----------
        st.subheader("Top Spending Areas")

        if not expense_summary.empty:
            top_expenses = expense_summary.head(5)

            for _, row in top_expenses.iterrows():
                percent = row["Amount"] / total_expense * 100 if total_expense > 0 else 0
                st.progress(percent / 100)
                st.write(f"**{row['Category']}** — ${row['Amount']:,.2f} ({percent:.1f}% of spending)")

        # ---------- FRIENDLY INSIGHTS ----------
        st.subheader("Plain-English Money Insights")

        insights = []

        if not expense_summary.empty:
            biggest = expense_summary.iloc[0]
            insights.append(
                f"Your biggest spending area is **{biggest['Category']}**, costing **${biggest['Amount']:,.2f}**."
            )

        if savings_rate >= 20:
            insights.append("You are saving a strong portion of your income. This is a healthy position.")
        elif savings_rate >= 10:
            insights.append("You are saving some money, but improving by even 5% could make a big difference.")
        elif net >= 0:
            insights.append("You are not overspending, but your leftover money is quite low.")
        else:
            insights.append("You are currently spending more than you earn. This needs attention.")

        subscription_keywords = ["Subscriptions", "Subscription"]
        subscription_total = expense_df[expense_df["Category"].isin(subscription_keywords)]["Amount"].abs().sum()

        if subscription_total > 0:
            insights.append(f"Your subscriptions cost **${subscription_total:,.2f}** in this period.")

        for insight in insights:
            st.markdown(f"- {insight}")

        # ---------- TRANSACTION EXPLORER ----------
        st.subheader("Transaction Explorer")

        categories = ["All"] + sorted(filtered["Category"].unique())
        selected_category = st.selectbox("Choose category", categories)

        if selected_category != "All":
            display_df = filtered[filtered["Category"] == selected_category]
        else:
            display_df = filtered

        st.dataframe(
            display_df.sort_values("Date", ascending=False),
            use_container_width=True
        )

else:
    st.info("Upload your sample bank statement CSV to start.")