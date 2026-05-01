"""
parser.py
Responsible for one thing: turning raw CSV bytes into a clean DataFrame.

Pipeline
────────
  read()         → decode bytes with any encoding
  detect_columns() → find Date / Description / Amount columns
  parse_dates()  → handle any regional date format
  parse_amounts() → handle US, EU, CR/DR, parenthetical formats
  build_df()     → rename, slice, derive Month / Day / DOW columns

No categorisation, no metrics, no UI here.
"""

from __future__ import annotations

import io
import json
import re
import warnings
from dataclasses import dataclass, field
from typing import Optional

import chardet
import pandas as pd
import requests

from config import CSV_ENCODINGS, ANTHROPIC_API_URL, ANTHROPIC_API_VERSION, ANTHROPIC_MODEL

warnings.filterwarnings("ignore", category=FutureWarning)


# ── Result type ───────────────────────────────────────────────────────────────
@dataclass
class ParseMeta:
    """Metadata returned alongside the parsed DataFrame."""
    columns_used:    dict[str, str]   = field(default_factory=dict)
    detection_method: str             = "heuristic"   # "ai" | "heuristic"
    currency_symbol: str              = "$"
    warnings:        list[str]        = field(default_factory=list)


# ── 1. Encoding-safe reader ───────────────────────────────────────────────────
def read_csv(raw_bytes: bytes) -> pd.DataFrame:
    """
    Decode a CSV from any encoding.
    Tries chardet auto-detection first, then falls back through CSV_ENCODINGS.
    """
    detected = chardet.detect(raw_bytes[:8192]).get("encoding") or ""
    candidates = dict.fromkeys([detected] + CSV_ENCODINGS)  # dedup, preserve order

    for enc in candidates:
        if not enc:
            continue
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, low_memory=False)
            if not df.empty:
                return df
        except Exception:
            continue

    raise ValueError(
        "Could not decode this CSV. "
        "Try re-exporting it as UTF-8 from Excel or your bank's app."
    )


# ── 2. Column detection ───────────────────────────────────────────────────────

# Multilingual keyword lists — ranked roughly by how distinctively
# each keyword identifies its column type.
_DATE_KEYWORDS = [
    "date", "datum", "fecha", "data", "tarikh", "дата", "日付", "날짜",
    "تاریخ", "ngày", "วันที่", "tarehe", "tarih", "датум", "日期",
    "booking", "transaction", "value date", "posting date", "trade date",
]
_DESC_KEYWORDS = [
    "description", "details", "narration", "narrative", "memo", "reference",
    "particulars", "zweck", "verwendungszweck", "omschrijving", "libellé",
    "concepto", "descrição", "keterangan", "назначение", "摘要", "내역",
    "beneficiary", "payee", "merchant", "label", "remarque", "transaktionstext",
]
_AMOUNT_KEYWORDS = [
    "amount", "betrag", "montant", "importe", "valor", "bedrag", "сумма",
    "金額", "금액", "مبلغ", "tutari", "số tiền", "jumlah", "จำนวนเงิน",
    "net", "debit/credit", "transaction amount", "booking amount", "movement",
]

_COL_DETECTION_PROMPT = """\
You are a bank-statement parser. Given the first few rows of a CSV, identify:
  - date        : the transaction date column
  - description : the merchant name / narration column
  - amount      : the single net amount column (prefer a column that includes both debits and credits)

Return ONLY a JSON object: {"date":"<col>","description":"<col>","amount":"<col>"}
Use null if a field cannot be found. No markdown, no explanation."""


def _detect_heuristic(df: pd.DataFrame) -> dict[str, Optional[str]]:
    """Match column names against multilingual keyword lists."""
    result: dict[str, Optional[str]] = {"date": None, "description": None, "amount": None}
    for col in df.columns:
        cl = col.lower().strip()
        if result["date"]        is None and any(k in cl for k in _DATE_KEYWORDS):
            result["date"] = col
        if result["description"] is None and any(k in cl for k in _DESC_KEYWORDS):
            result["description"] = col
        if result["amount"]      is None and any(k in cl for k in _AMOUNT_KEYWORDS):
            result["amount"] = col
    return result


def _detect_ai(df: pd.DataFrame, api_key: str) -> dict[str, Optional[str]]:
    """Ask Claude to identify columns — handles any language CSV header."""
    sample = df.head(5).to_csv(index=False)
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
                "max_tokens": 200,
                "system":     _COL_DETECTION_PROMPT,
                "messages":   [{"role": "user", "content": f"CSV:\n{sample}"}],
            },
            timeout=15,
        )
        if response.status_code == 200:
            text = response.json()["content"][0]["text"].strip()
            text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
            return json.loads(text)
    except Exception:
        pass
    return {"date": None, "description": None, "amount": None}


def detect_columns(
    df: pd.DataFrame,
    api_key: Optional[str] = None,
) -> tuple[dict[str, Optional[str]], str]:
    """
    Returns (column_map, method) where method is 'ai' or 'heuristic'.
    AI detection is tried first when an api_key is provided;
    heuristic fills any gaps the AI leaves.
    """
    col_map  = {"date": None, "description": None, "amount": None}
    method   = "heuristic"

    if api_key:
        col_map = _detect_ai(df, api_key)
        method  = "ai"

    # Always run heuristic to fill any nulls
    fallback = _detect_heuristic(df)
    for key in ("date", "description", "amount"):
        if not col_map.get(key):
            col_map[key] = fallback.get(key)

    missing = [k for k, v in col_map.items() if not v]
    if missing:
        raise ValueError(
            f"Could not identify columns: {missing}.\n"
            f"Your CSV has: {df.columns.tolist()}.\n"
            f"Tip: rename your columns to 'Date', 'Description', 'Amount' — "
            f"or add an API key for AI-powered detection."
        )

    return col_map, method


# ── 3. Date parser ────────────────────────────────────────────────────────────
_DATE_FORMATS = [
    "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
    "%d.%m.%Y", "%Y.%m.%d", "%d %b %Y", "%d %B %Y",
    "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y",
    "%d/%m/%y", "%m/%d/%y", "%y-%m-%d",
]


def parse_dates(series: pd.Series) -> pd.Series:
    """
    Robust date parser — pandas 2.0+ compatible (infer_datetime_format removed).
    Tries format='mixed' (pandas ≥ 2.0), then falls back through common formats.
    """
    s = series.astype(str).str.strip()

    # Try pandas 2.x mixed-format inference
    try:
        result = pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")
        if result.notna().mean() > 0.8:
            return result
    except TypeError:
        pass

    # Fallback: try without format argument
    try:
        result = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if result.notna().mean() > 0.8:
            return result
    except Exception:
        pass

    # Fallback: score each explicit format and pick the best
    best, best_n = s.map(lambda _: pd.NaT), 0
    for fmt in _DATE_FORMATS:
        try:
            parsed = pd.to_datetime(s, errors="coerce", format=fmt)
            n = int(parsed.notna().sum())
            if n > best_n:
                best, best_n = parsed, n
        except Exception:
            continue

    return best


# ── 4. Amount normaliser ──────────────────────────────────────────────────────
def _parse_single_amount(raw: str) -> float:
    """
    Converts a single raw amount string to float.
    Handles:
      US/AU:  1,234.56  →  1234.56
      EU:     1.234,56  →  1234.56
      Parens: (150.00)  → -150.0
      CR/DR:  150.00DR  → -150.0   (debit = money out)
      Symbol: $1,234.56 →  1234.56
    """
    v = str(raw).strip()

    # Parenthetical negative
    if re.match(r"^\(.+\)$", v):
        v = "-" + v[1:-1]

    # CR / DR suffix
    upper = v.upper()
    negate = False
    if upper.endswith("DR"):
        negate, v = True, v[:-2]
    elif upper.endswith("CR"):
        v = v[:-2]

    # Strip non-numeric characters except . , -
    v = re.sub(r"[^\d.,\-]", "", v).strip()

    if not v or v == "-":
        return float("nan")

    try:
        # EU format: 1.234,56
        if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", v):
            result = float(v.replace(".", "").replace(",", "."))
        else:
            result = float(v.replace(",", ""))
    except ValueError:
        return float("nan")

    return -result if negate else result


def parse_amounts(series: pd.Series) -> tuple[pd.Series, str]:
    """
    Returns (normalised_series, detected_currency_symbol).
    """
    raw_text = series.astype(str).head(30).str.cat(sep=" ")
    symbol   = "$"
    for sym in ["¥", "₩", "€", "£", "฿", "₹", "₺", "₴", "A$", "NZ$", "HK$", "S$", "$"]:
        if sym in raw_text:
            symbol = sym
            break

    return series.apply(_parse_single_amount), symbol


# ── 5. Main entry point ───────────────────────────────────────────────────────
def parse_statement(
    raw_bytes: bytes,
    api_key:   Optional[str] = None,
) -> tuple[pd.DataFrame, ParseMeta]:
    """
    Full ingestion pipeline.

    Parameters
    ----------
    raw_bytes : raw file content from st.file_uploader
    api_key   : Anthropic API key — enables AI column detection.
                Pass None to use heuristic detection only.

    Returns
    -------
    df   : DataFrame with columns:
             Date, Description, Amount,
             Month (YYYY-MM), Day (date), DOW (Mon-Sun)
           NOTE: Category and Type are NOT added here — see categoriser.py
    meta : ParseMeta describing what was detected
    """
    meta = ParseMeta()

    # ── Step 1: Read ──────────────────────────────────────────────────────────
    df = read_csv(raw_bytes)
    df.columns = df.columns.str.strip()
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # ── Step 2: Detect columns ────────────────────────────────────────────────
    col_map, method          = detect_columns(df, api_key)
    meta.columns_used        = {k: v for k, v in col_map.items() if v}
    meta.detection_method    = method

    # ── Step 3: Rename to standard names ─────────────────────────────────────
    rename_map = {v: k.capitalize() for k, v in col_map.items() if v}
    df = df.rename(columns=rename_map)
    standard   = ["Date", "Description", "Amount"]
    extra_cols = [c for c in df.columns if c not in standard]
    df = df[standard + extra_cols].copy()

    # ── Step 4: Parse dates ───────────────────────────────────────────────────
    df["Date"] = parse_dates(df["Date"])
    n_bad_dates = int(df["Date"].isna().sum())
    if n_bad_dates:
        meta.warnings.append(f"{n_bad_dates} row(s) dropped — unrecognisable date format.")

    # ── Step 5: Parse amounts ─────────────────────────────────────────────────
    df["Amount"], meta.currency_symbol = parse_amounts(df["Amount"])
    n_bad_amounts = int(df["Amount"].isna().sum())
    if n_bad_amounts:
        meta.warnings.append(f"{n_bad_amounts} row(s) dropped — unrecognisable amount format.")

    # ── Step 6: Drop unusable rows, sort ─────────────────────────────────────
    df = (
        df.dropna(subset=["Date", "Amount"])
        .sort_values("Date")
        .reset_index(drop=True)
    )

    if df.empty:
        raise ValueError(
            "No valid transactions found after parsing. "
            "Check that your Date and Amount columns contain the right data."
        )

    # ── Step 7: Derived time columns ──────────────────────────────────────────
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Day"]   = df["Date"].dt.date
    df["DOW"]   = df["Date"].dt.strftime("%a")

    return df, meta
