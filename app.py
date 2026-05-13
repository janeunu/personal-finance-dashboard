"""
app.py — Money Health Agent
───────────────────────────
This file is a thin orchestrator. It:
  1. Configures the page
  2. Renders the sidebar
  3. Handles file upload
  4. Calls parser → categoriser → metrics → charts → ui
  5. Renders each section in order

No business logic lives here. If you find yourself doing
calculations or building HTML strings in this file, move
that code to the appropriate module.

Module responsibilities
───────────────────────
  config.py      → constants (categories, colours, budgets)
  parser.py      → CSV ingestion, column detection, normalisation
  categoriser.py → AI + keyword transaction categorisation
  metrics.py     → financial calculations (pure functions)
  charts.py      → Plotly chart builders (pure functions)
  ui.py          → CSS, formatters, HTML component builders
"""

import os

import pandas as pd
import streamlit as st

import charts
import metrics as m
from metrics import monthly_income_vs_expense, score_breakdown, ScoreComponent
import ui
from categoriser import add_categories, flag_transactions
from config import BUDGET_GUIDE, ALL_CATEGORIES
from parser import parse_statement

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Money Health",
    page_icon  = "💰",
    layout     = "wide",
)
ui.inject_css()


# ══════════════════════════════════════════════════════════════════════════════
#  TOP BAR  (replaces sidebar — gives full width to dashboard content)
# ══════════════════════════════════════════════════════════════════════════════
col_upload, col_api, col_ai, col_export = st.columns([3, 2, 1, 1])

with col_upload:
    st.markdown(
        '<div class="mh-privacy">'
        "🔒 Your file stays in this session — never stored or shared."
        '</div>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Upload your bank statement — CSV or Excel, any bank",
        type=["csv", "xlsx", "xls"],
        label_visibility="collapsed",
        help="CSV or Excel. Needs at least a date, description, and amount column.",
    )

with col_api:
    api_key = st.text_input(
        "API Key (optional)",
        type="password",
        placeholder="sk-ant-… for AI categorisation",
        help="Enables AI-powered categorisation in any language.",
    )

with col_ai:
    st.markdown("<br>", unsafe_allow_html=True)
    run_ai = st.button("✦ AI Insights", use_container_width=True)

with col_export:
    st.markdown("<br>", unsafe_allow_html=True)
    ph_export = st.empty()

if uploaded is None:
    ui.onboarding_tiles()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  PARSE  →  CATEGORISE
# ══════════════════════════════════════════════════════════════════════════════
key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")


@st.cache_data(show_spinner=False)
def load_data(raw: bytes, api_key_used: str, fname: str = ""):
    """Cache parse + categorise together — re-runs only when file or key changes."""
    try:
        df, meta = parse_statement(raw, api_key_used or None, filename=fname)
    except TypeError:
        # Fallback: older parser.py without filename parameter
        df, meta = parse_statement(raw, api_key_used or None)
    df = add_categories(df, api_key_used or None)
    df = flag_transactions(df)
    return df, meta


with st.spinner("Reading and categorising your transactions…"):
    try:
        df, meta = load_data(uploaded.read(), key, fname=uploaded.name)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        st.stop()

sym = meta.currency_symbol or "$"

# Show user-facing warnings only (e.g. dropped rows) — not column mapping details
if meta.warnings:
    for w in meta.warnings:
        st.warning(w)

# ── Top filter bar (inline — no sidebar needed) ──────────────────────────────
ph_export.download_button(
    "⬇ Export CSV",
    data      = df.to_csv(index=False).encode("utf-8"),
    file_name = "money_health_transactions.csv",
    mime      = "text/csv",
    help      = "Export all transactions. For corrected categories, use the download button at the bottom of the page.",
    use_container_width = True,
)
f1, f2, f3, _ = st.columns([2, 2, 2, 4])
with f1:
    sel_month = st.selectbox("Month", ["All months"] + sorted(df["Month"].unique()),
                             label_visibility="visible")
with f2:
    sel_cat = st.selectbox("Category", ["All categories"] + sorted(df["Category"].unique()),
                           label_visibility="visible")
with f3:
    sel_type = st.selectbox("Type", ["All types", "Income", "Expense", "Transfer"],
                            label_visibility="visible")

# Normalise filter values
sel_month = None if sel_month == "All months" else sel_month
sel_cat   = None if sel_cat == "All categories" else sel_cat
sel_type  = None if sel_type == "All types" else sel_type


# ══════════════════════════════════════════════════════════════════════════════
#  FILTER
# ══════════════════════════════════════════════════════════════════════════════
fdf = df.copy()
if sel_month:
    fdf = fdf[fdf["Month"] == sel_month]
if sel_cat:
    fdf = fdf[fdf["Category"] == sel_cat]
if sel_type:
    fdf = fdf[fdf["Type"] == sel_type]

exp_df = fdf[fdf["Type"] == "Expense"]


# ══════════════════════════════════════════════════════════════════════════════
#  COMPUTE
# ══════════════════════════════════════════════════════════════════════════════
exp_by_cat   = m.expense_by_category(fdf)           # computed first — needed for headline
top_cat      = exp_by_cat.iloc[0]["Category"] if not exp_by_cat.empty else None
period       = m.compute_period_metrics(fdf, top_category=top_cat)
sr_trend     = m.savings_rate_by_month(df)           # always full dataset for trend
dow_spend    = m.spend_by_dow(fdf)
top_txns     = m.top_expenses(fdf, n=3)
subs         = m.subscription_breakdown(fdf)
delta        = m.previous_period(df, sel_month) if sel_month else m.PeriodDelta()
monthly_df   = monthly_income_vs_expense(df)


# ══════════════════════════════════════════════════════════════════════════════
#  §0  VERDICT BANNER
#  Answers "Am I okay?" in under 3 seconds.
#  One score. One sentence. Three numbers.
# ══════════════════════════════════════════════════════════════════════════════

ui.verdict_banner(
    score        = period.health_score,
    score_label  = period.score_label,
    headline     = period.verdict_headline,
    sub_html     = (
        f"Earned <b>{ui.fmt_money(period.total_income, sym)}</b>"
        f" &nbsp;&middot;&nbsp; "
        f"Spent <b>{ui.fmt_money(period.total_expense, sym)}</b>"
        f" &nbsp;&middot;&nbsp; "
        f"Saved <b>{ui.fmt_money(period.net, sym, signed=True)}</b>"
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  KPI STRIP  — three numbers every user understands immediately
#
#  Deliberately three (not four):
#    1. Money left over  — the headline result, positive or negative
#    2. Saved this month — savings rate as %, relatable goal
#    3. Avg daily spend  — grounding number, easy to act on
#
#  Removed: "Flexible spending" — finance jargon unfamiliar to everyday users.
# ══════════════════════════════════════════════════════════════════════════════

k1, k2, k3, k4 = st.columns(4)

# ── KPI 1: Money left over ────────────────────────────────────────────────────
with k1:
    net_color = ui.COLOR["income"] if period.net >= 0 else ui.COLOR["expense"]
    ui.kpi_card(
        label         = "Money left over",
        value         = ui.fmt_money_kpi(period.net, sym, signed=True),
        value_color   = net_color,
        delta_html    = ui.delta_badge(period.net, delta.prev_net),
        delta_context = "vs last month",
    )

# ── KPI 2: Saved this month ───────────────────────────────────────────────────
with k2:
    sr = period.savings_rate
    if sr >= 20:
        sr_color   = ui.COLOR["income"]
        sr_context = f"Goal: 20% &nbsp;&middot;&nbsp; You&#39;re ahead"
    elif sr >= 10:
        sr_color   = ui.COLOR["accent"]
        sr_context = f"Goal: 20% &nbsp;&middot;&nbsp; Getting there"
    elif sr > 0:
        sr_color   = ui.COLOR["warning"]
        sr_context = f"Goal: 20% &nbsp;&middot;&nbsp; Keep improving"
    elif period.net >= 0:
        sr_color   = ui.COLOR["warning"]
        sr_context = "Nothing saved yet this period"
    else:
        sr_color   = ui.COLOR["expense"]
        sr_context = "Spending more than you earn"

    ui.kpi_card(
        label         = "% of income saved",
        value         = ui.fmt_pct(sr, decimals=0),
        value_color   = sr_color,
        delta_html    = f'<span class="neu">{sr_context}</span>',
        delta_context = "",
    )

# ── KPI 3: Avg daily spend ────────────────────────────────────────────────────
with k3:
    ui.kpi_card(
        label         = "Daily spend (avg)",
        value         = ui.fmt_money_kpi(period.avg_daily_spend, sym),
        value_color   = ui.COLOR["text_primary"],
        delta_html    = f'<span class="neu">Across {period.spending_days} days</span>',
        delta_context = "",
    )

# ── KPI 4: Needs Review count (if any), otherwise biggest cost ──────────────
with k4:
    needs_review_count = int(fdf["NeedsReview"].sum()) if "NeedsReview" in fdf.columns else 0
    if needs_review_count > 0:
        nr_color = ui.COLOR["warning"] if needs_review_count < 10 else ui.COLOR["expense"]
        ui.kpi_card(
            label         = "Check these",
            value         = str(needs_review_count),
            value_color   = nr_color,
            delta_html    = '<span class="neu">Transactions to double-check</span>',
            delta_context = "",
        )
    elif top_cat and not exp_by_cat.empty:
        top_amt = float(exp_by_cat.iloc[0]["Total"])
        ui.kpi_card(
            label         = "Biggest cost",
            value         = ui.fmt_money_kpi(top_amt, sym),
            value_color   = ui.COLOR["expense"],
            delta_html    = f'<span class="neu">{top_cat}</span>',
            delta_context = "",
        )
    else:
        ui.kpi_card(
            label         = "Transactions",
            value         = str(period.txn_count),
            value_color   = ui.COLOR["text_primary"],
            delta_html    = '<span class="neu">This period</span>',
            delta_context = "",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  §2  SPENDING DONUT  +  INCOME VS EXPENSE  +  BUDGET CHECK
#
#  Chart titles are plain <p> elements above the chart, NOT card wrappers.
#  card_start()/card_end() around st.plotly_chart() create ghost boxes because
#  Streamlit wraps each st.* call in its own container — the HTML div from
#  card_start() is not a real parent of the subsequent plotly chart element.
#
#  Correct pattern: one st.markdown() call = one real HTML block.
#  Charts sit directly on the page — their white paper_bgcolor is the "card".
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Where did the money go?", "A breakdown of how your money was spent this period.")
col_donut, col_right = st.columns([1.2, 1])

with col_donut:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:.06em;color:#64748B;margin-bottom:6px">Spending breakdown</p>',
        unsafe_allow_html=True,
    )
    if not exp_by_cat.empty:
        st.plotly_chart(
            charts.spending_donut(exp_by_cat, sym),
            use_container_width=True, config={"displayModeBar": False},
        )
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:.06em;color:#64748B;margin:10px 0 6px">Income vs spending by month</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        charts.income_vs_expense_bars(monthly_df, sym),
        use_container_width=True, config={"displayModeBar": False},
    )

with col_right:
    # Spending split — entire card in one st.markdown() → renders correctly
    st.markdown(
        f'<div class="mh-card" style="margin-bottom:10px">'
        f'<div class="mh-card-title">Your spending split</div>'
        f'<div style="margin-bottom:14px">'
        f'<div style="font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.06em;color:#94A3B8;margin-bottom:4px">Fixed bills</div>'
        f'<div style="font-size:24px;font-weight:600;color:#374151;font-variant-numeric:tabular-nums;letter-spacing:-0.5px">{ui.fmt_money(period.fixed_total, sym)}</div>'
        f'<div style="font-size:12px;color:#94A3B8;margin-top:2px">Rent, utilities, insurance</div>'
        f'</div>'
        f'<div style="height:0.5px;background:#F1F5F9;margin-bottom:14px"></div>'
        f'<div>'
        f'<div style="font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.06em;color:#94A3B8;margin-bottom:4px">Cuttable spend</div>'
        f'<div style="font-size:24px;font-weight:600;color:#2563EB;font-variant-numeric:tabular-nums;letter-spacing:-0.5px">{ui.fmt_money(period.flex_total, sym)}</div>'
        f'<div style="font-size:12px;color:#94A3B8;margin-top:2px">Groceries, dining, shopping</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Budget check — all bars built as one HTML string, rendered in ONE call
    bars_html = ""
    shown = 0
    for cat, rec_pct in BUDGET_GUIDE.items():
        actual = float(exp_by_cat[exp_by_cat["Category"] == cat]["Total"].sum())
        if actual == 0:
            continue
        actual_pct = (actual / period.total_income * 100) if period.total_income > 0 else 0.0
        bar_w = min(actual_pct / rec_pct * 100, 108) if rec_pct else 0.0
        if actual_pct > rec_pct:
            color, status, sc = "#E11D48", "Over budget", "#E11D48"
        elif actual_pct > rec_pct * 0.85:
            color, status, sc = "#D97706", "Near limit", "#D97706"
        else:
            color, status, sc = "#059669", "On track", "#059669"
        bars_html += (
            f'<div style="margin-bottom:13px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'font-size:12.5px;color:#374151;font-weight:500;margin-bottom:5px">'
            f'<span>{cat} <span style="color:#94A3B8;font-weight:400;font-size:11.5px">{ui.fmt_money(actual, sym)}</span></span>'
            f'<span style="font-size:11px;font-weight:500;color:{sc}">{status}</span></div>'
            f'<div style="background:#F1F5F9;border-radius:3px;height:4px;overflow:hidden">'
            f'<div style="width:{bar_w:.1f}%;height:100%;border-radius:3px;background:{color}"></div>'
            f'</div></div>'
        )
        shown += 1
        if shown == 5:
            break

    if bars_html:
        st.markdown(
            f'<div class="mh-card"><div class="mh-card-title">Budget check</div>{bars_html}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  §3  TREEMAP  +  TOP TRANSACTIONS  +  SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Top spending areas", "Your biggest individual transactions and any recurring subscriptions.")
col_top, col_detail = st.columns([1.1, 1])

with col_top:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:.06em;color:#64748B;margin-bottom:6px">Top categories</p>',
        unsafe_allow_html=True,
    )
    if not exp_by_cat.empty:
        bars_html = ""
        for _, row in exp_by_cat.head(6).iterrows():
            pct   = row["Total"] / period.total_expense * 100 if period.total_expense > 0 else 0
            bar_w = min(pct, 100)
            bars_html += (
                f'<div style="margin-bottom:10px">'
                f'<div style="display:flex;justify-content:space-between;font-size:13px;color:#374151;margin-bottom:3px">'
                f'<span style="font-weight:500">{row["Category"]}</span>'
                f'<span style="color:#6941C6;font-weight:600;font-variant-numeric:tabular-nums">{ui.fmt_money(row["Total"], sym)}</span>'
                f'</div>'
                f'<div style="background:#EAECF0;border-radius:3px;height:5px;overflow:hidden">'
                f'<div style="width:{bar_w:.1f}%;height:100%;background:#6941C6;border-radius:3px"></div>'
                f'</div></div>'
            )
        st.markdown(
            f'<div class="mh-card">{bars_html}</div>',
            unsafe_allow_html=True,
        )

with col_detail:
    st.markdown('<p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;margin-bottom:10px">Biggest single spends</p>', unsafe_allow_html=True)
    for _, row in top_txns.iterrows():
        ui.transaction_card(
            amount      = ui.fmt_money(abs(row["Amount"]), sym),
            description = str(row["Description"]),
            date        = row["Date"].strftime("%d %b %Y"),
            category    = str(row["Category"]),
        )

    if not subs.empty:
        st.markdown('<p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;margin:16px 0 10px">Subscriptions</p>', unsafe_allow_html=True)
        rows_html = "".join(
            f'<div class="mh-sub-row">'
            f'<span class="mh-sub-name">{r["Description"]}</span>'
            f'<span class="mh-sub-amount">{ui.fmt_money(r["Amount"], sym)}</span>'
            f'</div>'
            for _, r in subs.iterrows()
        )
        ui.subscription_list(rows_html, ui.fmt_money(period.sub_total, sym))


# ══════════════════════════════════════════════════════════════════════════════
#  §4  DAY-OF-WEEK  +  SAVINGS RATE TREND  +  BALANCE TREND
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Spending patterns", "When and how your spending behaviour changes over time.")

# Balance trend — shown first as it's the most intuitive ("is my balance going up?")
_bal_fig = charts.balance_trend(fdf, sym)
if _bal_fig is not None:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;' +
        'letter-spacing:.06em;color:#64748B;margin-bottom:4px">Balance over time</p>' +
        '<p style="font-size:12.5px;color:#98A2B3;margin-bottom:6px">'
        'Is your account balance going up or down over this period?</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        _bal_fig,
        use_container_width=True, config={"displayModeBar": False},
    )

col_dow, col_sr = st.columns(2)

with col_dow:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;' +
        'letter-spacing:.06em;color:#64748B;margin-bottom:6px">When do you spend?</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        charts.dow_bar(dow_spend, sym),
        use_container_width=True, config={"displayModeBar": False},
    )

with col_sr:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;' +
        'letter-spacing:.06em;color:#64748B;margin-bottom:6px">Savings rate over time</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        charts.savings_trend(sr_trend),
        use_container_width=True, config={"displayModeBar": False},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  §5  INSIGHTS  ·  ACTIONS  ·  AI COACH  (tabbed)
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Insights & actions", "Plain-English summary of what happened and what to do next.")
tab_story, tab_actions, tab_ai = st.tabs(["What happened", "What to do", "AI insights"])

# ── Tab 1: Story ──────────────────────────────────────────────────────────────
with tab_story:
    story_items = []

    earned = ui.fmt_money(period.total_income, sym)
    spent  = ui.fmt_money(period.total_expense, sym)
    if period.net >= 0:
        outcome = f"You came out <b>{ui.fmt_money(period.net, sym)} ahead</b>."
    else:
        outcome = f"You overspent by <b>{ui.fmt_money(abs(period.net), sym)}</b>."
    story_items.append(f"You earned <b>{earned}</b> and spent <b>{spent}</b>. {outcome}")

    if not exp_by_cat.empty:
        top = exp_by_cat.iloc[0]
        pct = top["Total"] / period.total_expense * 100 if period.total_expense > 0 else 0
        story_items.append(
            f"<b>{top['Category']}</b> was your biggest cost at "
            f"{ui.fmt_money(top['Total'], sym)} ({pct:.0f}% of all spending)."
        )

    story_items.append(
        f"<b>{period.flex_pct:.0f}%</b> of your spending ({ui.fmt_money(period.flex_total, sym)}) "
        f"is discretionary and cuttable. The other {100 - period.flex_pct:.0f}% "
        f"({ui.fmt_money(period.fixed_total, sym)}) are fixed bills."
    )

    if period.sub_total > 0:
        story_items.append(
            f"Subscriptions cost <b>{ui.fmt_money(period.sub_total, sym)}</b> this period."
        )

    if period.savings_rate >= 20:
        story_items.append(
            f"A savings rate of <b>{period.savings_rate:.1f}%</b> is excellent — "
            "you're genuinely building a financial cushion."
        )
    elif period.savings_rate < 10 and period.total_income > 0:
        story_items.append(
            f"A savings rate of <b>{period.savings_rate:.1f}%</b> is below the 10–20% target. "
            "Small automated transfers help build the habit."
        )

    ca, cb = st.columns(2)
    for i, item in enumerate(story_items):
        (ca if i % 2 == 0 else cb).markdown(
            f'<div class="ins">{item}</div>', unsafe_allow_html=True
        )

# ── Tab 2: Actions ────────────────────────────────────────────────────────────
with tab_actions:
    actions = []

    if period.net < 0:
        actions.append(("🔴", "Spending exceeds income",
            f"You're over by {ui.fmt_money(abs(period.net), sym)}. "
            "Eating out and shopping are usually the fastest wins."))
    elif period.savings_rate < 10:
        actions.append(("🟡", "Boost your savings rate",
            f"At {period.savings_rate:.1f}% you're below the 10% floor. "
            f"Automate a transfer on payday — even {ui.fmt_money(50, sym)} builds the habit."))
    else:
        actions.append(("🟢", "Invest your surplus",
            f"You're saving {period.savings_rate:.1f}% — "
            "put it in a high-interest account or index fund."))

    if period.flex_pct > 40 and period.flex_total > 200:
        actions.append(("✂️", "Cut flexible spending",
            f"{ui.fmt_money(period.flex_total, sym)} of your spending is discretionary. "
            "Pick two categories to reduce this month."))

    if not exp_by_cat.empty:
        top = exp_by_cat.iloc[0]
        actions.append(("📌", f"Dig into {top['Category']}",
            f"At {ui.fmt_money(top['Total'], sym)} this is your biggest category — "
            "one review here has the most leverage."))

    if period.sub_total > 80:
        actions.append(("📺", "Review subscriptions",
            f"You're paying {ui.fmt_money(period.sub_total, sym)}. "
            "Cancel anything unused this month."))

    actions.append(("📅", "Upload next month",
        "Month-over-month tracking is the most effective financial habit you can build."))

    ca, cb = st.columns(2)
    for i, (emoji, title, desc) in enumerate(actions[:4]):
        with (ca if i % 2 == 0 else cb):
            ui.action_card(i + 1, "", title, desc)

# ── Tab 3: AI Coach ───────────────────────────────────────────────────────────
with tab_ai:
    ai_text = None

    if run_ai:
        if not key:
            st.info("Add your Anthropic API key in the sidebar to enable AI coaching.")
        else:
            import requests as _req
            import json as _json

            tc = exp_by_cat.iloc[0]["Category"] if not exp_by_cat.empty else "N/A"
            ta = ui.fmt_money(exp_by_cat.iloc[0]["Total"], sym) if not exp_by_cat.empty else "N/A"

            summary = "\n".join([
                f"Income: {ui.fmt_money(period.total_income, sym)}",
                f"Expenses: {ui.fmt_money(period.total_expense, sym)}",
                f"Net: {ui.fmt_money(period.net, sym, signed=True)}",
                f"Savings Rate: {period.savings_rate:.1f}%",
                f"Health Score: {period.health_score}/100 ({period.score_label})",
                f"Biggest expense category: {tc} ({ta})",
                f"Fixed bills: {ui.fmt_money(period.fixed_total, sym)}",
                f"Flexible spend: {ui.fmt_money(period.flex_total, sym)}",
                f"Subscriptions: {ui.fmt_money(period.sub_total, sym)}",
                f"Avg daily spend: {ui.fmt_money(period.avg_daily_spend, sym)}",
            ])

            with st.spinner("Thinking…"):
                try:
                    resp = _req.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": key, "content-type": "application/json",
                                 "anthropic-version": "2023-06-01"},
                        json={"model": "claude-sonnet-4-20250514", "max_tokens": 600,
                              "messages": [{"role": "user", "content": (
                                  "You are a warm, plain-English personal finance coach.\n"
                                  "Write exactly 4 short insights from the summary below.\n"
                                  "Rules: start each with one emoji · max 2 sentences · "
                                  "mention real numbers · honest and encouraging · no intro/outro.\n\n"
                                  f"Summary:\n{summary}"
                              )}]},
                        timeout=20,
                    )
                    if resp.status_code == 200:
                        ai_text = resp.json()["content"][0]["text"]
                    else:
                        st.warning(f"API returned status {resp.status_code}. Check your key.")
                except Exception as exc:
                    st.warning(f"Could not reach AI: {exc}")

    if ai_text:
        st.markdown(
            f'<div class="ai-panel">'
            f'<span class="ai-tag">✦ Claude AI</span>'
            f'<div class="ai-body">{ai_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    elif not run_ai:
        st.markdown(
            '<div style="padding:28px;text-align:center;color:#b8a898;font-size:14px">'
            "Enter your Anthropic API key in the sidebar and click <b>Generate Insights</b>."
            "</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  §4b  SCORE EXPLANATION  (follows the spending section)
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header(
    "Your financial health explained",
    "See exactly how your score was calculated and what you can do to improve it.",
)

# Score band card
_band_info = {
    "Excellent": ("Your finances are in great shape — keep up the good habits.",
                  "Consider investing your savings surplus or building an emergency fund."),
    "Healthy":   ("You have solid financial habits with a few areas to improve.",
                  "Focus on the lowest-scoring components above to push into the Excellent band."),
    "Needs attention": ("Some areas of your finances need attention.",
                  "Start with the red components in the breakdown — they have the biggest impact."),
    "At risk":   ("Multiple financial areas are under stress.",
                  "Focus on reducing spending and building a small emergency buffer first."),
}
_desc, _tip = _band_info.get(period.score_label, ("Review your financial habits.", "Focus on the red components."))
_score_color = (
    "#12B76A" if period.health_score >= 85 else
    "#6941C6" if period.health_score >= 70 else
    "#F79009" if period.health_score >= 50 else
    "#F04438"
)
ui.score_band_card(period.health_score, period.score_label, _score_color, _desc, _tip)

# Score breakdown chart
_breakdown = score_breakdown(fdf)
_col_bd_chart, _col_bd_tips = st.columns([1.2, 1])
with _col_bd_chart:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:.06em;color:#64748B;margin-bottom:6px">Score breakdown</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        charts.score_breakdown_chart(_breakdown),
        use_container_width=True, config={"displayModeBar": False},
    )
with _col_bd_tips:
    st.markdown(
        '<p style="font-size:11px;font-weight:600;text-transform:uppercase;'
        'letter-spacing:.06em;color:#64748B;margin-bottom:10px">What each score means</p>',
        unsafe_allow_html=True,
    )
    for comp in _breakdown:
        pct = comp.score / comp.max_score * 100 if comp.max_score > 0 else 0
        dot_color = "#12B76A" if pct >= 80 else "#F79009" if pct >= 50 else "#F04438"
        st.markdown(
            f'<div style="display:flex;gap:8px;margin-bottom:10px;align-items:flex-start">'
            f'<div style="width:8px;height:8px;border-radius:50%;background:{dot_color};'
            f'flex-shrink:0;margin-top:4px"></div>'
            f'<div><div style="font-size:13px;font-weight:500;color:#374151">{comp.label}'
            f'<span style="color:#98A2B3;font-size:11px;margin-left:6px">{comp.score:.0f}/{comp.max_score:.0f} pts</span></div>'
            f'<div style="font-size:12px;color:#98A2B3;margin-top:2px">{comp.tip}</div></div></div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  §6  TRANSACTIONS NEEDING REVIEW  +  FULL TRANSACTION TABLE
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header(
    "Transactions that need checking",
    "These transactions had unclear descriptions, unknown merchants, or unusual amounts. "
    "Use the Category dropdown to correct any that look wrong.",
)

# ── Session state: persist category corrections across Streamlit reruns ───────
# Key is derived from filename + size so corrections reset when a new file is uploaded.
_cache_key = f"cat_corrections_{uploaded.name}_{uploaded.size}"
if _cache_key not in st.session_state:
    st.session_state[_cache_key] = {}   # {row_position: corrected_category}

# ── Build the review dataframe ────────────────────────────────────────────────
if "Flag" in fdf.columns:
    _flagged = (
        fdf[fdf["Flag"] != ""]
        .sort_values("Amount")
        .reset_index(drop=True)
    )
else:
    _flagged = pd.DataFrame()

if _flagged.empty:
    st.markdown(
        '<div style="padding:18px;text-align:center;color:#98A2B3;'
        'font-size:13.5px;background:#F9FAFB;border:1px solid #EAECF0;border-radius:10px">'
        '✅ All transactions were categorised with high confidence — nothing needs review.'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    # Columns to display in the editable table
    _review_cols = [c for c in
        ["Date", "Description", "Amount", "Category", "Flag", "Confidence"]
        if c in _flagged.columns]

    _review_df = _flagged[_review_cols].copy()
    _review_df["Date"] = _review_df["Date"].dt.strftime("%d %b %Y")

    # Apply any corrections saved from previous interactions in this session
    for pos, corrected_cat in st.session_state[_cache_key].items():
        if pos < len(_review_df):
            _review_df.at[pos, "Category"] = corrected_cat

    # ── Editable table with category dropdown ─────────────────────────────────
    st.markdown(
        f'<div style="font-size:12.5px;color:#6941C6;font-weight:500;margin-bottom:8px">'
        f'📝 {len(_flagged)} transaction{"s" if len(_flagged) != 1 else ""} flagged '
        f'— click any Category cell to correct it</div>',
        unsafe_allow_html=True,
    )

    _edited = st.data_editor(
        _review_df,
        column_config={
            "Date": st.column_config.TextColumn(
                "Date",
                disabled=True,
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                disabled=True,
                width="large",
            ),
            "Amount": st.column_config.NumberColumn(
                "Amount",
                format=f"{sym}%.2f",
                disabled=True,
            ),
            "Category": st.column_config.SelectboxColumn(
                "Category ✏",          # ✏ icon signals editability
                options=sorted(ALL_CATEGORIES),
                required=True,
                width="medium",
            ),
            "Flag": st.column_config.TextColumn(
                "Why flagged",
                disabled=True,
                width="medium",
            ),
            "Confidence": st.column_config.TextColumn(
                "Confidence",
                disabled=True,
                width="small",
            ),
        },
        use_container_width = True,
        hide_index          = True,
        num_rows            = "fixed",          # no adding/deleting rows
        height              = min(420, 55 + len(_flagged) * 36),
        key                 = f"review_editor_{_cache_key}",
    )

    # ── Detect changes and persist to session state ───────────────────────────
    if _edited is not None and "Category" in _edited.columns:
        _orig_cats = _review_df["Category"].tolist()
        _new_cats  = _edited["Category"].tolist()

        for pos, (orig, new) in enumerate(zip(_orig_cats, _new_cats)):
            if orig != new and new in ALL_CATEGORIES:
                st.session_state[_cache_key][pos] = new

    # ── Show summary of corrections ───────────────────────────────────────────
    _n_corrections = len(st.session_state[_cache_key])
    if _n_corrections > 0:
        _corrected_items = ", ".join(
            f'row {p+1} → {c}'
            for p, c in list(st.session_state[_cache_key].items())[:3]
        )
        if len(st.session_state[_cache_key]) > 3:
            _corrected_items += f" + {len(st.session_state[_cache_key]) - 3} more"
        st.success(
            f"✓ {_n_corrections} correction{'s' if _n_corrections != 1 else ''} saved "
            f"for this session. ({_corrected_items})"
        )
        if st.button("↩ Reset all corrections", key="reset_corrections"):
            st.session_state[_cache_key] = {}
            st.rerun()

# ── Build corrected full dataframe for analysis and export ───────────────────
# Apply session-state corrections to the full filtered dataframe.
fdf_corrected = fdf.copy()
if "Flag" in fdf.columns and st.session_state.get(_cache_key):
    # Map corrections: the flagged df was sorted by Amount + reset_index,
    # so we need to recover the original fdf indices.
    if not _flagged.empty:
        _flagged_with_orig_idx = (
            fdf[fdf["Flag"] != ""]
            .sort_values("Amount")
        )
        for pos, new_cat in st.session_state[_cache_key].items():
            if pos < len(_flagged_with_orig_idx):
                orig_idx = _flagged_with_orig_idx.index[pos]
                fdf_corrected.at[orig_idx, "Category"] = new_cat

# ── Full transaction table (read-only, shows corrected categories) ────────────
ui.section_header(
    "Transaction explorer",
    "Browse all your transactions. Categories show any corrections you made above.",
)

_show_cols = [c for c in
    ["Date", "Description", "Amount", "Category", "Type", "Confidence", "Flag"]
    if c in fdf_corrected.columns]

_full_df = (
    fdf_corrected[_show_cols]
    .copy()
    .assign(Date=fdf_corrected["Date"].dt.strftime("%d %b %Y"))
    .sort_values("Date", ascending=False)
    .reset_index(drop=True)
)

st.dataframe(
    _full_df,
    use_container_width = True,
    height              = 420,
    column_config       = {
        "Amount":     st.column_config.NumberColumn("Amount", format=f"{sym}%.2f"),
        "Category":   st.column_config.TextColumn("Category"),
        "Type":       st.column_config.TextColumn("Type"),
        "Confidence": st.column_config.TextColumn("Confidence"),
        "Flag":       st.column_config.TextColumn("Flagged reason"),
    },
)

# ── Export with corrected categories ─────────────────────────────────────────
_export_data = fdf_corrected.copy()
_export_data["Date"] = _export_data["Date"].dt.strftime("%Y-%m-%d")
st.download_button(
    label     = "⬇ Download corrected CSV",
    data      = _export_data.to_csv(index=False).encode("utf-8"),
    file_name = "money_health_corrected.csv",
    mime      = "text/csv",
    help      = "Includes any category corrections you made in the review table above.",
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer">'
    "Money Health Agent is for personal education and spending awareness only. "
    "It does not constitute financial, tax, investment, or credit advice. "
    "Consult a licensed financial adviser for professional guidance."
    "</div>",
    unsafe_allow_html=True,
)
