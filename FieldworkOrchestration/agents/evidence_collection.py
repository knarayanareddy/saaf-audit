"""evidence_collection agent — organizes gathered evidence for a control objective.

Stage 1 of the Mollie Group X evidence-audit pipeline (Track 2 — Evidence
Collection, plans/alignment/mollie-group-x-evidence-audit.md). See
agents/prompts/evidence_collection.py for what's plan-specified vs. this
port's own design.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.evidence_collection import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.evidence_collection import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the evidence_collection agent and return its structured result.

    ``inputs`` keys:
        control_objective (str), evidence_items (list[str] — a free-text
        description per item, e.g. "Access review log Q4 2025 (system
        export): 342 users reviewed, 12 revoked").
    """
    client = client or ClaudeClient()

    evidence_items = "\n".join(f"- {item}" for item in inputs["evidence_items"])
    user_prompt = USER_PROMPT_TEMPLATE.format(
        control_objective=inputs["control_objective"],
        evidence_items=evidence_items,
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="evidence_collection",
    )

    return extract_json_block(text_from_message(message))
