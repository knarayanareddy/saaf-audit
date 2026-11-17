"""Per-run audit trail: runs/<run_id>/log.jsonl plus stage artifacts.

Same convention as audit_planning_orchestrator/run_logger.py, plus three fixes
for gaps found in that component's AUDIT-CRITERIA.md:
- run ids carry microseconds and a random suffix, and the directory is created
  with exist_ok=False, so two runs can never share a trail (D-5);
- every tool call records sha256 digests of its input and output, and the model
  and prompt hash used (coverage gap 4);
- the orchestrator always finalizes through ``finalize()`` in a ``finally`` (D-4).
"""

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

RUNS_DIR = Path(__file__).parent / "runs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(obj: Any) -> str:
    raw = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def new_run_id(label: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in label.lower()).strip("-")[:40] or "run"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    return f"{slug}-{stamp}-{secrets.token_hex(3)}"


class RunLogger:
    def __init__(self, run_id: str, label: str) -> None:
        self.run_id = run_id
        self.dir = RUNS_DIR / run_id
        self.dir.mkdir(parents=True, exist_ok=False)
        self.log_path = self.dir / "log.jsonl"
        self._seq = 0
        self.closed = False
        self.event("run_start", label=label)

    def event(self, kind: str, **fields: Any) -> None:
        self._seq += 1
        record = {"seq": self._seq, "event": kind, "at": _now(), **fields}
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def artifact(self, name: str, content: Any) -> str:
        path = self.dir / name
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_text(json.dumps(content, indent=2, ensure_ascii=False), encoding="utf-8")
        return name

    def tool_call(self, tool: str, payload: Any, result: Any, status: str,
                  model: Optional[str] = None, prompt_hash: Optional[str] = None,
                  errors: Optional[list] = None, artifact: Optional[str] = None) -> None:
        fields: Dict[str, Any] = {"tool": tool, "status": status,
                                  "input_digest": digest(payload), "output_digest": digest(result)}
        if model:
            fields["model"] = model
        if prompt_hash:
            fields["prompt_hash"] = prompt_hash
        if errors:
            fields["errors"] = errors
        if artifact:
            fields["artifact"] = artifact
        self.event("tool_call", **fields)

    def finalize(self, summary: Dict[str, Any]) -> None:
        if self.closed:
            return
        self.artifact("summary.json", summary)
        self.event("run_end", outcome=summary.get("outcome"))
        self.closed = True
