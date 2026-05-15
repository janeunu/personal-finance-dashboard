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
    NAVY_COLOR,
    ACCENT_COLOR,
    INCOME_COLOR,
    EXPENSE_COLOR,
    WARNING_COLOR,
    NEUTRAL_COLOR,
    TREEMAP_SCALE,
    CHART_COLORS,
    DAY_ORDER,
)


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════
_FONT = "'Inter', -apple-system, sans-serif"
_TEXT = "#64748B"    # slate-600 — matches ui.py text_secondary
_GRID = "#F1F5F9"    # slate-100 — barely visible gridlines
_LINE = "#E2E8F0"    # slate-200 — axis lines


def _layout(
    height: int = 360,
    t: int = 16, b: int = 32, l: int = 4, r: int = 8,
    **kwargs,
) -> dict:
    """Single source of truth for all chart layout properties."""
    return dict(
        height        = height,
        paper_bgcolor = "#FFFFFF",
        plot_bgcolor  = "#FFFFFF",   # charts sit on white card background
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
_LABEL_THRESHOLD = 1000   # only label bars with absolute value ≥ this


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
    _day_full = {"Mon":"Mondays","Tue":"Tuesdays","Wed":"Wednesdays",
                 "Thu":"Thursdays","Fri":"Fridays","Sat":"Saturdays","Sun":"Sundays"}
    fig.update_layout(
        **_layout(height=220),
        xaxis = _xax(),
        yaxis = _yax(prefix=currency, showticklabels=False, showgrid=False),
        annotations = [dict(
            text      = f"Most spending on <b>{_day_full.get(peak_day, peak_day)}</b>",
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
        fillcolor    = "rgba(37,99,235,0.05)",
    ))

    fig.update_layout(
        **_layout(height=185),
        showlegend = False,
        xaxis      = dict(
            **_xax(),
            tickangle = -25,
            nticks    = 5,
            tickfont  = {"size": 9, "family": _FONT},
        ),
        yaxis      = _yax(
            suffix        = "%",
            range         = [y_min, y_max],
            tickformat    = ".0f",
        ),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  5. SPENDING DONUT  (replaces treemap — universally understood)
# ══════════════════════════════════════════════════════════════════════════════
def spending_donut(
    exp_by_category: "pd.DataFrame",
    currency:        str = "$",
    max_slices:      int = 6,
) -> "go.Figure":
    """
    Simple donut chart showing top spending categories.
    Non-finance users understand donuts immediately — "what percentage is each slice?"

    Top N categories are shown; the rest are grouped into "Other".
    """
    if exp_by_category.empty:
        fig = go.Figure()
        fig.update_layout(**_layout(height=320))
        return fig

    top    = exp_by_category.head(max_slices).copy()
    other  = exp_by_category.iloc[max_slices:]["Total"].sum()
    if other > 0:
        top = pd.concat([top, pd.DataFrame({"Category": ["Other"], "Total": [other]})])

    total = float(top["Total"].sum())
    labels = [
        f"{row['Category']}<br>{currency}{row['Total']:,.0f}"
        for _, row in top.iterrows()
    ]

    fig = go.Figure(go.Pie(
        labels        = top["Category"],
        values        = top["Total"],
        hole          = 0.52,
        textinfo      = "percent",
        textfont      = {"size": 11, "family": _FONT},
        hovertemplate = f"<b>%{{label}}</b><br>{currency}%{{value:,.0f}}<extra></extra>",
        marker        = dict(
            colors    = CHART_COLORS[:len(top)],
            line      = dict(color="#FFFFFF", width=2),
        ),
        sort          = False,
    ))
    total_label = f"{currency}{total:,.0f}" if total < 100_000 else f"{currency}{total/1000:.0f}K"
    fig.update_layout(
        **_layout(height=310, b=12, l=0, r=0),
        showlegend  = True,
        legend      = dict(
            orientation="v", x=1.02, y=0.5,
            font=dict(size=11, family=_FONT, color=_TEXT),
        ),
        annotations = [dict(
            text      = f"<b>{total_label}</b><br><span style='font-size:10px'>total spent</span>",
            x=0.38, y=0.5, font_size=13, showarrow=False,
            font      = {"family": _FONT, "color": "#374151"},
        )],
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  6. INCOME VS EXPENSE GROUPED BARS  (replaces waterfall — simpler to read)
# ══════════════════════════════════════════════════════════════════════════════
def income_vs_expense_bars(
    monthly_df: "pd.DataFrame",
    currency:   str = "$",
) -> "go.Figure":
    """
    Side-by-side bars showing income and expenses per month.
    Far easier for non-finance users than a waterfall chart:
    "the green bar should be taller than the red bar every month."

    monthly_df: output of metrics.monthly_income_vs_expense()
    """
    if monthly_df.empty:
        fig = go.Figure()
        fig.update_layout(**_layout(height=320))
        return fig

    inc = monthly_df[monthly_df["Type"] == "Income"]
    exp = monthly_df[monthly_df["Type"] == "Expense"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name         = "Income",
        x            = inc["Month"],
        y            = inc["Amount"],
        marker_color = INCOME_COLOR,
        marker_line_width = 0,
        text         = [
            f"{currency}{v/1000:.0f}K" if v >= 1000 else f"{currency}{v:.0f}"
            for v in inc["Amount"]
        ],
        textposition = "outside",
        textfont     = {"size": 10, "family": _FONT},
    ))
    fig.add_trace(go.Bar(
        name         = "Spending",
        x            = exp["Month"],
        y            = exp["Amount"],
        marker_color = EXPENSE_COLOR,
        marker_line_width = 0,
        text         = [
            f"{currency}{v/1000:.0f}K" if v >= 1000 else f"{currency}{v:.0f}"
            for v in exp["Amount"]
        ],
        textposition = "outside",
        textfont     = {"size": 10, "family": _FONT},
    ))
    fig.update_layout(
        **_layout(height=265),
        barmode    = "group",
        showlegend = True,
        legend     = dict(
            orientation="h", x=0, y=1.12,
            font=dict(size=11, family=_FONT),
        ),
        xaxis = _xax(),
        yaxis = _yax(prefix=currency),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  7. SCORE BREAKDOWN  (horizontal bars — shows what each component earned)
# ══════════════════════════════════════════════════════════════════════════════
def score_breakdown_chart(components: list) -> "go.Figure":
    """
    Horizontal bar chart showing the score contribution of each component.
    Grey = maximum possible, coloured = actual earned.
    Plain-English labels so non-finance users can understand at a glance.
    """
    labels  = [c.label for c in reversed(components)]
    actuals = [c.score for c in reversed(components)]
    maxes   = [c.max_score for c in reversed(components)]
    gaps    = [m - a for m, a in zip(maxes, actuals)]
    pcts    = [a / m * 100 if m > 0 else 0 for a, m in zip(actuals, maxes)]

    fig = go.Figure()
    # Background (grey = max possible)
    fig.add_trace(go.Bar(
        name         = "Maximum",
        y            = labels,
        x            = gaps,
        orientation  = "h",
        base         = actuals,
        marker_color = "#EAECF0",
        marker_line_width = 0,
        showlegend   = False,
        hoverinfo    = "skip",
    ))
    # Foreground (coloured = actual)
    bar_colors = [
        "#12B76A" if p >= 80 else "#F79009" if p >= 50 else "#F04438"
        for p in pcts
    ]
    fig.add_trace(go.Bar(
        name         = "Your score",
        y            = labels,
        x            = actuals,
        orientation  = "h",
        marker_color = bar_colors,
        marker_line_width = 0,
        text         = [f"{a:.0f}/{m:.0f}" for a, m in zip(actuals, maxes)],
        textposition = "outside",
        textfont     = {"size": 10, "family": _FONT, "color": _TEXT},
    ))
    fig.update_layout(
        **_layout(height=265, l=130, r=50, t=8, b=8),
        barmode    = "stack",
        showlegend = False,
        xaxis      = dict(showgrid=False, zeroline=False, showticklabels=False,
                          range=[0, max(maxes) * 1.25]),
        yaxis      = _xax(showticklabels=True),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  8. BALANCE TREND  (line chart — most intuitive chart for non-finance users)
# ══════════════════════════════════════════════════════════════════════════════
def balance_trend(df: "pd.DataFrame", currency: str = "$") -> "go.Figure | None":
    """
    Line chart of reconstructed running balance over time.
    Uses the cumulative sum of Amount as a proxy if no Balance column exists.
    Returns None if insufficient data.
    """
    if len(df) < 3:
        return None

    # Use actual balance column if available, otherwise reconstruct
    if "Balance" in df.columns:
        try:
            bal = pd.to_numeric(df["Balance"], errors="coerce").dropna()
            dates = df.loc[bal.index, "Date"]
            if bal.notna().sum() >= 3:
                bal_series = bal.values
                date_series = dates.values
            else:
                raise ValueError("not enough balance data")
        except Exception:
            bal_series = df["Amount"].cumsum().values
            date_series = df["Date"].values
    else:
        bal_series = df["Amount"].cumsum().values
        date_series = df["Date"].values

    # Color dots by trend (is balance going up or down week-over-week?)
    line_color = INCOME_COLOR if float(bal_series[-1]) >= float(bal_series[0]) else EXPENSE_COLOR

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x            = date_series,
        y            = bal_series,
        mode         = "lines",
        line         = dict(color=line_color, width=2),
        fill         = "tozeroy",
        fillcolor    = f"rgba({int(line_color[1:3],16)},{int(line_color[3:5],16)},{int(line_color[5:7],16)},0.07)",
        hovertemplate= f"{currency}%{{y:,.0f}}<extra></extra>",
    ))
    fig.update_layout(
        **_layout(height=130, b=12, t=4),
        xaxis = _xax(),
        yaxis = _yax(prefix=currency),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  9. SPENDING HEATMAP  (day-of-week × top categories)
#  Replaces DOW bar chart — shows WHICH categories dominate on each day.
# ══════════════════════════════════════════════════════════════════════════════
def spending_heatmap(df: "pd.DataFrame", currency: str = "$") -> "go.Figure":
    """
    Heatmap: rows = days of week, columns = top spending categories.
    Cell value = total spent on that day in that category.
    Gives users a quick pattern: "I spend on Groceries Mon/Wed/Sat".
    """
    from config import DAY_ORDER

    exp_df = df[df["Type"] == "Expense"].copy()
    if exp_df.empty:
        return go.Figure()

    # Top 7 categories by total spend
    top_cats = (
        exp_df.groupby("Category")["Amount"]
        .apply(lambda x: x.abs().sum())
        .nlargest(5)
        .index.tolist()
    )
    exp_df = exp_df[exp_df["Category"].isin(top_cats)]

    pivot = (
        exp_df.groupby(["DOW", "Category"])["Amount"]
        .apply(lambda x: x.abs().sum())
        .unstack(fill_value=0)
        .reindex(index=DAY_ORDER, fill_value=0)
    )
    # Only keep columns that are in top_cats
    pivot = pivot[[c for c in top_cats if c in pivot.columns]]

    # Custom hover text
    hover = [
        [f"{currency}{pivot.iloc[r, c]:,.0f}" for c in range(len(pivot.columns))]
        for r in range(len(pivot))
    ]

    fig = go.Figure(go.Heatmap(
        z            = pivot.values,
        x            = pivot.columns.tolist(),
        y            = pivot.index.tolist(),
        text         = hover,
        texttemplate = "%{text}",
        textfont     = {"size": 9, "family": _FONT},
        colorscale   = [
            [0.0, "#F4EBFF"],
            [0.4, "#9E77ED"],
            [1.0, "#3B0764"],
        ],
        showscale    = False,
        hovertemplate = "<b>%{y}</b> / <b>%{x}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        **_layout(height=185, l=52, r=8, t=4, b=36),
        xaxis = dict(side="bottom", tickfont={"size": 9, "family": _FONT}, tickangle=-15),
        yaxis = dict(tickfont={"size": 10, "family": _FONT}, autorange="reversed"),
    )
    return fig
