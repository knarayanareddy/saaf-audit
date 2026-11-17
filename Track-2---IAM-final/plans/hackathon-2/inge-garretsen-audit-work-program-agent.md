# Plan: Audit Work Program Agent (UC 8)

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Inge Garretsen |
| **Organisation** | Anonymous |
| **Session** | Session 2 |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Auditors schrijven work programs handmatig: ze nemen een Risk & Control Matrix (RCM), bedenken per control een toetsingsaanpak en schatten uren in. Dit is tijdrovend, inconsistent tussen teamleden, en mist vaak de analytische diepgang die CAATs (Computer-Assisted Audit Techniques) kunnen bieden. Een AI-agent kan dit werk structureren: per control de juiste testmethodologie selecteren, CAATs-kansen signaleren, uren schatten en auditors toewijzen op basis van beschikbaarheid en skills.

---

## 3. Use-Case Type and Scope

**Audit domain:** Cross-domain — werkt met elke RCM als input, ongeacht het auditonderwerp

**Applicable standards:**

- GIAS 13.5 — Resources identification (uren en skills per taak)
- GIAS 13.6 — Work program: criteria, tasks, methodologies, auditor assignments

**In scope:**

- Genereren van Test of Design (ToD) en Test of Operating Effectiveness (ToE) stappen per control uit de RCM
- Methodologiekeuze per stap (inquiry / observation / inspection / re-performance / analytical procedure)
- Identificatie van CAATs-kansen met toolspecificatie (Python, SQL, Claude Code)
- Auditeurstoewijzing op basis van een resource-directory (skill-tags + beschikbaarheid)
- Urenschatting per taak en resource-alert bij overschrijding
- Sufficiency-check: vlag wanneer methodologie onvoldoende is voor hoog-significante risico's

**Out of scope:**

- Daadwerkelijke uitvoering van CAATs-scripts
- UC 9 (QA-review van het work program door de CAE)
- Integratie met ticketsystemen (Jira, ServiceNow)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt + user prompt templates in `prompts/audit-use-cases/work-program-agent.md` |
| **Tools** | New Python script `tools/scripts/work_program_generator.py` — reads RCM JSON, calls Claude API, outputs work program |
| **Regulatory** | Reuse `regulatory/guardrails/` for allowed commands checklist |
| **Outputs** | Work program as JSON + Markdown (own schema per control entry); `outputs/schemas/finding-schema.json` is used downstream when a test step produces a finding — linked via `control_id` → `control_objective` |

---

## 5. Prompts

### System prompt (draft)

```
You are an internal audit work program specialist.
Your role is to translate a Risk & Control Matrix (RCM) into a detailed,
executable engagement work program compliant with GIAS 13.5 and 13.6.

For every control in the RCM, generate:
1. A Test of Design (ToD) step
2. One or more Tests of Operating Effectiveness (ToE)
3. The methodology for each step:
   inquiry / observation / inspection / re-performance / analytical procedure
4. If analytical procedures apply: specify the tool (Python, SQL, Claude Code)
   and a pseudocode outline of the analysis
5. The evidence required (source system, time period)
6. Pass/Fail criteria
7. Estimated hours
8. Required auditor skill tag (e.g. "IT Specialist", "Data Analyst", "Senior Auditor")
   — the script resolves skill tag → named auditor from the resource directory; do not invent names

Guardrail: If a High-significance risk has only "Inquiry" as methodology,
flag this as INSUFFICIENT and propose at least one additional method.

Always respond in valid JSON.
Never fabricate control descriptions — use only what is provided in the RCM input.
```

### Example user prompts

**Prompt 1:**
```
Here is the RCM entry:
{
  "risk_id": "R-004",
  "risk": "Unauthorized payments processed due to missing approval",
  "control_id": "C-004",
  "control": "All payment runs above €10,000 require dual approval in the ERP system",
  "control_type": "Automated",
  "significance": "High"
}

Auditor resource pool:
[
  {"name": "Jan Bakker", "skills": ["Senior Auditor"], "available_hours": 40},
  {"name": "Sara Li", "skills": ["Data Analyst", "Python"], "available_hours": 24}
]

Generate the work program steps for this control.
```

**Prompt 2:**
```
Process the following RCM (3 controls) and produce a complete work program.
Flag any resource conflicts if total estimated hours exceed available hours.
[RCM JSON attached]
```

**Intended file location:** `prompts/audit-use-cases/work-program-agent.md`

---

## 6. Tools and Techniques

### Approach

1. Read RCM JSON input (output from UC 7 / manually prepared)
2. Call Claude API per control row using the system prompt above
3. Parse JSON output per control into work program entries
4. Apply sufficiency check: high-significance risk + inquiry-only → flag + add method
5. Match auditors from resource directory based on skill tags
6. Calculate total hours per auditor; generate resource alert if exceeded
7. Write final output to Markdown + JSON

### Example script or pseudocode

```python
import json
import anthropic

client = anthropic.Anthropic()  # API key via ANTHROPIC_API_KEY env var

SYSTEM_PROMPT = "..."  # full prompt from section 5

def generate_work_program(rcm: list[dict], auditors: list[dict]) -> dict:
    work_program = []
    for control in rcm:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_prompt(control, auditors)}]
        )
        steps = json.loads(response.content[0].text)
        steps = sufficiency_check(steps, control["significance"])
        work_program.append(steps)
    resource_alert = check_resource_totals(work_program, auditors)
    return {"work_program": work_program, "resource_alert": resource_alert}
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), Strapi (synthetic RCM data)

**Intended file location:** `tools/scripts/work_program_generator.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.5 | Types and quantity of resources — hours and skills per task |
| GIAS 13.6 | Tasks, methodologies, tools, and auditor assignments per control |

### Claude / AI tool usage notes

No real audit evidence or personal data is sent to the API. All testing uses synthetic RCM data (hardcoded JSON or generated via Strapi).

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only (`ANTHROPIC_API_KEY`)

---

## 8. Output Format and Examples

**Format:** JSON + Markdown

**Schema reference:** The work program has its own schema per control entry (see example below). It is separate from `outputs/schemas/finding-schema.json`, which is used when a test step produces a finding. The handoff point between the two is `control_id` (work program) → `control_objective` (finding schema).

### Synthetic example output

```json
{
  "control_id": "C-004",
  "risk_id": "R-004",
  "significance": "High",
  "test_of_design": {
    "step": "Inspect ERP configuration to verify the dual-approval threshold is set at €10,000",
    "methodology": "Inspection",
    "evidence": "ERP system settings screenshot — current configuration",
    "pass_criteria": "Threshold = €10,000 and minimum 2 distinct approvers required",
    "estimated_hours": 1,
    "skill_required": "Senior Auditor",
    "assigned_to": "Jan Bakker"
  },
  "tests_of_effectiveness": [
    {
      "step": "Extract all payment runs > €10,000 in scope period; verify each has 2 distinct approver IDs",
      "methodology": "Analytical procedure",
      "tool": "Python / pandas",
      "pseudocode": "df[df['amount'] > 10000].groupby('payment_id')['approver_id'].nunique().lt(2)",
      "evidence": "ERP payment export Jan–Dec",
      "pass_criteria": "Zero exceptions — all payments have ≥ 2 distinct approvers",
      "estimated_hours": 4,
      "skill_required": "Data Analyst",
      "assigned_to": "Sara Li"
    }
  ],
  "sufficiency_flag": null
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [x] Strapi (synthetic data API — optional)

**Stretch goals:**

- [ ] Automatic RCM ingest from UC 7 output (end-to-end pipeline)
- [ ] Markdown resource table with per-auditor hour burndown

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- System prompt (`prompts/audit-use-cases/work-program-agent.md`)
- Python script (`tools/scripts/work_program_generator.py`)
- Synthetic test RCM (3-5 controls across different domains)

**What help I'm looking for:**

- Review by someone with GIAS 13.5/13.6 expertise on the sufficiency-check logic
- Feedback from UC 9 (QA-review) builders on what fields they need as input, so the work program output schema can be aligned early

**Cross-org interest:**

Yes — any team building UC 7 (RCM Builder) needs UC 8 as the natural next step. Happy to collaborate on a combined demo.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | All sections filled in; open questions resolved |
| **Do** | In progress | Prototype built during hackathon |
| **Check** | Not started | Planned for internal adoption after hackathon |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. ~~Moet auditeurstoewijzing per stap of per control plaatsvinden (of beide)?~~
   **Besluit:** Auditeurstoewijzing vindt plaats per test step (ToD en elke ToE afzonderlijk), zoals al getoond in het synthetic example output in sectie 8.

2. ~~Hoe integreren we het work program output-schema optimaal met `finding-schema.json`?~~
   **Besluit:** Scheiding bewaren (Option A). Het work program heeft een eigen schema; `finding-schema.json` wordt gebruikt zodra een test step een bevinding oplevert. De koppeling verloopt via `control_id` in het work program → `control_objective` in het finding schema. UC 8 blijft gefocust op planning; UC 9 (QA-review) consumeert findings onafhankelijk.

3. ~~Zijn er al resource-directory formaten beschikbaar in de repo die we als standaard kunnen aannemen voor UC 8 en UC 9?~~
   **Besluit:** Nee — UC 8 definieert zelf het resource-directory schema (naam, skills, beschikbare uren). Dit kan later als standaard worden voorgesteld aan de SAAF-community.
