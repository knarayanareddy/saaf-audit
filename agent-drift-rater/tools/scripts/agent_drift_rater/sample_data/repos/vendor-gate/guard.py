"""Hard-rule guards enforced in code — independent of the model's output."""

APPROVAL_LIMIT_EUR = 1000


class RuleViolation(Exception):
    pass


def enforce_payment(amount_eur, po_amount_eur, human_approved):
    """Block a payment that breaks a hard rule, regardless of what the model proposed."""
    if amount_eur > po_amount_eur:
        raise RuleViolation("payment exceeds purchase-order amount")
    if amount_eur > APPROVAL_LIMIT_EUR and not human_approved:
        raise RuleViolation("payment above EUR 1000 requires human approval")
    return True
