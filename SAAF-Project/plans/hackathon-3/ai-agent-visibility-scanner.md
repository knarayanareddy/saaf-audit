# Plan: AI Agent Visibility Scanner

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `ai-agent-visibility-scanner.md` |
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Agent |
| **Primary domain** | AI Governance / IT Governance |
| **Source** | WhatsApp: "AI Innovators: Hub • General" (April 2026) — Akto 2025 State of Agentic AI Security report shared: only **21% of enterprises have visibility into their own AI agents**. Discussion of "shadow AI" problem: employees deploy AI tools outside IT governance. NCSC NL Mythos directive (April 2026): organizations must assess their AI agent deployments. |

---

## 2. Problem Statement

Only 21% of enterprises know what AI agents are running in their organization (Akto 2025 State of Agentic AI Security). The other 79% have employees who have deployed:
- API integrations with Claude, GPT-4, Gemini in business tools
- N8N workflows calling AI APIs
- Claude Code or Cursor AI in development pipelines
- Microsoft Copilot Studio agents built by business users
- Zapier/Make automations with AI steps
- Browser extensions with AI capabilities

This is the **shadow AI** problem — analogous to shadow IT but with higher risk because AI agents can take autonomous actions, process sensitive data, and have unpredictable failure modes.

Internal audit cannot govern what it cannot see. The first step toward EU AI Act compliance, NCSC NL compliance, and responsible AI governance is knowing what AI agents exist.

**Gap:** No existing SAAF plan addresses AI agent discovery and inventory from an audit perspective.

---

## 3. Use-Case Type & Scope

**Type:** Agent

**Scope:**
- Scan for evidence of AI agent deployments using available signals (API logs, environment variables, installed packages, workflow tools, network traffic patterns)
- Interview-based discovery: structured questionnaire for IT managers, department heads, and developers
- Produce an AI agent inventory with: name, owner, data processed, autonomous capability, regulatory tier
- Risk-rate each discovered agent (using EU AI Act classification from `eu-ai-act-compliance-monitor.md`)
- Flag undocumented agents ("shadow AI") for governance review

**Out of scope:**
- Network packet inspection or deep system monitoring (requires IT cooperation)
- Actively blocking unauthorized AI usage (audit role — observe, not enforce)

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Interview questionnaire generator; API log analysis prompt; shadow AI risk assessment prompt; inventory synthesis prompt |
| **Tools** | Claude API (Sonnet), Python (file/env scan), `cli-audit-system-wrapper.md` (approved system commands), `eu-ai-act-compliance-monitor.md` (classification) |
| **Regulatory** | EU AI Act Art. 6+Annex III (high-risk classification), NCSC NL AI security directive (April 2026), IIA Standard 2110 (governance — assessing adequacy of IT governance processes) |
| **Outputs** | AI agent inventory JSON; shadow AI report; risk-rated agent register; discovery interview transcript |

---

## 5. Prompts

### Prompt 1 — Discovery Interview Generator
```
System: You are preparing an AI governance discovery interview for an internal audit.
Generate a structured questionnaire to identify AI agent deployments in a department.

The interview should identify:
1. What AI tools does the team use? (ChatGPT, Copilot, Claude, Gemini, etc.)
2. Are any AI tools connected to production systems or data?
3. Has anyone built automations that call AI APIs? (N8N, Zapier, Power Automate, custom scripts)
4. Does any AI tool have access to customer data, financial data, or employee data?
5. Who approved the use of each AI tool?
6. Is there a data processing agreement with each AI provider?

Tailor the questions for: [DEPARTMENT: IT / Finance / HR / Legal / Operations]

Output: numbered question list with follow-up probes for each.
```

### Prompt 2 — API Log Analysis
```
System: You are analyzing IT system logs to identify AI API usage within an organization.
Specifically, look for:
- HTTP requests to known AI API endpoints (api.anthropic.com, api.openai.com, 
  generativelanguage.googleapis.com, api.mistral.ai, ollama local ports)
- Authorization headers with AI provider key patterns (sk-ant-, sk-proj-, AIza...)
- AI-related package imports in Python/Node logs (anthropic, openai, langchain, litellm)
- AI tool user-agent strings (Claude Code, Cursor, Copilot Studio, N8N AI nodes)

For each hit: extract the source (system/team/user), frequency, and data type if determinable.

User: Analyze the following log excerpt for AI API usage:

[LOG_EXCERPT]

Output: list of discovered AI connections with confidence (High/Medium/Low) and context.
```

### Prompt 3 — Shadow AI Risk Assessment
```
System: You are assessing the risk of an undiscumented AI agent (shadow AI) in an organization.

Risk factors:
- Data sensitivity: personal data (High), financial data (High), internal only (Medium), public (Low)
- Autonomous actions: can take actions without human approval (High), human-in-the-loop (Low)
- Regulatory scope: EU AI Act high-risk category (Critical), GPAI (High), limited-risk (Low)
- Authorization: no IT approval (High), business approval but no IT review (Medium), approved (Low)
- DPA status: no data processing agreement with AI provider (High), DPA in place (Low)

User: Assess the risk of the following shadow AI deployment:

[AGENT_DESCRIPTION]

Output: risk rating (Critical/High/Medium/Low), rationale (3 sentences), 
recommended action (register + DPA review / escalate to CISO / accept with monitoring).
```

### Prompt 4 — Inventory Synthesis
```
System: You are synthesizing an organizational AI agent inventory report for internal audit.

Categorize discovered agents:
1. AUTHORIZED: registered, approved, DPA in place, EU AI Act tier known
2. PARTIALLY AUTHORIZED: business approved but missing IT review or DPA
3. SHADOW: not registered, discovered via logs or interviews only

For each shadow or partial agent: recommended action and deadline.

Overall metrics:
- Total agents discovered
- Shadow AI rate (% undocumented)
- High-risk agents (EU AI Act Annex III)
- DPA gaps (% without provider DPA)

User: Synthesize the following discovery results into an AI agent inventory:

[DISCOVERY_RESULTS]

Output: inventory JSON + Markdown summary report.
```

---

## 6. Tools & Techniques

| Tool | Role |
|---|---|
| Claude API (Sonnet) | Interview generation, log analysis, risk assessment |
| `cli-audit-system-wrapper.md` | Allowed system commands for environment/package scanning |
| `eu-ai-act-compliance-monitor.md` | Classification of each discovered agent |
| Python `pathlib` + `subprocess` | Scanning for AI packages in virtual environments (approved commands only) |

**Scan techniques (allowlisted only):**
```bash
# Find Python AI packages installed (allowlisted command)
pip list | grep -E "anthropic|openai|langchain|litellm|ollama|transformers"

# Find .env files with AI API keys (allowlisted via CLI wrapper)
find /path/to/scan -name ".env" -readable

# Check for running Ollama processes
pgrep -a ollama
```

All scan commands go through the CLI wrapper allowlist from `cli-audit-system-wrapper.md` — no unauthorized system access.

---

## 7. Regulatory Framework

| Standard | Requirement |
|---|---|
| **EU AI Act Art. 6 + Annex III** | Organizations must know which AI systems qualify as high-risk and apply corresponding obligations |
| **NCSC NL (April 2026 directive)** | Following Mythos capabilities disclosure, NCSC NL requires Dutch organizations to assess their AI agent security posture — you cannot assess what you haven't inventoried |
| **IIA Standard 2110** | Governance engagement — internal audit must assess whether the organization has adequate AI governance processes; this starts with knowing what AI is deployed |
| **GDPR Art. 30** | Records of processing activities — if an AI agent processes personal data, it must appear in the GDPR Art. 30 record |

---

## 8. Output Format

### AI Agent Inventory (JSON)
```json
{
  "scan_date": "2026-04-21",
  "organization": "[ORG]",
  "discovery_methods": ["IT interview", "log analysis", "developer questionnaire"],
  "summary": {
    "total_discovered": 23,
    "authorized": 8,
    "partially_authorized": 7,
    "shadow": 8,
    "shadow_rate_pct": 35,
    "high_risk_eu_ai_act": 2,
    "dpa_gaps": 11
  },
  "agents": [
    {
      "id": "AGENT-007",
      "name": "Finance team ChatGPT plugin (undocumented)",
      "status": "SHADOW",
      "discovered_via": "IT log analysis — api.openai.com calls from Finance subnet",
      "owner": "Unknown",
      "data_processed": "Possibly financial data (Finance subnet)",
      "eu_ai_act_tier": "PENDING CLASSIFICATION",
      "dpa_status": "NONE",
      "risk_rating": "High",
      "recommended_action": "Escalate to Head of Finance for owner identification; register within 30 days"
    }
  ]
}
```

---

## 9. Tech Stack

```
Language:     Python 3.9+
Dependencies: anthropic (Claude API)
Config:       ANTHROPIC_API_KEY from environment; scan paths from config JSON
Input:        IT interview responses JSON + log excerpts + env scan results
Output:       AI agent inventory JSON + shadow AI report Markdown
Permissions:  All system commands via cli-audit-system-wrapper allowlist only
```

---

## 10. Collaboration & Cross-References

**Dependencies:**
- `cli-audit-system-wrapper.md` — all system scan commands must go through the allowlist
- `eu-ai-act-compliance-monitor.md` — classifies each discovered agent under EU AI Act
- `saaf-strapi-synthetic-data.md` — test the scanner against a synthetic AI deployment inventory

**Feeds into:**
- `eu-ai-act-compliance-monitor.md` — discovered agents become input to the compliance monitor
- `audit-automation-overview.md` — the "shadow AI" finding is a level-0 governance gap before automation levels even apply

**WhatsApp source attribution:**
> The impetus for this plan was the **Akto 2025 State of Agentic AI Security** report shared in the **"AI Innovators: Hub • General"** WhatsApp group (April 2026): only 21% of enterprises know what AI agents are running inside them. This was discussed alongside the NCSC NL Mythos directive, creating a sense of urgency: organizations cannot defend against AI-level threats if they do not know which AI systems they have deployed.

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | Pending | Build at Hackathon #3 |
| **Check** | Not started | Run discovery questionnaire on SAAF community organizations; measure shadow AI rate |
| **Act** | Not started | Update scan commands as new AI tools emerge |

**Hackathon #3 task (Analyst role):**
Run the discovery questionnaire on your own organization. Count: how many AI tools does your team use? Of those, how many are in the IT register? Calculate your shadow AI rate. Expected finding: 30-60% of AI tools are not in the IT register.

---

## 12. Open Questions

1. **Passive vs. active scanning**: Active log analysis requires IT cooperation and authorization. Should the agent offer both a "passive" mode (interview-only) and an "active" mode (log analysis + package scan)?
2. **False positives**: A developer using Claude for personal code review on a work laptop may not constitute shadow AI. What is the organizational threshold for "AI agent" vs. "AI tool use"?
3. **Continuous monitoring**: Shadow AI grows over time as employees discover new tools. Should the scanner run quarterly or as part of continuous monitoring?
4. **GDPR Art. 30 integration**: Can the discovered AI agent inventory automatically generate GDPR Art. 30 data processing records for each agent?
