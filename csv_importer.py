"""
csv_importer.py — Parses bank CSV exports and maps them to expense records.

Supports:
  - VR Bank / Volksbank / Raiffeisenbank (Germany) — semicolon-separated, German decimals
  - Generic German bank CSV (fallback)
  - Monzo (UK) — comma-separated
  - Generic CSV fallback with auto-detection
"""

import pandas as pd
import re
from datetime import datetime
from io import StringIO, BytesIO


# ── Category keyword mapping ──────────────────────────────────────────────────
# Maps keywords found in transaction descriptions → expense categories.
# Edit these to match your real spending patterns.

CATEGORY_RULES = {
    "Rent":          ["miete", "rent", "wohnung", "vermieter", "hausgeld"],
    "Food":          ["rewe", "lidl", "aldi", "edeka", "netto", "penny",
                      "kaufland", "supermarkt", "bäcker", "bakery",
                      "restaurant", "mcdonald", "burger", "pizza", "döner",
                      "spar", "tegut", "norma", "rossmann", "dm markt"],
    "Transport":     ["db ", "deutsche bahn", "bahn", "bus", "u-bahn",
                      "s-bahn", "uber", "taxi", "tankstelle", "shell",
                      "aral", "esso", "jet ", "fuel", "parking", "parken"],
    "Entertainment": ["netflix", "spotify", "amazon prime", "disney",
                      "kino", "cinema", "theater", "steam", "playstation",
                      "apple.com/bill", "youtube", "dazn", "sky "],
    "Savings":       ["sparplan", "saving", "depot", "etf", "invest",
                      "dkb invest", "scalable", "trade republic"],
    "Other":         [],  # Catch-all — always keep last
}


def guess_category(description: str) -> str:
    """Return the best-matching category based on keywords in the description."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_RULES.items():
        if category == "Other":
            continue
        for kw in keywords:
            if kw in desc_lower:
                return category
    return "Other"


def parse_german_amount(value: str) -> float:
    """
    Convert German-formatted number to float.
    Examples:  '1.234,56' → 1234.56 | '-50,00' → -50.0
    """
    value = str(value).strip().replace(" ", "")
    # Remove thousand separators (dots), replace decimal comma with dot
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_german_date(value: str) -> str:
    """
    Convert DD.MM.YYYY or DD.MM.YY to YYYY-MM-DD.
    Returns empty string if parsing fails.
    """
    value = str(value).strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


# ── VR Bank / Volksbank parser ────────────────────────────────────────────────

def parse_vrbank_csv(file_bytes: bytes) -> tuple[list, list]:
    """
    Parse a VR Bank / Volksbank Raiffeisenbank CSV export.

    VR Bank exports look like this (semicolon-separated, Latin-1 or UTF-8):
    Buchungstag;Valuta;Auftraggeber/Beguenstigter;Buchungstext;Verwendungszweck;Betrag;...

    Returns:
        (expense_rows, skipped_rows)
        expense_rows = list of (amount, category, description, date)
        skipped_rows = list of raw row dicts that were skipped (income/zero)
    """
    # Try UTF-8 first, then Latin-1 (common for German banks)
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Could not decode file — please check the encoding.")

    # VR Bank sometimes has header rows before the actual column headers.
    # Find the line that starts with "Buchungstag" — that's the real header.
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Buchungstag" in line or "buchungstag" in line.lower():
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Could not find 'Buchungstag' column in file. "
            "Please make sure you exported from VR Bank as CSV."
        )

    # Re-read from the header line onward
    csv_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(
        StringIO(csv_text),
        sep=";",
        dtype=str,
        on_bad_lines="skip",
    )

    # Normalise column names: strip spaces, lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    expense_rows = []
    skipped_rows = []

    for _, row in df.iterrows():
        # ── Get date ─────────────────────────────────────────────────────────
        date_raw = row.get("buchungstag", row.get("valuta", ""))
        date = parse_german_date(date_raw)
        if not date:
            skipped_rows.append(dict(row))
            continue

        # ── Get amount ────────────────────────────────────────────────────────
        # Column is usually "betrag" or "umsatz"
        amount_raw = row.get("betrag", row.get("umsatz", "0"))
        amount = parse_german_amount(amount_raw)

        # Skip zero amounts
        if amount == 0:
            skipped_rows.append(dict(row))
            continue

        # Skip positive amounts (income/credits) — only track expenses
        if amount > 0:
            skipped_rows.append(dict(row))
            continue

        # Make amount positive (we store expenses as positive numbers)
        amount = abs(amount)

        # ── Get description ───────────────────────────────────────────────────
        # Combine Auftraggeber + Verwendungszweck for best keyword matching
        payee     = row.get("auftraggeber/beguenstigter", row.get("auftraggeber", ""))
        purpose   = row.get("verwendungszweck", "")
        book_text = row.get("buchungstext", "")
        description = f"{payee} {purpose} {book_text}".strip()
        if not description:
            description = "Imported transaction"

        # ── Guess category ────────────────────────────────────────────────────
        category = guess_category(description)

        expense_rows.append((amount, category, description, date))

    return expense_rows, skipped_rows


# ── Generic / fallback parser ─────────────────────────────────────────────────

def parse_generic_csv(file_bytes: bytes) -> tuple[list, list]:
    """
    Fallback parser for other CSV formats.
    Tries to auto-detect: date column, amount column, description column.
    Works for Monzo, HSBC, Barclays, and most standard exports.
    """
    for encoding in ("utf-8", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    # Try comma and semicolon separators
    for sep in (",", ";", "\t"):
        try:
            df = pd.read_csv(StringIO(text), sep=sep, dtype=str, on_bad_lines="skip")
            if len(df.columns) >= 3:
                break
        except Exception:
            continue

    df.columns = [c.strip().lower() for c in df.columns]

    # Map common column name variations
    DATE_COLS   = ["date", "buchungstag", "transaction date", "datum", "created"]
    AMOUNT_COLS = ["amount", "betrag", "umsatz", "debit", "credit", "value"]
    DESC_COLS   = ["description", "verwendungszweck", "name", "merchant", "payee",
                   "auftraggeber", "memo", "details"]

    date_col   = next((c for c in DATE_COLS   if c in df.columns), None)
    amount_col = next((c for c in AMOUNT_COLS if c in df.columns), None)
    desc_col   = next((c for c in DESC_COLS   if c in df.columns), None)

    if not date_col or not amount_col:
        raise ValueError(
            "Could not find date/amount columns in your CSV. "
            "Please contact support or add expenses manually."
        )

    expense_rows = []
    skipped_rows = []

    for _, row in df.iterrows():
        # Parse date — try multiple formats
        date_raw = str(row.get(date_col, "")).strip()
        date = ""
        for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                date = datetime.strptime(date_raw, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        if not date:
            skipped_rows.append(dict(row))
            continue

        # Parse amount
        amount_raw = str(row.get(amount_col, "0"))
        # Handle German format
        if "," in amount_raw and "." in amount_raw:
            amount = parse_german_amount(amount_raw)
        else:
            amount_raw = amount_raw.replace(",", ".")
            try:
                amount = float(re.sub(r"[^\d.\-]", "", amount_raw))
            except ValueError:
                skipped_rows.append(dict(row))
                continue

        if amount == 0 or amount > 0:
            skipped_rows.append(dict(row))
            continue

        amount = abs(amount)
        description = str(row.get(desc_col, "Imported")) if desc_col else "Imported"
        category = guess_category(description)
        expense_rows.append((amount, category, description, date))

    return expense_rows, skipped_rows
