# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of KOEKENPAN) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | ESG Risk Management Audit |
| **Status** | Draft |

---

## 2. Problem Statement

ESG risk management has become a core supervisory expectation for financial institutions, driven by ECB, EBA, and DNB regulatory frameworks. Internal auditors must assess whether their organisation has adequately identified, measured, monitored, and reported ESG risks — including climate-related transition and physical risks, social risks, and governance failures. Translating supervisory expectations into concrete audit test procedures, interview questions, and document request lists is complex, inconsistent, and time-intensive. The IA-Fieldwork-Preparation agent for ESG aims to automate or substantially support this step, helping auditors produce structured ESG audit fieldwork plans that are aligned with current prudential supervisory expectations.

---

## 3. Use-Case Type and Scope

**Audit domain:** ESG Risk Management (Financial Institutions)

**Applicable standards:**

- **ECB** — ECB Guide on climate-related and environmental risks (2020); ECB supervisory expectations on climate and environmental risk management
- **EBA** — EBA Guidelines on management of ESG risks (EBA/GL/2024); EBA Pillar 3 ESG disclosures (EBA/GL/2022/03); EBA Guidelines on loan origination and monitoring (ESG integration)
- **DNB** — DNB Good Practice Climate-related Risk Management; DNB supervisory expectations on sustainable finance and ESG governance
- **IIA IPPF** — Standard 2200 (Engagement Planning), Standard 2300 (Performing the Engagement)
- **CSRD / ESRS** — as reference for ESG disclosure requirements that the institution must be audited against

**In scope:**

- Generating fieldwork artefacts (test procedures, interview questions, PBC lists) for ESG risk management audits
- Mapping ECB/EBA/DNB supervisory expectations to auditable controls
- Supporting double materiality assessments and ESG data quality reviews

**Out of scope:**

- Actual ESG data collection or processing of real environmental/personal data
- Investment advice or portfolio-level ESG scoring

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | System prompt for ESG fieldwork preparation — see Section 5; intended location: `prompts/audit-use-cases/ia-fieldwork-preparation-esg.md` |
| **Tools** | Python script in `tools/scripts/` calling Claude API; see [IA-Fieldwork-Preparation repo](https://github.com/SAAF-Project/IA-Fieldwork-Preparation) for workflow diagram |
| **Regulatory** | ECB Guide, EBA/GL/2024, DNB Good Practice — reuse control mappings from `regulatory/control-mappings/` where available |
| **Outputs** | Markdown fieldwork plan + PBC list + JSON findings conforming to SAAF finding schema |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI assistant specialised in internal audit fieldwork preparation for ESG risk management
at financial institutions. Given an audit scope or risk assessment, help auditors produce structured
fieldwork artefacts: test procedures, interview questions, and document request lists.
Base your output on ECB, EBA, and DNB supervisory expectations for ESG risk management —
do not invent audit objectives not mentioned in the scope.
Map findings to the relevant regulatory expectation (e.g. ECB Guide chapter, EBA guideline paragraph,
or DNB Good Practice element) where applicable.
Never request or process real personal data, confidential client data, or actual audit evidence.
```

### Example user prompts

**Prompt 1:**
```
Audit scope: Climate-related risk integration in the credit risk framework of a Dutch bank.
Applicable standards: ECB Guide on climate-related and environmental risks (expectations 7–9),
EBA Guidelines on loan origination (ESG section).
Generate a fieldwork plan with test procedures and key interview questions.
```

**Prompt 2:**
```
Audit area: ESG governance and risk appetite framework.
Standards: EBA Guidelines on management of ESG risks (EBA/GL/2024), DNB supervisory expectations
on ESG governance.
Produce a document request list and fieldwork checklist for this audit area.
```

**Intended file location:** `prompts/audit-use-cases/ia-fieldwork-preparation.md`

---

## 6. Tools and Techniques

### Approach

The agent takes a free-text audit scope and a list of applicable ECB/EBA/DNB standards as input. It calls Claude API with the ESG fieldwork preparation system prompt and returns three structured outputs: a Markdown fieldwork plan, a PBC list, and JSON findings. The workflow diagram in the [IA-Fieldwork-Preparation repo](https://github.com/SAAF-Project/IA-Fieldwork-Preparation) illustrates the intended agent architecture.

### Example script or pseudocode

```python
import anthropic
from pathlib import Path
from typing import Optional

def prepare_esg_fieldwork(
    audit_scope: str,
    standards: list[str],
    output_dir: Optional[Path] = None,
) -> dict:
    client = anthropic.Anthropic()
    system_prompt = Path("prompts/audit-use-cases/ia-fieldwork-preparation-esg.md").read_text()
    user_prompt = f"Audit scope: {audit_scope}\nApplicable standards: {', '.join(standards)}\n"
    user_prompt += "Generate: (1) fieldwork plan, (2) PBC list, (3) findings in SAAF JSON schema."

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    # Parse and write Markdown + JSON outputs to output_dir
    return {"content": response.content[0].text}
```

**Tech stack used:** Python 3.9+, Anthropic SDK, Claude API (claude-sonnet-4-6)

**Intended file location:** `tools/scripts/prepare_esg_fieldwork.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ECB Guide on climate-related and environmental risks (2020) | Expectations 1–13: governance, risk appetite, credit risk, operational risk, stress testing, disclosure |
| EBA Guidelines on management of ESG risks (EBA/GL/2024) | ESG risk identification, measurement, integration into ICAAP/ILAAP, transition plans |
| EBA Pillar 3 ESG disclosures (EBA/GL/2022/03) | Quantitative and qualitative ESG disclosure requirements |
| EBA Guidelines on loan origination and monitoring | ESG integration in credit underwriting and monitoring |
| DNB Good Practice — Climate-related Risk Management | DNB supervisory expectations on governance, strategy, risk management, and disclosure |
| DNB supervisory expectations on sustainable finance | Integration of ESG risks in business strategy and risk frameworks |
| IIA IPPF Standard 2200 | Engagement Planning |
| IIA IPPF Standard 2300 | Performing the Engagement |
| CSRD / ESRS | Reference for ESG disclosure obligations relevant to auditee |

### Claude / AI tool usage notes

The agent processes only synthetic or anonymised audit scope descriptions. No real audit evidence, client data, or personal data should be passed to the Claude API. ECB/EBA/DNB regulatory texts are public documents and may be referenced freely. All API keys must be loaded from environment variables.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Two complementary outputs per audit engagement:

1. **Fieldwork plan (Markdown)** — human-readable document containing test procedures, interview questions, and audit objectives mapped to ECB/EBA/DNB expectations. Suitable for direct use by auditors and exportable to Word/PDF.
2. **PBC list (Markdown table)** — document request list structured per supervisory expectation (e.g. ECB Guide expectation 7, EBA/GL/2024 section 4.3).
3. **Findings (JSON)** — structured output conforming to the SAAF finding schema (`outputs/schemas/finding-schema.json`), enabling findings to be reused and shared across SAAF organisations.

**Schema reference:** `outputs/schemas/finding-schema.json` — required fields: `id` (pattern `F-\d{2,4}`), `title`, `risk_rating` (High/Medium/Low/Informational), `observation`, `recommendation`.

### Synthetic example output

```markdown
## Fieldwork Plan — ESG Risk Management Audit
### Audit area: Climate risk integration in credit risk framework
**Applicable standard:** ECB Guide expectation 7 — Credit risk

#### Test procedures
1. Inspect the credit risk policy to verify ESG/climate risk criteria are included in underwriting standards.
2. Select a sample of 25 corporate loan files and verify whether climate risk was assessed at origination.
3. Review minutes of the Credit Committee for evidence that ESG risk is discussed in credit approval decisions.

#### Interview questions
- How does the credit risk team identify and assess transition risk for high-emission sectors?
- What thresholds trigger an ESG risk flag during loan origination?

#### Document request list (PBC)
| # | Document | Owner | Standard reference |
|---|---|---|---|
| 1 | Credit risk policy (current version) | CRO | ECB Guide exp. 7 |
| 2 | Sample of 25 corporate loan files (past 12 months) | Credit Risk | EBA loan origination guidelines |
| 3 | Credit Committee minutes (past 2 quarters) | Secretariat | ECB Guide exp. 5 |
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6) — core model for fieldwork plan generation
- [x] Python script in `tools/scripts/` — assembles the prompt from audit scope input, calls Claude API, writes output files
- [x] Output: Markdown fieldwork plan + PBC list + JSON findings per SAAF finding schema

**Stretch goals:**

- [ ] GRC system integration (e.g. export to TeamMate, AuditBoard)
- [ ] Dynamic regulatory mapping — agent selects relevant ECB/EBA/DNB paragraphs based on institution type (bank, insurer, asset manager)
- [ ] CSRD/ESRS double materiality scoping module

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- ESG fieldwork preparation system prompt (`prompts/audit-use-cases/ia-fieldwork-preparation-esg.md`)
- Python script (`tools/scripts/prepare_esg_fieldwork.py`)
- Synthetic example outputs (fieldwork plan, PBC list, JSON findings)
- Regulatory mapping for ECB/EBA/DNB ESG expectations in `regulatory/control-mappings/`

**What help I'm looking for:**

- Reviewers with ECB/EBA/DNB ESG supervisory experience to validate the regulatory mappings
- Organisations willing to test the agent against their own (anonymised) audit scopes
- Input on which ESRS topics are most relevant to include for CSRD-scoped institutions

**Cross-org interest:**

Fieldwork preparation is a universal challenge across internal audit functions. A reusable skill or agent for this step would be directly applicable to many of the 45+ SAAF organizations, regardless of audit domain.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Prototype demonstrated at Hackathon 1 (March 10, 2026) — see workflow diagram in repo |
| **Check** | Not started | Validate agent output against real audit scopes with ESG supervisory experts; target Hackathon 3 |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the exact input format — free-text audit scope, structured ESG risk assessment, or a filled-in audit universe?
2. What artefacts does the tool produce — test procedures, interview questions, PBC items, or a combination?
3. Which ECB/EBA/DNB expectations are prioritised for the first MVP — governance, credit risk integration, or disclosure?
4. How does the agent handle the difference between transition risk and physical risk in the fieldwork output?
5. Should the agent support double materiality scoping (CSRD) in addition to prudential supervisory expectations?
6. Which institution types are in scope — banks only, or also insurers (Solvency II ESG) and asset managers (SFDR)?
