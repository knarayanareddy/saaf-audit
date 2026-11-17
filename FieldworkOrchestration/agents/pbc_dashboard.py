"""pbc_dashboard agent — turns PBC validation results into a status dashboard.

Ported from Status_Dashboard_Agent in PBC-Assistant-Isabelle (Track 2 —
Evidence Collection). Takes the PBC list produced by ``pbc_creation`` and the
validation results produced by ``pbc_validation``, and returns completion
counts, percentage, outstanding IDs, and a short narrative summary.
"""

from __future__ import annotations

import json

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.pbc_dashboard import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.pbc_dashboard import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_dashboard agent and return its structured result.

    ``inputs`` keys:
        pbc_list (dict — the output of ``pbc_creation.run``),
        validation_status (dict — the output of ``pbc_validation.run``:
        ``{"results": [...]}``).
    """
    client = client or ClaudeClient()

    pbc_list = inputs["pbc_list"]
    validation_status = inputs["validation_status"]
    val_json = json.dumps(validation_status["results"], indent=2)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        audit_scope=pbc_list["audit_scope"],
        audit_period=pbc_list["audit_period"],
        total_items=len(pbc_list["items"]),
        val_json=val_json,
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="pbc_dashboard",
    )

    return extract_json_block(text_from_message(message))
