"""
charts.py  —  All Plotly chart builders.

Every chart is a pure function: receives data, returns a Figure.
All styling flows from config.py tokens — change a token, every chart updates.

Design principles applied in this revision:
  1. One colour per semantic meaning across all charts (config.py constants)
  2. Labels only on bars large enough to hold them (≥ $500 threshold)
  3. Savings rate y-axis floored at -20% to prevent one outlier distorting scale
  4. Treemap uses single-hue blue scale matching the accent colour family
  5. Font: Inter (matches ui.py body font — no mixed typefaces)
  6. Grid lines: very subtle (#F3F4F6) — guides, not distractions
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
    WARNING_COLOR,
    TREEMAP_SCALE,
    DAY_ORDER,
)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════
_FONT = "'Inter', 'Plus Jakarta Sans', sans-serif"
_TEXT = "#374151"    # text_secondary — not too dark, not too muted
_GRID = "#F3F4F6"    # barely-there gridlines
_LINE = "#E5E7EB"    # axis lines


def _layout(
    height: int = 360,
    t: int = 16, b: int = 32, l: int = 4, r: int = 8,
    **kwargs,
) -> dict:
    """Single source of truth for all chart layout properties."""
    return dict(
        height        = height,
        paper_bgcolor = "#FFFFFF",
        plot_bgcolor  = "#FFFFFF",
        font          = {"family": _FONT, "color": _TEXT, "size": 12},
        margin        = dict(t=t, b=b, l=l, r=r),
        **kwargs,
    )


def _xax(**kw) -> dict:
    return dict(
        title      = "",
        zeroline   = False,
        linecolor  = _LINE,
        showgrid   = False,
        tickfont   = {"size": 11, "color": _TEXT},
        **kw,
    )


def _yax(prefix: str = "", suffix: str = "", **kw) -> dict:
    ax = dict(
        title     = "",
        zeroline  = False,
        linecolor = _LINE,
        showgrid  = True,
        gridcolor = _GRID,
        gridwidth = 1,
        tickfont  = {"size": 11, "color": _TEXT},
    )
    if prefix: ax["tickprefix"] = prefix
    if suffix: ax["ticksuffix"] = suffix
    ax.update(kw)
    return ax


def _fmt(v: float, currency: str = "$") -> str:
    """Compact money label — whole dollars ≥ $1,000, two decimals below."""
    return f"{currency}{abs(v):,.0f}" if abs(v) >= 1_000 else f"{currency}{abs(v):,.2f}"


# ══════════════════════════════════════════════════════════════════════════════
#  1. CASHFLOW WATERFALL
# ══════════════════════════════════════════════════════════════════════════════
_LABEL_THRESHOLD = 500   # only label bars with absolute value ≥ this


def waterfall_chart(
    exp_by_category: pd.DataFrame,
    total_income:    float,
    total_expense:   float,
    net:             float,
    currency:        str = "$",
) -> go.Figure:
    """
    Shows the complete money flow: income → each expense category → net.

    Labels are suppressed on small bars (< $500) to reduce clutter.
    Colours: green income · red expenses · blue net total.
    """
    cats = exp_by_category["Category"].head(9).tolist()
    vals = (-exp_by_category["Total"].head(9)).tolist()

    # Aggregate any tail into "Other"
    shown    = exp_by_category["Total"].head(9).sum()
    residual = -(total_expense - shown)
    if abs(residual) > 0.5:
        cats.append("Other")
        vals.append(residual)

    # Build labels — blank for small bars to keep the chart readable
    def _bar_label(v: float, signed: bool = True) -> str:
        if abs(v) < _LABEL_THRESHOLD:
            return ""
        if signed:
            return f"-{_fmt(abs(v), currency)}" if v < 0 else f"+{_fmt(v, currency)}"
        return _fmt(v, currency)

    labels = (
        [_fmt(total_income, currency)]
        + [_bar_label(v) for v in vals]
        + [_bar_label(net, signed=True)]
    )

    net_color = ACCENT_COLOR if net >= 0 else EXPENSE_COLOR

    fig = go.Figure(go.Waterfall(
        orientation  = "v",
        measure      = ["absolute"] + ["relative"] * len(cats) + ["total"],
        x            = ["Income"] + cats + ["Net"],
        y            = [total_income] + vals + [0],
        text         = labels,
        textposition = "outside",
        textfont     = {"size": 10, "family": _FONT, "color": _TEXT},
        connector    = {"line": {"color": _GRID, "width": 1}},
        increasing   = {"marker": {"color": INCOME_COLOR,  "line": {"width": 0}}},
        decreasing   = {"marker": {"color": EXPENSE_COLOR, "line": {"width": 0}}},
        totals       = {"marker": {"color": net_color,     "line": {"width": 0}}},
    ))
    fig.update_layout(
        **_layout(height=400),
        showlegend = False,
        xaxis      = _xax(),
        yaxis      = _yax(prefix=currency),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  2. SPENDING TREEMAP
# ══════════════════════════════════════════════════════════════════════════════
def spending_treemap(
    exp_by_category: pd.DataFrame,
    currency:        str = "$",
) -> go.Figure:
    """
    Area-proportional category breakdown.
    Uses a single-hue blue scale (matches the accent colour family).
    """
    fig = px.treemap(
        exp_by_category,
        path   = ["Category"],
        values = "Total",
        color  = "Total",
        color_continuous_scale = TREEMAP_SCALE,
    )
    fig.update_traces(
        texttemplate  = f"<b>%{{label}}</b><br>{currency}%{{value:,.0f}}",
        textfont      = {"size": 12, "family": _FONT},
        hovertemplate = f"<b>%{{label}}</b><br>{currency}%{{value:,.2f}}<extra></extra>",
        marker_line_width = 0.5,
        marker_line_color = "#FFFFFF",
    )
    fig.update_layout(
        **_layout(height=380, b=8),
        coloraxis_showscale = False,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  3. DAY-OF-WEEK BAR
# ══════════════════════════════════════════════════════════════════════════════
def dow_bar(
    dow_df:   pd.DataFrame,
    currency: str = "$",
) -> go.Figure:
    """
    Total spending per day of week.
    Peak day highlighted in accent blue; all others in neutral grey.
    Zero-spend days shown as empty bars (not suppressed).
    """
    non_zero = dow_df[dow_df["Amount"] > 0]
    if non_zero.empty:
        peak_day = dow_df.iloc[0]["DOW"]
    else:
        peak_day = non_zero.loc[non_zero["Amount"].idxmax(), "DOW"]

    colors = [ACCENT_COLOR if d == peak_day else NEUTRAL_COLOR for d in dow_df["DOW"]]

    # Label only days with actual spending
    labels = [
        f"{currency}{v:,.0f}" if v > 0 else ""
        for v in dow_df["Amount"]
    ]

    fig = go.Figure(go.Bar(
        x                 = dow_df["DOW"],
        y                 = dow_df["Amount"],
        marker_color      = colors,
        marker_line_width = 0,
        text              = labels,
        textposition      = "outside",
        textfont          = {"size": 10, "family": _FONT, "color": _TEXT},
    ))
    fig.update_layout(
        **_layout(height=300),
        xaxis = _xax(),
        yaxis = _yax(prefix=currency, showticklabels=False, showgrid=False),
        annotations = [dict(
            text      = f"Most spending on <b>{peak_day}s</b>",
            x=0.0, y=1.08, xref="paper", yref="paper",
            showarrow = False,
            font      = {"size": 12, "color": ACCENT_COLOR, "family": _FONT},
            align     = "left",
        )],
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  4. SAVINGS RATE TREND
# ══════════════════════════════════════════════════════════════════════════════
def savings_trend(sr_df: pd.DataFrame) -> go.Figure:
    """
    Monthly savings rate as a line chart.

    Improvements over previous version:
      - Y-axis floored at -20% so one bad month can't squash the whole chart
      - Dot colours: green ≥ 20%, amber ≥ 10%, red < 10%
      - Fill area clipped at zero (only positive savings shaded)
      - Axis labels shown as integers (no decimal noise)
    """
    def _dot_color(v: float) -> str:
        if v >= 20: return INCOME_COLOR
        if v >= 10: return WARNING_COLOR
        return EXPENSE_COLOR

    dot_colors = sr_df["SavingsRate"].apply(_dot_color).tolist()

    # Y-axis range: floor at -20 so outliers don't distort scale
    y_min = max(sr_df["SavingsRate"].min() - 5, -20)
    y_max = sr_df["SavingsRate"].max() + 10

    fig = go.Figure()

    # 20% goal reference line
    fig.add_hline(
        y                  = 20,
        line_dash          = "dot",
        line_color         = "#BBF7D0",   # light green — guides, not distracts
        line_width         = 1.5,
        annotation_text    = "20% goal",
        annotation_position= "right",
        annotation_font    = {"size": 10, "color": INCOME_COLOR, "family": _FONT},
    )

    # Zero reference line (only shown if any negatives exist)
    if y_min < 0:
        fig.add_hline(y=0, line_color=_LINE, line_width=1)

    # Savings rate line + fill
    fig.add_trace(go.Scatter(
        x            = sr_df["Month"],
        y            = sr_df["SavingsRate"],
        mode         = "lines+markers+text",
        line         = dict(color=ACCENT_COLOR, width=2),
        marker       = dict(
            size  = 8,
            color = dot_colors,
            line  = dict(color="#FFFFFF", width=2),
        ),
        text         = [f"{v:.0f}%" for v in sr_df["SavingsRate"]],
        textposition = "top center",
        textfont     = {"size": 10, "family": _FONT, "color": _TEXT},
        fill         = "tozeroy",
        fillcolor    = "rgba(37,99,235,0.06)",
    ))

    fig.update_layout(
        **_layout(height=300),
        showlegend = False,
        xaxis      = _xax(),
        yaxis      = _yax(
            suffix        = "%",
            range         = [y_min, y_max],
            tickformat    = ".0f",
        ),
    )
    return fig
