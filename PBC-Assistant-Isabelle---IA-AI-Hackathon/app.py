import json
import os
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Optional AI analysis ──────────────────────────────────────────────────────
try:
    from pbc_workflow.document_agent import (
        ALLOWED_EXTENSIONS,
        extract_text_from_file,
        run_document_analysis_agent,
    )
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    ALLOWED_EXTENSIONS = {"pdf", "xlsx", "xls", "docx", "csv"}

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="PBC Audit Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_FILE    = "data/pbc_data.json"
FILES_DATA   = "data/files_data.json"
UPLOADS_DIR  = "data/uploads"
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB

# Create required directories on startup
for _d in ("data", UPLOADS_DIR, "static"):
    os.makedirs(_d, exist_ok=True)

# ── Sample PBC data ───────────────────────────────────────────────────────────
SAMPLE_DATA = [
    {
        "id": "PBC-001",
        "description": "Signed trial balance as at 31 December 2024",
        "contact_person": "Sarah Johnson",
        "contact_email": "sarah.johnson@acme-corp.com",
        "deadline": "2026-02-15",
        "status": "received",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
    {
        "id": "PBC-002",
        "description": "General ledger full year",
        "contact_person": "David Wilson",
        "contact_email": "david.wilson@acme-corp.com",
        "deadline": "2026-02-15",
        "status": "received",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
    {
        "id": "PBC-003",
        "description": "Bank statements for all accounts",
        "contact_person": "Mike Chen",
        "contact_email": "mike.chen@acme-corp.com",
        "deadline": "2026-02-28",
        "status": "received",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
    {
        "id": "PBC-004",
        "description": "Bank reconciliation statements",
        "contact_person": "Mike Chen",
        "contact_email": "mike.chen@acme-corp.com",
        "deadline": "2026-02-28",
        "status": "overdue",
        "reminder_count": 2,
        "last_reminder_date": "2026-03-05",
    },
    {
        "id": "PBC-005",
        "description": "Accounts receivable ageing report",
        "contact_person": "Lisa Park",
        "contact_email": "lisa.park@acme-corp.com",
        "deadline": "2026-03-05",
        "status": "received",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
    {
        "id": "PBC-006",
        "description": "Accounts payable ageing report",
        "contact_person": "Lisa Park",
        "contact_email": "lisa.park@acme-corp.com",
        "deadline": "2026-03-05",
        "status": "overdue",
        "reminder_count": 1,
        "last_reminder_date": "2026-03-08",
    },
    {
        "id": "PBC-007",
        "description": "Fixed asset register",
        "contact_person": "Sarah Johnson",
        "contact_email": "sarah.johnson@acme-corp.com",
        "deadline": "2026-03-20",
        "status": "pending",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
    {
        "id": "PBC-008",
        "description": "Board minutes for the year",
        "contact_person": "David Wilson",
        "contact_email": "david.wilson@acme-corp.com",
        "deadline": "2026-03-01",
        "status": "received",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
    {
        "id": "PBC-009",
        "description": "Monthly management accounts",
        "contact_person": "David Wilson",
        "contact_email": "david.wilson@acme-corp.com",
        "deadline": "2026-03-01",
        "status": "overdue",
        "reminder_count": 3,
        "last_reminder_date": "2026-03-09",
    },
    {
        "id": "PBC-010",
        "description": "Payroll summary and reconciliation",
        "contact_person": "Mike Chen",
        "contact_email": "mike.chen@acme-corp.com",
        "deadline": "2026-03-25",
        "status": "pending",
        "reminder_count": 0,
        "last_reminder_date": None,
    },
]


# ── PBC data helpers ──────────────────────────────────────────────────────────

def load_data() -> List[dict]:
    if not os.path.exists(DATA_FILE):
        os.makedirs("data", exist_ok=True)
        save_data(SAMPLE_DATA)
        return SAMPLE_DATA
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_data(items: List[dict]):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def refresh_overdue(items: List[dict]) -> List[dict]:
    today = date.today().isoformat()
    for item in items:
        # "received" and "validated" are terminal — never demote them to overdue
        if item["status"] not in ("received", "validated") and item["deadline"] < today:
            item["status"] = "overdue"
    return items


def get_next_id(items: List[dict]) -> str:
    nums = []
    for item in items:
        try:
            nums.append(int(item["id"].split("-")[1]))
        except (IndexError, ValueError):
            pass
    n = max(nums) + 1 if nums else 1
    return f"PBC-{n:03d}"


# ── Files data helpers ────────────────────────────────────────────────────────

def load_files() -> List[dict]:
    if not os.path.exists(FILES_DATA):
        return []
    with open(FILES_DATA, encoding="utf-8") as f:
        return json.load(f)


def save_files(files: List[dict]):
    os.makedirs("data", exist_ok=True)
    with open(FILES_DATA, "w", encoding="utf-8") as f:
        json.dump(files, f, indent=2, ensure_ascii=False)


def sanitize_filename(name: str) -> str:
    """Strip path separators and replace spaces."""
    name = Path(name).name                      # strip any directory component
    name = re.sub(r"[^\w.\-]", "_", name)       # replace unsafe chars
    return name or "file"


def generate_file_id(pbc_id: str) -> str:
    """Generate a collision-resistant file ID."""
    ts = int(time.time() * 1000)
    rand = os.urandom(2).hex()
    safe = pbc_id.replace("-", "")
    return f"f_{safe}_{ts}_{rand}"


# ── Pydantic models ───────────────────────────────────────────────────────────

class PBCItemCreate(BaseModel):
    description: str
    contact_person: str
    contact_email: str
    deadline: str
    status: str = "pending"


class PBCItemUpdate(BaseModel):
    description: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    reminder_count: Optional[int] = None
    last_reminder_date: Optional[str] = None


# ── PBC endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/pbc")
def get_all_items():
    items = load_data()
    items = refresh_overdue(items)
    save_data(items)
    return items


@app.post("/api/pbc", status_code=201)
def create_item(item: PBCItemCreate):
    items = load_data()
    new_item = {
        "id": get_next_id(items),
        "description": item.description,
        "contact_person": item.contact_person,
        "contact_email": item.contact_email,
        "deadline": item.deadline,
        "status": item.status,
        "reminder_count": 0,
        "last_reminder_date": None,
    }
    items.append(new_item)
    save_data(items)
    return new_item


@app.put("/api/pbc/{item_id}")
def update_item(item_id: str, update: PBCItemUpdate):
    items = load_data()
    for i, item in enumerate(items):
        if item["id"] == item_id:
            patch = update.model_dump(exclude_unset=True)
            items[i].update(patch)
            save_data(items)
            return items[i]
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@app.delete("/api/pbc/{item_id}")
def delete_item(item_id: str):
    items = load_data()
    for i, item in enumerate(items):
        if item["id"] == item_id:
            removed = items.pop(i)
            save_data(items)
            return {"message": f"Item {item_id} deleted", "item": removed}
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@app.post("/api/pbc/{item_id}/reminder")
def send_reminder(item_id: str):
    items = load_data()
    for i, item in enumerate(items):
        if item["id"] == item_id:
            items[i]["reminder_count"] = items[i].get("reminder_count", 0) + 1
            items[i]["last_reminder_date"] = date.today().isoformat()
            save_data(items)
            return items[i]
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@app.get("/api/dashboard")
def get_dashboard():
    items = load_data()
    items = refresh_overdue(items)
    save_data(items)

    total      = len(items)
    validated  = sum(1 for i in items if i["status"] == "validated")
    received   = sum(1 for i in items if i["status"] == "received")
    complete   = validated + received          # both count toward completion
    missing    = total - complete
    overdue    = sum(1 for i in items if i["status"] == "overdue")
    pct        = round(complete / total * 100, 1) if total else 0.0

    contacts         = {i["contact_email"] for i in items if i["contact_email"]}
    notified_emails  = {i["contact_email"] for i in items
                        if i.get("reminder_count", 0) > 0 and i["contact_email"]}
    total_reminders  = sum(i.get("reminder_count", 0) for i in items)

    return {
        "total": total,
        "received": complete,           # combined received+validated for card display
        "received_only": received,
        "validated": validated,
        "missing": missing,
        "overdue": overdue,
        "completion_percentage": pct,
        "unique_contacts": len(contacts),
        "notified_contacts": len(notified_emails),
        "total_reminders": total_reminders,
        "ai_available": AI_AVAILABLE,
    }


# ── Document endpoints ────────────────────────────────────────────────────────

@app.post("/api/pbc/{item_id}/documents", status_code=201)
async def upload_document(
    item_id: str,
    file: UploadFile = File(...),
    uploaded_by: str = Form("Coordinator"),
):
    # Verify PBC item exists
    items = load_data()
    pbc_item = next((i for i in items if i["id"] == item_id), None)
    if not pbc_item:
        raise HTTPException(status_code=404, detail=f"PBC item {item_id} not found")

    # Validate extension
    original_name = sanitize_filename(file.filename or "file")
    ext = Path(original_name).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' is not supported. "
                   f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read bytes and check size
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")

    # Save to disk
    file_id = generate_file_id(item_id)
    stored_name = f"{file_id}_{original_name}"
    dest = Path(UPLOADS_DIR) / stored_name
    dest.write_bytes(content)

    # Build metadata record
    record = {
        "file_id": file_id,
        "pbc_id": item_id,
        "original_name": original_name,
        "stored_name": stored_name,
        "file_ext": ext,
        "size_bytes": len(content),
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "uploaded_by": uploaded_by,
        "analysis": None,
    }

    files = load_files()
    files.append(record)
    save_files(files)

    # Promote PBC status to "received" if not already complete
    for item in items:
        if item["id"] == item_id:
            if item["status"] not in ("received", "validated"):
                item["status"] = "received"
                save_data(items)
            break

    return record


@app.get("/api/pbc/{item_id}/documents")
def list_documents(item_id: str):
    return [f for f in load_files() if f["pbc_id"] == item_id]


@app.get("/api/documents/counts")
def document_counts():
    """Return {pbc_id: file_count} for all PBC items."""
    files = load_files()
    counts: dict[str, int] = {}
    for f in files:
        counts[f["pbc_id"]] = counts.get(f["pbc_id"], 0) + 1
    return counts


@app.delete("/api/documents/{file_id}")
def delete_document(file_id: str):
    files = load_files()
    record = next((f for f in files if f["file_id"] == file_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    # Remove from disk (best-effort)
    disk_path = Path(UPLOADS_DIR) / record["stored_name"]
    try:
        disk_path.unlink(missing_ok=True)
    except OSError:
        pass

    save_files([f for f in files if f["file_id"] != file_id])
    return {"message": "File deleted", "file_id": file_id}


@app.get("/api/documents/{file_id}/download")
def download_file(file_id: str):
    files = load_files()
    record = next((f for f in files if f["file_id"] == file_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    disk_path = Path(UPLOADS_DIR) / record["stored_name"]
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        str(disk_path),
        filename=record["original_name"],
        media_type="application/octet-stream",
    )


@app.post("/api/documents/{file_id}/analyze")
def analyze_document(file_id: str):
    """Run (or re-run) AI analysis on an uploaded document."""
    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="AI analysis is not available. Install the anthropic package.",
        )

    files = load_files()
    record = next((f for f in files if f["file_id"] == file_id), None)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    disk_path = Path(UPLOADS_DIR) / record["stored_name"]
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Get PBC description
    items = load_data()
    pbc_item = next((i for i in items if i["id"] == record["pbc_id"]), None)
    pbc_description = pbc_item["description"] if pbc_item else record["pbc_id"]

    # Extract text
    text, method = extract_text_from_file(str(disk_path), record["file_ext"])

    # Run Claude analysis
    analysis = run_document_analysis_agent(
        document_text=text,
        file_name=record["original_name"],
        pbc_description=pbc_description,
    )
    analysis["extraction_method"] = method
    analysis["raw_text_length"] = len(text)
    analysis["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
    analysis["model"] = "claude-opus-4-6"

    # Store analysis in file record
    record["analysis"] = analysis
    save_files(files)

    # Auto-promote PBC status based on AI conclusion
    if pbc_item:
        conclusion = analysis.get("conclusion", "")
        if conclusion == "sufficient":
            pbc_item["status"] = "validated"
            save_data(items)
        elif conclusion in ("partially sufficient", "insufficient"):
            # Ensure it's at least "received" (not pending/overdue)
            if pbc_item["status"] not in ("received", "validated"):
                pbc_item["status"] = "received"
                save_data(items)

    return record


# ── Static file serving ───────────────────────────────────────────────────────

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
