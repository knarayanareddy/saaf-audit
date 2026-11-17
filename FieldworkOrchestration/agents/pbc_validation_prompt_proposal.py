"""pbc_validation_prompt_proposal agent — proposes a tailored validation prompt for one PBC item.

An auditor reviews (and may edit) the proposed prompt before it is ever run
against a document — see ``pbc_document_check``, which is the agent that
actually performs the check, using whatever prompt was approved. This
agent's only job is the proposal.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.data.loaders import extract_text_from_file
from agents.prompts.pbc_validation_prompt_proposal import (
    CONTEXT_SECTION_TEMPLATE,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from agents.settings.pbc_validation_prompt_proposal import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_validation_prompt_proposal agent and return its structured result.

    ``inputs`` keys:
        pbc_description (str), file_path (str), file_ext (str), filename
        (str, optional), pbc_id (str, optional — tags the call as
        ``item_ref``), risk / control / control_objective / planned_work
        (str, all optional — omit all four when this item isn't linked to
        a UC8 work program; include whichever are known otherwise).

    Returns ``{"proposed_prompt": str, "rationale": str}``.
    """
    document_excerpt, _method = extract_text_from_file(
        inputs["file_path"], inputs["file_ext"], max_chars=SETTINGS["excerpt_chars"]
    )

    context_section = ""
    if inputs.get("risk") or inputs.get("control"):
        context_section = CONTEXT_SECTION_TEMPLATE.format(
            risk=inputs.get("risk") or "(not stated)",
            control=inputs.get("control") or "(not stated)",
            control_objective=inputs.get("control_objective") or "(not stated)",
            planned_work=inputs.get("planned_work") or "(not stated)",
        )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        pbc_description=inputs["pbc_description"],
        context_section=context_section,
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
        agent="pbc_validation_prompt_proposal",
        item_ref=inputs.get("pbc_id"),
    )

    if message.stop_reason == "max_tokens":
        # The response was cut off mid-generation — extract_json_block would
        # only surface this as a cryptic JSONDecodeError on the truncated
        # JSON (seen in practice: "Unterminated string..."). Raise something
        # an operator can actually act on instead: this item's context
        # (risk/control/planned work/document excerpt) needs more room than
        # settings["max_tokens"] currently allows.
        raise RuntimeError(
            "pbc_validation_prompt_proposal's response was cut off before "
            f"finishing (hit max_tokens={SETTINGS['max_tokens']}) for "
            f"{inputs.get('pbc_id') or 'this item'} — increase max_tokens in "
            "agents/settings/pbc_validation_prompt_proposal.py."
        )

    return extract_json_block(text_from_message(message))
