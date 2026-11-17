import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

load_dotenv()

from app.services.claude_service import generate_report_content
from app.services.data_service import parse_uploaded_file
from app.services.document_service import extract_placeholders, fill_template

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Audit Report Generator")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/extract-placeholders")
async def api_extract_placeholders(template: UploadFile = File(...)):
    """Step 1: Upload a Word template and get back its placeholders."""
    if not template.filename.endswith(".docx"):
        raise HTTPException(400, "Only .docx files are supported as templates.")
    docx_bytes = await template.read()
    placeholders = extract_placeholders(docx_bytes)
    return {"placeholders": placeholders, "template_name": template.filename}


@app.post("/api/generate-report")
async def api_generate_report(
    # Template
    template: UploadFile = File(...),
    # Core audit metadata
    audit_type: str = Form(...),
    auditee_name: str = Form(...),
    audit_period: str = Form(...),
    auditor_name: str = Form(...),
    scope: str = Form(...),
    objectives: str = Form(...),
    methodology: str = Form(...),
    # Optional inputs
    free_text_notes: str = Form(""),
    findings_json: str = Form("[]"),   # JSON array of finding objects
    # Optional structured data file
    data_file: UploadFile = File(None),
):
    """Step 2: Generate and download the filled audit report."""
    if not template.filename.endswith(".docx"):
        raise HTTPException(400, "Only .docx files are supported as templates.")

    docx_bytes = await template.read()

    # Parse structured data if provided
    structured_data_summary = None
    if data_file and data_file.filename:
        try:
            file_bytes = await data_file.read()
            structured_data_summary = parse_uploaded_file(data_file.filename, file_bytes)
        except ValueError as e:
            raise HTTPException(400, str(e))

    # Parse findings from form
    try:
        findings = json.loads(findings_json)
    except json.JSONDecodeError:
        findings = []

    form_data = {"findings": findings} if findings else None

    # Extract placeholders from template
    placeholders = extract_placeholders(docx_bytes)
    if not placeholders:
        raise HTTPException(
            400,
            "No placeholders found in the template. "
            "Add placeholders like {{EXECUTIVE_SUMMARY}}, {{FINDINGS}}, etc."
        )

    # Call Claude to generate content
    try:
        content_map = generate_report_content(
            audit_type=audit_type,
            auditee_name=auditee_name,
            audit_period=audit_period,
            auditor_name=auditor_name,
            scope=scope,
            objectives=objectives,
            methodology=methodology,
            free_text_notes=free_text_notes or None,
            structured_data_summary=structured_data_summary,
            form_data=form_data,
            template_placeholders=placeholders,
        )
    except Exception as e:
        raise HTTPException(500, f"AI generation failed: {str(e)}")

    # Fill the Word template
    filled_docx = fill_template(docx_bytes, content_map)

    safe_name = auditee_name.replace(" ", "_")
    filename = f"Audit_Report_{safe_name}.docx"

    return Response(
        content=filled_docx,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
