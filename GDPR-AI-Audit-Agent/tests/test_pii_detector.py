import pytest

from gdpr_agent.models import PIICategory
from gdpr_agent.pii_detector import detect_pii_in_record


def test_detects_email():
    record = {"email": "hans@example.com", "id": "RMB-001"}
    fields = detect_pii_in_record(record)
    emails = [f for f in fields if f.field_name == "email"]
    assert len(emails) == 1
    assert emails[0].category == PIICategory.CONTACT
    assert emails[0].confidence >= 0.9


def test_detects_iban():
    record = {"iban": "DE89370400440532013000"}
    fields = detect_pii_in_record(record)
    ibans = [f for f in fields if f.field_name == "iban"]
    assert len(ibans) == 1
    assert ibans[0].category == PIICategory.FINANCIAL


def test_detects_name():
    record = {"employee_name": "Hans Mueller"}
    fields = detect_pii_in_record(record)
    names = [f for f in fields if f.field_name == "employee_name"]
    assert len(names) == 1
    assert names[0].category == PIICategory.IDENTIFIER


def test_ignores_safe_fields():
    record = {"id": "RMB-001", "amount": 245.50, "category": "Travel"}
    fields = detect_pii_in_record(record)
    assert len(fields) == 0


def test_detects_phone():
    record = {"phone": "+49 170 1234567"}
    fields = detect_pii_in_record(record)
    phones = [f for f in fields if f.field_name == "phone"]
    assert len(phones) == 1
    assert phones[0].category == PIICategory.CONTACT


def test_detects_multiple_pii_fields(sample_records):
    fields = detect_pii_in_record(sample_records[0])
    field_names = {f.field_name for f in fields}
    assert "employee_name" in field_names
    assert "email" in field_names
    assert "iban" in field_names
    assert "id" not in field_names
    assert "amount" not in field_names


def test_date_field_is_not_reported_as_a_phone_number():
    """"2026-01-15" is digit-dense enough to trip a loose phone pattern."""
    record = {"processed_on": "2026-01-15"}
    assert detect_pii_in_record(record) == []


def test_safe_field_name_still_has_its_value_inspected():
    """A column called `id` holding an IBAN is still an IBAN."""
    record = {"id": "DE89370400440532013000"}
    fields = detect_pii_in_record(record)
    assert len(fields) == 1
    assert fields[0].category == PIICategory.FINANCIAL


def test_safe_field_with_non_pii_value_is_still_ignored():
    record = {"id": "RMB-001", "amount": 245.50, "category": "Travel"}
    assert detect_pii_in_record(record) == []


def test_detects_valid_bsn():
    record = {"citizen_number": "111222333"}
    fields = detect_pii_in_record(record)
    assert len(fields) == 1
    assert fields[0].category == PIICategory.IDENTIFIER
    assert "bsn" in fields[0].matched_patterns


def test_nine_digit_number_failing_the_11_proef_is_not_a_bsn():
    """Order numbers and cost centres are nine digits too.

    Such a value may still be picked up by the (deliberately permissive) phone
    heuristic — over-detection is the safe direction for a masker — but it must
    not be reported as a national identifier.
    """
    record = {"order_number": "123456789"}
    fields = detect_pii_in_record(record)
    for field in fields:
        assert "bsn" not in field.matched_patterns
        assert field.category != PIICategory.IDENTIFIER


def test_detects_pii_nested_in_objects():
    record = {"id": "RMB-003", "employee": {"contact": {"email": "hans@example.com"}}}
    fields = detect_pii_in_record(record)
    names = {f.field_name for f in fields}
    assert "employee.contact.email" in names


def test_detects_pii_nested_in_lists():
    record = {"id": "RMB-004", "recipients": ["hans@example.com", "maria@example.com"]}
    fields = detect_pii_in_record(record)
    names = {f.field_name for f in fields}
    assert names == {"recipients.0", "recipients.1"}


def test_reports_every_pattern_that_fired():
    """A national ID that also looks like a phone number is an identifier."""
    record = {"national_id": "12 345678 A 123"}
    fields = detect_pii_in_record(record)
    assert len(fields) == 1
    assert fields[0].category == PIICategory.IDENTIFIER
    assert "ssn" in fields[0].matched_patterns
