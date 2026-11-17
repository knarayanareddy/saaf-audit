"""Audit Copilot — chat + proposal persistence. Owns its own DB sessions (called
both from request handlers and from the stream-completion callback, which
outlives the request's own session)."""
import json
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from models.copilot import CopilotSession, CopilotMessage, CopilotProposal, CopilotTask
from models.engagement import Engagement
from models.reporting import Finding
from models.interview import InterviewSession

# Where an item-level "ready for review" card should link to — (base, route),
# combined the same way STAGE_GRAPH entries are: /engagements/{id}/{base}/{route}.
ITEM_TYPE_ROUTE = {
    "finding": ("", "reporting"),
    "interview_session": ("planning", "interview"),
}

# Stable marker prefixed onto a coherence-settle nudge's message content
# (Part 2b) — copilot_orchestrator.py builds the message with it,
# latest_coherence_nudge_at below filters on it. Kept here rather than in
# copilot_orchestrator.py since this module already owns every other
# dedup-marker convention (e.g. _PAUSE_NOTICE's role there).
COHERENCE_NUDGE_MARKER = "[coherence-nudge]"

VALID_PROPOSAL_STATUSES = {"pending", "accepted", "dismissed"}
VALID_TASK_STATUSES = {"queued", "running", "ready_for_review", "reviewed", "dismissed", "failed"}
# A stage with any task in one of these statuses is not re-queued by the next
# scan. "failed" and "ready_for_review" are included deliberately: a failed
# attempt should surface for the auditor to notice and retry manually (chat's
# propose_run_stage, or the page's own action) rather than be silently
# re-attempted every scan, and a stage already sitting in the review queue
# must not be re-drafted before the auditor has even looked at it — some
# stages' auto-fire action only completes one step of a multi-step flow
# (e.g. Process Understanding's reasoning pass), so the stage can keep
# reading as "available" afterwards without this guard.
ACTIVE_TASK_STATUSES = ("queued", "running", "failed", "ready_for_review")


async def get_or_create_session(engagement_id: str) -> str:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CopilotSession).where(CopilotSession.engagement_id == engagement_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            session = CopilotSession(id=str(uuid4()), engagement_id=engagement_id)
            db.add(session)
            await db.commit()
        return session.id


async def list_messages(engagement_id: str) -> list[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CopilotSession).where(CopilotSession.engagement_id == engagement_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return []
        rows = (await db.execute(
            select(CopilotMessage).where(CopilotMessage.session_id == session.id)
            .order_by(CopilotMessage.created_at)
        )).scalars().all()
        proposals = (await db.execute(
            select(CopilotProposal).where(CopilotProposal.session_id == session.id)
        )).scalars().all()
        status_by_id = {p.id: p.status for p in proposals}

        out = []
        for r in rows:
            tool_calls = json.loads(r.tool_calls) if r.tool_calls else []
            # The message row is a write-once snapshot; a proposal's status can
            # change afterwards (accepted/dismissed), so always read it live
            # from CopilotProposal rather than trusting the snapshot's status.
            for tc in tool_calls:
                pid = tc.get("proposal_id")
                tc["status"] = status_by_id.get(pid, "expired")
            out.append({
                "role": r.role, "content": r.content, "tool_calls": tool_calls,
                "is_proactive": bool(r.is_proactive),
            })
        return out


async def append_message(
    session_id: str, role: str, content: str, tool_calls: list | None = None, is_proactive: bool = False,
) -> None:
    async with AsyncSessionLocal() as db:
        db.add(CopilotMessage(
            id=str(uuid4()), session_id=session_id, role=role, content=content or "",
            tool_calls=json.dumps(tool_calls) if tool_calls else None, is_proactive=is_proactive,
        ))
        await db.commit()


async def latest_proactive_message_at(engagement_id: str):
    """created_at of the most recent proactive nudge (M10), or None — the
    rate-limit check maybe_ask_proactive_question uses so it doesn't
    re-interrupt the auditor before the cooldown has elapsed."""
    async with AsyncSessionLocal() as db:
        session = (await db.execute(
            select(CopilotSession).where(CopilotSession.engagement_id == engagement_id)
        )).scalar_one_or_none()
        if session is None:
            return None
        times = (await db.execute(
            select(CopilotMessage.created_at).where(
                CopilotMessage.session_id == session.id, CopilotMessage.is_proactive.is_(True),
            )
        )).scalars().all()
    return max(times) if times else None


async def create_proposal(session_id: str, tool_name: str, tool_input: dict) -> str:
    async with AsyncSessionLocal() as db:
        proposal = CopilotProposal(
            id=str(uuid4()), session_id=session_id, tool_name=tool_name,
            input=json.dumps(tool_input or {}),
        )
        db.add(proposal)
        await db.commit()
        return proposal.id


async def set_proposal_status(proposal_id: str, status: str) -> dict | None:
    if status not in VALID_PROPOSAL_STATUSES:
        raise ValueError(f"Invalid proposal status '{status}'")
    async with AsyncSessionLocal() as db:
        proposal = await db.get(CopilotProposal, proposal_id)
        if not proposal:
            return None
        proposal.status = status
        await db.commit()
        return {"id": proposal.id, "status": proposal.status}


def _task_dict(t: CopilotTask) -> dict:
    return {
        "id": t.id, "engagement_id": t.engagement_id, "stage_key": t.stage_key,
        "item_id": t.item_id,
        "status": t.status, "triggered_by": t.triggered_by, "flagged": t.flagged,
        "error": t.error, "rationale": t.rationale,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


async def create_task(
    engagement_id: str, stage_key: str, triggered_by: str = "auto",
    item_id: str | None = None, rationale: str | None = None,
) -> str:
    """stage_key is a STAGE_GRAPH key for ordinary stage tasks. For item-level
    tasks (item_id set) it instead holds a short, constant item-type label
    ("finding", "interview_session") — see models/copilot.py's CopilotTask.
    rationale is the Orchestrator Agent's one-sentence "why this now" (Part 2
    — advise_stage_order); None for every other caller (manual runs, item
    tasks) — backward compatible, existing call sites are unaffected."""
    async with AsyncSessionLocal() as db:
        task = CopilotTask(
            id=str(uuid4()), engagement_id=engagement_id, stage_key=stage_key,
            item_id=item_id, triggered_by=triggered_by,
            rationale=(rationale[:300] if rationale else None),
        )
        db.add(task)
        await db.commit()
        return task.id


async def active_stage_keys(engagement_id: str) -> set[str]:
    """Stage keys with a queued/running task — a scan must not double-queue these.
    Item-level tasks (item_id set) are excluded — see active_item_ids."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(CopilotTask.stage_key).where(
                CopilotTask.engagement_id == engagement_id,
                CopilotTask.item_id.is_(None),
                CopilotTask.status.in_(ACTIVE_TASK_STATUSES),
            )
        )).scalars().all()
        return set(rows)


async def active_item_ids(engagement_id: str, item_type: str) -> set[str]:
    """Item ids of the given type with a queued/running/failed/ready_for_review
    task — the item scanner (M7) must not double-queue these. Mirrors
    active_stage_keys, scoped by item_type instead of engagement-wide."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(CopilotTask.item_id).where(
                CopilotTask.engagement_id == engagement_id,
                CopilotTask.stage_key == item_type,
                CopilotTask.item_id.isnot(None),
                CopilotTask.status.in_(ACTIVE_TASK_STATUSES),
            )
        )).scalars().all()
        return set(rows)


async def count_auto_tasks(engagement_id: str) -> int:
    """How many auto-triggered STAGE-level tasks this engagement has ever
    queued — the session budget copilot_preflight enforces so a stuck loop
    can't run away. Item-level tasks have their own, separate budget
    (count_auto_item_tasks) so a finding-heavy engagement can't starve it."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(CopilotTask.id).where(
                CopilotTask.engagement_id == engagement_id, CopilotTask.triggered_by == "auto",
                CopilotTask.item_id.is_(None),
            )
        )).scalars().all()
        return len(rows)


async def count_auto_item_tasks(engagement_id: str) -> int:
    """How many auto-triggered ITEM-level tasks (findings + interview sessions
    combined) this engagement has ever queued — separate budget from
    count_auto_tasks, see its docstring."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(CopilotTask.id).where(
                CopilotTask.engagement_id == engagement_id, CopilotTask.triggered_by == "auto",
                CopilotTask.item_id.isnot(None),
            )
        )).scalars().all()
        return len(rows)


async def is_autonomy_paused(engagement_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        return bool(eng and eng.copilot_autonomy_paused)


async def is_closed(engagement_id: str) -> bool:
    """A closed audit is finished work, and autonomy stops there.

    Auto-firing paid AI drafting on a signed-off file produces review cards
    nobody asked for, against conclusions that are already issued — the demo
    data had four of them queued on a closed engagement. A human can still run
    any stage on a closed audit by hand; that is their decision to make, not
    something the copilot should decide for them in the background.
    """
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        return bool(eng and eng.status == "closed")


async def set_autonomy_paused(engagement_id: str, paused: bool) -> dict | None:
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        if not eng:
            return None
        eng.copilot_autonomy_paused = paused
        await db.commit()
        return {"engagement_id": engagement_id, "copilot_autonomy_paused": paused}


async def resolve_items(db, finding_ids: list[str], session_ids: list[str]) -> dict[str, dict]:
    """Label + structural detail for a batch of item ids, keyed by item_id.

    The single shared resolution formula for both list_tasks()'s item_label
    column and the Orchestrator Agent's item-ordering advice
    (advise_item_order, Part 1) — factored out of list_tasks() so there is
    exactly one place that decides "what do we call this item". `detail` is
    purely structural (rating/status — controlled vocabulary), never free text
    like condition/notes: advise_item_order deliberately keeps it outside its
    wrap_untrusted() call, so it must never carry anything an auditor typed.
    """
    out: dict[str, dict] = {}
    if finding_ids:
        findings = (await db.execute(select(Finding).where(Finding.id.in_(finding_ids)))).scalars().all()
        for f in findings:
            out[f.id] = {"label": f.title, "detail": f"rating: {f.rating or 'unrated'}"}
    if session_ids:
        sessions = (await db.execute(select(InterviewSession).where(InterviewSession.id.in_(session_ids)))).scalars().all()
        for s in sessions:
            out[s.id] = {"label": s.label or s.persona or "Interview session", "detail": f"status: {s.status}"}
    return out


async def list_tasks(engagement_id: str, status: str | None = None) -> list[dict]:
    async with AsyncSessionLocal() as db:
        stmt = select(CopilotTask).where(CopilotTask.engagement_id == engagement_id)
        if status:
            stmt = stmt.where(CopilotTask.status == status)
        rows = (await db.execute(stmt.order_by(CopilotTask.created_at.desc()))).scalars().all()
        out = [_task_dict(t) for t in rows]

        # Item-level tasks (item_id set) can't be resolved via STAGE_GRAPH like
        # ordinary stage tasks — look their label up here, in one batch, so the
        # frontend never needs its own item_type branching logic.
        finding_ids = [t.item_id for t in rows if t.stage_key == "finding" and t.item_id]
        session_ids = [t.item_id for t in rows if t.stage_key == "interview_session" and t.item_id]
        resolved = await resolve_items(db, finding_ids, session_ids)

        for d, t in zip(out, rows):
            route = ITEM_TYPE_ROUTE.get(t.stage_key) if t.item_id else None
            if not route:
                continue
            base, path = route
            d["item_label"] = resolved.get(t.item_id, {}).get("label") or t.stage_key
            d["item_base"] = base
            d["item_route"] = path
        return out


async def set_task_status(task_id: str, status: str, error: str | None = None) -> dict | None:
    if status not in VALID_TASK_STATUSES:
        raise ValueError(f"Invalid task status '{status}'")
    async with AsyncSessionLocal() as db:
        task = await db.get(CopilotTask, task_id)
        if not task:
            return None
        task.status = status
        if error is not None:
            task.error = error[:500]
        await db.commit()
        await db.refresh(task)
        return _task_dict(task)


async def set_task_flagged(task_id: str, flagged: bool) -> None:
    async with AsyncSessionLocal() as db:
        task = await db.get(CopilotTask, task_id)
        if task:
            task.flagged = flagged
            await db.commit()


async def latest_report_draft_proposal_at(engagement_id: str):
    """created_at of the most recent propose_run_stage(report_draft) proposal,
    or None. Lets the settle-window check (copilot_orchestrator) tell "already
    surfaced for this quiet period" apart from "findings changed since, ask
    again" without a dedicated table — pending and dismissed both count, only
    a finding change after this timestamp should trigger a fresh proposal."""
    async with AsyncSessionLocal() as db:
        session = (await db.execute(
            select(CopilotSession).where(CopilotSession.engagement_id == engagement_id)
        )).scalar_one_or_none()
        if session is None:
            return None
        rows = (await db.execute(
            select(CopilotProposal).where(
                CopilotProposal.session_id == session.id,
                CopilotProposal.tool_name == "propose_run_stage",
            )
        )).scalars().all()
    times = [p.created_at for p in rows if json.loads(p.input or "{}").get("stage_key") == "report_draft"]
    return max(times) if times else None


async def latest_coherence_nudge_at(engagement_id: str):
    """created_at of the most recent coherence-settle nudge (Part 2b), or None —
    near-twin of latest_report_draft_proposal_at, but keyed on a stable marker
    string inside the message content rather than a CopilotProposal row: this
    nudge is a plain, contentless pointer (never an actionable proposal), so
    there is no CopilotProposal to key off. Used by
    copilot_orchestrator.maybe_notify_coherence_settle so it doesn't re-nudge
    for a coverage state the auditor has already been pointed at."""
    async with AsyncSessionLocal() as db:
        session = (await db.execute(
            select(CopilotSession).where(CopilotSession.engagement_id == engagement_id)
        )).scalar_one_or_none()
        if session is None:
            return None
        rows = (await db.execute(
            select(CopilotMessage.content, CopilotMessage.created_at).where(
                CopilotMessage.session_id == session.id, CopilotMessage.is_proactive.is_(True),
            )
        )).all()
    times = [created_at for content, created_at in rows if COHERENCE_NUDGE_MARKER in (content or "")]
    return max(times) if times else None
