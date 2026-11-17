"""Configuration for the Privacy Guard engine.

Adapted for IA Wingman: the HMAC key is read from the app-wide `Settings`
(`backend/config.py`) instead of a package-local `.env`, and the GDPR legal
basis table is bundled next to this package.
"""

import json
import re
from pathlib import Path

from config import settings

PACKAGE_DIR = Path(__file__).parent

# --- Pseudonymisation ------------------------------------------------------
# The HMAC key has no default. A shared or hardcoded key makes every token
# reproducible by anyone holding the source, which would leave the data merely
# obfuscated rather than pseudonymised in the sense of GDPR Art. 4(5).
PSEUDONYM_KEY_ENV_VAR = "GDPR_PSEUDONYM_KEY"
MIN_PSEUDONYM_KEY_LENGTH = 32
PSEUDONYM_TOKEN_HEX_CHARS = 32  # 128 bits of token space


def get_pseudonym_key() -> str:
    """Read the HMAC key at call time from the app settings."""
    return getattr(settings, PSEUDONYM_KEY_ENV_VAR, "") or ""


# --- PII detection ---------------------------------------------------------
# Ordered most-specific first: the detector reports the highest-priority
# category, so the loose patterns (phone) sit last for readability.
PII_PATTERNS: dict[str, str] = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
    "bsn": r"(?<!\d)\d{9}(?!\d)",
    "ssn": r"\b\d{2}\s?\d{6}\s?[A-Z]\s?\d{3}\b",
    "ip_address": (
        r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
    ),
    "phone": r"(?<![\d.])\+?\d[\d\s\-]{7,15}\d(?![\d.])",
}

# Values shaped like a date or timestamp. Digit-dense but not personal data,
# and they otherwise trip the phone pattern.
DATE_LIKE_PATTERN = r"^\s*\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?\s*$"

# Phone numbers carry at least 9 digits once separators are stripped. This is
# what keeps "2026-01-15" (8 digits) from being reported as a phone number.
MIN_PHONE_DIGITS = 9
MAX_PHONE_DIGITS = 15

# Field names that carry no PII *by virtue of their name*. These still have
# their values pattern-matched: a column called "id" holding an IBAN is an
# IBAN. Only the name-based heuristics are skipped.
SAFE_FIELDS: set[str] = {
    "id", "date", "amount", "category", "department", "currency",
    "risk_rating", "country", "ubo_verified",
}


def is_valid_bsn(value: str) -> bool:
    """Validate a Dutch BSN against the 11-proef checksum.

    Weights 9..2 for the first eight digits and -1 for the ninth; the weighted
    sum must be divisible by 11. Without this every 9-digit number (order
    numbers, cost centres) would be reported as a national identifier.
    """
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 9:
        return False
    if all(d == 0 for d in digits):
        return False
    weights = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    return sum(d * w for d, w in zip(digits, weights)) % 11 == 0


def is_probable_bsn_value(value: str) -> bool:
    """True if the value contains a 9-digit run that passes the 11-proef."""
    for match in re.finditer(PII_PATTERNS["bsn"], value):
        if is_valid_bsn(match.group()):
            return True
    return False


def is_probable_phone(value: str) -> bool:
    """Reject date-like and too-short candidates matched by the phone pattern."""
    if re.match(DATE_LIKE_PATTERN, value):
        return False
    digit_count = sum(1 for c in value if c.isdigit())
    return MIN_PHONE_DIGITS <= digit_count <= MAX_PHONE_DIGITS


def load_legal_bases() -> dict:
    with open(PACKAGE_DIR / "gdpr_legal_bases.json", encoding="utf-8") as f:
        return json.load(f)
