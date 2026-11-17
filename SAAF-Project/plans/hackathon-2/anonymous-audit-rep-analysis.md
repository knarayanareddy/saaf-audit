# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Anonymous) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Auditors preparing for a new engagement often need to review previous audit reports covering the same domain or entity to understand what findings were raised before, whether they were resolved, and which ones remain relevant to the current audit objective. This review is time-consuming and subjective — different auditors assess relevance differently, and the volume of past reports can be large. The AuditRepAnalysis agent automates this: it reads previous audit reports, scores each historical finding for relevance to the current audit objective, selects those worth following up, and drafts follow-up findings — including a risk score — ready for the auditor to review and finalize.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Prior Findings Review / Follow-up

**Applicable standards:**

- IIA IPPF — Standard 2500 (Monitoring Progress — following up on prior audit findings)
- IIA IPPF — Standard 2200 (Engagement Planning — considering prior audit results)

**In scope:**

- Ingesting previous audit reports (PDF or structured formats)
- Scoring each historical finding for relevance to the current audit objective
- Selecting findings that warrant follow-up (above a relevance threshold)
- Drafting follow-up findings with updated observation and risk score
- Structuring output as a follow-up register

**Out of scope:**

- Substantive testing of whether prior findings have been resolved (requires evidence review)
- Integration with audit management systems (manual import/export only in MVP)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | System prompt for relevance scoring and follow-up finding drafting — TBD (repo is empty) |
| **Tools** | TBD — see [AuditRepAnalysis repo](https://github.com/SAAF-Project/AuditRepAnalysis) |
| **Regulatory** | Reuse `regulatory/control-mappings/` for cross-referencing finding domains |
| **Outputs** | Follow-up finding register conforming to `outputs/schemas/finding-schema.json` |

---

## 5. Prompts

### System prompt (draft)

```
You are an internal audit assistant specialised in prior findings review.
Given a set of historical audit findings and the objective of the current audit,
score each finding for relevance (0–10) and explain why.
For findings with a relevance score above the threshold, draft a follow-up finding:
updated observation (what was the original finding and what is the expected current status),
risk score (High/Medium/Low/Informational), and recommendation.
Base your output only on the provided historical findings and current objective.
Do not invent evidence or assume findings have been resolved without evidence.
```

### Example user prompts

**Prompt 1 — relevance scoring:**
```
Current audit objective: Assess the effectiveness of access management controls for FY 2025.

Previous audit findings (2023 report):
- F-001: User accounts of terminated employees not deactivated within SLA (High)
- F-002: Privileged accounts not reviewed quarterly (Medium)
- F-003: Network segmentation gaps in the DMZ (Low)

Score each finding for relevance to the current objective (0–10). Explain your scoring.
```

**Prompt 2 — follow-up finding drafting:**
```
F-001 (relevance: 9/10): User accounts of terminated employees not deactivated within SLA.
Original recommendation: Implement automated deprovisioning triggered by HR system.
Current status: Unknown — no evidence of implementation received.

Draft a follow-up finding with updated observation and risk score.
```

**Intended file location:** `prompts/audit-use-cases/audit-rep-analysis.md`

---

## 6. Tools and Techniques

### Approach

TBD — the repository was created during Hackathon 2 (March 24, 2026) but contains no code. Based on the description, the intended approach is:

1. Ingest previous audit report(s) (PDF/DOCX/structured format)
2. Extract individual findings (id, title, risk rating, observation, recommendation)
3. Score each finding for relevance to the current audit objective via Claude
4. Filter to findings above the relevance threshold
5. Draft follow-up findings with updated observation and risk score
6. Output as a structured follow-up register

### Example script or pseudocode

```python
# TBD — pseudocode placeholder
def analyse_prior_findings(
    prior_reports: list[str],
    current_objective: str,
    relevance_threshold: float = 6.0
) -> list[dict]:
    findings = extract_findings(prior_reports)
    scored = [score_relevance(f, current_objective) for f in findings]
    relevant = [f for f in scored if f["relevance"] >= relevance_threshold]
    return [draft_followup(f) for f in relevant]
```

**Tech stack used:** TBD — likely Python 3.9+, Claude API

**Intended file location:** `tools/scripts/audit-rep-analysis/` (reference [AuditRepAnalysis repo](https://github.com/SAAF-Project/AuditRepAnalysis))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF Standard 2500 | Monitoring Progress — follow-up on prior audit findings |
| IIA IPPF Standard 2200 | Engagement Planning — consideration of prior audit results |

### Claude / AI tool usage notes

Previous audit reports processed by the agent should be anonymized — no real personal data, client names, or confidential findings should be sent to the API. Use synthetic or anonymized versions for testing.

### Guardrails checklist

- [ ] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [ ] No runtime `pip install`
- [ ] Python scripts run only from `tools/scripts/`
- [ ] No real audit evidence, credentials, or personal data committed
- [ ] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (follow-up finding register)

**Schema reference:** `outputs/schemas/finding-schema.json` — each follow-up finding has id, title, risk_rating, observation, recommendation.

### Synthetic example output

```json
{
  "id": "F-FUP-001",
  "title": "Follow-up: User accounts of terminated employees — SLA compliance (originally F-001, 2023)",
  "risk_rating": "High",
  "observation": "In the 2023 audit, user accounts of terminated employees were not deactivated within the agreed 24-hour SLA in 15 of 50 sampled cases. The recommended automated deprovisioning workflow has not been evidenced as implemented. The finding remains relevant to the current access management audit objective.",
  "recommendation": "Request evidence of implementation of the automated deprovisioning workflow (or equivalent control). If not implemented, maintain the High risk rating and expand the sample to assess current SLA compliance."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [ ] Claude API
- [ ] Python 3.9+
- [ ] GitHub (fork + PR)

**Stretch goals:**

- [ ] Integration with audit management systems (TeamMate+, AuditBoard) for automated prior finding import
- [ ] Relevance scoring calibration based on auditor feedback

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- TBD — system prompt for relevance scoring and follow-up drafting once developed

**What help I'm looking for:**

- Auditors to validate the relevance scoring logic against real prior findings review workflows
- Input on relevance thresholds and follow-up finding structure

**Cross-org interest:**

Prior findings review is a mandatory step in most internal audit methodologies (IIA Standard 2500). This agent is immediately relevant to all 45+ SAAF organizations. Combining it with the Team-HighTable semantic similarity approach could produce a powerful cross-engagement knowledge reuse tool.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan; repo created Hackathon 2 (March 24, 2026) |
| **Do** | Not started | Repository is empty — prototype not yet built |
| **Check** | Not started | TBD |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the optimal relevance scoring scale — 0–10 numeric, or categorical (High/Medium/Low relevance)?
2. How should the agent handle findings that were partially resolved — include them with a lower risk rating, or flag as "partially open"?
3. Is there interest in combining this agent with Team-HighTable's semantic similarity approach for a unified prior findings + past issues knowledge base?
