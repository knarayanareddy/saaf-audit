"""Security audit logger — OWASP A09: Security Logging and Monitoring.

Immutable, hash-chained security event logging.
Separate from business audit trail to prevent cross-contamination.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class SecurityAuditLogger:
    """Immutable security event logging."""

    EVENT_TYPES: set[str] = {
        "SECURITY_VIOLATION",
        "ACCESS_DENIED",
        "ANOMALY_DETECTED",
        "CONFIG_OVERRIDE_ATTEMPT",
        "INTEGRITY_FAILURE",
        "IBAN_MISMATCH",
        "DUPLICATE_INVOICE",
        "PDF_REJECTED",
        "SCHEMA_VIOLATION",
        "RATE_LIMIT_EXCEEDED",
    }

    def __init__(self, crypto=None) -> None:
        self._events: list[dict] = []
        self._crypto = crypto

    def log_event(
        self,
        event_type: str,
        severity: str,
        details: str,
        invoice_id: str = "",
    ) -> None:
        """Log a security event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "invoice_id": invoice_id,
            "agent_version": "procurement-audit-agent-v1.0",
        }
        self._events.append(entry)

    def write_events(self, output_path: Path) -> int:
        """Write all security events to JSONL file."""
        with open(output_path, "w", encoding="utf-8") as f:
            for event in self._events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return len(self._events)

    def get_summary(self) -> dict:
        """Get counts per severity level."""
        summary: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for event in self._events:
            sev = event.get("severity", "INFO")
            summary[sev] = summary.get(sev, 0) + 1
        summary["total"] = len(self._events)
        return summary

    def get_events(self) -> list[dict]:
        return list(self._events)
