"""Audit trail for Claude calls made by fieldwork agents.

An internal auditor must be able to trace, for any fieldwork run, which
prompt produced which answer, with which model, at which point in the
pipeline. When a ``ClaudeClient`` is constructed with an ``AuditTrail``, every
call through ``ClaudeClient.message()`` or ``.stream()`` is recorded: the
system/user prompt, model and settings, the raw response text, the model's
extended-thinking trace when ``thinking`` was enabled for that call (see
``record``'s ``reasoning_text``), timing, and token usage.

Quality verdicts (from the ``quality_check`` agent, typically run in bulk via
``orchestrator.review_run``) are recorded separately, in
``runs/<run_id>/quality.jsonl``, linked back to the entry they review by
``entry_id`` — the original trail entry is never mutated.

Human approval decisions live in ``runs/<run_id>/approvals.jsonl``, the same
append-only, entry_id-linked shape. This is not a blocking gate in the sense
of pausing a running pipeline — there is no workflow engine here to pause and
resume. It is the honest equivalent for a synchronous script: nothing an
agent produces is treated as final until an internal auditor records an
explicit decision, and any action that would treat a result as final must
check that decision first (see ``orchestrator.require_approved``) and fail
loudly if it is missing or rejected.

Entries are append-only JSON Lines, one file per run, under ``runs/`` (which
is gitignored). Audit trail content can include real engagement data sent to
or returned by Claude, so ``runs/`` must never be committed — treat it the
same as any other directory holding real client/engagement data.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def new_run_id() -> str:
    """Generate a sortable, unique run id: ``<UTC timestamp>-<8 hex chars>``."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


class AuditTrail:
    """Append-only audit trail for one orchestrator run.

    Share one instance across every ``ClaudeClient`` used in a run (the
    default when ``orchestrator.run_orchestrator`` creates the client) so
    every Claude call across every agent lands in the same
    ``runs/<run_id>/audit_trail.jsonl`` file, in call order.
    """

    APPROVAL_DECISIONS = ("approved", "rejected")

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id or new_run_id()
        self.path = RUNS_DIR / self.run_id / "audit_trail.jsonl"
        self.quality_path = RUNS_DIR / self.run_id / "quality.jsonl"
        self.approvals_path = RUNS_DIR / self.run_id / "approvals.jsonl"

    def record(
        self,
        *,
        agent: str | None,
        system_prompt: str | None,
        user_prompt: str | list[Any],
        model: str,
        max_tokens: int,
        thinking: Any,
        response_text: str,
        started_at: datetime,
        finished_at: datetime,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        stop_reason: str | None = None,
        item_ref: str | None = None,
        reasoning_text: str | None = None,
    ) -> dict:
        """Append one Claude call to the trail and return the recorded entry.

        ``item_ref`` is an optional caller-defined id (e.g. a PBC item id)
        tagging this call as being *about* one specific item, not just made
        by one agent — see ``entries_for_item``. Explicit, not inferred: an
        agent that processes one item per call (``pbc_creation``,
        ``pbc_validation``, ...) passes it through from
        ``ClaudeClient.message(..., item_ref=...)``; an agent with no
        natural single-item scope leaves it ``None``.

        ``reasoning_text`` is the model's extended-thinking trace (see
        ``claude_init.reasoning_from_message``) when ``thinking`` was
        enabled for this call — ``None`` when it wasn't, or when the model
        produced no thinking blocks even though it was. Kept separate from
        ``response_text`` (the actual answer) the same way ``quality.jsonl``
        is kept separate from ``audit_trail.jsonl`` — this is *why* the
        model answered the way it did, not the answer itself, and a reader
        auditing *what happened* should be able to tell the two apart.
        """
        entry = {
            "entry_id": uuid.uuid4().hex,
            "run_id": self.run_id,
            "agent": agent,
            "item_ref": item_ref,
            "timestamp": started_at.isoformat(),
            "latency_ms": round((finished_at - started_at).total_seconds() * 1000, 1),
            "model": model,
            "max_tokens": max_tokens,
            "thinking": thinking,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_text": response_text,
            "reasoning_text": reasoning_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "stop_reason": stop_reason,
        }
        self._append(self.path, entry)
        return entry

    def entries(self) -> list[dict]:
        """Read back every entry recorded so far, in call order."""
        return self._read(self.path)

    def entries_for_item(self, item_ref: str) -> list[dict]:
        """Every entry tagged with ``item_ref``, in call order.

        Only finds entries recorded with an explicit ``item_ref`` — older
        entries (recorded before this field existed) or entries from agents
        that don't tag one are simply absent, not guessed at positionally.
        """
        return [e for e in self.entries() if e.get("item_ref") == item_ref]

    def record_quality(
        self, *, entry_id: str, verdict: dict, reviewed_at: datetime | None = None
    ) -> dict:
        """Record a quality_check verdict for the trail entry ``entry_id``.

        Does not touch the original entry — quality review is a separate,
        append-only layer, the same way a review note in a work paper never
        overwrites the item it comments on.
        """
        quality_entry = {
            "run_id": self.run_id,
            "entry_id": entry_id,
            "reviewed_at": (reviewed_at or datetime.now(timezone.utc)).isoformat(),
            "review": verdict,
        }
        self._append(self.quality_path, quality_entry)
        return quality_entry

    def quality_entries(self) -> list[dict]:
        """Read back every quality verdict recorded so far, in review order."""
        return self._read(self.quality_path)

    def record_approval(
        self,
        *,
        entry_id: str,
        decision: str,
        reviewer: str,
        role: str | None = None,
        comment: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> dict:
        """Record an internal auditor's approve/reject decision on ``entry_id``.

        ``reviewer`` identifies the auditor (name or email) — required, so a
        decision is never anonymous. ``role`` (e.g. "auditor" vs.
        "senior_auditor") is optional metadata only — it is not a second
        approval tier the way ``require_approved`` gates finalization; there
        is one flat approved/rejected status per entry regardless of who
        (or which role) recorded it. Recording a second decision for the
        same ``entry_id`` (e.g. approving after an earlier rejection was
        addressed) does not overwrite the first — ``approval_status`` always
        reflects the most recent one, but the full history stays in
        ``approvals.jsonl``.
        """
        if decision not in self.APPROVAL_DECISIONS:
            raise ValueError(
                f"decision must be one of {self.APPROVAL_DECISIONS}, got {decision!r}"
            )
        approval_entry = {
            "run_id": self.run_id,
            "entry_id": entry_id,
            "decision": decision,
            "reviewer": reviewer,
            "role": role,
            "comment": comment,
            "reviewed_at": (reviewed_at or datetime.now(timezone.utc)).isoformat(),
        }
        self._append(self.approvals_path, approval_entry)
        return approval_entry

    def approvals(self) -> list[dict]:
        """Read back every approval decision recorded so far, in review order."""
        return self._read(self.approvals_path)

    def approval_status(self, entry_id: str) -> str:
        """The most recent approval decision for ``entry_id``, or "pending"."""
        latest = self.latest_approval(entry_id)
        return latest["decision"] if latest else "pending"

    def latest_approval(self, entry_id: str) -> dict | None:
        """The most recent full approval record for ``entry_id``, or ``None``."""
        matching = [a for a in self.approvals() if a["entry_id"] == entry_id]
        return matching[-1] if matching else None

    @staticmethod
    def _append(path: Path, entry: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _read(path: Path) -> list[dict]:
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
