"""
config.py
All application-wide constants in one place.
No logic. No imports. Just data.
"""

# ── Categories ────────────────────────────────────────────────────────────────
INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Business Income",
    "Investment Return",
    "Government Payment",
    "Refund",
    "Other Income",
]

EXPENSE_CATEGORIES = [
    "Groceries",
    "Eating Out",
    "Coffee & Cafes",
    "Alcohol & Bars",
    "Rent",
    "Mortgage",
    "Utilities",
    "Phone",
    "Internet",
    "Insurance",
    "Transport",
    "Fuel",
    "Car Expenses",
    "Parking & Tolls",
    "Health & Medical",
    "Pharmacy",
    "Gym & Fitness",
    "Shopping",
    "Clothing",
    "Electronics",
    "Entertainment",
    "Streaming",
    "Subscriptions",
    "Travel & Accommodation",
    "Flights",
    "Education",
    "Childcare",
    "Charity & Donations",
    "ATM & Cash",
    "Bank Fees",
    "Taxes",
    "Transfer",
    "Credit Card Payment",
    "Other Expense",
]

ALL_CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES

# Categories considered non-discretionary (can't easily cut)
FIXED_CATEGORIES: set[str] = {
    "Rent", "Mortgage", "Childcare", "Insurance",
    "Utilities", "Phone", "Internet", "Car Expenses",
}

# Categories to surface separately as recurring bills
SUBSCRIPTION_CATEGORIES: set[str] = {"Subscriptions", "Streaming"}

# ── Budget guide (% of gross income, international standard) ──────────────────
BUDGET_GUIDE: dict[str, int] = {
    "Rent":           30,
    "Groceries":      12,
    "Eating Out":      5,
    "Transport":       5,
    "Subscriptions":   3,
    "Shopping":        5,
    "Health & Medical":5,
    "Utilities":       6,
}

# ── Health score thresholds ───────────────────────────────────────────────────
SCORE_EXCELLENT  = 80
SCORE_HEALTHY    = 65
SCORE_ATTENTION  = 45

# ── Chart palette (consistent across all charts) ──────────────────────────────
# ── Chart colour tokens — single source of truth ─────────────────────────────
# These must match the semantic colours in ui.py COLOR exactly.
# Charts use config constants; cards use ui.COLOR — both reference the same values.
INCOME_COLOR  = "#16A34A"   # green  — income, healthy, on track
EXPENSE_COLOR = "#EF4444"   # red    — expenses, concern
ACCENT_COLOR  = "#2563EB"   # blue   — net cashflow, primary highlight
NEUTRAL_COLOR = "#D1D5DB"   # grey   — inactive bars, background elements
WARNING_COLOR = "#D97706"   # amber  — near limit, caution

# Treemap: single-hue blue scale (lightest → darkest)
# Matches ACCENT_COLOR family — one cohesive system across all charts
TREEMAP_SCALE = [
    "#EFF6FF", "#BFDBFE", "#93C5FD",
    "#60A5FA", "#2563EB", "#1D4ED8",
]

# Multi-series palette (for categoricals — kept minimal)
CHART_COLORS = [
    "#2563EB", "#16A34A", "#EF4444", "#D97706",
    "#7C3AED", "#0891B2", "#DB2777", "#65A30D",
]

# ── Encoding candidates (ordered by global prevalence) ───────────────────────
CSV_ENCODINGS = [
    "utf-8-sig", "utf-8", "latin-1", "cp1252",
    "shift_jis", "euc-kr", "gb2312", "cp1256", "cp1251",
]

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ── API ───────────────────────────────────────────────────────────────────────
ANTHROPIC_API_URL     = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
ANTHROPIC_MODEL       = "claude-sonnet-4-20250514"
AI_BATCH_SIZE         = 80        # transactions per categorisation call
AI_TIMEOUT_SECS       = 25
