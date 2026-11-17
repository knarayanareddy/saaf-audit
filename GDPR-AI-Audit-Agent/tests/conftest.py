import json
from pathlib import Path

import pytest

from gdpr_agent.config import PSEUDONYM_KEY_ENV_VAR
from gdpr_agent.models import AuditContext, Role

# Test-only key. Long enough to satisfy the minimum-length check; the point of
# the check is that no key ships in the source, so real runs must supply one
# through the environment.
TEST_PSEUDONYM_KEY = "test-pseudonym-key-for-unit-tests-only-0123456789"


@pytest.fixture(autouse=True)
def pseudonym_key_env(monkeypatch):
    """Supply a pseudonymisation key for every test.

    The pipeline refuses to start without one, which is the behaviour under
    test in tests/test_pseudonymizer.py.
    """
    monkeypatch.setenv(PSEUDONYM_KEY_ENV_VAR, TEST_PSEUDONYM_KEY)
    return TEST_PSEUDONYM_KEY


@pytest.fixture
def sample_records():
    data_path = Path(__file__).parent.parent / "data" / "sample_reimbursement.json"
    with open(data_path) as f:
        return json.load(f)


@pytest.fixture
def auditor_context():
    return AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )


@pytest.fixture
def dpo_context():
    return AuditContext(
        role=Role.DPO,
        purpose="compliance_check",
        legal_basis="legal_obligation",
    )


@pytest.fixture
def admin_context():
    """Admin access is unmasked, so it must carry a justification."""
    return AuditContext(
        role=Role.ADMIN,
        purpose="system_admin",
        legal_basis="consent",
        justification="Investigating ticket INC-4417: corrupted reimbursement export.",
    )
