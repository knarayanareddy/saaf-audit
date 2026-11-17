import asyncio
import json
import re
from uuid import uuid4
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from paths import UPLOAD_ROOT  # on the data volume once this is deployed
from models.engagement import Engagement
from models.agent_run import AgentRun
from models.agent_activity import AgentActivity
from models.planning import UploadedDocument
from services.orchestrator import run_topic_intelligence_pipeline, run_topic_intelligence_v2, compute_engagement_pack, _set_ti_status
from services.document_service import extract_text
from services.injection_scan import scan_text, scan_summary
from services.agent_ledger import attributed, spend_for, recent_calls
from services.model_tiers import AUTO_SPEND_BUDGET_USD, PRICES_VERIFIED_ON
from services.agent_registry import catalog
from schemas import RunAgentsRequest

router = APIRouter()

# Note: legacy .doc (OLE2) is intentionally NOT accepted — python-docx only reads
# the .docx (OOXML/zip) format, so a .doc upload could only ever fail on parse.
# Reject it up front with a clear message instead.
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".markdown", ".csv", ".tsv", ".text", ".log"}
MAX_BYTES = 20 * 1024 * 1024  # 20 MB
_READ_CHUNK = 1024 * 1024     # 1 MB
_EXTRACT_TIMEOUT = 30         # seconds — backstop around the parser


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an upload in chunks, aborting as soon as it exceeds max_bytes so a
    huge body can't be fully spooled to disk/memory before we reject it."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


def serialize_run(r: AgentRun) -> dict:
    output = None
    if r.raw_output:
        try:
            output = json.loads(r.raw_output)
        except (json.JSONDecodeError, TypeError):
            # Don't echo the raw internal output (may hold an exception string /
            # internal detail) — surface a generic marker; status conveys failure.
            output = {"error": "Agent output could not be parsed."}
    return {
        "id": r.id,
        "engagement_id": r.engagement_id,
        "agent_type": r.agent_type,
        "status": r.status,
        "input_summary": r.input_summary,
        "output": output,
    }


@router.post("/engagements/{engagement_id}/agents/run")
async def run_agents(
    engagement_id: str,
    payload: RunAgentsRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Remove any prior runs for a clean re-run
    prior = await db.execute(select(AgentRun).where(AgentRun.engagement_id == engagement_id))
    for r in prior.scalars().all():
        await db.delete(r)

    reg_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="regulatory", status="pending")
    pol_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="policy", status="pending")
    int_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="interview", status="pending")
    db.add_all([reg_run, pol_run, int_run])
    await db.commit()

    background_tasks.add_task(
        attributed(run_topic_intelligence_pipeline, engagement_id, "topic_intelligence"),
        engagement_id, reg_run.id, pol_run.id, int_run.id,
        payload.urls, payload.use_web_search,
        payload.custom_queries, payload.manual_keyword or None,
    )
    return {"reg_run_id": reg_run.id, "pol_run_id": pol_run.id, "int_run_id": int_run.id}


@router.post("/engagements/{engagement_id}/agents/run-v2")
async def run_agents_v2(
    engagement_id: str,
    payload: RunAgentsRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    # Remove prior runs for a clean re-run
    prior = await db.execute(select(AgentRun).where(AgentRun.engagement_id == engagement_id))
    for r in prior.scalars().all():
        await db.delete(r)

    lens1_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="lens1", status="pending")
    lens2_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="lens2", status="pending")
    lens3_run = AgentRun(id=str(uuid4()), engagement_id=engagement_id, agent_type="lens3", status="pending")
    db.add_all([lens1_run, lens2_run, lens3_run])
    await db.commit()

    # Flip TI status to agents_pending SYNCHRONOUSLY (before returning), so the frontend's
    # refetch after this call already sees 'agents_pending' and starts polling. Otherwise the
    # background task sets it only after the response and the poll never starts — the result
    # then appears only after leaving and re-entering the page.
    await _set_ti_status(engagement_id, "agents_pending")

    background_tasks.add_task(
        attributed(run_topic_intelligence_v2, engagement_id, "topic_intelligence"),
        engagement_id, lens1_run.id, lens2_run.id, lens3_run.id,
        payload.urls, payload.use_web_search, payload.manual_keyword or None,
        payload.extra_context or None,
    )
    return {"lens1_run_id": lens1_run.id, "lens2_run_id": lens2_run.id, "lens3_run_id": lens3_run.id}


@router.get("/engagements/{engagement_id}/activity")
async def engagement_activity(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Append-only AI activity trail (provenance) for this engagement, newest first."""
    result = await db.execute(
        select(AgentActivity)
        .where(AgentActivity.engagement_id == engagement_id)
        .order_by(AgentActivity.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "agent": r.agent,
            "action": r.action,
            "summary": r.summary,
            "sources": json.loads(r.sources or "[]"),
            "confidence": r.confidence,
            "actor": r.actor,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/engagements/{engagement_id}/agents/status")
async def agents_status(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.engagement_id == engagement_id))
    runs = result.scalars().all()
    return {r.agent_type: serialize_run(r) for r in runs}


@router.get("/engagements/{engagement_id}/agents/runs")
async def agents_runs(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Full agent-run history for the Agent Studio run-graph, newest first."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(AgentRun.created_at.desc())
    )
    return [
        {
            "id": r.id,
            "agent_type": r.agent_type,
            "status": r.status,
            "input_summary": r.input_summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
        }
        for r in result.scalars().all()
    ]


@router.get("/engagements/{engagement_id}/agents/pack")
async def agents_pack(engagement_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Live state of the full lifecycle cascade (Planning through Reporting).
    Deterministic — safe to poll."""
    if not await db.get(Engagement, engagement_id):
        raise HTTPException(status_code=404, detail="Engagement not found")
    # Deferred import: services.copilot_orchestrator -> services.stage_actions
    # -> this very module, so a top-level import here would be circular.
    from services import copilot_orchestrator, copilot_service
    if not await copilot_service.is_autonomy_paused(engagement_id):
        await copilot_orchestrator.scan_and_queue(engagement_id, background_tasks)
        await copilot_orchestrator.scan_and_queue_items(engagement_id, background_tasks)
        await copilot_orchestrator.check_report_draft_settle(engagement_id)
        await copilot_orchestrator.maybe_notify_coherence_settle(engagement_id)
    return await compute_engagement_pack(engagement_id, db)


@router.get("/agents/{run_id}/status")
async def agent_run_status(run_id: str, db: AsyncSession = Depends(get_db)):
    r = await db.get(AgentRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return serialize_run(r)


@router.get("/agents/{run_id}/search-progress")
async def agent_search_progress(run_id: str, db: AsyncSession = Depends(get_db)):
    """Return live search progress for the Regulatory Intelligence agent."""
    import json as _j
    r = await db.get(AgentRun, run_id)
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    progress_raw = r.search_progress
    if not progress_raw:
        return {"stage": "not_started", "queries": [], "results_found": 0}
    try:
        return _j.loads(progress_raw)
    except Exception:
        return {"stage": "unknown", "queries": [], "results_found": 0}


@router.get("/engagements/{engagement_id}/agents/reg-run-id")
async def get_reg_run_id(engagement_id: str, db: AsyncSession = Depends(get_db)):
    """Return the most recent regulatory agent run ID for this engagement."""
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.engagement_id == engagement_id, AgentRun.agent_type == "regulatory")
        .order_by(AgentRun.created_at.desc())
    )
    run = result.scalars().first()
    if not run:
        return {"run_id": None}
    return {"run_id": run.id, "status": run.status}


@router.post("/engagements/{engagement_id}/documents")
async def upload_document(
    request: Request,
    engagement_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=422, detail="Accepted files: PDF, Word (.docx), or text (.txt, .md, .csv)")

    # Fast reject on a declared oversize body before reading anything.
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BYTES + _READ_CHUNK:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit")

    contents = await _read_capped(file, MAX_BYTES)

    doc_id = str(uuid4())
    eng_dir = UPLOAD_ROOT / engagement_id
    eng_dir.mkdir(parents=True, exist_ok=True)
    stored_path = eng_dir / f"{doc_id}{suffix}"
    stored_path.write_bytes(contents)

    doc = UploadedDocument(
        id=doc_id,
        engagement_id=engagement_id,
        original_filename=file.filename,
        file_path=str(stored_path),
        mime_type=file.content_type,
        file_size_bytes=len(contents),
        upload_status="processing",
    )
    db.add(doc)
    await db.commit()

    # Run CPU-bound text extraction in a thread pool so it doesn't block the event
    # loop, with a wall-clock backstop on top of the parser's own size/page guards.
    try:
        loop = asyncio.get_event_loop()
        text = await asyncio.wait_for(
            loop.run_in_executor(None, extract_text, str(stored_path), file.content_type or ""),
            timeout=_EXTRACT_TIMEOUT,
        )
        doc.extracted_text = text
        flags = scan_text(text)
        doc.injection_flags = json.dumps(flags) if flags else None
        doc.upload_status = "ready"
    except Exception:  # noqa: BLE001
        doc.upload_status = "failed"
    await db.commit()

    flags_list = json.loads(doc.injection_flags) if doc.injection_flags else []
    return {
        "id": doc.id,
        "original_filename": doc.original_filename,
        "upload_status": doc.upload_status,
        "file_size_bytes": doc.file_size_bytes,
        "injection_flag_count": len(flags_list),
    }


@router.get("/engagements/{engagement_id}/documents")
async def list_documents(engagement_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UploadedDocument).where(UploadedDocument.engagement_id == engagement_id)
    )
    out = []
    for d in result.scalars().all():
        try:
            flags = json.loads(d.injection_flags) if d.injection_flags else []
        except (ValueError, TypeError):
            flags = []
        summary = scan_summary(flags)
        out.append({
            "id": d.id,
            "original_filename": d.original_filename,
            "upload_status": d.upload_status,
            "file_size_bytes": d.file_size_bytes,
            "injection_flag_count": summary["count"],
            "injection_max_severity": summary["max_severity"],
        })
    return out


def _safe_filename(stem: str) -> str:
    """Keep only filename-safe characters so a crafted filename can't inject
    newlines/quotes into the Content-Disposition header."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", stem or "")
    return re.sub(r"-{2,}", "-", cleaned).strip("-") or "document"


class DocumentUpdate(BaseModel):
    extracted_text: str


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Full document incl. the extracted text the analysers read — used by the
    viewer so the auditor can open and correct it."""
    d = await db.get(UploadedDocument, document_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        flags = json.loads(d.injection_flags) if d.injection_flags else []
    except (ValueError, TypeError):
        flags = []
    return {
        "id": d.id,
        "engagement_id": d.engagement_id,
        "original_filename": d.original_filename,
        "mime_type": d.mime_type,
        "upload_status": d.upload_status,
        "file_size_bytes": d.file_size_bytes,
        "extracted_text": d.extracted_text or "",
        "injection_flags": flags,
    }


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str, payload: DocumentUpdate, db: AsyncSession = Depends(get_db)
):
    """Edit the extracted text. The auditor corrects OCR/extraction errors; the
    analysers pick up the revised text on their next run. Re-scan for injection
    signals so the Verify badge stays honest after an edit."""
    d = await db.get(UploadedDocument, document_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    d.extracted_text = payload.extracted_text
    flags = scan_text(payload.extracted_text)
    d.injection_flags = json.dumps(flags) if flags else None
    await db.commit()
    return {
        "id": d.id,
        "original_filename": d.original_filename,
        "upload_status": d.upload_status,
        "extracted_text": d.extracted_text or "",
        "injection_flag_count": len(flags),
    }


@router.get("/documents/{document_id}/download")
async def download_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Serve the original uploaded file so the auditor can open it verbatim."""
    d = await db.get(UploadedDocument, document_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(d.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    filename = _safe_filename(d.original_filename or path.name)
    return FileResponse(
        str(path),
        media_type=d.mime_type or "application/octet-stream",
        filename=filename,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    d = await db.get(UploadedDocument, document_id)
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        Path(d.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    await db.delete(d)
    await db.commit()


@router.get("/engagements/{engagement_id}/agents/spend")
async def agent_spend(engagement_id: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """What this engagement has spent on AI, and the calls behind it.

    Read-only and deterministic — it reads the ledger, it never queues work, so
    it is safe to poll from a page that is open all day.
    """
    eng = await db.get(Engagement, engagement_id)
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return {
        "spend": await spend_for(engagement_id),
        "budget_usd": AUTO_SPEND_BUDGET_USD,
        "prices_verified": PRICES_VERIFIED_ON,
        "recent": await recent_calls(engagement_id, limit),
    }


@router.get("/agents/catalog")
async def agents_catalog():
    """Every agent this platform has, independent of any engagement.

    Deterministic and free: it is the registry, not a query. This is what the
    roster screen reads, and what gives one name and one icon to every surface
    that mentions an agent.
    """
    return {"agents": catalog()}
