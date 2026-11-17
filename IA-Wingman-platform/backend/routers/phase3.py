"""Phase 3 planning endpoints: Resource Planning, Work Program, Document Request List."""
import json
import re
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.agent_ledger import agent_context, attributed
from services.work_program_view import (
    rows_for as _wp_rows, apply_patch, snapshot as wp_snapshot,
    drift_since_signoff,
)
from models.engagement import Engagement
from models.planning import (
    ApplicableFramework,
    ProcessNotes,
    DRLDocument,
    ResourcePlan,
    UploadedDocument,
    WorkProgram,
)

router = APIRouter()


def _safe_filename(stem: str) -> str:
    """Keep only filename-safe characters so a crafted engagement name can't
    inject newlines/quotes into the Content-Disposition header."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", stem or "")
    return re.sub(r"-{2,}", "-", cleaned).strip("-") or "export"


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ── Resource Planning ─────────────────────────────────────────────────────────

def _serialize_rp(rp: ResourcePlan) -> dict:
    checks = {
        "dates_confirmed": rp.dates_confirmed,
        "hours_confirmed": rp.hours_confirmed,
        "team_confirmed": rp.team_confirmed,
        "head_ia_acknowledged": rp.head_ia_acknowledged,
    }
    completed = sum(1 for v in checks.values() if v)
    return {
        "id": rp.id,
        "hours_budget": rp.hours_budget,
        "planned_fieldwork_start": rp.planned_fieldwork_start,
        "planned_fieldwork_end": rp.planned_fieldwork_end,
        "planned_report_date": rp.planned_report_date,
        "milestones": _loads(rp.milestones, []),
        "checks": checks,
        "checks_completed": completed,
        "ai_timeline": rp.ai_timeline,
    }


@router.get("/planning/{engagement_id}/resource-plan")
async def get_resource_plan(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ResourcePlan).where(ResourcePlan.engagement_id == engagement_id)
    )
    rp = result.scalar_one_or_none()
    if not rp:
        return {
            "hours_budget": None, "planned_fieldwork_start": None,
            "planned_fieldwork_end": None, "planned_report_date": None,
            "milestones": [], "checks": {
                "dates_confirmed": False, "hours_confirmed": False,
                "team_confirmed": False, "head_ia_acknowledged": False,
            },
            "checks_completed": 0, "ai_timeline": None,
        }
    return _serialize_rp(rp)


@router.patch("/planning/{engagement_id}/resource-plan")
async def update_resource_plan(
    engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ResourcePlan).where(ResourcePlan.engagement_id == engagement_id)
    )
    rp = result.scalar_one_or_none()
    if not rp:
        rp = ResourcePlan(id=str(uuid4()), engagement_id=engagement_id)
        db.add(rp)

    scalar_fields = {
        "hours_budget", "planned_fieldwork_start", "planned_fieldwork_end",
        "planned_report_date", "ai_timeline",
    }
    bool_fields = {"dates_confirmed", "hours_confirmed", "team_confirmed", "head_ia_acknowledged"}

    for key, value in payload.items():
        if key in scalar_fields:
            setattr(rp, key, value)
        elif key in bool_fields:
            setattr(rp, key, bool(value))
        elif key == "milestones":
            rp.milestones = json.dumps(value)

    await db.commit()
    return _serialize_rp(rp)


@router.post("/planning/{engagement_id}/resource-plan/generate-timeline")
async def generate_resource_timeline(
    engagement_id: str, db: AsyncSession = Depends(get_db)
):
    """AI generates a suggested milestone timeline from the engagement scope."""
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Count accepted items to gauge scope complexity
    pn_res = await db.execute(
        select(ProcessNotes).where(ProcessNotes.engagement_id == engagement_id)
    )
    pn = pn_res.scalar_one_or_none()
    process_count = len(_loads(pn.process_items if pn else None, []))

    fw_res = await db.execute(
        select(ApplicableFramework).where(
            ApplicableFramework.engagement_id == engagement_id,
            ApplicableFramework.is_accepted == True,  # noqa: E712
        )
    )
    fw_count = len(fw_res.scalars().all())

    from services.ai_service import run_agent_to_json, BASE_SYSTEM_PROMPT
    prompt = f"""Generate a realistic audit milestone timeline for this engagement.

Audit: {eng.name}
Entity: {eng.entity}
Audit type: {eng.audit_type}
Scope complexity: {process_count} processes, {fw_count} frameworks

Return ONLY a valid JSON object:
{{
  "suggested_hours": 120,
  "timeline_text": "2-3 sentences describing recommended phasing and key milestones",
  "milestones": [
    {{"name": "Kick-off meeting", "offset_weeks": 0}},
    {{"name": "Planning complete", "offset_weeks": 3}},
    {{"name": "Fieldwork start", "offset_weeks": 4}},
    {{"name": "Fieldwork complete", "offset_weeks": 8}},
    {{"name": "Draft report", "offset_weeks": 10}},
    {{"name": "Final report", "offset_weeks": 12}}
  ]
}}

Calibrate hours to the organisation norms: compliance audit 80-160h, IT audit 100-200h, financial 80-120h.
Milestones are relative to engagement start date (offset_weeks from week 0).
"""
    with agent_context(engagement_id=engagement_id, agent="resource_plan"):
        result = await run_agent_to_json(BASE_SYSTEM_PROMPT, prompt, max_tokens=1000)

    # Store in resource plan
    rp_res = await db.execute(
        select(ResourcePlan).where(ResourcePlan.engagement_id == engagement_id)
    )
    rp = rp_res.scalar_one_or_none()
    if not rp:
        rp = ResourcePlan(id=str(uuid4()), engagement_id=engagement_id)
        db.add(rp)

    if isinstance(result, dict):
        rp.ai_timeline = result.get("timeline_text", "")
        if "suggested_hours" in result and not rp.hours_budget:
            rp.hours_budget = result["suggested_hours"]
        if "milestones" in result and not rp.milestones:
            milestones = [{"name": m["name"], "date": "", "done": False} for m in result["milestones"]]
            rp.milestones = json.dumps(milestones)
    await db.commit()
    return _serialize_rp(rp)


# ── Work Program ──────────────────────────────────────────────────────────────

async def _serialize_wp(wp: WorkProgram, db) -> dict:
    # `rows` comes from the spine now. The blob keeps one job: what was signed.
    rows = await _wp_rows(wp.engagement_id, db)
    return {
        "id": wp.id,
        "status": wp.status,
        "rows": rows,
        "row_count": len(rows),
        "signed_off_at": wp.signed_off_at.isoformat() if wp.signed_off_at else None,
    }


@router.get("/planning/{engagement_id}/work-program")
async def get_work_program(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        return {"status": "draft", "rows": [], "row_count": 0, "signed_off_at": None}
    return await _serialize_wp(wp, db)


@router.post("/planning/{engagement_id}/work-program/generate")
async def generate_work_program_endpoint(
    engagement_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        wp = WorkProgram(id=str(uuid4()), engagement_id=engagement_id)
        db.add(wp)

    if wp.status == "signed_off":
        raise HTTPException(status_code=400, detail="Work program already signed off")

    wp.status = "generating"
    await db.commit()

    from services.work_program_generator import generate_work_program
    background_tasks.add_task(attributed(generate_work_program, engagement_id, "work_program"), wp.id, engagement_id)
    return {"id": wp.id, "status": "generating"}


@router.patch("/planning/{engagement_id}/work-program/rows/{row_id}")
async def patch_work_program_row(
    engagement_id: str,
    row_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        raise HTTPException(status_code=404, detail="Work program not found")
    if wp.status == "signed_off":
        raise HTTPException(status_code=400, detail="Cannot edit signed-off work program")

    # The edit lands on the spine node the field belongs to. `test_steps` is not
    # in the map: adding or removing a step creates or deletes a test, which is
    # a spine operation with its own endpoint and its own provenance.
    await apply_patch(engagement_id, db, row_id, payload)
    return await _serialize_wp(wp, db)


@router.post("/planning/{engagement_id}/work-program/add-row")
async def add_work_program_row(
    engagement_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        wp = WorkProgram(id=str(uuid4()), engagement_id=engagement_id, status="ready")
        db.add(wp)
        await db.commit()

    rows = _loads(wp.rows, [])
    new_row = {
        "id": f"wp_{len(rows) + 1}_{uuid4().hex[:6]}",
        "process": payload.get("process", ""),
        "activity": payload.get("activity", ""),
        "risk_description": payload.get("risk_description", ""),
        "control_objective": payload.get("control_objective", ""),
        "test_steps": payload.get("test_steps", []),
        "test_approach": payload.get("test_approach", ""),
        "priority": payload.get("priority", "medium"),
        "responsibility": payload.get("responsibility", "IA team"),
        "status": "not_started",
    }
    rows.append(new_row)
    wp.rows = json.dumps(rows)
    if wp.status == "draft":
        wp.status = "ready"
    await db.commit()
    return await _serialize_wp(wp, db)


@router.delete("/planning/{engagement_id}/work-program/rows/{row_id}")
async def delete_work_program_row(
    engagement_id: str, row_id: str, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        raise HTTPException(status_code=404, detail="Work program not found")
    rows = _loads(wp.rows, [])
    wp.rows = json.dumps([r for r in rows if r.get("id") != row_id])
    await db.commit()
    return await _serialize_wp(wp, db)


@router.post("/planning/{engagement_id}/work-program/sign-off")
async def sign_off_work_program(engagement_id: str, db: AsyncSession = Depends(get_db)):
    from datetime import datetime
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp or not await _wp_rows(engagement_id, db):
        raise HTTPException(status_code=400, detail="No work program rows to sign off")
    wp.status = "signed_off"
    wp.signed_off_at = datetime.utcnow()
    # `rows` stops being the source of truth here and becomes the record of what
    # was signed. Everything after this can be compared against it.
    wp.rows = await wp_snapshot(engagement_id, db)
    await db.commit()
    return await _serialize_wp(wp, db)


@router.get("/planning/{engagement_id}/work-program/drift")
async def work_program_drift(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """What has changed in the spine since the work program was signed."""
    return await drift_since_signoff(engagement_id, db)


@router.post("/planning/{engagement_id}/work-program/reopen")
async def reopen_work_program(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        raise HTTPException(status_code=404, detail="Work program not found")
    wp.status = "ready"
    wp.signed_off_at = None
    await db.commit()
    return await _serialize_wp(wp, db)


@router.get("/planning/{engagement_id}/work-program/export-xlsx")
async def export_work_program_xlsx(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    result = await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )
    wp = result.scalar_one_or_none()
    if not wp:
        raise HTTPException(status_code=404, detail="Work program not found")

    rows = _loads(wp.rows, [])
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    import io

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Work Program"

    # Header — brand colour from the org profile (white-label).
    from organization import ORG
    _brand6 = ((ORG.brand_hex or "#1E6B4F").lstrip("#") or "1E6B4F")[:6]
    header_fill = PatternFill("solid", fgColor=_brand6)
    header_font = Font(color="FFFFFF", bold=True)
    headers = ["#", "Process", "Activity", "Risk description",
               "Control objective", "Test steps", "Priority", "Responsibility", "Status"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    for col, w in zip("ABCDEFGHI", (5, 22, 22, 30, 30, 34, 10, 16, 14)):
        ws.column_dimensions[col].width = w

    def _steps_text(row):
        steps = row.get("test_steps") or ([row["test_approach"]] if row.get("test_approach") else [])
        return "\n".join(f"{n}. {s}" for n, s in enumerate(steps, 1))

    for i, row in enumerate(rows, 2):
        ws.cell(row=i, column=1, value=i - 1)
        ws.cell(row=i, column=2, value=row.get("process", ""))
        ws.cell(row=i, column=3, value=row.get("activity", ""))
        ws.cell(row=i, column=4, value=row.get("risk_description", ""))
        ws.cell(row=i, column=5, value=row.get("control_objective", ""))
        ws.cell(row=i, column=6, value=_steps_text(row))
        ws.cell(row=i, column=7, value=(row.get("priority") or "").title())
        ws.cell(row=i, column=8, value=row.get("responsibility", "IA team"))
        ws.cell(row=i, column=9, value=row.get("status", "not_started").replace("_", " ").title())
        for col in range(1, 10):
            ws.cell(row=i, column=col).alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 70

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"WorkProgram-{_safe_filename(eng.audit_code or eng.name[:20])}.xlsx"
    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Document Request List ──────────────────────────────────────────────────────

STATUS_LABELS = {
    "not_requested": "Not requested",
    "requested": "Requested",
    "received": "Received",
    "not_needed": "Not needed",
}


@router.get("/planning/{engagement_id}/drl")
async def get_drl(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )
    drl = result.scalar_one_or_none()
    if not drl:
        return {"items": [], "generated_at": None, "distribution_email": None, "reminder_log": None}
    return {
        "items": _loads(drl.items, []),
        "generated_at": drl.generated_at.isoformat() if drl.generated_at else None,
        "distribution_email": _loads(drl.distribution_email, None),
        "reminder_log": _loads(drl.reminder_log, None),
    }


@router.post("/planning/{engagement_id}/drl/generate")
async def generate_drl_endpoint(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    from services.drl_generator import generate_drl
    from datetime import datetime
    with agent_context(engagement_id=engagement_id, agent="drl"):
        items = await generate_drl(engagement_id)

    result = await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )
    drl = result.scalar_one_or_none()
    if not drl:
        drl = DRLDocument(id=str(uuid4()), engagement_id=engagement_id)
        db.add(drl)

    drl.items = json.dumps(items)
    drl.generated_at = datetime.utcnow()
    await db.commit()

    # The generator said which needs each request settles. Recording it here is
    # what makes "has anyone asked for the evidence this test needs?" answerable
    # by reference rather than by comparing words.
    from services.evidence_needs import link, unlink_all
    # The old list's ids are gone; they were positional, so leaving a link
    # behind would point a need at whatever is third in the new list.
    await unlink_all(engagement_id, db)
    linked = await link(engagement_id, db,
                        {i["id"]: i.get("covers") or [] for i in items if i.get("id")})
    return {"items": items, "generated_at": drl.generated_at.isoformat(),
            "needs_linked": linked}


@router.get("/planning/{engagement_id}/drl/coverage")
async def drl_coverage(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Evidence the tests need against the requests actually made."""
    from services.evidence_needs import coverage
    cov = await coverage(engagement_id, db)
    # Whether regenerating is even possible changes the advice the screen gives.
    # A signed work program cannot be regenerated, so telling its auditor to do
    # that is the one thing they cannot act on.
    wp = (await db.execute(
        select(WorkProgram).where(WorkProgram.engagement_id == engagement_id)
    )).scalar_one_or_none()
    # The counts stay at the top level and the rows go under `detail`. Spreading
    # both into one object meant every list silently overwrote its own count.
    return {
        **cov.summary(),
        "work_program_signed": bool(wp and wp.signed_off_at),
        "detail": {
            "unrequested": [
                {"id": n.id, "ref": n.ref, "title": n.title, "kind": n.kind,
                 "test_id": n.test_id, "test_title": n.test_title}
                for n in cov.unrequested
            ],
            "unused_requests": cov.unused_requests,
            "controls_without_needs": cov.controls_without_needs,
        },
    }


@router.patch("/planning/{engagement_id}/drl/items/{item_id}")
async def patch_drl_item(
    engagement_id: str, item_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )
    drl = result.scalar_one_or_none()
    if not drl:
        raise HTTPException(status_code=404, detail="DRL not found")

    items = _loads(drl.items, [])
    for item in items:
        if item.get("id") == item_id:
            # every auditor-editable cell of the row
            for key in ("status", "document", "description", "requested_from",
                        "regulatory_basis", "category", "deadline"):
                if key in payload:
                    item[key] = payload[key]
            break
    drl.items = json.dumps(items)
    await db.commit()
    return {"items": items}


# ── PBC assistant ("Isabelle") — dashboard (free) + opt-in AI drafts ─────────

async def _get_drl_or_404(engagement_id: str, db: AsyncSession) -> DRLDocument:
    result = await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )
    drl = result.scalar_one_or_none()
    if not drl:
        raise HTTPException(status_code=404, detail="DRL not generated yet")
    return drl


@router.get("/planning/{engagement_id}/drl/dashboard")
async def get_drl_dashboard(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Deterministic PBC status roll-up (free, no AI): counts, completion %, and
    derived overdue detection."""
    from services.pbc_assistant import compute_dashboard
    result = await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )
    drl = result.scalar_one_or_none()
    items = _loads(drl.items, []) if drl else []
    return compute_dashboard(items)


@router.post("/planning/{engagement_id}/drl/distribution-email")
async def draft_distribution_email_endpoint(
    engagement_id: str, payload: dict | None = None, db: AsyncSession = Depends(get_db)
):
    """Opt-in AI: draft the PBC distribution email to the auditee. Modelled — never sent."""
    from datetime import datetime
    from services.pbc_assistant import draft_distribution_email
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    drl = await _get_drl_or_404(engagement_id, db)
    items = _loads(drl.items, [])
    contact = (payload or {}).get("contact")
    email = await draft_distribution_email(eng, items, contact)
    email["contact"] = contact
    email["drafted_at"] = datetime.utcnow().isoformat()
    drl.distribution_email = json.dumps(email)
    await db.commit()
    return email


@router.post("/planning/{engagement_id}/drl/reminders")
async def draft_reminders_endpoint(
    engagement_id: str, payload: dict | None = None, db: AsyncSession = Depends(get_db)
):
    """Opt-in AI: draft reminders for outstanding/overdue items. Modelled — never sent."""
    from datetime import datetime
    from services.pbc_assistant import draft_reminders
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    drl = await _get_drl_or_404(engagement_id, db)
    items = _loads(drl.items, [])
    contact = (payload or {}).get("contact")
    log = await draft_reminders(eng, items, contact)
    log["drafted_at"] = datetime.utcnow().isoformat()
    drl.reminder_log = json.dumps(log)
    await db.commit()
    return log


@router.post("/planning/{engagement_id}/drl/items/{item_id}/validate")
async def validate_drl_item_document(
    engagement_id: str, item_id: str, payload: dict, db: AsyncSession = Depends(get_db)
):
    """Opt-in AI: judge whether an uploaded document satisfies this PBC item.
    Reuses the document's already-extracted text (fenced as untrusted)."""
    from services.pbc_assistant import validate_document
    drl = await _get_drl_or_404(engagement_id, db)
    items = _loads(drl.items, [])
    item = next((it for it in items if it.get("id") == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="DRL item not found")

    document_id = (payload or {}).get("document_id")
    doc = await db.get(UploadedDocument, document_id) if document_id else None
    if not doc or doc.engagement_id != engagement_id:
        raise HTTPException(status_code=404, detail="Uploaded document not found for this engagement")

    validation = await validate_document(item, doc)
    item["validation"] = validation
    drl.items = json.dumps(items)
    await db.commit()
    return {"item_id": item_id, "validation": validation}


@router.get("/planning/{engagement_id}/drl/export-word")
async def export_drl_word(engagement_id: str, db: AsyncSession = Depends(get_db)):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    result = await db.execute(
        select(DRLDocument).where(DRLDocument.engagement_id == engagement_id)
    )
    drl = result.scalar_one_or_none()
    if not drl:
        raise HTTPException(status_code=404, detail="DRL not generated yet")

    items = _loads(drl.items, [])
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import io

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Inter"
    style.font.size = Pt(10)

    title = doc.add_heading(f"Document Request List", 0)
    title.runs[0].font.color.rgb = RGBColor(0, 75, 50)

    doc.add_paragraph(f"Audit: {eng.name}  |  Entity: {eng.entity}")
    doc.add_paragraph("")

    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["#", "Document", "Description", "Regulatory basis", "Requested from", "Status"]):
        hdr[i].text = h
        hdr[i].paragraphs[0].runs[0].bold = True

    for i, item in enumerate(items, 1):
        row = table.add_row().cells
        row[0].text = str(i)
        row[1].text = item.get("document", "")
        row[2].text = item.get("description", "")
        row[3].text = item.get("regulatory_basis", "") or ""
        row[4].text = item.get("requested_from", "")
        row[5].text = STATUS_LABELS.get(item.get("status", "not_requested"), "Not requested")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    filename = f"DRL-{_safe_filename(eng.audit_code or eng.name[:20])}.docx"
    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
