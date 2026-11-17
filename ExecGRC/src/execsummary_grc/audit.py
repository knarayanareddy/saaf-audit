from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_default(value: Any) -> str:
    return str(value)


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=_json_default, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditTrail:
    def __init__(self, output_dir: Path, run_id: str, hash_chain: bool = True) -> None:
        self.output_dir = output_dir
        self.run_id = run_id
        self.hash_chain = hash_chain
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.output_dir / "audit_trail.ndjson"
        self.events: list[dict[str, Any]] = []
        self._previous_hash = "0" * 64
        self.path.write_text("", encoding="utf-8")

    def record(
        self,
        step: str,
        action: str,
        *,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        decision: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": len(self.events) + 1,
            "timestamp_utc": _utc_now(),
            "run_id": self.run_id,
            "step": step,
            "action": action,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "decision": decision or {},
            "artifacts": artifacts or [],
            "previous_hash": self._previous_hash if self.hash_chain else None,
        }
        event["event_hash"] = _hash_payload(event)
        self._previous_hash = event["event_hash"]
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=_json_default) + "\n")
        return event

    @property
    def current_hash(self) -> str:
        return self._previous_hash

    def write_summary(self) -> Path:
        lines = [
            "# Audit Summary",
            "",
            f"- Run id: `{self.run_id}`",
            f"- Events: {len(self.events)}",
            f"- Hash chain enabled: {self.hash_chain}",
            f"- Final event hash: `{self.current_hash}`",
            "",
            "## Steps",
            "",
        ]
        for event in self.events:
            lines.append(
                f"{event['event_id']}. `{event['step']}` - {event['action']} "
                f"(`{event['event_hash']}`)"
            )
        lines.extend(
            [
                "",
                "## Verification Note",
                "",
                "The NDJSON trail is append-only for this run. Recompute each event hash from the "
                "canonical event payload and compare `previous_hash` with the prior `event_hash` "
                "to detect later edits.",
                "",
            ]
        )
        summary_path = self.output_dir / "audit_summary.md"
        summary_path.write_text("\n".join(lines), encoding="utf-8")
        return summary_path
