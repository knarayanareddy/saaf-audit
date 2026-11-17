# ICFCOP Control Testing Agent

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Schuberg Philis) |
| **Organisation** | Schuberg Philis |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Schuberg Philis operates under an **Integrated Control Framework for Compliance and Operations Purposes (ICFCOP)** that maps 12 compliance frameworks (ISO 27001, SOC 2, NIS2, DORA, GDPR, BIO, ISO 9001, ISAE 3402, ISO 22301, NIST CSF, CIS Controls, COBIT) onto approximately 30 control domains with 6 central "mega-controls" at the core.

The problem: auditors test these controls manually, cross-referencing each finding against all 12 frameworks to determine which compliance obligations are affected. This mapping is:

- **Time-consuming** — a single control test may require checking 12 framework documents
- **Error-prone** — mappings between frameworks are not always consistent or documented
- **Opaque** — different auditors interpret framework overlaps differently

There is no automated way to:
1. Load a control test result and instantly see which frameworks are impacted
2. Generate a framework-specific finding narrative from a single raw observation
3. Identify which of the 6 mega-controls is failing and what its cascading framework impact is

---

## 3. Use-Case Type and Scope

**Audit domain:** IT Governance — Integrated Control Framework Testing (ICFCOP)

**Applicable standards:**

- ISO 27001:2022 (primary)
- SOC 2 (Trust Service Criteria)
- DORA (Digital Operational Resilience Act)
- NIS2 Directive
- GDPR
- COBIT 2019
- NIST CSF 2.0
- BIO (Baseline Informatiebeveiliging Overheid)

**In scope:**

- Loading ICFCOP control framework mappings (12 frameworks × 30 domains)
- Accepting a control test result (evidence, observation, conclusion)
- Generating cross-framework impact analysis: which frameworks, which articles/controls are violated?
- Drafting framework-specific finding narratives (Condition / Criterion / Cause / Effect)
- Prioritisation: which framework violation is highest risk?

**Out of scope:**

- Real Schuberg Philis audit data (synthetic datasets only)
- Automated evidence collection (handled by separate Evidence Harvester plan)
- Penetration testing or technical scanning

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt: ICFCOP impact analyser; new user prompt template for control test → cross-framework finding generation |
| **Tools** | Python script (`tools/scripts/icfcop_agent.py`); JSON control-mapping schema (`docs/reference/icfcop-control-map.json`) |
| **Regulatory** | New: `regulatory/control-mappings/icfcop-crosswalk.md` mapping all 12 frameworks to 30 control domains |
| **Outputs** | Structured finding per framework conforming to `outputs/schemas/finding-schema.json`; cross-framework impact summary in Markdown |

---

## 5. Prompts

### System prompt (draft)

```
You are an ICFCOP (Integrated Control Framework for Compliance and Operations Purposes) audit
analyst for Schuberg Philis.

You work with a control framework that maps 12 compliance standards onto 30 control domains.
The 6 core mega-controls are:
1. Identity & Access Management
2. Change Management & SDLC
3. Business Continuity & DR
4. Incident & Problem Management
5. Data Protection & Privacy
6. Vendor & Third-Party Risk

When given a control test result (observation, evidence, conclusion), you will:
1. Identify which mega-control is affected
2. List all 12 frameworks where this mega-control appears
3. For each affected framework, cite the specific article/control reference
4. Assess the severity of the violation per framework (High / Medium / Low)
5. Draft a one-paragraph finding narrative per framework (Condition / Criterion / Cause / Effect)

Always respond with valid JSON conforming to the ICFCOP finding schema.
Never fabricate framework references — only cite articles that are in your mapping.
```

### Example user prompts

**Prompt 1 — Control test input:**
```
Control domain: Identity & Access Management
Test performed: Review of user access provisioning for privileged accounts (SY-ADM-001)
Evidence reviewed: Active Directory export, HR offboarding records (synthetic data)
Observation: 12 former employees still have active privileged accounts 90+ days after termination.
Conclusion: Control FAILED — leaver process not enforced for privileged accounts.

Analyse cross-framework impact. Which mega-control? Which frameworks are violated?
Generate finding narratives for the top 3 most severely affected frameworks.
```

**Prompt 2 — Framework gap check:**
```
We have completed testing of the following controls this quarter:
[list of tested controls with results]

Which of the 12 frameworks now has the highest number of untested or failing controls?
Produce a framework-level compliance dashboard (tested %, failing %, risk score).
```

**Intended file location:** `prompts/audit-use-cases/icfcop-control-testing.md`

---

## 6. Tools and Techniques

### Approach

1. **Control mapping JSON** — A structured crosswalk (`icfcop-control-map.json`) that maps each of the 30 control domains to specific articles across all 12 frameworks. This becomes the agent's "regulatory memory."
2. **Agent loop** — Auditor inputs a control test result (text). Agent retrieves relevant mappings, generates cross-framework impact analysis, drafts findings.
3. **Synthetic test data** — Strapi provides synthetic access review datasets, change tickets, and incident logs for testing.
4. **Output schema** — Each generated finding conforms to `outputs/schemas/finding-schema.json`.

### Example script or pseudocode

```python
import json, anthropic
from pathlib import Path

# Load ICFCOP crosswalk mapping
crosswalk = json.loads(Path("docs/reference/icfcop-control-map.json").read_text())

client = anthropic.Anthropic()

def analyse_control_test(observation: str, control_domain: str) -> dict:
    relevant_frameworks = crosswalk.get(control_domain, {})
    system_prompt = build_system_prompt(relevant_frameworks)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": observation}]
    )
    return json.loads(response.content[0].text)

def build_system_prompt(framework_map: dict) -> str:
    # Inject the relevant framework articles into the prompt context
    framework_context = json.dumps(framework_map, indent=2)
    return SYSTEM_PROMPT_TEMPLATE.format(framework_context=framework_context)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), JSON (control mapping), Strapi (synthetic test data)

**Intended file location:** `tools/scripts/icfcop_agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO 27001:2022 | A.5.15–A.5.18 (Access control), A.8.24 (Change), A.5.37 (Documented procedures) |
| DORA | Art. 9 (ICT risk), Art. 12 (Backup), Art. 13 (Incident classification) |
| GDPR | Art. 32 (Security of processing), Art. 33 (Breach notification) |
| SOC 2 | CC6 (Logical and Physical Access), CC7 (System Operations) |
| NIST CSF 2.0 | PR.AA (Access control), DE.CM (Monitoring) |

### Claude / AI tool usage notes

- All test data is synthetic — no real Schuberg Philis audit evidence committed.
- Framework crosswalk is based on publicly available standards; no confidential content.
- Agent outputs are advisory — human auditor must validate all generated finding narratives.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (per-framework finding) + Markdown (cross-framework summary)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "id": "F-001",
  "title": "Privileged accounts not deactivated upon termination — ISO 27001 A.5.18 violation",
  "risk_rating": "High",
  "framework": "ISO 27001:2022",
  "article": "A.5.18 — Access rights",
  "mega_control": "Identity & Access Management",
  "observation": "12 former employees retain active privileged accounts 90+ days post-termination.",
  "criterion": "ISO 27001 A.5.18 requires access rights to be removed promptly upon termination.",
  "cause": "HR offboarding process does not trigger automatic AD account deactivation for privileged users.",
  "effect": "Unauthorised access to critical systems by former employees; potential data breach risk.",
  "recommendation": "Implement automated deactivation trigger via HR system → IAM integration within 30 days.",
  "cross_framework_impact": {
    "DORA": {"article": "Art. 9.2", "severity": "High"},
    "SOC2": {"article": "CC6.2", "severity": "High"},
    "GDPR": {"article": "Art. 32", "severity": "Medium"},
    "NIST CSF": {"article": "PR.AA-02", "severity": "High"}
  }
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] JSON control-mapping schema
- [x] Strapi (synthetic access review / incident data)

**Stretch goals:**

- [ ] Web UI (Streamlit) for auditors to paste control test results without CLI
- [ ] Excel export of cross-framework impact matrix
- [ ] Integration with Jira: auto-create finding tickets from agent output
- [ ] Automated completeness check: which controls have not been tested this quarter?

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- ICFCOP crosswalk JSON schema (12 frameworks × 30 domains)
- Python agent script
- System prompt template
- Synthetic test dataset (access reviews, change tickets)

**What help I'm looking for:**

- Auditors familiar with SOC 2, DORA, and NIS2 to validate the framework crosswalk
- Engineers to help with Strapi synthetic data setup
- Vaktechniek to review finding narrative quality

**Cross-org interest:**

The ICFCOP framework is Schuberg Philis-specific, but the multi-framework crosswalk approach is broadly applicable. Any organisation managing overlapping compliance obligations (DORA + ISO 27001, SOx + COBIT) can adapt this agent.

**Related SAAF plans:**

- [`plans/hackathon-2/the-control-freaks-uc7-rcm-builder.md`](../hackathon-2/the-control-freaks-uc7-rcm-builder.md) — RCM builder shares the control-testing lifecycle pattern
- [`plans/hackathon-2/frank-van-dissel-uc7-rcm-builder.md`](../hackathon-2/frank-van-dissel-uc7-rcm-builder.md) — parallel RCM submission with three-stage design
- [`plans/hackathon-3/saaf-strapi-synthetic-data.md`](saaf-strapi-synthetic-data.md) — Strapi sandbox provides test data for this agent

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Framework crosswalk designed; agent architecture defined |
| **Do** | In progress | Crosswalk JSON + prototype script at Hackathon #3 |
| **Check** | Not started | Validate finding narratives against human auditor baseline |
| **Act** | Not started | Target: pilot on one real Schuberg Philis control domain (with synthetic data) |

---

## 12. Open Questions

1. Is the ICFCOP crosswalk accurate enough to include in the agent's context, or does it need legal/framework expert validation first?
2. Should each framework get its own finding, or should the agent produce one consolidated finding with a cross-framework appendix?
3. How do we handle version differences (e.g. ISO 27001:2013 vs 2022) when organisations are at different stages of migration?
4. Can this agent be integrated with the Jira/Confluence MCP to auto-fetch evidence from tickets?
