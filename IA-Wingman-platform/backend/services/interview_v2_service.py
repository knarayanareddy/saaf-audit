"""Interview Agent v2 + live Companion — services.

Two opt-in, human-in-the-loop agents:
1. generate_guide  — builds a persona-structured interview guide grounded in the
   engagement's Topic Intelligence risk areas, applicable frameworks and scope.
   Every question carries traceability (which risk/framework it probes) and
   follow-ups, plus a coverage check so the auditor sees what is / isn't asked.
2. run_companion   — during/after an interview the auditor pastes anonymised
   answers; the agent proposes follow-ups, observations and candidate control
   gaps, and drafts minutes. It proposes; it never concludes. Privacy-first.

Additive: the legacy TI interview cascade (services/interview_agent.py) is left
byte-for-byte untouched.
"""
import json
from uuid import uuid4

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement
from models.interview import InterviewGuide, InterviewSession
from models.planning import TopicIntelligence, ScopeObjectives, ScopeItem, KeyAuditQuestion, ApplicableFramework
from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
from services.activity_service import log_activity
from services.prompt_safety import wrap_untrusted


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


PERSONAS = [
    {"persona": "sponsor", "role_label": "Audit sponsor / senior management"},
    {"persona": "process_owner", "role_label": "Process owner (first line)"},
    {"persona": "second_line", "role_label": "Risk & compliance (second line)"},
    {"persona": "operator", "role_label": "Operational staff (first line)"},
]

GUIDE_SYSTEM = BASE_SYSTEM_PROMPT + """

INTERVIEW-GUIDE ROLE:
You design a persona-based interview guide for an internal audit. For each persona you produce a clear
goal, a warm opening, and a small set of high-signal questions. Every question must be TRACEABLE: link it
to a specific key risk area or framework where possible. Provide 1-3 follow-ups per question that dig into
evidence, exceptions and root cause. Keep questions short, open, non-leading. Do NOT invent regulations or
facts about the organisation. Where context is thin, ask broad process questions rather than fabricating.
"""


async def _gather_context(engagement_id: str, db) -> dict:
    ti = (await db.execute(select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id))).scalar_one_or_none()
    risks = _loads(ti.key_risk_areas if ti else None, [])
    fws = (await db.execute(select(ApplicableFramework).where(ApplicableFramework.engagement_id == engagement_id))).scalars().all()
    scope = (await db.execute(select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id))).scalar_one_or_none()
    in_scope, questions = [], []
    if scope:
        items = (await db.execute(select(ScopeItem).where(ScopeItem.scope_id == scope.id))).scalars().all()
        in_scope = [i.description for i in items if i.item_type == "in_scope"]
        questions = [q.question_text for q in (await db.execute(select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id))).scalars().all()]
    from services.auditee_context import load as load_auditee_context
    sme_questions = (await load_auditee_context(db, engagement_id)).sme_questions
    return {
        "sme_questions": sme_questions,
        "risks": [{"title": r.get("title", ""), "rationale": r.get("rationale", "")} for r in risks],
        "frameworks": [{"code": f.framework_code, "name": f.framework_name} for f in fws],
        "in_scope": in_scope,
        "questions": questions,
        "has_any": bool(risks or fws or in_scope or questions),
    }


async def generate_guide(guide_id: str, engagement_id: str):
    """Owns its own sessions. Builds the persona guide grounded in planning context."""
    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        ctx = await _gather_context(engagement_id, db)

    if not ctx["has_any"]:
        async with AsyncSessionLocal() as db:
            g = await db.get(InterviewGuide, guide_id)
            g.status = "no_data"
            g.personas = json.dumps([])
            g.coverage = json.dumps({"summary": "No planning context yet — run Topic Intelligence and Scope first for a grounded guide."})
            await db.commit()
        return

    risks_txt = "\n".join(f"- {r['title']}: {r['rationale']}" for r in ctx["risks"]) or "(none captured)"
    fw_txt = "\n".join(f"- {f['code']}: {f['name']}" for f in ctx["frameworks"]) or "(none captured)"
    scope_txt = "\n".join(f"- {s}" for s in ctx["in_scope"]) or "(scope not yet defined)"
    kaq_txt = "\n".join(f"- {q}" for q in ctx["questions"]) or "(none yet)"
    sme_txt = "\n".join(f"- {q}" for q in ctx["sme_questions"]) or "(none)"
    personas_txt = "\n".join(f'- "{p["persona"]}": {p["role_label"]}' for p in PERSONAS)

    prompt = f"""Design a persona-based interview guide for internal audit engagement "{eng.name}" ({eng.entity}, {eng.audit_type}).

KEY RISK AREAS:
{risks_txt}

APPLICABLE FRAMEWORKS:
{fw_txt}

IN SCOPE:
{scope_txt}

KEY AUDIT QUESTIONS:
{kaq_txt}

QUESTIONS THE TOPIC MEMO PROPOSES FOR SUBJECT-MATTER EXPERTS (the auditor ticked these):
{sme_txt}
Put each of these, worded as given, under the persona who can best answer it (process owner or second line, usually) and count it in that persona's questions.

Build a guide for exactly these personas:
{personas_txt}

Return ONLY a JSON object:
{{
  "personas": [
    {{
      "persona": "sponsor",
      "role_label": "Audit sponsor / senior management",
      "goal": "one sentence on what to learn from this persona",
      "opening": "a short, warm opening line the auditor can say",
      "questions": [
        {{
          "text": "short open question",
          "follow_ups": ["probe 1", "probe 2"],
          "traceability": {{"type": "risk|framework|scope", "ref": "the risk title or framework code it probes"}}
        }}
      ]
    }}
  ],
  "coverage": {{
    "summary": "1-2 sentences on how well the guide covers the key risks",
    "covered": ["risk area or framework that IS probed"],
    "gaps": ["risk area or framework NOT yet probed by any question"]
  }}
}}
Guidelines: sponsor 4-6 questions (strategy, risk appetite, known issues); process_owner 6-8 (walk-throughs, exceptions, evidence); second_line 5-7 (monitoring, control design, escalation); operator 5-7 (day-to-day, workarounds, pain points). Max 3 follow-ups per question. Keep every question one sentence."""

    try:
        # A 4-persona guide (up to ~26 questions with follow-ups + traceability) is a
        # large JSON; 4096 tokens truncated it mid-object ("No JSON found"). Give it room.
        result = await run_agent_to_json(GUIDE_SYSTEM, prompt, max_tokens=8000)
        personas = result.get("personas", []) if isinstance(result, dict) else []
        coverage = result.get("coverage", {}) if isinstance(result, dict) else {}
        async with AsyncSessionLocal() as db:
            g = await db.get(InterviewGuide, guide_id)
            g.status = "ready"
            g.personas = json.dumps(personas)
            g.coverage = json.dumps(coverage)
            await db.commit()
        n_q = sum(len(p.get("questions", [])) for p in personas)
        await log_activity(
            engagement_id, "interview_agent", "guide_ready",
            summary=f"Interview guide v2 built — {len(personas)} personas, {n_q} traceable questions",
            confidence=None,
        )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            g = await db.get(InterviewGuide, guide_id)
            g.status = "failed"
            g.coverage = json.dumps({"summary": f"Guide generation failed: {exc}"})
            await db.commit()


COMPANION_SYSTEM = BASE_SYSTEM_PROMPT + """

INTERVIEW-COMPANION ROLE:
You assist an auditor live during an interview. Given the anonymised answers the auditor pasted, you:
- propose sharp follow-up questions to close gaps and test evidence;
- surface candidate observations (things worth noting), each marked with confidence;
- flag CANDIDATE control gaps — phrase as hypotheses to verify, never as proven facts;
- draft concise minutes (bulleted, neutral, no names).
You PROPOSE; the auditor decides. Never assert a control failure as fact. Privacy: never introduce personal
names; if the auditor pasted a name, generalise it to a role.
"""


async def run_companion(session_id: str, engagement_id: str):
    """Analyse the pasted answers for one session. Owns its own sessions."""
    async with AsyncSessionLocal() as db:
        s = await db.get(InterviewSession, session_id)
        eng = await db.get(Engagement, engagement_id)
        notes = (s.notes or "").strip()
        persona = s.persona or "interviewee"

    if not notes:
        async with AsyncSessionLocal() as db:
            s = await db.get(InterviewSession, session_id)
            s.status = "ready"
            s.analysis = json.dumps({"summary": "Paste some interview answers first, then run the companion."})
            await db.commit()
        return

    prompt = f"""Engagement "{eng.name}" ({eng.entity}, {eng.audit_type}). Interview with persona: {persona}.

The auditor pasted these (anonymised) answers:
{wrap_untrusted(notes[:6000], "pasted interview answers")}

Return ONLY a JSON object:
{{
  "summary": "2-3 sentence neutral summary of what was learned",
  "follow_ups": ["sharp follow-up question the auditor could ask next"],
  "observations": [{{"text": "something worth noting", "confidence": "high|medium|low"}}],
  "control_gaps": [{{"text": "CANDIDATE control gap phrased as a hypothesis to verify", "verify": "what evidence would confirm/refute it"}}],
  "minutes": ["neutral bulleted minute line, no names"]
}}
Keep every item one sentence. Max 6 follow-ups, 6 observations, 5 control_gaps, 10 minutes. Do not assert facts you cannot support from the answers."""

    try:
        result = await run_agent_to_json(COMPANION_SYSTEM, prompt, max_tokens=3000)
        if not isinstance(result, dict):
            result = {"summary": "No structured output produced."}
        async with AsyncSessionLocal() as db:
            s = await db.get(InterviewSession, session_id)
            s.status = "ready"
            s.analysis = json.dumps(result)
            await db.commit()
        await log_activity(
            engagement_id, "interview_companion", "companion_ready",
            summary=f"Interview companion analysed {persona} answers — {len(result.get('control_gaps', []))} candidate gap(s)",
            confidence=None,
        )
    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            s = await db.get(InterviewSession, session_id)
            s.status = "failed"
            s.analysis = json.dumps({"summary": f"Companion analysis failed: {exc}"})
            await db.commit()
