"""Audit Planning Orchestrator.

An LLM "command" agent that runs and commands the Mollie audit-planning
sub-agents (UC7 RCM Builder -> UC8 Work Program -> UC9 Quality & Resource Guard)
via tool-calls, with schema gates at every hand-off, a bounded No-Go recovery
loop, and a full per-run audit trail.

See README.md for usage. Design: plans/hackathon-4/p-papen-audit-planning-orchestrator.md
"""

__all__ = ["orchestrator", "sub_agents", "schemas", "prompts", "run_logger"]
