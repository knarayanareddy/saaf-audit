import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.planning import KickoffAgenda, ScopeObjectives, ScopeItem, KeyAuditQuestion
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services import scope_sources
from services.agent_ledger import agent_context, attributed

router = APIRouter()

AGENDA_FIELDS = [
    "meeting_date", "attendees", "audit_purpose",
    "notes_welcome", "notes_context", "notes_documentation", "notes_missing",
    "notes_scope", "notes_risks", "notes_team", "notes_other", "notes_aob", "notes_next_steps",
]


def serialize_agenda(a: KickoffAgenda) -> dict:
    d = {f: getattr(a, f, None) for f in ["id", "engagement_id", "status"] + AGENDA_FIELDS}
    try:
        d["questions_for_auditor"] = json.loads(a.questions_for_auditor) if a.questions_for_auditor else []
    except (ValueError, TypeError):
        d["questions_for_auditor"] = []
    return d


@router.get("/planning/{engagement_id}/kickoff")
async def get_kickoff(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    return serialize_agenda(a) if a else {"status": "not_started"}


@router.patch("/planning/{engagement_id}/kickoff")
async def update_kickoff(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Kickoff agenda not started")
    for key in AGENDA_FIELDS:
        if key in payload:
            setattr(a, key, payload[key])
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/kickoff/draft")
async def draft_kickoff(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    if not a:
        a = KickoffAgenda(id=str(uuid4()), engagement_id=engagement_id)
        db.add(a)

    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="kickoff_drafter", status="pending")
    db.add(run)
    a.drafter_run_id = run.id
    a.status = "drafting"
    await db.commit()

    background_tasks.add_task(attributed(_run_kickoff_drafter, engagement_id, "kickoff", run.id), a.id, run.id, engagement_id)
    return {"run_id": run.id, "agenda_id": a.id}


@router.get("/planning/{engagement_id}/kickoff/export-word")
async def export_kickoff_word(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Kickoff agenda not started")

    import asyncio, json as _json
    from services.word_export import generate_kickoff_docx
    eng_data = {"name": eng.name, "audit_code": eng.audit_code, "entity": eng.entity}
    agenda_data = serialize_agenda(a)
    docx_bytes = await asyncio.get_event_loop().run_in_executor(None, generate_kickoff_docx, agenda_data, eng_data)
    filename = f"KickOff-{eng.audit_code or eng.name[:20].replace(' ','-')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _run_kickoff_drafter(agenda_id: str, run_id: str, engagement_id: str):
    from services.kickoff_drafter import run_kickoff_drafter
    await run_kickoff_drafter(agenda_id, run_id, engagement_id)


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ── Scope & Objectives contribution ──────────────────────────────────────────

@router.post("/planning/{engagement_id}/kickoff/generate-scope")
async def kickoff_generate_scope(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Generate key audit questions from kick-off agenda notes."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    if not a:
        return {"scope_items": [], "key_questions": []}

    notes_parts = []
    note_map = {
        "notes_context": "Audit context",
        "notes_scope": "Scope discussed",
        "notes_risks": "Risks discussed",
        "notes_documentation": "Documentation available",
    }
    for field, label in note_map.items():
        val = getattr(a, field, None)
        if val and val.strip():
            notes_parts.append(f"{label}:\n{val[:800]}")

    if not notes_parts:
        return {"scope_items": [], "key_questions": []}

    notes_text = "\n\n".join(notes_parts)
    prompt = f"""Based on the kick-off meeting notes for this internal audit, generate key audit questions
and scope items for the Scope & Objectives module.

Audit: {eng.name}
Entity: {eng.entity}

KICK-OFF MEETING NOTES:
{notes_text}

Return ONLY valid JSON (no explanation, no markdown):
{{
  "scope_items": [
    {{
      "item_type": "in_scope",
      "description": "Specific scope area confirmed in the meeting",
      "rationale": "What was discussed in the kick-off"
    }}
  ],
  "key_questions": [
    {{
      "question_text": "Key audit question derived from kick-off discussion",
      "regulatory_basis": "Context from meeting notes"
    }}
  ]
}}

Rules: 2-4 scope items + 3-5 key questions directly derived from what was discussed.
Only include items actually mentioned — do not invent topics not in the notes.
"""
    with agent_context(engagement_id=engagement_id, agent="kickoff"):
        contribution = await run_agent_to_json(BASE_SYSTEM_PROMPT, prompt, max_tokens=2000)
    if not isinstance(contribution, dict):
        contribution = {"scope_items": [], "key_questions": []}

    run_res = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "kickoff_scope",
        ).order_by(AgentRun.created_at.desc())
    )
    scope_run = run_res.scalars().first()
    if not scope_run:
        scope_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id,
                             agent_type="kickoff_scope", status="complete")
        db.add(scope_run)
    scope_run.accepted_output = json.dumps(contribution)
    await db.commit()
    return contribution


@router.get("/planning/{engagement_id}/kickoff/scope-contribution")
async def kickoff_get_scope(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "kickoff_scope",
        ).order_by(AgentRun.created_at.desc())
    )
    run = result.scalars().first()
    if not run or not run.accepted_output:
        return {"scope_items": [], "key_questions": []}
    return _loads(run.accepted_output, {"scope_items": [], "key_questions": []})


@router.post("/planning/{engagement_id}/kickoff/publish-scope")
async def kickoff_publish_scope(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    scope_result = await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )
    scope = scope_result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id, status="in_progress")
        db.add(scope)
        await db.commit()
        await db.refresh(scope)

    ref = await scope_sources.run_ref(db, engagement_id, "kickoff_scope")

    items_added = 0
    for i, item in enumerate(payload.get("scope_items", [])):
        if not item.get("selected", True):
            continue
        db.add(ScopeItem(
            id=str(uuid4()), scope_id=scope.id,
            item_type=item.get("item_type", "in_scope"),
            description=item.get("description", ""),
            rationale=item.get("rationale", ""),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.KICKOFF, ref),
        ))
        items_added += 1

    q_added = 0
    for i, q in enumerate(payload.get("key_questions", [])):
        if not q.get("selected", True):
            continue
        db.add(KeyAuditQuestion(
            id=str(uuid4()), scope_id=scope.id,
            question_text=q.get("question_text", ""),
            regulatory_basis=q.get("regulatory_basis", ""),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.KICKOFF, ref),
        ))
        q_added += 1

    await db.commit()
    return {"scope_items_added": items_added, "questions_added": q_added}
