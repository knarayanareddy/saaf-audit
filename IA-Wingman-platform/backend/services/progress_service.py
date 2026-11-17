from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.planning import (
    TopicIntelligence,
    ScopeObjectives,
    ScopeItem,
    KeyAuditQuestion,
    ApplicableFramework,
    ProcessNotes,
    AuditNotificationLetter,
    KickoffAgenda,
    BackgroundRiskAssessment,
    RegRequirement,
    ResourcePlan,
    WorkProgram,
    DRLDocument,
)
from models.agent_run import AgentRun
import json as _json
from services.work_program_view import rows_for as _wp_rows


async def topic_intelligence_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
    )
    ti = result.scalar_one_or_none()
    if not ti:
        return 0
    return {
        "not_started": 0,
        "agents_pending": 25,
        "review": 60,
        "agreed": 100,
    }.get(ti.status, 0)


async def process_notes_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id)
    )
    pn = result.scalar_one_or_none()
    if not pn:
        return 0
    if pn.status == "agreed":
        return 100
    if pn.status in ("draft_ready", "generating", "reasoning_ready", "reasoning"):
        return 50
    return 100 if pn.notes and pn.notes.strip() else 0


async def scope_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )
    scope = result.scalar_one_or_none()
    if not scope:
        return 0
    items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
    questions = (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all()
    total = len(items) + len(questions)
    if total == 0:
        return 0
    accepted = sum(1 for x in [*items, *questions] if x.is_accepted)
    return min(int(accepted / total * 100), 100)


async def framework_requirements_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(RegRequirement).where(RegRequirement.engagement_id == engagement_id))
    rr = result.scalar_one_or_none()
    if not rr or rr.status == "not_started":
        return 0
    if rr.status == "analysing":
        return 25
    if rr.status == "draft_ready":
        return 50
    if rr.status == "agreed":
        import json as _j
        items = _j.loads(rr.items or "[]")
        included = sum(1 for i in items if i.get("is_included") is not False)
        return 100 if included else 50
    return 0


async def anl_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(
        select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id)
    )
    anl = result.scalar_one_or_none()
    if not anl:
        return 0
    return {
        "not_started": 0,
        "drafting": 15,
        "draft_ready": 40,
        "review_pending": 55,
        "reviewed": 75,
        "head_ia_review": 90,
        "approved": 100,
        "sent": 100,
    }.get(anl.status, 0)


async def kickoff_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    if not a:
        return 0
    return 100 if a.status == "draft_ready" else (25 if a.status == "drafting" else 0)


async def bra_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra:
        return 0
    if bra.status == "draft_ready":
        import json as _j
        items = _j.loads(bra.risk_items or "[]") if bra.risk_items else []
        if not items:
            return 50
        accepted = sum(1 for i in items if i.get("is_accepted"))
        return min(50 + int(accepted / len(items) * 50), 100)
    return 25 if bra.status == "drafting" else 0


async def _ti_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))
    ti = result.scalar_one_or_none()
    if not ti: return "Not started"
    return {"not_started": "Not started", "agents_pending": "Agents running…",
            "review": "Memo ready for review", "agreed": "Memo agreed"}.get(ti.status, "In progress")


async def _pn_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id))
    pn = result.scalar_one_or_none()
    if not pn: return "Not started"
    import json as _j
    status = pn.status or "not_started"
    if status == "agreed":
        items = _j.loads(pn.process_items or "[]")
        included = sum(1 for it in items if it.get("is_included") is not False)
        return f"{included} processes mapped"
    if status == "draft_ready":
        items = _j.loads(pn.process_items or "[]")
        return f"{len(items)} proposals — review pending"
    if status in ("reasoning", "generating"):
        return "Analysing…"
    if status == "reasoning_ready":
        return "Reasoning ready — approve to continue"
    return "Not started"


async def supervisory_guidance_progress(engagement_id: str, db: AsyncSession) -> int:
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "supervisory_guidance",
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if run and run.status in ("pending", "running"):
        return 25
    if run and run.status == "complete":
        return 100
    count = len((await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.category == "guidance",
        )
    )).scalars().all())
    return 100 if count else 0


async def _guidance_label(engagement_id: str, db: AsyncSession) -> str:
    rows = (await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.category == "guidance",
        )
    )).scalars().all()
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id,
            AgentRun.agent_type == "supervisory_guidance",
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if run and run.status in ("pending", "running"):
        return "Searching supervisory sites…"
    if run and run.status == "failed":
        return "Search failed — retry"
    if rows:
        return f"{len(rows)} guidance document{'' if len(rows) == 1 else 's'}"
    return "Not started"


async def _frw_label(engagement_id: str, db: AsyncSession) -> str:
    fws = (await db.execute(select(ApplicableFramework).where(
        ApplicableFramework.engagement_id == engagement_id,
        ApplicableFramework.category != "guidance",
    ))).scalars().all()
    result = await db.execute(select(RegRequirement).where(RegRequirement.engagement_id == engagement_id))
    rr = result.scalar_one_or_none()
    if not rr or rr.status == "not_started":
        return "Not started"
    if rr.status == "analysing":
        return "Analysing…"
    import json as _j
    items = _j.loads(rr.items or "[]")
    if rr.status == "draft_ready":
        return f"{len(fws)} frameworks, {len(items)} requirements — review pending"
    if rr.status == "agreed":
        included = sum(1 for i in items if i.get("is_included") is not False)
        return f"{len(fws)} frameworks, {included} requirements agreed"
    return "Not started"


async def _scope_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
    scope = result.scalar_one_or_none()
    if not scope: return "Nothing queued yet"
    items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
    questions = (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all()
    total = len(items) + len(questions)
    if total == 0: return "Nothing queued yet"
    accepted = sum(1 for x in [*items, *questions] if x.is_accepted)
    return f"{accepted}/{total} items accepted"


async def _anl_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == engagement_id))
    anl = result.scalar_one_or_none()
    if not anl: return "Not started"
    return {"not_started": "Not started", "drafting": "Drafting…", "draft_ready": "Draft ready",
            "review_pending": "AI review in progress…", "reviewed": "AI review complete",
            "head_ia_review": "Awaiting Head IA review", "approved": "Approved",
            "sent": "Sent to auditees"}.get(anl.status, "In progress")


async def _kickoff_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == engagement_id))
    a = result.scalar_one_or_none()
    if not a: return "Not started"
    if a.status == "draft_ready": return "Agenda drafted"
    if a.status == "drafting": return "Drafting…"
    return "Not started"


async def _bra_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id))
    bra = result.scalar_one_or_none()
    if not bra: return "Not started"
    if bra.status == "draft_ready":
        import json as _j
        items = _j.loads(bra.risk_items or "[]")
        if not items: return "Draft ready"
        accepted = sum(1 for i in items if i.get("is_accepted"))
        return f"{accepted}/{len(items)} risks accepted"
    if bra.status == "drafting": return "Drafting…"
    return "Not started"


async def _rplan_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(ResourcePlan).where(ResourcePlan.engagement_id == engagement_id))
    rp = result.scalar_one_or_none()
    if not rp: return 0
    checks = [rp.dates_confirmed, rp.hours_confirmed, rp.team_confirmed, rp.head_ia_acknowledged]
    return min(int(sum(1 for c in checks if c) / 4 * 100), 100)


async def _rplan_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(ResourcePlan).where(ResourcePlan.engagement_id == engagement_id))
    rp = result.scalar_one_or_none()
    if not rp: return "Not started"
    checks = [rp.dates_confirmed, rp.hours_confirmed, rp.team_confirmed, rp.head_ia_acknowledged]
    done = sum(1 for c in checks if c)
    if done == 4: return "All 4 checks confirmed"
    hours = f"{rp.hours_budget}h budget" if rp.hours_budget else "No hours set"
    return f"{done}/4 checks · {hours}"


async def _wp_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(WorkProgram).where(WorkProgram.engagement_id == engagement_id))
    wp = result.scalar_one_or_none()
    if not wp: return 0
    if wp.status == "signed_off": return 100
    if wp.status == "ready":
        rows = await _wp_rows(engagement_id, db)
        complete = sum(1 for r in rows if r.get("status") == "complete")
        total = len(rows)
        return 50 + int(complete / total * 50) if total else 50
    if wp.status == "generating": return 25
    return 0


async def _wp_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(WorkProgram).where(WorkProgram.engagement_id == engagement_id))
    wp = result.scalar_one_or_none()
    if not wp or wp.status == "draft": return "Not started"
    if wp.status == "signed_off": return "Signed off — Fieldwork unlocked"
    if wp.status == "generating": return "Generating rows…"
    if wp.status == "ready":
        rows = await _wp_rows(engagement_id, db)
        return f"{len(rows)} rows — pending sign-off"
    return "Not started"


async def _drl_progress(engagement_id: str, db: AsyncSession) -> int:
    result = await db.execute(select(DRLDocument).where(DRLDocument.engagement_id == engagement_id))
    drl = result.scalar_one_or_none()
    if not drl or not drl.items:
        return 0
    try:
        items = _json.loads(drl.items)
    except (TypeError, ValueError):
        items = []
    return 100 if items else 0


async def _drl_label(engagement_id: str, db: AsyncSession) -> str:
    result = await db.execute(select(DRLDocument).where(DRLDocument.engagement_id == engagement_id))
    drl = result.scalar_one_or_none()
    if not drl or not drl.items:
        return "Not started"
    try:
        items = _json.loads(drl.items)
    except (TypeError, ValueError):
        items = []
    return f"{len(items)} documents requested" if items else "Not started"


async def planning_progress(engagement_id: str, db: AsyncSession) -> dict:
    return {
        "topic_intelligence": await topic_intelligence_progress(engagement_id, db),
        "process_understanding": await process_notes_progress(engagement_id, db),
        "framework_requirements": await framework_requirements_progress(engagement_id, db),
        "supervisory_guidance": await supervisory_guidance_progress(engagement_id, db),
        "scope_objectives": await scope_progress(engagement_id, db),
        "anl": await anl_progress(engagement_id, db),
        "kickoff": await kickoff_progress(engagement_id, db),
        "bra": await bra_progress(engagement_id, db),
        "resource_plan": await _rplan_progress(engagement_id, db),
        "work_program": await _wp_progress(engagement_id, db),
        "drl": await _drl_progress(engagement_id, db),
        "labels": {
            "topic_intelligence": await _ti_label(engagement_id, db),
            "process_understanding": await _pn_label(engagement_id, db),
            "framework_requirements": await _frw_label(engagement_id, db),
            "supervisory_guidance": await _guidance_label(engagement_id, db),
            "scope_objectives": await _scope_label(engagement_id, db),
            "anl": await _anl_label(engagement_id, db),
            "kickoff": await _kickoff_label(engagement_id, db),
            "bra": await _bra_label(engagement_id, db),
            "resource_plan": await _rplan_label(engagement_id, db),
            "work_program": await _wp_label(engagement_id, db),
            "drl": await _drl_label(engagement_id, db),
        },
    }
