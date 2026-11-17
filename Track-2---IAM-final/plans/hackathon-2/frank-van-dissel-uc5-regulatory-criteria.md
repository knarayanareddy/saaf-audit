# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Frank van Dissel & Lauren Browne) |
| **Organisation** | Mollie |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Audits must be measured against valid, authoritative "yardsticks." Identifying the right external regulations, industry frameworks, and internal policies applicable to an audit scope is time-consuming — and getting it wrong means testing against the wrong criteria. Beyond simple identification, GIAS 13.4 requires auditors to assess whether management's own criteria are adequate to measure objective achievement. The Regulatory & Evaluation Criteria Agent automates this: it identifies applicable regulations and frameworks, reviews management's internal KPIs, assesses their adequacy against external standards, identifies gaps, and produces a structured Evaluation Criteria Matrix — including a Discussion Guide for cases where management's criteria fall short.

This is **Use Case 5 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It consumes the Context Brief from [UC1](frank-van-dissel-uc1-policy-process-intake.md) and feeds its output into the [RCM Builder (UC7)](frank-van-dissel-uc7-rcm-builder.md).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Evaluation Criteria Identification (GIAS 13.4)

**Applicable standards:**

- GIAS 13.4 — "Identify the most relevant criteria to be used to evaluate the aspects of the activity... Assess the extent to which the board and senior management have established adequate criteria."
- GIAS 13.2 — "Identify and gather... applicable frameworks, guidance, and other criteria... Identify the criteria that management uses to measure whether the activity is achieving its objectives."

**In scope:**

- Regulatory discovery: identifying applicable external regulations and industry frameworks (GDPR, DORA, NIST, SOX, ISO 27001, NIS2, etc.)
- Internal policy ingestion: identifying operational expectations from internal policies and procedures
- Management criteria extraction: identifying KPIs, benchmarks, and measures used by management
- Adequacy assessment: comparing management's criteria against external best practice / regulatory requirements
- Alternative identification: proposing alternative criteria where management's are inadequate
- Requirement-to-risk mapping: linking regulatory clauses to risks identified in UC2–UC4
- Producing a Discussion Guide for board/management conversations where criteria are inadequate

**Out of scope:**

- Testing compliance against identified criteria (that is the role of UC8)
- Legal interpretation of regulatory requirements
- Real-time regulatory change monitoring (see [WhatsTheNews](yellowraptor-whats-the-news.md) for that capability)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Regulatory discovery prompt; adequacy assessment prompt; Discussion Guide drafting prompt |
| **Tools** | Legal/regulatory RAG pipeline for high-fidelity retrieval; gap analysis logic for semantic comparison of KPIs vs. requirements; version control for regulatory currency |
| **Regulatory** | Directly produces regulatory criteria mappings; reuse and extend `regulatory/control-mappings/` in the SAAF-Project repo; related to [Compliance-Report-Generator](rohan-sobha-compliance-report-generator.md) |
| **Outputs** | Evaluation Criteria Matrix: external frameworks, internal standards, adequacy rating, criteria gap report, Discussion Guide |

---

## 5. Prompts

### System prompt (draft — Regulatory Discovery)

```
You are a regulatory compliance specialist for internal audit.
Given an audit scope and jurisdiction, identify all applicable external regulations,
industry frameworks, and standards.
For each identified framework: state the specific articles or controls relevant
to this scope, and explain why they apply.
Only include frameworks that are demonstrably applicable — do not speculate.
Ensure you are referencing the current version of each regulation.
```

### System prompt (draft — Adequacy Assessment)

```
You are an internal audit quality specialist.
Given management's internal KPIs and measurement criteria for an activity,
and the applicable external regulatory requirements for that activity:
1. For each management KPI, assess whether it adequately measures the
   corresponding regulatory or best-practice requirement (Adequate/Inadequate)
2. For Inadequate ratings: identify the gap and propose an alternative criterion
   from a recognized external framework
3. Draft structured talking points for a discussion with board/management
   about inadequate criteria (tone: constructive, specific, evidence-based)
```

### Example user prompts

**Prompt 1 — DORA Compliance Scenario:**
```
Audit scope: IT Incident Management at a Dutch bank.
Jurisdiction: Netherlands (EU).
Management's current criteria: "Average incident resolution time < 4 hours."

Identify applicable regulatory frameworks. Assess whether the management KPI
adequately covers DORA requirements. If not, propose alternative criteria.
```

**Prompt 2 — Inadequate KPI Scenario:**
```
Audit scope: Customer Support process.
Management's current criteria: "Average handle time < 5 minutes."
Audit objective includes: "Data Privacy compliance."

Is "average handle time" adequate to measure Data Privacy compliance?
If not, suggest alternative criteria.
```

**Intended file location:** `prompts/audit-use-cases/uc5-regulatory-criteria.md`

---

## 6. Tools and Techniques

### Approach

Three-component pipeline:

1. **Regulatory Discovery:** RAG pipeline retrieves applicable laws, regulations, and industry standards for the audit scope and jurisdiction (using up-to-date regulatory knowledge base)
2. **Adequacy Assessment:** Semantic comparison between management's internal KPIs and the identified external requirements; produces Adequate/Inadequate verdicts with justification
3. **Gap Report and Discussion Guide:** For inadequate criteria, proposes alternative criteria from recognized frameworks and drafts talking points for the required management/board discussion

### Quality Safeguards

**Safeguard 1 — Version & Authority Validator:** A specialized agent cross-references all identified regulations against "Last Updated" metadata to ensure the most current version is cited. Flags any outdated references.

**Safeguard 2 — Framework Alignment Check:** If a specific framework is cited (e.g., ISO 27001), the agent verifies that all mandatory controls relevant to the specific audit scope have been captured — preventing cherry-picking of only convenient requirements.

### Example script or pseudocode

```python
def run_criteria_agent(audit_scope: str, context_brief: dict, management_kpis: list) -> dict:
    # Step 1: Regulatory discovery
    frameworks = discover_frameworks(audit_scope)            # RAG pipeline
    validated = version_validator(frameworks)               # Currency check
    
    # Step 2: Adequacy assessment
    assessment = assess_adequacy(management_kpis, validated)
    
    # Step 3: Gap report
    gaps = identify_gaps(assessment)
    discussion_guide = draft_discussion_guide(gaps)
    
    return build_criteria_matrix(validated, assessment, gaps, discussion_guide)
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6 for adequacy assessment), RAG pipeline for regulatory knowledge base

**Intended file location:** `tools/scripts/uc5-regulatory-criteria/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.4 | Identifying evaluation criteria; assessing adequacy of management's criteria |
| GIAS 13.2 | Identifying applicable frameworks, guidance, and other criteria |
| GDPR, DORA, NIS2, ISO 27001, SOX | Example frameworks discoverable by this agent |

### Claude / AI tool usage notes

No real management documents or confidential KPI data should be sent to the API in production. Use synthetic or anonymized versions for testing. The RAG pipeline operates on publicly available regulatory texts — no proprietary data is ingested.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (Evaluation Criteria Matrix) + Markdown (Discussion Guide)

**Schema reference:** Criteria gaps map to `outputs/schemas/finding-schema.json` (inadequate management criteria = finding)

### Test Scenario 1 — DORA in Financial Services

- **Input:** Audit of "IT Incident Management" for a bank; management KPI = "average resolution time < 4 hours"
- **Expected:** Identification of DORA Art. 17 incident classification requirements; detection that "resolution time" does not cover DORA's classification criteria requirement
- **Validation:** Independent review by compliance officer

### Test Scenario 2 — Inadequate Management KPIs

- **Input:** Customer Support audit; management only measures "average handle time"
- **Expected:** Agent flags that handle time is inadequate to measure Data Privacy objective; suggests "% of interactions with properly redacted PII in logs"
- **Validation:** Lead auditor confirms gap is material

### Synthetic example output

```json
{
  "external_frameworks": [
    {"framework": "DORA", "relevant_articles": ["Art. 17", "Art. 18", "Art. 19"], "applicability": "Mandatory for credit institutions"}
  ],
  "management_criteria": [
    {
      "kpi": "Average incident resolution time < 4 hours",
      "adequacy": "Inadequate",
      "gap": "DORA Art. 17 requires classification by impact level — resolution time alone does not satisfy this requirement",
      "alternative": "Percentage of incidents classified by DORA severity tier within 1 hour of detection"
    }
  ],
  "discussion_guide": "When meeting with management: 'Your current KPI measures speed of resolution, which is valuable. However, DORA Art. 17 specifically requires classification of incidents by impact level...'"
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] RAG pipeline (regulatory knowledge base)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Real-time regulatory update integration (link with [WhatsTheNews](yellowraptor-whats-the-news.md))
- [ ] Multi-jurisdiction support (EU + US + UK simultaneously)

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Regulatory discovery and adequacy assessment prompts
- Version & Authority Validator logic
- Evaluation Criteria Matrix JSON schema
- Discussion Guide prompt templates

**What help I'm looking for:**

- Legal or compliance specialists to validate the adequacy assessment logic
- Organizations with diverse regulatory scope (e.g. both DORA and GDPR in scope) for testing

**Related SAAF plans:**

- [UC1 — Policy-to-Process Intake](frank-van-dissel-uc1-policy-process-intake.md) — provides Context Brief input
- [UC7 — RCM Builder](frank-van-dissel-uc7-rcm-builder.md) — consumes Criteria Matrix as input
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates criteria coverage
- [Compliance-Report-Generator](rohan-sobha-compliance-report-generator.md) — closely related: both identify applicable frameworks; consider alignment
- [WhatsTheNews](yellowraptor-whats-the-news.md) — regulatory monitoring skill; could feed regulatory updates into this agent's knowledge base

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie compliance audit criteria |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. How do we keep the regulatory knowledge base current — should it use a live RAG pipeline against official regulatory websites, or a curated and periodically updated document store?
2. How do we handle situations where multiple frameworks apply and their requirements conflict?
3. How does this agent align with the [Compliance-Report-Generator](rohan-sobha-compliance-report-generator.md) — should these be merged into a single shared tool?
