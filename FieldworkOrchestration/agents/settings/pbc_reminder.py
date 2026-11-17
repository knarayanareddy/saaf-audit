"""Run configuration for the pbc_reminder agent."""

SETTINGS = {
    # Opus + adaptive thinking: matches the source agent — escalation tone
    # needs to be calibrated per item, not templated.
    "model": "claude-opus-4-8",
    "max_tokens": 4096,
    "thinking": "adaptive",
}
