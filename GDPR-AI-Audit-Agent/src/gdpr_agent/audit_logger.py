"""Tamper-evident audit trail with chain-of-thought logging."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from gdpr_agent.models import GENESIS_HASH, AuditRecord, Role


def compute_entry_hash(record: AuditRecord) -> str:
    """Hash an entry over every field except the hash itself.

    Canonical JSON (sorted keys, no incidental whitespace) so the digest is
    reproducible by any verifier, not just this process.
    """
    payload = record.model_dump(mode="json", exclude={"entry_hash"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class AuditLogger:
    """Append-only audit logger that persists to JSONL files.

    Each entry stores the hash of its predecessor, so the file is not merely
    written in append mode but verifiably ordered: editing or deleting an entry
    breaks every hash that follows it. `verify_chain` and `verify_file` expose
    that check.
    """

    def __init__(self, log_dir: Path):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[AuditRecord] = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._log_file = self._log_dir / f"audit_{timestamp}.jsonl"

    @property
    def log_file(self) -> Path:
        return self._log_file

    def log(
        self,
        action: str,
        role: Role,
        purpose: str,
        fields_detected: int,
        fields_masked: int,
        reasoning: str,
        record_id: str | None = None,
        field_names: list[str] | None = None,
        justification: str | None = None,
    ) -> AuditRecord:
        """Create and persist an audit log entry, linked to its predecessor."""
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH

        record = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            role=role,
            purpose=purpose,
            fields_detected=fields_detected,
            fields_masked=fields_masked,
            reasoning=reasoning,
            sequence=len(self._entries),
            record_id=record_id,
            field_names=list(field_names or []),
            justification=justification,
            prev_hash=prev_hash,
        )
        record.entry_hash = compute_entry_hash(record)
        self._entries.append(record)

        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        return record

    def get_entries(self) -> list[AuditRecord]:
        """Return all entries from the current session."""
        return list(self._entries)

    @staticmethod
    def verify_chain(entries: list[AuditRecord]) -> bool:
        """True if every entry's hash and back-link are intact."""
        expected_prev = GENESIS_HASH
        for index, entry in enumerate(entries):
            if entry.sequence != index:
                return False
            if entry.prev_hash != expected_prev:
                return False
            if entry.entry_hash != compute_entry_hash(entry):
                return False
            expected_prev = entry.entry_hash
        return True

    @classmethod
    def read_file(cls, path: Path) -> list[AuditRecord]:
        """Load a persisted JSONL trail back into records."""
        entries: list[AuditRecord] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(AuditRecord.model_validate_json(line))
        return entries

    @classmethod
    def verify_file(cls, path: Path) -> bool:
        """Verify a trail on disk, independently of the process that wrote it."""
        return cls.verify_chain(cls.read_file(path))
