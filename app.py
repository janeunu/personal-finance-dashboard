import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Personal Finance Dashboard", layout="wide")

st.title("💰 Personal Finance Dashboard Agent")
st.write("Upload your bank statement and understand your finances easily.")

# Upload CSV
uploaded_file = st.file_uploader("Upload your bank statement (CSV)", type=["csv"])

# Load category rules
rules = pd.read_csv("category_rules.csv")

# Categorisation function
def categorise(desc, amount):
    desc = str(desc).lower()
    for _, row in rules.iterrows():
        if row["keyword"] in desc:
            return row["category"], row["type"]
    return ("Other", "Income" if amount > 0 else "Expense")


if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
    st.write("Detected columns:", df.columns.tolist())

    # Clean data
    df["Date"] = pd.to_datetime(df["Date"])
    df["Amount"] = pd.to_numeric(df["Amount"])

    # Categorise
    df["Category"], df["Type"] = zip(*df.apply(
        lambda row: categorise(row["Description"], row["Amount"]), axis=1
    ))

    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    # Split income/expense
    income_df = df[df["Type"] == "Income"]
    expense_df = df[df["Type"] == "Expense"]

    total_income = income_df["Amount"].sum()
    total_expense = abs(expense_df["Amount"].sum())
    net = total_income - total_expense
    savings_rate = (net / total_income * 100) if total_income > 0 else 0

    # Dashboard metrics
    st.subheader("📊 Financial Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Income", f"${total_income:,.2f}")
    col2.metric("Expenses", f"${total_expense:,.2f}")
    col3.metric("Net", f"${net:,.2f}")
    col4.metric("Savings Rate", f"{savings_rate:.1f}%")

    # Expense pie chart
    st.subheader("📌 Expense Breakdown")

    expense_summary = (
        expense_df.groupby("Category")["Amount"]
        .sum()
        .abs()
        .reset_index()
        .sort_values("Amount", ascending=False)
    )

    fig1 = px.pie(expense_summary, names="Category", values="Amount")
    st.plotly_chart(fig1, use_container_width=True)

    # Monthly chart
    st.subheader("📅 Monthly Income vs Expense")

    monthly = df.groupby(["Month", "Type"])["Amount"].sum().reset_index()
    monthly["Amount"] = monthly.apply(
        lambda r: abs(r["Amount"]) if r["Type"] == "Expense" else r["Amount"],
        axis=1
    )

    fig2 = px.bar(monthly, x="Month", y="Amount", color="Type", barmode="group")
    st.plotly_chart(fig2, use_container_width=True)

    # Transactions
    st.subheader("📋 Transactions")
    st.dataframe(df)

    # Insight
    st.subheader("🧠 Insight")

    if net > 0:
        st.success(f"You are saving ${net:,.2f} this period 👍")
    else:
        st.warning(f"You are overspending by ${abs(net):,.2f} ⚠️")

else:
    st.info("Please upload your CSV file to begin.")