"""pbc_upload_check agent — fast sanity check at auditee upload time.

Runs immediately when a file is uploaded, before it ever reaches the
auditor queue — see agents/prompts/pbc_upload_check.py for why this is
deliberately a coarse, fast pass rather than the detailed review
(``pbc_document_check`` does that, after a tailored prompt has been
proposed and approved — see ``pbc_validation_prompt_proposal``).
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.data.loaders import extract_text_from_file
from agents.prompts.pbc_upload_check import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.pbc_upload_check import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_upload_check agent and return its structured result.

    ``inputs`` keys:
        pbc_description (str), file_path (str), file_ext (str), pbc_id
        (str, optional — tags the call as ``item_ref`` so it shows up in
        this item's audit-trail history).
    """
    document_excerpt, _method = extract_text_from_file(
        inputs["file_path"], inputs["file_ext"], max_chars=SETTINGS["excerpt_chars"]
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        pbc_description=inputs["pbc_description"],
        filename=inputs.get("filename") or inputs["file_path"],
        document_excerpt=document_excerpt,
    )

    client = client or ClaudeClient()
    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="pbc_upload_check",
        item_ref=inputs.get("pbc_id"),
    )

    return extract_json_block(text_from_message(message))
