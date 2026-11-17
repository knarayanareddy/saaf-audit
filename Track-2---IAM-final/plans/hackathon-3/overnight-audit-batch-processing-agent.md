# Overnight Audit Batch Processing Agent

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Long-running audit tasks — building a Risk & Control Matrix from scratch, assessing 100+ vendor contracts, generating work programs for 20 audit domains — exceed the context window of a single Claude session. When Claude loses context, the auditor must restart manually, losing partial progress and re-explaining everything.

Current workarounds (copying partial output, summarizing in new chats) are fragile and slow. There is no pattern for running audit tasks that take hours or days without continuous human supervision.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Agent Infrastructure / All Domains

**Applicable standards:**

- IIA IPPF — Standard 2010 (Planning), 2340 (Engagement Supervision)
- ISO 42001 — AI management systems

**In scope:**

- Pattern for persisting audit task state across Claude context resets using JSON task files
- Overnight batch runs: agents execute autonomously while the auditor sleeps
- Progress tracking via filesystem checkpoints between context windows
- Example: RCM building for 30 control domains, vendor assessment batch (100+ vendors)

**Out of scope:**

- Real-time audit tasks requiring human judgment between steps
- Tasks requiring live system API calls that time out overnight
- Multi-machine distributed execution (single local machine only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | System prompt for the batch orchestrator; task-file prompt template |
| **Tools** | `tools/scripts/audit-batch-agent.py` — orchestrator that reads task file, calls Claude, writes progress |
| **Regulatory** | IIA 2340 (supervision) — overnight runs must produce an audit trail |
| **Outputs** | JSON task file (`audit-batch-task.json`) + checkpoint files per completed sub-task |

---

## 5. Prompts

### System prompt (draft)

```
You are an audit batch processing agent running in overnight mode.
Your task definition is provided in the attached JSON task file.
Work through each sub-task in the "pending" list sequentially.
After completing each sub-task:
1. Write your output to the specified output file
2. Move the sub-task from "pending" to "completed" in the task file
3. Append a one-line summary to the audit trail log
If you approach your context limit, save your current state to the task file and stop cleanly — the orchestrator will restart you with the updated task file.
Never skip a sub-task. Never modify the "completed" list of sub-tasks.
Always cite the source data used for each finding.
```

### Example user prompts

**Prompt 1 — RCM batch:**
```
Task file: audit-batch-task.json
Mode: overnight-batch
Current sub-task: Build RCM for domain "Change Management"
Input: Strapi change ticket export (500 records, attached)
Output: Write to outputs/rcm-change-management.md
Proceed.
```

**Prompt 2 — Vendor assessment batch:**
```
Task file: vendor-assessment-task.json
Mode: overnight-batch
Current sub-task: Assess vendor "Contoso B.V." against DORA ICT third-party risk criteria
Input: vendor-contracts/contoso-bv.pdf (attached)
Output: Append finding to outputs/vendor-assessments.jsonl
Proceed.
```

**Intended file location:** `prompts/audit-use-cases/overnight-batch-agent.md`

---

## 6. Tools and Techniques

### Approach

The Ralph loop pattern: an external Python orchestrator manages the task queue. It reads a JSON task file, selects the next pending sub-task, launches a Claude API call with that sub-task's context, writes the output to a checkpoint file, then marks the sub-task complete. The orchestrator loops until the pending list is empty or a stop condition is met.

Context window exhaustion is handled gracefully: the agent writes partial progress to the task file before stopping. The orchestrator detects the stop signal and restarts with the updated state — no work is lost.

### Example script or pseudocode

```python
import json
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

def run_batch(task_file: Path):
    with open(task_file) as f:
        task = json.load(f)

    while task["pending"]:
        sub_task = task["pending"][0]
        print(f"Processing: {sub_task['id']} — {sub_task['description']}")

        # Build context from task definition + sub-task input
        context = build_context(task, sub_task)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=task["system_prompt"],
            messages=[{"role": "user", "content": context}],
        )

        output = response.content[0].text

        # Write checkpoint
        out_path = Path(sub_task["output_file"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output)

        # Update task file
        task["completed"].append(task["pending"].pop(0))
        task["completed"][-1]["output"] = str(out_path)
        with open(task_file, "w") as f:
            json.dump(task, f, indent=2)

        print(f"  ✓ Written to {out_path}")

    print("Batch complete.")
```

**Task file format (`audit-batch-task.json`):**

```json
{
  "batch_id": "rcm-build-2026-04-21",
  "system_prompt": "...",
  "pending": [
    {
      "id": "rcm-01",
      "description": "Build RCM for Change Management",
      "input_file": "data/change-tickets.csv",
      "output_file": "outputs/rcm-change-management.md"
    }
  ],
  "completed": [],
  "audit_trail": []
}
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), JSON, pathlib

**Intended file location:** `tools/scripts/audit-batch-agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2010 | Risk-based planning — batch agent runs must be scoped to planned audit objectives |
| IIA IPPF 2340 | Engagement supervision — overnight runs produce checkpoint files as audit trail |
| ISO 42001 | AI system management — batch agent requires documented system description |

### Claude / AI tool usage notes

Overnight batch runs use the Claude API with synthetic or anonymized data only. Real audit evidence must not be included in batch input files. Output files (RCMs, finding drafts) require auditor review before entering the dossier.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON task file (state) + Markdown per sub-task output + JSONL audit trail

**Schema reference:** `outputs/schemas/finding-schema.json` for finding outputs

### Synthetic example output (task file after 2 completed sub-tasks)

```json
{
  "batch_id": "rcm-build-2026-04-21",
  "pending": [
    { "id": "rcm-03", "description": "Build RCM for User Access Management" }
  ],
  "completed": [
    {
      "id": "rcm-01",
      "description": "Build RCM for Change Management",
      "output": "outputs/rcm-change-management.md",
      "completed_at": "2026-04-21T23:14:02Z"
    },
    {
      "id": "rcm-02",
      "description": "Build RCM for Incident Management",
      "output": "outputs/rcm-incident-management.md",
      "completed_at": "2026-04-21T23:31:45Z"
    }
  ],
  "audit_trail": [
    "2026-04-21T23:14:02Z rcm-01 COMPLETE — 6 risks, 12 controls identified",
    "2026-04-21T23:31:45Z rcm-02 COMPLETE — 4 risks, 9 controls identified"
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] JSON task files (filesystem state)
- [x] Strapi (synthetic data API — input data source)

**Stretch goals:**

- [ ] GitHub Actions scheduled job (cron overnight run)
- [ ] Slack/Teams notification when batch completes
- [ ] Web dashboard showing progress across multiple active batches

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `audit-batch-agent.py` orchestrator script
- JSON task file schema and example task files
- System prompt template for batch agents

**Help requested:**

- Auditors: propose overnight batch use cases from your practice (what tasks are worth automating overnight?)
- Engineers: extend the orchestrator with parallel sub-task execution
- Risk managers: validate that checkpoint files meet audit trail requirements

**Cross-org interest:**

Any organization running multi-domain audits (20+ control domains, 100+ vendor assessments) can benefit from this pattern. The orchestrator is domain-agnostic — any SAAF plan that currently requires manual Claude restarts is a candidate for batch wrapping.

**Related SAAF plans:**

- [`the-control-freaks-uc7-rcm-builder.md`](../hackathon-2/the-control-freaks-uc7-rcm-builder.md) — primary batch use case (RCM building)
- [`audit-loop-orchestration-sdk.md`](audit-loop-orchestration-sdk.md) — SDK-based variant of this pattern
- [`audit-subagent-coordination-framework.md`](audit-subagent-coordination-framework.md) — parallel multi-agent extension

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Pattern designed; task file schema defined |
| **Do** | In progress | Hackathon #3: implement orchestrator, run RCM batch on Strapi data |
| **Check** | Not started | Validate: does checkpoint recovery work after context reset? |
| **Act** | Not started | Target: production overnight run for H4 |

---

## 12. Open Questions

1. What is the maximum safe batch size (number of sub-tasks) before overnight runs risk hitting API rate limits?
2. Should the task file format be standardized across SAAF so any plan can be wrapped as a batch job?
3. How should auditors review overnight output — before or after all sub-tasks complete?
4. Can this pattern work with local models (Ollama) to avoid overnight API costs?
