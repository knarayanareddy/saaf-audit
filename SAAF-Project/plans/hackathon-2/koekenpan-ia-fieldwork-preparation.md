# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of KOEKENPAN) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | TBD |
| **Status** | Draft |

---

## 2. Problem Statement

Preparing for internal audit fieldwork is one of the most time-intensive steps in an engagement. Auditors must translate a risk assessment or audit scope into concrete test procedures, interview questions, and document request lists — consistently and in line with applicable standards. This preparation is often done ad hoc and differs significantly across team members. The IA-Fieldwork-Preparation agent aims to automate or substantially support this step, helping auditors produce structured fieldwork plans faster and more consistently.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Fieldwork Preparation

**Applicable standards:**

- TBD — likely IIA IPPF (Standard 2200 — Engagement Planning, Standard 2300 — Performing the Engagement)
- TBD — domain-specific standards per audit area (e.g. ISO 27001, DORA, NIS2)

**In scope:**

- TBD — generating fieldwork artefacts from audit scope or risk input

**Out of scope:**

- TBD

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | TBD — system prompt for fieldwork preparation |
| **Tools** | TBD — see [IA-Fieldwork-Preparation repo](https://github.com/SAAF-Project/IA-Fieldwork-Preparation) (workflow diagram available) |
| **Regulatory** | TBD — reuse relevant control mappings from `regulatory/control-mappings/` |
| **Outputs** | TBD — structured fieldwork plan, checklist, or PBC list |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI assistant specialised in internal audit fieldwork preparation.
Given an audit scope or risk assessment, help auditors produce structured fieldwork
artefacts: test procedures, interview questions, and document request lists.
Base your output on the stated scope and applicable standards — do not invent
audit objectives not mentioned.
Never request or process real personal data or confidential evidence.
```

### Example user prompts

**Prompt 1:**
```
Audit scope: Access management controls at a financial institution.
Applicable standard: ISO 27001 (A.9 — Access Control).
Generate a fieldwork plan with test procedures and key interview questions.
```

**Prompt 2:**
```
Audit area: Change management process.
Standards: ITIL / ISO 20000.
Produce a document request list and fieldwork checklist for this audit area.
```

**Intended file location:** `prompts/audit-use-cases/ia-fieldwork-preparation.md`

---

## 6. Tools and Techniques

### Approach

TBD — the repository contains a workflow diagram (see `IA preparation agent SAAF.png` in the [IA-Fieldwork-Preparation repo](https://github.com/SAAF-Project/IA-Fieldwork-Preparation)) showing the intended agent architecture. No code was committed; the prototype likely ran in Claude Desktop or as a prompt-only skill during Hackathon 1.

### Example script or pseudocode

```python
# TBD — pseudocode placeholder
def prepare_fieldwork(audit_scope: str, framework: str) -> dict:
    # Call Claude with fieldwork preparation prompt
    # Return structured fieldwork plan (test procedures, interview questions, PBC items)
    pass
```

**Tech stack used:** TBD

**Intended file location:** TBD

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF Standard 2200 | Engagement Planning |
| IIA IPPF Standard 2300 | Performing the Engagement |
| TBD | Domain-specific standards per audit area |

### Claude / AI tool usage notes

TBD — no real audit evidence or personal data should be processed by the agent.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** TBD — likely Markdown or structured JSON

**Schema reference:** TBD

### Synthetic example output

```
TBD — see IA preparation agent workflow diagram in the repo for intended output structure.
```

---

## 9. Tech Stack

**MVP scope:**

- [ ] Claude API / Claude Desktop
- [ ] TBD

**Stretch goals:**

- [ ] TBD

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- TBD — the workflow diagram and prompt(s) at minimum

**What help I'm looking for:**

- TBD

**Cross-org interest:**

Fieldwork preparation is a universal challenge across internal audit functions. A reusable skill or agent for this step would be directly applicable to many of the 45+ SAAF organizations, regardless of audit domain.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Prototype demonstrated at Hackathon 1 (March 10, 2026) — see workflow diagram in repo |
| **Check** | Not started | TBD |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the exact input format — free-text audit scope, structured risk assessment, or a filled-in audit universe?
2. What artefacts does the tool produce — test procedures, interview questions, PBC items, or a combination?
3. Which standards and audit domains were tested during the hackathon prototype?
