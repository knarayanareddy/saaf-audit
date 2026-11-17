"""Configuration for the GDPR Audit Agent."""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
REGULATORY_DIR = PROJECT_ROOT / "regulatory"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL", "")

# --- Pseudonymisation ------------------------------------------------------
# The HMAC key is deliberately NOT read at import time and has no default. A
# shared or hardcoded key makes every token reproducible by anyone holding the
# source, which would leave the data merely obfuscated rather than
# pseudonymised in the sense of GDPR Art. 4(5).
PSEUDONYM_KEY_ENV_VAR = "GDPR_PSEUDONYM_KEY"
MIN_PSEUDONYM_KEY_LENGTH = 32
PSEUDONYM_TOKEN_HEX_CHARS = 32  # 128 bits of token space


def get_pseudonym_key() -> str:
    """Read the HMAC key at call time so it is never baked into an import."""
    return os.getenv(PSEUDONYM_KEY_ENV_VAR, "")


# --- PII detection ---------------------------------------------------------
# Ordered most-specific first: the detector takes the first match, so the loose
# patterns (phone) must come last or they swallow IBANs and national IDs.
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
    path = REGULATORY_DIR / "gdpr_legal_bases.json"
    with open(path) as f:
        return json.load(f)
