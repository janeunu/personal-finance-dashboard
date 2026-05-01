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
CHART_COLORS = [
    "#5b7cf0", "#f0a05b", "#2db88a", "#f06b5b",
    "#9b7cf0", "#5bbef0", "#f0c85b", "#d45b8a",
    "#7cd45b", "#5b9af0", "#f07b5b", "#5bf0d4",
]

TREEMAP_SCALE = [
    "#fef0eb", "#f5c4ab", "#ec996b",
    "#e06d35", "#c8501a", "#8c300a",
]

INCOME_COLOR  = "#2db88a"
EXPENSE_COLOR = "#f06b5b"
ACCENT_COLOR  = "#e06d35"
NEUTRAL_COLOR = "#d4c4b4"

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
