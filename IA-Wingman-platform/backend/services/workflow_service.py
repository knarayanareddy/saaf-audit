"""Workflow map — the audit lifecycle as a graph, for the Workflow page.

Stages, gates and live statuses come straight from services/orchestrator.py, so
the picture can never disagree with the cascade Agent Studio and the copilot
use. This module only layers presentation on top: phases, the moments where the
auditor decides, and companion agents that are deliberately NOT STAGE_GRAPH
stages — adding them there would change copilot auto-fire and review logic.

Deterministic and read-only. Unlike GET .../agents/pack it never queues copilot
work, so it is safe to poll.
"""
import json

from sqlalchemy import select, func, or_

from models.agent_run import AgentRun
from models.copilot import CopilotTask
from models.engagement import Engagement
from models.planning import ScopeObjectives, ScopeItem, KeyAuditQuestion, BackgroundRiskAssessment
from models.racm import RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence
from services.orchestrator import STAGE_GRAPH, compute_engagement_pack
from services.progress_service import planning_progress
from services.privacy_guard.agent import AGENT_TYPE as PRIVACY_AGENT
from services.vendor_guard.agent import AGENT_TYPE as VENDOR_AGENT
from services.pbc_assistant import AGENT_TYPE as PBC_AGENT

ENGAGEMENT_STATUSES = [
    {"key": "to_be_scheduled", "label": "To be scheduled"},
    {"key": "in_planning", "label": "Planning"},
    {"key": "in_fieldwork", "label": "Fieldwork"},
    {"key": "in_reporting", "label": "Reporting"},
    {"key": "closed", "label": "Closed"},
]

PHASES = [
    {"key": "planning", "label": "Planning",
     "summary": "Understand the topic, agree the scope and prepare the work program."},
    {"key": "gathering", "label": "Gathering",
     "summary": "Ask people, request documents, and match what arrives to the test it belongs to."},
    {"key": "fieldwork", "label": "Fieldwork",
     "summary": "Test controls, gather evidence and record observations."},
    {"key": "reporting", "label": "Reporting",
     "summary": "Turn observations into findings and the audit report."},
    {"key": "quality", "label": "Quality", "cross_cutting": True,
     "summary": "Cross-cutting checks you can run at any point."},
]

PHASE_OF = {
    "topic_intelligence": "planning", "frameworks": "planning", "process_understanding": "planning",
    "scope": "planning", "bra": "planning", "anl": "planning", "kickoff": "planning",
    "resource_plan": "planning", "work_program": "planning",
    # Gathering: getting information out of people and out of the auditee. It is
    # used from both sides of the sign-off — interviews happen at the kick-off
    # and again during fieldwork — but its centre of gravity is here, and one
    # band reads better than four loose companions.
    "interview_guide": "gathering", "interview_companion": "gathering", "drl": "gathering",
    # The spine is built and signed in planning — that is where the work program
    # lives and where the gate that opens fieldwork sits.
    "racm_scoping": "planning",
    # Their panels live on the Fieldwork page, so that is where the auditor meets them.
    "racm_governance": "fieldwork", "racm_data_analysis": "fieldwork",
    "racm_evidence_chase": "gathering",
    "fieldwork": "fieldwork",
    "findings": "reporting", "report_draft": "reporting",
    "quality_coverage": "quality", "quality_review": "quality", "quality_peer_review": "quality",
}

# ai = an AI agent drafts or proposes in this step (the auditor still decides).
STAGE_INFO = {
    "topic_intelligence": {"ai": True, "description": "Scans regulation, supervisory publications and public signals to explain the topic and propose key risk areas."},
    "frameworks": {"ai": True, "description": "Maps the laws, regulations and internal frameworks that apply and extracts testable requirements."},
    "process_understanding": {"ai": True, "description": "Drafts the process walkthrough and preliminary observations."},
    "scope": {"ai": True, "description": "Proposes in-scope and out-of-scope areas and the key audit questions."},
    "bra": {"ai": True, "description": "Drafts the background risk assessment for the areas in scope."},
    "anl": {"ai": True, "description": "Drafts the audit notification letter, with an AI review before sign-off."},
    "kickoff": {"ai": True, "description": "Prepares the kick-off meeting agenda."},
    "resource_plan": {"ai": False, "description": "Confirms dates, hours and the team for the engagement."},
    "interview_guide": {"ai": True, "description": "Generates persona-based interview guides traceable to risks and requirements."},
    "work_program": {"ai": True, "description": "Generates the test program from scope and risks. Your sign-off unlocks fieldwork."},
    "drl": {"ai": True, "description": "Builds the document request list for the auditee."},
    "interview_companion": {"ai": True, "description": "A live companion during interviews that turns answers into follow-ups, observations and minutes."},
    "racm_scoping": {"ai": True, "description": "Builds the objective → risk → control → test spine from scope and the risk assessment."},
    "racm_governance": {"ai": True, "description": "Assesses governance documents against the applicable frameworks and proposes gaps as risks."},
    "racm_data_analysis": {"ai": False, "description": "Runs full-population checks on the data and proposes exceptions as tests."},
    "racm_evidence_chase": {"ai": False, "description": "Matches every document that arrives to the test it belongs to, and keeps a running list of the evidence still outstanding."},
    "fieldwork": {"ai": False, "description": "Record findings, recommendations, good practices and improvements."},
    "findings": {"ai": True, "description": "Turns observations into 5C findings. A second agent challenges each rating."},
    "report_draft": {"ai": True, "description": "Assembles the audit report and overall opinion for your approval."},
    "quality_coverage": {"ai": False, "description": "Checks that every in-scope area really has risks, controls and tests behind it — so nothing you promised to cover is left unexamined."},
    "quality_review": {"ai": True, "description": "Reviews each drafted artefact for quality before anyone relies on it, and flags what must be fixed against what is merely a suggestion."},
    "quality_peer_review": {"ai": True, "description": "An independent second opinion on the whole engagement, scored criterion by criterion against the Global Internal Audit Standards. It rates only what the file actually evidences — anything not produced reads as 'not evidenced', never as a pass. It proposes the ratings; a human peer reviewer confirms them."},
}

COMPANIONS = [
    {"key": "supervisory_guidance", "label": "Supervisory Guidance", "agent": "Guidance scout",
     "phase": "planning", "route": "supervisory-guidance", "base": "planning", "gates": [], "assists": "frameworks",
     "ai": True, "description": "Searches supervisory guidance relevant to the topic and jurisdictions."},
    {"key": "rcsa_import", "label": "RCSA import", "agent": "RCSA import",
     "phase": "planning", "route": "rcsa", "base": "planning", "gates": [], "assists": "bra",
     "ai": True, "description": "Reads the risk and control self-assessment the business made about itself. An agent proposes what each column of the export holds, you confirm it once, and the next import from the same template is one click."},
    {"key": "pbc_assistant", "label": "PBC assistant", "agent": "Isabelle",
     "phase": "gathering", "route": "drl", "base": "planning", "gates": ["drl"],
     "ai": True, "description": "PBC stands for Prepared By Client: the documents the auditee has to deliver. Tracks every request, drafts the distribution email and the reminders, and checks each document as it comes in."},
    {"key": "privacy_guard", "label": "Privacy Guard", "agent": "PII masking",
     "phase": "fieldwork", "route": "fieldwork", "base": "", "gates": [],
     "ai": False, "description": "Detects personal data, classifies it per audit purpose and masks or pseudonymises it by role."},
    {"key": "vendor_guard", "label": "Vendor Guard", "agent": "Third-party risk",
     "phase": "fieldwork", "route": "fieldwork", "base": "", "gates": [],
     "ai": True, "description": "Assesses a third party against 8 curated EU/NL frameworks and proposes critical gaps into the matrix."},
]

HUMAN_GATES = [
    {"key": "agree_memo", "stage": "topic_intelligence", "label": "Agree the Topic Intelligence memo"},
    {"key": "accept_scope", "stage": "scope", "label": "Accept scope items and key audit questions"},
    {"key": "accept_risks", "stage": "bra", "label": "Accept the background risks"},
    {"key": "sign_off_work_program", "stage": "work_program", "unlocks": "fieldwork",
     "label": "Sign off the Work Program — this unlocks Fieldwork"},
    {"key": "accept_matrix", "stage": "racm_scoping", "label": "Accept or dismiss AI proposals in the matrix"},
    {"key": "confirm_findings", "stage": "findings", "label": "Confirm each finding and its rating"},
    {"key": "approve_report", "stage": "report_draft", "label": "Approve the audit report"},
]

_PROGRESS_KEY = {"frameworks": "framework_requirements", "scope": "scope_objectives"}
_ITEM_STAGE = {"finding": "findings", "interview_session": "interview_companion"}
_COMPANION_AGENT = {"privacy_guard": PRIVACY_AGENT, "vendor_guard": VENDOR_AGENT, "pbc_assistant": PBC_AGENT}


def method_map() -> dict:
    """The lifecycle as a graph, independent of any engagement."""
    nodes = []
    for s in STAGE_GRAPH:
        info = STAGE_INFO.get(s["key"], {})
        nodes.append({
            "key": s["key"], "label": s["label"], "agent": s["agent"], "route": s["route"], "base": s["base"],
            "kind": s["kind"], "gates": list(s["gates"]), "phase": PHASE_OF.get(s["key"], "planning"),
            "ai": info.get("ai", True), "description": info.get("description", ""), "companion": False,
        })
    for c in COMPANIONS:
        nodes.append({**c, "gates": list(c["gates"]), "kind": "companion", "companion": True})

    edges = []
    for n in nodes:
        for gate in n["gates"]:
            edges.append({"from": gate.split(":", 1)[0], "to": n["key"], "kind": "hard_gate" if ":" in gate else "gate"})
        if n.get("assists"):
            edges.append({"from": n["key"], "to": n["assists"], "kind": "assist"})

    return {
        "phases": PHASES,
        "statuses": ENGAGEMENT_STATUSES,
        "nodes": nodes,
        "edges": edges,
        "human_gates": HUMAN_GATES,
    }


async def engagement_workflow(engagement_id: str, db) -> dict | None:
    """method_map() with this engagement's live state layered on. None if unknown."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        return None

    wf = method_map()
    pack = await compute_engagement_pack(engagement_id, db)
    progress = await planning_progress(engagement_id, db)
    labels = progress.get("labels", {})
    pending = await _pending_decisions(engagement_id, db)
    live = {s["key"]: s for s in pack["stages"]}

    for node in wf["nodes"]:
        key = node["key"]
        if node["companion"]:
            node.update(await _companion_state(node, engagement_id, db, live, progress))
        else:
            node["status"] = live[key]["status"]
            node["detail"] = live[key]["detail"]
        pkey = _PROGRESS_KEY.get(key, key)
        if pkey != "labels" and isinstance(progress.get(pkey), int):
            node["progress"] = progress[pkey]
            node["detail"] = labels.get(pkey) or node.get("detail")
        node["pending_decisions"] = pending["by_stage"].get(key, 0)

    wf.update({
        "engagement": {
            "id": eng.id, "name": eng.name, "audit_code": eng.audit_code,
            "entity": eng.entity, "status": eng.status,
        },
        "next_gate": pack["next_gate"],
        "completed": pack["completed"],
        "total": pack["total"],
        "summary": pack["summary"],
        "pending": pending,
    })
    return wf


async def _rcsa_state(engagement_id: str, db) -> dict:
    """The RCSA companion writes an import, not an AgentRun.

    And "done" means something stricter here than elsewhere: an import that
    nobody has decided about is not finished work, because leaning on
    second-line work without assessing it is the claim this whole step exists to
    keep out of the file. So an imported RCSA with no reliance decision reads as
    in progress, and says what it is waiting for.
    """
    from models.rcsa import RcsaImport
    from services.rcsa_mapping import may_rely_on

    imports = (await db.execute(
        select(RcsaImport).where(RcsaImport.engagement_id == engagement_id)
        .order_by(RcsaImport.uploaded_at.desc())
    )).scalars().all()
    if not imports:
        return {"status": "available", "detail": "No RCSA imported yet"}

    imported = [i for i in imports if i.status == "imported"]
    if not imported:
        return {"status": "in_progress", "detail": "Uploaded — the column mapping is not confirmed yet"}

    decided = 0
    for imp in imported:
        allowed, _ = await may_rely_on(imp.id)
        decided += bool(allowed)
    rows = sum(i.row_count for i in imported)
    if decided == 0:
        return {"status": "in_progress",
                "detail": f"{rows} rows imported — no reliance decision recorded yet"}
    return {"status": "complete",
            "detail": f"{rows} rows from {len(imported)} import(s), {decided} relied on"}


async def _companion_state(node: dict, engagement_id: str, db, live: dict, progress: dict) -> dict:
    if node["gates"] and not all(live.get(g.split(":", 1)[0], {}).get("status") == "complete" for g in node["gates"]):
        return {"status": "locked", "detail": "Not available yet"}

    if node["key"] == "supervisory_guidance":
        pct = progress.get("supervisory_guidance", 0)
        status = "complete" if pct == 100 else ("in_progress" if pct > 0 else "available")
        return {"status": status, "detail": "Not started"}

    if node["key"] == "rcsa_import":
        return await _rcsa_state(engagement_id, db)

    run = (await db.execute(
        select(AgentRun)
        .where(AgentRun.engagement_id == engagement_id, AgentRun.agent_type == _COMPANION_AGENT[node["key"]])
        .order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if not run:
        return {"status": "available", "detail": "Not run yet"}
    if run.status in ("pending", "running", "waiting"):
        return {"status": "in_progress", "detail": "Running…"}
    if run.status == "complete":
        return {"status": "complete", "detail": "Last run complete"}
    return {"status": "available", "detail": "Last run failed — run it again"}


async def _pending_decisions(engagement_id: str, db) -> dict:
    """What AI has proposed that still waits for the auditor, per stage."""
    by_stage: dict[str, int] = {}

    def add(key: str, n: int) -> None:
        if n:
            by_stage[key] = by_stage.get(key, 0) + n

    rows = (await db.execute(
        select(CopilotTask.stage_key, func.count(CopilotTask.id))
        .where(CopilotTask.engagement_id == engagement_id, CopilotTask.status == "ready_for_review")
        .group_by(CopilotTask.stage_key)
    )).all()
    for key, n in rows:
        add(_ITEM_STAGE.get(key, key), n)

    matrix = 0
    for model in (RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence):
        matrix += (await db.execute(
            select(func.count()).select_from(model)
            .where(model.engagement_id == engagement_id, model.origin == "ai", model.accepted.is_(False))
        )).scalar_one()
    add("racm_scoping", matrix)

    scope = (await db.execute(
        select(ScopeObjectives).where(ScopeObjectives.engagement_id == engagement_id)
    )).scalar_one_or_none()
    if scope:
        for model in (ScopeItem, KeyAuditQuestion):
            add("scope", (await db.execute(
                select(func.count()).select_from(model)
                .where(model.scope_id == scope.id, or_(model.is_accepted.is_(False), model.is_accepted.is_(None)))
            )).scalar_one())

    bra = (await db.execute(
        select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == engagement_id)
    )).scalar_one_or_none()
    if bra and bra.risk_items:
        try:
            items = json.loads(bra.risk_items)
        except (TypeError, ValueError):
            items = []
        if isinstance(items, list):
            add("bra", sum(1 for i in items if isinstance(i, dict) and not i.get("is_accepted")))

    return {"by_stage": by_stage, "matrix": matrix, "total": sum(by_stage.values())}
