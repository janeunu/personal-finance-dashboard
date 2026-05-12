"""
categoriser.py  —  Smart transaction categorisation
Phase 1 upgrade: regex rules + confidence scoring + Needs Review flag.

Two strategies, clearly separated:

  REGEX RULES   — fast, offline, deterministic
                  Covers 90% of recognisable transactions
                  Uses DescriptionClean (noise-stripped) for matching
                  Returns confidence: HIGH or MEDIUM

  AI BATCH      — Claude API, handles anything the rules miss
                  Sends descriptions in batches for efficiency
                  Returns confidence: MEDIUM (AI is right most of the time)

  FALLBACK      — when both fail, assigns "Other Income/Expense"
                  Marks with NEEDS_REVIEW = True
                  Returns confidence: LOW

Output columns added to DataFrame:
  Category       — the assigned category name
  Type           — "Income" | "Expense" | "Transfer"
  Confidence     — "High" | "Medium" | "Low"
  NeedsReview    — True if confidence is Low or category is genuinely ambiguous
"""

from __future__ import annotations

import json
import re
from typing import Optional

import pandas as pd
import requests

from config import (
    ALL_CATEGORIES,
    ANTHROPIC_API_URL,
    ANTHROPIC_API_VERSION,
    ANTHROPIC_MODEL,
    AI_BATCH_SIZE,
    AI_TIMEOUT_SECS,
)

# ── Confidence levels ─────────────────────────────────────────────────────────
HIGH   = "High"
MEDIUM = "Medium"
LOW    = "Low"

CategoryResult = tuple[str, str, str, bool]  # (category, type, confidence, needs_review)


# ══════════════════════════════════════════════════════════════════════════════
#  REGEX RULE ENGINE
#  Each rule: (pattern, category, type, confidence)
#  Rules are tried in order — first match wins.
#  Uses the DescriptionClean column (noise already stripped by parser.py).
# ══════════════════════════════════════════════════════════════════════════════
_RULES: list[tuple[str, str, str, str]] = [

    # ── Income patterns ───────────────────────────────────────────────────────
    (r"\b(salary|payroll|pay\s*run|wages|wage|fortnightly\s*pay)\b",
        "Salary",             "Income", HIGH),
    (r"\b(freelance|invoice|consulting\s*fee|contractor|self\s*employed)\b",
        "Freelance",          "Income", HIGH),
    (r"\b(centrelink|welfare|jobseeker|youth\s*allowance|newstart|austudy"
     r"|family\s*payment|parenting\s*payment|disability\s*support)\b",
        "Government Payment", "Income", HIGH),
    (r"\b(tax\s*refund|ato\s*refund|hmrc\s*refund|irs\s*refund|gst\s*refund)\b",
        "Refund",             "Income", HIGH),
    (r"\b(refund|reversal|chargeback|cashback)\b",
        "Refund",             "Income", MEDIUM),
    (r"\b(dividend|interest\s*earned|term\s*deposit|investment\s*return)\b",
        "Investment Return",  "Income", HIGH),
    (r"\b(rent\s*received|rental\s*income|airbnb\s*payout)\b",
        "Other Income",       "Income", HIGH),

    # ── Transfers (exclude from income/expense) ───────────────────────────────
    (r"\b(transfer|tfr|trf|trsf)\b.{0,20}\b(savings|offset|loan|mortgage)\b",
        "Transfer",           "Transfer", HIGH),
    (r"\b(savings|offset|loan|mortgage)\b.{0,20}\b(transfer|tfr|trf)\b",
        "Transfer",           "Transfer", HIGH),
    (r"\b(credit\s*card\s*payment|card\s*payment|pay\s*credit\s*card)\b",
        "Credit Card Payment","Transfer", HIGH),
    (r"^(transfer|tfr|trf|trsf)\b",
        "Transfer",           "Transfer", MEDIUM),

    # ── Fixed bills ───────────────────────────────────────────────────────────
    (r"\b(rent|lease\s*payment|landlord)\b",
        "Rent",               "Expense", HIGH),
    (r"\b(mortgage|home\s*loan|repayment)\b",
        "Mortgage",           "Expense", HIGH),
    (r"\b(electricity|gas\s*bill|water\s*bill|energy|agl|origin\s*energy"
     r"|powershop|simply\s*energy|energyaustralia|jemena)\b",
        "Utilities",          "Expense", HIGH),
    (r"\b(phone|mobile|telstra|optus|vodafone|tpg|boost\s*mobile"
     r"|belong|amaysim|aussie\s*broadband)\b",
        "Phone",              "Expense", HIGH),
    (r"\b(internet|broadband|nbn|iinet|internode|aussie\s*broadband"
     r"|superloop|exetel)\b",
        "Internet",           "Expense", HIGH),
    (r"\b(insurance|nrma|racq|racv|bupa|medibank|hcf|allianz"
     r"|suncorp|gio|aami|youi|real\s*insurance)\b",
        "Insurance",          "Expense", HIGH),
    (r"\b(childcare|child\s*care|daycare|day\s*care|kindy|kindergarten"
     r"|creche|after\s*school\s*care)\b",
        "Childcare",          "Expense", HIGH),

    # ── Groceries ─────────────────────────────────────────────────────────────
    (r"\b(woolworths|coles|aldi|iga|foodland|spar|fresh\s*food"
     r"|countdown|pak\s*n\s*save|harris\s*farm|costco)\b",
        "Groceries",          "Expense", HIGH),
    (r"\b(supermarket|grocery|groceries)\b",
        "Groceries",          "Expense", HIGH),

    # ── Eating out ────────────────────────────────────────────────────────────
    (r"\b(mcdonald|macca|kfc|hungry\s*jacks|burger\s*king|subway|domino"
     r"|pizza\s*hut|red\s*rooster|grill\s*d|nandos|oporto|guzman)\b",
        "Eating Out",         "Expense", HIGH),
    (r"\b(restaurant|cafe|coffee|bakery|takeaway|takeout|food\s*court"
     r"|bistro|brasserie|sushi|ramen|thai|indian|chinese|vietnamese)\b",
        "Eating Out",         "Expense", MEDIUM),
    (r"\b(uber\s*eats|doordash|menulog|deliveroo|grubhub|just\s*eat)\b",
        "Eating Out",         "Expense", HIGH),

    # ── Coffee ────────────────────────────────────────────────────────────────
    (r"\b(starbucks|gloria\s*jeans|muffin\s*break|hudsons|zarraffa"
     r"|coffee\s*club|single\s*origin|specialty\s*coffee)\b",
        "Coffee & Cafes",     "Expense", HIGH),

    # ── Transport ─────────────────────────────────────────────────────────────
    (r"\b(uber(?!\s*eats)|lyft|ola|didi|taxi|cab|rideshare)\b",
        "Transport",          "Expense", HIGH),
    (r"\b(opal|myki|go\s*card|smartrider|metrocard|translink"
     r"|public\s*transport|bus|train|ferry|tram|metro)\b",
        "Transport",          "Expense", HIGH),
    (r"\b(petrol|fuel|bp|shell|caltex|ampol|mobil|7\s*eleven"
     r"|liberty|puma\s*energy)\b",
        "Fuel",               "Expense", HIGH),
    (r"\b(parking|car\s*park|secure\s*park|wilson\s*parking|toll"
     r"|linkt|e-toll|citylink|eastlink|roam\s*express)\b",
        "Parking & Tolls",    "Expense", HIGH),
    (r"\b(car\s*service|mechanic|tyres|rego|registration|roadside"
     r"|nrma\s*road|racq\s*road|ctp|greenslip)\b",
        "Car Expenses",       "Expense", HIGH),

    # ── Health & Medical ──────────────────────────────────────────────────────
    (r"\b(doctor|gp|medical\s*centre|hospital|clinic|specialist"
     r"|pathology|radiology|physio|osteo|chiro|dentist|dental"
     r"|optometrist|ophthalmologist|psychologist|therapist)\b",
        "Health & Medical",   "Expense", HIGH),
    (r"\b(pharmacy|chemist|priceline|terry\s*white|amcal|discount\s*drug)\b",
        "Pharmacy",           "Expense", HIGH),
    (r"\b(gym|fitness|crossfit|yoga|pilates|swimming|sport"
     r"|anytime\s*fitness|f45|goodlife|snap\s*fitness)\b",
        "Gym & Fitness",      "Expense", HIGH),

    # ── Streaming & Subscriptions ─────────────────────────────────────────────
    (r"\b(netflix|stan|disney\s*\+?|binge|foxtel|kayo|paramount"
     r"|apple\s*tv|amazon\s*prime|prime\s*video|hbo|hulu)\b",
        "Streaming",          "Expense", HIGH),
    (r"\b(spotify|apple\s*music|youtube\s*premium|tidal|deezer|audible)\b",
        "Subscriptions",      "Expense", HIGH),
    (r"\b(adobe|microsoft\s*365|office\s*365|dropbox|google\s*storage"
     r"|icloud|notion|canva|zoom|slack|github)\b",
        "Subscriptions",      "Expense", HIGH),
    (r"\b(subscription|monthly\s*fee|annual\s*fee|membership)\b",
        "Subscriptions",      "Expense", MEDIUM),

    # ── Shopping ─────────────────────────────────────────────────────────────
    (r"\b(amazon|ebay|etsy|catch|kogan|temu|shein|aliexpress)\b",
        "Shopping",           "Expense", HIGH),
    (r"\b(kmart|target|big\s*w|myer|david\s*jones|harvey\s*norman"
     r"|jb\s*hi[\s-]?fi|the\s*good\s*guys|officeworks|bunnings)\b",
        "Shopping",           "Expense", HIGH),
    (r"\b(clothing|fashion|dress|shoes|apparel|uniqlo|zara|h&m"
     r"|cotton\s*on|country\s*road|witchery|jeanswest)\b",
        "Clothing",           "Expense", HIGH),

    # ── Travel ────────────────────────────────────────────────────────────────
    (r"\b(qantas|jetstar|virgin\s*australia|rex\s*regional|tigerair"
     r"|emirates|singapore\s*air|cathay|air\s*new\s*zealand)\b",
        "Flights",            "Expense", HIGH),
    (r"\b(hotel|motel|hostel|airbnb|booking\.com|expedia|wotif"
     r"|agoda|trivago|hilton|marriott|ibis)\b",
        "Travel & Accommodation", "Expense", HIGH),

    # ── Education ────────────────────────────────────────────────────────────
    (r"\b(university|uni\b|tafe|school\s*fee|school\s*fees|tuition"
     r"|udemy|coursera|skillshare|linkedin\s*learning)\b",
        "Education",          "Expense", HIGH),
    (r"\b(monash|rmit|unsw|unimelb|usyd|uq|anu|curtin|deakin)\b",
        "Education",          "Expense", HIGH),

    # ── Charity ──────────────────────────────────────────────────────────────
    (r"\b(donation|charity|red\s*cross|salvation\s*army|oxfam"
     r"|world\s*vision|cancer\s*council|heart\s*foundation)\b",
        "Charity & Donations","Expense", HIGH),

    # ── Banking & Fees ────────────────────────────────────────────────────────
    (r"\b(bank\s*fee|account\s*fee|monthly\s*fee|service\s*fee"
     r"|overdraft|dishonour|dishonored|nsf\s*fee|late\s*fee)\b",
        "Bank Fees",          "Expense", HIGH),
    (r"\b(atm|cash\s*withdrawal|cash\s*advance)\b",
        "ATM & Cash",         "Expense", HIGH),
    (r"\b(tax|ato\s*payment|bas\s*payment|payg|fines|infringement)\b",
        "Taxes",              "Expense", HIGH),

    # ── Electronics ──────────────────────────────────────────────────────────
    (r"\b(apple\s*store|apple\.com|samsung|microsoft\s*store"
     r"|lenovo|dell|hp\b|asus|acer|mwave|umart|pccasegear)\b",
        "Electronics",        "Expense", HIGH),

    # ── Entertainment ────────────────────────────────────────────────────────
    (r"\b(cinema|hoyts|event\s*cinema|village\s*cinema|reading\s*cinema"
     r"|concert|theatre|theater|ticket|eventbrite|ticketek|ticketmaster)\b",
        "Entertainment",      "Expense", HIGH),
    (r"\b(bar|pub|hotel\b|nightclub|club\b|bottleshop|bottle\s*shop"
     r"|dans\s*murphy|bws|liquorland|first\s*choice)\b",
        "Alcohol & Bars",     "Expense", HIGH),
]

# Compile all patterns once at import time
_COMPILED_RULES: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(p, re.IGNORECASE), cat, typ, conf)
    for p, cat, typ, conf in _RULES
]


def _apply_rules(desc_clean: str, amount: float) -> CategoryResult | None:
    """
    Try all regex rules against the cleaned description.
    Returns the first match, or None if no rule matches.
    """
    for pattern, category, txn_type, confidence in _COMPILED_RULES:
        if pattern.search(desc_clean):
            return category, txn_type, confidence, False
    return None


def _fallback(amount: float) -> CategoryResult:
    """
    Last resort: assign Other Income/Expense with Low confidence.
    Mark as NeedsReview so the user knows to check it.
    """
    if amount > 0:
        return "Other Income",  "Income",  LOW, True
    return     "Other Expense", "Expense", LOW, True


# ══════════════════════════════════════════════════════════════════════════════
#  AI BATCH CATEGORISATION
# ══════════════════════════════════════════════════════════════════════════════
_AI_SYSTEM = (
    "You are a personal finance transaction categoriser.\n"
    "Input: JSON array of transactions with id, desc, amount.\n"
    "Output: JSON array with id, category, type, confidence.\n\n"
    "Rules:\n"
    "  • 'type' must be exactly 'Income', 'Expense', or 'Transfer'.\n"
    "  • 'confidence' must be 'High' or 'Medium'.\n"
    "  • Use 'Medium' when the description is ambiguous.\n"
    f" • 'category' must be one of: {json.dumps(ALL_CATEGORIES)}\n"
    "  • Negative amount = expense; positive = income (unless clearly a transfer).\n"
    "  • Return ONLY the JSON array. No markdown, no explanation."
)


def _call_ai_batch(records: list[dict], api_key: str) -> list[dict]:
    try:
        r = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key":         api_key,
                "content-type":      "application/json",
                "anthropic-version": ANTHROPIC_API_VERSION,
            },
            json={
                "model":      ANTHROPIC_MODEL,
                "max_tokens": 2048,
                "system":     _AI_SYSTEM,
                "messages":   [{"role": "user",
                                "content": json.dumps(records, ensure_ascii=False)}],
            },
            timeout=AI_TIMEOUT_SECS,
        )
        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            text = __import__("re").sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
            return json.loads(text)
    except Exception:
        pass
    return []


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def add_categories(
    df:      pd.DataFrame,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Add Category, Type, Confidence, and NeedsReview columns to the DataFrame.

    Strategy:
      1. Apply regex rules to DescriptionClean → covers most recognisable transactions
      2. Send unmatched transactions to AI (if api_key provided)
      3. Apply fallback to anything still unmatched → NeedsReview = True

    The caller can filter df[df["NeedsReview"]] to show a review queue.
    """
    df = df.copy()
    desc_col = "DescriptionClean" if "DescriptionClean" in df.columns else "Description"

    n = len(df)
    categories  = [None] * n
    types       = [None] * n
    confidences = [None] * n
    needs_review= [False] * n

    # ── Pass 1: Regex rules ───────────────────────────────────────────────────
    unmatched_idx = []
    for i, (desc, amount) in enumerate(zip(df[desc_col], df["Amount"])):
        result = _apply_rules(str(desc), float(amount))
        if result:
            categories[i], types[i], confidences[i], needs_review[i] = result
        else:
            unmatched_idx.append(i)

    # ── Pass 2: AI batch for unmatched ────────────────────────────────────────
    still_unmatched = []
    if api_key and unmatched_idx:
        records = [
            {
                "id":     i,
                "desc":   str(df.iloc[i][desc_col]),
                "amount": float(df.iloc[i]["Amount"]),
            }
            for i in unmatched_idx
        ]
        # Process in batches
        ai_results: dict[int, dict] = {}
        for start in range(0, len(records), AI_BATCH_SIZE):
            batch  = records[start : start + AI_BATCH_SIZE]
            output = _call_ai_batch(batch, api_key)
            for item in output:
                idx = item.get("id", -1)
                if 0 <= idx < n:
                    ai_results[idx] = item

        for i in unmatched_idx:
            item = ai_results.get(i)
            if item:
                categories[i]  = item.get("category", "Other Expense")
                types[i]       = item.get("type",     "Expense")
                raw_conf       = item.get("confidence", MEDIUM)
                confidences[i] = raw_conf if raw_conf in (HIGH, MEDIUM) else MEDIUM
                needs_review[i]= confidences[i] == MEDIUM
            else:
                still_unmatched.append(i)
    else:
        still_unmatched = unmatched_idx

    # ── Pass 3: Fallback ──────────────────────────────────────────────────────
    for i in still_unmatched:
        categories[i], types[i], confidences[i], needs_review[i] = _fallback(
            float(df.iloc[i]["Amount"])
        )

    df["Category"]   = categories
    df["Type"]        = types
    df["Confidence"]  = confidences
    df["NeedsReview"] = needs_review

    return df
