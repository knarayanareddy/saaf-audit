"""Agent Drift Rater — static design review of AI agents for drift susceptibility.

"Drift" (Drift Watch, J. Angula, Agents Gone Rogue Amsterdam, 6 Oct 2026): an agent acts
outside its approved mandate without anyone having changed that mandate. This package rates
each agent in the SAAF-Project GitHub org (or a local repo) against its own documented
mandate and the talk's six red flags, and produces findings, a scorecard, a dashboard and
improvement advice.

Static review only: results are design evidence, never certification.

Run from the repo root:
    python -m tools.scripts.agent_drift_rater.cli selftest
    python -m tools.scripts.agent_drift_rater.cli rate --simulate
    python -m tools.scripts.agent_drift_rater.cli rate --path <local repo> --no-llm
"""

__all__ = ["cli"]
