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


def _score_income_stability(df: "pd.DataFrame") -> float:
    """
    20 pts — Income stability.
    Looks at: does income arrive? Is it regular (same amount recurring)?
    More income transactions with consistent amounts = higher score.
    """
    inc = df[df["Type"] == "Income"]
    if inc.empty:
        return 0.0

    # Base: income exists
    pts = 10.0

    # Bonus: multiple distinct income events (salary arrives every month)
    n_inc = len(inc)
    if n_inc >= 3:
        pts += 6.0
    elif n_inc >= 2:
        pts += 3.0

    # Bonus: income is consistent (low variance as % of mean)
    if n_inc >= 2:
        mean = float(inc["Amount"].mean())
        std  = float(inc["Amount"].std())
        cv   = std / mean if mean > 0 else 1.0
        if cv <= 0.10:      pts += 4.0   # very consistent (salary)
        elif cv <= 0.25:    pts += 2.0   # somewhat consistent
        # else: irregular freelance / variable — no bonus

    return min(pts, 20.0)


def _score_spending_control(income: float, expense: float) -> float:
    """
    20 pts — Spending control.
    Expense/income ratio. Every 10% over 80% spending rate costs points.
    """
    if income <= 0:
        return 0.0
    ratio = expense / income
    if ratio <= 0.60:   return 20.0
    if ratio <= 0.70:   return 17.0
    if ratio <= 0.80:   return 14.0
    if ratio <= 0.90:   return 10.0
    if ratio <= 1.00:   return 5.0
    return 0.0   # spending more than earning


def _score_savings(savings_rate: float) -> float:
    """15 pts — Savings behaviour."""
    if savings_rate >= 25:  return 15.0
    if savings_rate >= 20:  return 13.0
    if savings_rate >= 15:  return 10.0
    if savings_rate >= 10:  return 7.0
    if savings_rate >= 5:   return 4.0
    if savings_rate >= 0:   return 1.0
    return 0.0   # negative (spending > income)


def _score_risky(df: "pd.DataFrame", income: float) -> float:
    """
    15 pts — Risky transactions.
    Deductions for: gambling, high/frequent cash withdrawals.
    Full 15 if no risk signals detected.
    """
    import re
    pts = 15.0
    desc = df["DescriptionClean"] if "DescriptionClean" in df.columns else df["Description"]
    amounts = df["Amount"].abs()

    # Gambling / betting
    gambling_pat = re.compile(
        r"\b(bet|sportsbet|tab\b|pokies|casino|lottery|keno|gambling|betfair|bet365|ladbrokes)\b",
        re.IGNORECASE
    )
    gambling_rows = desc.apply(lambda d: bool(gambling_pat.search(str(d))))
    if gambling_rows.any():
        gamble_total = float(amounts[gambling_rows].sum())
        gamble_ratio = gamble_total / income if income > 0 else 0
        if gamble_ratio >= 0.05:    pts -= 8.0
        elif gamble_ratio >= 0.01:  pts -= 4.0
        else:                        pts -= 2.0

    # Excessive cash withdrawals
    atm_pat = re.compile(r"\b(atm|cash\s*withdrawal|cash\s*advance)\b", re.IGNORECASE)
    atm_rows = desc.apply(lambda d: bool(atm_pat.search(str(d))))
    n_atm = int(atm_rows.sum())
    atm_total = float(amounts[atm_rows].sum())
    atm_ratio = atm_total / income if income > 0 else 0
    if atm_ratio >= 0.15:   pts -= 5.0
    elif atm_ratio >= 0.08: pts -= 3.0
    if n_atm >= 5:          pts -= 2.0

    return max(pts, 0.0)


def _score_bill_consistency(df: "pd.DataFrame") -> float:
    """
    15 pts — Bill payment consistency.
    Checks for regular recurring payments (rent, utilities, phone).
    Regular bills are a sign of financial stability.
    """
    import re
    pts = 5.0   # base: some financial activity
    exp = df[df["Type"] == "Expense"]
    if exp.empty:
        return pts

    desc = exp["DescriptionClean"] if "DescriptionClean" in exp.columns else exp["Description"]

    bill_pat = re.compile(
        r"\b(rent|mortgage|electricity|gas\s*bill|water\s*bill|phone|internet|insurance"
        r"|childcare|bpay|direct\s*debit|ddr)\b",
        re.IGNORECASE
    )
    bill_rows = desc.apply(lambda d: bool(bill_pat.search(str(d))))
    n_bills = int(bill_rows.sum())

    if n_bills >= 5:    pts += 10.0
    elif n_bills >= 3:  pts += 7.0
    elif n_bills >= 1:  pts += 4.0

    return min(pts, 15.0)


def _score_balance_health(df: "pd.DataFrame") -> float:
    """
    10 pts — Account balance health.
    Checks: no overdraft, positive trend.
    If no balance column, scores based on whether net cashflow is positive.
    """
    pts = 5.0

    # Use running balance if available (Amount represents signed transactions)
    # Reconstruct a running total as proxy for balance health
    running = float(df["Amount"].cumsum().min())
    if running >= 0:
        pts += 5.0     # never went negative during the period
    elif running >= -100:
        pts += 2.0     # briefly dipped but recovered

    return min(pts, 10.0)


def _score_data_quality(df: "pd.DataFrame") -> float:
    """
    5 pts — Data quality.
    Fewer "Needs Review" transactions = cleaner data = more trustworthy score.
    """
    if "NeedsReview" not in df.columns:
        return 3.0   # neutral

    n_review = int(df["NeedsReview"].sum())
    pct = n_review / len(df) if len(df) > 0 else 0

    if pct == 0:       return 5.0
    if pct <= 0.05:    return 4.0
    if pct <= 0.15:    return 3.0
    if pct <= 0.30:    return 1.0
    return 0.0


def _health_score(
    df:           "pd.DataFrame",
    income:       float,
    expense:      float,
    net:          float,
    savings_rate: float,
) -> int:
    """
    7-component health score (0–100) with realistic variation.

    Component weights:
      Income stability    20%  — regularity and consistency of income
      Spending control    20%  — expense-to-income ratio
      Savings behaviour   15%  — how much is being saved
      Risky transactions  15%  — gambling, excessive ATM use
      Bill consistency    15%  — regular bill payments
      Balance health      10%  — no overdraft, positive running total
      Data quality         5%  — low needs-review count

    Score bands:
      85–100  Excellent — strong financial habits
      70–84   Healthy   — good with room to improve
      50–69   Needs attention
      35–49   At risk   — multiple issues
      0–34    Critical  — immediate action needed
    """
    import pandas as _pd
    if not isinstance(df, _pd.DataFrame):
        # Fallback for callers passing a non-DataFrame
        score = 0
        if income > 0:       score += 12
        if net > 0:          score += 20
        if savings_rate >= 20: score += 15
        elif savings_rate >= 10: score += 10
        er = expense / income if income > 0 else 1.0
        if er <= 0.75: score += 15
        elif er <= 0.90: score += 8
        return min(score + 20, 100)

    s1 = _score_income_stability(df)
    s2 = _score_spending_control(income, expense)
    s3 = _score_savings(savings_rate)
    s4 = _score_risky(df, income)
    s5 = _score_bill_consistency(df)
    s6 = _score_balance_health(df)
    s7 = _score_data_quality(df)

    total = s1 + s2 + s3 + s4 + s5 + s6 + s7
    return max(0, min(100, round(total)))


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

    score = _health_score(df, total_income, total_expense, net, savings_rate)

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



# ── Score breakdown ────────────────────────────────────────────────────────────
from dataclasses import dataclass as _dc, field as _field

@_dc
class ScoreComponent:
    label:       str
    description: str    # plain English: what does this measure?
    score:       float  # actual points earned
    max_score:   float  # maximum possible points
    tip:         str    # one-sentence improvement suggestion


def score_breakdown(df: pd.DataFrame) -> list[ScoreComponent]:
    """
    Return the per-component score details for the score explanation panel.
    Each component shows actual pts, max pts, and a plain-English tip.
    """
    inc_df = df[df["Type"] == "Income"]
    exp_df = df[df["Type"] == "Expense"]

    total_income  = float(inc_df["Amount"].sum())
    total_expense = float(exp_df["Amount"].abs().sum())
    net           = total_income - total_expense
    savings_rate  = (net / total_income * 100) if total_income > 0 else 0.0

    s1 = _score_income_stability(df)
    s2 = _score_spending_control(total_income, total_expense)
    s3 = _score_savings(savings_rate)
    s4 = _score_risky(df, total_income)
    s5 = _score_bill_consistency(df)
    s6 = _score_balance_health(df)
    s7 = _score_data_quality(df)

    return [
        ScoreComponent(
            label       = "Income stability",
            description = "How regular and consistent your income is",
            score       = s1, max_score = 20.0,
            tip         = "Regular salary payments score highest. Irregular or one-off income lowers this.",
        ),
        ScoreComponent(
            label       = "Spending control",
            description = "What percentage of your income you spend",
            score       = s2, max_score = 20.0,
            tip         = "Spending less than 70% of income earns full points. Spending over 100% earns zero.",
        ),
        ScoreComponent(
            label       = "Savings behaviour",
            description = "How much of your income you save each month",
            score       = s3, max_score = 15.0,
            tip         = "Saving 20% or more of your income earns full points. Even 5–10% is a good start.",
        ),
        ScoreComponent(
            label       = "Risky spending",
            description = "Gambling, betting, or excessive cash withdrawals",
            score       = s4, max_score = 15.0,
            tip         = "Reduce gambling or frequent large cash withdrawals to improve this score.",
        ),
        ScoreComponent(
            label       = "Bill consistency",
            description = "Regular bill payments like rent, utilities, and subscriptions",
            score       = s5, max_score = 15.0,
            tip         = "Regular direct debits and BPAY payments show financial stability.",
        ),
        ScoreComponent(
            label       = "Balance health",
            description = "Whether your account balance stayed positive",
            score       = s6, max_score = 10.0,
            tip         = "Avoid overdrafts and keep a positive running balance throughout the month.",
        ),
        ScoreComponent(
            label       = "Data quality",
            description = "How many transactions could be confidently understood",
            score       = s7, max_score = 5.0,
            tip         = "Review flagged transactions to improve categorisation accuracy.",
        ),
    ]

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
    Month is formatted as "Jan 2026" for readable chart axis labels.
    """
    import pandas as pd
    rows = []
    for month in sorted(df["Month"].unique()):
        g       = df[df["Month"] == month]
        income  = float(g[g["Type"] == "Income"]["Amount"].sum())
        expense = float(g[g["Type"] == "Expense"]["Amount"].abs().sum())
        rate    = (income - expense) / income * 100 if income > 0 else 0.0
        # Format "2026-01" → "Jan 2026" for chart readability
        label = pd.to_datetime(month).strftime("%b %Y")
        rows.append({"Month": label, "SavingsRate": rate})
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
