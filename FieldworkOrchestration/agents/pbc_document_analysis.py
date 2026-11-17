"""pbc_document_analysis agent — analyses a document against a PBC request.

Ported from Document_Analysis_Agent in PBC-Assistant-Isabelle (Track 2 —
Evidence Collection). Extracts text from a PDF/Excel/Word/CSV file and asks
Claude whether it satisfies the given PBC (Prepared-By-Client) request,
returning a structured analysis (summary, key information, issues, missing
information, and a sufficient/partially sufficient/insufficient conclusion).
"""

from __future__ import annotations

from pathlib import Path

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.data.loaders import extract_text_from_file
from agents.prompts.pbc_document_analysis import (
    DEFAULT_AUDIT_CONTEXT,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from agents.settings.pbc_document_analysis import SETTINGS

_VALID_CONCLUSIONS = {"sufficient", "partially sufficient", "insufficient"}

_INSUFFICIENT_DEFAULTS = {
    "summary": "",
    "key_information": [],
    "potential_issues": [],
    "missing_information": [],
    "audit_comments": "",
    "conclusion": "insufficient",
}


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_document_analysis agent and return its structured result.

    ``inputs`` keys:
        file_path (str), file_ext (str — e.g. "pdf", "xlsx", "docx", "csv"),
        pbc_description (str — the PBC request this file is meant to
        satisfy), audit_context (str, optional), max_chars (int, optional —
        overrides ``SETTINGS["max_chars"]``).

    Never raises for a file-parsing or API failure: on error, returns an
    "insufficient" result explaining the failure, so one bad document does
    not abort a batch of PBC validations.
    """
    max_chars = inputs.get("max_chars", SETTINGS["max_chars"])
    document_text, _method = extract_text_from_file(
        inputs["file_path"], inputs["file_ext"], max_chars=max_chars
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        audit_context=inputs.get("audit_context", DEFAULT_AUDIT_CONTEXT),
        pbc_description=inputs["pbc_description"],
        file_name=Path(inputs["file_path"]).name,
        document_text=document_text,
        separator="─" * 60,
    )

    try:
        client = client or ClaudeClient()
        message = client.message(
            user_prompt,
            system=SYSTEM_PROMPT,
            model=SETTINGS["model"],
            max_tokens=SETTINGS["max_tokens"],
            thinking=SETTINGS["thinking"],
            agent="pbc_document_analysis",
        )
        data = extract_json_block(text_from_message(message))
    except Exception as exc:  # noqa: BLE001 — one bad file must not abort a batch
        return {
            **_INSUFFICIENT_DEFAULTS,
            "summary": f"Analysis could not be completed. Error: {exc}",
            "potential_issues": [f"AI analysis failed: {exc}"],
            "audit_comments": (
                "Automated analysis encountered an error. "
                "Please review the document manually or re-run the analysis."
            ),
        }

    for key, default in _INSUFFICIENT_DEFAULTS.items():
        data.setdefault(key, default)
    if data["conclusion"] not in _VALID_CONCLUSIONS:
        data["conclusion"] = "insufficient"

    return data
