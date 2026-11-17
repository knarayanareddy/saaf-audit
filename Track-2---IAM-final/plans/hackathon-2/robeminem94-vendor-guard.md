# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of robeminem94) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Auditing third-party vendors against multiple regulatory frameworks is a time-intensive, specialist task. Auditors must manually cross-reference vendor questionnaires and supporting documents (SOC 2 reports, ISO certificates, DORA self-assessments) against eight distinct EU and Dutch frameworks. This is error-prone, inconsistent across engagements, and does not scale when an organization manages dozens of vendor relationships. Vendor_Guard automates this entire process: it ingests vendor documents, determines which frameworks apply, runs framework-specific assessments in parallel, and produces a risk scorecard, gap register, and audit memo ready for management — in seconds.

---

## 3. Use-Case Type and Scope

**Audit domain:** Third-Party Risk Management / Vendor Risk

**Applicable standards:**

- ISO 27001 (A.15 — Supplier relationships)
- NIS2 / CBW (Cyberbeveiligingswet — Dutch NIS2 implementation)
- DORA (Digital Operational Resilience Act)
- BIO2 (Baseline Informatiebeveiliging Overheid — Dutch government only)
- EU AI Act / ALTAI / EC Ethical Guidelines (AI vendors only)

**In scope:**

- Ingesting vendor documents (PDF, DOCX, XLSX, TXT)
- Vendor profiling: sector, services, AI system flag, Dutch government flag
- Parallel framework assessment by specialist agents
- Producing Risk Scorecard (RAG), Gap Register, and Audit Memo
- Output in both Google Workspace (CSV, HTML) and Microsoft Office (XLSX, DOCX) formats

**Out of scope:**

- Continuous vendor monitoring (one-shot assessment only)
- Automated vendor questionnaire distribution
- Integration with GRC platforms

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | System prompts per specialist agent embedded in `prompts/` within the repo: `iso27001_controls.md`, `nis2_measures.md`, `cbw_requirements.md`, `dora_requirements.md`, `bio2_controls.md`, `ai_act_requirements.md`, `altai_requirements.md`, `ec_ethics_guidelines.md` |
| **Tools** | Full Python agent suite in the [Vendor_Guard repo](https://github.com/SAAF-Project/Vendor_Guard): `main.py`, `agents/`, `synthesizer/`, `utils/document_parser.py` |
| **Regulatory** | Framework knowledge embedded in prompt files; reusable from `regulatory/control-mappings/` in the SAAF-Project repo |
| **Outputs** | Scorecard (RAG per framework), Gap Register (control ID, status, severity, evidence, recommendation), Audit Memo — conforming to `outputs/schemas/finding-schema.json` structure |

---

## 5. Prompts

### System prompt (draft — orchestrator)

```
You are a vendor risk orchestrator. Given vendor documents, extract a structured
vendor profile: name, sector, primary services, whether the vendor is an AI system,
and whether they serve Dutch government entities.
Return a JSON object with these fields.
Only extract facts explicitly stated in the documents — do not infer or speculate.
Never include real personal data or credentials in your output.
```

### Example user prompts

**Prompt 1 — vendor profiling:**
```
Here are the vendor documents for CloudSafe Solutions B.V.:
[vendor questionnaire] [SOC 2 report] [ISO certificate] [DORA self-assessment]

Extract the vendor profile: sector, services, AI system (yes/no), Dutch government client (yes/no).
```

**Prompt 2 — specialist agent (ISO 27001):**
```
You are an ISO 27001 specialist auditor. Assess the following vendor documents
against the ISO 27001:2022 Annex A controls. For each relevant control, determine:
status (Compliant / Gap / Partial / Not Applicable), severity, evidence quote,
and recommendation. Return a JSON array of findings.
[vendor document content]
```

**Intended file location:** `prompts/audit-use-cases/vendor-guard-orchestrator.md`, `prompts/audit-use-cases/vendor-guard-iso27001.md` etc.

---

## 6. Tools and Techniques

### Approach

The agent uses a multi-agent pipeline:

1. **Document ingestion** — reads PDF, DOCX, XLSX, TXT files and combines content with filename labels
2. **Vendor profiling** — Claude Opus orchestrator extracts vendor profile and determines which specialist agents to invoke
3. **Parallel assessment** — specialist agents (Security, Resilience, AI Trust, Gov Baseline) run concurrently, each with the full framework text embedded in the system prompt
4. **Findings normalization** — output variations are mapped to canonical statuses (Compliant/Gap/Partial/N-A) and severities (Critical/High/Medium/Low/Info)
5. **Synthesis** — RAG scorecard computed (Red = any Critical/High gap; Amber = Medium/Low or Partial; Green = fully compliant)
6. **Report generation** — Claude Opus drafts the audit memo; outputs written to both Excel/Word and CSV/HTML

### Example script or pseudocode

```python
# Simplified pipeline — see main.py in Vendor_Guard repo
from agents.orchestrator import run_orchestrator
from agents.security_agent import run_security_agent
from agents.resilience_agent import run_resilience_agent
from synthesizer.synthesizer import synthesize

vendor_docs = load_documents(args.questionnaire, args.docs)
profile = run_orchestrator(vendor_docs)

findings = []
findings += run_security_agent(vendor_docs)          # ISO 27001, NIS2, CBW
findings += run_resilience_agent(vendor_docs)        # DORA
if profile.is_ai_system:
    findings += run_ai_trust_agent(vendor_docs)      # EU AI Act, ALTAI, EC Ethics
if profile.dutch_government_client:
    findings += run_gov_baseline_agent(vendor_docs)  # BIO2

scorecard, gap_register = synthesize(findings, profile)
write_outputs(scorecard, gap_register, memo)
```

**Tech stack used:** Python 3.11+, Claude API (claude-opus-4-6 for orchestration/memo, claude-sonnet-4-6 for specialist agents), `pdfplumber`, `python-docx`, `openpyxl`

**Intended file location:** `tools/scripts/vendor-guard/` (or reference [Vendor_Guard repo](https://github.com/SAAF-Project/Vendor_Guard))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO 27001:2022 | A.15 — Supplier relationships; A.5, A.8, A.9 (always) |
| NIS2 / CBW | Art. 21 — Security measures; Art. 23 — Incident reporting |
| DORA | Art. 28-30 — ICT third-party risk; Art. 17-23 — ICT incident management |
| BIO2 | Full baseline (Dutch government vendors only) |
| EU AI Act | Art. 9-15 — High-risk AI system requirements (AI vendors only) |
| ALTAI / EC Ethics | Trustworthiness criteria (AI vendors only) |

### Claude / AI tool usage notes

All testing uses synthetic vendor documents (included in repo). No real vendor data, personal data, or credentials are sent to the API. The repo includes `.env.example` — API key is never hardcoded.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (gap register), XLSX/CSV (scorecard + gap register), DOCX/HTML (audit memo)

**Schema reference:** `outputs/schemas/finding-schema.json` — gap register fields (id, title, risk_rating, observation, recommendation) map directly to the SAAF finding schema

### Synthetic example output

```json
{
  "id": "F-001",
  "title": "DORA ICT incident classification procedure not documented",
  "risk_rating": "High",
  "observation": "The vendor's DORA self-assessment does not reference a formal ICT incident classification procedure as required by Art. 17 DORA. The SOC 2 report covers incident response at a high level but does not address DORA-specific classification criteria.",
  "recommendation": "Request the vendor to provide a documented ICT incident classification procedure aligned with DORA Art. 17, including severity tiers and escalation thresholds, within 30 days."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6, claude-sonnet-4-6)
- [x] Python 3.11+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional)

**Stretch goals:**

- [ ] Web UI for document upload (beyond current Streamlit prototype)
- [ ] GRC platform integration (ServiceNow, Archer)
- [ ] Continuous monitoring mode with scheduled re-assessment

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- All 8 framework prompt files (ISO 27001, NIS2, CBW, DORA, BIO2, EU AI Act, ALTAI, EC Ethics)
- Full Python pipeline including document parser, specialist agents, synthesizer, and output generators
- 34-test suite (mocked API calls — no key needed to run)
- Sample vendor documents (synthetic CloudSafe Solutions B.V.)

**What help I'm looking for:**

- Review of DORA and BIO2 control coverage from organizations active in those areas
- Input from Dutch government auditors on BIO2 applicability rules
- Extension: additional frameworks (PCI DSS, SOC 2 Type II mapping)

**Cross-org interest:**

Third-party risk is a universal audit domain. This agent is immediately reusable by any of the 45+ SAAF organizations that audit vendors. The framework prompt files can be extended independently per organization.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Full prototype with 34 tests built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned for internal vendor audit adoption |
| **Act** | Not started | Target: Hackathon 3 — share learnings and extend framework coverage |

---

## 12. Open Questions

1. Should BIO2 applicability be determined by vendor self-report or by the auditor's knowledge of the vendor's client base?
2. How should the agent handle vendors with certifications that partially satisfy a framework (e.g. ISO 27001 certificate but scoped to only part of the relevant services)?
3. Is there interest in a shared, maintained library of framework prompt files that all SAAF organizations can contribute to and pull from?
