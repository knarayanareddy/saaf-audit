from gdpr_agent.field_classifier import classify_fields
from gdpr_agent.models import FieldClassification, PIICategory, PIIField


def test_financial_field_required_for_reimbursement():
    fields = [
        PIIField(field_name="amount", value="245.50", category=PIICategory.FINANCIAL, confidence=0.9),
        PIIField(field_name="iban", value="DE89...", category=PIICategory.FINANCIAL, confidence=0.95),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    iban_field = next(f for f in result if f.field_name == "iban")
    assert iban_field.classification == FieldClassification.REQUIRED


def test_name_optional_for_reimbursement():
    fields = [
        PIIField(field_name="employee_name", value="Hans", category=PIICategory.IDENTIFIER, confidence=0.9),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    assert result[0].classification == FieldClassification.OPTIONAL


def test_ssn_excessive_for_reimbursement():
    fields = [
        PIIField(field_name="ssn", value="12 345678 A 123", category=PIICategory.IDENTIFIER, confidence=0.95),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    assert result[0].classification == FieldClassification.EXCESSIVE


def test_special_category_always_excessive_unless_justified():
    fields = [
        PIIField(field_name="health_condition", value="diabetes", category=PIICategory.SPECIAL, confidence=0.9),
    ]
    result = classify_fields(fields, purpose="reimbursement_review")
    assert result[0].classification == FieldClassification.EXCESSIVE
