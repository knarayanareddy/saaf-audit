"""Shared file-reading helpers for agents that need text out of an uploaded document.

Not an agent itself — plain I/O, imported by whichever agents need it
(``pbc_document_analysis``, and the ``pbc_upload_check`` /
``pbc_validation_prompt_proposal`` / ``pbc_document_check`` family). Kept
here, per this package's own README, instead of duplicated in each agent
module — it was duplicated in two places before this file existed.
"""

from __future__ import annotations

import csv


def extract_text_from_file(file_path: str, file_ext: str, max_chars: int) -> tuple[str, str]:
    """Extract plain text from a PDF, Excel, Word, or CSV file.

    Returns ``(extracted_text, method_name)``. Never raises — a read/parse
    failure is folded into the returned text so the caller always gets
    something to send to Claude.
    """
    ext = file_ext.lower().lstrip(".")
    text = ""
    method = "unknown"

    try:
        if ext == "pdf":
            import pypdf

            reader = pypdf.PdfReader(file_path)
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n\n".join(pages)
            method = "pypdf"

        elif ext in ("xlsx", "xls"):
            import openpyxl

            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            lines: list[str] = []
            for ws in wb.worksheets:
                lines.append(f"\n=== Sheet: {ws.title} ===")
                for row in ws.iter_rows(values_only=True):
                    if any(c is not None for c in row):
                        lines.append("\t".join(str(c) if c is not None else "" for c in row))
            text = "\n".join(lines)
            method = "openpyxl"

        elif ext in ("docx", "doc"):
            from docx import Document

            doc = Document(file_path)
            parts: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]
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
                for i, row in enumerate(csv.reader(f)):
                    if i >= 1_000:
                        lines.append("[...truncated after 1000 rows]")
                        break
                    lines.append("\t".join(row))
            text = "\n".join(lines)
            method = "csv"

        elif ext == "txt":
            with open(file_path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            method = "txt"

        else:
            text = f"[Unsupported file type: {ext}]"
            method = "unsupported"

    except Exception as exc:  # noqa: BLE001
        text = f"[Error reading {ext} file: {exc}]"
        method = "error"

    if not text.strip():
        text = (
            "[No text could be extracted. The document may be empty, "
            "scanned (image-only), or use an unsupported encoding.]"
        )

    return text[:max_chars], method
