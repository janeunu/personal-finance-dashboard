"""
categoriser.py — Universal bank statement parser + AI categoriser
Compatible with pandas 3.x, Python 3.10+
"""

from __future__ import annotations

import io
import json
import os
import re
import warnings
from typing import Optional

import chardet
import pandas as pd
import requests

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Standard categories ───────────────────────────────────────────────────────
STANDARD_CATEGORIES = [
    "Salary", "Freelance", "Business Income", "Investment Return",
    "Government Payment", "Refund", "Other Income",
    "Groceries", "Eating Out", "Coffee & Cafes", "Alcohol & Bars",
    "Rent", "Mortgage", "Utilities", "Phone", "Internet", "Insurance",
    "Transport", "Fuel", "Car Expenses", "Parking & Tolls",
    "Health & Medical", "Pharmacy", "Gym & Fitness",
    "Shopping", "Clothing", "Electronics",
    "Entertainment", "Streaming", "Subscriptions",
    "Travel & Accommodation", "Flights",
    "Education", "Childcare",
    "Charity & Donations", "ATM & Cash",
    "Bank Fees", "Taxes",
    "Transfer", "Credit Card Payment",
    "Other Expense",
]

# ── Encoding candidates ───────────────────────────────────────────────────────
_ENCODINGS = [
    "utf-8-sig", "utf-8", "latin-1", "cp1252",
    "shift_jis", "euc-kr", "gb2312", "cp1256", "cp1251",
]

# ── API ───────────────────────────────────────────────────────────────────────
_API_URL = "https://api.anthropic.com/v1/messages"
_HEADERS = {"content-type": "application/json", "anthropic-version": "2023-06-01"}
_MODEL   = "claude-sonnet-4-20250514"
_BATCH   = 80


# ══════════════════════════════════════════════════════════════════════════════
#  1. ENCODING-SAFE CSV READER
# ══════════════════════════════════════════════════════════════════════════════
def read_csv_any_encoding(raw_bytes: bytes) -> pd.DataFrame:
    """Try chardet auto-detect first, then fall through a list of common encodings."""
    detected = chardet.detect(raw_bytes[:8192]).get("encoding") or ""
    order = ([detected] if detected else []) + _ENCODINGS

    for enc in dict.fromkeys(order):
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, low_memory=False)
            if not df.empty:
                return df
        except Exception:
            continue

    raise ValueError(
        "Could not decode your CSV. Try re-saving the file as UTF-8 from Excel or your bank app."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  2. DATE PARSER — pandas 3.x compatible
# ══════════════════════════════════════════════════════════════════════════════
def _parse_dates(series: pd.Series) -> pd.Series:
    """
    Robust date parser for pandas 2.0+ (infer_datetime_format removed).
    Tries format='mixed' first (handles most real-world bank exports),
    then falls back to common explicit formats.
    """
    s = series.astype(str).str.strip()

    # 1) Let pandas infer with mixed format (pandas ≥ 2.0)
    try:
        result = pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")
        if result.notna().mean() > 0.8:
            return result
    except TypeError:
        pass

    # 2) Try without format argument (pandas 1.x fallback)
    try:
        result = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if result.notna().mean() > 0.8:
            return result
    except Exception:
        pass

    # 3) Try explicit common formats in order
    formats = [
        "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
        "%d.%m.%Y", "%Y.%m.%d", "%d %b %Y", "%d %B %Y",
        "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y",
        "%d/%m/%y", "%m/%d/%y", "%y-%m-%d",
    ]
    best, best_count = s.copy().apply(lambda _: pd.NaT), 0

    for fmt in formats:
        try:
            parsed = pd.to_datetime(s, errors="coerce", format=fmt)
            count  = parsed.notna().sum()
            if count > best_count:
                best, best_count = parsed, count
        except Exception:
            continue

    return best


# ══════════════════════════════════════════════════════════════════════════════
#  3. AMOUNT NORMALISER
# ══════════════════════════════════════════════════════════════════════════════
def _normalise_amount(series: pd.Series) -> pd.Series:
    """
    Converts any regional number format to float.
      US/AU   1,234.56  →  1234.56
      EU      1.234,56  →  1234.56
      Parens  (150.00)  → -150.0
      CR/DR   150.00DR  → -150.0
      Symbol  $1,234.56 →  1234.56
    """
    s = series.astype(str).str.strip()

    # Parenthetical negatives
    s = s.str.replace(r"^\((.+)\)$", r"-\1", regex=True)

    # Strip everything that isn't a digit, dot, comma, dash, or CR/DR suffix
    def _clean_and_parse(v: str) -> float:
        v = v.strip()
        # Handle CR / DR suffix
        upper = v.upper()
        negate = False
        if upper.endswith("DR"):
            negate = True
            v = v[:-2]
        elif upper.endswith("CR"):
            v = v[:-2]

        # Strip non-numeric characters except . , -
        v = re.sub(r"[^\d.,\-]", "", v)
        if not v or v == "-":
            return float("nan")

        try:
            # EU format: 1.234,56  (comma is decimal, dots are thousands)
            if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", v):
                result = float(v.replace(".", "").replace(",", "."))
            else:
                # US/standard: 1,234.56 or plain 1234.56
                result = float(v.replace(",", ""))
        except ValueError:
            return float("nan")

        return -result if negate else result

    return s.apply(_clean_and_parse)


# ══════════════════════════════════════════════════════════════════════════════
#  4. COLUMN DETECTION
# ══════════════════════════════════════════════════════════════════════════════
_COL_SYSTEM = """You are a bank-statement parser.
Given a CSV sample, identify which columns correspond to:
  date        — the transaction date
  description — the merchant name / transaction narrative / narration
  amount      — the transaction amount (single net column preferred)

Return ONLY a compact JSON object, e.g.:
{"date":"Buchungsdatum","description":"Verwendungszweck","amount":"Betrag"}

Use null if a field cannot be identified. No explanation, no markdown."""


def _detect_columns_ai(df: pd.DataFrame, api_key: str) -> dict[str, Optional[str]]:
    sample = df.head(5).to_csv(index=False)
    try:
        r = requests.post(
            _API_URL,
            headers={**_HEADERS, "x-api-key": api_key},
            json={
                "model": _MODEL,
                "max_tokens": 200,
                "system": _COL_SYSTEM,
                "messages": [{"role": "user", "content": f"CSV:\n{sample}"}],
            },
            timeout=20,
        )
        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
            return json.loads(text)
    except Exception:
        pass
    return {"date": None, "description": None, "amount": None}


# Multilingual keyword heuristic (50+ languages)
_DATE_KW = [
    "date","datum","fecha","data","tarikh","дата","日付","날짜","تاریخ",
    "ngày","วันที่","tarehe","tarih","датум","日期","дата","تاريخ",
    "booking","transaction","value","posting","trade",
]
_DESC_KW = [
    "description","details","narration","narrative","memo","reference",
    "particulars","zweck","verwendungszweck","omschrijving","libellé",
    "concepto","descrição","keterangan","назначение","摘要","내역",
    "שם","شرح","chi tiết","beneficiary","payee","merchant","label",
    "remarque","betalingskenmerken","transaktionstext","mô tả",
]
_AMT_KW = [
    "amount","betrag","montant","importe","valor","bedrag","сумма",
    "金額","금액","مبلغ","tutari","số tiền","jumlah","จำนวนเงิน",
    "net","debit/credit","credit","withdrawal","deposit","change",
    "transaction amount","booking amount","movement",
]


def _detect_columns_heuristic(df: pd.DataFrame) -> dict[str, Optional[str]]:
    result: dict[str, Optional[str]] = {"date": None, "description": None, "amount": None}
    for col in df.columns:
        cl = col.lower().strip()
        if result["date"]        is None and any(k in cl for k in _DATE_KW):
            result["date"]        = col
        if result["description"] is None and any(k in cl for k in _DESC_KW):
            result["description"] = col
        if result["amount"]      is None and any(k in cl for k in _AMT_KW):
            result["amount"]      = col
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  5. AI BATCH CATEGORISER
# ══════════════════════════════════════════════════════════════════════════════
_CAT_SYSTEM = (
    "You are a personal finance transaction categoriser.\n"
    "Input: JSON array [{\"id\":N,\"desc\":\"...\",\"amount\":0.0}, ...]\n"
    "Output: JSON array [{\"id\":N,\"category\":\"...\",\"type\":\"Income|Expense|Transfer\"}, ...]\n\n"
    "Rules:\n"
    "- Descriptions may be in ANY language — understand them before categorising.\n"
    "- Use amount sign: negative = expense, positive = income (unless it's a transfer).\n"
    "- 'type' must be exactly 'Income', 'Expense', or 'Transfer'.\n"
    f"- 'category' must be one of: {json.dumps(STANDARD_CATEGORIES)}\n"
    "- Return ONLY the JSON array. No markdown, no preamble."
)


def _categorise_batch_ai(records: list[dict], api_key: str) -> list[dict]:
    try:
        r = requests.post(
            _API_URL,
            headers={**_HEADERS, "x-api-key": api_key},
            json={
                "model": _MODEL,
                "max_tokens": 2048,
                "system": _CAT_SYSTEM,
                "messages": [{"role": "user",
                              "content": json.dumps(records, ensure_ascii=False)}],
            },
            timeout=30,
        )
        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
            return json.loads(text)
    except Exception:
        pass
    return []


def _categorise_all_ai(
    descriptions: list[str],
    amounts: list[float],
    api_key: str,
) -> list[tuple[str, str]]:
    n       = len(descriptions)
    results: list[Optional[tuple[str, str]]] = [None] * n

    for start in range(0, n, _BATCH):
        end     = min(start + _BATCH, n)
        records = [
            {"id": i, "desc": descriptions[i], "amount": float(amounts[i])}
            for i in range(start, end)
        ]
        batch = _categorise_batch_ai(records, api_key)
        for item in batch:
            idx = item.get("id", -1)
            if 0 <= idx < n:
                results[idx] = (
                    item.get("category", "Other Expense"),
                    item.get("type",     "Expense"),
                )

    # Fill any gaps with safe defaults
    for i in range(n):
        if results[i] is None:
            results[i] = (
                ("Other Income", "Income") if amounts[i] > 0
                else ("Other Expense", "Expense")
            )

    return results  # type: ignore[return-value]


# ══════════════════════════════════════════════════════════════════════════════
#  6. KEYWORD FALLBACK
# ══════════════════════════════════════════════════════════════════════════════
def load_keyword_rules(path: Optional[str] = None) -> pd.DataFrame:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "category_rules.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["keyword", "category", "type"])
    rules = pd.read_csv(path)
    rules["keyword"] = rules["keyword"].astype(str).str.lower().str.strip()
    return rules


def _categorise_keyword(
    desc: str, amount: float, rules: pd.DataFrame
) -> tuple[str, str]:
    d = str(desc).lower()
    for _, r in rules.iterrows():
        if r["keyword"] in d:
            return r["category"], r["type"]
    return ("Other Income", "Income") if amount > 0 else ("Other Expense", "Expense")


# ══════════════════════════════════════════════════════════════════════════════
#  7. MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def parse_statement(
    raw_bytes: bytes,
    api_key:   Optional[str] = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Full pipeline: raw CSV bytes → cleaned, categorised DataFrame.

    Parameters
    ----------
    raw_bytes : raw file content from st.file_uploader
    api_key   : Anthropic API key — enables AI column detection + AI categorisation.
                Falls back to keyword rules + heuristic column detection if None.

    Returns
    -------
    df   : DataFrame with columns Date, Description, Amount, Category, Type, Month, Day, DOW
    meta : dict with keys columns_used, method, currency_symbol, warnings
    """
    meta = {
        "columns_used":   {},
        "method":         "keyword",
        "currency_symbol": "$",
        "warnings":       [],
    }

    use_ai = bool(api_key and str(api_key).strip().startswith("sk-ant-"))

    # ── 1. Read ───────────────────────────────────────────────────────────────
    df = read_csv_any_encoding(raw_bytes)
    df.columns = df.columns.str.strip()

    # Drop completely empty rows / columns
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # ── 2. Detect columns ─────────────────────────────────────────────────────
    if use_ai:
        col_map  = _detect_columns_ai(df, api_key)
        fallback = _detect_columns_heuristic(df)
        for k in ("date", "description", "amount"):
            if not col_map.get(k):
                col_map[k] = fallback.get(k)
        meta["method"] = "ai"
    else:
        col_map = _detect_columns_heuristic(df)

    missing = [k for k, v in col_map.items() if not v]
    if missing:
        raise ValueError(
            f"Could not identify these columns: {missing}.\n"
            f"Your CSV has: {df.columns.tolist()}.\n"
            f"Tip: Add an Anthropic API key for AI-powered column detection, or "
            f"rename your columns to 'Date', 'Description', 'Amount'."
        )

    meta["columns_used"] = col_map

    # ── 3. Rename & slice ─────────────────────────────────────────────────────
    rename = {v: k.capitalize() for k, v in col_map.items() if v}
    df     = df.rename(columns=rename)
    keep   = ["Date", "Description", "Amount"]
    extra  = [c for c in df.columns if c not in keep]
    df     = df[keep + extra].copy()

    # ── 4. Parse dates ────────────────────────────────────────────────────────
    df["Date"] = _parse_dates(df["Date"])
    n_bad_dates = int(df["Date"].isna().sum())
    if n_bad_dates:
        meta["warnings"].append(
            f"{n_bad_dates} row(s) had unrecognisable dates and were removed."
        )

    # ── 5. Parse amounts ──────────────────────────────────────────────────────
    # Detect currency symbol before stripping
    raw_sample = df["Amount"].astype(str).head(30).str.cat(sep=" ")
    for sym in ["¥", "₩", "€", "£", "฿", "₹", "₺", "₴", "A$", "NZ$", "HK$", "S$", "$"]:
        if sym in raw_sample:
            meta["currency_symbol"] = sym
            break

    df["Amount"] = _normalise_amount(df["Amount"])
    n_bad_amts   = int(df["Amount"].isna().sum())
    if n_bad_amts:
        meta["warnings"].append(
            f"{n_bad_amts} row(s) had unrecognisable amounts and were removed."
        )

    df = (
        df.dropna(subset=["Date", "Amount"])
        .reset_index(drop=True)
        .sort_values("Date")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(
            "No valid transactions found after parsing. "
            "Check that your Date and Amount columns contain the right data."
        )

    # ── 6. Categorise ─────────────────────────────────────────────────────────
    descs   = df["Description"].astype(str).tolist()
    amounts = df["Amount"].tolist()

    if use_ai:
        results = _categorise_all_ai(descs, amounts, api_key)
    else:
        rules   = load_keyword_rules()
        results = [_categorise_keyword(d, a, rules) for d, a in zip(descs, amounts)]

    df["Category"] = [r[0] for r in results]
    df["Type"]     = [r[1] for r in results]

    # ── 7. Derived columns ────────────────────────────────────────────────────
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Day"]   = df["Date"].dt.date
    df["DOW"]   = df["Date"].dt.strftime("%a")

    return df, meta
