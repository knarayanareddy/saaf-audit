# IIA Prompt Library — Reference

> **Source:** IIA (Institute of Internal Auditors) — AI in Internal Audit resources  
> **Maintained by:** SAAF Project Organisation  
> **Purpose:** Reference document for the IIA's AI prompting resources and guidance, mentioned in SAAF hackathon presentations.

---

## What is the IIA Prompt Library?

The IIA (Institute of Internal Auditors) has developed an **AI Prompt Library** as part of its broader AI in Internal Audit knowledge center. The library provides practitioners with curated, ready-to-use prompts for common internal audit tasks — structured to work with general-purpose AI assistants (ChatGPT, Copilot, Claude) without requiring technical knowledge.

The prompt library is part of a wider IIA initiative on AI literacy for internal auditors, consistent with:

- **IIA Standard 1200 — Proficiency**: Auditors must demonstrate competency when using AI tools
- **EU AI Act Article 4 — AI Literacy**: Organizations must ensure staff understand AI capabilities and limitations
- **IIA IPPF**: AI as a tool to support, not replace, professional judgment

---

## How to Access

The IIA AI prompting resources are available through:

- **IIA Knowledge Center — Artificial Intelligence:** `https://www.theiia.org/en/resources/knowledge-centers/artificial-intelligence/`
- **Podcast "From Prompts to Practice":** `https://www.theiia.org/en/content/podcast/all-things-internal-audit/2025/ep-0073/` — Covers AI-driven innovation in internal audit (2025 episode)
- **IIA Global AI resources page:** `https://www.theiia.org/en/topics/artificial-intelligence/`

> **Note:** Access to the full prompt library may require an IIA membership login. Check with your organization's IIA membership contact.

---

## Prompt Categories in the IIA Library

Based on IIA publications and the SAAF hackathon slide reference, the IIA Prompt Library covers prompts for the following audit lifecycle phases:

### Planning & Risk Assessment

- Prompts for drafting risk-based audit plans from organizational context
- Prompts for summarizing regulatory changes and mapping to audit universe
- Prompts for identifying high-risk audit areas from prior findings

### Fieldwork & Evidence

- Prompts for structuring interview questions for audit walkthroughs
- Prompts for analyzing data exports (CSV/Excel) for exceptions and anomalies
- Prompts for drafting evidence request letters (PBC lists)

### Findings & Reporting

- Prompts for drafting findings in **Condition / Criterion / Cause / Effect** structure
- Prompts for rating risk (High / Medium / Low / Informational) based on finding descriptions
- Prompts for converting technical findings into executive-language summaries

### Quality Assurance

- Prompts for reviewing draft audit reports for completeness and IIA standard compliance
- Prompts for checking that findings cite applicable standards

---

## SAAF Context

The IIA Prompt Library is referenced in the SAAF hackathon presentation slides (Hackathon #1 and #2 briefings by Mathijs Schouten and Eduward van de Kamp). The lesson learned from SAAF Hackathon #1 states:

> **"The IIA has a Prompt Library"** — Teams that were unaware of existing IIA resources re-invented prompts from scratch. The IIA library provides a validated starting point that teams can extend with SAAF-specific context.

### Relationship to SAAF Prompts

SAAF prompts in `prompts/audit-use-cases/` are **extensions** of the IIA base prompts, adding:

- SAAF-specific output format (structured JSON / `finding-schema.json`)
- Regulatory citations specific to the audit domain (DORA, GDPR, ISO 27001, EU AI Act)
- Integration context (Jira data, Strapi synthetic data, RAG knowledge base)
- Dutch-language variants where needed

The IIA prompts should be the **starting point**; SAAF prompts should be the **production-ready extension**.

---

## Dutch-Language Resources

For Dutch-speaking auditors, the following resources are available:

- **IIA Nederland:** `https://www.iia.nl/` — Dutch chapter of the IIA; publishes guidance on AI in de auditpraktijk
- **`plans/hackathon-3/audit-automation-overview-nl.md`** — SAAF's Dutch-language overview of AI use cases in the audit lifecycle, including Dutch example prompts
- **NOREA** (Dutch IT-auditors association): `https://www.norea.nl/` — publishes guidance on AI auditing from an IT audit perspective

---

## Recommended Reading

| Resource | Type | URL |
|---|---|---|
| IIA AI Knowledge Center | Web portal | `https://www.theiia.org/en/resources/knowledge-centers/artificial-intelligence/` |
| From Prompts to Practice (podcast) | Podcast episode | `https://www.theiia.org/en/content/podcast/all-things-internal-audit/2025/ep-0073/` |
| IIA Global Technology Audit Guide (GTAG): Artificial Intelligence | Guidance document | Available via IIA membership |
| ISACA AI Audit Toolkit | Toolkit | `https://www.isaca.org/resources/isaca-journal/issues/2024/volume-1/ai-auditing` |
| NIST AI RMF (AI Risk Management Framework) | Framework | `https://www.nist.gov/system/files/documents/2023/01/26/AI%20RMF%201.0.pdf` |

---

## Notes

- The IIA prompt library URL was not publicly visible at time of writing — access via IIA member portal
- If the library URL changes, update this document and the cross-reference in `plans/hackathon-3/audit-automation-overview-nl.md` (Section 9, Lesson 4)
- SAAF participants should check the IIA library before building new prompts for standard audit tasks — avoid duplicating work the IIA has already done
