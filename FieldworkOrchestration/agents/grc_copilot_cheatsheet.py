"""grc_copilot_cheatsheet agent — generates an M365 Copilot cheat sheet for an audit domain.

Built from the GRC Copilot Mindshift Agent plan (Track 2 — Evidence
Collection, plans/hackathon-3/grc-copilot-mindshift-agent.md). Unlike the
PBC agents, this was never a working code repository — the source is a
draft system prompt and pseudocode only. Output is a Markdown practitioner
guide (copy-paste-ready Copilot prompts per scenario), not a structured
finding: the plan is explicit that this isn't machine-readable audit
evidence, it's a human aid for using Copilot effectively.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, text_from_message
from agents.prompts.grc_copilot_cheatsheet import (
    DEFAULT_AUDIENCE,
    DEFAULT_LANGUAGE,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from agents.settings.grc_copilot_cheatsheet import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the grc_copilot_cheatsheet agent and return its structured result.

    ``inputs`` keys:
        audit_domain (str — e.g. "Identity & Access Management controls
        (ISO 27001 A.5.15-A.5.18)"), focus_areas (list[str], optional —
        specific tasks the auditor needs prompts for; defaults to letting
        Claude pick relevant scenarios from the six in the system prompt),
        language (str, optional), audience (str, optional).
    """
    client = client or ClaudeClient()

    focus_areas = inputs.get("focus_areas")
    focus_areas_text = (
        "\n".join(f"- {area}" for area in focus_areas)
        if focus_areas
        else "(none specified — pick the scenarios most relevant to this domain)"
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        audit_domain=inputs["audit_domain"],
        focus_areas=focus_areas_text,
        language=inputs.get("language") or DEFAULT_LANGUAGE,
        audience=inputs.get("audience") or DEFAULT_AUDIENCE,
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="grc_copilot_cheatsheet",
    )

    return {"cheat_sheet_markdown": text_from_message(message)}
