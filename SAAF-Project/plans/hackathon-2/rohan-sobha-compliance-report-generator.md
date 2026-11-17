# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Rohan Sobha) |
| **Organisation** | Auditdienst Rijk (Ministerie van Financiën) |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Finalised |
| **Repository** | https://github.com/SAAF-Project/Compliance-Report-Generator |

---

## 2. Problem Statement

Auditors working across different financial entities (banks, insurers, payment institutions, government bodies) spend significant time identifying which regulatory frameworks apply to a given entity. This mapping is error-prone when done manually and needs to be repeated for every new engagement. The Compliance Report Generator automates this lookup: given a description of a financial entity, it determines which regulatory frameworks are relevant and produces a structured overview.

---

## 3. Use-Case Type and Scope

**Audit domain:** Compliance Monitoring / Regulatory Framework Selection

**Applicable standards:**

- ISO 27001
- DORA
- NIS2
- TBD — additional frameworks identified dynamically per entity type

**In scope:**

- Identifying applicable regulatory frameworks for a given financial entity
- Producing a structured report of relevant frameworks

**Out of scope:**

- Performing the actual compliance assessment against those frameworks
- Ingesting entity documents for evidence review

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | TBD — system prompt for framework identification logic |
| **Tools** | Python script in `tools/scripts/` (see [Compliance-Report-Generator repo](https://github.com/SAAF-Project/Compliance-Report-Generator)) |
| **Regulatory** | Reuse or extend `regulatory/control-mappings/` — framework applicability rules per entity type |
| **Outputs** | TBD — structured list of applicable frameworks per entity |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI compliance specialist for the financial sector.
Given a description of a financial entity (sector, services, size, jurisdiction),
identify all regulatory frameworks that apply to this entity.
For each framework, explain briefly why it applies.
Only include frameworks that are demonstrably applicable — do not speculate.
Never include credentials, personal data, or real entity names in your output.
```

### Example user prompts

**Prompt 1:**
```
Entity: A Dutch bank offering retail and business current accounts and payment services.
Jurisdiction: Netherlands (EU).
What regulatory frameworks apply to this entity?
```

**Prompt 2:**
```
Entity: A mid-sized insurance company active in life and non-life insurance, operating in the Netherlands.
Jurisdiction: Netherlands (EU).
Which compliance and security frameworks are relevant?
```

**Intended file location:** `prompts/audit-use-cases/compliance-report-generator.md`

---

## 6. Tools and Techniques

### Approach

The tool takes a description of a financial entity as input (sector, services, jurisdiction), passes it to a Claude model, and returns a structured list of applicable regulatory frameworks with a short rationale for each. The output is designed to be the starting point for a broader audit engagement.

### Example script or pseudocode

```python
# Pseudocode — actual implementation in Compliance-Report-Generator repo
import anthropic

def identify_frameworks(entity_description: str) -> list[dict]:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": entity_description}]
    )
    # Parse structured output into framework list
    return parse_frameworks(response.content[0].text)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6)

**Intended file location:** `tools/scripts/compliance-report-generator.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO 27001 | A.18 — Compliance |
| DORA | All — Digital Operational Resilience Act applicability for financial entities |
| NIS2 | Scope determination for operators of essential services |
| TBD | Additional frameworks per entity type |

### Claude / AI tool usage notes

No real entity data or personal data sent to the API. Input should be synthetic or anonymized descriptions only during testing.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown / JSON

**Schema reference:** TBD — findings not yet mapped to `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "entity": "Dutch retail bank",
  "jurisdiction": "Netherlands (EU)",
  "applicable_frameworks": [
    {
      "framework": "DORA",
      "rationale": "Applies to credit institutions as defined in Article 2(2)(a) of DORA."
    },
    {
      "framework": "NIS2",
      "rationale": "Banks qualify as operators of essential services under Annex I."
    },
    {
      "framework": "ISO 27001",
      "rationale": "Required by DNB supervisory guidance for information security management."
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

**Stretch goals:**

- [ ] Web interface for non-technical users
- [ ] Export to PDF or Word report

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The system prompt and framework applicability logic
- The Python script

**What help I'm looking for:**

- Review of framework applicability rules from organizations active in other EU jurisdictions
- Input on additional frameworks to cover (e.g. sector-specific DNB/AFM requirements)

**Cross-org interest:**

Framework identification is a common starting point for any audit engagement. Multiple organizations likely face the same question: "which rules apply here?" This skill is a strong candidate for shared adoption across the 45+ SAAF organizations.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Prototype built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned for internal adoption at Auditdienst Rijk |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. Which specific frameworks does the current implementation cover, and how are applicability rules encoded?
2. How does the tool handle entities that fall on the boundary of framework scope (e.g. a fintech that may or may not qualify as a credit institution under DORA)?
3. Is there interest from other organizations in a shared, maintained framework-applicability knowledge base?
