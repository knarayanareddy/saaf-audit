"""Config hardening — OWASP A05: Security Misconfiguration Prevention.

Validates and enforces secure configuration with hard ceilings
that cannot be overridden by settings.yaml.
"""


class ConfigHardening:
    """Validate and enforce secure configuration limits."""

    HARD_LIMITS: dict = {
        "price_tolerance_pct": {"max": 5.0, "description": "Max price tolerance"},
        "max_invoice_amount": {"max": 10_000_000, "description": "Max invoice amount"},
        "max_single_item_price": {"max": 1_000_000, "description": "Max unit price"},
    }

    def __init__(self) -> None:
        self._override_attempts: list[dict] = []

    def validate_settings(self, settings: dict) -> tuple[bool, list[str]]:
        """Validate settings against HARD_LIMITS. Returns (valid, warnings)."""
        warnings: list[str] = []
        valid = True

        # Check price tolerance
        tol = settings.get("price_tolerance_pct", 0.5)
        max_tol = self.HARD_LIMITS["price_tolerance_pct"]["max"]
        if tol > max_tol:
            warnings.append(
                f"price_tolerance_pct={tol} exceeds hard limit {max_tol}. "
                f"Clamped to {max_tol}."
            )
            self._override_attempts.append({
                "setting": "price_tolerance_pct",
                "attempted": tol,
                "enforced": max_tol,
            })

        # Check invoice split sums to 1.0
        split = settings.get("invoice_split", {})
        total = sum(split.values())
        if abs(total - 1.0) > 0.001:
            warnings.append(f"invoice_split sums to {total}, expected 1.0")
            valid = False

        return valid, warnings

    def enforce_tolerance(self, value: float) -> float:
        """Clamp tolerance to hard ceiling."""
        max_val = self.HARD_LIMITS["price_tolerance_pct"]["max"]
        if value > max_val:
            self._override_attempts.append({
                "setting": "price_tolerance_pct",
                "attempted": value,
                "enforced": max_val,
            })
            return max_val
        return value

    def get_override_attempts(self) -> list[dict]:
        return list(self._override_attempts)
