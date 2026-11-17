import json

from gdpr_agent.audit_logger import AuditLogger
from gdpr_agent.models import GENESIS_HASH, Role


def test_log_creates_entry(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    logger.log(
        action="pii_detection",
        role=Role.AUDITOR,
        purpose="reimbursement_review",
        fields_detected=5,
        fields_masked=4,
        reasoning="Detected 5 PII fields, masked 4 per auditor role policy.",
    )
    logs = logger.get_entries()
    assert len(logs) == 1
    assert logs[0].action == "pii_detection"
    assert logs[0].fields_detected == 5


def test_log_persists_to_file(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    logger.log(
        action="masking",
        role=Role.DPO,
        purpose="compliance_check",
        fields_detected=3,
        fields_masked=2,
        reasoning="DPO role: partial masking applied.",
    )
    log_files = list(tmp_path.glob("audit_*.jsonl"))
    assert len(log_files) == 1
    with open(log_files[0]) as f:
        line = f.readline()
        entry = json.loads(line)
        assert entry["action"] == "masking"
        assert entry["role"] == "dpo"


def test_multiple_entries(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    for i in range(3):
        logger.log(
            action=f"step_{i}",
            role=Role.AUDITOR,
            purpose="review",
            fields_detected=i,
            fields_masked=i,
            reasoning=f"Step {i}",
        )
    assert len(logger.get_entries()) == 3


def test_log_contains_no_pii(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    logger.log(
        action="detection",
        role=Role.AUDITOR,
        purpose="review",
        fields_detected=1,
        fields_masked=1,
        reasoning="Masked email field.",
    )
    log_files = list(tmp_path.glob("audit_*.jsonl"))
    content = log_files[0].read_text()
    assert "hans" not in content.lower()
    assert "@" not in content


def test_entries_are_hash_chained(tmp_path):
    """Each entry links to its predecessor, so the order is verifiable."""
    logger = AuditLogger(log_dir=tmp_path)
    for i in range(3):
        logger.log(
            action=f"step_{i}",
            role=Role.AUDITOR,
            purpose="review",
            fields_detected=i,
            fields_masked=i,
            reasoning=f"Step {i}",
        )
    entries = logger.get_entries()
    assert entries[0].prev_hash == GENESIS_HASH
    for earlier, later in zip(entries, entries[1:]):
        assert later.prev_hash == earlier.entry_hash
    assert AuditLogger.verify_chain(entries)


def test_verify_file_accepts_an_untouched_trail(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    for i in range(3):
        logger.log(
            action=f"step_{i}",
            role=Role.DPO,
            purpose="review",
            fields_detected=i,
            fields_masked=i,
            reasoning=f"Step {i}",
        )
    assert AuditLogger.verify_file(logger.log_file)


def test_editing_an_entry_is_detected(tmp_path):
    """The point of the chain: a silent edit no longer passes verification."""
    logger = AuditLogger(log_dir=tmp_path)
    for i in range(3):
        logger.log(
            action=f"step_{i}",
            role=Role.AUDITOR,
            purpose="review",
            fields_detected=i,
            fields_masked=i,
            reasoning=f"Step {i}",
        )

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[1])
    tampered["fields_masked"] = 999
    lines[1] = json.dumps(tampered)
    logger.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert not AuditLogger.verify_file(logger.log_file)


def test_deleting_an_entry_is_detected(tmp_path):
    logger = AuditLogger(log_dir=tmp_path)
    for i in range(3):
        logger.log(
            action=f"step_{i}",
            role=Role.AUDITOR,
            purpose="review",
            fields_detected=i,
            fields_masked=i,
            reasoning=f"Step {i}",
        )

    lines = logger.log_file.read_text(encoding="utf-8").splitlines()
    del lines[1]
    logger.log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert not AuditLogger.verify_file(logger.log_file)


def test_log_records_which_record_and_fields(tmp_path):
    """Counts alone cannot evidence what was processed."""
    logger = AuditLogger(log_dir=tmp_path)
    entry = logger.log(
        action="process_record",
        role=Role.AUDITOR,
        purpose="review",
        fields_detected=2,
        fields_masked=2,
        reasoning="Masked 2 fields.",
        record_id="RMB-001",
        field_names=["email", "iban"],
    )
    assert entry.record_id == "RMB-001"
    assert entry.field_names == ["email", "iban"]
