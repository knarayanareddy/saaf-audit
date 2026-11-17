"""SAAF Guard: veilige bouwstenen + CI-check tegen bekende fouten in SAAF-agents."""
from .safe import (FENCE_RULE, FENCE_RULE_EN, INCONCLUSIVE, fence_rule, AuditTrail, fence, is_grounded, require_finite,
                   rollup, safe_cell, within_tolerance)

__all__ = ["FENCE_RULE", "FENCE_RULE_EN", "fence_rule", "INCONCLUSIVE", "AuditTrail", "fence", "is_grounded", "require_finite",
           "rollup", "safe_cell", "within_tolerance"]
__version__ = "0.2.0"
