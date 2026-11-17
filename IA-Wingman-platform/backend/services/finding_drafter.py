"""Finding drafter — turns a fieldwork observation into a report-ready 5C finding
and rates it, then a second agent challenges that rating.

Human-in-the-loop: everything is a proposal the auditor edits or overrides. The
rating challenge is deliberately a separate opinion, never an override.
"""
import json
import logging
from uuid import uuid4

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.reporting import Finding
from services.ai_service import BASE_SYSTEM_PROMPT
from services.agent_contract import run_agent
from services.agent_schemas import FindingDraft, RatingChallenge
from services.memory_context import recall_for
from services.prompt_safety import wrap_untrusted
from services.activity_service import log_activity

logger = logging.getLogger("ia.wingman")

RATINGS = ("high", "medium", "low")

DRAFTER_SYSTEM = BASE_SYSTEM_PROMPT + """

FINDING-DRAFTER ROLE:
You turn a raw internal-audit observation into a crisp, report-ready finding using the 5 C's:
- Condition: what was actually found (factual, specific).
- Criteria: the norm/standard/regulation it should meet.
- Cause: the underlying reason it happened (root cause, not a symptom).
- Effect: the consequence/risk to the organisation if unaddressed.
- Corrective action: a concrete, feasible recommendation.
Then assign a severity rating (high/medium/low) with a one-line rationale grounded in effect and likelihood.
Be precise and neutral. Do not overstate. If a C is unknown from the input, propose a reasonable draft and
keep it clearly tentative rather than inventing facts.
"""

CHALLENGE_SYSTEM = BASE_SYSTEM_PROMPT + """

RATING-CHALLENGE ROLE:
You are a second, independent reviewer. Given a finding and the drafter's proposed rating, critically assess
whether the rating is justified by the effect and criteria. Offer a genuine second opinion — you may agree or
disagree. Never assert your view as the final answer; the human decides.
"""


def finding_prompt(eng_name: str, entity: str, audit_type: str, seed: dict) -> str:
    """The drafting prompt from plain values — shared with the eval suite, so the
    score is for the prompt the agent actually sends."""
    raw_observation = (
        f"Title: {seed.get('title') or ''}\n"
        f"What was found (condition): {seed.get('condition') or '(not given)'}\n"
        f"Expected (criteria): {seed.get('criteria') or '(not given)'}\n"
        f"Cause: {seed.get('cause') or '(not given)'}\n"
        f"Effect/risk: {seed.get('effect') or '(not given)'}"
    )
    return f"""Engagement "{eng_name}" ({entity}, {audit_type}). Draft a report-ready finding.

RAW OBSERVATION:
{wrap_untrusted(raw_observation, "auditor-entered finding fields")}

Return the finding in the JSON format this request requires. Keep each field to 1-3 sentences."""


def challenge_prompt(draft: dict, memory_block: str = "") -> str:
    """The rating challenge prompt from a drafted finding — shared with the eval
    suite, which measures the judge tier on exactly this text."""
    return f"""Finding: {draft.get('title')}
Condition: {draft.get('condition')}
Criteria: {draft.get('criteria')}
Effect: {draft.get('effect')}
Proposed rating: {draft.get('rating')} — {draft.get('rating_rationale')}

{memory_block}
Give your second opinion in the JSON format this request requires."""


async def draft_finding(finding_id: str, engagement_id: str):
    """Draft the 5C + rating, then challenge the rating. Owns its own sessions."""
    async with AsyncSessionLocal() as db:
        f = await db.get(Finding, finding_id)
        eng = await db.get(Engagement, engagement_id)
        seed = {
            "title": f.title, "condition": f.condition, "criteria": f.criteria,
            "cause": f.cause, "effect": f.effect,
        }

    prompt = finding_prompt(eng.name, eng.entity, eng.audit_type, seed)

    try:
        drafted = await run_agent(
            DRAFTER_SYSTEM, prompt, FindingDraft, max_tokens=2000,
            description="Return the finding as the 5 C's, with a severity rating.",
        )
        # Validated: `rating` is one of the three by construction, so the
        # "default to medium when the model says something else" fallback that
        # used to sit here — and quietly changed a finding's severity — is gone.
        draft = drafted.data
        rating = draft.rating

        # How comparable findings were rated elsewhere is a real input to whether
        # this rating is defensible — and consistency across audits is itself an
        # audit-quality concern. It is context, not a precedent to follow.
        async with AsyncSessionLocal() as db:
            memory = await recall_for(db, engagement_id, limit=4, kinds=("finding",))
        memory_block = ("" if memory.is_empty else
                        f"\nHOW COMPARABLE FINDINGS WERE RATED ELSEWHERE\n{memory.block}\n"
                        "Consistency across audits matters, but a prior rating is not binding: "
                        "rate what is in front of you and say where you differ from precedent.\n")

        try:
            challenged = await run_agent(
                CHALLENGE_SYSTEM, challenge_prompt(draft.model_dump(), memory_block), RatingChallenge,
                max_tokens=600,
                description="Give an independent second opinion on the proposed rating.",
            )
            challenge = challenged.dump()
        except Exception:  # noqa: BLE001
            # A challenge that cannot be produced is recorded as absent rather
            # than as agreement — silence is not a second opinion.
            challenge = None

        async with AsyncSessionLocal() as db:
            f = await db.get(Finding, finding_id)
            # Never let a missing key erase what the auditor typed. These fields
            # are seeded from the auditor's own observation, so a model that
            # omits "cause" — or returns it empty — must leave that text standing
            # rather than blanking it. Only a real value replaces a real value.
            for field in ("condition", "criteria", "cause", "effect", "recommendation"):
                value = getattr(draft, field)
                if value and value.strip():
                    setattr(f, field, value.strip())
            if draft.title.strip():
                f.title = draft.title.strip()[:500]
            f.rating = rating
            f.rating_rationale = draft.rating_rationale
            f.rating_challenge = json.dumps(challenge) if challenge else None
            f.status = "ready"
            await db.commit()

        note = ("rating upheld" if not challenge or challenge["agrees"]
                else f"reviewer suggests {challenge['suggested_rating']}")
        await log_activity(
            engagement_id, "finding_drafter", "finding_ready",
            summary=f"Drafted 5C finding '{draft.title[:60]}' — rated {rating} ({note})",
            confidence=None,
        )
    except Exception:  # noqa: BLE001
        # Log the real error server-side; the finding field must not carry an
        # internal exception string into the auditor-visible UI.
        logger.exception("Finding drafter failed for finding %s", finding_id)
        async with AsyncSessionLocal() as db:
            f = await db.get(Finding, finding_id)
            f.status = "failed"
            f.rating_rationale = "AI draft could not be completed — please try again."
            await db.commit()
