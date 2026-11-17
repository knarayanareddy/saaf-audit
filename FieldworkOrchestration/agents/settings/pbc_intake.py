"""Run configuration for the pbc_intake agent."""

SETTINGS = {
    # Sonnet, no extended thinking: matching a filename to a request
    # description is simple pattern-matching, and every suggestion still
    # needs an auditor's confirmation — no need for Opus-level judgement.
    "model": "claude-sonnet-4-6",
    "max_tokens": 2048,
    "thinking": None,
}
