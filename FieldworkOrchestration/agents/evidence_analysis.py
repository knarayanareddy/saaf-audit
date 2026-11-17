"""evidence_analysis agent — assesses evidence sufficiency/appropriateness for a control objective.

Stage 2 of the Mollie Group X evidence-audit pipeline (Track 2 — Evidence
Collection, plans/alignment/mollie-group-x-evidence-audit.md). Supports an
optional revision pass: pass ``feedback`` (from a ``quality_check`` verdict
on a prior run) to have this agent address specific issues, mirroring the
source plan's own revision-loop pseudocode.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.evidence_analysis import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.evidence_analysis import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the evidence_analysis agent and return its structured result.

    ``inputs`` keys:
        control_objective (str), evidence_collected (list[dict] — the
        ``evidence_collected`` field from ``evidence_collection.run``'s
        output), feedback (str, optional — quality-review feedback to
        address in a revised analysis).
    """
    client = client or ClaudeClient()

    evidence_summary = "\n".join(
        f"- {item['type']} ({item['source']}, reliability: {item['reliability']}): "
        f"{item['relevance_note']}"
        for item in inputs["evidence_collected"]
    )

    feedback = inputs.get("feedback")
    feedback_section = (
        f"\nFeedback from a prior quality review of your previous analysis — "
        f"address this in your revised analysis:\n{feedback}\n"
        if feedback
        else ""
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        control_objective=inputs["control_objective"],
        evidence_summary=evidence_summary,
        feedback_section=feedback_section,
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="evidence_analysis",
    )

    return extract_json_block(text_from_message(message))
