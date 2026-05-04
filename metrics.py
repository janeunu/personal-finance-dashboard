"""
metrics.py
All financial calculations as pure functions.

Rules:
  • No Streamlit imports.
  • No chart logic.
  • Every function takes a DataFrame and returns a scalar, Series, or DataFrame.
  • All functions are independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import (
    FIXED_CATEGORIES,
    SUBSCRIPTION_CATEGORIES,
    SCORE_EXCELLENT,
    SCORE_HEALTHY,
    SCORE_ATTENTION,
)


# ── Core period summary ───────────────────────────────────────────────────────
@dataclass
class PeriodMetrics:
    """All scalar metrics for a filtered period."""
    total_income:    float
    total_expense:   float
    net:             float
    savings_rate:    float   # percentage
    fixed_total:     float
    flex_total:      float
    flex_pct:        float   # percentage
    sub_total:       float
    avg_daily_spend: float
    spending_days:   int
    txn_count:       int
    health_score:    int     # 0-100
    score_label:     str     # "Excellent" | "Healthy" | "Needs Attention" | "At Risk"
    verdict_headline: str    # plain-English sentence for the hero banner
    # Note: score colours are owned by ui.py — not duplicated here


def _score_label(score: int) -> str:
    if score >= SCORE_EXCELLENT: return "Excellent"
    if score >= SCORE_HEALTHY:   return "Healthy"
    if score >= SCORE_ATTENTION: return "Needs attention"
    return "At risk"


def _verdict_headline(
    score:       int,
    net:         float,
    savings_rate: float,
    top_category: str | None,
) -> str:
    """
    One warm, plain-English sentence that answers "Am I okay?"
    Written for someone with no finance background.
    Varies based on the actual financial situation — not generic.
    """
    tc = top_category or "your spending"

    if score >= SCORE_EXCELLENT:
        if savings_rate >= 30:
            return f"Excellent — you're saving {savings_rate:.0f}% of your income this month"
        return "You're in great shape — income is well ahead of spending"

    if score >= SCORE_HEALTHY:
        return "You're doing well — keep watching your spending to go further"

    if score >= SCORE_ATTENTION:
        if net < 0:
            return "Spending is slightly ahead of income — a few small cuts will fix that"
        return f"Some areas need attention — {tc.lower()} is the best place to start"

    # At risk
    if net < 0:
        return "Spending is higher than income right now — let's find where to cut"
    return "Your finances need attention — the actions below will help most"


def _health_score(
    income:       float,
    expense:      float,
    net:          float,
    savings_rate: float,
    sub_total:    float,
) -> int:
    """
    Score out of 100 based on four factors:
      20 pts — has income
      25 pts — positive net cashflow
      25 pts — savings rate (≥20% full, ≥10% partial)
      15 pts — expense ratio vs income
      15 pts — subscription burden vs income
    """
    score = 0

    if income > 0:
        score += 20

    if net > 0:
        score += 25

    if savings_rate >= 20:
        score += 25
    elif savings_rate >= 10:
        score += 15
    elif savings_rate > 0:
        score += 8

    expense_ratio = expense / income if income > 0 else 1.0
    if expense_ratio <= 0.75:
        score += 15
    elif expense_ratio <= 0.90:
        score += 8

    sub_ratio = sub_total / income if income > 0 else 0.0
    if sub_ratio <= 0.03:
        score += 15
    elif sub_ratio <= 0.06:
        score += 8

    return min(score, 100)


def compute_period_metrics(
    df:           pd.DataFrame,
    top_category: str | None = None,
) -> PeriodMetrics:
    """
    Compute all scalar metrics for a (filtered) DataFrame.
    Pass top_category (highest-spend category) so the verdict headline
    can reference it specifically in plain English.
    """
    inc_df = df[df["Type"] == "Income"]
    exp_df = df[df["Type"] == "Expense"]

    total_income  = float(inc_df["Amount"].sum())
    total_expense = float(exp_df["Amount"].abs().sum())
    net           = total_income - total_expense
    savings_rate  = (net / total_income * 100) if total_income > 0 else 0.0

    fixed_total = float(
        exp_df[exp_df["Category"].isin(FIXED_CATEGORIES)]["Amount"].abs().sum()
    )
    sub_total = float(
        exp_df[exp_df["Category"].isin(SUBSCRIPTION_CATEGORIES)]["Amount"].abs().sum()
    )
    flex_total    = max(total_expense - fixed_total, 0.0)
    flex_pct      = (flex_total / total_expense * 100) if total_expense > 0 else 0.0
    spending_days = int(exp_df["Day"].nunique())
    avg_daily     = total_expense / max(spending_days, 1)

    score = _health_score(total_income, total_expense, net, savings_rate, sub_total)

    return PeriodMetrics(
        total_income     = total_income,
        total_expense    = total_expense,
        net              = net,
        savings_rate     = savings_rate,
        fixed_total      = fixed_total,
        flex_total       = flex_total,
        flex_pct         = flex_pct,
        sub_total        = sub_total,
        avg_daily_spend  = avg_daily,
        spending_days    = spending_days,
        txn_count        = len(df),
        health_score     = score,
        score_label      = _score_label(score),
        verdict_headline = _verdict_headline(score, net, savings_rate, top_category),
    )


# ── Expense breakdown ─────────────────────────────────────────────────────────
def expense_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return expenses grouped by category, sorted descending by total."""
    exp_df = df[df["Type"] == "Expense"]
    if exp_df.empty:
        return pd.DataFrame(columns=["Category", "Total"])

    return (
        exp_df.groupby("Category", as_index=False)["Amount"]
        .apply(lambda x: x.abs().sum())
        .rename(columns={"Amount": "Total"})
        .sort_values("Total", ascending=False)
        .reset_index(drop=True)
    )


# ── Monthly savings rate trend ────────────────────────────────────────────────
def savings_rate_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame with Month and SavingsRate columns.
    Uses explicit iteration — avoids groupby.apply() deprecation in pandas 3.x.
    """
    rows = []
    for month in sorted(df["Month"].unique()):
        g       = df[df["Month"] == month]
        income  = float(g[g["Type"] == "Income"]["Amount"].sum())
        expense = float(g[g["Type"] == "Expense"]["Amount"].abs().sum())
        rate    = (income - expense) / income * 100 if income > 0 else 0.0
        rows.append({"Month": month, "SavingsRate": rate})
    return pd.DataFrame(rows)


# ── Day-of-week spending ──────────────────────────────────────────────────────
def spend_by_dow(df: pd.DataFrame) -> pd.DataFrame:
    """Return total expense per day of week, in Mon–Sun order."""
    from config import DAY_ORDER

    exp_df = df[df["Type"] == "Expense"]
    dow = (
        exp_df.groupby("DOW", as_index=True)["Amount"]
        .apply(lambda x: x.abs().sum())
        .reindex(DAY_ORDER, fill_value=0.0)
        .reset_index()
    )
    dow.columns = ["DOW", "Amount"]
    return dow


# ── Monthly income vs expense ─────────────────────────────────────────────────
def monthly_income_vs_expense(df: pd.DataFrame) -> pd.DataFrame:
    """Return a long-format DataFrame suitable for a grouped bar chart."""
    rows = []
    for month in sorted(df["Month"].unique()):
        g = df[df["Month"] == month]
        rows.append({"Month": month, "Type": "Income",
                     "Amount": float(g[g["Type"] == "Income"]["Amount"].sum())})
        rows.append({"Month": month, "Type": "Expense",
                     "Amount": float(g[g["Type"] == "Expense"]["Amount"].abs().sum())})
    return pd.DataFrame(rows)


# ── Top individual transactions ───────────────────────────────────────────────
def top_expenses(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    """Return the n largest individual expense rows."""
    return (
        df[df["Type"] == "Expense"]
        .nsmallest(n, "Amount")
        [["Date", "Description", "Amount", "Category"]]
        .reset_index(drop=True)
    )


# ── Subscription breakdown ────────────────────────────────────────────────────
def subscription_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-merchant subscription totals, sorted descending."""
    sub_df = df[df["Category"].isin(SUBSCRIPTION_CATEGORIES)]
    if sub_df.empty:
        return pd.DataFrame(columns=["Description", "Amount"])

    return (
        sub_df.groupby("Description", as_index=False)["Amount"]
        .apply(lambda x: x.abs().sum())
        .rename(columns={"Amount": "Amount"})
        .sort_values("Amount", ascending=False)
        .reset_index(drop=True)
    )


# ── Previous-period deltas ────────────────────────────────────────────────────
@dataclass
class PeriodDelta:
    prev_income:  float = 0.0
    prev_expense: float = 0.0
    prev_net:     float = 0.0


def previous_period(df: pd.DataFrame, current_month: str) -> PeriodDelta:
    """
    Return income/expense/net for the month preceding current_month.
    Returns zero-filled PeriodDelta if no previous month exists.
    """
    all_months = sorted(df["Month"].unique())
    if current_month not in all_months:
        return PeriodDelta()

    idx = all_months.index(current_month)
    if idx == 0:
        return PeriodDelta()

    prev_df     = df[df["Month"] == all_months[idx - 1]]
    prev_income = float(prev_df[prev_df["Type"] == "Income"]["Amount"].sum())
    prev_expense= float(prev_df[prev_df["Type"] == "Expense"]["Amount"].abs().sum())
    return PeriodDelta(
        prev_income  = prev_income,
        prev_expense = prev_expense,
        prev_net     = prev_income - prev_expense,
    )
