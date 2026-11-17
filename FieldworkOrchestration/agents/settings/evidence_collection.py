"""Run configuration for the evidence_collection agent."""

SETTINGS = {
    # Sonnet, no extended thinking: classifying type/source/reliability of
    # already-gathered items is organizing work, not the judgement-heavy
    # step (that's evidence_analysis).
    "model": "claude-sonnet-4-6",
    "max_tokens": 2048,
    "thinking": None,
}
