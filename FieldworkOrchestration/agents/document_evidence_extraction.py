"""document_evidence_extraction agent — OCR + layout-aware evidence extraction.

Built from the Document Evidence Extraction Agent plan (Track 2 — Evidence
Collection, plans/hackathon-3/document-evidence-extraction-agent.md; a
draft plan, not existing code — see agents/cli_runner.py's docstring for
what that distinction means for this port). Extracts policy metadata,
control statements, and evidence-implied gaps from a PDF, page by page:
digital pages (with a usable text layer) are sent as text via `pdfplumber`;
pages with no usable text layer (scanned/image-only) are rendered to a PNG
via `pdf2image` and sent to Claude as a vision input. Per-page extractions
are merged into one document-level result.

`pdf2image` additionally requires the `poppler` system binaries (`brew
install poppler` / `apt install poppler-utils`) — a scanned page fails with
a clear per-page error, not a crash of the whole document, if poppler isn't
installed.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.document_evidence_extraction import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.document_evidence_extraction import SETTINGS

_MERGED_METADATA_FIELDS = ("document", "effective_date", "owner")


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the document_evidence_extraction agent and return its structured result.

    ``inputs`` keys:
        file_path (str — a PDF), framework (str, optional — default "ISO 27001"),
        max_pages (int, optional — overrides ``SETTINGS["max_pages"]``).

    A page that fails to extract (unreadable image render, malformed model
    response, ...) is recorded in the returned ``page_errors`` list rather
    than aborting the whole document — one bad page shouldn't lose every
    other page's evidence.
    """
    client = client or ClaudeClient()
    framework = inputs.get("framework", "ISO 27001")
    max_pages = inputs.get("max_pages", SETTINGS["max_pages"])

    pages = _read_pages(inputs["file_path"], max_pages)

    merged: dict[str, Any] = {field: None for field in _MERGED_METADATA_FIELDS}
    merged["controls"] = []
    merged["gaps"] = []
    page_errors: list[dict] = []

    for page_number, kind, content in pages:
        if kind == "error":
            page_errors.append({"page": page_number, "error": content})
            continue
        try:
            extraction = _extract_page(kind, content, page_number, framework, client)
        except Exception as exc:  # noqa: BLE001 — one bad page must not abort the document
            page_errors.append({"page": page_number, "error": str(exc)})
            continue

        for field in _MERGED_METADATA_FIELDS:
            if not merged[field] and extraction.get(field):
                merged[field] = extraction[field]
        merged["controls"].extend(extraction.get("controls", []))
        merged["gaps"].extend(extraction.get("gaps", []))

    merged["pages_processed"] = len(pages)
    merged["page_errors"] = page_errors
    return merged


def _extract_page(
    kind: str, content: str, page_number: int, framework: str, client: ClaudeClient
) -> dict:
    instruction = USER_PROMPT_TEMPLATE.format(page_number=page_number, framework=framework)

    if kind == "text":
        user_content: str | list[dict] = f"{instruction}\n\nPage text:\n{content}"
    else:  # "image"
        user_content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": content},
            },
            {"type": "text", "text": instruction},
        ]

    message = client.message(
        user_content,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="document_evidence_extraction",
    )
    return extract_json_block(text_from_message(message))


def _read_pages(file_path: str, max_pages: int) -> list[tuple[int, str, str]]:
    """Return ``[(page_number, "text" | "image" | "error", content)]`` for a PDF.

    A page's digital text is used when there's enough of it to be useful;
    otherwise the page is rendered to a base64 PNG. ``content`` is the
    extracted text, that base64 string, or — for ``"error"`` — a message
    explaining why the page couldn't be read at all (e.g. poppler isn't
    installed for scanned-page rendering). Rendering failures are caught
    here, not left to raise, so one bad page can't crash every other page's
    extraction before it even starts.
    """
    if Path(file_path).suffix.lower() != ".pdf":
        raise ValueError(
            f"document_evidence_extraction only supports PDF files, got {file_path!r}"
        )

    import pdfplumber

    pages: list[tuple[int, str, str]] = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages], start=1):
            text = (page.extract_text() or "").strip()
            if len(text) >= SETTINGS["min_digital_text_chars"]:
                pages.append((i, "text", text))
                continue
            try:
                pages.append((i, "image", _render_page_png_base64(file_path, i)))
            except Exception as exc:  # noqa: BLE001 — e.g. poppler not installed
                pages.append((i, "error", f"Could not render page as an image: {exc}"))
    return pages


def _render_page_png_base64(file_path: str, page_number: int) -> str:
    from pdf2image import convert_from_path

    images = convert_from_path(
        file_path, dpi=200, first_page=page_number, last_page=page_number
    )
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()
