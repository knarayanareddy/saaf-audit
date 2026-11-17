"""
web/app.py — SAAF Local User Access Review Comparator — FastAPI web app
Bart van den Broek

Start with:
    cd tools/scripts/bart && python3 -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
"""

from __future__ import annotations

import io
import logging
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure the parent (bart/) directory is importable
_BART_DIR = Path(__file__).parents[1]
if str(_BART_DIR) not in sys.path:
    sys.path.insert(0, str(_BART_DIR))

import pandas as pd
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from access_review_agent import (
    DEFAULT_EXCLUSION_PATTERNS,
    detect_exceptions,
    load_file,
    write_run_outputs,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="SAAF Local User Access Review Comparator", docs_url=None, redoc_url=None)

_WEB_DIR = Path(__file__).parent
_TEMPLATES_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"

# Repo root = bart/../../.. = Track-2---IAM-final/
_REPO_ROOT = _BART_DIR.parents[2]
_OUTPUTS_RUNS_DIR = _REPO_ROOT / "outputs" / "runs"

templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_filename(name: str) -> str:
    """Remove path separators and unsafe characters from a filename."""
    name = Path(name).name  # strip directory components
    name = re.sub(r"[^\w\.\-]", "_", name)
    return name or "upload"


def _detect_match_key(df: pd.DataFrame) -> str:
    """Prefer 'username', fallback to 'email', else first column."""
    cols_lower = {c.lower(): c for c in df.columns}
    for preferred in ("username", "email", "user", "user_id", "userid"):
        if preferred in cols_lower:
            return cols_lower[preferred]
    return df.columns[0]


def _parse_exclusion_patterns(raw: str) -> list[str]:
    """Parse newline- or comma-separated exclusion patterns."""
    patterns = []
    for part in re.split(r"[\n,]+", raw):
        part = part.strip()
        if part:
            patterns.append(part)
    return patterns or DEFAULT_EXCLUSION_PATTERNS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_exclusions": "\n".join(DEFAULT_EXCLUSION_PATTERNS),
        },
    )


@app.post("/run", response_class=HTMLResponse)
async def run_comparison(
    request: Request,
    hr_file: UploadFile = File(...),
    access_file: UploadFile = File(...),
    match_key: str = Form("username"),
    stale_days: int = Form(90),
    exclusion_patterns: str = Form(""),
    hr_role_col: Optional[str] = Form(None),
    access_role_col: Optional[str] = Form(None),
    hr_dept_col: Optional[str] = Form(None),
    access_dept_col: Optional[str] = Form(None),
) -> HTMLResponse:
    """Process uploaded files and render results."""

    run_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = _OUTPUTS_RUNS_DIR / run_ts
    run_dir.mkdir(parents=True, exist_ok=True)

    error_msg: Optional[str] = None
    results = None
    hr_columns: list[str] = []
    access_columns: list[str] = []

    try:
        # Save uploaded files
        hr_filename = _sanitize_filename(hr_file.filename or "hr_upload.csv")
        access_filename = _sanitize_filename(access_file.filename or "access_upload.csv")

        hr_path = run_dir / hr_filename
        access_path = run_dir / access_filename

        hr_content = await hr_file.read()
        access_content = await access_file.read()

        hr_path.write_bytes(hr_content)
        access_path.write_bytes(access_content)

        # Load into DataFrames
        hr_df = load_file(hr_path)
        access_df = load_file(access_path)

        hr_columns = list(hr_df.columns)
        access_columns = list(access_df.columns)

        # Auto-detect match_key if not provided or blank
        effective_match_key = match_key.strip() or _detect_match_key(access_df)

        # Parse exclusion patterns
        exc_patterns = _parse_exclusion_patterns(exclusion_patterns) if exclusion_patterns.strip() else DEFAULT_EXCLUSION_PATTERNS

        # Build column kwargs — only pass overrides if non-empty
        kwargs: dict = {}
        if hr_role_col and hr_role_col.strip():
            kwargs["hr_role_col"] = hr_role_col.strip()
        if access_role_col and access_role_col.strip():
            kwargs["access_role_col"] = access_role_col.strip()
        if hr_dept_col and hr_dept_col.strip():
            kwargs["hr_dept_col"] = hr_dept_col.strip()
        if access_dept_col and access_dept_col.strip():
            kwargs["access_dept_col"] = access_dept_col.strip()

        # Run detection
        results = detect_exceptions(
            hr_df=hr_df,
            access_df=access_df,
            match_key=effective_match_key,
            stale_days=stale_days,
            exclusion_patterns=exc_patterns,
            **kwargs,
        )

        anon_map = results.pop("_anon_map")
        reveal_map = results.pop("_reveal_map")

        write_run_outputs(results, anon_map, reveal_map, run_dir)

    except Exception as exc:
        log.exception("Error during comparison")
        error_msg = str(exc)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "default_exclusions": "\n".join(DEFAULT_EXCLUSION_PATTERNS),
            "results": results,
            "run_id": run_ts,
            "error_msg": error_msg,
            "hr_columns": hr_columns,
            "access_columns": access_columns,
        },
    )


@app.get("/download/{run_id}/{filename}")
async def download_file(run_id: str, filename: str) -> FileResponse:
    """Serve a file from outputs/runs/{run_id}/."""
    # Sanitize to prevent path traversal
    safe_run_id = re.sub(r"[^\w\-]", "", run_id)
    safe_filename = _sanitize_filename(filename)
    file_path = _OUTPUTS_RUNS_DIR / safe_run_id / safe_filename
    if not file_path.exists() or not file_path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=safe_filename)


@app.get("/download-example/{filename}")
async def download_example(filename: str) -> FileResponse:
    """Serve example/test data files."""
    safe_filename = _sanitize_filename(filename)
    example_dir = _BART_DIR / "test_data"
    file_path = example_dir / safe_filename
    if not file_path.exists() or not file_path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Example file not found")
    return FileResponse(path=str(file_path), filename=safe_filename)
