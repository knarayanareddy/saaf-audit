from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import json
import pytest

from agents.document_validity_agent import run_document_validity_agent, _assess_document


TODAY = date(2026, 4, 21)


def _make_mock_response(records: list) -> MagicMock:
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(records))]
    return mock_message


# --- Unit tests for _assess_document (no API calls) ---

def test_soc2_within_validity_window():
    record = {
        "doc_type": "SOC2_TYPE_II",
        "title": "SOC 2 Type II Report",
        "audit_period_end": "2025-10-01",  # 202 days ago
    }
    findings = _assess_document(record, TODAY)
    assert len(findings) == 1
    assert findings[0].status == "Compliant"
    assert findings[0].severity == "Info"
    assert findings[0].framework == "Document Validity"
    assert findings[0].control_id == "SOC2-PERIOD"


def test_soc2_expired_over_12_months():
    old_date = (TODAY - timedelta(days=400)).isoformat()
    record = {
        "doc_type": "SOC2_TYPE_II",
        "title": "SOC 2 Type II Report",
        "audit_period_end": old_date,
    }
    findings = _assess_document(record, TODAY)
    assert len(findings) == 1
    assert findings[0].status == "Gap"
    assert findings[0].severity == "High"


def test_soc2_missing_date_returns_partial_low():
    record = {
        "doc_type": "SOC2_TYPE_II",
        "title": "SOC 2 Type II Report",
        "audit_period_end": None,
    }
    findings = _assess_document(record, TODAY)
    assert len(findings) == 1
    assert findings[0].status == "Partial"
    assert findings[0].severity == "Low"


def test_iso_cert_valid():
    record = {
        "doc_type": "ISO_27001",
        "title": "ISO 27001 Certificate",
        "certificate_expiry": "2027-06-30",
        "last_surveillance_audit": None,
    }
    findings = _assess_document(record, TODAY)
    assert len(findings) == 1
    assert findings[0].status == "Compliant"
    assert findings[0].severity == "Info"
    assert findings[0].control_id == "ISO-CERT-EXPIRY"


def test_iso_cert_expired():
    record = {
        "doc_type": "ISO_27001",
        "title": "ISO 27001 Certificate",
        "certificate_expiry": "2025-01-01",  # expired
        "last_surveillance_audit": None,
    }
    findings = _assess_document(record, TODAY)
    assert any(f.status == "Gap" and f.severity == "High" for f in findings)


def test_iso_cert_expiring_within_90_days():
    expiry = (TODAY + timedelta(days=45)).isoformat()
    record = {
        "doc_type": "ISO_27001",
        "title": "ISO 27001 Certificate",
        "certificate_expiry": expiry,
        "last_surveillance_audit": None,
    }
    findings = _assess_document(record, TODAY)
    assert any(f.status == "Partial" and f.severity == "Medium" for f in findings)


def test_iso_surveillance_audit_overdue():
    expiry = "2027-06-30"
    old_surv = (TODAY - timedelta(days=400)).isoformat()
    record = {
        "doc_type": "ISO_27001",
        "title": "ISO 27001 Certificate",
        "certificate_expiry": expiry,
        "last_surveillance_audit": old_surv,
    }
    findings = _assess_document(record, TODAY)
    # Should have cert finding (Compliant) + surveillance finding (Gap/High)
    control_ids = [f.control_id for f in findings]
    assert "ISO-CERT-EXPIRY" in control_ids
    assert "ISO-SURVEILLANCE" in control_ids
    surv = next(f for f in findings if f.control_id == "ISO-SURVEILLANCE")
    assert surv.status == "Gap"
    assert surv.severity == "High"


def test_dora_questionnaire_within_window():
    record = {
        "doc_type": "DORA_QUESTIONNAIRE",
        "title": "DORA ICT Risk Questionnaire",
        "completion_date": "2026-03-01",  # 51 days ago
    }
    findings = _assess_document(record, TODAY)
    assert findings[0].status == "Compliant"
    assert findings[0].control_id == "DORA-Q-CURRENCY"


def test_vendor_questionnaire_expired():
    old_date = (TODAY - timedelta(days=400)).isoformat()
    record = {
        "doc_type": "VENDOR_QUESTIONNAIRE",
        "title": "Vendor Security Questionnaire",
        "completion_date": old_date,
    }
    findings = _assess_document(record, TODAY)
    assert findings[0].status == "Gap"
    assert findings[0].severity == "High"
    assert findings[0].control_id == "VENDOR-Q-CURRENCY"


# --- Integration test with mocked Claude API ---

@patch("anthropic.Anthropic")
def test_run_document_validity_agent_multiple_docs(mock_anthropic_cls):
    records = [
        {
            "doc_type": "SOC2_TYPE_II",
            "title": "SOC 2 Type II Report",
            "audit_period_end": "2025-10-01",
        },
        {
            "doc_type": "ISO_27001",
            "title": "ISO 27001 Certificate",
            "certificate_expiry": "2027-06-30",
            "last_surveillance_audit": "2025-06-14",
        },
        {
            "doc_type": "DORA_QUESTIONNAIRE",
            "title": "DORA Questionnaire",
            "completion_date": "2026-03-01",
        },
    ]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response(records)
    mock_anthropic_cls.return_value = mock_client

    findings = run_document_validity_agent("sample vendor docs text", TODAY)

    assert len(findings) >= 3
    frameworks = {f.framework for f in findings}
    assert frameworks == {"Document Validity"}
    statuses = {f.status for f in findings}
    assert "Compliant" in statuses
