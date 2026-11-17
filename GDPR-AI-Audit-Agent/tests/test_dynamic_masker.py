from gdpr_agent.dynamic_masker import mask_value
from gdpr_agent.models import MaskingLevel, MaskingResult, PIICategory


def test_full_mask_email():
    result = mask_value("hans.mueller@example.com", "email", PIICategory.CONTACT, MaskingLevel.FULL)
    assert result.masked_value == "h***@***.com"
    assert result.masking_method == "redacted"
    assert "hans" not in result.masked_value


def test_partial_mask_email():
    result = mask_value("hans.mueller@example.com", "email", PIICategory.CONTACT, MaskingLevel.PARTIAL)
    assert "@" in result.masked_value
    assert result.masked_value != "hans.mueller@example.com"
    assert result.masking_method == "partial"


def test_no_mask():
    result = mask_value("hans.mueller@example.com", "email", PIICategory.CONTACT, MaskingLevel.NONE)
    assert result.masked_value == "hans.mueller@example.com"
    assert result.masking_method == "none"


def test_full_mask_iban():
    result = mask_value("DE89370400440532013000", "iban", PIICategory.FINANCIAL, MaskingLevel.FULL)
    assert result.masked_value.startswith("DE")
    assert "****" in result.masked_value
    assert result.masking_method == "redacted"


def test_full_mask_name():
    result = mask_value("Hans Mueller", "employee_name", PIICategory.IDENTIFIER, MaskingLevel.FULL)
    assert result.masked_value == "[REDACTED]"
    assert result.masking_method == "redacted"


def test_partial_mask_name():
    result = mask_value("Hans Mueller", "employee_name", PIICategory.IDENTIFIER, MaskingLevel.PARTIAL)
    assert result.masked_value == "H*** M***"
    assert result.masking_method == "partial"
