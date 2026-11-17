"""Rate limiter — OWASP A05: Security Misconfiguration / DoS Prevention.

Prevents abuse through excessive processing, duplicate submissions,
and stale invoices.
"""

from datetime import date, timedelta
from pathlib import Path


class RateLimiter:
    """Prevent abuse through excessive processing."""

    MAX_BATCH_SIZE: int = 500
    MAX_FILE_SIZE_MB: int = 10
    MAX_INVOICE_AGE_DAYS: int = 90

    def __init__(self) -> None:
        self._processed_ids: set[str] = set()

    def check_batch_size(self, count: int) -> tuple[bool, str]:
        """Reject batches exceeding maximum size."""
        if count > self.MAX_BATCH_SIZE:
            return False, f"Batch size {count} exceeds limit {self.MAX_BATCH_SIZE}"
        return True, "OK"

    def check_file_size(self, path: Path) -> tuple[bool, str]:
        """Reject files exceeding maximum size."""
        if not path.exists():
            return False, f"File not found: {path}"
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            return False, f"File {path.name} is {size_mb:.1f}MB (limit: {self.MAX_FILE_SIZE_MB}MB)"
        return True, "OK"

    def check_invoice_age(self, invoice_date_str: str) -> tuple[bool, str]:
        """Reject invoices older than MAX_INVOICE_AGE_DAYS."""
        try:
            inv_date = date.fromisoformat(invoice_date_str)
            age_days = (date.today() - inv_date).days
            if age_days > self.MAX_INVOICE_AGE_DAYS:
                return False, f"Invoice date {invoice_date_str} is {age_days} days old (limit: {self.MAX_INVOICE_AGE_DAYS})"
            return True, "OK"
        except (ValueError, TypeError):
            return False, f"Invalid invoice date: {invoice_date_str}"

    def check_duplicate(self, invoice_id: str) -> tuple[bool, str]:
        """Detect duplicate invoice submission."""
        if invoice_id in self._processed_ids:
            return False, f"Duplicate invoice: {invoice_id}"
        self._processed_ids.add(invoice_id)
        return True, "OK"

    def get_processed_ids(self) -> set[str]:
        return set(self._processed_ids)
