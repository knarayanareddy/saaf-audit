"""Input sanitizer — OWASP A03: Injection Prevention.

Sanitizes all external inputs before processing.
Blocks SQL injection, command injection, path traversal,
script injection, CSV formula injection, and XXE attacks.
"""

import re
import unicodedata
from datetime import date
from pathlib import Path


class SecurityViolation(Exception):
    """Raised when a security violation is detected in input data."""

    def __init__(self, field: str, pattern: str, value: str) -> None:
        self.field = field
        self.pattern = pattern
        self.value_preview = value[:80] if value else ""
        super().__init__(
            f"Security violation in '{field}': matched pattern '{pattern}' "
            f"in value '{self.value_preview}'"
        )


# Pre-compiled regex patterns for injection detection
_BLOCKED_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("SQL_INJECTION", re.compile(
        r"(?i)\b(SELECT|UNION|DROP|INSERT|UPDATE|DELETE|EXEC|EXECUTE)\b|--|;|'|OR\s+1\s*=\s*1",
    )),
    ("COMMAND_INJECTION", re.compile(
        r"\||\&\&|\$\(|`|\/bin\/|cmd\.exe|powershell",
        re.IGNORECASE,
    )),
    ("PATH_TRAVERSAL", re.compile(
        r"\.\./|\.\.\\|%2e%2e|%252e",
        re.IGNORECASE,
    )),
    ("SCRIPT_INJECTION", re.compile(
        r"<script|javascript:|on\w+\s*=|data:text/html",
        re.IGNORECASE,
    )),
    ("CSV_FORMULA", re.compile(r"^[=+\-@\|]")),
    ("XXE_ATTACK", re.compile(
        r"<!DOCTYPE|<!ENTITY|SYSTEM\s",
        re.IGNORECASE,
    )),
]


class InputSanitizer:
    """Sanitize all external inputs before processing."""

    MAX_ID_LENGTH: int = 50
    MAX_TEXT_LENGTH: int = 500
    MIN_DATE_YEAR: int = 2020
    MAX_DATE_YEAR: int = 2030
    MAX_AMOUNT: float = 10_000_000.0
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Dangerous PDF keywords (read as raw bytes, not parsed)
    _PDF_DANGEROUS: list[bytes] = [
        b"/JavaScript", b"/JS", b"/OpenAction",
        b"/AA", b"/Launch", b"/EmbeddedFile",
    ]

    def sanitize_string(self, value: str, field_name: str, max_len: int | None = None) -> str:
        """Sanitize a string value: strip, limit length, normalize, check patterns."""
        if not isinstance(value, str):
            raise SecurityViolation(field_name, "NOT_STRING", str(value))

        # Strip whitespace
        value = value.strip()

        # Limit length
        limit = max_len or self.MAX_TEXT_LENGTH
        if len(value) > limit:
            raise SecurityViolation(field_name, f"LENGTH>{limit}", value)

        # NFC normalize to prevent homoglyph attacks
        value = unicodedata.normalize("NFC", value)

        # Check blocked patterns
        for pattern_name, pattern in _BLOCKED_PATTERNS:
            if pattern.search(value):
                raise SecurityViolation(field_name, pattern_name, value)

        return value

    def sanitize_invoice(self, data: dict) -> dict:
        """Sanitize all fields in an invoice dict."""
        sanitized = {}

        # String fields with ID length limit
        id_fields = ["invoice_id", "supplier_id", "part_id", "po_ref", "grn_ref"]
        for field in id_fields:
            if field in data and data[field] is not None:
                sanitized[field] = self.sanitize_string(str(data[field]), field, self.MAX_ID_LENGTH)

        # String fields with text length limit
        text_fields = ["supplier_name", "part_description", "iban", "vat_number", "currency"]
        for field in text_fields:
            if field in data and data[field] is not None:
                sanitized[field] = self.sanitize_string(str(data[field]), field, self.MAX_TEXT_LENGTH)

        # Numeric fields: validate actual numbers
        numeric_fields = ["quantity", "unit_price", "total_amount", "vat_amount", "total_incl_vat"]
        for field in numeric_fields:
            if field in data and data[field] is not None:
                val = data[field]
                if isinstance(val, str):
                    try:
                        val = float(val)
                    except (ValueError, OverflowError):
                        raise SecurityViolation(field, "INVALID_NUMBER", str(val))

                if not isinstance(val, (int, float)):
                    raise SecurityViolation(field, "NOT_NUMERIC", str(val))

                # Check for NaN, Inf
                import math
                if math.isnan(val) or math.isinf(val):
                    raise SecurityViolation(field, "NAN_OR_INF", str(val))

                # Amount bounds
                if field in ("unit_price", "total_amount", "vat_amount", "total_incl_vat"):
                    if val < 0 or val > self.MAX_AMOUNT:
                        raise SecurityViolation(field, f"OUT_OF_RANGE(0-{self.MAX_AMOUNT})", str(val))

                if field == "quantity" and (val <= 0 or val > 100_000):
                    raise SecurityViolation(field, "OUT_OF_RANGE(1-100000)", str(val))

                sanitized[field] = val

        # Date fields
        date_fields = ["invoice_date", "due_date"]
        for field in date_fields:
            if field in data and data[field] is not None:
                val = str(data[field]).strip()
                try:
                    d = date.fromisoformat(val)
                    if d.year < self.MIN_DATE_YEAR or d.year > self.MAX_DATE_YEAR:
                        raise SecurityViolation(field, f"YEAR_OUT_OF_RANGE({self.MIN_DATE_YEAR}-{self.MAX_DATE_YEAR})", val)
                    sanitized[field] = val
                except ValueError:
                    raise SecurityViolation(field, "INVALID_DATE", val)

        # Copy remaining safe fields
        passthrough = ["invoice_status", "error_injected"]
        for field in passthrough:
            if field in data:
                sanitized[field] = data[field]

        return sanitized

    def validate_pdf(self, pdf_path: Path) -> tuple[bool, str]:
        """Validate PDF file safety without parsing (avoids ReDoS)."""
        if not pdf_path.exists():
            return False, "File does not exist"

        # Size check
        size = pdf_path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            return False, f"File too large: {size / 1024 / 1024:.1f}MB > 10MB limit"

        if size == 0:
            return False, "Empty file"

        # Magic bytes check
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                return False, f"Invalid magic bytes: {header!r} (expected %PDF-)"

            # Read entire content for dangerous keywords
            f.seek(0)
            content = f.read()

        for keyword in self._PDF_DANGEROUS:
            if keyword in content:
                return False, f"Dangerous PDF keyword found: {keyword.decode()}"

        return True, "OK"
