"""Run configuration for the cli_evidence_analysis agent."""

SETTINGS = {
    # Opus + adaptive thinking: deciding what counts as an "audit-relevant
    # exception" in arbitrary CLI output (like pbc_validation's judgement
    # calls) needs more than pattern extraction.
    "model": "claude-opus-4-8",
    "max_tokens": 2048,
    "thinking": "adaptive",
}
