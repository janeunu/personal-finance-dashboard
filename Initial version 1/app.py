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
    run_ai = st.button("✦ AI Insights", use_container_width=True)

with col_export:
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
f1, f2, f3 = st.columns(3)
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
#  RENDERING LAYER  —  rebuilt for V7 target
#
#  Design principle: each logical dashboard section = 1–2 st.* calls.
#  KPI cards, top-spending areas, and all card-based sections are built
#  as pure HTML strings and rendered in a SINGLE st.markdown() per section.
#  This eliminates Streamlit container overhead that was making V10 tall.
#
#  Variables available from the logic layer (lines 1-206):
#    master_df, fdf, period, exp_by_cat, top_txns, subs, delta,
#    sr_trend, monthly_df, dow_spend, sym, top_cat
#    _file_key, _custom_key, _all_categories, _pending
# ══════════════════════════════════════════════════════════════════════════════

# ── Inline helpers (no st.* calls) ───────────────────────────────────────────
def _sec(label: str) -> str:
    """Section header HTML."""
    return (
        f'<div style="display:flex;align-items:center;gap:8px;margin:14px 0 8px">'
        f'<div style="width:4px;height:15px;background:#6941C6;border-radius:2px;flex-shrink:0"></div>'
        f'<div style="font-size:10.5px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:.08em;color:#64748B">{label}</div>'
        f'</div>'
    )

def _card(content: str, mb: str = "10px", pad: str = "13px 16px") -> str:
    return (
        f'<div style="background:#fff;border:1px solid #EAECF0;border-radius:10px;'
        f'padding:{pad};margin-bottom:{mb}">{content}</div>'
    )

def _kpi(label: str, value: str, color: str, sub: str) -> str:
    return (
        f'<div style="background:#fff;border:1px solid #EAECF0;border-radius:10px;'
        f'padding:11px 15px 9px">'
        f'<div style="font-size:10px;font-weight:500;text-transform:uppercase;'
        f'letter-spacing:.07em;color:#98A2B3;margin-bottom:5px">{label}</div>'
        f'<div style="font-size:22px;font-weight:600;line-height:1;'
        f'font-variant-numeric:tabular-nums;color:{color}">{value}</div>'
        f'<div style="font-size:11px;margin-top:4px;color:#98A2B3">{sub}</div>'
        f'</div>'
    )

def _chart_label(text: str) -> str:
    return (
        f'<p style="font-size:10.5px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:.07em;color:#64748B;margin:0 0 3px">{text}</p>'
    )


# ══════════════════════════════════════════════════════════════════════════════
#  1.  HERO  —  verdict left, 2×2 KPI grid right
#  Single st.markdown for verdict. Single st.markdown for KPI grid.
# ══════════════════════════════════════════════════════════════════════════════
_col_v, _col_k = st.columns([1.8, 1])

with _col_v:
    _score_color = (
        "#34D399" if period.health_score >= 85 else
        "#A78BFA" if period.health_score >= 70 else
        "#FBBF24" if period.health_score >= 50 else "#F87171"
    )
    st.markdown(
        f'<div style="background:#0F172A;border-radius:11px;padding:22px 28px;'
        f'display:flex;align-items:center;gap:24px">'
        f'<div style="font-size:68px;font-weight:600;line-height:1;letter-spacing:-2px;'
        f'font-variant-numeric:tabular-nums;flex-shrink:0;color:{_score_color}">'
        f'{period.health_score}</div>'
        f'<div>'
        f'<div style="font-size:9.5px;font-weight:500;letter-spacing:.1em;'
        f'text-transform:uppercase;color:#334155;margin-bottom:6px">'
        f'Money health score &nbsp;·&nbsp; {period.score_label}</div>'
        f'<div style="font-size:17px;font-weight:600;color:#F1F5F9;'
        f'line-height:1.35;margin-bottom:5px">{period.verdict_headline}</div>'
        f'<div style="font-size:12.5px;color:#475569">'
        f'Earned <b style="color:#64748B">{ui.fmt_money(period.total_income, sym)}</b>'
        f' &nbsp;·&nbsp; '
        f'Spent <b style="color:#64748B">{ui.fmt_money(period.total_expense, sym)}</b>'
        f' &nbsp;·&nbsp; '
        f'Saved <b style="color:#64748B">{ui.fmt_money(period.net, sym, signed=True)}</b>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

with _col_k:
    # All 4 KPI cards in ONE st.markdown — no Streamlit container overhead between cards
    _nr_count = int(
        (master_df["ReviewStatus"] == "Review").sum()
        if "ReviewStatus" in master_df.columns else 0
    )
    _sr = period.savings_rate
    _net_col  = "#12B76A" if period.net >= 0 else "#F04438"
    _sr_col   = "#12B76A" if _sr >= 20 else "#F79009" if _sr >= 10 else "#F04438"
    _nr_col   = "#F79009" if _nr_count < 10 else "#F04438"
    _nr_val   = str(_nr_count) if _nr_count > 0 else "—"
    _sr_ctx   = "Goal: 20% · You're ahead" if _sr >= 20 else f"Goal: 20% · {_sr:.0f}% this month"
    _net_ctx  = ui.delta_badge(period.net, delta.prev_net) + " vs last month"

    st.markdown(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
        f'{_kpi("Money left over", ui.fmt_money_kpi(period.net, sym, signed=True), _net_col, _net_ctx)}'
        f'{_kpi("% of income saved", ui.fmt_pct(_sr, 0), _sr_col, _sr_ctx)}'
        f'{_kpi("Daily spend (avg)", ui.fmt_money_kpi(period.avg_daily_spend, sym), "#101828", f"Across {period.spending_days} days")}'
        f'{_kpi("Check these", _nr_val, _nr_col, "Transactions to double-check")}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  2.  WHERE DID THE MONEY GO
#  Left: donut + income/expense bars.  Right: spending split + budget check.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Where did the money go?"), unsafe_allow_html=True)
_c_charts, _c_right = st.columns([1.3, 1])

with _c_charts:
    st.markdown(_chart_label("Spending breakdown"), unsafe_allow_html=True)
    if not exp_by_cat.empty:
        st.plotly_chart(charts.spending_donut(exp_by_cat, sym),
                        use_container_width=True, config={"displayModeBar": False})
    st.markdown(_chart_label("Income vs spending by month"), unsafe_allow_html=True)
    st.plotly_chart(charts.income_vs_expense_bars(monthly_df, sym),
                    use_container_width=True, config={"displayModeBar": False})

with _c_right:
    # Spending split + budget check — two cards in ONE st.markdown
    _budget_rows = ""
    for _cat, _rec_pct in BUDGET_GUIDE.items():
        _actual = float(exp_by_cat[exp_by_cat["Category"] == _cat]["Total"].sum())
        if _actual == 0:
            continue
        _apct  = (_actual / period.total_income * 100) if period.total_income > 0 else 0.0
        _bw    = min(_apct / _rec_pct * 100, 105) if _rec_pct else 0.0
        _bcol, _bst = (
            ("#F04438", "Over") if _apct > _rec_pct else
            ("#F79009", "Near") if _apct > _rec_pct * 0.85 else
            ("#12B76A", "On track")
        )
        _budget_rows += (
            f'<div style="margin-bottom:10px">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:12px;color:#374151;font-weight:500;margin-bottom:4px">'
            f'<span>{_cat} <span style="color:#98A2B3;font-weight:400">'
            f'{ui.fmt_money(_actual, sym)}</span></span>'
            f'<span style="color:{_bcol};font-size:10.5px">{_bst}</span></div>'
            f'<div style="background:#F1F5F9;border-radius:3px;height:4px;overflow:hidden">'
            f'<div style="width:{_bw:.1f}%;height:100%;background:{_bcol};border-radius:3px">'
            f'</div></div></div>'
        )
        if _budget_rows.count("margin-bottom:10px") >= 5:
            break

    st.markdown(
        _card(
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.07em;color:#64748B;margin-bottom:10px">Your spending split</div>'
            f'<div style="margin-bottom:12px">'
            f'<div style="font-size:10px;font-weight:500;text-transform:uppercase;'
            f'letter-spacing:.06em;color:#98A2B3;margin-bottom:3px">Fixed bills</div>'
            f'<div style="font-size:22px;font-weight:600;color:#374151;'
            f'font-variant-numeric:tabular-nums">{ui.fmt_money(period.fixed_total, sym)}</div>'
            f'<div style="font-size:11px;color:#98A2B3;margin-top:1px">Rent, utilities, insurance</div>'
            f'</div>'
            f'<div style="height:0.5px;background:#F1F5F9;margin-bottom:12px"></div>'
            f'<div>'
            f'<div style="font-size:10px;font-weight:500;text-transform:uppercase;'
            f'letter-spacing:.06em;color:#98A2B3;margin-bottom:3px">Cuttable spend</div>'
            f'<div style="font-size:22px;font-weight:600;color:#6941C6;'
            f'font-variant-numeric:tabular-nums">{ui.fmt_money(period.flex_total, sym)}</div>'
            f'<div style="font-size:11px;color:#98A2B3;margin-top:1px">Groceries, dining, shopping</div>'
            f'</div>',
            mb="8px",
        ) +
        _card(
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.07em;color:#64748B;margin-bottom:10px">Budget check</div>'
            f'{_budget_rows}',
        ),
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  3.  TOP SPENDING AREAS
#  Left: categories (ONE call). Right: biggest spends + subs (ONE call).
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Top spending areas"), unsafe_allow_html=True)
_c_cats, _c_spends = st.columns([1.1, 1])

with _c_cats:
    _cat_bars = ""
    for _, _row in exp_by_cat.head(5).iterrows():
        _pct = _row["Total"] / period.total_expense * 100 if period.total_expense > 0 else 0
        _cat_bars += (
            f'<div style="margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:12.5px;color:#374151;margin-bottom:3px">'
            f'<span style="font-weight:500">{_row["Category"]}</span>'
            f'<span style="color:#6941C6;font-weight:600;font-variant-numeric:tabular-nums">'
            f'{ui.fmt_money(_row["Total"], sym)}</span></div>'
            f'<div style="background:#EAECF0;border-radius:3px;height:5px;overflow:hidden">'
            f'<div style="width:{min(_pct,100):.1f}%;height:100%;background:#6941C6;border-radius:3px">'
            f'</div></div></div>'
        )
    st.markdown(
        f'<div style="font-size:10.5px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:.07em;color:#64748B;margin-bottom:7px">Top categories</div>'
        + _card(_cat_bars, mb="0"),
        unsafe_allow_html=True,
    )

with _c_spends:
    _right_html = (
        f'<div style="font-size:10.5px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:.07em;color:#64748B;margin-bottom:7px">Biggest single spends</div>'
    )
    for _, _row in top_txns.head(3).iterrows():
        _amt  = ui.fmt_money(abs(float(_row["Amount"])), sym)
        _desc = str(_row["Description"])[:42]
        _dt   = _row["Date"].strftime("%d %b %Y")
        _cat  = str(_row["Category"])
        _right_html += (
            f'<div style="border:1px solid #EAECF0;border-radius:8px;'
            f'padding:8px 13px;margin-bottom:6px">'
            f'<div style="font-size:16px;font-weight:600;color:#F04438;'
            f'font-variant-numeric:tabular-nums;letter-spacing:-0.3px">{_amt}</div>'
            f'<div style="font-size:12px;font-weight:500;color:#374151;margin:1px 0">{_desc}</div>'
            f'<div style="font-size:10.5px;color:#94A3B8">{_dt} · {_cat}</div>'
            f'</div>'
        )
    if not subs.empty:
        _right_html += (
            f'<div style="font-size:10.5px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.07em;color:#64748B;margin:8px 0 6px">Subscriptions</div>'
            f'<div style="border:1px solid #EAECF0;border-radius:8px;padding:8px 13px">'
        )
        for _, _r in subs.head(4).iterrows():
            _right_html += (
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:4px 0;border-bottom:0.5px solid #F2F4F7">'
                f'<span style="font-size:12px;color:#374151">{_r["Description"]}</span>'
                f'<span style="font-size:12px;font-weight:600;color:#F04438;'
                f'font-variant-numeric:tabular-nums">{ui.fmt_money(_r["Amount"], sym)}</span>'
                f'</div>'
            )
        _right_html += (
            f'<div style="display:flex;justify-content:space-between;padding:5px 0 1px;'
            f'font-size:10.5px;color:#98A2B3;font-weight:500">'
            f'<span>Total / period</span>'
            f'<span style="font-size:12.5px;font-weight:600;color:#F04438;'
            f'font-variant-numeric:tabular-nums">{ui.fmt_money(period.sub_total, sym)}</span>'
            f'</div></div>'
        )
    st.markdown(_right_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  4.  SPENDING PATTERNS
#  Balance chart full width. Heatmap | savings rate side by side.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Spending patterns"), unsafe_allow_html=True)

_bal_fig = charts.balance_trend(fdf, sym)
if _bal_fig is not None:
    st.markdown(_chart_label("Balance over time"), unsafe_allow_html=True)
    st.plotly_chart(_bal_fig, use_container_width=True, config={"displayModeBar": False})

_c_heat, _c_sr = st.columns(2)
with _c_heat:
    st.markdown(_chart_label("When do you spend?"), unsafe_allow_html=True)
    st.plotly_chart(charts.spending_heatmap(fdf, sym),
                    use_container_width=True, config={"displayModeBar": False})
with _c_sr:
    st.markdown(_chart_label("Savings rate over time"), unsafe_allow_html=True)
    st.plotly_chart(charts.savings_trend(sr_trend),
                    use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
#  5.  INSIGHTS & ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Insights & actions"), unsafe_allow_html=True)
tab_story, tab_actions, tab_ai = st.tabs(["What happened", "What to do", "AI insights"])

with tab_story:
    _earned = ui.fmt_money(period.total_income, sym)
    _spent  = ui.fmt_money(period.total_expense, sym)
    _net    = ui.fmt_money(abs(period.net), sym, signed=False)
    _net_dir = "ahead" if period.net >= 0 else "short"
    _story_items = [
        f'You earned <b>{_earned}</b> and spent <b>{_spent}</b>. You came out <b>{_net} {_net_dir}</b>.',
        f'<b>{period.flex_pct:.0f}%</b> of your spending (<b>{ui.fmt_money(period.flex_total, sym)}</b>) is discretionary. The other <b>{100-period.flex_pct:.0f}%</b> (<b>{ui.fmt_money(period.fixed_total, sym)}</b>) are fixed bills.' if hasattr(period, 'flex_pct') else None,
        f'A savings rate of <b>{period.savings_rate:.1f}%</b> is {"excellent — you\'re genuinely building a financial cushion" if period.savings_rate >= 20 else "below the 20% goal — try to reduce discretionary spending"}.',
        f'<b>{top_cat}</b> was your biggest cost at <b>{ui.fmt_money(float(exp_by_cat.iloc[0]["Total"]), sym)}</b> ({float(exp_by_cat.iloc[0]["Total"])/period.total_expense*100:.0f}% of all spending).' if top_cat and not exp_by_cat.empty else None,
        f'Subscriptions cost <b>{ui.fmt_money(period.sub_total, sym)}</b> this period.' if period.sub_total > 0 else None,
    ]
    _story_left  = [s for s in _story_items[:3] if s]
    _story_right = [s for s in _story_items[3:] if s]
    _sc1, _sc2 = st.columns(2)
    with _sc1:
        st.markdown(
            "".join(f'<p style="font-size:13.5px;line-height:1.65;color:#374151;margin-bottom:8px">{s}</p>' for s in _story_left),
            unsafe_allow_html=True,
        )
    with _sc2:
        st.markdown(
            "".join(f'<p style="font-size:13.5px;line-height:1.65;color:#374151;margin-bottom:8px">{s}</p>' for s in _story_right),
            unsafe_allow_html=True,
        )

with tab_actions:
    _actions = []
    if period.savings_rate < 10:
        _actions.append(("Review discretionary spending", "Your savings rate is below 10%. Identify your top 2 non-essential categories and set a monthly limit."))
    if period.sub_total > 0:
        _actions.append(("Audit subscriptions", f"You're spending {ui.fmt_money(period.sub_total, sym)}/period on subscriptions. Cancel any you haven't used this month."))
    if period.net >= 0 and period.savings_rate >= 20:
        _actions.append(("Invest your surplus", f"You're saving {period.savings_rate:.0f}% — put the surplus into an index fund or high-interest account."))
    if not _actions:
        _actions.append(("Keep it up", "Your financial habits are healthy. Stay consistent."))
    _ac1, _ac2 = st.columns(2)
    for _i, (title, desc) in enumerate(_actions[:4]):
        _col = _ac1 if _i % 2 == 0 else _ac2
        with _col:
            st.markdown(
                f'<div style="background:#fff;border:1px solid #EAECF0;border-radius:8px;'
                f'padding:10px 14px;margin-bottom:8px;display:flex;gap:10px;align-items:flex-start">'
                f'<div style="width:18px;height:18px;background:#F4EBFF;color:#6941C6;border-radius:4px;'
                f'display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;'
                f'flex-shrink:0;margin-top:1px">{_i+1}</div>'
                f'<div><div style="font-size:13px;font-weight:600;color:#101828;margin-bottom:2px">{title}</div>'
                f'<div style="font-size:12px;color:#667085;line-height:1.5">{desc}</div></div></div>',
                unsafe_allow_html=True,
            )

with tab_ai:
    _has_key = bool((api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", ""))
    if run_ai and _has_key:
        with st.spinner("Generating AI insights…"):
            try:
                import requests as _req
                _prompt = (
                    f"You are a personal finance coach. Analyse this statement:\n"
                    f"Income: {ui.fmt_money(period.total_income, sym)}, "
                    f"Expenses: {ui.fmt_money(period.total_expense, sym)}, "
                    f"Savings rate: {period.savings_rate:.1f}%, "
                    f"Top category: {top_cat or 'N/A'}, "
                    f"Subscriptions: {ui.fmt_money(period.sub_total, sym)}.\n"
                    f"Give 3 short, plain-English insights and 2 actionable steps. "
                    f"Use simple language. No jargon. Max 120 words total."
                )
                _r = _req.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY",""),
                             "content-type": "application/json",
                             "anthropic-version": "2023-06-01"},
                    json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                          "messages": [{"role": "user", "content": _prompt}]},
                    timeout=20,
                )
                _ai_text = _r.json()["content"][0]["text"] if _r.status_code == 200 else "Could not load insights."
            except Exception as _e:
                _ai_text = f"Could not generate insights: {_e}"
        st.markdown(
            f'<div style="background:#F9FAFB;border:1px solid #EAECF0;border-radius:10px;padding:16px 20px">'
            f'<div style="font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;'
            f'color:#6941C6;margin-bottom:10px">AI Coach</div>'
            f'<div style="font-size:13.5px;color:#374151;line-height:1.7;white-space:pre-line">{_ai_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="padding:20px;text-align:center;color:#98A2B3;font-size:13px">'
            'Enter your Anthropic API key and click <b>✦ AI Insights</b> for personalised coaching.</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  6.  FINANCIAL HEALTH EXPLAINED
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Your financial health explained"), unsafe_allow_html=True)

_band_info = {
    "Excellent":       ("#ECFDF3", "#12B76A", "Your finances are in great shape — keep up the good habits.",
                        "Consider investing your savings surplus or building an emergency fund."),
    "Healthy":         ("#F4EBFF", "#6941C6", "You have solid financial habits with a few areas to improve.",
                        "Focus on the lowest-scoring components below to push into the Excellent band."),
    "Needs attention": ("#FFFAEB", "#D97706", "Some areas of your finances need attention.",
                        "Start with the red components in the breakdown — they have the biggest impact."),
    "At risk":         ("#FEF3F2", "#F04438", "Multiple financial areas are under stress.",
                        "Focus on reducing spending and building a small emergency buffer first."),
}
_bi = _band_info.get(period.score_label, ("#F9FAFB", "#667085", "", ""))
_score_c = "#34D399" if period.health_score >= 85 else "#A78BFA" if period.health_score >= 70 else "#FBBF24" if period.health_score >= 50 else "#F87171"

st.markdown(
    f'<div style="background:{_bi[0]};border-radius:10px;padding:13px 18px;'
    f'display:flex;align-items:flex-start;gap:14px;margin-bottom:10px">'
    f'<div style="font-size:36px;font-weight:600;line-height:1;color:{_score_c};'
    f'font-variant-numeric:tabular-nums;flex-shrink:0">{period.health_score}</div>'
    f'<div><div style="font-size:13px;font-weight:600;color:{_bi[1]};margin-bottom:3px">'
    f'{period.score_label} — {_bi[2]}</div>'
    f'<div style="font-size:12.5px;color:{_bi[1]};opacity:.8">💡 {_bi[3]}</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

_breakdown = score_breakdown(fdf)
_bd_chart_col, _bd_tips_col = st.columns([1.2, 1])
with _bd_chart_col:
    st.markdown(_chart_label("Score breakdown"), unsafe_allow_html=True)
    st.plotly_chart(charts.score_breakdown_chart(_breakdown),
                    use_container_width=True, config={"displayModeBar": False})
with _bd_tips_col:
    _tips_html = '<div style="font-size:10.5px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:#64748B;margin-bottom:8px">What each score means</div>'
    for _comp in _breakdown:
        _p = _comp.score / _comp.max_score * 100 if _comp.max_score > 0 else 0
        _dot = "#12B76A" if _p >= 80 else "#F79009" if _p >= 50 else "#F04438"
        _tips_html += (
            f'<div style="display:flex;gap:7px;margin-bottom:8px;align-items:flex-start">'
            f'<div style="width:7px;height:7px;border-radius:50%;background:{_dot};'
            f'flex-shrink:0;margin-top:4px"></div>'
            f'<div><div style="font-size:12.5px;font-weight:500;color:#374151">'
            f'{_comp.label} '
            f'<span style="color:#98A2B3;font-size:11px">{_comp.score:.0f}/{_comp.max_score:.0f} pts</span>'
            f'</div><div style="font-size:11.5px;color:#98A2B3;margin-top:1px">{_comp.tip}</div>'
            f'</div></div>'
        )
    st.markdown(_tips_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  7.  TRANSACTIONS THAT NEED CHECKING
#  Compact review table — max 8 visible rows, progress bar, confirm workflow.
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Transactions that need checking"), unsafe_allow_html=True)
st.markdown(
    '<p style="font-size:12.5px;color:#98A2B3;margin-bottom:8px">'
    'Review each flagged transaction, assign the correct category, then click Confirm. '
    'Confirmed transactions move to the Transaction Explorer automatically.</p>',
    unsafe_allow_html=True,
)

_pending = master_df[master_df["ReviewStatus"] == "Review"].copy() if "ReviewStatus" in master_df.columns else pd.DataFrame()
_reviewed_n = int((master_df["ReviewStatus"] == "Reviewed").sum()) if "ReviewStatus" in master_df.columns else 0
_total_flagged = len(_pending) + _reviewed_n

if _total_flagged > 0:
    _pct_done = int(_reviewed_n / _total_flagged * 100)
    st.markdown(
        f'<div style="background:#F9FAFB;border:1px solid #EAECF0;border-radius:8px;'
        f'padding:9px 14px;margin-bottom:10px;display:flex;align-items:center;gap:14px">'
        f'<div style="flex:1;background:#EAECF0;border-radius:99px;height:5px;overflow:hidden">'
        f'<div style="width:{_pct_done}%;height:100%;background:#12B76A;border-radius:99px"></div>'
        f'</div>'
        f'<div style="font-size:12.5px;color:#374151;white-space:nowrap">'
        f'<b>{_reviewed_n}</b> of <b>{_total_flagged}</b> reviewed'
        f'{"  ✅" if len(_pending)==0 else f"  —  {len(_pending)} remaining"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

if _pending.empty:
    st.markdown(
        '<div style="padding:16px;text-align:center;color:#98A2B3;font-size:13px;'
        'background:#F9FAFB;border:1px solid #EAECF0;border-radius:10px">'
        '✅ All flagged transactions have been reviewed.</div>',
        unsafe_allow_html=True,
    )
else:
    # Column header — ONE markdown call
    _h = st.columns([1.1, 2.8, 1, 2, 1.8, 0.7])
    for _col, _lbl in zip(_h, ["Date", "Description", "Amount", "Category", "Why flagged", ""]):
        _col.markdown(
            f'<div style="font-size:9.5px;font-weight:500;text-transform:uppercase;'
            f'letter-spacing:.06em;color:#98A2B3;padding-bottom:3px;'
            f'border-bottom:1px solid #EAECF0">{_lbl}</div>',
            unsafe_allow_html=True,
        )

    # Show max 10 rows to keep section compact
    for _idx, _row in list(_pending.iterrows())[:10]:
        _c1, _c2, _c3, _c4, _c5, _c6 = st.columns([1.1, 2.8, 1, 2, 1.8, 0.7])
        with _c1:
            st.markdown(
                f'<div style="font-size:11.5px;color:#98A2B3;padding-top:6px">'
                f'{_row["Date"].strftime("%d %b %Y")}</div>',
                unsafe_allow_html=True,
            )
        with _c2:
            st.markdown(
                f'<div style="font-size:13px;font-weight:500;color:#374151;padding-top:6px;'
                f'overflow:hidden;white-space:nowrap;text-overflow:ellipsis" '
                f'title="{_row["Description"]}">'
                f'{str(_row["Description"])[:45]}</div>',
                unsafe_allow_html=True,
            )
        with _c3:
            _amt = float(_row["Amount"])
            _ac  = "#12B76A" if _amt >= 0 else "#F04438"
            st.markdown(
                f'<div style="font-size:13px;font-weight:600;color:{_ac};'
                f'font-variant-numeric:tabular-nums;padding-top:6px">'
                f'{ui.fmt_money(_amt, sym)}</div>',
                unsafe_allow_html=True,
            )
        with _c4:
            _cur_cat = str(_row.get("Category", "Other Expense"))
            _def_idx = _all_categories.index(_cur_cat) if _cur_cat in _all_categories else 0
            _sel = st.selectbox("", _all_categories, index=_def_idx,
                                key=f"sel_{_idx}", label_visibility="collapsed")
        with _c5:
            _flag = str(_row.get("Flag", ""))
            st.markdown(
                f'<div style="font-size:11px;color:#F79009;padding-top:6px">'
                f'{_flag[:38]}</div>',
                unsafe_allow_html=True,
            )
        with _c6:
            if st.button("✓", key=f"confirm_{_idx}", help="Confirm category"):
                _final = st.session_state.get(f"sel_{_idx}", _sel)
                st.session_state[_file_key].at[_idx, "Category"]    = _final
                st.session_state[_file_key].at[_idx, "ReviewStatus"] = "Reviewed"
                st.session_state[_file_key].at[_idx, "NeedsReview"]  = False
                st.session_state[_file_key].at[_idx, "Flag"]         = ""
                st.toast(f"✓ {str(_row['Description'])[:30]} → {_final}", icon="✅")
                st.rerun()

        st.markdown('<div style="height:0.5px;background:#F2F4F7;margin:1px 0"></div>',
                    unsafe_allow_html=True)

    if len(_pending) > 10:
        st.markdown(
            f'<div style="text-align:center;font-size:12px;color:#98A2B3;'
            f'margin-top:6px">{len(_pending)-10} more transactions not shown — '
            f'confirm above to see the next batch.</div>',
            unsafe_allow_html=True,
        )

    with st.expander("➕ Need a category that isn't in the list?"):
        _nc1, _nc2 = st.columns([3, 1])
        with _nc1:
            _new_cat = st.text_input("New category name", placeholder="e.g. Pet care, Hobbies…",
                                     key="new_category_input")
        with _nc2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add", key="add_category_btn"):
                _nc = _new_cat.strip()
                if _nc and _nc not in st.session_state[_custom_key]:
                    st.session_state[_custom_key].append(_nc)
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  8.  TRANSACTION EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(_sec("Transaction explorer"), unsafe_allow_html=True)
st.markdown(
    '<p style="font-size:12.5px;color:#98A2B3;margin-bottom:8px">'
    'All your transactions — including ones you have already reviewed and confirmed.</p>',
    unsafe_allow_html=True,
)

_te1, _te2, _te3 = st.columns([3, 1, 1])
with _te1:
    _txn_search = st.text_input("Search", placeholder="Search transactions, merchants…",
                                label_visibility="collapsed", key="txn_search")
with _te2:
    _show_flagged = st.toggle("Show only flagged ⚑", key="show_flagged")
with _te3:
    if "txn_page" not in st.session_state:
        st.session_state["txn_page"] = 0

# Build display dataframe
_show_cols = [c for c in ["Date","Description","Amount","Category","Type","ReviewStatus","Confidence","Flag"] if c in fdf.columns]
_txn_df = fdf[_show_cols].copy()
if _txn_search:
    _m = (_txn_df["Description"].astype(str).str.contains(_txn_search, case=False, na=False) |
          _txn_df["Category"].astype(str).str.contains(_txn_search, case=False, na=False))
    _txn_df = _txn_df[_m]
    st.session_state["txn_page"] = 0
if _show_flagged and "Flag" in _txn_df.columns:
    _txn_df = _txn_df[_txn_df["Flag"] != ""]
    st.session_state["txn_page"] = 0
_txn_df = _txn_df.sort_values("Date", ascending=False).reset_index(drop=True)

_PAGE  = 12
_table_html, _total_pages = ui.styled_transaction_table(
    _txn_df, sym=sym, max_rows=_PAGE, page=st.session_state["txn_page"])
_start = st.session_state["txn_page"] * _PAGE + 1
_end   = min(_start + _PAGE - 1, len(_txn_df))
_pend_n = int((fdf["ReviewStatus"] == "Review").sum()) if "ReviewStatus" in fdf.columns else 0

st.markdown(
    f'<div style="font-size:12px;color:#98A2B3;margin-bottom:6px">'
    f'Showing {_start}–{_end} of {len(_txn_df)} transactions'
    f'{f"  ·  {_pend_n} pending review" if _pend_n > 0 else ""}'
    f'</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div style="background:#fff;border:1px solid #EAECF0;border-radius:10px;'
    f'padding:2px 0;overflow:hidden">{_table_html}</div>',
    unsafe_allow_html=True,
)

if _total_pages > 1:
    _p1, _p2, _p3 = st.columns([1, 2, 1])
    with _p1:
        if st.button("← Previous", disabled=st.session_state["txn_page"] == 0, key="txn_prev"):
            st.session_state["txn_page"] -= 1
            st.rerun()
    with _p2:
        st.markdown(
            f'<div style="text-align:center;font-size:12px;color:#98A2B3;padding-top:8px">'
            f'Page {st.session_state["txn_page"]+1} of {_total_pages}</div>',
            unsafe_allow_html=True,
        )
    with _p3:
        if st.button("Next →", disabled=st.session_state["txn_page"] >= _total_pages-1, key="txn_next"):
            st.session_state["txn_page"] += 1
            st.rerun()

st.download_button(
    "⬇ Download transactions CSV",
    data=(fdf.assign(Date=fdf["Date"].dt.strftime("%Y-%m-%d")).to_csv(index=False).encode("utf-8")),
    file_name="money_health_transactions.csv",
    mime="text/csv",
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;font-size:11px;color:#98A2B3;'
    'margin-top:20px;padding:10px 0;border-top:1px solid #EAECF0">'
    'Money Health Agent is for personal education and spending awareness only. '
    'It does not constitute financial, tax, investment, or credit advice. '
    'Consult a licensed financial adviser for professional guidance.</div>',
    unsafe_allow_html=True,
)
