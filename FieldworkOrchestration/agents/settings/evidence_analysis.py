"""Run configuration for the evidence_analysis agent."""

SETTINGS = {
    # Opus + adaptive thinking: matches the source plan's emphasis on not
    # drawing conclusions beyond what evidence explicitly supports, and
    # flagging inference vs. fact -- real judgement, not extraction.
    "model": "claude-opus-4-8",
    "max_tokens": 2048,
    "thinking": "adaptive",
}
