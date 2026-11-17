"""Work Program Generator.

Generates the audit program rows from the planning work already done:
- processes + activities from ProcessNotes
- requirements from RegRequirements
- risk items from BackgroundRiskAssessment
- the key audit questions this audit exists to answer

Each row: process | activity | risk | control objective | test steps | the
questions it answers | the evidence its testing needs. The last two are what
let the platform say, by reference rather than by resemblance, whether a
question has a test and whether a test has been asked for.
"""
import json
import logging
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import (
    BackgroundRiskAssessment, KeyAuditQuestion, ProcessNotes, RegRequirement,
    ScopeObjectives, WorkProgram,
)
from services.memory_context import recall_for
from services.work_program_migration import rows_to_spine
from services.agent_contract import run_agent
from services.agent_schemas import WorkProgram as WorkProgramSchema

logger = logging.getLogger("ia.wingman")

SYSTEM = (
    "You are an expert internal auditor at the organisation. "
    "You create precise, audit-ready work program rows. "
    "Each row links a process/activity to its risk and the control objective to test. "
    "Test approaches must be actionable: specify walkthrough, sample size, document names where possible."
)


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


#: Provenance for nodes this agent proposed, so a re-run replaces its own.
GENERATOR_SOURCE = "work_program_generator"


async def generate_work_program(wp_id: str, engagement_id: str) -> None:
    """Background task: generate work program rows from all accepted planning data."""
    async with AsyncSessionLocal() as db:
        wp = await db.get(WorkProgram, wp_id)
        if not wp:
            return
        wp.status = "generating"
        await db.commit()

    try:
        async with AsyncSessionLocal() as db:
            eng = await db.get(Engagement, engagement_id)

            # Gather accepted process items
            pn_res = await db.execute(
                select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id)
            )
            pn = pn_res.scalar_one_or_none()
            process_items = _loads(pn.process_items if pn else None, [])
            included_processes = [p for p in process_items if p.get("is_included") is not False]

            # Gather regulatory requirements
            rr_res = await db.execute(
                select(RegRequirement).where(RegRequirement.engagement_id == engagement_id)
            )
            rr = rr_res.scalar_one_or_none()
            req_items = _loads(rr.items if rr else None, [])
            included_reqs = [r for r in req_items if r.get("is_included") is not False]

            # The questions this audit exists to answer. The generator did not
            # read them at all, which is why `coverage_service` check 5 had to
            # compare the wording of a question against the wording of a test:
            # the two had never been introduced.
            scope = (await db.execute(
                select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
            )).scalar_one_or_none()
            questions = []
            if scope:
                rows = (await db.execute(
                    select(KeyAuditQuestion).where(KeyAuditQuestion.scope_id == scope.id)
                    .order_by(KeyAuditQuestion.sort_order)
                )).scalars().all()
                # Accepted ones if the auditor has been through them; all of
                # them if nobody has, because a question nobody has ruled on is
                # still a question this audit is meant to answer.
                questions = [q for q in rows if q.is_accepted] or list(rows)

            # Gather BRA risk items
            bra_res = await db.execute(
                select(BackgroundRiskAssessment).where(
                    BackgroundRiskAssessment.engagement_id == engagement_id
                )
            )
            bra = bra_res.scalar_one_or_none()
            risk_items = _loads(bra.risk_items if bra else None, [])
            accepted_risks = [r for r in risk_items if r.get("is_accepted")]

            # What earlier audits actually found on this topic is the best
            # available evidence about which controls are worth testing here.
            memory = await recall_for(db, engagement_id, limit=6, kinds=("finding", "control", "risk"))

        # Build context summary
        process_ctx = ""
        if included_processes:
            lines = []
            for p in included_processes[:10]:
                activities = ", ".join(a["name"] for a in p.get("activities", [])[:5])
                lines.append(f"- {p['name']}: {p.get('description', '')} | Activities: {activities}")
            process_ctx = "IN-SCOPE PROCESSES:\n" + "\n".join(lines)

        req_ctx = ""
        if included_reqs:
            lines = [
                f"- {r.get('provision', '')}: {r.get('control_objective', '')} | Test: {r.get('test_approach', '')}"
                for r in included_reqs[:10]
            ]
            req_ctx = "\nREGULATORY REQUIREMENTS:\n" + "\n".join(lines)

        # Short refs in the prompt, real ids on the way back: a model asked to
        # echo a uuid gets one character wrong often enough to matter, and a
        # ref that does not resolve is indistinguishable from a row that
        # answers nothing.
        q_by_ref = {f"Q{i + 1}": q for i, q in enumerate(questions)}
        question_ctx = ""
        if q_by_ref:
            lines = [f"- {ref}: {q.question_text}" for ref, q in q_by_ref.items()]
            question_ctx = ("\nKEY AUDIT QUESTIONS — the questions this audit "
                            "exists to answer:\n" + "\n".join(lines))

        risk_ctx = ""
        if accepted_risks:
            lines = [
                f"- {r.get('ref', '')}: {r.get('description', '')} (Residual: {r.get('residual_risk', 'Medium')})"
                for r in accepted_risks[:10]
            ]
            risk_ctx = "\nACCEPTED RISKS:\n" + "\n".join(lines)

        prompt = f"""Generate the work program for this internal audit.

Audit: {eng.name}
Entity: {eng.entity}
Audit type: {eng.audit_type}

{process_ctx}
{req_ctx}
{question_ctx}
{risk_ctx}

{memory.block if not memory.is_empty else ''}

Generate work program rows. Each row covers one process-activity combination and its associated control test.
Return the rows in the JSON format this request requires. Its schema carries each field's
meaning, so what follows is only the judgement it cannot express.

Rules:
- Generate 8-14 rows, and stop. The whole answer must fit in one reply: this
  engagement has seven in-scope processes with three activities each, and a row
  for every one of them does not fit. Choose the control points that carry the
  risk
- One row per significant control point, not one per activity
- Derive from the processes, requirements, and risks above
- Where a prior audit found something on this topic, make sure a row tests whether it still
  holds here, and name that audit in the risk_description. Do not assume the finding recurs —
  the point is to look, not to conclude
- risk_description: concrete, specific (not generic "there is a risk")
- test_steps: an ORDERED list of 3-4 short, imperative test steps (obtain population →
  sample → inspect/re-perform → evaluate → conclude). Mention sample sizes where
  appropriate (e.g. "sample 25 files"). Each step is one short sentence.
- answers: the refs from KEY AUDIT QUESTIONS this row helps answer, usually one
  and sometimes none. Between them the rows should answer every question listed;
  a question left with no row is a gap the auditor needs to see, so do not
  stretch a row to cover one it does not really test
- evidence: 1-2 items for the row as a whole, not per step — the steps of one
  row share their documents. Name what the auditee would recognise, and name a
  department that exists rather than inventing a function. Mark an interview or
  an observation as such: those are arranged, not requested
- Keep every string under 160 characters. A row nobody can read in one line is
  not more audit-ready, and the answer has to fit
"""
        # The tool is forced, so there is no prose path left to parse around.
        # On the untyped path this run produced valid-looking JSON that would
        # not parse about one time in two, and a whole generation was lost to a
        # stray character — expensive, and invisible to the auditor watching a
        # spinner. A schema violation now comes back as a named error after the
        # model has been shown it once, instead of as "No JSON found".
        result = await run_agent(
            SYSTEM, prompt, WorkProgramSchema, max_tokens=12_000,
            description="Return the work program rows.",
        )
        rows = [r.model_dump() for r in result.data.rows]

        for i, row in enumerate(rows):
            row["id"] = f"wp_{i + 1}"
            # Not in the schema: nothing is in progress the moment it is drafted,
            # and a field whose only allowed value is a constant teaches the
            # model nothing.
            row["status"] = "not_started"
            # Refs back to real ids here, where the mapping is still in hand.
            # A ref the model invented resolves to nothing and is dropped,
            # which reads downstream as "this row answers no question" — true,
            # and better than a link to a question that does not exist.
            row["answers"] = [q_by_ref[r].id for r in (row.get("answers") or [])
                              if r in q_by_ref]

        async with AsyncSessionLocal() as db:
            wp = await db.get(WorkProgram, wp_id)
            if wp:
                wp.status = "ready"
                # The rows go into the spine, not into the blob. `wp.rows` holds
                # one thing now: the snapshot taken when the auditor signs.
                await rows_to_spine(db, engagement_id, rows, source_type=GENERATOR_SOURCE)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        # `exc` was bound and never used: a generation that hit the token
        # ceiling put the work program back to `draft` and told nobody — not
        # the auditor watching the screen, and not the log. It took a run that
        # produced nothing to notice the run had failed at all.
        logger.exception("Work program generation failed for %s: %s", engagement_id, exc)
        async with AsyncSessionLocal() as db:
            wp = await db.get(WorkProgram, wp_id)
            if wp:
                wp.status = "draft"
                wp.rows = json.dumps([])
            await db.commit()
