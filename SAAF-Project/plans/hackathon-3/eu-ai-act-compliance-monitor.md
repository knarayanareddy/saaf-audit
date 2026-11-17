# Plan: EU AI Act Compliance Monitor

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `eu-ai-act-compliance-monitor.md` |
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Agent |
| **Primary domain** | Compliance & Regulatory — EU AI Act |
| **Source** | WhatsApp: "AI Innovators: Hub • General" (April 2026) — EU AI Act August 2, 2026 GPAI compliance deadline repeatedly discussed; AI Toezichtcongres (AP, RDI, EU AI Act) shared; EU AI Act portal (artificialintelligenceact.eu) shared; ALTAI self-assessment tool shared. WhatsApp: "AI in Internal Audit" — IIA Algorithm Assurance training (Imran Nashir) signals the IIA community is actively preparing for AI regulatory compliance. |

---

## 2. Problem Statement

The EU AI Act's GPAI (General Purpose AI) obligations come into force on **August 2, 2026** — less than four months away. This date affects any organization deploying foundation models (ChatGPT Enterprise, Microsoft Copilot, Claude API integrations) without a provider-level exemption.

Most internal audit departments have not yet inventoried which AI systems in their organization fall under EU AI Act obligations, what tier (prohibited, high-risk, limited-risk, minimal-risk) each system falls under, or what ongoing compliance monitoring is required.

**Gap vs. existing SAAF plans:** `frank-van-dissel-uc5-regulatory-criteria.md` covers regulatory criteria retrieval generally (DORA, GDPR, ISO 27001). `johannesiv-policy-to-controls-extractor.md` covers EU AI Act in the context of policy extraction. No existing plan covers continuous EU AI Act compliance monitoring — tracking which deployed AI systems comply, which have gaps, and what changes in the regulation require organizational action.

---

## 3. Use-Case Type & Scope

**Type:** Agent

**Scope:**
- Maintain an AI system inventory for the organization (manually updated or via MCP integration)
- For each AI system: classify under EU AI Act (prohibited / high-risk / limited-risk / minimal-risk)
- Map each high-risk system to its Article 9 obligations (risk management) and Article 13 (transparency)
- Monitor the EU AI Act portal (artificialintelligenceact.eu) for regulatory updates
- Run ALTAI self-assessment checklist for each high-risk system
- Generate a compliance gap report with priority actions and deadlines
- Track changes over time: which gaps were closed, which are still open

**Out of scope:**
- Legal advice — the agent flags obligations and gaps; legal/compliance team decides
- Full legal text interpretation — uses pre-processed regulation summaries from SAAF RAG corpus

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | AI system classification prompt (per Annex III); ALTAI self-assessment driver; gap analysis prompt; compliance status summary prompt |
| **Tools** | Claude API (Sonnet), SAAF RAG (EU AI Act corpus), `saaf-intelligence-monitor.md` (regulatory updates feed), JSON system inventory |
| **Regulatory** | EU AI Act Art. 5 (prohibited practices), Art. 6+Annex III (high-risk classification), Art. 9 (risk management), Art. 13 (transparency), Art. 14 (human oversight), Art. 55 (GPAI obligations), ALTAI self-assessment checklist (EC) |
| **Outputs** | Compliance status dashboard (JSON), gap report (Markdown), ALTAI self-assessment JSON, remediation action list with deadlines |

---

## 5. Prompts

### Prompt 1 — AI System Classification
```
System: You are an EU AI Act compliance specialist. Your task is to classify an AI system
under the EU AI Act using the official categorization framework.

Classification tiers:
- PROHIBITED: listed in Article 5 (social scoring, real-time biometric surveillance, etc.)
- HIGH-RISK: listed in Annex III (critical infrastructure, employment, education, law enforcement, etc.)
- LIMITED-RISK: AI systems with specific transparency obligations (chatbots, deepfakes)
- MINIMAL-RISK: all other AI systems — no specific obligations

For GPAI models specifically (foundation models, LLMs):
- GPAI with systemic risk: >10^25 FLOPs training compute → Chapter V obligations
- GPAI without systemic risk: Article 53 obligations only (transparency, copyright summary)

User: Classify the following AI system under the EU AI Act:

System name: [NAME]
Description: [DESCRIPTION]
Deployment context: [CONTEXT]
Data processed: [DATA_TYPES]
Autonomous decision capability: [YES/NO + DESCRIPTION]
Output: classification tier, applicable articles, rationale (2-3 sentences)
```

#### Prompt 1.5 - Extended AI System Classification
```
System: You are an EU AI Act compliance specialist (Regulation (EU) 2024/1689) advising
as of April 2026. Classify an AI system by applying the following decision order strictly:

1. Art. 5 — prohibited practices (including the four biometric sub-regimes: 5(1)(f), (g), (h),
   and untargeted scraping 5(1)(e); plus manipulation 5(1)(a)-(b), social scoring 5(1)(c),
   crime prediction 5(1)(d)).
2. Art. 6(1) + Annex I — AI as safety component of a regulated product.
3. Art. 6(2) + Annex III — eight high-risk use areas, then apply the Art. 6(3) carve-out
   (narrow procedural / preparatory / pattern-detection / confirming human work) if it fits,
   noting Art. 49(2) registration still applies.
4. Art. 50 — transparency layer for chatbots, emotion recognition, biometric categorisation,
   synthetic content (50(2)), and deepfakes (50(4)).
5. Chapter V (Arts. 51–55) — GPAI model layer, stacked on top of any system-level tier:
   - Systemic-risk GPAI if training compute ≥10^25 FLOPs or Commission designation.
   - Otherwise Art. 53 baseline (technical documentation Annex XI, copyright policy,
     public training-data summary), with Art. 53(2) open-source partial carve-out that
     does not apply to systemic-risk or copyright/data-summary duties.
6. Check exemptions in Art. 2 before finalising (national security, defence, R&D, Art. 60
   real-world testing, purely personal use).

If any required input below is absent or ambiguous, ask a clarifying question before classifying.

User: Classify the following AI system.

Role of assessed party: [provider / deployer / importer / distributor / authorised rep]
Substantial modification by deployer? [yes/no — if yes, Art. 25(1)(c) may re-classify]
System name: [NAME]
Provider legal entity and EU representative: [ENTITY / Art. 22 rep if non-EU]
Intended purpose (verbatim as declared): [PURPOSE]
Free-text description: [DESCRIPTION]
Lifecycle stage: [development / sandbox (Art. 57) / Art. 60 testing / placed on market / in service]
Placement / use geography: [EU market? deployer in EU? output used in EU?]
Sectoral domain: [map to Annex III area or Annex I product law if any]
Safety-component status: [yes/no — is it a safety component of a product covered by Annex I?]
Biometric functionality: [none / real-time RBI / post RBI / categorisation / emotion recognition /
  verification — with context (workplace, education, public space, law enforcement)]
Decision subjects: [natural persons affected? vulnerable groups per Art. 5(1)(b)?]
Autonomy and human oversight: [describe per Art. 14 — who can override, logging, stop]
Data processed: [input modalities, personal / special-category data, GDPR role]
Training-data provenance: [sources, copyright stance, Art. 53(1)(c)–(d) summary status]
Model facts (if GPAI is involved): [parameters, training compute in FLOPs, modalities,
  release date relative to 2 Aug 2025, licence (open-source?), systemic-risk notification filed?]
Existing compliance evidence: [CE marking, Annex VI or VII conformity route, notified body,
  Art. 49 registration, FRIA per Art. 27, DPIA, ISO/IEC 42001, GPAI Code of Practice]
Interacting regimes: [GDPR, MDR/IVDR, Machinery Reg, Product Liability Dir 2024/2853, DSA,
  sectoral financial regulation, etc.]

Output — structured:
1. Tier(s): Art. 5 / Annex I high-risk / Annex III high-risk (+ Art. 6(3) carve-out y/n) /
   Art. 50 layer / GPAI layer / minimal. More than one may apply.
2. Applicable articles — cite article + paragraph + quoted trigger text.
3. Provider obligations triggered.
4. Deployer obligations triggered (incl. Art. 26(11) information to affected persons, Art. 27 FRIA).
5. Registration route (Art. 49, 49(2), or Annex III §1, 6, 7 restricted section).
6. Conformity-assessment route (Art. 43 + Annex VI or VII).
7. Applicability date(s) under the staged timeline (2 Feb 2025 / 2 Aug 2025 / 2 Aug 2026 /
   2 Aug 2027) noting the Digital Omnibus conditionality on harmonised standards.
8. Interaction with adjacent law (GDPR, MDR/IVDR, DSA, Product Liability Dir 2024).
9. Uncertainty flags and what additional information would resolve them.
10. Rationale: 3–5 sentences tying the inputs to the articles cited.

Disclaimer: this is a structured compliance assessment, not legal advice.
```

### Prompt 2 — ALTAI Self-Assessment Driver
```
System: You are conducting an ALTAI (Assessment List for Trustworthy AI) self-assessment
for a high-risk AI system. ALTAI is the European Commission's self-assessment tool
for trustworthy AI based on 7 requirements:

1. Human agency and oversight
2. Technical robustness and safety
3. Privacy and data governance
4. Transparency
5. Diversity, non-discrimination and fairness
6. Societal and environmental wellbeing
7. Accountability

For each requirement: ask the relevant sub-questions, evaluate evidence provided, 
rate: Fully met / Partially met / Not met / Not applicable.

User: Run an ALTAI self-assessment for:

System: [SYSTEM_DESCRIPTION]
Available documentation: [DOCS_LIST]
Known gaps: [GAPS]

Generate a structured assessment with ratings and gap explanations per requirement.
```

### Prompt 3 — Regulatory Update Monitor
```
System: You are monitoring the EU AI Act implementation status for new developments
that affect an organization's compliance obligations.

Monitor for:
- New implementing acts or delegated acts (specify dates and scope)
- New high-risk system classifications added to Annex III
- Guidance documents from the AI Office or national supervisory authorities
- Deadline changes or grace period extensions
- Enforcement actions (cases, fines, orders)

User: Analyze the following regulatory updates and determine their impact on
an organization's compliance status:

[REGULATORY_UPDATE_TEXT]

Impact assessment per update:
- What changed?
- Which systems are now affected?  
- What new action is required?
- By when?
```

### Prompt 4 — Gap Report Synthesis
```
System: You are synthesizing an EU AI Act compliance gap report for internal audit.

For each system in the inventory:
- Current classification
- Compliance status per applicable article
- Open gaps (specific obligation not yet met)
- Priority: Critical (before August 2, 2026) / High (before December 2026) / Medium (2027)
- Responsible owner

User: Generate a gap report from the following compliance assessment data:

[ASSESSMENT_DATA_JSON]

Output: executive summary (3 bullets) + per-system gap table + overall readiness score (%)
```

---

## 6. Tools & Techniques

| Tool | Role |
|---|---|
| Claude API (Sonnet) | Classification, ALTAI assessment, gap analysis |
| SAAF RAG knowledge base | EU AI Act full text + ALTAI checklist corpus |
| `saaf-intelligence-monitor.md` | Regulatory update feed (artificialintelligenceact.eu source) |
| JSON system inventory | AI systems register maintained by compliance/audit team |
| Python `json` + `pathlib` | Inventory management, report generation |

**Integration point with intelligence monitor:** The `saaf-intelligence-monitor.md` agent should be configured to scrape artificialintelligenceact.eu and flag EU AI Act updates. Those updates feed into this agent's monitoring function automatically.

---

## 7. Regulatory Framework

| Article | Obligation |
|---|---|
| **Art. 5** | Prohibited AI practices — verify no deployed system falls under this category |
| **Art. 6 + Annex III** | High-risk AI system classification — classify all deployed AI systems |
| **Art. 9** | Risk management system — document risk management for each high-risk system |
| **Art. 13** | Transparency — ensure users know they are interacting with AI |
| **Art. 14** | Human oversight — mechanisms for human review of high-risk AI outputs |
| **Art. 55** | GPAI obligations — providers of GPAI models (e.g., internal LLM deployments) must document model capabilities and limitations |
| **Art. 72** | Post-market monitoring — ongoing monitoring of high-risk AI systems in use |

**Key deadline: August 2, 2026** — GPAI provisions (Chapter V, Art. 51-56) become enforceable. Organizations using GPT Enterprise, Microsoft Copilot, Claude API, or similar foundation models must be able to demonstrate compliance with applicable GPAI obligations.

---

## 8. Output Format

### AI System Inventory (JSON)
```json
{
  "inventory_date": "2026-04-21",
  "organization": "[ORG]",
  "systems": [
    {
      "id": "AI-001",
      "name": "Claude API — Fraud Risk Agent",
      "provider": "Anthropic",
      "classification": "LIMITED-RISK",
      "applicable_articles": ["Art. 13", "Art. 52"],
      "compliance_status": {
        "Art. 13": "COMPLIANT",
        "Art. 52": "GAP"
      },
      "gaps": ["Transparency notice not displayed to end users"],
      "priority": "High",
      "owner": "Head of Internal Audit"
    }
  ]
}
```

### Compliance Gap Report (Markdown)
```markdown
# EU AI Act Compliance Gap Report — [ORG] — April 2026

## Executive Summary
- 12 AI systems inventoried; 3 classified as Limited-Risk, 1 High-Risk, 8 Minimal-Risk
- 4 open gaps identified; 1 Critical (before August 2, 2026)
- Overall readiness score: 67%

## Critical Gap (before August 2, 2026)
**System:** Microsoft Copilot (GPAI)
**Gap:** No GPAI compliance documentation from provider; no organizational GPAI inventory filed
**Action:** Request GPAI compliance documentation from Microsoft; add system to AI register
**Owner:** IT Director
**Deadline:** August 1, 2026

## Gap Table
| System | Classification | Article | Gap | Priority | Owner | Deadline |
|...

## ALTAI Self-Assessment Summary
| System | Human Oversight | Technical Robustness | Privacy | Transparency | Overall |
|...
```

---

## 9. Tech Stack

```
Language:     Python 3.9+
Dependencies: anthropic (Claude API), chromadb (EU AI Act corpus)
Config:       ANTHROPIC_API_KEY from environment
Input:        AI system inventory JSON (maintained by audit/compliance team)
Output:       Gap report Markdown + compliance status JSON + ALTAI assessment JSON
Scheduling:   Monthly via cron or GitHub Actions; triggered on regulatory updates
```

---

## 10. Collaboration & Cross-References

**Dependencies:**
- `saaf-rag-knowledge-base.md` — EU AI Act full text must be in the corpus
- `saaf-intelligence-monitor.md` — feeds regulatory updates from artificialintelligenceact.eu
- `frank-van-dissel-uc5-regulatory-criteria.md` — retrieves specific article text on demand

**Complementary plans:**
- `johannesiv-policy-to-controls-extractor.md` — extracts controls from policies including EU AI Act; can feed the ALTAI assessment
- `robeminem94-gdpr-ai-audit-agent.md` — GDPR compliance is a prerequisite for EU AI Act compliance (both regulate AI data processing)
- `ai-audit-explainability-framework.md` — Art. 13 (transparency) and Art. 14 (human oversight) requirements are directly operationalized there

**WhatsApp source attribution:**
> This plan originated from sustained discussion in **"AI Innovators: Hub • General"** (April 2026) about the August 2, 2026 GPAI compliance deadline. Patrick Chu (NOREA, IT audit + risk, M365 Copilot) and Rohan Sobha (ADR, IT auditor) both flagged this deadline as the most urgent regulatory moment for Dutch internal audit departments. The EU AI Act portal (artificialintelligenceact.eu) and ALTAI self-assessment tool were shared as resources. The **"AI in Internal Audit"** WhatsApp group (Imran Nashir) independently signals IIA demand for EU AI Act training, confirming urgency in the broader audit community.

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | Pending | Build at Hackathon #3 |
| **Check** | Not started | Run classification on 5 SAAF agents; validate classification vs. vaktechniek review |
| **Act** | Not started | Update classification prompts as new Annex III systems are added; update deadlines annually |

**Hackathon #3 task (Vaktechniek role):**
Use the classification prompt to classify 5 SAAF agents (choose from: fraud risk, GDPR audit, CLI wrapper, always-on agent, batch processor). Validate each classification against your own EU AI Act knowledge. For any discrepancy, note which article was misapplied.

---

## 12. Open Questions

1. **GPAI scope**: Does deploying Claude API (not building a foundation model) trigger GPAI obligations? The consensus in the SAAF community is: the API provider (Anthropic) holds GPAI obligations; the deployer (the audit department) holds high-risk deployment obligations if Annex III applies. Legal confirmation needed.
2. **Supervisory authority**: The EU AI Act enforcement in NL falls under the RDI (Rijksdienst voor Digitale Infrastructuur). Should this agent also track RDI guidance publications as a regulatory feed?
3. **AI register requirement**: Some interpretations of Art. 71 require organizations to maintain a public AI system register. Should this agent also generate the public-facing register format?
4. **Continuous vs. point-in-time**: Should this agent run continuously (triggered by regulatory updates) or quarterly as a point-in-time compliance check?
