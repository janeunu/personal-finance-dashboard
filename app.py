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

import streamlit as st

import charts
import metrics as m
import ui
from categoriser import add_categories
from config import BUDGET_GUIDE
from parser import parse_statement

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Money Health",
    page_icon  = "💰",
    layout     = "wide",
)
ui.inject_css()


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748B;margin:6px 0 10px">Filters</p>', unsafe_allow_html=True)
    ph_month  = st.empty()
    ph_cat    = st.empty()

    st.markdown('<div style="height:1px;background:#1E293B;margin:10px 0"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748B;margin:6px 0 4px">API Key</p>', unsafe_allow_html=True)
    st.caption("Enables AI column detection and categorisation in any language.")
    api_key = st.text_input(
        "Anthropic API Key", type="password",
        placeholder="sk-ant-…",
        help="Optional. Get one free at console.anthropic.com",
    )

    st.markdown('<div style="height:1px;background:#1E293B;margin:10px 0"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748B;margin:6px 0 10px">AI Coach</p>', unsafe_allow_html=True)
    run_ai = st.button("✦ Generate Insights", use_container_width=True)

    st.markdown('<div style="height:1px;background:#1E293B;margin:10px 0"></div>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#64748B;margin:6px 0 10px">Export</p>', unsafe_allow_html=True)
    ph_export = st.empty()


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="mh-privacy">'
    "🔒 <b>Privacy:</b> Your file is processed only in this session — "
    "never stored or shared. For personal tracking only, not financial advice."
    "</div>",
    unsafe_allow_html=True,
)

uploaded = st.file_uploader(
    "Upload your bank statement — any language, any bank",
    type=["csv"],
    help="CSV with at least a date column, description column, and amount column.",
)

if uploaded is None:
    ui.onboarding_tiles()
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
#  PARSE  →  CATEGORISE
# ══════════════════════════════════════════════════════════════════════════════
key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")


@st.cache_data(show_spinner=False)
def load_data(raw: bytes, api_key_used: str):
    """Cache parse + categorise together — re-runs only when file or key changes."""
    df, meta = parse_statement(raw, api_key_used or None)
    df       = add_categories(df, api_key_used or None)
    return df, meta


with st.spinner("Reading and categorising your transactions…"):
    try:
        df, meta = load_data(uploaded.read(), key)
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

# ── Sidebar filters (filled now that df is loaded) ───────────────────────────
sel_month = ph_month.selectbox("Month", ["All"] + sorted(df["Month"].unique()))
sel_cat   = ph_cat.selectbox("Category", ["All"] + sorted(df["Category"].unique()))
ph_export.download_button(
    "⬇ Download Categorised CSV",
    data      = df.to_csv(index=False).encode("utf-8"),
    file_name = "money_health_transactions.csv",
    mime      = "text/csv",
    use_container_width = True,
)


# ══════════════════════════════════════════════════════════════════════════════
#  FILTER
# ══════════════════════════════════════════════════════════════════════════════
fdf = df.copy()
if sel_month != "All":
    fdf = fdf[fdf["Month"] == sel_month]
if sel_cat != "All":
    fdf = fdf[fdf["Category"] == sel_cat]

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
delta        = m.previous_period(df, sel_month) if sel_month != "All" else m.PeriodDelta()


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
        value         = ui.fmt_money(period.net, sym, signed=True),
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
        label         = "Saved this month",
        value         = ui.fmt_pct(sr, decimals=0),
        value_color   = sr_color,
        delta_html    = f'<span class="neu">{sr_context}</span>',
        delta_context = "",
    )

# ── KPI 3: Avg daily spend ────────────────────────────────────────────────────
with k3:
    ui.kpi_card(
        label         = "Avg daily spend",
        value         = ui.fmt_money(period.avg_daily_spend, sym),
        value_color   = ui.COLOR["text_primary"],
        delta_html    = f'<span class="neu">Across {period.spending_days} days</span>',
        delta_context = "",
    )

# ── KPI 4: Top spending category — show amount as value, name as context ────
with k4:
    if top_cat and not exp_by_cat.empty:
        top_amt = float(exp_by_cat.iloc[0]["Total"])
        ui.kpi_card(
            label         = "Biggest cost",
            value         = ui.fmt_money(top_amt, sym),
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
#  §2  WATERFALL  +  FIXED vs FLEXIBLE  +  BUDGET CHECK
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Where did the money go?")
col_wf, col_right = st.columns([1.6, 1])

with col_wf:
    ui.card_start("Cash flow")
    st.plotly_chart(
        charts.waterfall_chart(exp_by_cat, period.total_income, period.total_expense, period.net, sym),
        use_container_width=True, config={"displayModeBar": False},
    )
    ui.card_end()

with col_right:
    # Two plain stat rows replace the confusing Fixed vs Flexible donut
    # "Fixed bills" and "Cuttable spend" are self-explanatory
    st.markdown(
        f'<div class="mh-card" style="margin-bottom:10px">'
        f'  <div class="mh-card-title">Your spending split</div>'
        f'  <div style="margin-bottom:14px">'
        f'    <div style="font-size:11px;font-weight:500;text-transform:uppercase;'
        f'letter-spacing:.06em;color:#9CA3AF;margin-bottom:4px">Fixed bills</div>'
        f'    <div style="font-family:\'Inter\',sans-serif;font-size:24px;'
        f'font-weight:500;color:#374151;font-variant-numeric:tabular-nums">'
        f'{ui.fmt_money(period.fixed_total, sym)}</div>'
        f'    <div style="font-size:12px;color:#9CA3AF;margin-top:2px">'
        f'Rent, insurance, utilities — can\'t easily cut</div>'
        f'  </div>'
        f'  <div style="height:0.5px;background:#F3F4F6;margin-bottom:14px"></div>'
        f'  <div>'
        f'    <div style="font-size:11px;font-weight:500;text-transform:uppercase;'
        f'letter-spacing:.06em;color:#9CA3AF;margin-bottom:4px">Cuttable spend</div>'
        f'    <div style="font-family:\'Inter\',sans-serif;font-size:24px;'
        f'font-weight:500;color:#2563EB;font-variant-numeric:tabular-nums">'
        f'{ui.fmt_money(period.flex_total, sym)}</div>'
        f'    <div style="font-size:12px;color:#9CA3AF;margin-top:2px">'
        f'Groceries, dining, shopping — adjustable</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Budget check bars — only show categories the user actually spent in
    ui.card_start("Budget check")
    shown = 0
    for cat, rec_pct in BUDGET_GUIDE.items():
        actual = float(exp_by_cat[exp_by_cat["Category"] == cat]["Total"].sum())
        if actual == 0:
            continue                          # skip irrelevant categories
        actual_pct = (actual / period.total_income * 100) if period.total_income > 0 else 0.0
        ui.budget_bar(cat, ui.fmt_money(actual, sym), actual_pct, rec_pct)
        shown += 1
        if shown == 5:
            break                             # cap at 5 for layout balance
    if shown == 0:
        st.caption("No budget categories matched this period.")
    ui.card_end()



# ══════════════════════════════════════════════════════════════════════════════
#  §3  TREEMAP  +  TOP TRANSACTIONS  +  SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Spending breakdown")
col_tree, col_detail = st.columns([1.5, 1])

with col_tree:
    if not exp_by_cat.empty:
        ui.card_start()
        st.plotly_chart(
            charts.spending_treemap(exp_by_cat, sym),
            use_container_width=True, config={"displayModeBar": False},
        )
        ui.card_end()

with col_detail:
    st.markdown('<div class="cc-title" style="margin-bottom:10px">Biggest Single Spends</div>', unsafe_allow_html=True)
    for _, row in top_txns.iterrows():
        ui.transaction_card(
            amount      = ui.fmt_money(abs(row["Amount"]), sym),
            description = str(row["Description"]),
            date        = row["Date"].strftime("%d %b %Y"),
            category    = str(row["Category"]),
        )

    if not subs.empty:
        st.markdown('<div class="mh-card-title" style="margin:16px 0 10px">Subscriptions</div>', unsafe_allow_html=True)
        rows_html = "".join(
            f'<div class="mh-sub-row">'
            f'<span class="mh-sub-name">{r["Description"]}</span>'
            f'<span class="mh-sub-amount">{ui.fmt_money(r["Amount"], sym)}</span>'
            f'</div>'
            for _, r in subs.iterrows()
        )
        ui.subscription_list(rows_html, ui.fmt_money(period.sub_total, sym))


# ══════════════════════════════════════════════════════════════════════════════
#  §4  DAY-OF-WEEK  +  SAVINGS RATE TREND
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Spending patterns")
col_dow, col_sr = st.columns(2)

with col_dow:
    ui.card_start("When Do You Spend?")
    st.plotly_chart(
        charts.dow_bar(dow_spend, sym),
        use_container_width=True, config={"displayModeBar": False},
    )
    ui.card_end()

with col_sr:
    ui.card_start("Savings Rate Over Time")
    st.plotly_chart(
        charts.savings_trend(sr_trend),
        use_container_width=True, config={"displayModeBar": False},
    )
    ui.card_end()


# ══════════════════════════════════════════════════════════════════════════════
#  §5  INSIGHTS  ·  ACTIONS  ·  AI COACH  (tabbed)
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Insights & actions")
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
#  §6  TRANSACTION TABLE
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Transaction explorer")

display_df = (
    fdf[["Date", "Description", "Amount", "Category", "Type", "Month"]]
    .copy()
    .assign(Date=fdf["Date"].dt.strftime("%d %b %Y"))
    .sort_values("Date", ascending=False)
    .reset_index(drop=True)
)

st.dataframe(
    display_df,
    use_container_width = True,
    height              = 420,
    column_config       = {
        "Amount":   st.column_config.NumberColumn("Amount", format=f"{sym}%.2f"),
        "Category": st.column_config.TextColumn("Category"),
        "Type":     st.column_config.TextColumn("Type"),
    },
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
