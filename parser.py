"""
parser.py  —  Universal bank statement parser
Phase 1 upgrade: handles real-world messy bank statement formats.

Supported file formats
  CSV  — any encoding, any delimiter
  XLSX — Excel workbooks (openpyxl)
  XLS  — legacy Excel (xlrd, optional)

Supported column layouts
  1. Single signed Amount column     (+income / -expense)
  2. Separate Debit + Credit columns (Amount = Credit − Debit)
  3. Balance-only column             (Amount = Balance[i] − Balance[i−1])
  4. CR/DR suffix amounts            (150.00DR = −150.00)
  5. Parenthetical negatives         ((150.00) = −150.00)
  6. European number format          (1.234,56 = 1234.56)

Description cleaning
  Strips EFTPOS terminal IDs, POS reference numbers, random card suffixes,
  date/time stamps embedded in descriptions, and other noise that makes
  categorisation fail. The cleaned description is stored alongside the original.
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


# ══════════════════════════════════════════════════════════════════════════════
#  RESULT TYPE
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class ParseMeta:
    """Metadata returned alongside the parsed DataFrame."""
    columns_used:      dict[str, str]  = field(default_factory=dict)
    detection_method:  str             = "heuristic"   # "ai" | "heuristic"
    amount_strategy:   str             = "single"      # "single" | "debit_credit" | "balance_diff"
    currency_symbol:   str             = "$"
    file_format:       str             = "csv"         # "csv" | "xlsx"
    warnings:          list[str]       = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════════
#  1. FILE READERS
# ══════════════════════════════════════════════════════════════════════════════
# Keywords that indicate a header row vs freeform metadata
_HEADER_KEYWORDS = {
    "date", "datum", "fecha", "buchungsdatum", "wertstellung",
    "description", "details", "narrative", "narration", "particulars",
    "verwendungszweck", "omschrijving", "transaction", "debit", "credit",
    "amount", "betrag", "montant", "balance", "saldo", "withdrawal",
}


def _find_data_start(lines: list[str], sep: str) -> int:
    """
    Find the row index where the actual table data starts.

    Real bank statements have freeform metadata (account name, period, etc.)
    before the column headers. This function finds the first row that either:
      a) contains a recognised column header keyword, OR
      b) contains a date-like value (YYYY-MM-DD, DD/MM/YYYY, DD Mon YYYY)

    Falls back to the first row with >= 3 fields if nothing better is found.
    """
    import re
    date_like = re.compile(
        r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}"     # YYYY-MM-DD
        r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"     # DD/MM/YYYY or DD.MM.YYYY
        r"|\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}"    # DD Mon YYYY
        r"|[A-Za-z]{3}\s+\d{1,2}\s+\d{4})\b"  # Mon DD YYYY
    )

    best_header_row = None
    first_wide_row  = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        fields = [f.strip() for f in stripped.split(sep)]
        non_empty = [f for f in fields if f]

        if len(non_empty) < 2:
            continue

        # Track first row with 3+ fields as fallback
        if first_wide_row is None and len(non_empty) >= 3:
            first_wide_row = i

        # Check if any field looks like a known column header keyword.
        # Real column headers are short AND contain no digits.
        # This excludes metadata like "Opening Balance: 3.812,50 EUR"
        # while matching proper headers like "Date", "Debit (DR)", "Balance".
        lower_fields = [f.lower() for f in non_empty]
        import re as _re
        header_like = [
            f for f in lower_fields
            if len(f) <= 50 and not _re.search(r"\d", f)
        ]
        if header_like and any(kw in " ".join(header_like) for kw in _HEADER_KEYWORDS):
            return i

        # Check if any field looks like a date — only count if >= 3 fields
        # (metadata lines like "Period: 2026-01-01" have only 2 fields)
        if len(non_empty) >= 3 and any(date_like.search(f) for f in non_empty):
            # Row above is likely the header
            return max(0, i - 1)

    return first_wide_row or 0


def _score_delimiter_result(df: pd.DataFrame) -> int:
    """
    Score how well a parsed DataFrame matches expected bank statement structure.
    Higher score = better delimiter/encoding/skiprows combination.
    """
    score = len(df.columns) * 10   # more columns = more likely correct

    header_text = " ".join(str(c).lower() for c in df.columns)
    # Bonus for every recognised column header keyword
    for kw in _HEADER_KEYWORDS:
        if kw in header_text:
            score += 15

    # Penalty if header columns look like actual data (contain digits)
    import re as _re
    for col in df.columns:
        if _re.search(r"\d{4}", str(col)):   # 4-digit year or number sequence
            score -= 30

    return score


def _read_csv(raw_bytes: bytes) -> pd.DataFrame:
    """
    Decode a CSV from any encoding, auto-detecting the correct delimiter.

    For each encoding × delimiter combination, scores the result by:
      - Number of columns found (more = better)
      - Whether column names match known bank statement keywords
      - Penalty if column names look like data rows (contain long numbers)

    Returns the highest-scoring valid DataFrame.
    """
    detected  = chardet.detect(raw_bytes[:8192]).get("encoding") or ""
    candidates = dict.fromkeys([detected] + CSV_ENCODINGS)

    best_df    = None
    best_score = -9999

    for enc in candidates:
        if not enc:
            continue
        try:
            text  = raw_bytes.decode(enc, errors="replace")
            lines = text.splitlines()
        except Exception:
            continue

        for sep in [",", ";", "\t", "|"]:
            try:
                skip = _find_data_start(lines, sep)
                try:
                    df = pd.read_csv(
                        io.BytesIO(raw_bytes), encoding=enc,
                        sep=sep, skiprows=skip, low_memory=False,
                        on_bad_lines="warn",
                    )
                except TypeError:
                    df = pd.read_csv(
                        io.BytesIO(raw_bytes), encoding=enc,
                        sep=sep, skiprows=skip, low_memory=False,
                        error_bad_lines=False,
                    )
                df.columns = [str(c).strip() for c in df.columns]
                df = df.dropna(how="all")

                if df.empty or len(df.columns) < 2:
                    continue

                score = _score_delimiter_result(df)
                if score > best_score:
                    best_score = score
                    best_df    = df

            except Exception:
                continue

        # Early exit: if we found something with a high score, don't try more encodings
        if best_score >= 50:
            break

    if best_df is not None:
        return best_df

    raise ValueError(
        "Could not decode this file. "
        "Try re-exporting it as UTF-8 from Excel or your bank's app."
    )


def _read_excel(raw_bytes: bytes) -> pd.DataFrame:
    """
    Read an Excel workbook (.xlsx or .xls).
    Tries every sheet and picks the one with the most rows
    that looks like a transaction list (has a date-like column).
    """
    try:
        xl = pd.ExcelFile(io.BytesIO(raw_bytes), engine="openpyxl")
    except Exception:
        try:
            xl = pd.ExcelFile(io.BytesIO(raw_bytes), engine="xlrd")
        except Exception as e:
            raise ValueError(f"Could not open Excel file: {e}")

    best_df   = None
    best_rows = 0

    for sheet in xl.sheet_names:
        try:
            df = xl.parse(sheet, header=None)
            if df.empty:
                continue

            # Find the header row — the first row that looks like column headers
            # (has at least 2 non-null string cells)
            header_row = 0
            for i, row in df.iterrows():
                non_null = row.dropna()
                if len(non_null) >= 2 and non_null.apply(lambda x: isinstance(x, str)).sum() >= 2:
                    header_row = i
                    break

            df = xl.parse(sheet, header=header_row)
            df = df.dropna(how="all").dropna(axis=1, how="all")
            df.columns = [str(c).strip() for c in df.columns]

            if len(df) > best_rows:
                best_df, best_rows = df, len(df)
        except Exception:
            continue

    if best_df is None or best_df.empty:
        raise ValueError("No usable data found in Excel file.")

    return best_df


def read_file(raw_bytes: bytes, filename: str = "") -> tuple[pd.DataFrame, str]:
    """
    Dispatch to the correct reader based on file extension.
    Returns (DataFrame, format_name).
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext in ("xlsx", "xls"):
        return _read_excel(raw_bytes), "xlsx"
    else:
        # Default to CSV (also handles files without extension)
        return _read_csv(raw_bytes), "csv"


# ══════════════════════════════════════════════════════════════════════════════
#  2. COLUMN DETECTION
#  Now detects four layouts:
#    a) Single amount column
#    b) Debit + Credit columns (most Australian/UK banks)
#    c) Balance column only
#    d) Single column with CR/DR suffix
# ══════════════════════════════════════════════════════════════════════════════
_DATE_KEYWORDS = [
    "date", "datum", "fecha", "data", "tarikh", "дата", "日付", "날짜",
    "تاریخ", "ngày", "วันที่", "tarehe", "tarih", "датум", "日期",
    "booking", "transaction", "value date", "posting date", "trade date",
    "processed",
]
_DESC_KEYWORDS = [
    "description", "details", "narration", "narrative", "memo", "reference",
    "particulars", "zweck", "verwendungszweck", "omschrijving", "libellé",
    "concepto", "descrição", "keterangan", "назначение", "摘要", "내역",
    "beneficiary", "payee", "merchant", "label", "transaktionstext",
    "transaction details", "transaction description",
]
_AMOUNT_KEYWORDS = [
    "amount", "betrag", "montant", "importe", "valor", "bedrag", "сумма",
    "金額", "금액", "مبلغ", "tutari", "số tiền", "jumlah", "จำนวนเงิน",
    "net", "debit/credit", "transaction amount", "booking amount",
]
# Short ambiguous codes ("cr", "dr", "in", "out") must match the FULL
# column name to avoid false positives like "description" matching "cr".
# Longer keywords are safe to match as substrings.
_DEBIT_EXACT   = {"debit", "dr", "out", "withdrawals", "debits"}
_DEBIT_SUBSTR  = ["withdrawal", "paid out", "paid-out", "money out"]
_CREDIT_EXACT  = {"credit", "cr", "in", "deposits", "credits"}
_CREDIT_SUBSTR = ["deposit", "paid in", "paid-in", "money in"]
_BALANCE_KEYWORDS = ["balance", "running balance", "closing balance", "ledger balance"]


def _detect_heuristic(df: pd.DataFrame) -> dict:
    """
    Detect date, description, amount/debit/credit/balance columns.

    Short ambiguous codes ("cr", "dr", "in", "out") are matched EXACTLY
    against the full column name to prevent false positives like
    "description" matching "cr" (which caused catastrophic mis-parsing).
    """
    result = {k: None for k in ("date", "description", "amount", "debit", "credit", "balance")}

    for col in df.columns:
        cl = col.lower().strip()
        if result["date"]        is None and any(k in cl for k in _DATE_KEYWORDS):
            result["date"] = col
        if result["description"] is None and any(k in cl for k in _DESC_KEYWORDS):
            result["description"] = col
        if result["amount"]      is None and any(k in cl for k in _AMOUNT_KEYWORDS):
            result["amount"] = col
        if result["debit"] is None and (
            cl in _DEBIT_EXACT or any(k in cl for k in _DEBIT_SUBSTR)
        ):
            result["debit"] = col
        if result["credit"] is None and (
            cl in _CREDIT_EXACT or any(k in cl for k in _CREDIT_SUBSTR)
        ):
            result["credit"] = col
        if result["balance"]     is None and any(k in cl for k in _BALANCE_KEYWORDS):
            result["balance"] = col

    return result


_COL_DETECTION_PROMPT = """\
You are a bank-statement parser. Given the first few rows of a bank statement, identify:
  - date        : the transaction date column
  - description : the merchant name / narration / details column
  - amount      : a single signed amount column (positive=credit, negative=debit), OR null if not present
  - debit       : a debit-only column (money out), OR null if not present
  - credit      : a credit-only column (money in), OR null if not present
  - balance     : a running balance column, OR null if not present

Return ONLY a JSON object with these 6 keys. Use null where not found.
Example: {"date":"Date","description":"Details","amount":null,"debit":"Withdrawals","credit":"Deposits","balance":"Balance"}
No markdown, no explanation."""


def _detect_ai(df: pd.DataFrame, api_key: str) -> dict:
    sample = df.head(6).to_csv(index=False)
    try:
        r = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key":         api_key,
                "content-type":      "application/json",
                "anthropic-version": ANTHROPIC_API_VERSION,
            },
            json={
                "model":    ANTHROPIC_MODEL,
                "max_tokens": 300,
                "system":   _COL_DETECTION_PROMPT,
                "messages": [{"role": "user", "content": f"Bank statement:\n{sample}"}],
            },
            timeout=15,
        )
        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
            return json.loads(text)
    except Exception:
        pass
    return {k: None for k in ("date", "description", "amount", "debit", "credit", "balance")}


def detect_columns(
    df: pd.DataFrame,
    api_key: Optional[str] = None,
) -> tuple[dict, str]:
    """
    Detect all relevant columns. Returns (col_map, method).
    col_map keys: date, description, amount, debit, credit, balance
    """
    if api_key:
        col_map = _detect_ai(df, api_key)
        method  = "ai"
        # Fill any nulls from heuristic
        fallback = _detect_heuristic(df)
        for k in col_map:
            if not col_map.get(k):
                col_map[k] = fallback.get(k)
    else:
        col_map = _detect_heuristic(df)
        method  = "heuristic"

    # Must have date and description at minimum
    if not col_map.get("date"):
        raise ValueError(
            f"Could not detect a date column. "
            f"Columns found: {df.columns.tolist()}. "
            f"Rename your date column to 'Date' or add an API key."
        )
    if not col_map.get("description"):
        raise ValueError(
            f"Could not detect a description column. "
            f"Columns found: {df.columns.tolist()}."
        )
    # Must have some form of amount
    has_amount   = bool(col_map.get("amount"))
    has_dc       = bool(col_map.get("debit")) or bool(col_map.get("credit"))
    has_balance  = bool(col_map.get("balance"))
    if not (has_amount or has_dc or has_balance):
        raise ValueError(
            f"Could not detect any amount column (amount, debit/credit, or balance). "
            f"Columns found: {df.columns.tolist()}."
        )

    return col_map, method


# ══════════════════════════════════════════════════════════════════════════════
#  3. DATE PARSER
# ══════════════════════════════════════════════════════════════════════════════
_DATE_FORMATS = [
    "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
    "%d.%m.%Y", "%Y.%m.%d", "%d %b %Y", "%d %B %Y",
    "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y",
    "%d/%m/%y", "%m/%d/%y", "%y-%m-%d",
    "%d-%b-%Y", "%d-%b-%y", "%b-%y",
]


def parse_dates(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    try:
        result = pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")
        if result.notna().mean() > 0.8:
            return result
    except TypeError:
        pass
    try:
        result = pd.to_datetime(s, errors="coerce", dayfirst=True)
        if result.notna().mean() > 0.8:
            return result
    except Exception:
        pass
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


# ══════════════════════════════════════════════════════════════════════════════
#  4. AMOUNT PARSING  (handles all column layouts)
# ══════════════════════════════════════════════════════════════════════════════
def _parse_single_amount(raw: str) -> float:
    """Convert one raw amount string to float. Handles all regional formats."""
    v = str(raw).strip()
    if not v or v.lower() in ("nan", "none", "", "-", "–"):
        return float("nan")

    # Parenthetical negative: (150.00) → -150.00
    if re.match(r"^\(.+\)$", v):
        v = "-" + v[1:-1]

    # CR / DR suffix
    upper  = v.upper()
    negate = False
    if upper.endswith("DR"):
        negate, v = True, v[:-2]
    elif upper.endswith("CR"):
        v = v[:-2]

    v = re.sub(r"[^\d.,\-]", "", v).strip()
    if not v or v in ("-", "."):
        return float("nan")

    try:
        if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", v):  # EU: 1.234,56
            result = float(v.replace(".", "").replace(",", "."))
        else:
            result = float(v.replace(",", ""))
    except ValueError:
        return float("nan")

    return -result if negate else result


def _currency_symbol(raw_text: str) -> str:
    # Check symbol characters first
    for sym in ["¥", "₩", "€", "£", "฿", "₹", "₺", "₴", "A$", "NZ$", "HK$", "S$", "$"]:
        if sym in raw_text:
            return sym
    # Check text currency codes (e.g. European banks write "EUR" not "€")
    text_upper = raw_text.upper()
    if " EUR" in text_upper or "EUR " in text_upper or "\nEUR" in text_upper:
        return "€"
    if " GBP" in text_upper or "GBP " in text_upper:
        return "£"
    if " JPY" in text_upper or "JPY " in text_upper:
        return "¥"
    return "$"


def resolve_amounts(
    df: pd.DataFrame,
    col_map: dict,
    file_text: str = "",
) -> tuple[pd.Series, str, str]:
    """
    Compute a single signed Amount series from whatever columns exist.

    Strategy 1 — single amount column (already signed)
    Strategy 2 — debit/credit columns: Amount = credit − debit
    Strategy 3 — balance column: Amount = Balance[i] − Balance[i−1]
                  (only used if no other amount data found)

    Returns (amount_series, currency_symbol, strategy_name)
    """
    # Detect currency: check amount column values first, then full file text
    amt_cols = [col_map.get(k) for k in ("amount", "debit", "credit", "balance") if col_map.get(k)]
    col_text = " ".join(
        df[c].astype(str).head(30).str.cat(sep=" ") for c in amt_cols if c in df.columns
    )
    # Combine column text + file header for currency detection (handles "EUR" in file header)
    raw_text = col_text + " " + file_text[:2000]
    sym = _currency_symbol(raw_text)

    # Strategy 1: single amount column
    if col_map.get("amount") and col_map["amount"] in df.columns:
        series = df[col_map["amount"]].apply(_parse_single_amount)
        if series.notna().mean() > 0.5:
            return series, sym, "single"

    # Strategy 2: debit + credit columns
    debit_col  = col_map.get("debit")
    credit_col = col_map.get("credit")
    if (debit_col and debit_col in df.columns) or (credit_col and credit_col in df.columns):
        debits  = df[debit_col].apply(_parse_single_amount).fillna(0) if debit_col and debit_col in df.columns else pd.Series(0, index=df.index)
        credits = df[credit_col].apply(_parse_single_amount).fillna(0) if credit_col and credit_col in df.columns else pd.Series(0, index=df.index)
        # Debits are money out (negative), credits are money in (positive)
        # Both columns typically show positive numbers
        series  = credits.abs() - debits.abs()
        if series.abs().sum() > 0:
            return series, sym, "debit_credit"

    # Strategy 3: balance difference
    bal_col = col_map.get("balance")
    if bal_col and bal_col in df.columns:
        balance = df[bal_col].apply(_parse_single_amount)
        series  = balance.diff()          # positive = balance went up = income
        series.iloc[0] = float("nan")    # first row has no prior balance
        if series.notna().sum() > 0:
            return series, sym, "balance_diff"

    raise ValueError(
        "Could not compute transaction amounts. "
        "The file must have an Amount column, Debit+Credit columns, or a Balance column."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  5. DESCRIPTION CLEANER
#  Real bank statements contain noise: terminal IDs, reference numbers,
#  card suffixes, timestamps. Strip these so categorisation works correctly.
# ══════════════════════════════════════════════════════════════════════════════

# Ordered list of cleaning rules. Each is a (pattern, replacement) tuple.
# Applied in sequence — earlier rules run first.
_CLEAN_RULES: list[tuple[str, str]] = [
    # EFTPOS / POS terminal IDs
    (r"\bEFTPOS\b\s*",                          ""),
    (r"\bPOS\b\s+\d+",                          ""),
    (r"\bPOS\b\s*#?\d*",                        ""),

    # Card numbers (last 4 digits suffix)
    (r"\*{2,}\d{4}\b",                          ""),
    (r"\bXXXX\d{4}\b",                          ""),
    (r"\bcard\s*\d{4}\b",                       "", ),

    # Reference / transaction numbers
    (r"\bREF[:#\s]\s*\w+",                      ""),
    (r"\bTXN[:#\s]\s*\w+",                      ""),
    (r"\bTRN[:#\s]\s*\w+",                      ""),
    (r"\b\d{10,}\b",                            ""),   # long number sequences

    # Dates embedded in descriptions (e.g. "AMAZON 12JAN26")
    (r"\b\d{1,2}[A-Z]{3}\d{2,4}\b",            ""),
    (r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",     ""),

    # Time stamps
    (r"\b\d{1,2}:\d{2}(:\d{2})?\b",            ""),

    # Direct debit / standing order prefixes
    (r"^(DDR|DD|SO|BPAY|BACS|SEPA|FASTER PAY)\s+", ""),

    # Internet banking transfer noise
    (r"^(TFR|FT|TRANSFER|IBT|INTERNET TRANSFER)\s+(OUT|IN|FROM|TO)?\s*", ""),
    (r"INTERNET (BANKING|BKG|TRANSFER)",        ""),

    # Visa / Mastercard prefix noise
    (r"^(VISA|MC|MASTERCARD|DEBIT CARD|CREDIT CARD)\s+",  ""),
    (r"^(PURCHASE|PAYMENT|PAYMENT TO|PAY TO)\s+",          ""),

    # Australian-specific
    (r"\bAU\b$",                                ""),   # trailing country code
    (r"\bNSW\b|\bVIC\b|\bQLD\b|\bWA\b|\bSA\b", ""),

    # Excess whitespace after cleaning
    (r"\s{2,}",                                 " "),
    (r"^\s+|\s+$",                              ""),
]

_COMPILED_RULES = [(re.compile(p, re.IGNORECASE), r) for p, r in _CLEAN_RULES]


def clean_description(raw: str) -> str:
    """
    Strip noise from a bank transaction description.
    Returns a cleaner string suitable for categorisation.
    Preserves the spirit of the description — just removes the noise.
    """
    s = str(raw).strip()
    for pattern, replacement in _COMPILED_RULES:
        s = pattern.sub(replacement, s)
    return s.strip() or raw   # fallback to original if cleaning removed everything


# ══════════════════════════════════════════════════════════════════════════════
#  6. MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def parse_statement(
    raw_bytes: bytes,
    api_key:   Optional[str] = None,
    filename:  str           = "",
) -> tuple[pd.DataFrame, ParseMeta]:
    """
    Full ingestion pipeline. Accepts CSV or Excel. Returns a clean DataFrame.

    Parameters
    ----------
    raw_bytes : raw file bytes from st.file_uploader
    api_key   : Anthropic API key — enables AI column detection
    filename  : original filename (used to detect file format)

    Returns
    -------
    df   : DataFrame with columns:
             Date, Description, DescriptionClean, Amount,
             Month (YYYY-MM), Day (date), DOW (Mon-Sun)
    meta : ParseMeta with detected format, columns, strategy, warnings
    """
    meta = ParseMeta()

    # ── Step 1: Read file ─────────────────────────────────────────────────────
    df, meta.file_format = read_file(raw_bytes, filename)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")

    # ── Step 2: Detect columns ────────────────────────────────────────────────
    col_map, meta.detection_method = detect_columns(df, api_key)
    meta.columns_used = {k: v for k, v in col_map.items() if v}

    # ── Step 3: Extract description ───────────────────────────────────────────
    df["Description"] = df[col_map["description"]].astype(str).str.strip()

    # ── Step 4: Extract and parse dates ──────────────────────────────────────
    df["Date"] = parse_dates(df[col_map["date"]])
    n_bad = int(df["Date"].isna().sum())
    if n_bad:
        meta.warnings.append(f"{n_bad} row(s) had unreadable dates and were removed.")

    # ── Step 5: Resolve amounts ───────────────────────────────────────────────
    df["Amount"], meta.currency_symbol, meta.amount_strategy = resolve_amounts(df, col_map, file_text=raw_bytes.decode(meta_enc, errors="replace")[:3000] if (meta_enc := chardet.detect(raw_bytes[:512]).get("encoding") or "utf-8") else "")
    n_bad = int(df["Amount"].isna().sum())
    if n_bad:
        meta.warnings.append(f"{n_bad} row(s) had unreadable amounts and were removed.")

    # ── Step 6: Clean ─────────────────────────────────────────────────────────
    df = (
        df.dropna(subset=["Date", "Amount"])
          .sort_values("Date")
          .reset_index(drop=True)
    )
    if df.empty:
        raise ValueError(
            "No valid transactions found. "
            "Check that Date and Amount columns contain recognisable data."
        )

    # ── Step 7: Clean descriptions ────────────────────────────────────────────
    # Keep original for display, clean copy for categorisation
    df["DescriptionClean"] = df["Description"].apply(clean_description)

    # ── Step 8: Derived time columns ──────────────────────────────────────────
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    df["Day"]   = df["Date"].dt.date
    df["DOW"]   = df["Date"].dt.strftime("%a")

    # Keep only the standard columns (plus extras the caller might want)
    keep = ["Date", "Description", "DescriptionClean", "Amount", "Month", "Day", "DOW"]
    df   = df[keep].copy()

    return df, meta
