"""
app_clean_v7.py — Money Health Agent V7 Rebuild

Purpose:
A clean, manager-aligned V7 dashboard rebuild using the existing backend logic.

This file should:
1. Keep backend logic stable
2. Use parser.py for file parsing
3. Use categoriser.py for categorisation and review flags
4. Use metrics.py for financial calculations
5. Use charts.py for Plotly figures
6. Use ui.py for V7 styling and reusable components

This is safer than overwriting app.py immediately.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

import charts
import metrics as m
import ui

from categoriser import add_categories, flag_transactions
from config import ALL_CATEGORIES, BUDGET_GUIDE
from parser import parse_statement


# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Money Health Agent V7",
    page_icon="💰",
    layout="wide",
)

# Existing CSS + V7 rebuild CSS
ui.inject_css()
ui.inject_v7_css()


# ══════════════════════════════════════════════════════════════════════════════
# SMALL HELPERS FOR THIS ORCHESTRATOR FILE ONLY
# Keep business logic in metrics.py, parser.py, categoriser.py.
# These helpers only convert existing outputs into V7 UI input formats.
# ══════════════════════════════════════════════════════════════════════════════

def _safe_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _build_budget_rows(exp_by_cat: pd.DataFrame, total_income: float) -> list[dict]:
    """
    Convert category spending into V7 budget check rows.

    Uses BUDGET_GUIDE from config.py.
    Each budget limit is calculated as:
        total_income * recommended_percentage
    """
    rows: list[dict] = []

    if exp_by_cat is None or exp_by_cat.empty or total_income <= 0:
        return rows

    for category, pct_limit in BUDGET_GUIDE.items():
        match = exp_by_cat[exp_by_cat["Category"] == category]

        if match.empty:
            continue

        amount = _safe_float(match.iloc[0]["Total"])
        limit = total_income * (pct_limit / 100)

        if limit <= 0:
            continue

        ratio = amount / limit
        status = "On track"

        if ratio >= 1:
            status = "Over"
        elif ratio >= 0.8:
            status = "Watch"

        rows.append(
            {
                "label": category,
                "amount": amount,
                "limit": limit,
                "status": status,
            }
        )

    return rows[:6]


def _build_top_category_rows(exp_by_cat: pd.DataFrame, total_expense: float) -> list[dict]:
    """Convert expense category dataframe into V7 progress-bar rows."""
    rows: list[dict] = []

    if exp_by_cat is None or exp_by_cat.empty or total_expense <= 0:
        return rows

    for _, row in exp_by_cat.head(7).iterrows():
        amount = _safe_float(row["Total"])
        rows.append(
            {
                "category": row["Category"],
                "amount": amount,
                "pct": amount / total_expense,
            }
        )

    return rows


def _build_big_spend_rows(top_txns: pd.DataFrame) -> list[dict]:
    """Convert top expenses dataframe into V7 card rows."""
    rows: list[dict] = []

    if top_txns is None or top_txns.empty:
        return rows

    for _, row in top_txns.head(4).iterrows():
        date_value = row.get("Date", "")

        if hasattr(date_value, "strftime"):
            date_text = date_value.strftime("%d %b %Y")
        else:
            date_text = str(date_value)

        rows.append(
            {
                "description": row.get("Description", "Transaction"),
                "date": date_text,
                "amount": abs(_safe_float(row.get("Amount", 0))),
                "category": row.get("Category", ""),
            }
        )

    return rows


def _build_insights(period, exp_by_cat: pd.DataFrame, top_txns: pd.DataFrame) -> list[dict]:
    """
    Build simple plain-English insight cards.

    These are intentionally short and non-technical.
    """
    insights: list[dict] = []

    if period.net >= 0:
        insights.append(
            {
                "title": "Money position",
                "body": f"You finished this period with {ui.v7_money(period.net)} left after spending.",
            }
        )
    else:
        insights.append(
            {
                "title": "Money position",
                "body": f"Spending is higher than income by {ui.v7_money(abs(period.net))}. Start with the biggest flexible categories.",
            }
        )

    if exp_by_cat is not None and not exp_by_cat.empty:
        top = exp_by_cat.iloc[0]
        insights.append(
            {
                "title": "Biggest spending area",
                "body": f"{top['Category']} is your largest category. Reviewing this first will have the biggest impact.",
            }
        )

    if period.sub_total > 0:
        insights.append(
            {
                "title": "Subscriptions",
                "body": f"Subscriptions and streaming cost {ui.v7_money(period.sub_total)} in this view. Check if all are still useful.",
            }
        )
    else:
        insights.append(
            {
                "title": "Subscriptions",
                "body": "No major subscription spending was detected in this selected view.",
            }
        )

    return insights[:3]


def _render_plotly_card(title: str, fig) -> None:
    """Render a chart inside a V7 card."""
    st.markdown(
        f"""
        <div class="v7-card" style="padding:12px 14px 4px;">
            <div class="v7-kpi-label">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TOP CONTROL BAR
# V7 requirement:
# - privacy + upload on left
# - API key on right
# - AI insights button
# - export button
# - compact height
# ══════════════════════════════════════════════════════════════════════════════
top_upload, top_api, top_ai, top_export = st.columns([3.2, 2.1, 1.05, 1.05])

with top_upload:
    ui.v7_top_privacy_note()
    uploaded = st.file_uploader(
        "Upload your bank statement",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
        help="Upload a CSV or Excel bank statement with date, description, and amount information.",
    )

with top_api:
    api_key = st.text_input(
        "API key",
        type="password",
        placeholder="sk-ant-… for AI categorisation",
        label_visibility="visible",
        help="Optional. Enables AI-assisted categorisation/insights.",
    )

with top_ai:
    st.write("")
    run_ai = st.button("✦ AI Insights", use_container_width=True)

with top_export:
    st.write("")
    export_placeholder = st.empty()


# ══════════════════════════════════════════════════════════════════════════════
# EMPTY STATE
# ══════════════════════════════════════════════════════════════════════════════
if uploaded is None:
    st.markdown(
        """
        <div class="v7-card" style="margin-top:12px;padding:26px;">
            <div style="font-size:22px;font-weight:700;color:#101828;margin-bottom:6px;">
                Welcome to Money Health Agent
            </div>
            <div style="font-size:13px;color:#667085;line-height:1.6;max-width:760px;">
                Upload a bank statement to turn raw transactions into a clear money story.
                You will see your income, spending, money left over, savings rate,
                spending split, budget check, insights, and transactions to review.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# PARSE → CATEGORISE → FLAG
# Uses existing backend logic.
# parser.py already handles messy CSV/Excel formats and amount parsing.
# categoriser.py already handles regex categorisation, optional AI fallback,
# confidence scoring, and review flags.
# ══════════════════════════════════════════════════════════════════════════════
key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")

file_key = f"v7_master_{uploaded.name}_{uploaded.size}"
meta_key = f"v7_meta_{uploaded.name}_{uploaded.size}"

if file_key not in st.session_state:
    with st.spinner("Reading and categorising your transactions…"):
        try:
            raw_bytes = uploaded.read()

            master_df, meta = parse_statement(
                raw_bytes,
                key or None,
                filename=uploaded.name,
            )

            master_df = add_categories(master_df, key or None)
            master_df = flag_transactions(master_df)

            # Normalise review status for UI
            if "Flag" in master_df.columns:
                master_df["ReviewStatus"] = master_df["Flag"].apply(
                    lambda value: "Review" if bool(value) else "Auto"
                )
            else:
                master_df["ReviewStatus"] = "Auto"

            st.session_state[file_key] = master_df
            st.session_state[meta_key] = meta

        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.stop()

master_df = st.session_state[file_key]
meta = st.session_state[meta_key]

sym = getattr(meta, "currency_symbol", "$") or "$"

if getattr(meta, "warnings", None):
    for warning in meta.warnings:
        st.warning(warning)


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT BUTTON
# ══════════════════════════════════════════════════════════════════════════════
export_df = master_df.copy()

if "Date" in export_df.columns:
    export_df["Date"] = pd.to_datetime(export_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

export_placeholder.download_button(
    "⬇ Export CSV",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name="money_health_transactions.csv",
    mime="text/csv",
    use_container_width=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# FILTER ROW
# ══════════════════════════════════════════════════════════════════════════════
filter_1, filter_2, filter_3 = st.columns(3)

with filter_1:
    selected_month = st.selectbox(
        "Month",
        ["All months"] + sorted(master_df["Month"].dropna().unique().tolist()),
    )

with filter_2:
    selected_category = st.selectbox(
        "Category",
        ["All categories"] + sorted(master_df["Category"].dropna().unique().tolist()),
    )

with filter_3:
    selected_type = st.selectbox(
        "Type",
        ["All types", "Income", "Expense", "Transfer"],
    )

selected_month = None if selected_month == "All months" else selected_month
selected_category = None if selected_category == "All categories" else selected_category
selected_type = None if selected_type == "All types" else selected_type


# ══════════════════════════════════════════════════════════════════════════════
# NAVIGATION PILLS
# V7 requirement: Overview active by default, custom pill style.
# For Stage 1, all sections remain visible in Overview.
# Later we can conditionally hide/show by section.
# ══════════════════════════════════════════════════════════════════════════════
sections = ["Overview", "Spending", "Income", "Subscriptions", "Bills"]

active_section = st.radio(
    "Section",
    sections,
    index=0,
    horizontal=True,
    label_visibility="collapsed",
    key="v7_section",
)


# ══════════════════════════════════════════════════════════════════════════════
# FILTER DATA
# ══════════════════════════════════════════════════════════════════════════════
fdf = master_df.copy()

if selected_month:
    fdf = fdf[fdf["Month"] == selected_month]

if selected_category:
    fdf = fdf[fdf["Category"] == selected_category]

if selected_type:
    fdf = fdf[fdf["Type"] == selected_type]

exp_df = fdf[fdf["Type"] == "Expense"]


# ══════════════════════════════════════════════════════════════════════════════
# COMPUTE METRICS
# Uses metrics.py so app remains a thin orchestrator.
# ══════════════════════════════════════════════════════════════════════════════
exp_by_cat = m.expense_by_category(fdf)
top_cat = exp_by_cat.iloc[0]["Category"] if not exp_by_cat.empty else None

period = m.compute_period_metrics(
    fdf,
    top_category=top_cat,
)

top_txns = m.top_expenses(fdf, n=4)
subs = m.subscription_breakdown(fdf)
monthly_df = m.monthly_income_vs_expense(master_df)
sr_trend = m.savings_rate_by_month(master_df)

review_count = 0

if "ReviewStatus" in fdf.columns:
    review_count = int((fdf["ReviewStatus"] == "Review").sum())
elif "NeedsReview" in fdf.columns:
    review_count = int(fdf["NeedsReview"].sum())


# ══════════════════════════════════════════════════════════════════════════════
# HERO SECTION
# Left: dark Money Health Score
# Right: 2x2 KPI grid
# ══════════════════════════════════════════════════════════════════════════════
hero_left, hero_right = st.columns([1.7, 1])

with hero_left:
    ui.v7_hero_score_card(
        score=period.health_score,
        score_label=period.score_label,
        headline=period.verdict_headline,
        earned=period.total_income,
        spent=period.total_expense,
        saved=period.net,
        savings_rate=period.savings_rate,
        sym=sym,
    )

with hero_right:
    ui.v7_kpi_grid(
        money_left=period.net,
        savings_rate=period.savings_rate,
        daily_spend=period.avg_daily_spend,
        review_count=review_count,
        sym=sym,
    )


# ══════════════════════════════════════════════════════════════════════════════
# WHERE DID THE MONEY GO?
# V7-style main dashboard section.
# ══════════════════════════════════════════════════════════════════════════════
ui.v7_section_header(
    "Where did the money go?",
    "A simple breakdown of how money moved during this selected period.",
)

money_left, money_right = st.columns([1.45, 1])

with money_left:
    if not exp_by_cat.empty:
        try:
            fig_cashflow = charts.waterfall_chart(
                exp_by_category=exp_by_cat,
                total_income=period.total_income,
                total_expense=period.total_expense,
                net=period.net,
                currency=sym,
            )
            _render_plotly_card("Cash flow story", fig_cashflow)
        except Exception:
            st.warning("Cash flow chart could not be rendered.")

    try:
        fig_monthly = charts.income_vs_spending_bar(
            monthly_df,
            currency=sym,
        )
        _render_plotly_card("Income vs spending by month", fig_monthly)
    except Exception:
        # Fallback if existing charts.py uses a different function name
        st.info("Monthly income vs spending chart is not connected yet.")

with money_right:
    ui.v7_spending_split_card(
        fixed_total=period.fixed_total,
        flex_total=period.flex_total,
        sym=sym,
    )

    budget_rows = _build_budget_rows(
        exp_by_cat=exp_by_cat,
        total_income=period.total_income,
    )

    ui.v7_budget_check_card(
        rows=budget_rows,
        sym=sym,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TOP SPENDING AREAS
# ══════════════════════════════════════════════════════════════════════════════
ui.v7_section_header(
    "Top spending areas",
    "Your largest categories and biggest individual transactions.",
)

spend_left, spend_right = st.columns([1, 1])

with spend_left:
    top_category_rows = _build_top_category_rows(
        exp_by_cat=exp_by_cat,
        total_expense=period.total_expense,
    )
    ui.v7_top_categories_card(top_category_rows, sym=sym)

with spend_right:
    big_spend_rows = _build_big_spend_rows(top_txns)
    ui.v7_big_spends_card(big_spend_rows, sym=sym)


# ══════════════════════════════════════════════════════════════════════════════
# SUBSCRIPTIONS / SAVINGS / INSIGHTS
# Compact product-style cards.
# ══════════════════════════════════════════════════════════════════════════════
ui.v7_section_header(
    "Insights & actions",
    "Plain-English guidance to help users understand what to check next.",
)

insights = _build_insights(period, exp_by_cat, top_txns)
ui.v7_insight_cards(insights)


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTION EXPLORER
# Stage 1 uses a compact preview table.
# Later stage: connect full search, filters, pagination, and review workflow.
# ══════════════════════════════════════════════════════════════════════════════
ui.v7_section_header(
    "Transaction explorer",
    "Review individual transactions and check categories.",
)

search_col, status_col = st.columns([2, 1])

with search_col:
    search_text = st.text_input(
        "Search transactions",
        placeholder="Search description, category, amount…",
        label_visibility="collapsed",
    )

with status_col:
    review_filter = st.selectbox(
        "Review status",
        ["All", "Review", "Auto"],
        label_visibility="collapsed",
    )

table_df = fdf.copy()

if search_text:
    query = search_text.strip().lower()

    text_cols = ["Description", "Category", "Type", "ReviewStatus"]

    mask = pd.Series(False, index=table_df.index)

    for col in text_cols:
        if col in table_df.columns:
            mask = mask | table_df[col].astype(str).str.lower().str.contains(query, na=False)

    table_df = table_df[mask]

if review_filter != "All" and "ReviewStatus" in table_df.columns:
    table_df = table_df[table_df["ReviewStatus"] == review_filter]

table_df = table_df.sort_values("Date", ascending=False)

ui.v7_transaction_explorer_table(
    table_df,
    sym=sym,
    max_rows=14,
)

st.caption(
    "Money Health Agent is for personal tracking and education only. "
    "It does not provide financial, tax, credit, or investment advice."
)