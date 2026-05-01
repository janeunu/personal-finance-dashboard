"""
charts.py
Every chart is a pure function: receives data, returns a plotly Figure.

Rules:
  • No Streamlit imports.
  • No business logic — receives already-computed data.
  • All styling is consistent via _layout() and _axes().
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import (
    INCOME_COLOR,
    EXPENSE_COLOR,
    ACCENT_COLOR,
    NEUTRAL_COLOR,
    CHART_COLORS,
    TREEMAP_SCALE,
    DAY_ORDER,
)


# ── Shared layout helpers ─────────────────────────────────────────────────────
_FONT_FAMILY = "'DM Sans', sans-serif"
_FONT_COLOR  = "#5a4e42"


def _layout(
    height: int = 360,
    t: int = 14, b: int = 28, l: int = 4, r: int = 4,
    **kwargs,
) -> dict:
    """Single source of truth for chart layout defaults."""
    return dict(
        height         = height,
        paper_bgcolor  = "#ffffff",
        plot_bgcolor   = "#ffffff",
        font           = {"family": _FONT_FAMILY, "color": _FONT_COLOR},
        margin         = dict(t=t, b=b, l=l, r=r),
        **kwargs,
    )
    base = dict(title="", zeroline=False, linecolor="#ddd4c8", showticklabels=True)
    if grid:
        base.update(showgrid=True, gridcolor="#f4ede4", gridwidth=1)
    else:
        base.update(showgrid=False)
    return base


def _xax(grid: bool = False) -> dict:
    base = dict(title="", zeroline=False, linecolor="#ddd4c8", showticklabels=True)
    if grid:
        base.update(showgrid=True, gridcolor="#f4ede4", gridwidth=1)
    else:
        base.update(showgrid=False)
    return base


def _yax(prefix: str = "", suffix: str = "") -> dict:
    ax = dict(
        title="", zeroline=False, linecolor="#ddd4c8",
        showgrid=True, gridcolor="#f4ede4", gridwidth=1,
    )
    if prefix: ax["tickprefix"] = prefix
    if suffix: ax["ticksuffix"] = suffix
    return ax


# ── 1. Cashflow waterfall ─────────────────────────────────────────────────────
def waterfall_chart(
    exp_by_category: pd.DataFrame,
    total_income:    float,
    total_expense:   float,
    net:             float,
    currency:        str = "$",
) -> go.Figure:
    """Income → each expense category → net cashflow."""
    cats = exp_by_category["Category"].head(9).tolist()
    vals = (-exp_by_category["Total"].head(9)).tolist()

    # Aggregate tail categories into "Other"
    shown   = exp_by_category["Total"].head(9).sum()
    residual = -(total_expense - shown)
    if abs(residual) > 0.5:
        cats.append("Other")
        vals.append(residual)

    def _fmt(v: float) -> str:
        return f"{currency}{abs(v):,.0f}" if abs(v) >= 1000 else f"{currency}{abs(v):,.2f}"

    labels = (
        [_fmt(total_income)]
        + [f"-{_fmt(abs(v))}" for v in vals]
        + [(f"+{_fmt(net)}" if net >= 0 else f"-{_fmt(abs(net))}")]
    )

    fig = go.Figure(go.Waterfall(
        orientation  = "v",
        measure      = ["absolute"] + ["relative"] * len(cats) + ["total"],
        x            = ["Income"] + cats + ["Net"],
        y            = [total_income] + vals + [0],
        text         = labels,
        textposition = "outside",
        textfont     = {"size": 10, "family": _FONT_FAMILY},
        connector    = {"line": {"color": "#e8ddd2", "width": 1}},
        increasing   = {"marker": {"color": INCOME_COLOR,  "line": {"width": 0}}},
        decreasing   = {"marker": {"color": EXPENSE_COLOR, "line": {"width": 0}}},
        totals       = {"marker": {"color": "#5b7cf0",     "line": {"width": 0}}},
    ))
    fig.update_layout(
        **_layout(height=400),
        showlegend = False,
        xaxis = {**_xax(), "tickfont": {"size": 11}},
        yaxis = _yax(prefix=currency),
    )
    return fig


# ── 2. Fixed vs flexible donut ────────────────────────────────────────────────
def fixed_vs_flex_donut(
    fixed_total:   float,
    flex_total:    float,
    total_expense: float,
    currency:      str = "$",
) -> go.Figure:
    """Shows what proportion of spending is cuttable."""
    total_label = f"{currency}{total_expense:,.0f}" if total_expense >= 1000 \
                  else f"{currency}{total_expense:,.2f}"

    df = pd.DataFrame({
        "Type":   ["Fixed Bills", "Flexible Spending"],
        "Amount": [fixed_total, flex_total],
    })
    fig = px.pie(
        df, names="Type", values="Amount", hole=0.58,
        color_discrete_sequence=["#5b7cf0", EXPENSE_COLOR],
    )
    fig.update_traces(
        textposition = "inside",
        textinfo     = "percent+label",
        textfont_size = 12,
        pull         = [0, 0.03],
    )
    fig.update_layout(
        **_layout(height=230, b=10, l=0, r=0),
        showlegend  = False,
        annotations = [dict(
            text      = f"<b>{total_label}</b><br><span style='font-size:10px'>total spend</span>",
            x=0.5, y=0.5, font_size=13, showarrow=False,
            font      = {"family": _FONT_FAMILY, "color": "#2a1c10"},
        )],
    )
    return fig


# ── 3. Spending treemap ───────────────────────────────────────────────────────
def spending_treemap(
    exp_by_category: pd.DataFrame,
    currency:        str = "$",
) -> go.Figure:
    """Area-proportional breakdown of all expense categories."""
    fig = px.treemap(
        exp_by_category,
        path   = ["Category"],
        values = "Total",
        color  = "Total",
        color_continuous_scale = TREEMAP_SCALE,
    )
    fig.update_traces(
        texttemplate   = f"<b>%{{label}}</b><br>{currency}%{{value:,.0f}}",
        textfont       = {"size": 13, "family": _FONT_FAMILY},
        hovertemplate  = f"<b>%{{label}}</b><br>{currency}%{{value:,.2f}}<extra></extra>",
    )
    fig.update_layout(
        **_layout(height=400, b=8),
        coloraxis_showscale = False,
    )
    return fig


# ── 4. Day-of-week bar ────────────────────────────────────────────────────────
def dow_bar(
    dow_df:   pd.DataFrame,
    currency: str = "$",
) -> go.Figure:
    """Highlight peak spending day in accent color."""
    peak_day = dow_df.loc[dow_df["Amount"].idxmax(), "DOW"]
    colors   = [ACCENT_COLOR if d == peak_day else NEUTRAL_COLOR for d in dow_df["DOW"]]

    fig = go.Figure(go.Bar(
        x              = dow_df["DOW"],
        y              = dow_df["Amount"],
        marker_color   = colors,
        marker_line_width = 0,
        text           = [f"{currency}{v:,.0f}" for v in dow_df["Amount"]],
        textposition   = "outside",
        textfont       = {"size": 10},
    ))
    fig.update_layout(
        **_layout(height=320),
        xaxis = {**_xax(), "tickfont": {"size": 12}},
        yaxis = _yax(prefix=currency),
        annotations = [dict(
            text    = f"Most spending on <b>{peak_day}s</b>",
            x=0.01, y=1.06, xref="paper", yref="paper",
            showarrow = False,
            font      = {"size": 12, "color": "#8c7c6c", "family": _FONT_FAMILY},
        )],
    )
    return fig


# ── 5. Savings rate trend ─────────────────────────────────────────────────────
def savings_trend(sr_df: pd.DataFrame) -> go.Figure:
    """Line chart of monthly savings rate with a 20% goal line."""
    colors = sr_df["SavingsRate"].apply(
        lambda v: INCOME_COLOR if v >= 20 else "#e09a2e" if v >= 10 else EXPENSE_COLOR
    )

    fig = go.Figure()
    fig.add_hline(
        y=20, line_dash="dot", line_color="#c0d8c0", line_width=1.5,
        annotation_text="20% goal", annotation_position="right",
        annotation_font={"size": 10, "color": "#8ca88c"},
    )
    fig.add_trace(go.Scatter(
        x            = sr_df["Month"],
        y            = sr_df["SavingsRate"],
        mode         = "lines+markers+text",
        line         = dict(color="#5b7cf0", width=2.5),
        marker       = dict(size=10, color=colors, line=dict(color="#fff", width=2)),
        text         = [f"{v:.0f}%" for v in sr_df["SavingsRate"]],
        textposition = "top center",
        textfont     = {"size": 10, "family": _FONT_FAMILY},
        fill         = "tozeroy",
        fillcolor    = "rgba(91,124,240,.07)",
    ))
    fig.update_layout(
        **_layout(height=320),
        xaxis = {**_xax(), "tickfont": {"size": 11}},
        yaxis = _yax(suffix="%"),
    )
    return fig
