"""End-to-end test: auditor requests a customer reimbursement dataset."""

import json
from pathlib import Path

import pytest

from gdpr_agent.models import AuditContext, Role
from gdpr_agent.pipeline import AuditPipeline


def test_e2e_reimbursement_audit(sample_records, tmp_path):
    """Scenario: Auditor requests a customer reimbursement dataset.

    Input: Full dataset with names, emails, IBANs
    Expected: No raw PII exposed, masking consistent, logs complete
    """
    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)

    # Process
    masked_records = pipeline.process_records(sample_records)

    # Validation 1: No raw PII exposed
    raw_pii_values = {
        "Hans Mueller", "Maria Schmidt",
        "hans.mueller@example.com", "maria.schmidt@example.com",
        "DE89370400440532013000", "DE27100777770209299700",
        "+49 170 1234567", "12 345678 A 123",
    }
    for record in masked_records:
        for value in record.values():
            assert str(value) not in raw_pii_values, f"Raw PII leaked: {value}"

    # Validation 2: Safe fields preserved
    assert masked_records[0]["id"] == "RMB-001"
    assert masked_records[0]["amount"] == 245.50
    assert masked_records[0]["category"] == "Travel"
    assert masked_records[1]["department"] == "Marketing"

    # Validation 3: Masking consistent (same input -> same output)
    masked_again = pipeline.process_records(sample_records)
    for r1, r2 in zip(masked_records, masked_again):
        for key in r1:
            assert r1[key] == r2[key], f"Inconsistent masking for {key}"

    # Validation 4: Audit log complete
    entries = pipeline.get_audit_log()
    assert len(entries) >= len(sample_records) * 2  # 2 runs

    # Validation 5: Summary correct
    summary = pipeline.get_summary()
    assert summary["records_processed"] == len(sample_records) * 2
    assert summary["total_pii_fields"] > 0
    assert summary["total_masked"] > 0

    # Validation 6: Log files exist and contain no PII
    log_files = list(tmp_path.glob("audit_*.jsonl"))
    assert len(log_files) >= 1
    for log_file in log_files:
        content = log_file.read_text()
        for pii in raw_pii_values:
            assert pii not in content, f"PII in log: {pii}"


def test_e2e_role_comparison(sample_records, tmp_path):
    """Verify that different roles see different masking levels."""
    results_by_role = {}

    for role in [Role.AUDITOR, Role.DPO, Role.ADMIN]:
        ctx = AuditContext(
            role=role,
            purpose="reimbursement_review",
            legal_basis="legitimate_interest",
            # Only the admin path requires this, but supplying it for every
            # role keeps the loop uniform.
            justification="Comparing masking levels for control testing.",
        )
        log_subdir = tmp_path / role.value
        pipeline = AuditPipeline(audit_context=ctx, log_dir=log_subdir)
        results_by_role[role] = pipeline.process_records(sample_records)

    # Auditor should see more masking than DPO
    auditor_email = results_by_role[Role.AUDITOR][0].get("email", "")
    dpo_email = results_by_role[Role.DPO][0].get("email", "")
    admin_email = results_by_role[Role.ADMIN][0].get("email", "")

    assert auditor_email != dpo_email, "Auditor and DPO should have different masking"
    assert admin_email == "hans.mueller@example.com", "Admin should see raw data"


def test_e2e_audit_trail_is_tamper_evident(sample_records, tmp_path):
    """The trail must be verifiable after the process that wrote it exits."""
    from gdpr_agent.audit_logger import AuditLogger

    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    assert pipeline.verify_audit_log()
    assert AuditLogger.verify_file(pipeline.audit_log_file)

    # Rewrite one entry the way an attacker covering their tracks would.
    lines = pipeline.audit_log_file.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["fields_masked"] = 0
    lines[0] = json.dumps(tampered)
    pipeline.audit_log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert not AuditLogger.verify_file(pipeline.audit_log_file)


def test_e2e_records_which_records_were_processed(sample_records, tmp_path):
    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )
    pipeline = AuditPipeline(audit_context=ctx, log_dir=tmp_path)
    pipeline.process_records(sample_records)

    entries = pipeline.get_audit_log()
    assert [e.record_id for e in entries] == ["RMB-001", "RMB-002"]
    assert all(e.field_names for e in entries)


def test_e2e_requires_a_pseudonymisation_key(sample_records, tmp_path, monkeypatch):
    """Without a key the pipeline refuses to run rather than using a default."""
    from gdpr_agent.config import PSEUDONYM_KEY_ENV_VAR

    monkeypatch.delenv(PSEUDONYM_KEY_ENV_VAR, raising=False)
    ctx = AuditContext(
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        legal_basis="legitimate_interest",
    )
    with pytest.raises(ValueError, match="pseudonymisation key"):
        AuditPipeline(audit_context=ctx, log_dir=tmp_path)
