# UC8 — Audit Work Program Agent

Part of the **Standard Audit Agent Framework (SAAF)**.

Transforms a Risk & Control Matrix (RCM) into a detailed, executable engagement work program compliant with **GIAS 13.5** (resources) and **GIAS 13.6** (tasks, methodologies, auditor assignments).

---

## What it does

For each control in the RCM the agent generates:

| Phase | Output |
|---|---|
| Context | Control objective, frequency, owner |
| Design | Test of Design step with methodology, evidence, hours, auditor |
| Execution | Test(s) of Effectiveness with population, sampling, CAAT suggestions |
| QA | Six sufficiency flags (INQUIRY_ONLY, EVIDENCE_MISSING, SAMPLE_TOO_SMALL, POPULATION_NOT_RECONCILED, PERIOD_INCOMPLETE, INDEPENDENCE_GAP — the last one fires either when the control owner is also the sole evidence provider, or when the assigned auditor's name matches the control owner) |
| Planning | Auditor assignments distributed by available hours + resource overrun alerts |

All controls are submitted to the API in a single batch call (50% token discount).

---

## Output files

Every run writes four files to the output folder:

| File | Description |
|---|---|
| `work_program.json` | Full structured work program + resource alert |
| `work_program.md` | Human-readable markdown report |
| `work_program.xlsx` | Excel workbook — "Work Program" tab (one row per test step) + "Resource Summary" tab (all auditors, including unassigned) |
| `work_program_log.json` | Full run log: timestamps, API entrypoint, model, prompts sent, raw responses, token usage |

---

## Installation

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and fill in your ANTHROPIC_API_KEY
```

---

## Usage

```bash
python work_program_generator.py \
    --rcm Input/rcm_output.json \
    --resources Input/resource_directory.json \
    --output outputs/work_program.json
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `--rcm` | `Input/rcm_output.json` | Path to RCM JSON (UC7 format from upstream UC7 agent) |
| `--resources` | `Input/resource_directory.json` | Path to auditor resource directory |
| `--output` | `outputs/work_program.json` | Base path for all output files |

---

## RCM input format

The agent expects UC7 hierarchical format (`risks[].stage2.controls[]`) as produced by the upstream UC7 RCM Builder.

```json
{
  "rcm_version": "2.0.0",
  "risks": [
    {
      "risk_id": "RISK-0001",
      "stage1": {
        "risk_statement": "...",
        "risk_category": "Financial"
      },
      "stage2": {
        "inherent_risk_rating": "High",
        "controls": [
          {
            "control_id": "CTRL-0001",
            "description": "...",
            "control_owner": "...",
            "frequency": "Monthly",
            "execution_type": "IT-Dependent",
            "significance": "Key"
          }
        ]
      }
    }
  ]
}
```

### Resource directory (`Input/resource_directory.json`)

```json
[
  {
    "name": "Jan Bakker",
    "skills": ["Senior Auditor", "IT Audit"],
    "available_hours": 40
  }
]
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Your Anthropic API key |
| `AUDIT_SCOPE_PERIOD` | Optional | Defaults to `Jan-Dec 2025` |

---

## Project structure

```
Audit-Work-Program-Agent-UC-8-/
├── .env.example                   ← copy to .env and fill in your key
├── .claudeignore                  ← prevents Claude from reading .env
├── .gitignore
├── requirements.txt               ← anthropic, python-dotenv, openpyxl
├── README.md
├── CLAUDE.md                      ← guidance for Claude Code
├── AUDIT-CRITERIA.md              ← A2 audit-criteria doc: control objectives, acceptance
│                                     criteria, coverage gaps, validation status
├── work_program_generator.py      ← main agent script
├── work-program-agent.md          ← system prompt documentation
├── PLAN inge-garretsen-audit-work-program-agent.md  ← original hackathon plan
├── Input/
│   ├── rcm_output.json            ← live RCM output from UC7 (primary input)
│   ├── resource_directory.json   ← auditor pool with skills and available hours
│   └── rcm-schema.json            ← UC7 RCM JSON schema reference
└── outputs/                       ← default --output target (gitignored — see .gitignore)
```

The per-model example runs (`outputs Haiku/`, `outputs Sonnet/`, `outputs Opus/`) were removed on 2026-10-04; they remain in git history.

---

## SAAF connections

- **Upstream:** UC7 (RCM Builder) — feed its JSON output as `--rcm` (use `Input/rcm_output.json`)
- **Downstream:** UC9 (QA Review) — consumes `control_id` → `control_objective` from this output

---

## Guardrails

- No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- No runtime `pip install`
- No real audit evidence, credentials, or personal data committed
- API keys loaded from environment variables only; `.env` excluded from Claude reads via `.claudeignore`

