"""Importing the auditee's own risk and control self-assessment.

Four steps, and the order is the point: upload, choose the header, confirm what
each column holds, and only then are rows stored. Nothing is written on the
model's say-so — the agent proposes a mapping and a person confirms it, and their
confirmation is the template that the next import reuses.

Every response that carries rows carries `AUDITEE_LABEL` with them. An RCSA is
evidence about the control environment, never Internal Audit's conclusion, and
the label travels with the data rather than living in one page's heading.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.engagement import Engagement
from models.rcsa import RcsaImport, RcsaRow, RcsaTemplate, RelianceDecision
from routers.agents import MAX_BYTES, UPLOAD_ROOT, _READ_CHUNK, _read_capped
from services import rcsa_mapping as mapping
from services import rcsa_to_spine
from services.agent_ledger import agent_context
from services.rcsa_source import (
    PREVIEW_ROWS, column_names, data_rows, header_candidates, source_for,
)

router = APIRouter()

#: Tabular formats only. A PDF of an RCSA is a document, not an import, and
#: pretending otherwise produces a mapping over text that was never a grid.
RCSA_SUFFIXES = {".xlsx", ".xlsm", ".csv"}


def _label(payload: dict) -> dict:
    """Every payload that carries rows says whose assessment they are."""
    return {**payload, "auditee_label": mapping.AUDITEE_LABEL}


async def _get_import(db: AsyncSession, import_id: str) -> RcsaImport:
    imp = await db.get(RcsaImport, import_id)
    if not imp:
        raise HTTPException(status_code=404, detail="RCSA import not found")
    return imp


# ── 1 · Upload ───────────────────────────────────────────────────────────────
@router.post("/engagements/{engagement_id}/rcsa/imports")
async def upload_rcsa(
    request: Request,
    engagement_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in RCSA_SUFFIXES:
        raise HTTPException(status_code=422,
                            detail="Accepted files: Excel (.xlsx, .xlsm) or CSV")

    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES + _READ_CHUNK:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")
    contents = await _read_capped(file, MAX_BYTES)

    import_id = str(uuid4())
    eng_dir = UPLOAD_ROOT / engagement_id / "rcsa"
    eng_dir.mkdir(parents=True, exist_ok=True)
    stored = eng_dir / f"{import_id}{suffix}"
    stored.write_bytes(contents)

    imp = RcsaImport(id=import_id, engagement_id=engagement_id,
                     original_filename=file.filename or stored.name,
                     file_path=str(stored), status="uploaded")
    db.add(imp)
    await db.commit()
    return {"id": import_id, "filename": imp.original_filename, "status": imp.status}


# ── 2 · Look at the sheet ────────────────────────────────────────────────────
@router.get("/rcsa/imports/{import_id}/preview")
async def preview(import_id: str, sheet: str | None = None,
                  db: AsyncSession = Depends(get_db)):
    """The sheets, the rows that could be the header, and the grid itself.

    The header candidates are ranked, not chosen: a real export opens with a
    title block and a banded, multi-row header, and which rows name the columns
    is something a person can see at a glance and a heuristic can only guess at.
    """
    imp = await _get_import(db, import_id)
    src = source_for(imp.file_path)
    try:
        sheets = src.sheets(imp.file_path)
        grid = src.preview(imp.file_path, sheet, PREVIEW_ROWS)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not read the file: {exc}") from exc

    return {
        "id": imp.id, "filename": imp.original_filename,
        "sheets": sheets, "sheet": sheet or (sheets[0] if sheets else None),
        "grid": grid[:PREVIEW_ROWS],
        "header_candidates": [
            {"row": c.row, "filled": c.filled, "score": c.score, "cells": c.cells}
            for c in header_candidates(grid)
        ],
        "templates": [
            {"id": t.id, "name": t.name, "source_label": t.source_label,
             "header_rows": json.loads(t.header_rows or "[]"),
             "columns": len(json.loads(t.columns or "[]"))}
            for t in (await db.execute(select(RcsaTemplate))).scalars().all()
        ],
    }


# ── 3 · Propose the mapping ──────────────────────────────────────────────────
@router.post("/rcsa/imports/{import_id}/propose")
async def propose(import_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """What each column appears to hold. A proposal — nothing is stored."""
    imp = await _get_import(db, import_id)
    header_rows = [int(r) for r in (payload.get("header_rows") or [1])]
    sheet = payload.get("sheet") or imp.sheet_name

    src = source_for(imp.file_path)
    grid = src.preview(imp.file_path, sheet, PREVIEW_ROWS)
    names = column_names(grid, header_rows)
    if not names:
        raise HTTPException(status_code=422, detail="Those header rows are not in the sheet")
    samples = [cells for _, cells in data_rows(grid, header_rows)][:3]

    with agent_context(engagement_id=imp.engagement_id, agent="rcsa_import"):
        proposal = await mapping.propose_mapping(names, samples)

    imp.sheet_name = sheet
    imp.status = "mapping_proposed"
    await db.commit()
    return {"columns": proposal["columns"], "notes": proposal.get("notes", ""),
            "targets": [{"key": t.key, "label": t.label, "why": t.why, "banded": t.banded}
                        for t in mapping.TARGETS],
            "meta": proposal.get("meta")}


# ── 4 · Confirm, and import ──────────────────────────────────────────────────
@router.post("/rcsa/imports/{import_id}/confirm")
async def confirm(import_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """The person's mapping becomes the template, and the rows are read with it.

    Re-confirming replaces this import's rows; the source file is untouched, and
    so is any other import that used the same template.
    """
    imp = await _get_import(db, import_id)
    columns = payload.get("columns") or []
    if not columns:
        raise HTTPException(status_code=422, detail="A template needs at least one column")
    header_rows = [int(r) for r in (payload.get("header_rows") or [1])]

    template_id = payload.get("template_id")
    template = await db.get(RcsaTemplate, template_id) if template_id else None
    if template is None:
        template = RcsaTemplate(id=str(uuid4()), name=payload.get("name") or "Untitled template")
        db.add(template)
    template.name = payload.get("name") or template.name
    template.source_label = payload.get("source_label") or template.source_label
    template.sheet_name = payload.get("sheet") or imp.sheet_name
    template.header_rows = json.dumps(header_rows)
    template.columns = json.dumps(columns)
    template.primary_band = payload.get("primary_band") or None
    template.confirmed_by = payload.get("confirmed_by") or "auditor"
    template.confirmed_at = datetime.now(timezone.utc)
    await db.flush()

    src = source_for(imp.file_path)
    grid = src.grid(imp.file_path, template.sheet_name, limit=20_000)
    names = column_names(src.preview(imp.file_path, template.sheet_name, PREVIEW_ROWS), header_rows)

    for row in (await db.execute(select(RcsaRow).where(RcsaRow.import_id == imp.id))).scalars().all():
        await db.delete(row)

    written = 0
    for sheet_row, cells in data_rows(grid, header_rows):
        raw = {names[i]: (cells[i] if i < len(cells) else "") for i in range(len(names))}
        if not any(v for v in raw.values()):
            continue
        projected = mapping.project(raw, columns, template.primary_band)
        db.add(RcsaRow(
            id=str(uuid4()), import_id=imp.id, sheet_row=sheet_row,
            raw=json.dumps(raw), projected=json.dumps(projected),
            risk_title=(projected.get("risk_title") or "")[:500] or None,
            process=(projected.get("process") or "")[:300] or None,
            key_risk=projected.get("key_risk"),
        ))
        written += 1

    imp.template_id = template.id
    imp.sheet_name = template.sheet_name
    imp.process = payload.get("process") or imp.process
    imp.period = payload.get("period") or imp.period
    imp.row_count = written
    imp.status = "imported"
    imp.imported_by = payload.get("confirmed_by") or "auditor"
    await db.commit()

    return _label({"id": imp.id, "template_id": template.id, "rows": written,
                   "coverage": mapping.coverage(columns)})


@router.post("/rcsa/imports/{import_id}/reproject")
async def reproject(import_id: str, db: AsyncSession = Depends(get_db)):
    """Re-read the stored rows under the template as it stands now.

    The correction path: an auditor who mapped the wrong residual band fixes the
    template and calls this. The source rows were kept whole on the way in, so
    nothing is re-uploaded and nothing is lost.
    """
    await _get_import(db, import_id)
    count = await mapping.reproject(import_id)
    return _label({"id": import_id, "rows": count})


# ── Reading it back ──────────────────────────────────────────────────────────
@router.get("/engagements/{engagement_id}/rcsa/imports")
async def list_imports(engagement_id: str, db: AsyncSession = Depends(get_db)):
    imports = (await db.execute(
        select(RcsaImport).where(RcsaImport.engagement_id == engagement_id)
        .order_by(RcsaImport.uploaded_at.desc())
    )).scalars().all()

    out = []
    for imp in imports:
        allowed, why = await mapping.may_rely_on(imp.id)
        out.append({
            "id": imp.id, "filename": imp.original_filename, "status": imp.status,
            "sheet": imp.sheet_name, "process": imp.process, "period": imp.period,
            "rows": imp.row_count, "template_id": imp.template_id,
            "uploaded_at": imp.uploaded_at.isoformat() if imp.uploaded_at else None,
            "reliance": {"allowed": allowed, "reason": why},
        })
    return _label({"imports": out})


@router.get("/rcsa/imports/{import_id}/rows")
async def rows(import_id: str, db: AsyncSession = Depends(get_db)):
    imp = await _get_import(db, import_id)
    template = await db.get(RcsaTemplate, imp.template_id) if imp.template_id else None
    columns = json.loads(template.columns or "[]") if template else []
    stored = (await db.execute(
        select(RcsaRow).where(RcsaRow.import_id == import_id).order_by(RcsaRow.sheet_row)
    )).scalars().all()
    allowed, why = await mapping.may_rely_on(import_id)

    return _label({
        "id": imp.id, "filename": imp.original_filename,
        "process": imp.process, "period": imp.period,
        "primary_band": template.primary_band if template else None,
        "coverage": mapping.coverage(columns),
        "reliance": {"allowed": allowed, "reason": why},
        "rows": [{
            "id": r.id, "sheet_row": r.sheet_row,
            "raw": json.loads(r.raw or "{}"),
            "projected": json.loads(r.projected or "{}"),
        } for r in stored],
    })


# ── Into the matrix ──────────────────────────────────────────────────────────
@router.post("/rcsa/imports/{import_id}/propose-risks")
async def propose_risks(import_id: str, payload: dict | None = None,
                        db: AsyncSession = Depends(get_db)):
    """Put the selected rows in front of the auditor as proposed risks.

    Refused, with the reason, until a reliance decision exists — the check lives
    in the service rather than here, so a second caller cannot skip it. Sending
    no `row_ids` uses the default: the rows the business itself flagged as key
    risks, which is a starting point and not a decision.
    """
    imp = await _get_import(db, import_id)
    body = payload or {}
    result = await rcsa_to_spine.propose_rows(
        imp.engagement_id, import_id, body.get("row_ids"))
    if result["refused"]:
        raise HTTPException(status_code=409, detail=result["reason"])
    return _label(result)


@router.get("/rcsa/imports/{import_id}/default-selection")
async def default_selection(import_id: str, db: AsyncSession = Depends(get_db)):
    """Which rows the page starts with ticked, and why."""
    await _get_import(db, import_id)
    rows = (await db.execute(
        select(RcsaRow).where(RcsaRow.import_id == import_id))).scalars().all()
    ids = rcsa_to_spine.default_selection(rows)
    return {"row_ids": ids,
            "reason": "The rows the business itself flagged as key risks"
                      if ids else "No row carries a key-risk flag — choose the rows yourself"}


# ── The reliance decision ────────────────────────────────────────────────────
@router.post("/rcsa/imports/{import_id}/reliance")
async def record_reliance(import_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Record what the auditor decided about relying on this second-line work.

    Required together: leaning on it is a decision, and a decision without a
    rationale is a preference. `extent = "none"` is recorded like any other —
    the auditor looked and chose not to rely, which belongs in the file.
    """
    await _get_import(db, import_id)
    extent = (payload.get("extent") or "").lower()
    if extent not in {"full", "partial", "none"}:
        raise HTTPException(status_code=422, detail="extent must be full, partial or none")
    rationale = (payload.get("rationale") or "").strip()
    if not rationale:
        raise HTTPException(status_code=422,
                            detail="A reliance decision needs a rationale — what was assessed, and why this extent")

    decision = RelianceDecision(
        id=str(uuid4()), rcsa_import_id=import_id,
        quality_assessed=bool(payload.get("quality_assessed")),
        extent=extent, rationale=rationale,
        decided_by=payload.get("decided_by") or "auditor",
        decided_at=datetime.now(timezone.utc),
    )
    db.add(decision)
    await db.commit()

    allowed, why = await mapping.may_rely_on(import_id)
    return {"id": decision.id, "reliance": {"allowed": allowed, "reason": why}}


@router.get("/rcsa/imports/{import_id}/reliance")
async def read_reliance(import_id: str, db: AsyncSession = Depends(get_db)):
    await _get_import(db, import_id)
    decision = (await db.execute(
        select(RelianceDecision).where(RelianceDecision.rcsa_import_id == import_id)
        .order_by(RelianceDecision.decided_at.desc())
    )).scalars().first()
    allowed, why = await mapping.may_rely_on(import_id)
    return {
        "decision": None if decision is None else {
            "quality_assessed": decision.quality_assessed, "extent": decision.extent,
            "rationale": decision.rationale, "decided_by": decision.decided_by,
            "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
        },
        "reliance": {"allowed": allowed, "reason": why},
    }
