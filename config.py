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
# ══════════════════════════════════════════════════════════════════════════════
#  COLOUR TOKENS  —  5 semantic colours, used consistently in ui.py + charts.py
#  Navy · Blue · Emerald · Rose · Amber
# ══════════════════════════════════════════════════════════════════════════════
NAVY_COLOR    = "#0F172A"   # slate-900  — sidebar, verdict bg, primary text
ACCENT_COLOR  = "#2563EB"   # blue-600   — net cashflow, highlights, section dots
INCOME_COLOR  = "#059669"   # emerald-600 — income, positive, on track
EXPENSE_COLOR = "#E11D48"   # rose-600   — expenses, over budget
WARNING_COLOR = "#D97706"   # amber-600  — near limit, caution

# Supporting neutrals (not semantic — structural only)
NEUTRAL_COLOR = "#CBD5E1"   # slate-300  — inactive chart bars
PAGE_BG       = "#F1F5F9"   # slate-100  — page background
CARD_BG       = "#FFFFFF"
BORDER_COLOR  = "#E2E8F0"   # slate-200

# Treemap: navy-to-blue single-hue scale
TREEMAP_SCALE = [
    "#EFF6FF", "#BFDBFE", "#93C5FD",
    "#60A5FA", "#2563EB", "#1E40AF",
]

# Multi-series chart palette (rarely used — only for grouped bars)
CHART_COLORS = [
    "#2563EB", "#059669", "#E11D48",
    "#D97706", "#7C3AED", "#0891B2",
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
