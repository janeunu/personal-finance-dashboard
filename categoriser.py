"""
categoriser.py
Adds Category and Type columns to a parsed DataFrame.

Two strategies, cleanly separated:
  1. AI batch   — sends descriptions to Claude in batches → works in any language
  2. Keyword    — matches English keyword rules from category_rules.csv

Both return the same shape: list of (category: str, type: str) tuples.
The caller (app.py) decides which strategy to use.
"""

from __future__ import annotations

import json
import os
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

# ── Types ─────────────────────────────────────────────────────────────────────
CategoryResult = tuple[str, str]   # (category, type)


# ══════════════════════════════════════════════════════════════════════════════
#  AI STRATEGY
# ══════════════════════════════════════════════════════════════════════════════
_AI_SYSTEM = (
    "You are a personal finance transaction categoriser.\n"
    "Input: JSON array [{\"id\":N, \"desc\":\"...\", \"amount\":0.0}, ...]\n"
    "Output: JSON array [{\"id\":N, \"category\":\"...\", \"type\":\"Income|Expense|Transfer\"}, ...]\n\n"
    "Rules:\n"
    "  • Descriptions may be in ANY language — translate mentally before categorising.\n"
    "  • Negative amount = expense; positive = income (unless clearly a transfer).\n"
    "  • 'type' must be exactly 'Income', 'Expense', or 'Transfer'.\n"
    f" • 'category' must be one of: {json.dumps(ALL_CATEGORIES)}\n"
    "  • Return ONLY the JSON array. No markdown, no preamble."
)


def _call_ai_batch(
    records: list[dict],
    api_key: str,
) -> list[dict]:
    """
    Send one batch to the API.
    Returns list of {id, category, type} or empty list on failure.
    """
    try:
        response = requests.post(
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
        if response.status_code == 200:
            text = response.json()["content"][0]["text"].strip()
            text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
            return json.loads(text)
    except Exception:
        pass
    return []


def categorise_ai(
    descriptions: list[str],
    amounts:      list[float],
    api_key:      str,
) -> list[CategoryResult]:
    """
    Categorise all transactions using the Claude API in batches.
    Falls back to a safe default for any record the API fails on.
    """
    n       = len(descriptions)
    results: list[Optional[CategoryResult]] = [None] * n

    for start in range(0, n, AI_BATCH_SIZE):
        end     = min(start + AI_BATCH_SIZE, n)
        records = [
            {"id": i, "desc": descriptions[i], "amount": float(amounts[i])}
            for i in range(start, end)
        ]
        batch = _call_ai_batch(records, api_key)
        for item in batch:
            idx = item.get("id", -1)
            if 0 <= idx < n:
                results[idx] = (
                    item.get("category", "Other Expense"),
                    item.get("type",     "Expense"),
                )

    # Fill any gaps left by API failures
    return [
        r if r is not None
        else ("Other Income", "Income") if amounts[i] > 0
        else ("Other Expense", "Expense")
        for i, r in enumerate(results)
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  KEYWORD STRATEGY
# ══════════════════════════════════════════════════════════════════════════════
def _load_keyword_rules(path: Optional[str] = None) -> pd.DataFrame:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "category_rules.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["keyword", "category", "type"])
    rules = pd.read_csv(path)
    rules["keyword"] = rules["keyword"].astype(str).str.lower().str.strip()
    return rules


def _categorise_one_keyword(
    desc:   str,
    amount: float,
    rules:  pd.DataFrame,
) -> CategoryResult:
    d = str(desc).lower()
    for _, row in rules.iterrows():
        if row["keyword"] in d:
            return row["category"], row["type"]
    return ("Other Income", "Income") if amount > 0 else ("Other Expense", "Expense")


def categorise_keywords(
    descriptions: list[str],
    amounts:      list[float],
) -> list[CategoryResult]:
    """Categorise using English keyword rules. Fast, no API call required."""
    rules = _load_keyword_rules()
    return [
        _categorise_one_keyword(desc, amt, rules)
        for desc, amt in zip(descriptions, amounts)
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def add_categories(
    df:      pd.DataFrame,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Add 'Category' and 'Type' columns to the DataFrame in-place.

    Uses AI categorisation if api_key is provided, keyword rules otherwise.
    Returns the modified DataFrame.
    """
    descs   = df["Description"].astype(str).tolist()
    amounts = df["Amount"].tolist()

    if api_key:
        results = categorise_ai(descs, amounts, api_key)
    else:
        results = categorise_keywords(descs, amounts)

    df = df.copy()
    df["Category"] = [r[0] for r in results]
    df["Type"]     = [r[1] for r in results]

    return df
