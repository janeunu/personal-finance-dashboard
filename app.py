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
from config import BUDGET_GUIDE, ALL_CATEGORIES, category_badge_colors
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

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE — single source of truth
#
#  master_df lives in st.session_state[file_key].
#  When a user confirms a category correction, master_df is mutated and
#  st.rerun() is called — every downstream computation automatically refreshes.
#
#  file_key is derived from filename + file size, so the dataset resets
#  automatically when a different file is uploaded.
# ══════════════════════════════════════════════════════════════════════════════
_file_key  = f"master_{uploaded.name}_{uploaded.size}"
_meta_key  = f"meta_{_file_key}"
_custom_key = "custom_categories"    # user-added categories, persists across files

# Initialise custom categories list once per session
if _custom_key not in st.session_state:
    st.session_state[_custom_key] = []

# Parse, categorise, and flag — only runs once per file
if _file_key not in st.session_state:
    with st.spinner("Reading and categorising your transactions…"):
        try:
            _raw = uploaded.read()
            _df, _meta = parse_statement(_raw, key or None, filename=uploaded.name)
            _df = add_categories(_df, key or None)
            _df = flag_transactions(_df)
            # Add ReviewStatus column: "Review" for flagged, "Auto" for clean
            _df["ReviewStatus"] = _df["Flag"].apply(
                lambda f: "Review" if f else "Auto"
            )
            st.session_state[_file_key] = _df
            st.session_state[_meta_key] = _meta
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            st.stop()

# All downstream code reads from master_df — never from the original parse output
master_df = st.session_state[_file_key]
meta      = st.session_state[_meta_key]
sym       = meta.currency_symbol or "$"

if meta.warnings:
    for w in meta.warnings:
        st.warning(w)

# All available category options (built-in + any user-added custom categories)
_all_categories = sorted(
    list(set(ALL_CATEGORIES + st.session_state[_custom_key]))
)

# ── Top filter bar ────────────────────────────────────────────────────────────
ph_export.download_button(
    "⬇ Export CSV",
    data      = master_df.assign(
                    Date=master_df["Date"].dt.strftime("%Y-%m-%d")
                ).to_csv(index=False).encode("utf-8"),
    file_name = "money_health_transactions.csv",
    mime      = "text/csv",
    help      = "Download all transactions with current category corrections applied.",
    use_container_width = True,
)
f1, f2, f3, _ = st.columns([2, 2, 2, 4])
with f1:
    sel_month = st.selectbox("Month",
        ["All months"] + sorted(master_df["Month"].unique()),
        label_visibility="visible")
with f2:
    sel_cat = st.selectbox("Category",
        ["All categories"] + sorted(master_df["Category"].unique()),
        label_visibility="visible")
with f3:
    sel_type = st.selectbox("Type",
        ["All types", "Income", "Expense", "Transfer"],
        label_visibility="visible")

sel_month = None if sel_month == "All months" else sel_month
sel_cat   = None if sel_cat == "All categories" else sel_cat
sel_type  = None if sel_type == "All types" else sel_type

# ── Section tab navigation ────────────────────────────────────────────────────
_sections = ["Overview", "Spending", "Income", "Subscriptions", "Bills"]
_active_section = st.radio(
    "Section",
    _sections,
    horizontal=True,
    label_visibility="collapsed",
    key="section_tab",
)

# ══════════════════════════════════════════════════════════════════════════════
#  FILTER  — fdf is a filtered view of master_df (never mutated)
# ══════════════════════════════════════════════════════════════════════════════
fdf = master_df.copy()
if sel_month: fdf = fdf[fdf["Month"] == sel_month]
if sel_cat:   fdf = fdf[fdf["Category"] == sel_cat]
if sel_type:  fdf = fdf[fdf["Type"] == sel_type]

exp_df = fdf[fdf["Type"] == "Expense"]


# ══════════════════════════════════════════════════════════════════════════════
#  COMPUTE
# ══════════════════════════════════════════════════════════════════════════════
exp_by_cat   = m.expense_by_category(fdf)           # computed first — needed for headline
top_cat      = exp_by_cat.iloc[0]["Category"] if not exp_by_cat.empty else None
period       = m.compute_period_metrics(fdf, top_category=top_cat)
sr_trend     = m.savings_rate_by_month(master_df)    # always full dataset for trend
dow_spend    = m.spend_by_dow(fdf)
top_txns     = m.top_expenses(fdf, n=3)
subs         = m.subscription_breakdown(fdf)
delta        = m.previous_period(master_df, sel_month) if sel_month else m.PeriodDelta()
monthly_df   = monthly_income_vs_expense(master_df)


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
    # Use master_df (not filtered fdf) so review count is always the full pending total
    needs_review_count = int(
        (master_df["ReviewStatus"] == "Review").sum()
        if "ReviewStatus" in master_df.columns
        else master_df.get("NeedsReview", pd.Series(False)).sum()
    )
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
        charts.spending_heatmap(fdf, sym),
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
#  §6  TRANSACTION REVIEW WORKFLOW
#
#  Architecture: master_df (session_state) is the single source of truth.
#  Confirming a review mutates master_df → st.rerun() → all views refresh.
#
#  ReviewStatus values:
#    "Auto"     — categorised with high confidence, no action needed
#    "Review"   — flagged by a rule, needs user confirmation
#    "Reviewed" — user has confirmed the category
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header(
    "Transactions that need checking",
    "Review each flagged transaction, assign the correct category, then click Confirm. "
    "Confirmed transactions move to the Transaction Explorer automatically.",
)

# ── Build the flagged view from master_df (not fdf — filtering is irrelevant here) ──
_pending = master_df[master_df["ReviewStatus"] == "Review"].copy()

# ── Summary bar ───────────────────────────────────────────────────────────────
_reviewed_count = int((master_df["ReviewStatus"] == "Reviewed").sum())
_pending_count  = len(_pending)
_total_flagged  = _pending_count + _reviewed_count

if _total_flagged > 0:
    _pct_done = int(_reviewed_count / _total_flagged * 100)
    st.markdown(
        f'<div style="background:#F9FAFB;border:1px solid #EAECF0;border-radius:8px;'
        f'padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;gap:16px">'
        f'<div style="flex:1;background:#EAECF0;border-radius:99px;height:6px;overflow:hidden">'
        f'<div style="width:{_pct_done}%;height:100%;background:#12B76A;border-radius:99px"></div>'
        f'</div>'
        f'<div style="font-size:13px;color:#374151;white-space:nowrap">'
        f'<b>{_reviewed_count}</b> of <b>{_total_flagged}</b> reviewed'
        f'{"  ✅ All done!" if _pending_count == 0 else f"  — {_pending_count} remaining"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

if _pending.empty:
    st.markdown(
        '<div style="padding:18px;text-align:center;color:#98A2B3;font-size:13.5px;'
        'background:#F9FAFB;border:1px solid #EAECF0;border-radius:10px">'
        '✅ All flagged transactions have been reviewed. They appear in the Transaction Explorer below.'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    # ── Column header ──────────────────────────────────────────────────────────
    _h = st.columns([1.1, 2.8, 1, 2, 1.8, 0.7])
    for col, lbl in zip(_h, ["Date","Description","Amount","Category","Why flagged",""]): 
        col.markdown(
            f'<div style="font-size:10px;font-weight:500;text-transform:uppercase;'
            f'letter-spacing:.06em;color:#98A2B3;padding-bottom:4px;'
            f'border-bottom:1px solid #EAECF0">{lbl}</div>',
            unsafe_allow_html=True,
        )

    # ── One row per pending transaction ───────────────────────────────────────
    for _idx, _row in _pending.iterrows():
        _c1, _c2, _c3, _c4, _c5, _c6 = st.columns([1.1, 2.8, 1, 2, 1.8, 0.7])

        # Date + description + amount (read-only)
        with _c1:
            st.markdown(
                f'<div style="font-size:12px;color:#98A2B3;padding-top:8px">'
                f'{_row["Date"].strftime("%d %b %Y")}</div>',
                unsafe_allow_html=True,
            )
        with _c2:
            st.markdown(
                f'<div style="font-size:13px;font-weight:500;color:#374151;padding-top:8px;'
                f'overflow:hidden;white-space:nowrap;text-overflow:ellipsis" title="{_row["Description"]}">'
                f'{str(_row["Description"])[:45]}</div>',
                unsafe_allow_html=True,
            )
        with _c3:
            _amt = float(_row["Amount"])
            _color = ui.COLOR["expense"] if _amt < 0 else ui.COLOR["income"]
            st.markdown(
                f'<div style="font-size:13px;font-weight:600;color:{_color};'
                f'font-variant-numeric:tabular-nums;padding-top:8px">'
                f'{ui.fmt_money(_amt, sym)}</div>',
                unsafe_allow_html=True,
            )

        # Category selectbox (editable)
        with _c4:
            _current_cat = str(_row.get("Category", "Other Expense"))
            _default_idx = (
                _all_categories.index(_current_cat)
                if _current_cat in _all_categories else 0
            )
            _selected_cat = st.selectbox(
                label           = "",
                options         = _all_categories,
                index           = _default_idx,
                key             = f"sel_{_idx}",
                label_visibility= "collapsed",
            )

        # Flag reason
        with _c5:
            _flag = str(_row.get("Flag", ""))
            st.markdown(
                f'<div style="font-size:11px;color:#F79009;padding-top:8px">'
                f'{_flag[:40]}</div>',
                unsafe_allow_html=True,
            )

        # Confirm button
        with _c6:
            if st.button("✓", key=f"confirm_{_idx}", help="Confirm this category"):
                # Update master_df — the single source of truth
                _final_cat = st.session_state.get(f"sel_{_idx}", _selected_cat)
                st.session_state[_file_key].at[_idx, "Category"]     = _final_cat
                st.session_state[_file_key].at[_idx, "ReviewStatus"]  = "Reviewed"
                st.session_state[_file_key].at[_idx, "NeedsReview"]   = False
                st.session_state[_file_key].at[_idx, "Flag"]          = ""
                st.toast(f"✓ {str(_row['Description'])[:30]} → {_final_cat}", icon="✅")
                st.rerun()   # ← triggers full refresh: charts, KPIs, explorer all update

        st.markdown(
            '<div style="height:0.5px;background:#F2F4F7;margin:2px 0"></div>',
            unsafe_allow_html=True,
        )

    # ── Custom category input ──────────────────────────────────────────────────
    with st.expander("➕ Need a category that isn't in the list?"):
        _new_cat_col, _add_col = st.columns([3, 1])
        with _new_cat_col:
            _new_cat_name = st.text_input(
                "New category name",
                placeholder="e.g. Pet care, Hobbies, Side business…",
                key="new_category_input",
            )
        with _add_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add category", key="add_category_btn"):
                _nc = _new_cat_name.strip()
                if _nc and _nc not in st.session_state[_custom_key]:
                    st.session_state[_custom_key].append(_nc)
                    st.success(f"✓ '{_nc}' added. It now appears in all category dropdowns.")
                    st.rerun()
                elif _nc in st.session_state[_custom_key]:
                    st.info(f"'{_nc}' is already in your list.")
                else:
                    st.warning("Please enter a category name.")

        if st.session_state[_custom_key]:
            st.markdown(
                f'<div style="font-size:12px;color:#98A2B3;margin-top:6px">'
                f'Custom categories: {", ".join(st.session_state[_custom_key])}</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
#  §7  TRANSACTION EXPLORER — styled table with badges, confidence bars, pagination
# ══════════════════════════════════════════════════════════════════════════════
ui.section_header(
    "Transaction explorer",
    "All your transactions — including ones you have already reviewed and confirmed.",
)

# ── Controls row ──────────────────────────────────────────────────────────────
_tc1, _tc2, _tc3 = st.columns([3, 1, 1])
with _tc1:
    _txn_search = st.text_input(
        "Search",
        placeholder="Search transactions, merchants…",
        label_visibility="collapsed",
        key="txn_search",
    )
with _tc2:
    _show_flagged = st.toggle("Show only flagged ⚑", key="show_flagged")
with _tc3:
    _txn_page_key = "txn_page"
    if _txn_page_key not in st.session_state:
        st.session_state[_txn_page_key] = 0

# ── Build display dataframe ───────────────────────────────────────────────────
_show_cols = [c for c in
    ["Date", "Description", "Amount", "Category", "Type", "ReviewStatus", "Confidence", "Flag"]
    if c in fdf.columns]
_txn_df = fdf[_show_cols].copy()

# Apply search
if _txn_search:
    _mask = (
        _txn_df["Description"].astype(str).str.contains(_txn_search, case=False, na=False)
        | _txn_df["Category"].astype(str).str.contains(_txn_search, case=False, na=False)
    )
    _txn_df = _txn_df[_mask]
    st.session_state[_txn_page_key] = 0   # reset to page 0 on new search

# Apply flagged filter
if _show_flagged and "Flag" in _txn_df.columns:
    _txn_df = _txn_df[_txn_df["Flag"] != ""]
    st.session_state[_txn_page_key] = 0

_txn_df = _txn_df.sort_values("Date", ascending=False).reset_index(drop=True)

# ── Render styled table ───────────────────────────────────────────────────────
_PAGE_SIZE = 12
_table_html, _total_pages = ui.styled_transaction_table(
    _txn_df, sym=sym, max_rows=_PAGE_SIZE, page=st.session_state[_txn_page_key]
)
_start_row = st.session_state[_txn_page_key] * _PAGE_SIZE + 1
_end_row   = min(_start_row + _PAGE_SIZE - 1, len(_txn_df))

st.markdown(
    f'<div style="font-size:12px;color:#98A2B3;margin-bottom:8px">'
    f'Showing {_start_row}–{_end_row} of {len(_txn_df)} transactions'
    f'{"  ·  " + str(int((fdf["ReviewStatus"]=="Review").sum())) + " pending review" if "ReviewStatus" in fdf.columns and (fdf["ReviewStatus"]=="Review").sum() > 0 else ""}'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="background:#FFFFFF;border:1px solid #EAECF0;border-radius:10px;padding:2px 0;overflow:hidden">'
    f'{_table_html}</div>',
    unsafe_allow_html=True,
)

# ── Pagination controls ───────────────────────────────────────────────────────
if _total_pages > 1:
    _pp1, _pp2, _pp3 = st.columns([1, 2, 1])
    with _pp1:
        if st.button("← Previous", disabled=st.session_state[_txn_page_key] == 0,
                     key="txn_prev"):
            st.session_state[_txn_page_key] -= 1
            st.rerun()
    with _pp2:
        st.markdown(
            f'<div style="text-align:center;font-size:12.5px;color:#98A2B3;padding-top:8px">'
            f'Page {st.session_state[_txn_page_key]+1} of {_total_pages}</div>',
            unsafe_allow_html=True,
        )
    with _pp3:
        if st.button("Next →", disabled=st.session_state[_txn_page_key] >= _total_pages - 1,
                     key="txn_next"):
            st.session_state[_txn_page_key] += 1
            st.rerun()

st.download_button(
    label     = "⬇ Download transactions CSV",
    data      = (
        fdf.assign(Date=fdf["Date"].dt.strftime("%Y-%m-%d"))
        .to_csv(index=False)
        .encode("utf-8")
    ),
    file_name = "money_health_transactions.csv",
    mime      = "text/csv",
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
