"""Run configuration for the pbc_validation_prompt_proposal agent."""

SETTINGS = {
    # Opus + adaptive thinking: working out what actually needs checking for
    # a specific risk/control is a judgement call, not extraction — the
    # entire point of this agent is to replace a one-size-fits-all prompt
    # with something that reflects real audit reasoning about this item.
    "model": "claude-opus-4-8",
    # 2048 was too tight and truncated mid-JSON in real use (stop_reason
    # "max_tokens", every single call, once a real UC8 risk/control/planned
    # -work context was included) — extract_json_block then fails on the
    # cut-off string with a raw JSONDecodeError instead of a usable result.
    # The output itself is a full drafted system prompt plus a rationale,
    # not a short classification, so it genuinely needs the room.
    "max_tokens": 6000,
    "thinking": "adaptive",
    "excerpt_chars": 6000,
}
