"""Run configuration for the pbc_upload_check agent."""

SETTINGS = {
    # Sonnet, no thinking, small budget: this needs to feel instant to the
    # auditee at upload time — it's a coarse sanity check, not the detailed
    # review (that's pbc_document_check, which does warrant Opus/thinking).
    "model": "claude-sonnet-4-6",
    "max_tokens": 512,
    "thinking": None,
    "excerpt_chars": 4000,
}
