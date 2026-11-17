"""Per-run directory and append-only JSONL trail.

Same pattern as audit_planning_orchestrator/run_logger.py, plus a dedicated record for every
Claude call (requested and served model, response id, prompt and payload hashes). The rater
holds itself to the control it audits: every judgment links back to its instruction version.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from . import config

logger = logging.getLogger(__name__)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_run_id(mode: str) -> str:
    """Return ``<mode>-YYYYMMDD-HHMMSS`` (mode is sim, local or org)."""
    return f"{mode}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


class RunLog:
    """Owns ``runs/<run_id>/`` and its ``log.jsonl`` trail."""

    def __init__(self, run_id: str, runs_dir: Optional[Path] = None) -> None:
        self.run_id = run_id
        self.dir = (runs_dir or config.RUNS_DIR) / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "log.jsonl"

    def event(self, event: str, **fields: Any) -> None:
        record: Dict[str, Any] = {"event": event, "at": now_iso()}
        record.update(fields)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def llm_call(
        self,
        unit_id: str,
        stage: str,
        model_requested: str,
        model_served: Optional[str],
        response_id: Optional[str],
        system_prompt: str,
        payload: str,
        response_text: str,
        usage: Optional[Dict[str, Any]] = None,
        stop_reason: Optional[str] = None,
        cached: bool = False,
        errors: Optional[list] = None,
    ) -> None:
        self.event(
            "llm_call",
            unit=unit_id,
            stage=stage,
            model_requested=model_requested,
            model_served=model_served,
            response_id=response_id,
            system_sha256=sha256_text(system_prompt),
            payload_sha256=sha256_text(payload),
            response_sha256=sha256_text(response_text),
            usage=usage or {},
            stop_reason=stop_reason,
            cached=cached,
            errors=errors or [],
        )

    def write_json(self, relative: str, data: Any) -> Path:
        path = self.dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_text(self, relative: str, text: str) -> Path:
        path = self.dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
