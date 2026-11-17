"""Run configuration for the pbc_document_check agent."""

SETTINGS = {
    # Opus + adaptive thinking: this is the compliance-critical judgement
    # call the whole propose/approve flow exists to get right — matches the
    # bar set for pbc_validation's per-item judgement.
    "model": "claude-opus-4-8",
    "max_tokens": 1536,
    "thinking": "adaptive",
    "max_chars": 40_000,
}
