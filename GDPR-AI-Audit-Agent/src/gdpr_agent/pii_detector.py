"""PII detection using regex pattern matching and heuristics."""

import re
from typing import Any, Iterator

from gdpr_agent.config import (
    PII_PATTERNS,
    SAFE_FIELDS,
    is_probable_bsn_value,
    is_probable_phone,
)
from gdpr_agent.models import PIICategory, PIIField

# Map pattern names to PII categories
PATTERN_CATEGORY_MAP: dict[str, PIICategory] = {
    "email": PIICategory.CONTACT,
    "iban": PIICategory.FINANCIAL,
    "bsn": PIICategory.IDENTIFIER,
    "ssn": PIICategory.IDENTIFIER,
    "ip_address": PIICategory.IDENTIFIER,
    "phone": PIICategory.CONTACT,
}

# When a value trips several patterns, report the most sensitive category
# rather than whichever happened to be checked first.
CATEGORY_PRIORITY: dict[PIICategory, int] = {
    PIICategory.SPECIAL: 0,
    PIICategory.IDENTIFIER: 1,
    PIICategory.FINANCIAL: 2,
    PIICategory.CONTACT: 3,
}

# Extra validation for patterns that are too permissive on their own.
PATTERN_VALIDATORS = {
    "bsn": is_probable_bsn_value,
    "phone": is_probable_phone,
}

# Keywords in field names that suggest PII
NAME_KEYWORDS: set[str] = {"name", "first_name", "last_name", "employee_name", "full_name"}
ADDRESS_KEYWORDS: set[str] = {"address", "street", "city", "zip", "postal"}


def _classify_by_pattern(value: str) -> tuple[PIICategory, list[str], float] | None:
    """Match a value against every known PII pattern.

    Returns the highest-priority category together with the full list of
    patterns that fired, so a value that is both an identifier and contact
    data is not silently reduced to whichever pattern was checked first.
    """
    str_value = str(value)
    matched: list[str] = []

    for pattern_name, pattern in PII_PATTERNS.items():
        if not re.search(pattern, str_value):
            continue
        validator = PATTERN_VALIDATORS.get(pattern_name)
        if validator and not validator(str_value):
            continue
        matched.append(pattern_name)

    if not matched:
        return None

    category = min(
        (PATTERN_CATEGORY_MAP[name] for name in matched),
        key=lambda c: CATEGORY_PRIORITY[c],
    )
    return category, matched, 0.95


def _classify_by_field_name(field_name: str) -> tuple[PIICategory, float] | None:
    """Classify PII based on the field name itself."""
    lower = field_name.lower()
    if any(kw in lower for kw in NAME_KEYWORDS):
        return PIICategory.IDENTIFIER, 0.9
    if any(kw in lower for kw in ADDRESS_KEYWORDS):
        return PIICategory.CONTACT, 0.85
    return None


def iter_leaf_fields(
    value: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Walk a record and yield every scalar leaf with its key path.

    Previously only top-level keys were examined, so PII nested inside an
    object or a list was stringified wholesale and never classified on its
    own terms.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_leaf_fields(child, path + (str(key),))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from iter_leaf_fields(child, path + (str(index),))
    else:
        yield path, value


def detect_pii_in_record(record: dict[str, Any]) -> list[PIIField]:
    """Detect PII fields in a single data record.

    Uses a two-pass approach:
    1. Regex pattern matching on values (high confidence)
    2. Field name heuristics (medium confidence)

    Nested objects and lists are traversed; each leaf is reported under its
    dotted key path.
    """
    detected: list[PIIField] = []

    for path, value in iter_leaf_fields(record):
        if not path or value is None:
            continue

        leaf_name = path[-1]
        display_name = ".".join(path)
        str_value = str(value)

        # Pass 1: Pattern matching. This runs even for "safe" field names —
        # a column called `id` that holds an IBAN is still an IBAN.
        pattern_match = _classify_by_pattern(str_value)
        if pattern_match:
            category, matched_patterns, confidence = pattern_match
            detected.append(PIIField(
                field_name=display_name,
                value=str_value,
                category=category,
                confidence=confidence,
                matched_patterns=matched_patterns,
                path=list(path),
            ))
            continue

        # Pass 2: Field name heuristics. Skipped for names known to be
        # non-identifying, since the heuristic keys off the name alone.
        if leaf_name.lower() in SAFE_FIELDS:
            continue

        name_match = _classify_by_field_name(leaf_name)
        if name_match:
            category, confidence = name_match
            detected.append(PIIField(
                field_name=display_name,
                value=str_value,
                category=category,
                confidence=confidence,
                matched_patterns=[],
                path=list(path),
            ))

    return detected
