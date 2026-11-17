from gdpr_agent.legal_basis_mapper import map_legal_basis
from gdpr_agent.models import PIICategory, PIIField


def test_maps_reimbursement_to_legitimate_interest():
    field = PIIField(field_name="iban", value="DE89...", category=PIICategory.FINANCIAL, confidence=0.95)
    result = map_legal_basis(field, purpose="reimbursement_review")
    assert result.legal_basis == "art_6_1_f"


def test_maps_breach_investigation():
    field = PIIField(field_name="email", value="a@b.com", category=PIICategory.CONTACT, confidence=0.9)
    result = map_legal_basis(field, purpose="breach_investigation")
    assert result.legal_basis == "art_33"


def test_unknown_purpose_defaults_to_no_basis():
    field = PIIField(field_name="email", value="a@b.com", category=PIICategory.CONTACT, confidence=0.9)
    result = map_legal_basis(field, purpose="unknown_purpose")
    assert result.legal_basis is None


def test_special_category_requires_explicit_basis():
    field = PIIField(field_name="health", value="diabetes", category=PIICategory.SPECIAL, confidence=0.9)
    result = map_legal_basis(field, purpose="reimbursement_review")
    assert result.legal_basis is None  # No basis for special data in reimbursement
