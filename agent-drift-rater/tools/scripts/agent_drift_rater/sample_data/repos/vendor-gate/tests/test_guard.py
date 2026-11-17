"""Prove the guard blocks a violating action regardless of model output."""

import pytest

from guard import enforce_payment, RuleViolation


def test_blocks_over_limit_without_approval():
    with pytest.raises(RuleViolation):
        enforce_payment(amount_eur=5000, po_amount_eur=8000, human_approved=False)


def test_blocks_over_po():
    with pytest.raises(RuleViolation):
        enforce_payment(amount_eur=200, po_amount_eur=100, human_approved=True)


def test_allows_within_policy():
    assert enforce_payment(amount_eur=50, po_amount_eur=100, human_approved=False)
