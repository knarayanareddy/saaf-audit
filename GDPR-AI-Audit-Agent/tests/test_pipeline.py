from pathlib import Path

from gdpr_agent.models import AuditContext, MaskingLevel, Role
from gdpr_agent.pipeline import AuditPipeline


def test_pipeline_masks_all_pii_for_auditor(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    assert len(results) == len(sample_records)
    for record in results:
        # No raw emails should survive
        for value in record.values():
            assert "@example.com" not in str(value)


def test_pipeline_preserves_safe_fields(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    assert results[0]["id"] == "RMB-001"
    assert results[0]["amount"] == 245.50
    assert results[0]["category"] == "Travel"


def test_pipeline_dpo_sees_partial_masking(sample_records, tmp_path):
    ctx = AuditContext(role=Role.DPO, purpose="compliance_check", legal_basis="legal_obligation")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    # DPO should see partial info (not fully redacted)
    email_val = str(results[0].get("email", ""))
    assert email_val != "hans.mueller@example.com"  # Not raw
    assert email_val != "[REDACTED]"  # Not fully masked


def test_pipeline_creates_audit_log(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    entries = pipeline.get_audit_log()
    assert len(entries) > 0


def test_pipeline_generates_summary(sample_records, tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    summary = pipeline.get_summary()
    assert "records_processed" in summary
    assert "total_pii_fields" in summary
    assert "total_masked" in summary
    assert summary["records_processed"] == 2


def test_pipeline_pseudonymizes_required_fields(sample_records, tmp_path):
    """Required PII fields should be pseudonymized (reversible) for auditors."""
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    results = pipeline.process_records(sample_records)

    # IBAN is Required for reimbursement_review — should be pseudonymized
    iban_val = results[0].get("iban", "")
    assert iban_val.startswith("PSE-"), "Required fields should be pseudonymized"
    assert iban_val != "DE89370400440532013000"


def test_pipeline_masks_pii_nested_in_objects(tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    record = {"id": "RMB-100", "employee": {"contact": {"email": "hans@example.com"}}}

    result = pipeline.process_record(record)

    assert result["employee"]["contact"]["email"] != "hans@example.com"
    assert result["id"] == "RMB-100"


def test_pipeline_does_not_mutate_the_input_record(tmp_path):
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    record = {"id": "RMB-101", "employee": {"contact": {"email": "hans@example.com"}}}

    pipeline.process_record(record)

    assert record["employee"]["contact"]["email"] == "hans@example.com"


def test_pipeline_is_one_way_by_default(sample_records, tmp_path):
    """Without a vault the pipeline retains no re-identification data."""
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    assert not pipeline._pseudonymizer.is_reversible


def test_pipeline_with_vault_supports_reidentification(sample_records, tmp_path):
    from gdpr_agent.pseudonymizer import PseudonymVault

    vault = PseudonymVault()
    ctx = AuditContext(role=Role.AUDITOR, purpose="reimbursement_review", legal_basis="legitimate_interest")
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path, vault=vault)
    results = pipeline.process_records(sample_records)

    token = results[0]["iban"]
    assert token.startswith("PSE-")
    restored = vault.resolve(token, role=Role.DPO, justification="SAR-2026-014")
    assert restored == "DE89370400440532013000"
