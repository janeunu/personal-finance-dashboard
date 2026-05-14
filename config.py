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
# ══════════════════════════════════════════════════════════════════════════════
#  COLOUR TOKENS  —  Softer, more approachable palette
#  Charcoal · Purple · Green · Red · Amber
# ══════════════════════════════════════════════════════════════════════════════
NAVY_COLOR    = "#1A2332"   # softer charcoal — header bg, primary text
ACCENT_COLOR  = "#6941C6"   # purple — highlights, section dots (distinctive, calm)
INCOME_COLOR  = "#12B76A"   # softer emerald — income, positive, on track
EXPENSE_COLOR = "#F04438"   # soft rose-red — expenses, over budget
WARNING_COLOR = "#F79009"   # warm amber — near limit, caution

# Supporting neutrals
NEUTRAL_COLOR = "#D0D5DD"   # neutral grey — inactive bars
PAGE_BG       = "#F7F8FA"   # near-white with a hint of cool — easy on the eyes
CARD_BG       = "#FFFFFF"
BORDER_COLOR  = "#EAECF0"   # very subtle card borders

# Donut/categorical chart palette (max 7 categories + Other)
CHART_COLORS = [
    "#6941C6", "#12B76A", "#F04438", "#F79009",
    "#0891B2", "#DB2777", "#16A34A", "#D0D5DD",
]

# Treemap scale (not used in new chart set — kept for backward compat)
TREEMAP_SCALE = [
    "#F4EBFF", "#D9BBFF", "#B692F6",
    "#9E77ED", "#7F56D9", "#6941C6",
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

# ── Category colour badges ────────────────────────────────────────────────────
CATEGORY_BADGE_COLORS: dict = {
    "Salary":               ("#DCFCE7", "#15803D"),
    "Freelance":            ("#DCFCE7", "#15803D"),
    "Business Income":      ("#DCFCE7", "#15803D"),
    "Investment Return":    ("#DCFCE7", "#15803D"),
    "Government Payment":   ("#DCFCE7", "#15803D"),
    "Refund":               ("#DCFCE7", "#15803D"),
    "Other Income":         ("#DCFCE7", "#15803D"),
    "Rent":                 ("#EDE9FE", "#5B21B6"),
    "Mortgage":             ("#EDE9FE", "#5B21B6"),
    "Utilities":            ("#F3E8FF", "#7E22CE"),
    "Phone":                ("#E0E7FF", "#3730A3"),
    "Internet":             ("#E0E7FF", "#3730A3"),
    "Insurance":            ("#E0E7FF", "#3730A3"),
    "Childcare":            ("#FEF9C3", "#854D0E"),
    "Groceries":            ("#D1FAE5", "#065F46"),
    "Eating Out":           ("#FEF3C7", "#92400E"),
    "Coffee & Cafes":       ("#FEF3C7", "#92400E"),
    "Alcohol & Bars":       ("#FEF3C7", "#92400E"),
    "Transport":            ("#DBEAFE", "#1E40AF"),
    "Fuel":                 ("#DBEAFE", "#1E40AF"),
    "Car Expenses":         ("#DBEAFE", "#1E40AF"),
    "Parking & Tolls":      ("#DBEAFE", "#1E40AF"),
    "Health & Medical":     ("#FFE4E6", "#9F1239"),
    "Pharmacy":             ("#FFE4E6", "#9F1239"),
    "Gym & Fitness":        ("#FFE4E6", "#9F1239"),
    "Shopping":             ("#FFEDD5", "#9A3412"),
    "Clothing":             ("#FFEDD5", "#9A3412"),
    "Electronics":          ("#FFEDD5", "#9A3412"),
    "Entertainment":        ("#DBEAFE", "#1D4ED8"),
    "Streaming":            ("#FEF9C3", "#713F12"),
    "Subscriptions":        ("#FEF9C3", "#713F12"),
    "Travel & Accommodation": ("#F0FDF4", "#166534"),
    "Flights":              ("#F0FDF4", "#166534"),
    "Education":            ("#E0F2FE", "#0C4A6E"),
    "Charity & Donations":  ("#FCE7F3", "#831843"),
    "ATM & Cash":           ("#F3F4F6", "#374151"),
    "Bank Fees":            ("#F3F4F6", "#374151"),
    "Taxes":                ("#F3F4F6", "#374151"),
    "Transfer":             ("#F3F4F6", "#6B7280"),
    "Credit Card Payment":  ("#F3F4F6", "#6B7280"),
    "Other Expense":        ("#F3F4F6", "#6B7280"),
}

def category_badge_colors(category: str) -> tuple:
    return CATEGORY_BADGE_COLORS.get(category, ("#F3F4F6", "#374151"))

