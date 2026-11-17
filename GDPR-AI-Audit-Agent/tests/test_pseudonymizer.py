import pytest

from gdpr_agent.config import MIN_PSEUDONYM_KEY_LENGTH, PSEUDONYM_TOKEN_HEX_CHARS
from gdpr_agent.models import Role
from gdpr_agent.pseudonymizer import Pseudonymizer, PseudonymVault

KEY = "unit-test-key-long-enough-to-pass-the-check-0123456789"
OTHER_KEY = "a-different-unit-test-key-long-enough-to-pass-9876543210"
REASON = "Subject access request SAR-2026-014."


def test_pseudonymize_returns_token():
    ps = Pseudonymizer(secret_key=KEY)
    token = ps.pseudonymize("Hans Mueller")
    assert token != "Hans Mueller"
    assert token.startswith("PSE-")


def test_pseudonymize_is_deterministic():
    ps = Pseudonymizer(secret_key=KEY)
    assert ps.pseudonymize("Hans Mueller") == ps.pseudonymize("Hans Mueller")


def test_pseudonymize_different_values_different_tokens():
    ps = Pseudonymizer(secret_key=KEY)
    assert ps.pseudonymize("Hans Mueller") != ps.pseudonymize("Maria Schmidt")


def test_different_keys_different_tokens():
    ps1 = Pseudonymizer(secret_key=KEY)
    ps2 = Pseudonymizer(secret_key=OTHER_KEY)
    assert ps1.pseudonymize("Hans Mueller") != ps2.pseudonymize("Hans Mueller")


def test_token_uses_full_width_digest():
    """48-bit tokens collide in the low millions of values; 128 bits does not."""
    ps = Pseudonymizer(secret_key=KEY)
    token = ps.pseudonymize("Hans Mueller")
    assert len(token) == len("PSE-") + PSEUDONYM_TOKEN_HEX_CHARS
    assert PSEUDONYM_TOKEN_HEX_CHARS >= 32


def test_empty_key_is_rejected():
    with pytest.raises(ValueError, match="key is required"):
        Pseudonymizer(secret_key="")


def test_short_key_is_rejected():
    with pytest.raises(ValueError, match="at least"):
        Pseudonymizer(secret_key="x" * (MIN_PSEUDONYM_KEY_LENGTH - 1))


def test_pseudonymizer_is_one_way_without_a_vault():
    """No vault means nothing retains the original value."""
    ps = Pseudonymizer(secret_key=KEY)
    token = ps.pseudonymize("Hans Mueller")
    assert not ps.is_reversible
    with pytest.raises(PermissionError, match="one-way"):
        ps.depseudonymize(token, role=Role.DPO, justification=REASON)


def test_vault_reverses_for_authorised_role():
    vault = PseudonymVault()
    ps = Pseudonymizer(secret_key=KEY, vault=vault)
    token = ps.pseudonymize("Hans Mueller")
    assert ps.depseudonymize(token, role=Role.DPO, justification=REASON) == "Hans Mueller"


def test_vault_refuses_unauthorised_role():
    """An auditor works with pseudonymised data and may not re-identify it."""
    vault = PseudonymVault()
    ps = Pseudonymizer(secret_key=KEY, vault=vault)
    token = ps.pseudonymize("Hans Mueller")
    with pytest.raises(PermissionError, match="not authorised"):
        ps.depseudonymize(token, role=Role.AUDITOR, justification=REASON)


def test_vault_requires_a_justification():
    vault = PseudonymVault()
    ps = Pseudonymizer(secret_key=KEY, vault=vault)
    token = ps.pseudonymize("Hans Mueller")
    with pytest.raises(PermissionError, match="justification"):
        ps.depseudonymize(token, role=Role.DPO, justification="   ")


def test_unknown_token_returns_none():
    vault = PseudonymVault()
    ps = Pseudonymizer(secret_key=KEY, vault=vault)
    assert ps.depseudonymize("PSE-unknown", role=Role.DPO, justification=REASON) is None


def test_vault_clear_drops_reidentification_data():
    vault = PseudonymVault()
    ps = Pseudonymizer(secret_key=KEY, vault=vault)
    ps.pseudonymize("Hans Mueller")
    assert len(vault) == 1
    vault.clear()
    assert len(vault) == 0
