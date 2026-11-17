"""pbc_document_check agent — validates one document with a caller-supplied prompt.

Replaces filename-only heuristic validation (what ``pbc_validation`` did)
with a content-based check driven by a prompt tailored to this specific
item's risk/control/request — proposed by ``pbc_validation_prompt_proposal``
and reviewed (optionally edited) by an auditor before it ever reaches here.
This agent does not know or care where its ``system_prompt`` came from; it
is a deliberate, documented exception to the usual "prompts/<slug>.py holds
a fixed SYSTEM_PROMPT" contract (see agents/prompts/pbc_document_check.py) —
the entire feature this agent exists for is that the prompt is per-item and
human-approved, not fixed.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.data.loaders import extract_text_from_file
from agents.prompts.pbc_document_check import USER_PROMPT_TEMPLATE
from agents.settings.pbc_document_check import SETTINGS

_VALID_STATUSES = {"validated", "received", "insufficient"}


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_document_check agent and return its structured verdict.

    ``inputs`` keys:
        system_prompt (str, required — the approved validation prompt),
        pbc_description (str), file_path (str), file_ext (str), filename
        (str, optional), pbc_id (str, optional — tags the call as
        ``item_ref``).

    Returns ``{"status": "validated"|"received"|"insufficient", "notes": str}``.
    """
    document_text, _method = extract_text_from_file(
        inputs["file_path"], inputs["file_ext"], max_chars=SETTINGS["max_chars"]
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        pbc_description=inputs["pbc_description"],
        filename=inputs.get("filename") or inputs["file_path"],
        document_text=document_text,
    )

    client = client or ClaudeClient()
    message = client.message(
        user_prompt,
        system=inputs["system_prompt"],
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="pbc_document_check",
        item_ref=inputs.get("pbc_id"),
    )

    data = extract_json_block(text_from_message(message))
    if data.get("status") not in _VALID_STATUSES:
        data["status"] = "received"  # a malformed status still needs a human look, not a crash
    data.setdefault("notes", "")
    return data
