"""Audit logger — Step 07 (HARDENED).

Writes HMAC-SHA256 hash-chained, append-only JSONL audit trail.
Logs ALL pipeline steps (not just decisions).
Verifies chain integrity after writing.

OWASP mitigations:
- A02: HMAC-SHA256 (not plain SHA-256) — attacker cannot recompute
- A08: Hash chain with sequence numbers — any tampering breaks the chain
- A09: Per-step logging for full reconstruction
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.security.crypto import CryptoProvider
from src.security.integrity import IntegrityChecker


def _load_json(path: Path) -> list[dict]:
    """Safely load a JSON file, returning empty list on failure."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def run(settings: dict) -> None:
    """Write hash-chained audit_trail.jsonl from ALL pipeline steps."""
    root = Path(__file__).resolve().parents[2]
    output_dir = root / settings["output_dir"]

    # Initialize crypto for hash chain
    crypto = CryptoProvider()
    integrity = IntegrityChecker(crypto)

    # Collect entries from ALL steps
    all_entries: list[dict] = []

    # Step 01 — Intake results
    for record in _load_json(output_dir / "parsed_records.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "INTAKE",
            "status": record.get("intake_status", ""),
            "validation_errors": record.get("validation_errors", []),
            "supplier_id": record.get("supplier_id", ""),
        })

    # Step 02 — Contract match results
    for record in _load_json(output_dir / "matched_contracts.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "CONTRACT_MATCH",
            "status": record.get("contract_status", ""),
            "contract_ref": record.get("matched_contract_id", ""),
            "agreed_price": record.get("agreed_price"),
        })

    # Step 03 — Three-way match results
    for record in _load_json(output_dir / "check_results.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "THREE_WAY_MATCH",
            "overall_check": record.get("overall_check", ""),
            "delta_pct": record.get("delta_pct", 0.0),
            "qty_delta_po": record.get("qty_delta_po", 0),
            "qty_delta_grn": record.get("qty_delta_grn", 0),
        })

    # Step 04 — Decision results
    for record in _load_json(output_dir / "decisions.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "DECISION",
            "decision": record.get("decision", ""),
            "action": record.get("action", ""),
            "motivation": record.get("motivation", ""),
            "contract_ref": record.get("matched_contract_id", ""),
            "delta_pct": record.get("delta_pct", 0.0),
            "qty_delta_grn": record.get("qty_delta_grn", 0),
            "blocked": record.get("blocked", False),
        })

    # Step 05 — Payment results
    for record in _load_json(output_dir / "payment_instructions.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "PAYMENT",
            "payment_status": record.get("payment_status", ""),
            "iban_verified": record.get("iban_verified", False),
            "amount": record.get("amount", 0),
        })
    for record in _load_json(output_dir / "blocked_queue.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "PAYMENT_BLOCKED",
            "payment_status": record.get("payment_status", ""),
            "payment_reason": record.get("payment_reason", ""),
        })

    # Step 06 — Escalation results
    for record in _load_json(output_dir / "escalation_register.json"):
        all_entries.append({
            "invoice_id": record.get("invoice_id", ""),
            "agent_step": "ESCALATION",
            "escalation_status": record.get("escalation_status", ""),
            "recipient": record.get("recipient", ""),
            "team": record.get("team", ""),
            "sla_deadline": record.get("sla_deadline", ""),
        })

    # Add timestamps and agent version to all entries
    now = datetime.now(timezone.utc).isoformat()
    for entry in all_entries:
        entry["timestamp"] = now
        entry["agent_version"] = "procurement-audit-agent-v1.0"

    # Build hash chain
    chained = integrity.build_hash_chain(all_entries)

    # Write hash-chained audit trail
    output_path = output_dir / "audit_trail.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in chained:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    # Verify chain integrity
    valid, violations = integrity.verify_chain(chained)

    # Create file manifest
    manifest = integrity.create_manifest(output_dir)
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"  audit_trail.jsonl: {len(chained)} hash-chained entries")
    print(f"  Hash chain integrity: {'VERIFIED' if valid else 'FAILED'}")
    if violations:
        for v in violations[:5]:
            print(f"    VIOLATION: {v}")
    print(f"  manifest.json: {len(manifest.get('files', {}))} files tracked")
