"""Run configuration for the document_evidence_extraction agent."""

SETTINGS = {
    # Sonnet with vision, no extended thinking: matches the source plan's
    # own choice — per-page extraction is careful reading, not multi-step
    # judgement (whole-document gap analysis, where judgement matters more,
    # is left to a future agent that consumes the merged output).
    "model": "claude-sonnet-4-6",
    "max_tokens": 2048,
    "thinking": None,
    # Safety cap: each page is a separate Claude call (and, for scanned
    # pages, a separate image render) — cap so a large PDF can't silently
    # rack up cost. Override per call for longer documents.
    "max_pages": 20,
    # A digital-PDF page with less extracted text than this is treated as
    # "scanned" (no usable digital text layer) and rendered to an image
    # instead of sent as text.
    "min_digital_text_chars": 40,
}
