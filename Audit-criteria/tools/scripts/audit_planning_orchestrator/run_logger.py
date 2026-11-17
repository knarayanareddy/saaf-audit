"""Per-run audit trail and hand-off artifacts.

Every orchestration run gets its own directory ``runs/<run_id>/`` containing:
- the JSON hand-off artifacts written by each sub-agent call, and
- ``log.jsonl`` — one line per orchestrator turn / tool call (IIA 2340 trail),
- ``summary.json`` — the final combined planning package and verdict.

Implements IIA IPPF 2340 (Engagement Supervision): the run log is the
supervision trail of what each agent did and why.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..mandate_guard import chain_log

logger = logging.getLogger(__name__)

# Run output lives next to this package, not in the repo tree at large.
RUNS_DIR = Path(__file__).parent / "runs"

# Stable, human-readable file names for each stage's hand-off artifact.
_ARTIFACT_NAMES = {
    "run_rcm_builder": "01_rcm.json",
    "run_work_program": "02_work_program.json",
    "run_quality_guard": "03_quality.json",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunLogger:
    """Writes artifacts and the append-only JSONL trail for a single run."""

    def __init__(self, run_id: str, engagement: str) -> None:
        self.run_id = run_id
        self.engagement = engagement
        self.dir = RUNS_DIR / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "log.jsonl"
        self._turn = 0
        # Each line carries the hash of the one before, so edits are detectable.
        self._prev_hash, self._seq = chain_log.GENESIS, 0
        self._write_line({"event": "run_start", "engagement": engagement, "at": _now()})

    def _write_line(self, record: Dict[str, Any]) -> None:
        sealed = chain_log.seal(record, self._prev_hash, self._seq)
        self._prev_hash, self._seq = sealed["hash"], self._seq + 1
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sealed, ensure_ascii=False) + "\n")

    def log_hold_resolved(self, tool_name: str, hold: Dict[str, Any], correction: Optional[str]) -> None:
        """Record that a held hand-off was cleared by a rechecked output, and why."""
        self._write_line({"turn": self._turn, "event": "hold_resolved", "tool": tool_name,
                          "previous_hold": hold, "correction": correction, "at": _now()})

    def log_mandate_check(self, tool_name: str, verdict: Dict[str, Any]) -> None:
        """Record the mandate guard's verdict on a hand-off."""
        self._write_line({"turn": self._turn, "event": "mandate_check", "tool": tool_name,
                          **verdict, "at": _now()})

    def log_reasoning(self, text: str) -> None:
        """Record the orchestrator's one-line rationale for a turn."""
        self._turn += 1
        self._write_line({"turn": self._turn, "event": "orchestrator", "reasoning": text, "at": _now()})

    def log_tool_call(
        self,
        tool_name: str,
        result: Dict[str, Any],
        status: str,
        errors: Optional[list] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> Optional[Path]:
        """Record a sub-agent call and persist its hand-off artifact.

        Attribution: the model that produced the output (or "mock"), and
        fingerprints of exactly what went in and what came out.
        """
        artifact_path: Optional[Path] = None
        name = _ARTIFACT_NAMES.get(tool_name)
        if name and status == "ok":
            artifact_path = self.dir / name
            artifact_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        record: Dict[str, Any] = {
            "turn": self._turn,
            "event": "tool_call",
            "model": model,
            "input_sha256": chain_log.sha256_json(tool_input) if tool_input is not None else None,
            "output_sha256": chain_log.sha256_json(result),
            "tool": tool_name,
            "status": status,
            "at": _now(),
        }
        if tool_name == "run_quality_guard" and status == "ok":
            record["verdict"] = result.get("verdict")
            record["gaps"] = result.get("gaps", [])
        if errors:
            record["errors"] = errors
        if artifact_path is not None:
            record["artifact"] = str(artifact_path.relative_to(self.dir))
        self._write_line(record)
        return artifact_path

    def finalize(self, summary: Dict[str, Any]) -> Path:
        """Write the final combined package and close the trail."""
        self._write_line({"event": "run_end", "final_verdict": summary.get("final_verdict"), "at": _now()})
        # The chain's final hash: record it outside this directory (PR, ticket,
        # portal) to anchor the log against a full rewrite.
        summary = dict(summary, log_final_hash=self._prev_hash)
        summary_path = self.dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Run %s finished: %s", self.run_id, summary.get("final_verdict"))
        return summary_path


def new_run_id(engagement: str) -> str:
    """Build a readable, unique run id from the engagement name and timestamp."""
    slug = "".join(c if c.isalnum() else "-" for c in engagement.lower()).strip("-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{slug or 'run'}-{stamp}"
