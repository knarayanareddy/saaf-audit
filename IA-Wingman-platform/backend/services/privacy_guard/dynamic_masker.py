"""Context-aware, role-based dynamic masking engine."""

from .models import MaskingLevel, MaskingResult, PIICategory

REDACTED = "[REDACTED]"


def _split_email(value: str) -> tuple[str, str] | None:
    local, sep, domain = value.rpartition("@")
    if not sep or not local or not domain:
        return None
    return local, domain


def _mask_email_full(value: str) -> str:
    """hans.mueller@example.com -> h***@***.com

    Only the public suffix survives, so the employer domain does not leak.
    """
    parts = _split_email(value)
    if parts is None:
        return REDACTED
    local, domain = parts
    tld = domain.rsplit(".", 1)[-1]
    return f"{local[0]}***@***.{tld}"


def _mask_email_partial(value: str) -> str:
    """hans.mueller@example.com -> h***@example.com"""
    parts = _split_email(value)
    if parts is None:
        return REDACTED
    local, domain = parts
    return f"{local[0]}***@{domain}"


def _mask_iban_full(value: str) -> str:
    """DE89370400440532013000 -> DE******************** (country code only)."""
    if len(value) >= 6:
        return value[:2] + "*" * (len(value) - 2)
    return REDACTED


def _mask_iban_partial(value: str) -> str:
    """DE89370400440532013000 -> DE****************3000

    The check digits are masked too: they are a mod-97 function of the rest of
    the account number, so publishing them alongside the last four narrows the
    search space for the remainder.
    """
    if len(value) >= 10:
        return value[:2] + "*" * (len(value) - 6) + value[-4:]
    return _mask_iban_full(value)


def _mask_name_full(value: str) -> str:
    return REDACTED


def _mask_name_partial(value: str) -> str:
    """Hans Mueller -> H*** M***"""
    words = value.split()
    return " ".join(f"{w[0]}***" if len(w) > 1 else "*" for w in words)


def _mask_generic_full(value: str) -> str:
    return REDACTED


def _mask_generic_partial(value: str) -> str:
    if len(value) > 4:
        return value[:2] + "***" + value[-1:]
    return "***"


def mask_value(
    value: str,
    field_name: str,
    category: PIICategory,
    masking_level: MaskingLevel,
) -> MaskingResult:
    """Mask a single PII value based on its category and the required level."""
    if masking_level == MaskingLevel.NONE:
        return MaskingResult(
            field_name=field_name,
            original_category=category,
            masked_value=value,
            masking_method="none",
        )

    is_full = masking_level == MaskingLevel.FULL
    method = "redacted" if is_full else "partial"

    if category == PIICategory.CONTACT:
        if "@" in value:
            masked = _mask_email_full(value) if is_full else _mask_email_partial(value)
        else:
            masked = _mask_generic_full(value) if is_full else _mask_generic_partial(value)
    elif category == PIICategory.FINANCIAL:
        masked = _mask_iban_full(value) if is_full else _mask_iban_partial(value)
    elif category == PIICategory.IDENTIFIER:
        masked = _mask_name_full(value) if is_full else _mask_name_partial(value)
    elif category == PIICategory.SPECIAL:
        # Special category always fully redacted
        masked = REDACTED
        method = "redacted"
    else:
        masked = _mask_generic_full(value) if is_full else _mask_generic_partial(value)

    return MaskingResult(
        field_name=field_name,
        original_category=category,
        masked_value=masked,
        masking_method=method,
    )
