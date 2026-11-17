# Plan: AI Finding Escalation Agent — OWASP & Hallucination Findings to Azure DevOps

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `frank-lubbers-ai-finding-escalation-azure-devops.md` |
| **Submitter** | Frank Lubbers |
| **Organization** | Wolters Kluwer |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Agent |
| **Primary domain** | AI Governance / Incident Management |
| **Claimed By** | Frank Lubbers |

---

## 2. Problem Statement

When the OWASP LLM Top 10 checker and the hallucination detection skill produce findings, those findings currently stay within the audit toolchain. There is no automated path to escalate them into the organisation's incident management workflow.

As a result, security and quality findings identified by AI governance tooling are manually copied into Azure DevOps — a slow, error-prone step that delays remediation and breaks traceability between the audit finding and the work item.

**Gap vs. existing SAAF plans:** `owasp-ai-testing-agent.md` produces a scored OWASP security report; `llm-hallucination-detection-agent.md` produces annotated findings with hallucination risk flags. Neither plan has a downstream escalation step. This agent closes that gap.

---

## 3. Use-Case Type & Scope

**Type:** Agent

**Scope:**
- Accept output from `owasp-ai-testing-agent.md` (OWASP findings, F-XXXX format) and `llm-hallucination-detection-agent.md` (hallucination-flagged findings)
- Classify each finding by severity (Critical / High / Medium / Low)
- Create Azure DevOps work items: Issue type for OWASP security findings, Task type for hallucination quality findings
- Populate work item fields: title, description, severity, source agent, evidence fragment, remediation suggestion
- Return a push report with work item URLs and creation status

**Out of scope:**
- Findings from other SAAF agents (scope is limited to OWASP and hallucination outputs)
- Updating or closing existing work items
- Other incident management systems (Jira, ServiceNow) — Azure DevOps only at this stage

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Classification prompt: maps finding severity to Azure DevOps work item type and priority; enrichment prompt: generates remediation text from finding context |
| **Tools** | Python script using Azure DevOps REST API (`azure-devops` SDK); reads `finding-schema.json` output; writes push report JSON |
| **Regulatory** | IIA Standard 2400 (Communicating Results) — findings must be communicated to responsible parties; EU AI Act Art. 9 — risk management requires that identified risks are tracked and resolved |
| **Outputs** | Push report JSON (work item URLs, status per finding); updated finding objects with `azure_devops_work_item_id` field |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI audit finding escalation specialist.
Your role is to classify audit findings from AI governance checks and prepare them for entry into an incident management system.
Always preserve the original finding ID, evidence fragment, and source agent reference in the work item description.
Never omit a finding — if a work item cannot be created, log it as a failed escalation with the reason.
```

### Example user prompts

**Prompt 1 — OWASP finding classification:**
```
Classify the following OWASP audit finding for escalation to Azure DevOps.
Determine the work item type (Bug), priority (1=Critical, 2=High, 3=Medium, 4=Low),
and generate a one-paragraph description suitable for an engineering team.

Finding:
{
  "id": "F-0088",
  "title": "Prompt injection via delimiter attack succeeded in 2/5 test cases",
  "risk_rating": "High",
  "observation": "Direct injection tests using delimiter boundaries bypassed the system prompt.",
  "recommendation": "Implement input sanitization and structured prompt boundaries."
}
```

**Prompt 2 — Hallucination finding classification:**
```
Classify the following hallucination detection finding for escalation to Azure DevOps.
Determine the work item type (Task), priority, and generate a description that explains
the hallucination risk to a non-audit reviewer.

Finding:
{
  "id": "F-0102",
  "title": "ISO 27001 citation unverifiable — clause 8.2.3 does not exist",
  "risk_rating": "Medium",
  "observation": "The agent cited ISO 27001 clause 8.2.3 which does not exist in the standard.",
  "recommendation": "Validate all regulatory citations against RAG knowledge base before dossier entry."
}
```

**Intended file location:** `prompts/audit-use-cases/frank-lubbers-ai-finding-escalation-azure-devops.md`

---

## 6. Tools & Techniques

### Approach

The agent reads finding JSON from the two upstream agents, calls the Claude API to classify and enrich each finding, then uses the Azure DevOps REST API to create work items. Each work item includes a link back to the SAAF finding ID so traceability is maintained between the audit dossier and the engineering backlog.

### Example script or pseudocode

```python
import os
import json
import anthropic
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication

def escalate_finding(finding: dict, client: anthropic.Anthropic) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"Classify finding for Azure DevOps escalation:\n{json.dumps(finding)}"
        }]
    )
    return json.loads(response.content[0].text)

def create_work_item(org_url: str, project: str, pat: str, finding: dict, work_item_type: str):
    credentials = BasicAuthentication("", pat)
    connection = Connection(base_url=org_url, creds=credentials)
    wit_client = connection.clients.get_work_item_tracking_client()
    document = [
        {"op": "add", "path": "/fields/System.Title", "value": finding["title"]},
        {"op": "add", "path": "/fields/System.Description", "value": finding["observation"]},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": finding["priority"]},
    ]
    return wit_client.create_work_item(document, project, work_item_type)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), `azure-devops` SDK, `finding-schema.json`

**Intended file location:** `tools/scripts/frank-lubbers-ai-finding-escalation-azure-devops.py`

---

## 7. Regulatory Framework

| Standard | Requirement |
|---|---|
| **IIA Standard 2400** | Audit findings must be communicated to responsible parties in a timely manner |
| **IIA Standard 2600** | When significant findings are identified, management must be informed and remediation tracked |
| **EU AI Act Art. 9** | High-risk AI systems require a risk management system that tracks and resolves identified risks |
| **ISO 27001 A.16** | Information security incidents must be reported and managed through a formal process |

### Claude / AI tool usage notes

No real audit evidence or personal data will be sent to the Claude API. Only synthetic finding objects (conforming to `finding-schema.json`) will be used during development and testing.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format

**Format:** JSON

**Schema reference:** `outputs/schemas/finding-schema.json` (extended with `azure_devops_work_item_id` and `escalation_status` fields)

### Synthetic example output

```json
{
  "push_report": {
    "timestamp": "2026-04-21T10:30:00Z",
    "total_findings": 5,
    "created": 4,
    "failed": 1
  },
  "work_items": [
    {
      "finding_id": "F-0088",
      "source_agent": "owasp-ai-testing-agent",
      "work_item_type": "Issue",
      "azure_devops_work_item_id": 4821,
      "url": "https://dev.azure.com/org/project/_workitems/edit/4821",
      "priority": 2,
      "escalation_status": "created"
    },
    {
      "finding_id": "F-0102",
      "source_agent": "llm-hallucination-detection-agent",
      "work_item_type": "Task",
      "azure_devops_work_item_id": 4822,
      "url": "https://dev.azure.com/org/project/_workitems/edit/4822",
      "priority": 3,
      "escalation_status": "created"
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional)
- [x] Other: `azure-devops` Python SDK, Azure DevOps REST API

**Stretch goals:**

- [ ] Support Jira as an alternative escalation target (configurable via env var)
- [ ] Automatic work item status update when finding is resolved in the audit dossier

---

## 10. Collaboration & Cross-References

**Dependencies:**

- [`owasp-ai-testing-agent.md`](owasp-ai-testing-agent.md) — upstream source of OWASP security findings (F-XXXX format)
- [`llm-hallucination-detection-agent.md`](llm-hallucination-detection-agent.md) — upstream source of hallucination-flagged findings
- `outputs/schemas/finding-schema.json` — input schema this agent consumes

**What I plan to open-source:**

- The Python escalation script with Azure DevOps integration
- The classification and enrichment prompts
- A synthetic test dataset of 10 OWASP + 5 hallucination findings

**What help I'm looking for:**

- Someone with Azure DevOps admin access to test the work item creation in a real project
- Review of the severity-to-priority mapping (does Critical OWASP = Priority 1 in your org's ADO setup?)

**Cross-org interest:**

Other organisations using Azure DevOps for incident management can reuse this agent directly. The classification prompts are generic enough to adapt to Jira or ServiceNow with minimal changes.

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | In progress | Build at Hackathon #3 — create work items from synthetic OWASP + hallucination findings |
| **Check** | Not started | Test against real Azure DevOps project at organisation; validate work item fields with engineering team |
| **Act** | Not started | Extend to Jira target; integrate into SAAF agent pipeline as a post-processing step |

**Hackathon #3 task (Engineer role):**
Connect the escalation agent to the output of `owasp-ai-testing-agent.md`. Run against 5 synthetic findings. Verify work items appear in an Azure DevOps test project. Expected output: push report JSON with 5 work item URLs.

---

## 12. Open Questions

1. **Azure DevOps authentication**: Personal Access Token (PAT) is simplest for a hackathon prototype — is service principal authentication required for organisational adoption?
2. **Work item field mapping**: Different Azure DevOps projects use different custom fields. Should the agent use a configurable mapping file, or assume standard fields only?
3. **Finding deduplication**: If the same finding is escalated twice (e.g. re-run of the OWASP agent), should the agent create a new work item or update the existing one?
4. **Bidirectional sync**: Should resolved work items in Azure DevOps trigger a status update back in the SAAF finding dossier?
