"""RACM spine — endpoints.

Deterministic CRUD over the Objective → Risk → Control → Test → Evidence chain
plus the ScopeDecision log. No AI here: agents (governance assessor, data
analysis, control testing, …) will write into these same tables in later phases,
each node carrying its origin/accepted/provenance so the chain stays herleidbaar.

Follows the house idiom: dict payloads (no separate Pydantic schemas), bare
select, dict serializers, engagement-scoped paths under the /api prefix.
"""
import json
import re
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.reporting import Finding
from models.planning import DRLDocument
from models.racm import (
    RacmObjective, RacmRisk, RacmControl, RacmTest, RacmEvidence, ScopeDecision,
)
from services.governance_assessor import run_governance_assessment, AGENT_TYPE as GOV_AGENT
from services.data_analysis import run_data_analysis, AGENT_TYPE as DATA_AGENT
from services.privacy_guard.agent import run_privacy_guard, AGENT_TYPE as PRIVACY_AGENT
from services.privacy_guard.models import MIN_JUSTIFICATION_LENGTH, Role
from services.vendor_guard.agent import run_vendor_guard, AGENT_TYPE as VENDOR_AGENT
from services import scoping_engine
from services.agent_ledger import attributed

router = APIRouter()


# node_type (URL segment) → model, parent FK field, type-specific editable fields.
# The governance fields (origin/accepted/accepted_by/confidence/provenance) are
# handled generically for every node type.
NODE_TYPES = {
    "objectives": {"model": RacmObjective, "parent": None,
                   "fields": ("ref", "title", "description")},
    "risks": {"model": RacmRisk, "parent": "objective_id",
              "fields": ("ref", "title", "description", "category", "inherent_rating")},
    "controls": {"model": RacmControl, "parent": "risk_id",
                 "fields": ("ref", "title", "description", "control_type", "frequency",
                            "owner", "design_conclusion")},
    "tests": {"model": RacmTest, "parent": "control_id",
              "fields": ("ref", "title", "description", "method", "sample_size",
                         "exceptions_count", "result", "conclusion")},
    # A row here is a need before it is met and the record after. The three
    # added fields are what makes the first half usable: who holds it, for what
    # period, and which document request settles it. Without them on this
    # editor, an engagement whose work program is already signed — and which
    # therefore cannot be regenerated — has no way to record an evidence need
    # at all.
    "evidence": {"model": RacmEvidence, "parent": "test_id",
                 "fields": ("ref", "kind", "title", "description", "source_document_id",
                            "requested_from", "period", "drl_item_id")},
}

_GOV_FIELDS = ("origin", "accepted", "accepted_by", "confidence")


def _loads(raw, default=None):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _serialize(obj) -> dict:
    """Row → JSON-safe dict: every column, provenance parsed, datetimes as ISO."""
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if col.name == "provenance":
            val = _loads(val)
        elif col.name in ("created_at", "updated_at") and val is not None:
            val = val.isoformat()
        out[col.name] = val
    return out


async def _require_engagement(engagement_id: str, db: AsyncSession) -> Engagement:
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return eng


def _spec(node_type: str) -> dict:
    spec = NODE_TYPES.get(node_type)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown node type '{node_type}'")
    return spec


def _apply_governance(obj, payload: dict, *, creating: bool) -> None:
    from services.edit_register import current_human

    if creating:
        obj.origin = (payload.get("origin") or "human").strip() or "human"
        # A human authoring a node owns it immediately; AI proposals await accept.
        obj.accepted = payload.get("accepted", obj.origin == "human")
    else:
        # Origin is fixed at creation. It used to be writable here, which let one
        # PATCH turn an AI proposal into a "human" node and erase the fact that a
        # model wrote it. Whoever edits an AI node is recorded as its editor in
        # the edit register; the node stays what it was.
        if "origin" in payload and payload["origin"] != obj.origin:
            raise HTTPException(status_code=422,
                                detail="origin is fixed at creation; edits are recorded in the edit register")
        if "accepted" in payload:
            obj.accepted = bool(payload["accepted"])
    # Who accepted is who sent the request — not whatever the payload says. The
    # frontend used to send the literal string "You".
    if obj.accepted and ("accepted" in payload or creating):
        obj.accepted_by = current_human() or payload.get("accepted_by") or "unknown"
    if "confidence" in payload:
        obj.confidence = payload["confidence"]
    if "provenance" in payload:
        prov = payload["provenance"]
        obj.provenance = json.dumps(prov) if prov is not None else None


# ── Full spine ────────────────────────────────────────────────────────────────

@router.get("/racm/{engagement_id}")
async def get_spine(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """The whole spine for an engagement as flat, parent-linked lists.

    The frontend builds the lanes and traces lineage from these; keeping the
    payload flat keeps the traversal identical in both directions.
    """
    out = {}
    for key, spec in NODE_TYPES.items():
        model = spec["model"]
        rows = (await db.execute(
            select(model).where(model.engagement_id == engagement_id)
            .order_by(model.sort_order, model.created_at)
        )).scalars().all()
        out[key] = [_serialize(r) for r in rows]
    sds = (await db.execute(
        select(ScopeDecision).where(ScopeDecision.engagement_id == engagement_id)
        .order_by(ScopeDecision.sort_order, ScopeDecision.created_at)
    )).scalars().all()
    out["scope_decisions"] = [_serialize(s) for s in sds]
    return out


# ── Scope decisions (declared before the generic node routes so the literal
#    path wins over /{node_type}) ────────────────────────────────────────────

def _scope(s: ScopeDecision) -> dict:
    return _serialize(s)


@router.post("/racm/{engagement_id}/scope-decisions")
async def create_scope_decision(engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    await _require_engagement(engagement_id, db)
    summary = (payload.get("summary") or "").strip()
    if not summary:
        raise HTTPException(status_code=422, detail="summary is required")
    last = (await db.execute(
        select(ScopeDecision).where(ScopeDecision.engagement_id == engagement_id)
        .order_by(ScopeDecision.sort_order.desc())
    )).scalars().first()
    s = ScopeDecision(
        id=str(uuid4()), engagement_id=engagement_id, summary=summary[:500],
        decision_type=payload.get("decision_type", "in_scope"),
        rationale=payload.get("rationale"), materiality=payload.get("materiality"),
        sponsor=payload.get("sponsor"), status=payload.get("status", "proposed"),
        origin=payload.get("origin", "human"),
        linked_objective_id=payload.get("linked_objective_id"),
        sort_order=(last.sort_order + 1) if last else 0,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _scope(s)


@router.patch("/racm/{engagement_id}/scope-decisions/{sid}")
async def update_scope_decision(engagement_id: str, sid: str, payload: dict, db: AsyncSession = Depends(get_db)):
    s = await db.get(ScopeDecision, sid)
    if not s or s.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Scope decision not found")
    for k in ("decision_type", "summary", "rationale", "materiality", "sponsor",
              "status", "linked_objective_id"):
        if k in payload:
            setattr(s, k, payload[k])
    await db.commit()
    await db.refresh(s)
    return _scope(s)


@router.delete("/racm/{engagement_id}/scope-decisions/{sid}")
async def delete_scope_decision(engagement_id: str, sid: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(ScopeDecision, sid)
    if not s or s.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Scope decision not found")
    await db.delete(s)
    await db.commit()
    return {"deleted": True}


# ── Planning & Scoping engine (deterministic; front-loads the spine) ─────────

@router.get("/racm/{engagement_id}/agents/scoping/preview")
async def scoping_preview(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Read-only, deterministic: what the completed planning modules would
    propose into the spine (objectives, risks, scope decisions). No writes."""
    await _require_engagement(engagement_id, db)
    return await scoping_engine.preview(engagement_id)


@router.post("/racm/{engagement_id}/agents/scoping/run")
async def scoping_run(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministically front-load the spine from the planning modules. Free —
    no AI. Writes objectives/risks/scope decisions as AI proposals (unaccepted)
    with provenance; idempotent (replaces this engine's earlier proposals)."""
    await _require_engagement(engagement_id, db)
    run_id = str(uuid4())
    counts = await scoping_engine.front_load(engagement_id, run_id)
    total = counts["objectives"] + counts["risks"] + counts["scope_decisions"]
    return {"run_id": run_id, "proposed": counts, "total": total}


# ── Governance-Document Assessor (opt-in AI; writes gap proposals into RISK) ──

def _run_out(run: AgentRun) -> dict:
    out = None
    if run.raw_output:
        try:
            out = json.loads(run.raw_output)
        except (json.JSONDecodeError, TypeError):
            out = None
    return {
        "id": run.id, "status": run.status, "input_summary": run.input_summary,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "result": out,
    }


@router.get("/racm/{engagement_id}/agents/governance-assessment")
async def get_governance_assessment(engagement_id: str, db: AsyncSession = Depends(get_db)):
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == GOV_AGENT
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if not run:
        return {"status": "none", "result": None}
    return _run_out(run)


@router.post("/racm/{engagement_id}/agents/governance-assessment/run")
async def run_governance_assessment_endpoint(
    engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    """Opt-in, uses AI budget. Assesses framework coverage and proposes gaps as
    AI risks in the spine; the auditor accepts or dismisses each one."""
    await _require_engagement(engagement_id, db)
    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id,
                   agent_type=GOV_AGENT, status="pending", document_ids="[]")
    db.add(run)
    await db.commit()
    background_tasks.add_task(attributed(run_governance_assessment, engagement_id, "racm_governance", run.id),
                              run.id, engagement_id)
    return {"id": run.id, "status": "pending"}


@router.get("/racm/{engagement_id}/agents/data-analysis")
async def get_data_analysis(engagement_id: str, db: AsyncSession = Depends(get_db)):
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == DATA_AGENT
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if not run:
        return {"status": "none", "result": None}
    return _run_out(run)


@router.post("/racm/{engagement_id}/agents/data-analysis/run")
async def run_data_analysis_endpoint(
    engagement_id: str, background_tasks: BackgroundTasks, narrate: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Deterministic full-population analysis (free) → exceptions proposed as tests
    in the spine. `narrate=true` adds an opt-in AI plain-language explanation."""
    await _require_engagement(engagement_id, db)
    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id,
                   agent_type=DATA_AGENT, status="pending", document_ids="[]")
    db.add(run)
    await db.commit()
    background_tasks.add_task(attributed(run_data_analysis, engagement_id, "racm_data_analysis", run.id),
                              run.id, engagement_id, narrate)
    return {"id": run.id, "status": "pending"}


# ── Privacy Guard: deterministic GDPR data-minimisation over the dataset ─────

@router.get("/racm/{engagement_id}/agents/privacy-guard")
async def get_privacy_guard(engagement_id: str, db: AsyncSession = Depends(get_db)):
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == PRIVACY_AGENT
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if not run:
        return {"status": "none", "result": None}
    return _run_out(run)


@router.post("/racm/{engagement_id}/agents/privacy-guard/run")
async def run_privacy_guard_endpoint(
    engagement_id: str, background_tasks: BackgroundTasks,
    role: str = "auditor", purpose: str = "customer_due_diligence",
    justification: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Deterministic PII scan (free): detect → classify per purpose → mask per
    role → tamper-evident audit trail. Writes nothing into the spine. Admin
    (unmasked) access requires a justification, recorded in the trail."""
    await _require_engagement(engagement_id, db)

    try:
        selected_role = Role(role)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"unknown role '{role}'")
    if selected_role == Role.ADMIN and len((justification or "").strip()) < MIN_JUSTIFICATION_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(f"admin (unmasked) access requires a justification of at least "
                    f"{MIN_JUSTIFICATION_LENGTH} characters"),
        )

    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id,
                   agent_type=PRIVACY_AGENT, status="pending", document_ids="[]")
    db.add(run)
    await db.commit()
    background_tasks.add_task(
        attributed(run_privacy_guard, engagement_id, "privacy_guard", run.id),
        run.id, engagement_id, role, purpose, justification
    )
    return {"id": run.id, "status": "pending"}


@router.get("/racm/{engagement_id}/agents/privacy-guard/audit-trail")
async def get_privacy_guard_audit_trail(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Return the latest Privacy Guard run's audit trail as JSONL for download."""
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == PRIVACY_AGENT
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    jsonl = ""
    if run and run.raw_output:
        try:
            result = json.loads(run.raw_output)
            entries = result.get("audit_trail", []) if isinstance(result, dict) else []
            jsonl = "\n".join(json.dumps(e, separators=(",", ":")) for e in entries)
        except (json.JSONDecodeError, TypeError):
            jsonl = ""
    return Response(
        content=jsonl,
        media_type="application/jsonl",
        headers={"Content-Disposition": 'attachment; filename="privacy_audit_trail.jsonl"'},
    )


# ── Vendor Guard: third-party risk assessment (opt-in AI) ────────────────────

@router.get("/racm/{engagement_id}/agents/vendor-guard")
async def get_vendor_guard(engagement_id: str, db: AsyncSession = Depends(get_db)):
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == VENDOR_AGENT
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if not run:
        return {"status": "none", "result": None}
    return _run_out(run)


@router.post("/racm/{engagement_id}/agents/vendor-guard/run")
async def run_vendor_guard_endpoint(
    engagement_id: str, background_tasks: BackgroundTasks,
    payload: dict | None = None, db: AsyncSession = Depends(get_db),
):
    """Opt-in AI: assess selected vendor documents against the applicable curated
    frameworks -> RAG scorecard + gap register (+ optional memo, + optional
    Critical/High gap proposals into the spine). Nothing is decided automatically."""
    await _require_engagement(engagement_id, db)
    p = payload or {}
    run = AgentRun(id=str(uuid4()), engagement_id=engagement_id,
                   agent_type=VENDOR_AGENT, status="pending", document_ids="[]")
    db.add(run)
    await db.commit()
    background_tasks.add_task(
        attributed(run_vendor_guard, engagement_id, "vendor_guard", run.id),
        run.id, engagement_id,
        p.get("vendor_name", ""), bool(p.get("is_ai_system")), bool(p.get("is_dutch_government")),
        p.get("document_ids") or [], bool(p.get("draft_memo")), bool(p.get("propose_to_spine")),
    )
    return {"id": run.id, "status": "pending"}


@router.get("/racm/{engagement_id}/agents/vendor-guard/export")
async def export_vendor_guard(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Download the latest Vendor Guard assessment as a Word report."""
    run = (await db.execute(
        select(AgentRun).where(
            AgentRun.engagement_id == engagement_id, AgentRun.agent_type == VENDOR_AGENT
        ).order_by(AgentRun.created_at.desc())
    )).scalars().first()
    if not run or not run.raw_output:
        raise HTTPException(status_code=404, detail="No vendor assessment to export yet")
    try:
        result = json.loads(run.raw_output)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=404, detail="No vendor assessment to export yet")

    import io
    from docx import Document
    from docx.shared import Pt, RGBColor
    from services.word_export import _brand_rgb

    doc = Document()
    doc.styles["Normal"].font.name = "Inter"
    doc.styles["Normal"].font.size = Pt(10)
    vendor = result.get("vendor_name") or "Vendor"
    h = doc.add_heading(f"Vendor Risk Assessment: {vendor}", 0)
    try:
        h.runs[0].font.color.rgb = _brand_rgb()
    except Exception:  # noqa: BLE001
        h.runs[0].font.color.rgb = RGBColor(0x1E, 0x6B, 0x4F)
    doc.add_paragraph(f"Overall RAG: {result.get('overall_rag', '-')}  |  "
                      f"Frameworks: {', '.join(result.get('specialists', []))}")

    doc.add_heading("Risk scorecard", level=1)
    sc = result.get("scorecard") or {}
    if sc:
        t = doc.add_table(rows=1, cols=5); t.style = "Table Grid"
        for i, hd in enumerate(["Framework", "RAG", "Total", "Gaps", "Critical/High"]):
            t.rows[0].cells[i].text = hd; t.rows[0].cells[i].paragraphs[0].runs[0].bold = True
        for fw, d in sc.items():
            row = t.add_row().cells
            row[0].text = fw; row[1].text = d.get("rag", "")
            row[2].text = str(d.get("total", 0)); row[3].text = str(d.get("gaps", 0))
            row[4].text = str(d.get("critical", 0) + d.get("high", 0))

    doc.add_heading("Gap register", level=1)
    gaps = result.get("gap_register") or []
    if gaps:
        t = doc.add_table(rows=1, cols=6); t.style = "Table Grid"
        for i, hd in enumerate(["Framework", "Control", "Status", "Severity", "Evidence", "Recommendation"]):
            t.rows[0].cells[i].text = hd; t.rows[0].cells[i].paragraphs[0].runs[0].bold = True
        for f in gaps:
            row = t.add_row().cells
            row[0].text = f.get("framework", ""); row[1].text = f"{f.get('control_id','')} {f.get('control_name','')}"
            row[2].text = f.get("status", ""); row[3].text = f.get("severity", "")
            row[4].text = f.get("evidence", ""); row[5].text = f.get("recommendation", "")

    if result.get("memo"):
        doc.add_heading("Audit memo", level=1)
        for line in str(result["memo"]).split("\n"):
            doc.add_paragraph(line) if line.strip() else doc.add_paragraph("")

    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    filename = f"Vendor-Risk-{re.sub(r'[^A-Za-z0-9._-]', '-', vendor)[:30] or 'assessment'}.docx"
    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Close the loop: promote a test's exceptions to a 5C finding ──────────────

_RATING_BY_EXCEPTIONS = lambda ex: "high" if ex >= 3 else "medium" if ex >= 1 else "low"  # noqa: E731


@router.post("/racm/{engagement_id}/tests/{test_id}/promote-to-finding")
async def promote_test_to_finding(engagement_id: str, test_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministically turn a test's exceptions into a 5C finding that carries
    the full lineage (objective → risk → control → test). No AI: the finding is
    composed from the spine; the existing 5C drafter and peer reviewer refine and
    challenge it afterwards. Idempotent — one finding per test."""
    test = await db.get(RacmTest, test_id)
    if not test or test.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Test not found")

    existing = (await db.execute(
        select(Finding).where(Finding.racm_test_id == test_id)
    )).scalars().first()
    if existing:
        return {"created": False, "finding_id": existing.id, "title": existing.title}

    control = await db.get(RacmControl, test.control_id) if test.control_id else None
    risk = await db.get(RacmRisk, control.risk_id) if control and control.risk_id else None
    objective = await db.get(RacmObjective, risk.objective_id) if risk and risk.objective_id else None

    ex = test.exceptions_count or 0
    norm = []
    if control:
        norm.append(f"Control '{control.title}' is expected to operate effectively.")
    if risk:
        norm.append(f"It must mitigate the risk '{risk.title}'.")
    if objective:
        norm.append(f"This supports the objective '{objective.title}'.")

    rating = risk.inherent_rating if (risk and risk.inherent_rating in ("high", "medium", "low")) else _RATING_BY_EXCEPTIONS(ex)
    lineage = [n.ref for n in (objective, risk, control, test) if n and n.ref]

    last = (await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id).order_by(Finding.sort_order.desc())
    )).scalars().first()

    finding = Finding(
        id=str(uuid4()), engagement_id=engagement_id, racm_test_id=test_id,
        title=(f"Control-testing exceptions — {control.title}" if control else f"Testing exceptions — {test.title}")[:500],
        condition=test.conclusion or f"Testing '{test.title}' found {ex} exception(s) in {test.sample_size or 0} item(s).",
        criteria=" ".join(norm) or "The control is expected to operate effectively.",
        effect=(risk.description or risk.title) if risk else "The control weakness may go undetected.",
        rating=rating,
        rating_rationale=(f"Proposed from inherent risk rating '{risk.inherent_rating}' and {ex} testing exception(s)."
                          if risk else f"Proposed from {ex} testing exception(s)."),
        status="draft",
        sort_order=(last.sort_order + 1) if last else 0,
    )
    db.add(finding)
    await db.commit()
    return {"created": True, "finding_id": finding.id, "title": finding.title, "lineage": lineage, "rating": rating}


# ── Control-Testing / Sampling agent (deterministic; proposes a test) ────────

_SAMPLE_BY_RISK = {"high": 25, "medium": 15, "low": 10}


@router.post("/racm/{engagement_id}/controls/{control_id}/propose-test")
async def propose_control_test(engagement_id: str, control_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministically propose a risk-based test for a control: sample size is
    driven by the linked risk's inherent rating, the method by the control type.
    Writes a pending test proposal (origin='ai', accepted=False) under the control.
    Idempotent — one proposed test per control from this agent."""
    control = await db.get(RacmControl, control_id)
    if not control or control.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Control not found")

    # Reuse this agent's earlier unaccepted proposal for the same control, if any.
    candidates = (await db.execute(
        select(RacmTest).where(
            RacmTest.engagement_id == engagement_id, RacmTest.control_id == control_id,
            RacmTest.origin == "ai", RacmTest.accepted == False,  # noqa: E712
        )
    )).scalars().all()
    for t in candidates:
        prov = _loads(t.provenance) or {}
        if prov.get("source_type") == "control_testing":
            return _serialize(t)

    risk = await db.get(RacmRisk, control.risk_id) if control.risk_id else None
    rating = risk.inherent_rating if (risk and risk.inherent_rating in _SAMPLE_BY_RISK) else "medium"
    n = _SAMPLE_BY_RISK[rating]
    method = "reperformance" if control.control_type == "preventive" else "inspection"

    last = (await db.execute(
        select(RacmTest).where(RacmTest.engagement_id == engagement_id).order_by(RacmTest.sort_order.desc())
    )).scalars().first()
    test = RacmTest(
        id=str(uuid4()), engagement_id=engagement_id, control_id=control_id,
        title=f"Test of control: {control.title}"[:500],
        description=(f"{method.capitalize()} test on a risk-based sample of {n} items to confirm "
                     f"'{control.title}' operates effectively."),
        method="sampling", sample_size=n, result="pending",
        origin="ai", accepted=False, confidence="high",
        provenance=json.dumps({
            "source_type": "control_testing", "source_ref": control.ref,
            "rationale": f"Sample size {n} for {rating} inherent risk ({method}).",
        }),
        sort_order=(last.sort_order + 1) if last else 0,
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return _serialize(test)


# ── Evidence / DRL chaser (deterministic; matches DRL to evidence) ───────────

def _keywords(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())}


@router.get("/racm/{engagement_id}/agents/evidence-chase")
async def evidence_chase(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministically match each DRL item to the evidence captured in the spine
    and flag what is still outstanding, with a draft follow-up. No AI."""
    await _require_engagement(engagement_id, db)
    drl = (await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
        .order_by(DRLDocument.id)
    )).scalars().first()
    drl_items = _loads(drl.items, []) if drl else []
    evidence = (await db.execute(
        select(RacmEvidence).where(RacmEvidence.engagement_id == engagement_id)
    )).scalars().all()
    ev_index = [(e, _keywords(f"{e.title} {e.description}")) for e in evidence]

    # A request now records which evidence needs it settles, so the match is a
    # reference. Two shared words is what this did for all of it, and a guess
    # shown the same way as a fact is how an auditor comes to believe a
    # document arrived. Keywords stay only for rows written before the link
    # existed, and every row says which way it was matched.
    by_request: dict[str, list] = {}
    for e in evidence:
        if e.drl_item_id:
            by_request.setdefault(str(e.drl_item_id), []).append(e)

    items = []
    outstanding = 0
    for it in drl_items:
        doc = it.get("document") or ""
        status = (it.get("status") or "").lower()
        linked = by_request.get(str(it.get("id")), [])
        match, how = (linked[0], "linked") if linked else (None, None)
        if match is None:
            kw = _keywords(doc)
            for e, ekw in ev_index:
                if e.drl_item_id:
                    continue  # already spoken for by the request that claimed it
                if len(kw & ekw) >= 2:  # at least two shared meaningful words
                    match, how = e, "keyword"
                    break
        received = status in ("received", "provided") or match is not None
        if not received:
            outstanding += 1
        items.append({
            "id": it.get("id"), "document": doc, "requested_from": it.get("requested_from"),
            "status": it.get("status"), "matched_evidence": (match.ref or match.title) if match else None,
            "matched_by": how,
            "outstanding": not received,
            "followup": None if received else f"Follow up with {it.get('requested_from') or 'the owner'}: please provide '{doc}'.",
        })
    return {
        "total": len(items), "outstanding": outstanding, "items": items,
        "matched_by_reference": sum(1 for i in items if i["matched_by"] == "linked"),
        "matched_by_keyword": sum(1 for i in items if i["matched_by"] == "keyword"),
    }


# ── Generic spine nodes ─────────────────────────────────────────────────────

@router.post("/racm/{engagement_id}/{node_type}")
async def create_node(engagement_id: str, node_type: str, payload: dict, db: AsyncSession = Depends(get_db)):
    spec = _spec(node_type)
    await _require_engagement(engagement_id, db)
    model = spec["model"]
    title = (payload.get("title") or "").strip()
    # Evidence may be titled by its kind; everything else needs a title.
    if not title and node_type != "evidence":
        raise HTTPException(status_code=422, detail="title is required")
    last = (await db.execute(
        select(model).where(model.engagement_id == engagement_id)
        .order_by(model.sort_order.desc())
    )).scalars().first()
    obj = model(id=str(uuid4()), engagement_id=engagement_id,
                sort_order=(last.sort_order + 1) if last else 0)
    for f in spec["fields"]:
        if f in payload:
            setattr(obj, f, payload[f])
    if spec["parent"] and spec["parent"] in payload:
        setattr(obj, spec["parent"], payload[spec["parent"]])
    _apply_governance(obj, payload, creating=True)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)  # reload server-generated timestamps in the async context
    return _serialize(obj)


@router.patch("/racm/{engagement_id}/{node_type}/{node_id}")
async def update_node(engagement_id: str, node_type: str, node_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    spec = _spec(node_type)
    obj = await db.get(spec["model"], node_id)
    if not obj or obj.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Node not found")
    for f in spec["fields"]:
        if f in payload:
            setattr(obj, f, payload[f])
    if spec["parent"] and spec["parent"] in payload:
        setattr(obj, spec["parent"], payload[spec["parent"]])
    _apply_governance(obj, payload, creating=False)
    await db.commit()
    await db.refresh(obj)  # reload server-generated timestamps in the async context
    return _serialize(obj)


@router.delete("/racm/{engagement_id}/{node_type}/{node_id}")
async def delete_node(engagement_id: str, node_type: str, node_id: str, db: AsyncSession = Depends(get_db)):
    spec = _spec(node_type)
    obj = await db.get(spec["model"], node_id)
    if not obj or obj.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.delete(obj)
    await db.commit()
    return {"deleted": True}
