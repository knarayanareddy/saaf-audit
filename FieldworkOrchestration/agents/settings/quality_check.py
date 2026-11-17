"""Run configuration for the quality_check agent."""

SETTINGS = {
    # Opus + adaptive thinking: catching an unsupported claim or a subtle
    # scope gap in someone else's answer is a judgement task, not
    # extraction — an under-powered reviewer is worse than no reviewer.
    "model": "claude-opus-4-8",
    "max_tokens": 2048,
    "thinking": "adaptive",
}
