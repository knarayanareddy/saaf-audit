"""Access control — OWASP A01: Broken Access Control Prevention.

Role-based access control for pipeline operations.
Enforces separation of duties per ASML audit requirements.
"""

from datetime import datetime, timezone


class AccessControl:
    """Role-based access control for pipeline operations."""

    ROLES: dict[str, list[str]] = {
        "INTAKE_OPERATOR": ["intake_agent"],
        "CONTRACT_REVIEWER": ["contract_agent", "threeway_agent"],
        "AUDITOR": ["decision_agent", "evaluate", "read_audit_trail"],
        "FINANCE_CONTROLLER": ["payment_agent"],
        "ADMIN": ["*"],
        "PIPELINE_RUNNER": ["*"],  # Automated pipeline execution
    }

    def __init__(self) -> None:
        self._access_log: list[dict] = []

    def check_permission(self, role: str, operation: str) -> bool:
        """Check if role has permission for operation."""
        allowed_ops = self.ROLES.get(role, [])
        if "*" in allowed_ops:
            return True
        return operation in allowed_ops

    def log_access(self, role: str, operation: str, allowed: bool, details: str = "") -> None:
        """Log access attempt for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "operation": operation,
            "allowed": allowed,
            "details": details,
        }
        self._access_log.append(entry)

    def get_access_log(self) -> list[dict]:
        return list(self._access_log)

    def enforce(self, role: str, operation: str) -> bool:
        """Check permission and log the attempt. Returns True if allowed."""
        allowed = self.check_permission(role, operation)
        self.log_access(role, operation, allowed)
        return allowed
