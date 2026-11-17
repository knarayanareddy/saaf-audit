# FieldworkOrchestration

Orchestration agent to call all fieldwork agents and deliver quality information on the process.
Agents information is copied from the other repositories at September 8, 2026.

The repo hosts a growing set of **fieldwork agents** (see
[agents/README.md](agents/README.md) for the current catalogue — two
chained pipelines, the PBC workflow and the evidence-audit workflow, plus
several standalone agents), each with its own prompts, input files and
settings, plus **one orchestrator** that runs them, chains the ones that
depend on each other, and tracks quality/approval status across a run.

## Layout

```
agents/                 # the agents, the orchestrator, and the shared Claude client
  claude_init.py        # ClaudeClient — shared wrapper, model is a dynamic input
  prompts/              # prompt text, one module per agent
  data/                 # input files, one subfolder per agent
  settings/             # model/token/thinking config, one module per agent
webapp/                 # demo UI over the orchestrator — see webapp/README.md
IdeasVoiceAssistedAuditAgent   # scratch notes on ElevenLabs voice agents
```

Every folder has a `README.md` saying what belongs in it — read
[agents/README.md](agents/README.md) first: it holds the naming convention, the
agent contract, and the checklist for adding an agent. For the demo web UI
(role-based review flow: auditee delivers evidence, auditor reviews the AI
output, an eindverantwoordelijke auditor finalizes), see
[webapp/README.md](webapp/README.md) — it's a concept prototype, and that
README is explicit about what it does and doesn't solve yet.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env    # then fill in ANTHROPIC_API_KEY
```

Check the connection end to end:

```powershell
python -m agents.claude_init
# -> connection OK
```

`.env` is gitignored — never commit a real key.
