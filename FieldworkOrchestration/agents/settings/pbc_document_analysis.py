"""Run configuration for the pbc_document_analysis agent."""

SETTINGS = {
    # Opus + adaptive thinking: matches the source agent — judging whether a
    # document actually satisfies a PBC request (vs. just being on-topic)
    # is a judgement call.
    "model": "claude-opus-4-8",
    "max_tokens": 2048,
    "thinking": "adaptive",
    # How much of an extracted document's text to send to the model.
    "max_chars": 40_000,
}
