import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.planning import BackgroundRiskAssessment, ScopeObjectives, ScopeItem, KeyAuditQuestion
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services import scope_sources
from services.agent_ledger import agent_context, attributed

router = APIRouter()

BG_FIELDS = ["section_strategy", "section_risk_tolerance", "section_governance", "section_frameworks"]


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def serialize_bra(bra: BackgroundRiskAssessment) -> dict:
    return {
        "id": bra.id, "engagement_id": bra.engagement_id, "status": bra.status,
        **{f: getattr(bra, f, None) for f in BG_FIELDS},
        "risk_items": _loads(bra.risk_items, []),
    }


@router.get("/planning/{engagement_id}/bra")
async def get_bra(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    return serialize_bra(bra) if bra else {"status": "not_started", "risk_items": []}


@router.patch("/planning/{engagement_id}/bra")
async def update_bra(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra:
        raise HTTPException(status_code=404, detail="BRA not started")
    for key in BG_FIELDS:
        if key in payload:
            setattr(bra, key, payload[key])
    if "risk_items" in payload:
        bra.risk_items = json.dumps(payload["risk_items"])
    await db.commit()
    return {"ok": True}


@router.patch("/planning/{engagement_id}/bra/risk-items/{ref}")
async def update_risk_item(engagement_id: str, ref: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Update a single risk item by its ref (R1, R2, etc.)."""
    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra:
        raise HTTPException(status_code=404, detail="BRA not started")
    items = _loads(bra.risk_items, [])
    for item in items:
        if item.get("ref") == ref:
            item.update({k: v for k, v in payload.items() if k in (
                "link_to_anl", "description", "process", "risk_statement",
                "inherent_risk", "controls", "residual_risk", "is_accepted",
            )})
            break
    bra.risk_items = json.dumps(items)
    await db.commit()
    return {"ok": True}


@router.post("/planning/{engagement_id}/bra/draft")
async def draft_bra(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra:
        bra = BackgroundRiskAssessment(id=str(uuid4()), engagement_id=engagement_id)
        db.add(bra)

    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="bra_drafter", status="pending")
    db.add(run)
    bra.drafter_run_id = run.id
    bra.status = "drafting"
    await db.commit()

    background_tasks.add_task(attributed(_run_bra_drafter, engagement_id, "bra", run.id), bra.id, run.id, engagement_id)
    return {"run_id": run.id, "bra_id": bra.id}


@router.get("/planning/{engagement_id}/bra/export-xlsx")
async def export_bra_xlsx(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra:
        raise HTTPException(status_code=404, detail="BRA not started")

    import asyncio, json as _json
    from services.word_export import generate_bra_xlsx
    eng_data = {"name": eng.name, "audit_code": eng.audit_code, "entity": eng.entity}
    bra_data = {**{f: getattr(bra, f) for f in BG_FIELDS}, "risk_items": bra.risk_items}
    xlsx_bytes = await asyncio.get_event_loop().run_in_executor(None, generate_bra_xlsx, bra_data, eng_data)
    filename = f"BRA-{eng.audit_code or eng.name[:20].replace(' ','-')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _run_bra_drafter(bra_id: str, run_id: str, engagement_id: str):
    from services.bra_drafter import run_bra_drafter
    await run_bra_drafter(bra_id, run_id, engagement_id)


# ── Scope & Objectives contribution ──────────────────────────────────────────

@router.post("/planning/{engagement_id}/bra/generate-scope")
async def bra_generate_scope(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Generate scope items + key questions from accepted BRA risk items."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra:
        return {"scope_items": [], "key_questions": []}

    risk_items = _loads(bra.risk_items, [])
    accepted = [r for r in risk_items if r.get("is_accepted")]
    if not accepted:
        accepted = risk_items  # fall back to all if none explicitly accepted

    risks_text = "\n".join(
        f"- [{r.get('ref','?')}] {r.get('risk_statement') or r.get('description','')}"
        f" | Residual: {r.get('residual_risk','?')}"
        for r in accepted[:10]
    )

    prompt = f"""Based on the following accepted background risk assessment risks for this internal audit,
generate a scope contribution (scope items + key audit questions).

Audit: {eng.name}
Entity: {eng.entity}
Audit type: {eng.audit_type}

ACCEPTED RISKS:
{risks_text}

Return ONLY valid JSON (no explanation, no markdown):
{{
  "scope_items": [
    {{
      "item_type": "in_scope",
      "description": "Concise scope item derived from the risk",
      "rationale": "Link to specific risk (e.g. R1 — high residual risk)"
    }}
  ],
  "key_questions": [
    {{
      "question_text": "Key audit question addressing this risk",
      "regulatory_basis": "Risk reference (e.g. R2 — Controls adequacy)"
    }}
  ]
}}

Rules: 3-5 in_scope items + 3-5 key questions. Focus on HIGH residual risks.
"""
    with agent_context(engagement_id=engagement_id, agent="bra"):
        contribution = await run_agent_to_json(BASE_SYSTEM_PROMPT, prompt, max_tokens=2000)
    if not isinstance(contribution, dict):
        contribution = {"scope_items": [], "key_questions": []}

    # Store in a bra_scope AgentRun for retrieval
    run_res = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "bra_scope",
        ).order_by(AgentRun.created_at.desc())
    )
    scope_run = run_res.scalars().first()
    if not scope_run:
        scope_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id,
                             agent_type="bra_scope", status="complete")
        db.add(scope_run)
    scope_run.accepted_output = json.dumps(contribution)
    await db.commit()
    return contribution


@router.get("/planning/{engagement_id}/bra/scope-contribution")
async def bra_get_scope(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Return previously generated scope contribution."""
    result = await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "bra_scope",
        ).order_by(AgentRun.created_at.desc())
    )
    run = result.scalars().first()
    if not run or not run.accepted_output:
        return {"scope_items": [], "key_questions": []}
    return _loads(run.accepted_output, {"scope_items": [], "key_questions": []})


@router.post("/planning/{engagement_id}/bra/publish-scope")
async def bra_publish_scope(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Publish selected scope items and key questions to Scope & Objectives."""
    scope_result = await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )
    scope = scope_result.scalar_one_or_none()
    if not scope:
        scope = ScopeObjectives(id=str(uuid4()), engagement_id=engagement_id, status="in_progress")
        db.add(scope)
        await db.commit()
        await db.refresh(scope)

    ref = await scope_sources.run_ref(db, engagement_id, "bra_scope")

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
            **scope_sources.stamp(scope_sources.BRA, ref),
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
            **scope_sources.stamp(scope_sources.BRA, ref),
        ))
        q_added += 1

    await db.commit()
    return {"scope_items_added": items_added, "questions_added": q_added}
