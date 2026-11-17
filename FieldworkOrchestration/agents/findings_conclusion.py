"""findings_conclusion agent — drafts the final finding or effective confirmation.

Stage 4 of the Mollie Group X evidence-audit pipeline (Track 2 — Evidence
Collection, plans/alignment/mollie-group-x-evidence-audit.md).
"""

from __future__ import annotations

import json

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.findings_conclusion import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.findings_conclusion import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the findings_conclusion agent and return its structured result.

    ``inputs`` keys:
        control_objective (str), analysis (dict — the output of
        ``evidence_analysis.run``), quality_verdict (str — e.g. "pass",
        "requires_revision", or "not reviewed").
    """
    client = client or ClaudeClient()

    user_prompt = USER_PROMPT_TEMPLATE.format(
        control_objective=inputs["control_objective"],
        analysis_json=json.dumps(inputs["analysis"], indent=2),
        quality_verdict=inputs.get("quality_verdict", "not reviewed"),
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="findings_conclusion",
    )

    return extract_json_block(text_from_message(message))
