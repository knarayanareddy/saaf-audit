"""
Document_Analysis_Agent — AI-powered audit document analysis.

Extracts text from PDF / Excel / Word / CSV files and calls Claude
to produce structured audit commentary.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import anthropic

_client = anthropic.Anthropic()
MODEL = "claude-opus-4-6"

ALLOWED_EXTENSIONS = {"pdf", "xlsx", "xls", "docx", "csv"}


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_file(
    file_path: str,
    file_ext: str,
    max_chars: int = 40_000,
) -> tuple[str, str]:
    """
    Extract plain text from a file.

    Returns
    -------
    (extracted_text, method_name)
    """
    ext = file_ext.lower().lstrip(".")
    text = ""
    method = "unknown"

    try:
        if ext == "pdf":
            import pypdf  # noqa: PLC0415
            reader = pypdf.PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
            method = "pypdf"

        elif ext in ("xlsx", "xls"):
            import openpyxl  # noqa: PLC0415
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            lines: list[str] = []
            for ws in wb.worksheets:
                lines.append(f"\n=== Sheet: {ws.title} ===")
                for row in ws.iter_rows(values_only=True):
                    non_empty = [c for c in row if c is not None]
                    if non_empty:
                        lines.append("\t".join(str(c) if c is not None else "" for c in row))
            text = "\n".join(lines)
            method = "openpyxl"

        elif ext in ("docx", "doc"):
            from docx import Document  # noqa: PLC0415
            doc = Document(file_path)
            parts: list[str] = []
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(
                        cell.text.strip() for cell in row.cells if cell.text.strip()
                    )
                    if row_text:
                        parts.append(row_text)
            text = "\n".join(parts)
            method = "python-docx"

        elif ext == "csv":
            lines = []
            with open(file_path, encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i >= 1_000:
                        lines.append(f"[...truncated after 1000 rows]")
                        break
                    lines.append("\t".join(row))
            text = "\n".join(lines)
            method = "csv"

        else:
            text = f"[Unsupported file type: {ext}]"
            method = "unsupported"

    except Exception as exc:  # noqa: BLE001
        text = f"[Error reading {ext} file: {exc}]"
        method = "error"

    if not text or not text.strip():
        text = (
            "[No text could be extracted. The document may be empty, "
            "scanned (image-only), or use an unsupported encoding.]"
        )

    return text[:max_chars], method


# ── AI analysis ───────────────────────────────────────────────────────────────

def run_document_analysis_agent(
    document_text: str,
    file_name: str,
    pbc_description: str,
    audit_context: str = (
        "Annual statutory audit of financial statements "
        "for the year ended 31 December 2024"
    ),
) -> dict:
    """
    Analyse an uploaded audit document and return structured findings.

    Returns a dict with keys:
        summary, key_information, potential_issues,
        missing_information, audit_comments, conclusion
    """

    system = (
        "You are a senior audit manager reviewing documents submitted as part of a "
        "Prepared By Client (PBC) audit engagement.\n\n"
        "Analyse the provided document and determine whether it satisfies the specific "
        "PBC request. Be professional and specific — reference actual figures, dates, "
        "and entities found in the document wherever possible.\n\n"
        "Return ONLY a valid JSON object with this exact schema (no text outside the "
        "JSON block):\n"
        "{\n"
        '  "summary": "<2-4 sentence overview of what the document contains and its '
        'relevance to the PBC request>",\n'
        '  "key_information": [\n'
        '    "<specific data point, figure, entity, or date found in the document>"\n'
        "  ],\n"
        '  "potential_issues": [\n'
        '    "<concern, anomaly, or discrepancy — omit array if none>"\n'
        "  ],\n"
        '  "missing_information": [\n'
        '    "<item expected by the PBC request but absent — omit array if none>"\n'
        "  ],\n"
        '  "audit_comments": "<3-5 sentence detailed professional commentary>",\n'
        '  "conclusion": "sufficient | partially sufficient | insufficient"\n'
        "}\n\n"
        "Conclusion definitions:\n"
        "  sufficient           — document fully and clearly satisfies the PBC request\n"
        "  partially sufficient — document relates to the request but has meaningful gaps\n"
        "  insufficient         — document does not satisfy the request, is the wrong "
        "document, or cannot be read\n\n"
        "If the extracted text is empty, very short, or mentions an extraction error, "
        "conclude 'insufficient' and note that the document may be scanned or corrupted."
    )

    user = (
        f"Audit context : {audit_context}\n\n"
        f"PBC request   : {pbc_description}\n\n"
        f"File name     : {file_name}\n\n"
        f"Extracted document text:\n"
        f"{'─' * 60}\n"
        f"{document_text}\n"
        f"{'─' * 60}\n\n"
        "Please produce your analysis."
    )

    try:
        full_text = ""
        with _client.messages.stream(
            model=MODEL,
            max_tokens=2_048,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            for chunk in stream.text_stream:
                full_text += chunk

        data = _parse_json(full_text)

        # Fill any missing keys with safe defaults
        defaults: dict = {
            "summary": "",
            "key_information": [],
            "potential_issues": [],
            "missing_information": [],
            "audit_comments": "",
            "conclusion": "insufficient",
        }
        for key, default in defaults.items():
            if key not in data:
                data[key] = default

        # Normalise conclusion value
        valid = {"sufficient", "partially sufficient", "insufficient"}
        if data["conclusion"] not in valid:
            data["conclusion"] = "insufficient"

        return data

    except Exception as exc:  # noqa: BLE001
        return {
            "summary": f"Analysis could not be completed. Error: {exc}",
            "key_information": [],
            "potential_issues": [f"AI analysis failed: {exc}"],
            "missing_information": [],
            "audit_comments": (
                "Automated analysis encountered an error. "
                "Please review the document manually or click Re-Analyze."
            ),
            "conclusion": "insufficient",
        }


def _parse_json(text: str) -> dict:
    """Extract the first JSON object from a Claude response string."""
    m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if m:
        return json.loads(m.group(1).strip())
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"No JSON found in response. Preview: {text[:300]}")
