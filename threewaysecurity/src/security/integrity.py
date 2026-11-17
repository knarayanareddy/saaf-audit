"""Integrity checker — OWASP A08: Data Integrity Failures Prevention.

HMAC-SHA256 hash chain for tamper detection on all data files.
Each record is chained to its predecessor; any modification breaks the chain.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class IntegrityChecker:
    """Hash chain and file manifest for tamper detection."""

    def __init__(self, crypto) -> None:
        """Initialize with a CryptoProvider instance."""
        self._crypto = crypto

    def build_hash_chain(self, records: list[dict]) -> list[dict]:
        """Add _hash, _prev_hash, _sequence_no to each record."""
        genesis_hash = self._crypto.hmac_sign_string("GENESIS")
        prev_hash = genesis_hash
        chained: list[dict] = []

        for i, record in enumerate(records):
            # Remove any existing chain fields
            clean = {k: v for k, v in record.items() if not k.startswith("_")}
            clean["_sequence_no"] = i + 1
            clean["_prev_hash"] = prev_hash

            # Compute hash of the record (excluding _hash itself)
            record_hash = self._crypto.hmac_sign_dict(clean)
            clean["_hash"] = record_hash

            prev_hash = record_hash
            chained.append(clean)

        return chained

    def verify_chain(self, records: list[dict]) -> tuple[bool, list[str]]:
        """Verify hash chain integrity. Returns (valid, list_of_violations)."""
        violations: list[str] = []

        if not records:
            return True, []

        genesis_hash = self._crypto.hmac_sign_string("GENESIS")
        expected_prev = genesis_hash

        for i, record in enumerate(records):
            seq = record.get("_sequence_no", -1)

            # Check sequence continuity
            if seq != i + 1:
                violations.append(f"Sequence gap at position {i}: expected {i + 1}, got {seq}")

            # Check prev_hash linkage
            if record.get("_prev_hash") != expected_prev:
                violations.append(f"Chain broken at sequence {seq}: _prev_hash mismatch")

            # Recompute hash
            verify_record = {k: v for k, v in record.items() if k != "_hash"}
            expected_hash = self._crypto.hmac_sign_dict(verify_record)
            actual_hash = record.get("_hash", "")

            if expected_hash != actual_hash:
                violations.append(f"Hash mismatch at sequence {seq}: record tampered")

            expected_prev = actual_hash

        return len(violations) == 0, violations

    def create_manifest(self, directory: Path) -> dict:
        """Create HMAC manifest of all files in directory."""
        manifest: dict = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {},
        }

        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file() and file_path.name != "manifest.json":
                rel = str(file_path.relative_to(directory))
                manifest["files"][rel] = {
                    "hash": self._crypto.hash_file(file_path),
                    "size": file_path.stat().st_size,
                }

        return manifest

    def verify_manifest(self, manifest: dict, directory: Path) -> tuple[bool, list[str]]:
        """Verify current files against stored manifest."""
        violations: list[str] = []

        for rel_path, info in manifest.get("files", {}).items():
            file_path = directory / rel_path
            if not file_path.exists():
                violations.append(f"Missing file: {rel_path}")
                continue

            current_hash = self._crypto.hash_file(file_path)
            if current_hash != info["hash"]:
                violations.append(f"Tampered file: {rel_path}")

        return len(violations) == 0, violations
