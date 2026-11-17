"""Run configuration for the pbc_creation agent."""

SETTINGS = {
    # Opus: phrasing an actionable request and judging standard-vs-urgent
    # is still a judgement call, not extraction — matches the source
    # agent's model choice. No extended thinking: each call now drafts one
    # short item, not a whole list — nothing here needs multi-step
    # reasoning, and "adaptive" thinking has repeatedly been observed to
    # consume its entire budget disproportionately on tasks like this (see
    # pbc_scope_from_work_program's settings for the measured case).
    "model": "claude-opus-4-8",
    "max_tokens": 1024,
    "thinking": None,
}
