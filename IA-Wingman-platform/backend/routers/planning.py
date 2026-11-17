import json
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.planning import (
    TopicIntelligence, ScopeObjectives, ScopeItem,
    KeyAuditQuestion, ApplicableFramework, ProcessNotes, RegRequirement,
)
from services.framework_library import frameworks_for_entity, FRAMEWORK_LIBRARY
from services.scan_context import scan_context
from services.agent_ledger import attributed
from services import scope_sources
from services.framework_requirements_agent import run_framework_requirements_analysis, generate_scope_contribution
from services.supervisory_guidance_agent import run_supervisory_guidance_analysis
from services.process_understanding_agent import run_process_analysis, generate_process_proposals
from services.progress_service import planning_progress
from schemas import (
    ProcessNotesUpdate, FrameworkAdd, ScopeItemCreate, QuestionCreate,
    ApproveReasoningRequest, PatchProcessItemRequest, AcceptProcessItemsRequest,
    Lens4UpdateRequest,
)

router = APIRouter()


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ───────────────────────── Topic Intelligence ─────────────────────────

@router.get("/planning/{engagement_id}/topic-intelligence")
async def get_topic_intelligence(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if not ti:
        return {"status": "not_started"}

    # Pull frameworks from the regulatory agent run for display
    frameworks = []
    if ti.regulatory_run_id:
        reg = await db.get(AgentRun, ti.regulatory_run_id)
        if reg and reg.raw_output:
            frameworks = _loads(reg.raw_output, {}).get("applicable_frameworks", [])

    # A re-run that failed leaves the earlier result in place, so the page has to be told:
    # a failed run of a lens that is not the one on the memo is the reason. A later run that
    # succeeds marks the failed ones "superseded", so a reason never outlives the problem.
    async def _lens_errors(ti):
        errors = {}
        for n in (1, 2, 3):
            failed = (await db.execute(
                select(AgentRun).where(AgentRun.engagement_id == engagement_id, AgentRun.agent_type == f"lens{n}",
                                       AgentRun.status == "failed", AgentRun.id != getattr(ti, f"lens{n}_run_id"))
            )).scalars().first()
            if failed:
                errors[f"lens{n}"] = _loads(failed.search_progress, {}).get("error") or "The lens failed."
        return errors

    # What each lens's searching actually did. Read from the run rather than
    # from the lens's own summary, because the summary is the model's account of
    # it and this is the tool's.
    async def _search_of(run_id):
        run = await db.get(AgentRun, run_id) if run_id else None
        progress = _loads(run.search_progress, {}) if run and run.search_progress else {}
        if "searches_used" not in progress:
            return None  # a run from before this was recorded: say nothing, not a guess
        return {
            "web_search": progress.get("web_search", False),
            "used": progress.get("searches_used", 0),
            "allowed": progress.get("searches_allowed", 0),
            "errors": progress.get("search_errors", []),
            # The lens ran no search the first time and was asked again.
            "retried": bool(progress.get("retried", False)),
            # What it asked, so the auditor can see where the lens looked.
            "queries": progress.get("queries", []),
            # The sources are the search's own pages, not the model's list.
            "sources_from_search": bool(progress.get("sources_from_search", False)),
        }

    return {
        # The record's own id, so the screen can ask the edit register about it.
        "id": ti.id,
        "lens1_search": await _search_of(ti.lens1_run_id),
        "lens2_search": await _search_of(ti.lens2_run_id),
        "lens3_search": await _search_of(ti.lens3_run_id),
        "status": ti.status,
        "progress_pct": ti.progress_pct,
        "synthesis_failed": ti.synthesis_failed,
        "regulatory_summary": ti.regulatory_summary,
        "internal_framework_summary": ti.internal_framework_summary,
        "external_developments": ti.external_developments,
        "applicable_frameworks": frameworks,
        "key_risk_areas": _loads(ti.key_risk_areas, []),
        "excluded_areas": _loads(ti.excluded_areas, []),
        "interview_agenda": _loads(ti.interview_agenda, {}),
        "conclusion": ti.conclusion,
        "proposed_frameworks": _loads(ti.proposed_frameworks, []),
        "topic_primer": ti.topic_primer,
        "verification": _loads(ti.verification, None),
        "lens_errors": await _lens_errors(ti),
        "memo_accepted": ti.memo_accepted,
        "search_results": _loads(ti.search_results, []),
        "search_queries": _loads(ti.search_queries, []),
        "lens1_summary": ti.lens1_summary,
        "lens1_sources": _loads(ti.lens1_sources, []),
        "lens2_summary": ti.lens2_summary,
        "lens2_sources": _loads(ti.lens2_sources, []),
        "lens3_summary": ti.lens3_summary,
        "lens3_sources": _loads(ti.lens3_sources, []),
        "lens4_notes": ti.lens4_notes,
        "lens4_state": ti.lens4_state or "empty",
        "extra_context": ti.extra_context,
    }


@router.post("/planning/{engagement_id}/topic-intelligence/lens/{lens}/rerun")
async def rerun_topic_lens(engagement_id: str, lens: int, background_tasks: BackgroundTasks,
                           db: AsyncSession = Depends(get_db)):
    """Run one lens again, for an auditor who is not happy with one lens of an otherwise good scan."""
    from services.agent_ledger import attributed
    from services.orchestrator import rerun_lens

    if lens not in (1, 2, 3):
        raise HTTPException(status_code=422, detail="lens must be 1, 2 or 3")
    ti = (await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    if not ti:
        raise HTTPException(status_code=404, detail="Topic Intelligence not started")
    if ti.memo_accepted:
        raise HTTPException(status_code=409, detail="The memo has been accepted; a lens cannot be re-run on it")
    if ti.status == "agents_pending":
        raise HTTPException(status_code=409, detail="A scan is already running")

    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type=f"lens{lens}", status="pending")
    db.add(run)
    ti.status = "agents_pending"
    await db.commit()
    background_tasks.add_task(attributed(rerun_lens, engagement_id, "topic_intelligence"), engagement_id, lens, run.id)
    return {"run_id": run.id, "lens": lens}


@router.get("/planning/{engagement_id}/topic-intelligence/export-word")
async def export_topic_memo_word(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """The memo as a Word file, built from the same answer the page reads."""
    import asyncio

    from fastapi.responses import Response

    from services.topic_memo_export import generate_topic_memo_docx

    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    ti = await get_topic_intelligence(engagement_id, db)
    if ti.get("status") == "not_started":
        raise HTTPException(status_code=404, detail="Topic Intelligence not started")
    eng_data = {"name": eng.name, "audit_code": eng.audit_code, "entity": eng.entity}
    docx_bytes = await asyncio.get_event_loop().run_in_executor(None, generate_topic_memo_docx, ti, eng_data)
    filename = f"Topic-Intelligence-{eng.audit_code or eng.name[:20].replace(' ', '-')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/planning/{engagement_id}/topic-intelligence/context")
async def get_scan_context(engagement_id: str):
    """What the scan will be given — and what it will not."""
    context = await scan_context(engagement_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return context


@router.patch("/planning/{engagement_id}/topic-intelligence")
async def update_topic_intelligence(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if not ti:
        raise HTTPException(status_code=404, detail="Topic Intelligence not started")

    text_fields = {"regulatory_summary", "internal_framework_summary", "external_developments", "conclusion"}
    json_fields = {"key_risk_areas", "excluded_areas", "interview_agenda", "proposed_frameworks"}
    for key, value in payload.items():
        if key in text_fields:
            setattr(ti, key, value)
        elif key in json_fields:
            setattr(ti, key, json.dumps(value))
    await db.commit()
    return {"ok": True}


@router.patch("/planning/{engagement_id}/ti/lens4")
async def update_lens4(engagement_id: str, payload: Lens4UpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if not ti:
        raise HTTPException(status_code=404, detail="Topic Intelligence not started")
    ti.lens4_notes = payload.notes
    ti.lens4_state = payload.state
    await db.commit()
    return {"lens4_notes": ti.lens4_notes, "lens4_state": ti.lens4_state}


@router.post("/planning/{engagement_id}/topic-intelligence/accept")
async def accept_topic_intelligence(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if not ti:
        raise HTTPException(status_code=404, detail="Topic Intelligence not started")

    ti.status = "agreed"
    ti.memo_accepted = True
    ti.memo_accepted_at = datetime.utcnow()
    ti.progress_pct = 100

    # Scope objectives (create or get)
    scope_result = await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )
    scope = scope_result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(
            id=str(uuid4()), engagement_id=engagement_id, status="in_progress",
            scope_period=eng.scope_period, scope_entity=eng.entity,
        )
        db.add(scope)
        await db.flush()

    key_risk_areas = _loads(ti.key_risk_areas, [])
    scope_count = 0
    for i, area in enumerate(key_risk_areas):
        if not area.get("included", True):
            continue
        db.add(ScopeItem(
            id=str(uuid4()), scope_id=scope.id, item_type="in_scope",
            description=area.get("title", ""), rationale=area.get("basis") or area.get("rationale"),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.TOPIC_INTELLIGENCE, area.get("id")),
        ))
        scope_count += 1
    excluded_areas = _loads(ti.excluded_areas, [])
    for i, area in enumerate(excluded_areas):
        if not area.get("included", True):
            continue
        db.add(ScopeItem(
            id=str(uuid4()), scope_id=scope.id, item_type="out_of_scope",
            description=area.get("title", ""), rationale=area.get("rationale"),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.TOPIC_INTELLIGENCE, area.get("id")),
        ))
        scope_count += 1

    agenda = _loads(ti.interview_agenda, {})
    # Only the key audit questions become Scope's key audit questions. Sponsor
    # questions are read by the kick-off drafter and SME questions by the interview
    # guide straight from the memo (see auditee_context), so each is asked where it
    # belongs instead of all of them landing in Scope. Items are
    # {id, question_text, included}, stamped by synthesize_topic_intelligence.
    key_questions = agenda.get("key_audit_questions", [])
    q_count = 0
    for i, q in enumerate(key_questions):
        if not q.get("included", True):
            continue
        db.add(KeyAuditQuestion(
            id=str(uuid4()), scope_id=scope.id, question_text=q.get("question_text", ""),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.TOPIC_INTELLIGENCE, q.get("id")),
        ))
        q_count += 1

    proposed_fws = _loads(ti.proposed_frameworks, [])
    fw_count = 0
    if proposed_fws:
        for fw in proposed_fws:
            if not fw.get("included", True):
                continue
            db.add(ApplicableFramework(
                id=str(uuid4()), engagement_id=engagement_id,
                framework_code=fw.get("framework_code", ""),
                framework_name=fw.get("framework_name", ""),
                applicability_rationale=fw.get("applicability_rationale", ""),
                jurisdiction=fw.get("jurisdiction"),
                confidence=fw.get("confidence", "medium"),
                is_primary=bool(fw.get("is_primary", False)),
                is_accepted=False, source="ai_suggested",
            ))
            fw_count += 1
    elif ti.regulatory_run_id:
        # Dead v1-pipeline fallback — unchanged behaviour, kept only so an old,
        # never-migrated TI row (proposed_frameworks never populated) still
        # cascades something instead of silently zero frameworks.
        reg = await db.get(AgentRun, ti.regulatory_run_id)
        frameworks = _loads(reg.raw_output, {}).get("applicable_frameworks", []) if reg else []
        for fw in frameworks:
            db.add(ApplicableFramework(
                id=str(uuid4()), engagement_id=engagement_id,
                framework_code=fw.get("framework_code", ""),
                framework_name=fw.get("framework_name", ""),
                applicability_rationale=fw.get("applicability_rationale", ""),
                is_primary=bool(fw.get("is_primary", False)),
                is_accepted=False, source="ai_suggested",
            ))
            fw_count += 1

    await db.commit()

    proposed_total = len(key_risk_areas) + len(excluded_areas) + len(key_questions) + len(proposed_fws)
    accepted_total = scope_count + q_count + fw_count
    skipped_note = (
        f" ({proposed_total - accepted_total} of {proposed_total} proposed item(s) not included)"
        if proposed_total > accepted_total else ""
    )
    from services.activity_service import log_activity
    await log_activity(
        engagement_id, "topic_intelligence", "accept",
        summary=f"Auditor accepted the Topic Intelligence memo — cascaded {scope_count} scope item(s), "
                f"{q_count} question(s), {fw_count} framework(s){skipped_note}",
        actor="auditor",
    )
    return {"scope_items_queued": scope_count, "questions_queued": q_count, "frameworks_queued": fw_count}


@router.post("/planning/{engagement_id}/topic-intelligence/resynthesize")
async def resynthesize_topic_intelligence(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Manual retry after a failed synthesis (ti.synthesis_failed). Reuses the
    ALREADY-STORED lens summaries — never re-runs a lens agent, so it can't
    silently discard edits the auditor made to a lens summary via its own
    EditableText field, and doesn't repeat three expensive web searches to
    fix a problem in one independent, downstream step. Synchronous (like
    /ai/suggest-*), not a background task — one LLM call, worth awaiting."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if not ti:
        raise HTTPException(status_code=404, detail="Topic Intelligence not started")

    l3_sources = _loads(ti.lens3_sources, [])
    materiality_signal = l3_sources[0].get("materiality_signal") if l3_sources else None

    from services.orchestrator_agent import synthesize_topic_intelligence
    try:
        synthesis = await synthesize_topic_intelligence(
            eng, ti.lens1_summary, ti.lens2_summary, ti.lens3_summary, materiality_signal,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Resynthesis failed — please try again") from exc

    ti.key_risk_areas = json.dumps(synthesis["key_risk_areas"])
    ti.excluded_areas = json.dumps(synthesis["excluded_areas"])
    ti.interview_agenda = json.dumps(synthesis["interview_agenda"])
    ti.conclusion = synthesis["conclusion"]
    ti.proposed_frameworks = json.dumps(synthesis["proposed_frameworks"])
    ti.synthesis_failed = False
    ti.progress_pct = 60
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/topic-intelligence/discard")
async def discard_topic_intelligence(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if ti:
        await db.delete(ti)
    runs = await db.execute(select(AgentRun).where(AgentRun.engagement_id == engagement_id))
    for r in runs.scalars().all():
        await db.delete(r)
    await db.commit()
    return {"ok": True}


# ───────────────────────── Process Notes ─────────────────────────

def _pn_response(pn: ProcessNotes | None) -> dict:
    """Serialise a ProcessNotes row for the frontend."""
    if not pn:
        return {"status": "not_started", "notes": "", "reasoning": None,
                "process_items": [], "preliminary_observations": []}
    return {
        "id": pn.id,
        "status": pn.status or "not_started",
        "notes": pn.notes or "",
        "reasoning": _loads(pn.reasoning, None),
        "process_items": _loads(pn.process_items, []),
        "preliminary_observations": _loads(pn.preliminary_observations, []),
    }


@router.get("/planning/{engagement_id}/process-notes")
async def get_process_notes(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    return _pn_response(pn)


@router.put("/planning/{engagement_id}/process-notes")
async def put_process_notes(engagement_id: str, payload: ProcessNotesUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    if not pn:
        pn = ProcessNotes(id=str(uuid4()), engagement_id=engagement_id, notes=payload.notes)
        db.add(pn)
    else:
        pn.notes = payload.notes
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/process-notes/analyse")
async def analyse_process_notes(
    engagement_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger Step 1: AI reasons about in-scope processes. Creates/resets ProcessNotes row."""
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    if not pn:
        pn = ProcessNotes(id=str(uuid4()), engagement_id=engagement_id, status="not_started")
        db.add(pn)
        await db.commit()
        await db.refresh(pn)

    # Don't re-run if already running
    if pn.status in ("reasoning", "generating"):
        return _pn_response(pn)

    pn.status = "not_started"
    pn.reasoning = None
    pn.process_items = None
    pn.preliminary_observations = None
    await db.commit()
    await db.refresh(pn)

    background_tasks.add_task(attributed(run_process_analysis, engagement_id, "process_understanding"), pn.id, engagement_id)
    return _pn_response(pn)


@router.post("/planning/{engagement_id}/process-notes/approve-reasoning")
async def approve_reasoning(
    engagement_id: str,
    payload: ApproveReasoningRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Step 2: Store approved reasoning, trigger proposal generation."""
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    if not pn:
        raise HTTPException(status_code=404, detail="Process notes not found")

    # Store approved (possibly edited) reasoning as plain text for the proposals step
    pn.reasoning = json.dumps({"approved_text": payload.reasoning})
    pn.status = "generating"
    await db.commit()
    await db.refresh(pn)

    background_tasks.add_task(attributed(generate_process_proposals, engagement_id, "process_understanding"),
                              pn.id, engagement_id, payload.reasoning)
    return _pn_response(pn)


@router.patch("/planning/{engagement_id}/process-notes/items/{item_id}")
async def patch_process_item(
    engagement_id: str,
    item_id: str,
    payload: PatchProcessItemRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a single process item within ProcessNotes.process_items JSON array."""
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    if not pn:
        raise HTTPException(status_code=404, detail="Process notes not found")

    items = _loads(pn.process_items, [])
    updated = False
    for item in items:
        if item.get("id") == item_id:
            if payload.name is not None:
                item["name"] = payload.name
            if payload.description is not None:
                item["description"] = payload.description
            if payload.is_included is not None:
                item["is_included"] = payload.is_included
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")

    pn.process_items = json.dumps(items)
    await db.commit()
    return _pn_response(pn)


@router.post("/planning/{engagement_id}/process-notes/accept")
async def accept_process_notes(
    engagement_id: str,
    payload: AcceptProcessItemsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Finalise process understanding: save items, cascade included ones to Scope & Objectives."""
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    if not pn:
        raise HTTPException(status_code=404, detail="Process notes not found")

    # Save the accepted items (with is_included flags)
    pn.process_items = json.dumps(payload.items)
    pn.status = "agreed"
    await db.commit()

    # Cascade included processes to Scope & Objectives
    scope_result = await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )
    scope = scope_result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id, status="in_progress")
        db.add(scope)
        await db.commit()
        await db.refresh(scope)

    items_added = 0
    for item in payload.items:
        if not item.get("is_included"):
            continue
        db.add(ScopeItem(
            id=str(uuid4()),
            scope_id=scope.id,
            item_type="in_scope",
            description=item.get("name", ""),
            rationale=item.get("description", ""),
            is_accepted=False,
            sort_order=items_added,
            **scope_sources.stamp(scope_sources.PROCESS_UNDERSTANDING, item.get("id")),
        ))
        items_added += 1

    # Cascade preliminary observations as key audit questions
    obs = _loads(pn.preliminary_observations, [])
    for i, ob in enumerate(obs):
        db.add(KeyAuditQuestion(
            id=str(uuid4()),
            scope_id=scope.id,
            question_text=ob.get("text", ""),
            regulatory_basis=ob.get("source", ""),
            is_accepted=False,
            sort_order=i,
            **scope_sources.stamp(scope_sources.PROCESS_UNDERSTANDING, ob.get("id")),
        ))

    await db.commit()
    return {
        **_pn_response(pn),
        "scope_items_added": items_added,
        "observations_added": len(obs),
    }


# ───────────────────────── Scope & Objectives ─────────────────────────

@router.get("/planning/{engagement_id}/scope")
async def get_scope(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
    scope = result.scalar_one_or_none()
    if not scope:
        return {"status": "not_started", "items": [], "questions": []}

    items = (await db.execute(
        select(ScopeItem).where(ScopeItem.scope_id == scope.id).order_by(ScopeItem.sort_order)
    )).scalars().all()
    questions = (await db.execute(
        select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id).order_by(KeyAuditQuestion.sort_order)
    )).scalars().all()

    return {
        "status": scope.status,
        "overall_objective": scope.overall_objective,
        "scope_period": scope.scope_period,
        "scope_entity": scope.scope_entity,
        "items": [
            {"id": i.id, "item_type": i.item_type, "description": i.description,
             "rationale": i.rationale, "is_accepted": i.is_accepted,
             **scope_sources.describe(i.source, i.source_ref)}
            for i in items
        ],
        "questions": [
            {"id": q.id, "question_text": q.question_text, "regulatory_basis": q.regulatory_basis,
             "is_accepted": q.is_accepted,
             **scope_sources.describe(q.source, q.source_ref)}
            for q in questions
        ],
    }


@router.patch("/planning/{engagement_id}/scope")
async def update_scope(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
    scope = result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id)
        db.add(scope)
    for key in ("overall_objective", "scope_period", "scope_entity"):
        if key in payload:
            setattr(scope, key, payload[key])
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/scope/items")
async def add_scope_item(engagement_id: str, payload: ScopeItemCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
    scope = result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id)
        db.add(scope)
        await db.flush()
    item = ScopeItem(
        id=str(uuid4()), scope_id=scope.id, item_type=payload.item_type,
        description=payload.description, rationale=payload.rationale,
        is_accepted=True, **scope_sources.stamp(scope_sources.MANUAL),
    )
    db.add(item)
    await db.commit()
    return {"id": item.id}


@router.patch("/scope-items/{item_id}")
async def update_scope_item(item_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    item = await db.get(ScopeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for key in ("description", "rationale", "item_type", "is_accepted"):
        if key in payload:
            setattr(item, key, payload[key])
    await db.commit()
    return {"ok": True}


@router.delete("/scope-items/{item_id}", status_code=204)
async def delete_scope_item(item_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(ScopeItem, item_id)
    if item:
        await db.delete(item)
        await db.commit()


@router.post("/planning/{engagement_id}/scope/questions")
async def add_question(engagement_id: str, payload: QuestionCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
    scope = result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id)
        db.add(scope)
        await db.flush()
    q = KeyAuditQuestion(
        id=str(uuid4()), scope_id=scope.id, question_text=payload.question_text,
        regulatory_basis=payload.regulatory_basis, is_accepted=True,
        **scope_sources.stamp(scope_sources.MANUAL),
    )
    db.add(q)
    await db.commit()
    return {"id": q.id}


@router.patch("/questions/{question_id}")
async def update_question(question_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    q = await db.get(KeyAuditQuestion, question_id)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    for key in ("question_text", "regulatory_basis", "is_accepted"):
        if key in payload:
            setattr(q, key, payload[key])
    await db.commit()
    return {"ok": True}


@router.delete("/questions/{question_id}", status_code=204)
async def delete_question(question_id: str, db: AsyncSession = Depends(get_db)):
    q = await db.get(KeyAuditQuestion, question_id)
    if q:
        await db.delete(q)
        await db.commit()


# ───────────────────────── Frameworks & Requirements ─────────────────────────

@router.get("/frameworks/library")
async def framework_library(entity: str | None = None):
    if entity:
        return frameworks_for_entity(entity)
    return FRAMEWORK_LIBRARY


def _group_frameworks_with_requirements(frameworks, items: list[dict]) -> list[dict]:
    by_id = {f.id: f for f in frameworks}
    by_code = {f.framework_code: f for f in frameworks}
    items_by_fw_id: dict[str, list[dict]] = {f.id: [] for f in frameworks}

    for item in items:
        fw = by_id.get(item.get("framework_id")) or by_code.get(item.get("framework_code"))
        if fw:
            items_by_fw_id[fw.id].append(item)

    return [
        {
            "id": f.id, "framework_code": f.framework_code, "framework_name": f.framework_name,
            "applicability_rationale": f.applicability_rationale,
            "specific_provision": f.specific_provision,
            "source_url": f.source_url,
            "confidence": f.confidence or "medium",
            "jurisdiction": f.jurisdiction or "",
            "category": f.category or "law",
            "is_primary": f.is_primary, "is_accepted": f.is_accepted, "source": f.source,
            "requirements": items_by_fw_id[f.id],
        }
        for f in frameworks
    ]


@router.get("/planning/{engagement_id}/framework-requirements")
async def get_framework_requirements(engagement_id: str, db: AsyncSession = Depends(get_db)):
    # Laws & Regulations shows only binding law rows — supervisory guidance
    # (category='guidance') has its own module and must not appear here.
    frameworks = (await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.category != "guidance",
        )
    )).scalars().all()

    rr_result = await db.execute(
        select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
    )
    rr = rr_result.scalar_one_or_none()
    items = _loads(rr.items, []) if rr else []

    return {
        "status": rr.status if rr else "not_started",
        "frameworks": _group_frameworks_with_requirements(frameworks, items),
    }


# ── Auto-analyse endpoints — must come BEFORE /frameworks/{framework_id} ──

@router.post("/planning/{engagement_id}/framework-requirements/analyse")
async def analyse_framework_requirements(
    engagement_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger the unified analysis if not already done (or if the previous run failed)."""
    existing = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "framework_requirements",
        ).order_by(AgentRun.created_at.desc())
    )
    run = existing.scalars().first()
    if run and run.status in ("running", "pending"):
        return {"run_id": run.id, "status": run.status, "already_running": True}
    if run and run.status == "complete":
        return {"run_id": run.id, "status": "complete", "already_done": True}

    new_run = AgentRun(
        id=str(uuid4()), engagement_id=engagement_id,
        agent_type="framework_requirements", status="pending",
        input_summary=f"Analyse frameworks & requirements for engagement {engagement_id}",
    )
    db.add(new_run)

    rr_result = await db.execute(
        select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
    )
    rr = rr_result.scalar_one_or_none()
    if not rr:
        rr = RegRequirement(id=str(uuid4()), engagement_id=engagement_id)
        db.add(rr)
    rr.status = "analysing"

    try:
        await db.commit()
    except IntegrityError:
        # Two near-simultaneous requests both passed the "no existing run" check above
        # and both tried to insert a RegRequirement row (unique per engagement_id) — treat
        # this as "another request already started it" instead of a 500.
        await db.rollback()
        other = await db.execute(
            select(AgentRun).where(
                AgentRun.engagement_id == engagement_id,
                AgentRun.agent_type == "framework_requirements",
            ).order_by(AgentRun.created_at.desc())
        )
        other_run = other.scalars().first()
        if other_run:
            return {"run_id": other_run.id, "status": other_run.status, "already_running": True}
        raise

    background_tasks.add_task(attributed(run_framework_requirements_analysis, engagement_id, "frameworks", new_run.id),
                              new_run.id, engagement_id)
    return {"run_id": new_run.id, "status": "pending"}


@router.get("/planning/{engagement_id}/framework-requirements/analyse-status")
async def get_framework_requirements_status(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Poll for framework & requirements analysis status."""
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "framework_requirements",
        ).order_by(AgentRun.created_at.desc())
    )
    run = result.scalars().first()
    if not run:
        return {"status": "not_started", "stage": None}
    stage = _loads(run.search_progress, {}).get("stage")
    return {"status": run.status, "run_id": run.id, "stage": stage}


@router.patch("/planning/{engagement_id}/framework-requirements/requirements/{item_id}")
async def patch_framework_requirement_item(
    engagement_id: str,
    item_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
    )
    rr = result.scalar_one_or_none()
    if not rr:
        raise HTTPException(status_code=404, detail="Not found")

    items = _loads(rr.items, [])
    for item in items:
        if item.get("id") == item_id:
            for key in ("control_objective", "test_approach", "is_included"):
                if key in payload:
                    item[key] = payload[key]
            break
    rr.items = json.dumps(items)
    await db.commit()
    return {"status": rr.status, "items": items}


@router.post("/planning/{engagement_id}/framework-requirements/accept")
async def accept_framework_requirements(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
    )
    rr = result.scalar_one_or_none()
    if not rr:
        raise HTTPException(status_code=404, detail="Not found")
    rr.status = "agreed"
    await db.commit()
    items = _loads(rr.items, [])
    included = sum(1 for i in items if i.get("is_included") is not False)
    return {"status": "agreed", "included": included}


@router.post("/planning/{engagement_id}/frameworks/generate-scope")
async def generate_fw_scope(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Generate scope contribution from accepted frameworks. Stores in AgentRun.accepted_output."""
    contribution = await generate_scope_contribution(engagement_id)

    # Store in the most recent framework_requirements run for retrieval
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "framework_requirements",
        ).order_by(AgentRun.created_at.desc())
    )
    run = result.scalars().first()
    if run:
        run.accepted_output = json.dumps(contribution)
        await db.commit()

    return contribution


@router.get("/planning/{engagement_id}/frameworks/scope-contribution")
async def get_fw_scope_contribution(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Return previously generated scope contribution."""
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "framework_requirements",
        ).order_by(AgentRun.created_at.desc())
    )
    run = result.scalars().first()
    if not run or not run.accepted_output:
        return {"scope_items": [], "key_questions": []}
    return _loads(run.accepted_output, {"scope_items": [], "key_questions": []})


@router.post("/planning/{engagement_id}/frameworks/publish-scope")
async def publish_fw_scope(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Publish selected scope items and questions to the Scope & Objectives module."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    scope_result = await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )
    scope = scope_result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id,
                                status="in_progress", scope_period=eng.scope_period,
                                scope_entity=eng.entity)
        db.add(scope)
        await db.flush()

    scope_items = payload.get("scope_items", [])
    key_questions = payload.get("key_questions", [])
    ref = await scope_sources.run_ref(db, engagement_id, "framework_requirements")
    items_added = 0
    questions_added = 0

    for i, item in enumerate(scope_items):
        if not item.get("description"):
            continue
        db.add(ScopeItem(
            id=str(uuid4()), scope_id=scope.id,
            item_type=item.get("item_type", "in_scope"),
            description=item["description"],
            rationale=item.get("rationale", ""),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.FRAMEWORKS, ref),
        ))
        items_added += 1

    for i, q in enumerate(key_questions):
        if not q.get("question_text"):
            continue
        db.add(KeyAuditQuestion(
            id=str(uuid4()), scope_id=scope.id,
            question_text=q["question_text"],
            regulatory_basis=q.get("regulatory_basis", ""),
            is_accepted=False, sort_order=i,
            **scope_sources.stamp(scope_sources.FRAMEWORKS, ref),
        ))
        questions_added += 1

    await db.commit()
    return {"items_added": items_added, "questions_added": questions_added}


@router.post("/planning/{engagement_id}/frameworks")
async def add_framework(engagement_id: str, payload: FrameworkAdd, db: AsyncSession = Depends(get_db)):
    fw = ApplicableFramework(
        id=str(uuid4()), engagement_id=engagement_id,
        framework_code=payload.framework_code, framework_name=payload.framework_name,
        applicability_rationale=payload.applicability_rationale or "",
        is_primary=payload.is_primary, is_accepted=True, source="manual",
    )
    db.add(fw)
    await db.commit()
    return {"id": fw.id}


@router.patch("/frameworks/{framework_id}")
async def update_framework(framework_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    fw = await db.get(ApplicableFramework, framework_id)
    if not fw:
        raise HTTPException(status_code=404, detail="Framework not found")
    for key in ("framework_name", "applicability_rationale", "specific_provision",
                "source_url", "confidence", "jurisdiction", "is_primary", "is_accepted"):
        if key in payload:
            setattr(fw, key, payload[key])
    await db.commit()
    return {"ok": True}


def _item_belongs_to_framework(item: dict, framework_id: str, framework_code: str) -> bool:
    if item.get("framework_id"):
        return item["framework_id"] == framework_id
    return item.get("framework_code") == framework_code


@router.delete("/frameworks/{framework_id}", status_code=204)
async def delete_framework(framework_id: str, db: AsyncSession = Depends(get_db)):
    fw = await db.get(ApplicableFramework, framework_id)
    if not fw:
        return
    engagement_id, framework_code = fw.engagement_id, fw.framework_code
    await db.delete(fw)

    # Cascade: drop this framework's requirement lines too, so removed frameworks
    # never silently keep feeding DRL/Work Program generation via RegRequirement.items.
    rr_result = await db.execute(
        select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
    )
    rr = rr_result.scalar_one_or_none()
    if rr and rr.items:
        items = _loads(rr.items, [])
        remaining = [i for i in items if not _item_belongs_to_framework(i, framework_id, framework_code)]
        if len(remaining) != len(items):
            rr.items = json.dumps(remaining)

    await db.commit()


# ───────────────────────── Supervisory Guidance ─────────────────────────
# Sibling of Laws & Regulations: searches supervisory authorities' soft law
# (guidelines, policy rules, good practices) and stores category='guidance' rows.

def _serialize_guidance(f: ApplicableFramework) -> dict:
    return {
        "id": f.id,
        "framework_code": f.framework_code,
        "framework_name": f.framework_name,
        "applicability_rationale": f.applicability_rationale,
        "guidance_type": f.specific_provision,   # reused column: Guideline | Policy rule | …
        "source_url": f.source_url,
        "confidence": f.confidence or "medium",
        "jurisdiction": f.jurisdiction or "",
        "is_primary": f.is_primary,
        "is_accepted": f.is_accepted,
        "source": f.source,
    }


async def _latest_guidance_run(engagement_id: str, db: AsyncSession):
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "supervisory_guidance",
        ).order_by(AgentRun.created_at.desc())
    )
    return result.scalars().first()


@router.get("/planning/{engagement_id}/supervisory-guidance")
async def get_supervisory_guidance(engagement_id: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.category == "guidance",
        )
    )).scalars().all()
    run = await _latest_guidance_run(engagement_id, db)
    return {
        "status": run.status if run else "not_started",
        "guidance": [_serialize_guidance(f) for f in rows],
    }


@router.post("/planning/{engagement_id}/supervisory-guidance/analyse")
async def analyse_supervisory_guidance(
    engagement_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger the supervisory-guidance web search (uses AI + web search — opt-in)."""
    run = await _latest_guidance_run(engagement_id, db)
    if run and run.status in ("running", "pending"):
        return {"run_id": run.id, "status": run.status, "already_running": True}

    new_run = AgentRun(
        id=str(uuid4()), engagement_id=engagement_id,
        agent_type="supervisory_guidance", status="pending",
        input_summary=f"Search supervisory guidance for engagement {engagement_id}",
    )
    db.add(new_run)
    await db.commit()

    background_tasks.add_task(attributed(run_supervisory_guidance_analysis, engagement_id, "supervisory_guidance", new_run.id),
                              new_run.id, engagement_id)
    return {"run_id": new_run.id, "status": "pending"}


@router.get("/planning/{engagement_id}/supervisory-guidance/analyse-status")
async def get_supervisory_guidance_status(engagement_id: str, db: AsyncSession = Depends(get_db)):
    run = await _latest_guidance_run(engagement_id, db)
    if not run:
        return {"status": "not_started", "stage": None}
    stage = _loads(run.search_progress, {}).get("stage")
    return {"status": run.status, "run_id": run.id, "stage": stage}


@router.post("/planning/{engagement_id}/supervisory-guidance")
async def add_supervisory_guidance(engagement_id: str, payload: FrameworkAdd, db: AsyncSession = Depends(get_db)):
    fw = ApplicableFramework(
        id=str(uuid4()), engagement_id=engagement_id,
        framework_code=payload.framework_code, framework_name=payload.framework_name,
        applicability_rationale=payload.applicability_rationale or "",
        category="guidance", is_primary=payload.is_primary,
        is_accepted=True, source="manual",
    )
    db.add(fw)
    await db.commit()
    return {"id": fw.id}
