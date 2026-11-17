"""Demo webapp — a thin HTTP layer over the existing orchestrator.

This is explicitly a concept-validation prototype, not production
infrastructure — see webapp/README.md for exactly what that means and what
it deliberately does not solve yet (real authentication, concurrency safety
under real multi-user load). It adds no new business logic: every endpoint
below is a thin wrapper calling an already-tested agents/orchestrator
function and returning its result as JSON, or serving a static file.

Run with (from the FieldworkOrchestration/ directory, after `pip install -r
requirements.txt`):

    uvicorn webapp.server:app --reload

Then open http://127.0.0.1:8000/
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agents import (
    pbc_creation,
    pbc_document_check,
    pbc_scope_from_work_program,
    pbc_upload_check,
    pbc_validation,
    pbc_validation_prompt_proposal,
)
from agents.audit_trail import AuditTrail
from agents.claude_init import ClaudeClient
from agents.dashboard import write_dashboard
from agents.orchestrator import (
    ApprovalRequiredError,
    control_coverage,
    finalize_run,
    record_approval,
    require_approved,
    review_last_entry,
)
from webapp.state import list_runs, load_state, save_state

STATIC_DIR = Path(__file__).parent / "static"
ASSETS_DIR = Path(__file__).parent / "assets"
INTAKE_DIR = Path(__file__).parent.parent / "intake"
ELEVENLABS_SIGNED_URL_ENDPOINT = "https://api.elevenlabs.io/v1/convai/conversation/get_signed_url"

app = FastAPI(title="Fieldwork Orchestration — Track 2 Demo")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.exception_handler(Exception)
async def unhandled_exception(_request, exc: Exception) -> JSONResponse:
    """Surface a readable message instead of a bare "Internal Server Error".

    This is a demo tool, not an internet-facing service — showing the
    exception text to whoever is using it is more useful here than hiding
    it. common.js's ``api()``/upload handlers already display whatever the
    response body says.
    """
    return JSONResponse({"detail": f"{type(exc).__name__}: {exc}"}, status_code=500)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/{page}.html")
def page(page: str) -> FileResponse:
    path = STATIC_DIR / f"{page}.html"
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)


@app.get("/static/{filename}")
def static_file(filename: str) -> FileResponse:
    path = STATIC_DIR / filename
    if not path.exists():
        raise HTTPException(404, "not found")
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #


@app.get("/api/runs")
def api_list_runs() -> list[dict]:
    return list_runs()


@app.post("/api/runs")
def api_create_run(body: dict) -> dict:
    """Create a new engagement: draft the PBC list from a required-documents list.

    Body: audit_scope, audit_period, auditee_name, auditee_email,
    auditee_org, auditor_name, senior_auditor_name, required_documents
    (list[str]).
    """
    audit_trail = AuditTrail()
    client = ClaudeClient(audit_trail=audit_trail)

    pbc_list = pbc_creation.run(
        {
            "audit_scope": body["audit_scope"],
            "audit_period": body["audit_period"],
            "required_documents": body["required_documents"],
        },
        client=client,
    )

    state = {
        "audit_scope": body["audit_scope"],
        "audit_period": body["audit_period"],
        "auditee_contact": {
            "name": body["auditee_name"],
            "email": body["auditee_email"],
            "organization": body["auditee_org"],
        },
        "assigned": {
            "auditor": body.get("auditor_name") or "",
            "senior_auditor": body.get("senior_auditor_name") or "",
        },
        "pbc_list": pbc_list,
        "received_documents": [],
        "validation_status": None,
    }
    save_state(audit_trail.run_id, state)
    return {"run_id": audit_trail.run_id}


@app.post("/api/runs/from-work-program")
async def api_create_run_from_work_program(
    audit_scope: str = Form(...),
    audit_period: str = Form(...),
    auditee_name: str = Form(...),
    auditee_email: str = Form(...),
    auditee_org: str = Form(...),
    auditor_name: str = Form(""),
    senior_auditor_name: str = Form(""),
    work_program_file: UploadFile = None,
) -> dict:
    """Bootstrap an engagement's PBC list from a UC8 work program (Track 1 -> Track 2).

    Runs the full bridge: pbc_scope_from_work_program (consolidate evidence,
    with traceability) -> pbc_creation. Slower than the plain-text path —
    a real work program means real Claude calls, some of them batched (see
    agents/README.md's "Per-item processing and cost") — so this can
    legitimately take a couple of minutes for a full work program.

    The blocking work runs in a worker thread (``asyncio.to_thread``), not
    on this coroutine directly: everything after the upload read is
    synchronous, long-running Anthropic SDK calls (including a batch poll
    loop that can run for many minutes) — doing that inline would block
    this whole server's event loop, including its own ability to check on
    other in-flight batches, for the entire duration.
    """
    raw_bytes = await work_program_file.read()
    raw = json.loads(raw_bytes)
    work_program = raw.get("work_program", raw)
    return await asyncio.to_thread(
        _create_run_from_work_program,
        audit_scope,
        audit_period,
        auditee_name,
        auditee_email,
        auditee_org,
        auditor_name,
        senior_auditor_name,
        work_program,
        raw_bytes,
    )


def _create_run_from_work_program(
    audit_scope: str,
    audit_period: str,
    auditee_name: str,
    auditee_email: str,
    auditee_org: str,
    auditor_name: str,
    senior_auditor_name: str,
    work_program: list[dict],
    raw_upload_bytes: bytes,
) -> dict:
    audit_trail = AuditTrail()
    client = ClaudeClient(audit_trail=audit_trail)

    # Keep the file exactly as supplied — the raw bytes, not a
    # json.loads()/json.dumps() round-trip (which would re-escape non-ASCII
    # characters and silently stop being byte-identical to the upload) —
    # alongside (not instead of) the parsed `work_program` embedded in
    # webapp_state.json below, so the original UC8 output for this run is
    # always recoverable on its own, not just as a field inside derived state.
    uploaded_path = audit_trail.path.parent / "uploaded_work_program.json"
    uploaded_path.parent.mkdir(parents=True, exist_ok=True)
    uploaded_path.write_bytes(raw_upload_bytes)

    scope = pbc_scope_from_work_program.run({"work_program": work_program}, client=client)
    pbc_list = pbc_creation.run(
        {
            "audit_scope": audit_scope,
            "audit_period": audit_period,
            "required_documents": scope["required_documents"],
        },
        client=client,
    )

    state = {
        "audit_scope": audit_scope,
        "audit_period": audit_period,
        "auditee_contact": {"name": auditee_name, "email": auditee_email, "organization": auditee_org},
        "assigned": {"auditor": auditor_name, "senior_auditor": senior_auditor_name},
        "pbc_list": pbc_list,
        "received_documents": [],
        "validation_status": None,
        "work_program": work_program,
        "scope_traceability": scope["traceability"],
    }
    save_state(audit_trail.run_id, state)
    return {"run_id": audit_trail.run_id}


@app.get("/api/runs/{run_id}/coverage")
def api_coverage(run_id: str) -> dict:
    state = _require_state(run_id)
    if "work_program" not in state:
        return {"available": False}
    rows = control_coverage(
        state["work_program"],
        state["scope_traceability"],
        state["pbc_list"],
        {"results": _merged_validation_results(state)},
    )
    return {"available": True, "rows": rows}


@app.get("/api/runs/{run_id}/finalized")
def api_finalized(run_id: str) -> dict:
    """Whether finalize_run has already succeeded for this run (for the dashboard banner)."""
    _require_state(run_id)
    path = AuditTrail(run_id=run_id).path.parent / "finalized.json"
    if not path.exists():
        return {"finalized": False}
    return {"finalized": True, **json.loads(path.read_text(encoding="utf-8"))}


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str) -> dict:
    state = load_state(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    return {"run_id": run_id, **state}


@app.post("/api/runs/{run_id}/update")
def api_update_run(run_id: str, body: dict) -> dict:
    """Update this engagement's master data.

    Body accepts the same field names the two creation forms use
    (audit_scope, audit_period, auditee_name, auditee_email, auditee_org,
    auditor_name, senior_auditor_name), plus elevenlabs_enabled (bool) —
    the per-engagement voice-assistant on/off switch. The ElevenLabs agent
    itself is one server-wide config (``ELEVENLABS_AGENT_ID`` in the
    environment, not stored per engagement — it's the same assistant for
    the whole app). Any subset; only fields present in the body are
    changed. Deliberately does not touch ``pbc_list``,
    ``received_documents``, ``validation_status``, ``work_program``, or
    anything else the pipeline itself owns — this is only the metadata an
    internal auditor might need to correct after creation (a typo in the
    scope, a changed contact email, reassigning who's the auditor), not a
    way to re-derive the PBC list.
    """
    state = _require_state(run_id)

    if "audit_scope" in body:
        state["audit_scope"] = body["audit_scope"]
    if "audit_period" in body:
        state["audit_period"] = body["audit_period"]

    contact = state.setdefault("auditee_contact", {})
    for key, field in (("auditee_name", "name"), ("auditee_email", "email"), ("auditee_org", "organization")):
        if key in body:
            contact[field] = body[key]

    assigned = state.setdefault("assigned", {})
    for key, field in (("auditor_name", "auditor"), ("senior_auditor_name", "senior_auditor")):
        if key in body:
            assigned[field] = body[key]

    if "elevenlabs_enabled" in body:
        state["elevenlabs_enabled"] = bool(body["elevenlabs_enabled"])

    save_state(run_id, state)
    return {"run_id": run_id, **state}


@app.get("/api/runs/{run_id}/elevenlabs/signed-url")
async def api_elevenlabs_signed_url(run_id: str) -> dict:
    """Mint a short-lived ElevenLabs conversation URL for this engagement's voice assistant.

    The ElevenLabs API key and agent id (``ELEVENLABS_API_KEY``,
    ``ELEVENLABS_AGENT_ID`` — server environment only, one agent for the
    whole app) never reach the browser — the widget asks this endpoint for
    a ``signed_url`` (good for one conversation, ~15 minutes per
    ElevenLabs) instead of talking to ElevenLabs directly. 400s if this
    engagement hasn't turned the voice assistant on (`engagement.html`'s
    toggle); 500 if the server itself has no key/agent id configured; 502
    if ElevenLabs' own call fails.
    """
    state = _require_state(run_id)
    if not state.get("elevenlabs_enabled"):
        raise HTTPException(400, "The voice assistant is not enabled for this engagement.")

    agent_id = os.environ.get("ELEVENLABS_AGENT_ID")
    if not agent_id:
        raise HTTPException(
            500, "ELEVENLABS_AGENT_ID is not configured on the server — see .env.example."
        )

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(
            500, "ELEVENLABS_API_KEY is not configured on the server — see .env.example."
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(
                ELEVENLABS_SIGNED_URL_ENDPOINT,
                params={"agent_id": agent_id},
                headers={"xi-api-key": api_key},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Could not reach ElevenLabs: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(
            502, f"ElevenLabs get_signed_url failed ({response.status_code}): {response.text[:300]}"
        )

    return {"signed_url": response.json()["signed_url"]}


@app.delete("/api/runs/{run_id}")
def api_delete_run(run_id: str) -> dict:
    """Permanently delete one engagement — irreversible, no soft-delete or trash.

    Removes ``runs/<run_id>/`` entirely (state, audit trail, quality and
    approval logs, prompt and note history, ``finalized.json`` if present)
    and ``intake/<run_id>/`` (every document the auditee uploaded). The
    server enforces no safeguard beyond the run existing — the required
    confirmation is a dialog on ``index.html``, which must warn this cannot
    be undone before ever calling this endpoint.
    """
    _require_state(run_id)  # 404s early if this run doesn't exist

    run_dir = AuditTrail(run_id=run_id).path.parent
    if run_dir.exists():
        shutil.rmtree(run_dir)

    intake_dir = INTAKE_DIR / run_id
    if intake_dir.exists():
        shutil.rmtree(intake_dir)

    return {"deleted": True, "run_id": run_id}


@app.get("/api/runs/{run_id}/board")
def api_board(run_id: str) -> list[dict]:
    state = _require_state(run_id)
    return _pbc_item_rows(run_id, state)


# --------------------------------------------------------------------------- #
# Auditee: deliver evidence
# --------------------------------------------------------------------------- #


@app.post("/api/runs/{run_id}/upload")
async def api_upload(run_id: str, pbc_id: str, file: UploadFile, force: bool = False) -> dict:
    """Save an uploaded file, sanity-check it, then run the full AI evaluation.

    First a fast sanity check (``pbc_upload_check``): if it thinks this
    looks like the wrong document, the file is saved to disk but NOT yet
    counted as delivered (``received_documents`` is left untouched) — the
    response tells the auditee why, so they can upload something else.
    Re-POSTing the same call with ``force=true`` accepts it anyway, flagged
    (``state["flags"][pbc_id]``, surfaced on the board and the
    item-history page) so the auditor sees the auditee overrode a concern,
    not a document that quietly looked fine.

    Once a document is accepted as delivered, ``_auto_evaluate_upload``
    immediately proposes a tailored validation prompt and runs the actual
    content check with it (see that function's docstring) — an AI verdict
    is already waiting when an auditor opens the board, not something they
    have to trigger by hand first. This makes the request slower (up to
    three sequential Claude calls: the sanity check, the prompt proposal,
    the document check), which is the right trade for a synchronous file
    upload at this project's scale; see agents/README.md's "Per-item
    processing and cost" for why individual calls, not a batch, are still
    correct here.
    """
    state = _require_state(run_id)
    item = _require_item(state, pbc_id)

    # Path(...).name strips any directory components the client-supplied
    # filename might carry (e.g. "../../etc/passwd") — dest_dir / filename
    # below must never be able to resolve outside dest_dir, since this same
    # filename is later used to look the file back up for download
    # (see api_item_document) and to build a filesystem path directly.
    filename = Path(file.filename or "upload").name or "upload"

    dest_dir = INTAKE_DIR / run_id / pbc_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_bytes(await file.read())

    audit_trail = AuditTrail(run_id=run_id)
    client = ClaudeClient(audit_trail=audit_trail)
    check = pbc_upload_check.run(
        {
            "pbc_description": item["description"],
            "file_path": str(dest_path),
            "file_ext": dest_path.suffix.lstrip(".") or "txt",
            "filename": filename,
            "pbc_id": pbc_id,
        },
        client=client,
    )
    looks_correct = check.get("looks_correct", True)

    if not looks_correct and not force:
        return {
            "ok": False,
            "looks_correct": False,
            "concern": check.get("concern"),
            "filename": filename,
        }

    doc = {"filename": filename, "pbc_id": pbc_id, "uploaded_at": _now_iso()}
    state["received_documents"].append(doc)
    if not looks_correct and force:
        flags = state.setdefault("flags", {})
        flags[pbc_id] = {
            "type": "auditee_override",
            "concern": check.get("concern"),
            "filename": filename,
            "at": _now_iso(),
        }

    ai_result = _auto_evaluate_upload(run_id, state, item, pbc_id, doc, client, audit_trail)
    save_state(run_id, state)
    return {"ok": True, "looks_correct": looks_correct, "ai_status": ai_result["status"] if ai_result else None}


@app.get("/api/runs/{run_id}/items/{pbc_id}/document")
def api_item_document(run_id: str, pbc_id: str) -> FileResponse:
    """Serve the most recently delivered document for one item, as-is.

    The AI verdict shown on ``auditor.html`` is not itself evidence — an
    auditor confirming it needs to open the same file the AI evaluated, not
    take the summary on faith. Serves whatever ``pbc_document_check`` most
    recently ran against (see ``_latest_received_document``); to open an
    earlier upload for the same item specifically, use the filename-scoped
    endpoint below (``item.html``'s upload history links to each by name).
    """
    state = _require_state(run_id)
    doc = _latest_received_document(state, pbc_id)
    if doc is None:
        raise HTTPException(404, f"No document has been delivered yet for {pbc_id!r}.")
    return _serve_item_document(run_id, pbc_id, doc["filename"])


@app.get("/api/runs/{run_id}/items/{pbc_id}/document/{filename}")
def api_item_document_by_name(run_id: str, pbc_id: str, filename: str) -> FileResponse:
    """Serve one specific historical upload for an item, by filename.

    ``filename`` must exactly match an entry this engagement actually
    recorded in ``received_documents`` for this ``pbc_id`` — never trusted
    as a raw filesystem path (see the comment in ``api_upload`` about
    sanitizing it on the way in); an unrecognized filename 404s rather than
    reading whatever that path happens to resolve to.
    """
    state = _require_state(run_id)
    known_filenames = {d["filename"] for d in state["received_documents"] if d["pbc_id"] == pbc_id}
    if filename not in known_filenames:
        raise HTTPException(404, f"{filename!r} was not delivered for {pbc_id!r} on this run.")
    return _serve_item_document(run_id, pbc_id, filename)


@app.post("/api/runs/{run_id}/items/{pbc_id}/propose-prompt")
def api_propose_prompt(run_id: str, pbc_id: str) -> dict:
    """Propose a tailored validation prompt for one PBC item's most recently
    delivered document — using risk/control/planned-work context when this
    engagement is linked to a UC8 work program. The proposal is not run
    against the document yet (see the ``process`` endpoint for that); it is
    recorded to ``runs/<run_id>/prompts/<pbc_id>.jsonl`` either way, so even
    a proposal an auditor never approves stays traceable.
    """
    state = _require_state(run_id)
    item = _require_item(state, pbc_id)
    doc = _latest_received_document(state, pbc_id)
    if doc is None:
        raise HTTPException(400, f"No document has been delivered yet for {pbc_id!r}.")

    audit_trail = AuditTrail(run_id=run_id)
    client = ClaudeClient(audit_trail=audit_trail)
    file_path = _document_file_path(run_id, pbc_id, doc["filename"])

    proposal = pbc_validation_prompt_proposal.run(
        {
            "pbc_description": item["description"],
            "file_path": str(file_path),
            "file_ext": file_path.suffix.lstrip(".") or "txt",
            "filename": doc["filename"],
            "pbc_id": pbc_id,
            **_work_program_context(state, pbc_id),
        },
        client=client,
    )
    _append_prompt_history(run_id, pbc_id, {"type": "proposed", **proposal, "at": _now_iso()})
    return proposal


@app.post("/api/runs/{run_id}/items/{pbc_id}/process")
def api_process_item(run_id: str, pbc_id: str, body: dict) -> list[dict]:
    """Run the detailed content-based check for one item using an approved
    (possibly auditor-edited) prompt, and fold the result into this
    engagement's validation status.

    Body: prompt (str, required — the approved instructions), edited
    (bool, optional), approved_by (str, optional — falls back to the
    engagement's assigned auditor). The approved prompt is recorded to
    ``runs/<run_id>/prompts/<pbc_id>.jsonl`` alongside any earlier proposal
    for the same item, so a correction loop (re-propose, edit, re-run)
    stays a visible history, not a silent overwrite.
    """
    state = _require_state(run_id)
    item = _require_item(state, pbc_id)
    doc = _latest_received_document(state, pbc_id)
    if doc is None:
        raise HTTPException(400, f"No document has been delivered yet for {pbc_id!r}.")

    audit_trail = AuditTrail(run_id=run_id)
    client = ClaudeClient(audit_trail=audit_trail)
    file_path = _document_file_path(run_id, pbc_id, doc["filename"])

    result = pbc_document_check.run(
        {
            "system_prompt": body["prompt"],
            "pbc_description": item["description"],
            "file_path": str(file_path),
            "file_ext": file_path.suffix.lstrip(".") or "txt",
            "filename": doc["filename"],
            "pbc_id": pbc_id,
        },
        client=client,
    )

    approved_by = body.get("approved_by") or (state.get("assigned") or {}).get("auditor") or "unknown"
    _append_prompt_history(
        run_id,
        pbc_id,
        {
            "type": "approved",
            "prompt": body["prompt"],
            "edited": bool(body.get("edited")),
            "approved_by": approved_by,
            "at": _now_iso(),
        },
    )

    _apply_validation_result(state, pbc_id, doc["filename"], result)
    save_state(run_id, state)

    review_last_entry(client, audit_trail)
    return _pbc_item_rows(run_id, state)


@app.get("/api/runs/{run_id}/items/{pbc_id}/history")
def api_item_history(run_id: str, pbc_id: str) -> dict:
    """Everything that happened to one PBC item — for the per-item detail
    page (see request in the conversation this was built from: "audittrail
    ... per uitgevoerde werkzaamheid"). Assembles: drafting, every delivered
    file, every Claude call tagged with this item (via ``item_ref`` — see
    ``AuditTrail.entries_for_item``) with its quality verdict and, when the
    call had thinking enabled, its reasoning trace (``reasoning_text`` —
    see ``claude_init.reasoning_from_message``) nested under it, the
    proposed/approved-prompt history, and approval decisions.
    """
    state = _require_state(run_id)
    item = _require_item(state, pbc_id)
    trail = AuditTrail(run_id=run_id)

    item_entries = trail.entries_for_item(pbc_id)
    quality_by_entry = {q["entry_id"]: q["review"] for q in trail.quality_entries()}
    entry_ids = {e["entry_id"] for e in item_entries}

    calls = [
        {
            "entry_id": e["entry_id"],
            "agent": e["agent"],
            "timestamp": e["timestamp"],
            "model": e["model"],
            "system_prompt": e["system_prompt"],
            "user_prompt": e["user_prompt"],
            "response_text": e["response_text"],
            "reasoning_text": e.get("reasoning_text"),
            "quality": quality_by_entry.get(e["entry_id"]),
        }
        for e in item_entries
        if e["agent"] != "quality_check"  # shown nested under the call it reviewed, above
    ]

    return {
        "pbc_id": pbc_id,
        "description": item["description"],
        "deadline": item["deadline"],
        "flag": (state.get("flags") or {}).get(pbc_id),
        "uploads": [d for d in state["received_documents"] if d["pbc_id"] == pbc_id],
        "calls": calls,
        "prompt_history": _prompt_history(run_id, pbc_id),
        "approvals": [a for a in trail.approvals() if a["entry_id"] in entry_ids],
        "auditor_notes": _item_notes(run_id, pbc_id),
        "work_program_context": _work_program_context(state, pbc_id),
    }


@app.post("/api/runs/{run_id}/items/{pbc_id}/notes")
def api_add_note(run_id: str, pbc_id: str, body: dict) -> list[dict]:
    """Record the auditor's own supplementary audit work on one item.

    Body: ``text`` (str, required), ``author`` (str, optional — falls back
    to the engagement's assigned auditor, same as ``/process``'s
    ``approved_by``). Independent of approving/rejecting — an auditor can
    add a note (extra evidence gathered themselves, a caveat, a reason they
    still want a colleague's eyes on this) without that also being a
    decision, and can add more than one over time; nothing here is ever
    overwritten. Returns this item's full note history.
    """
    state = _require_state(run_id)
    _require_item(state, pbc_id)  # 404s early if this isn't a real PBC item
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "A note needs some text.")
    author = body.get("author") or (state.get("assigned") or {}).get("auditor") or "unknown"
    _append_note(run_id, pbc_id, {"text": text, "author": author, "at": _now_iso()})
    return _item_notes(run_id, pbc_id)


# --------------------------------------------------------------------------- #
# Auditor / senior auditor: review, approve, finalize
# --------------------------------------------------------------------------- #


@app.post("/api/runs/{run_id}/approve")
def api_approve(run_id: str, body: dict) -> dict:
    """Body: entry_id, decision ('approved'|'rejected'), role, comment (optional).

    ``reviewer`` is resolved here from the engagement's own ``assigned``
    record for ``role``, not accepted from the client — the name attached to
    an approval is whoever is on record for that engagement, not whatever a
    particular browser happened to have typed in (see webapp/README.md).
    Falls back to a client-sent ``reviewer`` only for an engagement created
    before this field existed.
    """
    state = _require_state(run_id)
    role = body.get("role")
    reviewer = (state.get("assigned") or {}).get(role) or body.get("reviewer")
    if not reviewer:
        raise HTTPException(400, f"No name is assigned for role {role!r} on this engagement.")
    return record_approval(
        run_id,
        entry_id=body["entry_id"],
        decision=body["decision"],
        reviewer=reviewer,
        role=role,
        comment=body.get("comment"),
    )


@app.post("/api/runs/{run_id}/finalize")
def api_finalize(run_id: str) -> JSONResponse:
    state = _require_state(run_id)
    # Only require approval on the entries actually shown/reviewable on the
    # board — not every audit-trail entry ever recorded (a superseded
    # drafting call, for an item later re-validated, shouldn't still block
    # finalizing just because the UI never asked anyone to act on it again).
    entry_ids = [row["entry_id"] for row in _pbc_item_rows(run_id, state) if row["entry_id"]]
    try:
        finalized = finalize_run(run_id, entry_ids)
    except ApprovalRequiredError as exc:
        return JSONResponse({"ok": False, "detail": str(exc)}, status_code=409)
    return JSONResponse({"ok": True, **finalized})


@app.get("/api/runs/{run_id}/dashboard")
def api_dashboard(run_id: str) -> FileResponse:
    """Full audit-trail-level dashboard (agents/dashboard.py), for anyone who wants
    the underlying Claude calls, not just the PBC-item board above."""
    _require_state(run_id)
    path = write_dashboard(run_id)
    return FileResponse(path)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _require_state(run_id: str) -> dict:
    state = load_state(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    return state


def _require_item(state: dict, pbc_id: str) -> dict:
    item = next((i for i in state["pbc_list"]["items"] if i["id"] == pbc_id), None)
    if item is None:
        raise HTTPException(404, f"{pbc_id!r} is not a PBC item on this run")
    return item


def _latest_received_document(state: dict, pbc_id: str) -> dict | None:
    docs = [d for d in state["received_documents"] if d["pbc_id"] == pbc_id]
    return docs[-1] if docs else None


def _document_file_path(run_id: str, pbc_id: str, filename: str) -> Path:
    return INTAKE_DIR / run_id / pbc_id / filename


def _serve_item_document(run_id: str, pbc_id: str, filename: str) -> FileResponse:
    """Return a delivered file as a download, defensively.

    Callers must already have checked ``filename`` against a known-good
    list (recorded ``received_documents`` entries) before reaching here —
    this is the second, independent check: even a filename that passed that
    lookup must still resolve to a real file inside this item's own intake
    folder, never outside it, before it's served.
    """
    dest_dir = (INTAKE_DIR / run_id / pbc_id).resolve()
    file_path = (dest_dir / filename).resolve()
    if dest_dir not in file_path.parents or not file_path.is_file():
        raise HTTPException(404, f"{filename!r} could not be found for {pbc_id!r}.")
    return FileResponse(file_path, filename=filename)


def _apply_validation_result(state: dict, pbc_id: str, filename: str, result: dict) -> None:
    """Fold a pbc_document_check verdict into this engagement's validation_status.

    One current result per item — replaces this item's prior result (from
    an earlier automatic or manual check), doesn't accumulate duplicates;
    the full history of *how* we got here lives in the audit trail and
    prompts/<pbc_id>.jsonl, not in validation_status itself. Does not save
    state — the caller does that once, alongside whatever else it changed
    in the same request.
    """
    validation_status = state.get("validation_status") or {"results": []}
    results = [r for r in validation_status["results"] if r["pbc_id"] != pbc_id]
    results.append(
        {"pbc_id": pbc_id, "status": result["status"], "matched_file": filename, "notes": result.get("notes", "")}
    )
    validation_status["results"] = results
    state["validation_status"] = validation_status


def _work_program_context(state: dict, pbc_id: str) -> dict:
    """Best-effort risk/control/planned-work context for one PBC item.

    Empty (no keys) unless this engagement is linked to a UC8 work program
    *and* the consolidation traceability connects this specific pbc_id back
    to a control. Re-derives the same document->PBC-id mapping
    ``control_coverage`` (agents/orchestrator.py) builds, for one item
    instead of the whole run — small enough to keep local here rather than
    exposing another orchestrator-level helper for a single call site.
    """
    if "work_program" not in state:
        return {}
    traceability = state["scope_traceability"]
    pbc_items = state["pbc_list"]["items"]
    doc_to_pbc_id = {doc["document"]: item["id"] for doc, item in zip(traceability, pbc_items)}

    control_ids = {
        source["control_id"]
        for doc in traceability
        if doc_to_pbc_id.get(doc["document"]) == pbc_id
        for source in doc["sources"]
    }
    if not control_ids:
        return {}

    control = next((c for c in state["work_program"] if c["control_id"] in control_ids), None)
    if control is None:
        return {}

    steps = [control["test_of_design"]["step"]] + [
        t["step"] for t in control.get("tests_of_effectiveness", [])
    ]
    return {
        "risk_id": control["risk_id"],
        "risk": control["risk"],
        "control_id": control["control_id"],
        "control": control["control"],
        "control_objective": control.get("control_objective"),
        # "planned_work" stays a pre-formatted string — it's what
        # pbc_validation_prompt_proposal's prompt template interpolates
        # directly (see prompts/pbc_validation_prompt_proposal.py). The
        # webapp UI (auditor.html, item.html) wants the individual steps to
        # render as a real list, so "planned_work_steps" carries those too
        # rather than making a display concern re-parse the joined string.
        "planned_work": "\n".join(f"- {s}" for s in steps),
        "planned_work_steps": steps,
    }


def _auto_evaluate_upload(
    run_id: str,
    state: dict,
    item: dict,
    pbc_id: str,
    doc: dict,
    client: ClaudeClient,
    audit_trail: AuditTrail,
) -> dict | None:
    """Propose a validation prompt and immediately run the check with it.

    Runs right after a document is accepted as delivered (see ``/upload``),
    so an AI verdict is already waiting by the time an auditor opens the
    board, instead of requiring a manual "Propose" + "Run check" click
    first for the common case. Still fully traceable the same way a
    human-approved run is — both the proposed and the "approved" prompt
    land in ``runs/<run_id>/prompts/<pbc_id>.jsonl``, the latter tagged
    ``"auto": true`` so item.html can show it wasn't a human decision — and
    the fresh ``pbc_document_check`` call is still quality-reviewed like
    any other. An auditor who disagrees isn't stuck with this: the same
    "Propose"/"Run check" controls on ``auditor.html`` re-run it with an
    edited prompt — the correction loop this whole feature was built for —
    and *that* prompt-history entry is a real, named human approval, not
    this automatic one.

    Returns ``None`` (instead of raising) if the automatic check itself
    fails for any reason — a slow or flaky call here must never break an
    upload that already succeeded; the item is simply left without an AI
    verdict yet, same as before this automatic pass existed, and the
    auditor's manual controls remain the fallback.
    """
    try:
        file_path = _document_file_path(run_id, pbc_id, doc["filename"])
        proposal = pbc_validation_prompt_proposal.run(
            {
                "pbc_description": item["description"],
                "file_path": str(file_path),
                "file_ext": file_path.suffix.lstrip(".") or "txt",
                "filename": doc["filename"],
                "pbc_id": pbc_id,
                **_work_program_context(state, pbc_id),
            },
            client=client,
        )
        _append_prompt_history(run_id, pbc_id, {"type": "proposed", **proposal, "at": _now_iso()})

        result = pbc_document_check.run(
            {
                "system_prompt": proposal["proposed_prompt"],
                "pbc_description": item["description"],
                "file_path": str(file_path),
                "file_ext": file_path.suffix.lstrip(".") or "txt",
                "filename": doc["filename"],
                "pbc_id": pbc_id,
            },
            client=client,
        )
        _append_prompt_history(
            run_id,
            pbc_id,
            {
                "type": "approved",
                "prompt": proposal["proposed_prompt"],
                "edited": False,
                "approved_by": "AI (automatic first pass)",
                "auto": True,
                "at": _now_iso(),
            },
        )
        _apply_validation_result(state, pbc_id, doc["filename"], result)
        review_last_entry(client, audit_trail)
        return result
    except Exception:
        return None


def _prompts_path(run_id: str, pbc_id: str) -> Path:
    return AuditTrail(run_id=run_id).path.parent / "prompts" / f"{pbc_id}.jsonl"


def _append_prompt_history(run_id: str, pbc_id: str, entry: dict) -> None:
    """Append-only log of every proposed/approved validation prompt for one item.

    Separate from ``audit_trail.jsonl`` (which already logs the prompt
    actually *sent* to Claude for the resulting call) because this
    specifically preserves the human step: what was proposed vs. what was
    approved, by whom, whether it was edited — a correction loop (re-propose,
    edit, re-run) stays a visible history here, not a silent overwrite.
    """
    path = _prompts_path(run_id, pbc_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _prompt_history(run_id: str, pbc_id: str) -> list[dict]:
    path = _prompts_path(run_id, pbc_id)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _notes_path(run_id: str, pbc_id: str) -> Path:
    return AuditTrail(run_id=run_id).path.parent / "notes" / f"{pbc_id}.jsonl"


def _append_note(run_id: str, pbc_id: str, entry: dict) -> None:
    """Append-only log of an auditor's own supplementary work on one item.

    Separate from the ``comment`` an approve/reject decision can carry
    (``AuditTrail.record_approval``) — that comment explains *one decision*
    and only exists once a decision is made. A note is independent of
    deciding anything: the auditor's own additional audit evidence
    (something they checked outside the AI — a call to the bank, a
    reconciliation they ran themselves) or a caveat they want on the record
    before they, or a colleague, or the final auditor, decides. Recorded
    here rather than in ``validation_status`` or the audit trail proper
    because it's neither an AI verdict nor a Claude call — it's the human's
    own work product for this item.
    """
    path = _notes_path(run_id, pbc_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _item_notes(run_id: str, pbc_id: str) -> list[dict]:
    path = _notes_path(run_id, pbc_id)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _merged_validation_results(state: dict) -> list[dict]:
    """Every PBC item's current status, always fresh — nothing to manually re-validate.

    ``pbc_validation`` makes no Claude call any more (see its docstring) —
    it's a pure pending/overdue/received computation from today's date and
    what's been delivered, so there's no reason to cache its result in
    ``state`` or ask a user to refresh it; it's cheap enough to recompute on
    every read. A ``pbc_document_check`` result recorded in
    ``state["validation_status"]`` (by ``/items/{pbc_id}/process``) is the
    real, content-based judgement for an item that has one — it overrides
    the basic status for that item, never the reverse.
    """
    basic_results = pbc_validation.run(
        {"pbc_list": state["pbc_list"], "received_documents": state["received_documents"]}
    )["results"]
    detailed_by_id = {r["pbc_id"]: r for r in (state.get("validation_status") or {}).get("results", [])}
    return [detailed_by_id.get(r["pbc_id"], r) for r in basic_results]


def _display_status(validation_status: str, approval_status: str, checked: bool) -> tuple[str, str]:
    """One combined status label for the board, instead of two raw pills.

    A recorded human decision always wins; short of that, the label
    reflects what the AI actually found. "AI approved" is deliberately not
    the same wording as "Auditor approved" — the AI's verdict is a proposal
    for a human to confirm (or correct via the propose/edit/re-run loop),
    never itself the decision that gates finalization
    (``orchestrator.require_approved``), however confidently it's worded.

    ``checked`` disambiguates the one status string that means two very
    different things: ``"received"`` from ``pbc_validation`` (a file was
    delivered, no AI check has run for it yet — see
    ``_auto_evaluate_upload``, which normally runs one immediately, but can
    fail silently and leave this as the fallback) versus ``"received"`` as
    ``pbc_document_check``'s own legitimate verdict (a check *did* run and
    concluded it needs a human's judgement, not the AI's). Pass whether a
    ``pbc_document_check`` audit-trail entry actually exists for this item —
    the status string alone can't tell these apart.

    Returns ``(label, css_pill_suffix)``.
    """
    if approval_status == "approved":
        return "Auditor approved", "approved"
    if approval_status == "rejected":
        return "Rejected", "rejected"
    if validation_status == "validated":
        return "AI approved — awaiting auditor confirmation", "ai_approved"
    if validation_status == "insufficient":
        return "AI insufficient — awaiting auditor", "insufficient"
    if validation_status == "received":
        if checked:
            return "AI uncertain — awaiting auditor review", "received"
        return "Received — awaiting AI check", "received"
    if validation_status == "overdue":
        return "Overdue", "overdue"
    return "Not yet delivered", "pending"


def _pbc_item_rows(run_id: str, state: dict) -> list[dict]:
    """Join PBC items with their drafting/validation audit-trail entries.

    Looked up by each call's explicit ``item_ref`` (the PBC id — see
    ``AuditTrail.entries_for_item`` and ``agents/README.md``'s "Per-item
    audit trail linkage"), not guessed at positionally: every per-item
    agent call in this pipeline (``pbc_creation``, ``pbc_document_check``,
    ``quality_check`` reviewing either of them) is tagged with the PBC id
    it's about, so an item's full history is an exact lookup.
    """
    trail = AuditTrail(run_id=run_id)
    quality_by_entry = {q["entry_id"]: q["review"] for q in trail.quality_entries()}

    validation_by_id: dict[str, Any] = {r["pbc_id"]: r for r in _merged_validation_results(state)}
    flags_by_id: dict[str, Any] = state.get("flags") or {}

    rows = []
    for item in state["pbc_list"]["items"]:
        pbc_id = item["id"]
        item_entries = trail.entries_for_item(pbc_id)
        creation_entry = next((e for e in item_entries if e["agent"] == "pbc_creation"), None)
        # The *latest* pbc_document_check call, not the first — with the
        # automatic check-on-upload (see _auto_evaluate_upload) and the
        # correction loop (auditor.html's "Propose"/"Run check", re-run with
        # an edited prompt) an item routinely gets more than one of these;
        # quality and approval must track whichever run is current.
        validation_entries = [e for e in item_entries if e["agent"] == "pbc_document_check"]
        validation_entry = validation_entries[-1] if validation_entries else None
        validation_result = validation_by_id.get(pbc_id)

        review_entry = validation_entry or creation_entry
        entry_id = review_entry["entry_id"] if review_entry else None

        validation_status = validation_result["status"] if validation_result else "pending"
        approval_status = trail.approval_status(entry_id) if entry_id else "pending"
        display_status, display_status_class = _display_status(
            validation_status, approval_status, checked=validation_entry is not None
        )

        rows.append(
            {
                "pbc_id": pbc_id,
                "description": item["description"],
                "deadline": item["deadline"],
                "validation_status": validation_status,
                "matched_file": validation_result.get("matched_file") if validation_result else None,
                "validation_notes": validation_result.get("notes") if validation_result else None,
                "display_status": display_status,
                "display_status_class": display_status_class,
                "entry_id": entry_id,
                "quality": quality_by_entry.get(entry_id) if entry_id else None,
                "approval_status": approval_status,
                "approval": trail.latest_approval(entry_id) if entry_id else None,
                "flag": flags_by_id.get(pbc_id),
                "auditor_notes": _item_notes(run_id, pbc_id),
                "work_program_context": _work_program_context(state, pbc_id),
            }
        )
    return rows
