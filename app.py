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
from metrics import monthly_income_vs_expense
import ui
from categoriser import add_categories, flag_transactions
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
ui.section_header("Where did the money go?")
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
ui.section_header("Top spending areas")
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
#  §4  DAY-OF-WEEK  +  SAVINGS RATE TREND
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Spending patterns")
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
#  §6  NEEDS REVIEW  +  TRANSACTION TABLE
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header("Transaction explorer")

# ── Needs Review panel ────────────────────────────────────────────────────────
needs_review_df = fdf[fdf.get("NeedsReview", False)] if "NeedsReview" in fdf.columns else pd.DataFrame()
if not needs_review_df.empty:
    nr_count = len(needs_review_df)
    st.markdown(
        f'<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;'
        f'padding:14px 18px;margin-bottom:14px">'
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:.06em;color:#92400E;margin-bottom:8px">'
        f'⚠ {nr_count} transaction{"s" if nr_count != 1 else ""} need review</div>'
        f'<div style="font-size:13px;color:#78350F;line-height:1.55">'
        f'These transactions could not be confidently categorised — '
        f'descriptions were too vague, missing, or matched no known pattern. '
        f'Check the Category column and correct any that look wrong.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    review_display = (
        needs_review_df[["Date", "Description", "Amount", "Category", "Confidence"]]
        .copy()
        .assign(Date=needs_review_df["Date"].dt.strftime("%d %b %Y"))
        .sort_values("Amount")
        .reset_index(drop=True)
    )
    st.dataframe(
        review_display,
        use_container_width = True,
        height              = min(200, 40 + nr_count * 35),
        column_config       = {
            "Amount":     st.column_config.NumberColumn("Amount", format=f"{sym}%.2f"),
            "Confidence": st.column_config.TextColumn("Confidence"),
        },
    )

# ── Full transaction table ────────────────────────────────────────────────────
cols_to_show = ["Date", "Description", "Amount", "Category", "Type", "Confidence"]
cols_to_show = [c for c in cols_to_show if c in fdf.columns]

display_df = (
    fdf[cols_to_show]
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
        "Amount":     st.column_config.NumberColumn("Amount", format=f"{sym}%.2f"),
        "Category":   st.column_config.TextColumn("Category"),
        "Type":       st.column_config.TextColumn("Type"),
        "Confidence": st.column_config.TextColumn("Confidence"),
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
