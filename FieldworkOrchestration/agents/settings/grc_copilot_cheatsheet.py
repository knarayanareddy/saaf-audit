"""Run configuration for the grc_copilot_cheatsheet agent."""

SETTINGS = {
    # Sonnet, no extended thinking: matches the source plan's own choice —
    # adapting a template prompt library to a named domain is a moderate
    # creative-writing task, not deep multi-step judgement.
    "model": "claude-sonnet-4-6",
    "max_tokens": 2048,
    "thinking": None,
}
