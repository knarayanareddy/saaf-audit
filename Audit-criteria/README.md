# Track 1 — Planning en Orientatie

AI agents for the **planning & orientation** phase of an internal audit, built on
the SAAF (Shared Audit Agents Framework) use cases. This repository contains three
connected components that turn risk inputs into a CAE-ready audit planning
package — one of them driven by voice.

## Components

### 1. Audit Planning Orchestrator — `tools/scripts/audit_planning_orchestrator/`

An LLM "command" agent that runs and commands the audit-planning sub-agents as
tools:

```
UC7 RCM Builder  →  UC8 Work Program  →  UC9 Quality & Resource Guard (Go / No-Go)
```

The orchestrator (`claude-opus-5`) decides the calls; the loop enforces the parts
that must not be left to chance — a schema gate at every hand-off, a bounded
No-Go recovery loop, and a per-run audit trail (IIA 2340).

```bash
# Offline, no API key — proves the wiring and the No-Go → re-run → Go loop:
python -m tools.scripts.audit_planning_orchestrator.orchestrator --simulate
```

Details: [`tools/scripts/audit_planning_orchestrator/README.md`](tools/scripts/audit_planning_orchestrator/README.md).

### 2. UC7 Voice Walkthrough (ElevenLabs) — `tools/scripts/uc7_voice_walkthrough/`

A voice front-end for UC7. An **ElevenLabs Conversational-AI agent** conducts the
process walkthrough by voice, captures risks/controls as they are spoken via
ElevenLabs **client tools**, and calls UC7 to build the RCM live — then reads the
result back. ElevenLabs owns the voice loop; Claude (UC7) owns the audit
synthesis.

```bash
# Offline scripted walkthrough — no mic, no API key:
python -m tools.scripts.uc7_voice_walkthrough.walkthrough --simulate
```

Details: [`tools/scripts/uc7_voice_walkthrough/README.md`](tools/scripts/uc7_voice_walkthrough/README.md).
The voice component reuses the orchestrator's UC7 wrapper and schema gate, so it
front-ends the same UC7 → UC8 → UC9 pipeline.

### 3. Audit Criteria Orchestrator — `tools/scripts/audit_criteria_orchestrator/`

Drafts and hardens an `AUDIT-CRITERIA.md` for a PR: read PR → Q&A → draft →
review ∥ stress test (criteria are executed) → revise → gate (soft block:
retry / override / abort, bounded in code) → place.

```bash
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate
```

Details: [`tools/scripts/audit_criteria_orchestrator/README.md`](tools/scripts/audit_criteria_orchestrator/README.md).

## Audit criteria

[`AUDIT-CRITERIA.md`](AUDIT-CRITERIA.md) covers the Audit Planning Orchestrator.
Every acceptance criterion is executable offline:
`python -m tools.scripts.audit_planning_orchestrator.criteria_checks --list`.

## Plans

The design documents (SAAF plan template) live in
[`plans/hackathon-4/`](plans/hackathon-4/):

- [Audit Planning Orchestrator](plans/hackathon-4/p-papen-audit-planning-orchestrator.md)
- [UC7 Voice RCM Walkthrough](plans/hackathon-4/p-papen-uc7-voice-rcm-walkthrough.md)
- [Audit Criteria Orchestrator](plans/hackathon-4/p-audit-criteria-orchestrator.md)

The orchestrator system prompt is in
[`prompts/audit-use-cases/`](prompts/audit-use-cases/).

## Running

All commands run from the repository root, Python 3.9+. The `--simulate` paths
use only the standard library. For live / API-backed runs:

- Orchestrator and UC7 refine: `pip install anthropic`, set `ANTHROPIC_API_KEY`
  (models `claude-opus-5` / `claude-sonnet-5`).
- Voice session: `pip install "elevenlabs[pyaudio]"`, set `ELEVENLABS_API_KEY`
  and `ELEVENLABS_AGENT_ID` (create the agent from
  `tools/scripts/uc7_voice_walkthrough/agent_config.py`).

## Notes

- **Synthetic data only.** Inputs are synthetic planning data — no real audit
  evidence or personal data. API keys come from environment variables only.
- Guardrails: no `rm`/`sudo`/`curl`/`wget`/`ssh` in scripts, no runtime
  `pip install`, scripts under `tools/scripts/`, `runs/` output is gitignored.
- Extracted from the shared SAAF-Project framework as the Track 1 submission.

The agent.yaml mandate schema this guard enforces is documented in [docs/conventions/agent-yaml.md](https://github.com/SAAF-Project/SAAF-Project/blob/main/docs/conventions/agent-yaml.md) (SAAF-Project #145) and implemented in [SAAF-Project/saaf-living-map](https://github.com/SAAF-Project/saaf-living-map).
