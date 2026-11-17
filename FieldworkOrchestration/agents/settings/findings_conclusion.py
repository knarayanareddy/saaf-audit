"""Run configuration for the findings_conclusion agent."""

SETTINGS = {
    # Opus + adaptive thinking: assigning a risk rating and drafting a
    # grounded observation/recommendation is judgement work, matching the
    # bar set for pbc_reminder's escalation drafting.
    "model": "claude-opus-4-8",
    "max_tokens": 1536,
    "thinking": "adaptive",
}
