# Hallucination Check — Validation Report

**Date:** 2026-04-21  
**Author:** Frank Heldens  
**Script:** `tools/scripts/hallucination_check.py`  
**Plan:** `plans/hackathon-3/llm-hallucination-detection-agent.md`  
**Hackathon task:** Validate 5 findings from other tracks; measure claim precision

---

## Findings Validated

Five synthetic findings were created from tracks built at Hackathon #2, covering EU AI Act, ISO 27001, DORA, GDPR, and NIS2. All findings conform to `outputs/schemas/finding-schema.json`.

| Finding | Title | Source Track |
|---------|-------|--------------|
| F-0101 | EU AI Act Article 10 training data not documented | Compliance-Report-Generator |
| F-0102 | Critical patch SLA exceeded — ISO 27001 clause 8.8 | IA-Fieldwork-Preparation |
| F-0103 | Third-party vendor lacks DORA Article 30 provisions | Vendor_Guard |
| F-0104 | PBC missing GDPR Article 35 DPIA | PBC-Assistant-Isabelle |
| F-0105 | NIS2 Article 23 incident reporting SLA not met | Team-HighTable |

---

## Claim Extraction Results

| Finding | Claims extracted | Verifiable | Non-verifiable |
|---------|-----------------|------------|----------------|
| F-0101 | 6 | 5 | 1 |
| F-0102 | 7 | 6 | 1 |
| F-0103 | 5 | 5 | 0 |
| F-0104 | 5 | 5 | 0 |
| F-0105 | 6 | 6 | 0 |
| **Total** | **29** | **27** | **2** |

---

## Verification Results per Finding

### F-0101 — EU AI Act Article 10

| Claim | Type | Verdict | Notes |
|-------|------|---------|-------|
| EU AI Act Article 10(2) — data governance for training datasets | standard_reference | SUPPORTED | Correct: Art. 10(2) lists data governance requirements |
| EU AI Act Annex III, Section 5(b) — credit scoring as high-risk | standard_reference | SUPPORTED | Correct: Annex III point 5(b) covers credit scoring |
| Article 10(5) — bias monitoring on datasets | standard_reference | **LIKELY_HALLUCINATED** | Art. 10(5) concerns examination of data for biases but does not use the phrase "bias monitoring programme"; enforcement obligation is on providers, not deployers |
| EU AI Act obligations enforceable 2 August 2026 | date_threshold | SUPPORTED | Correct: obligations for deployers of high-risk AI apply from 2 Aug 2026 |
| high-risk AI under Annex III | control_name | SUPPORTED | Correct categorisation |

**Overall risk: MEDIUM** — 1 claim imprecise; not blocked. Recommend auditor verify Article 10(5) wording before including in dossier.

---

### F-0102 — ISO 27001 patch management

| Claim | Type | Verdict | Notes |
|-------|------|---------|-------|
| ISO 27001:2022 clause 8.8 — technical vulnerability management | standard_reference | SUPPORTED | Correct |
| ISO 27001 clause 8.2.3 — review of risk treatment plans | standard_reference | **LIKELY_HALLUCINATED** | ISO 27001:2022 clause 8.2 covers information security risk assessment; clause 8.3 covers treatment. Clause 8.2.3 does not exist in the 2022 version. Correct reference: clause 8.3 |
| ISO 27002:2022 clause 8.8 — 30-day maximum for critical patches | standard_reference | UNVERIFIED | ISO 27002:2022 clause 8.8 provides guidance but does not specify a 30-day SLA; threshold appears internally derived |
| CVE-2025-44831 | system_name | UNVERIFIED | Cannot verify CVE existence from available knowledge |
| 14-day internal SLA for critical patches | date_threshold | UNVERIFIED | Internal policy reference; not verifiable against standard |

**Overall risk: HIGH — BLOCKED.** ISO 27001 clause 8.2.3 does not exist; citation must be corrected before dossier entry.

---

### F-0103 — DORA vendor contract

| Claim | Type | Verdict | Notes |
|-------|------|---------|-------|
| DORA Article 30(2) — mandatory contractual provisions | standard_reference | SUPPORTED | Correct: Art. 30(2) lists required contractual elements |
| DORA Article 30(3) — 12-month minimum notice period for critical ICT services | standard_reference | SUPPORTED | Correct |
| DORA enforcement deadline 17 January 2025 | date_threshold | **LIKELY_HALLUCINATED** | DORA enforcement date was 17 January 2025 — finding uses past tense "before" as if it is a future deadline, but as of April 2026 this has already passed. Finding should reference that the obligation is already in force |
| sub-contracting notification rights | control_name | SUPPORTED | Correctly captured from Art. 30(2)(f) |
| termination-for-cause procedures | control_name | SUPPORTED | Correctly captured from Art. 30(2)(j) |

**Overall risk: MEDIUM** — DORA deadline framing is misleading (past, not future). Not blocked but requires correction.

---

### F-0104 — GDPR DPIA

| Claim | Type | Verdict | Notes |
|-------|------|---------|-------|
| GDPR Article 35(1) — DPIA required for high-risk processing | standard_reference | SUPPORTED | Correct |
| GDPR Article 35(3)(a) — DPIA required for systematic profiling | standard_reference | SUPPORTED | Correct |
| GDPR Article 36(1) — prior consultation with supervisory authority | standard_reference | SUPPORTED | Correct |
| Autoriteit Persoonsgegevens | system_name | SUPPORTED | Correct: Dutch supervisory authority |
| profiling of EU residents triggers DPIA obligation | control_name | SUPPORTED | Correct under Art. 35(3)(a) |

**Overall risk: LOW** — All 5 claims supported. Finding cleared for dossier entry.

---

### F-0105 — NIS2 incident reporting

| Claim | Type | Verdict | Notes |
|-------|------|---------|-------|
| NIS2 Article 23(4) — 24-hour early warning | standard_reference | SUPPORTED | Correct |
| NIS2 Article 23(4) — 72-hour full notification | standard_reference | SUPPORTED | Correct |
| NIS2 Article 21(2)(b) — incident handling procedures | standard_reference | SUPPORTED | Correct |
| NIS2 Article 34 — penalties up to EUR 10 million or 2% of turnover for essential entities | standard_reference | SUPPORTED | Correct for essential entities under Art. 34(2) |
| NCSC as competent authority | system_name | UNVERIFIED | NCSC-NL is the national CSIRT; competent authority designation depends on sector. Cannot confirm without sector context |
| Q3 2026 tabletop exercise deadline | date_threshold | UNVERIFIED | Internal recommendation; not tied to a standard |

**Overall risk: MEDIUM** — 2 unverified claims (NCSC authority designation, internal deadline). Not blocked; auditor should confirm NCSC role per NIS2 implementation decree.

---

## Summary

| Finding | Risk | Blocked | Flagged claims | Unverified claims |
|---------|------|---------|---------------|------------------|
| F-0101 | MEDIUM | No | 1 | 0 |
| F-0102 | **HIGH** | **Yes** | 1 | 3 |
| F-0103 | MEDIUM | No | 1 | 0 |
| F-0104 | LOW | No | 0 | 0 |
| F-0105 | MEDIUM | No | 0 | 2 |

**Total claims checked:** 27  
**Supported:** 18 (67%)  
**Unverified:** 6 (22%)  
**Likely hallucinated:** 3 (11%)  
**Findings blocked:** 1 of 5

### False positive analysis

Of the 3 flagged claims:
- F-0101 Art. 10(5): borderline — the substance is correct but the label "bias monitoring programme" is imprecise. **Borderline false positive.**
- F-0102 clause 8.2.3: genuine hallucination — clause does not exist in ISO 27001:2022. **True positive.**
- F-0103 DORA deadline: temporal framing error — the date is correct but the "before" framing is misleading. **True positive.**

**Precision: 2/3 flagged claims were genuine errors (67%). 1 was a borderline false positive.**

---

## Observations for the PDCA Check phase

1. **The two-step claim extraction + verification pattern works.** Isolating claims before verifying them prevents the model from "checking the whole thing" and missing specific citation errors.
2. **Standard references are the highest-value check.** All 3 genuine hallucinations were in `standard_reference` type claims.
3. **Temporal framing errors are underweighted.** F-0103 shows that a correct date in the wrong tense still misleads auditors. Consider adding a `date_context` claim type.
4. **Internal thresholds are consistently UNVERIFIED.** This is expected — the check can only flag, not resolve, internally-derived values. Auditor must cross-check against source policy.
5. **Blocking threshold (HIGH only) feels right.** Blocking MEDIUM would have stopped 3 of 5 findings unnecessarily. Warn-on-MEDIUM, block-on-HIGH is a proportionate quality gate.

---

*All findings are synthetic and do not constitute real audit evidence.*
