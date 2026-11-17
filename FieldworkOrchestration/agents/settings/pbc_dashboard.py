"""Run configuration for the pbc_dashboard agent."""

SETTINGS = {
    # Opus + adaptive thinking: matches the source agent — the arithmetic is
    # simple, but the narrative summary should read as a coherent status
    # judgement, not a template fill.
    "model": "claude-opus-4-8",
    "max_tokens": 4096,
    "thinking": "adaptive",
}
