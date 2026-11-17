import pytest

from gdpr_agent.models import (
    AuditContext,
    MaskingLevel,
    PIICategory,
    PIIField,
    Role,
)


def test_pii_field_creation():
    field = PIIField(
        field_name="email",
        value="hans@example.com",
        category=PIICategory.CONTACT,
        confidence=0.95,
    )
    assert field.field_name == "email"
    assert field.category == PIICategory.CONTACT
    assert field.confidence == 0.95


def test_audit_context_default_masking_level():
    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="review",
        legal_basis="legitimate_interest",
    )
    assert ctx.masking_level == MaskingLevel.FULL


def test_dpo_gets_partial_masking():
    ctx = AuditContext(
        role=Role.DPO,
        purpose="compliance",
        legal_basis="legal_obligation",
    )
    assert ctx.masking_level == MaskingLevel.PARTIAL


def test_admin_gets_no_masking(admin_context):
    assert admin_context.masking_level == MaskingLevel.NONE


def test_admin_without_justification_is_rejected():
    """Unmasked access is otherwise an unguarded dropdown selection."""
    with pytest.raises(ValueError, match="justification"):
        AuditContext(
            role=Role.ADMIN,
            purpose="system_admin",
            legal_basis="consent",
        )


def test_admin_with_token_justification_is_rejected():
    with pytest.raises(ValueError, match="justification"):
        AuditContext(
            role=Role.ADMIN,
            purpose="system_admin",
            legal_basis="consent",
            justification="ok",
        )


def test_non_admin_roles_need_no_justification():
    ctx = AuditContext(role=Role.AUDITOR, purpose="review", legal_basis="legitimate_interest")
    assert ctx.justification is None


def test_pii_category_values():
    assert PIICategory.IDENTIFIER.value == "identifier"
    assert PIICategory.FINANCIAL.value == "financial"
    assert PIICategory.CONTACT.value == "contact"
    assert PIICategory.SPECIAL.value == "special_category"
