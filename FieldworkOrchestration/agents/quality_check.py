"""quality_check agent — independent second-opinion review of one Claude call.

Not specific to any one fieldwork agent: it reviews an audit-trail-shaped
record (system prompt, user prompt, response) from *any* agent and returns a
pass / requires_revision / fail verdict with concrete issues. This is the
automated half of quality assurance — a human auditor's sign-off is still
required per standard fieldwork procedure; this agent's job is to flag what
that auditor should look at first, not to replace their judgement.

Typically invoked in bulk via ``orchestrator.review_run`` (one review per
audit trail entry of a run), not called ad hoc.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.quality_check import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.quality_check import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the quality_check agent and return its structured verdict.

    ``inputs`` keys (mirror an ``audit_trail`` entry):
        agent (str, optional — the slug of the agent being reviewed),
        system_prompt (str, optional), user_prompt (str), response_text (str),
        item_ref (str, optional — carried through from the entry being
        reviewed, so a review of an item's call is itself findable by that
        same item_ref).
    """
    client = client or ClaudeClient()

    user_prompt = USER_PROMPT_TEMPLATE.format(
        agent=inputs.get("agent") or "unknown",
        system_prompt=inputs.get("system_prompt") or "(none)",
        user_prompt=inputs["user_prompt"],
        response_text=inputs["response_text"],
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="quality_check",
        item_ref=inputs.get("item_ref"),
    )

    return extract_json_block(text_from_message(message))
