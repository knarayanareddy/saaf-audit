from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.planning import ScopeObjectives, ScopeItem
from models.racm import RacmTest
from services.model_tiers import QUICK
from services.ai_service import (
    stream_chat, run_text, BASE_SYSTEM_PROMPT, CHAT_STYLE_BRIEF, CHAT_STYLE_DETAILED,
)
from services.prompt_safety import wrap_untrusted
from services import copilot_service, copilot_orchestrator
from services.orchestrator import compute_engagement_pack
from services import briefing_service
from routers.engagements import serialize as serialize_engagement
from schemas import ChatRequest, ChatMessage, SummarySuggestRequest, NameSuggestRequest, ImproveTextRequest

router = APIRouter()

# The AI helper endpoints (improve-text, suggest-*) call the model synchronously.
# If the model call fails (missing/expired ANTHROPIC_API_KEY, exhausted quota, or a
# transient outage) surface a clean, actionable 503 instead of an opaque 500 so the
# auditor knows it's a configuration/quota issue, not an app bug.
_AI_UNAVAILABLE = (
    "AI service unavailable — check the ANTHROPIC_API_KEY and remaining quota "
    "in backend/.env, then try again."
)


async def _ai_or_503(system: str, prompt: str, **kw) -> str:
    try:
        return await run_text(system, prompt, **kw)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=_AI_UNAVAILABLE) from exc


@router.post("/ai/chat")
async def chat(payload: ChatRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    brief = payload.verbosity == "brief"
    system_prompt = BASE_SYSTEM_PROMPT + (CHAT_STYLE_BRIEF if brief else CHAT_STYLE_DETAILED)
    session_id = None
    if payload.engagement_id:
        eng = await db.get(Engagement, payload.engagement_id)
        if eng:
            # Reactive trigger runs FIRST, before this turn's context is built —
            # otherwise a gate-free stage (e.g. Topic Intelligence) that becomes
            # eligible on THIS very turn gets auto-started a moment after the
            # LLM already read the pack as "not started" and proposed running
            # it itself. Scanning first means the pack below reflects the
            # post-scan state, so the LLM sees it's already in progress.
            if not await copilot_service.is_autonomy_paused(payload.engagement_id):
                await copilot_orchestrator.scan_and_queue(payload.engagement_id, background_tasks)
                await copilot_orchestrator.scan_and_queue_items(payload.engagement_id, background_tasks)
                await copilot_orchestrator.check_report_draft_settle(payload.engagement_id)
                await copilot_orchestrator.maybe_notify_coherence_settle(payload.engagement_id)

            system_prompt += (
                f"\n\nCURRENT ENGAGEMENT CONTEXT:\n"
                f"Audit: {eng.name}\nAudit code: {eng.audit_code or 'none'}\nEntity: {eng.entity}\n"
                f"Type: {eng.audit_type}\n"
                f"The user is currently working on this engagement.\n"
                f"Details of this audit can be changed in two ways: by the user with the pencil next to "
                f"the active engagement in the left sidebar (name, code, entity, type, status, dates, "
                f"team), or by you proposing a correction of the name, code, summary, lead auditor or "
                f"scope period with propose_update_engagement_details. Never tell the user you are unable "
                f"to change the audit's name, and never say you do not know where it can be edited."
            )
            pack = await compute_engagement_pack(payload.engagement_id, db)
            system_prompt += f"\nLifecycle: {pack['summary']}\n"

            in_progress = [s["label"] for s in pack["stages"] if s["status"] == "in_progress"]
            if in_progress:
                system_prompt += (
                    f"\nCurrently running in the background (do NOT propose running these again — "
                    f"they will appear in the Ready for Review queue once done): {', '.join(in_progress)}\n"
                )

            # M9: the same deterministic rules the Dashboard's Daily Briefing
            # uses (briefing_service.py, a Python port of frontend/src/lib/
            # briefing.js), scoped to just this engagement — lets the copilot
            # bring up an overdue/looming deadline unprompted in conversation.
            deadline_items = briefing_service.build_briefing([serialize_engagement(eng)], datetime.utcnow())
            if deadline_items:
                system_prompt += f"\nDeadline/ownership signals for this engagement:\n{briefing_service.format_digest(deadline_items)}\n"

            tests = (await db.execute(
                select(RacmTest).where(
                    RacmTest.engagement_id == payload.engagement_id,
                    RacmTest.exceptions_count.isnot(None), RacmTest.exceptions_count > 0,
                )
            )).scalars().all()
            if tests:
                lines = "\n".join(f'- id={t.id} title="{t.title}" exceptions={t.exceptions_count}' for t in tests[:10])
                system_prompt += f"\nRACM tests with exceptions (candidates to promote to a finding):\n{lines}\n"

            session_id = await copilot_service.get_or_create_session(payload.engagement_id)
            last = payload.messages[-1] if payload.messages else None
            if last and last.role == "user":
                await copilot_service.append_message(session_id, "user", last.content)
    else:
        # M8: no engagement open (e.g. chatting from the Dashboard) — the
        # copilot stays stateless here (like /ai/suggest-*), but still gets a
        # portfolio-wide view so it can answer "what needs my attention?"
        # across every active audit, not just one.
        active = (await db.execute(
            select(Engagement).where(Engagement.status.in_(briefing_service.ACTIVE_STATUSES))
        )).scalars().all()
        digest = briefing_service.format_digest(
            briefing_service.build_briefing([serialize_engagement(e) for e in active], datetime.utcnow())
        )
        system_prompt += (
            f"\n\nNo specific engagement is open — the user is on the portfolio Dashboard. "
            f"Here is what needs attention across all active audits:\n{digest}\n"
            f"You can suggest opening a specific engagement with the propose_open_engagement tool. "
            f"Every other tool acts on one specific engagement — do not use them here without first "
            f"establishing which engagement the user means; propose opening it instead."
        )

    on_tool_use, on_complete = None, None
    if session_id:
        async def on_tool_use(tool_name: str, tool_input: dict):
            proposal_id = await copilot_service.create_proposal(session_id, tool_name, tool_input)
            return {"proposal_id": proposal_id, "status": "pending"}

        async def on_complete(full_text: str, tool_calls: list):
            await copilot_service.append_message(session_id, "assistant", full_text, tool_calls)

    return stream_chat(
        system_prompt, [m.model_dump() for m in payload.messages],
        # A brief answer needs far less room; the cap still leaves space for a
        # tool call, which is what the larger default was really for.
        max_tokens=1200 if brief else 4096,
        on_tool_use=on_tool_use, on_complete=on_complete,
    )


@router.post("/ai/suggest-summary")
async def suggest_summary(payload: SummarySuggestRequest):
    prompt = (
        f"Write a concise 2-sentence summary describing the purpose and scope of an internal audit "
        f"engagement titled '{payload.name}' for the organisation entity {payload.entity}"
        + (f" (audit type: {payload.audit_type})" if payload.audit_type else "")
        + ". Be specific to the regulatory and business context. Return only the summary text, no preamble."
    )
    text = await _ai_or_503(BASE_SYSTEM_PROMPT, prompt, max_tokens=256, tier=QUICK)
    return {"summary": text}


@router.post("/ai/suggest-name")
async def suggest_name(payload: NameSuggestRequest):
    prompt = (
        f"Suggest a single concise, professional internal-audit engagement title for the organisation entity "
        f"{payload.entity}"
        + (f", audit type {payload.audit_type}" if payload.audit_type else "")
        + (f", based on this topic: '{payload.hint}'" if payload.hint else "")
        + ". Return ONLY the title — no quotes, no preamble, max 8 words."
    )
    text = await _ai_or_503(BASE_SYSTEM_PROMPT, prompt, max_tokens=60, tier=QUICK)
    return {"name": text.strip().strip('"')}


@router.post("/ai/suggest-objective/{engagement_id}")
async def suggest_objective(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    in_scope = []
    scope_res = await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))
    scope = scope_res.scalar_one_or_none()
    if scope:
        items_res = await db.execute(
            select(ScopeItem).where(ScopeItem.scope_id == scope.id, ScopeItem.item_type == "in_scope")
        )
        in_scope = [i.description for i in items_res.scalars().all()]

    scope_text = "\n".join(f"- {s}" for s in in_scope) if in_scope else "(no scope items defined yet)"
    scope_block = wrap_untrusted(scope_text, "in-scope items") if in_scope else scope_text
    prompt = (
        f"Write a single clear overall audit objective for this the organisation internal audit.\n"
        f"Audit: {eng.name} ({eng.entity}, {eng.audit_type})\n"
        f"In-scope areas:\n{scope_block}\n\n"
        f"Use the standard IIA phrasing 'To assess the design and operating effectiveness of…'. "
        f"Return ONLY the objective sentence, no preamble."
    )
    text = await _ai_or_503(BASE_SYSTEM_PROMPT, prompt, max_tokens=200, tier=QUICK)
    return {"objective": text.strip()}


@router.post("/ai/improve-text")
async def improve_text(payload: ImproveTextRequest, db: AsyncSession = Depends(get_db)):
    """Improve or rephrase a field value. Uses engagement context if provided."""
    engagement_ctx = ""
    if payload.engagement_id:
        eng = await db.get(Engagement, payload.engagement_id)
        if eng:
            engagement_ctx = (
                f"\nCurrent engagement: {eng.name} ({eng.entity}, {eng.audit_type})\n"
            )

    # The instruction is the dominant task and goes AFTER the fenced current text
    # (recency) with an explicit "apply the change" directive — otherwise the model
    # tends to only polish the existing wording and ignore a substantive request.
    if payload.instruction.strip():
        task = (
            f"TASK: Rewrite the field so it satisfies this instruction:\n"
            f"\"{payload.instruction.strip()}\"\n"
            f"Apply the requested change to the content itself — add, remove or change what the "
            f"text says, not just its wording. Keep everything else professional and consistent. "
            f"Write in clear, professional English."
        )
    else:
        task = (
            "TASK: Improve the clarity, specificity and professional quality of the text without "
            "changing its meaning. Write in clear, professional English."
        )

    prompt = (
        f"You are editing a field labelled '{payload.field_label}' in an internal audit document.{engagement_ctx}\n"
        f"CURRENT TEXT:\n{wrap_untrusted(payload.text, 'field text to edit')}\n\n"
        f"{task}\n\n"
        f"Return ONLY the resulting field text. No preamble, no explanation, no quotes."
    )
    text = await _ai_or_503(BASE_SYSTEM_PROMPT, prompt, max_tokens=1000)
    return {"improved": text.strip()}
