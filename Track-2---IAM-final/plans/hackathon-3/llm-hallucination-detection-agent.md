# Plan: LLM Hallucination Detection Agent

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `llm-hallucination-detection-agent.md` |
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Skill |
| **Primary domain** | Evidence quality / AI risk management |
| **Source** | WhatsApp: "AI Innovators: Hub • General" (April 2026) — discussion on mechanistic interpretability and detecting when models generate false claims; "AI als tool voor audit" — auditor concern about AI-generated content reliability before entry into audit dossier |

---

## 2. Problem Statement

AI-generated audit findings can contain **hallucinations**: plausible-sounding statements that are factually incorrect, unsupported by source documents, or internally inconsistent. When these findings enter the audit dossier unchecked, they create audit quality failures that are difficult to detect after the fact.

Current SAAF plans produce findings as Claude API output but have no dedicated validation layer to flag potential hallucinations before the findings are accepted by the auditor. This is a systematic gap across all 52 existing plans.

**Concrete risk:** An agent generates a finding that cites "ISO 27001 clause 8.2.3" but that clause does not exist (or the citation is from a different framework). Without a hallucination check, this enters the dossier as a verified fact.

---

## 3. Use-Case Type & Scope

**Type:** Skill (reusable component that any SAAF agent can call as a post-processing step)

**Scope:**
- Accept a draft finding (from any SAAF agent) as input
- Cross-check factual claims: standard citations, article numbers, control names, dates
- Score each claim by confidence (Supported / Unverified / Likely hallucinated)
- Return an annotated finding with a hallucination risk flag
- Block entry to the audit dossier if risk = High; warn if Medium

**Out of scope:**
- Replacing auditor judgment — the skill flags claims, humans decide
- Real-time streaming validation (post-generation check only)
- Full document-level re-generation when hallucinations are found

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Claim extraction prompt; per-claim verification prompt; risk-scoring rubric |
| **Tools** | Claude API (verification), SAAF RAG knowledge base (regulatory corpus cross-check), finding-schema.json (input format) |
| **Regulatory** | IIA Standard 2310 (identifying information — quality of evidence), IIA Standard 1200 (proficiency), EU AI Act Art. 13 (transparency of high-risk AI outputs) |
| **Outputs** | Annotated finding JSON with `hallucination_risk` field; JSONL audit log per validation run |

---

## 5. Prompts

### Prompt 1 — Claim Extraction
```
System: You are an audit quality control assistant. Your task is to extract every factual claim from an audit finding.

A "factual claim" is any statement that references:
- A specific standard, framework, regulation, or article number (e.g., "ISO 27001 clause 6.1", "DORA Article 13")
- A specific control name, control number, or control domain
- A date, deadline, or time-bound requirement
- A numeric threshold or percentage
- A named system, tool, vendor, or process

User: Extract all factual claims from the following audit finding. For each claim, output a JSON object with:
- "claim": the exact quoted text
- "claim_type": one of [standard_reference, control_name, date_threshold, numeric_value, system_name, other]
- "verifiable": true/false (can this be checked against a reference document?)

Finding:
[FINDING_TEXT]
```

### Prompt 2 — Claim Verification
```
System: You are an audit evidence verification assistant. You have access to the SAAF regulatory corpus (DORA, GDPR, ISO 27001, IIA Standards, NIS2, EU AI Act summaries).

For each claim below, determine whether it is:
- SUPPORTED: The claim accurately matches the referenced source
- UNVERIFIED: The claim cannot be confirmed or denied from available sources
- LIKELY_HALLUCINATED: The claim appears factually incorrect (wrong article number, non-existent clause, misquoted threshold)

User: Verify the following claim extracted from an AI-generated audit finding:

Claim: [CLAIM_TEXT]
Claim type: [CLAIM_TYPE]

Retrieved context from regulatory corpus:
[RAG_CONTEXT]

Respond with:
- verdict: SUPPORTED | UNVERIFIED | LIKELY_HALLUCINATED
- confidence: High | Medium | Low
- reason: one sentence explaining the verdict
- corrected_reference: if LIKELY_HALLUCINATED, provide the correct reference (if known)
```

### Prompt 3 — Risk Score Aggregation
```
System: You are an audit quality gate. Based on individual claim verification results, determine the overall hallucination risk of a finding.

Rules:
- If ANY claim is LIKELY_HALLUCINATED with High confidence → overall_risk = HIGH (block finding)
- If 2+ claims are UNVERIFIED → overall_risk = MEDIUM (warn auditor)
- If all claims are SUPPORTED → overall_risk = LOW (pass)

User: Aggregate the following claim verification results into an overall hallucination risk assessment:

[CLAIM_RESULTS_JSON]

Output a JSON object:
{
  "overall_risk": "HIGH | MEDIUM | LOW",
  "blocked": true/false,
  "summary": "one sentence for the auditor",
  "flagged_claims": [list of LIKELY_HALLUCINATED claims],
  "unverified_claims": [list of UNVERIFIED claims]
}
```

---

## 6. Tools & Techniques

| Tool | Role |
|---|---|
| Claude API (Sonnet) | Claim extraction and verification |
| SAAF RAG knowledge base (`saaf-rag-knowledge-base.md`) | Regulatory corpus for cross-referencing claims |
| `outputs/schemas/finding-schema.json` | Input format (all SAAF findings) |
| Python `json` + `pathlib` | Reading findings, writing annotated output |
| JSONL logger | Audit trail of all validation runs |

**Key pattern — two-step verification:**
1. Extract claims from the finding text (structured extraction)
2. For each claim, run a focused RAG query + verification prompt

This is more reliable than asking one prompt to "check the whole finding for hallucinations" — extracting claims first forces the model to be explicit about what it is checking.

---

## 7. Regulatory Framework

| Standard | Requirement |
|---|---|
| **IIA Standard 2310** | Auditors must identify sufficient, reliable, relevant, and useful information. AI-generated findings must meet these criteria before entering the dossier |
| **IIA Standard 1200** | Proficiency — internal auditors must apply due professional care, including evaluating automated tools used in the engagement |
| **EU AI Act Article 13** | Transparency obligation: high-risk AI systems must provide output that is interpretable and traceable to the basis for conclusions |
| **IIA GTAG: Artificial Intelligence** | Recommends auditors establish quality controls over AI-generated content, including validation of AI output accuracy |

**Audit trail requirement:** Every hallucination check must be logged (input finding, extracted claims, per-claim verdict, final risk score, timestamp, model used). This log must be retained as part of the audit dossier.

---

## 8. Output Format

### Annotated Finding (JSON)
```json
{
  "id": "F-0042",
  "title": "Insufficient patch application timeliness for critical vulnerabilities",
  "risk_rating": "High",
  "observation": "ISO 27001 clause 8.8 requires...",
  "recommendation": "...",
  "hallucination_check": {
    "run_at": "2026-04-21T14:32:00Z",
    "model": "claude-sonnet-4-6",
    "overall_risk": "MEDIUM",
    "blocked": false,
    "summary": "One citation (ISO 27001 clause 8.8) verified; one threshold (30 days) is unverified against source policy",
    "flagged_claims": [],
    "unverified_claims": [
      {
        "claim": "critical patches must be applied within 30 days",
        "verdict": "UNVERIFIED",
        "reason": "30-day threshold not found in ISO 27001 text; may derive from internal policy"
      }
    ]
  }
}
```

### Validation Log (JSONL)
One line per validation run appended to `outputs/logs/hallucination-checks.jsonl`:
```json
{"timestamp": "2026-04-21T14:32:00Z", "finding_id": "F-0042", "claims_checked": 3, "supported": 2, "unverified": 1, "hallucinated": 0, "overall_risk": "MEDIUM", "blocked": false}
```

---

## 9. Tech Stack

```
Language:     Python 3.9+
Dependencies: anthropic (Claude API), chromadb (RAG lookup)
Config:       ANTHROPIC_API_KEY from environment
Input:        Any SAAF finding JSON (finding-schema.json format)
Output:       Annotated finding JSON + JSONL log
```

### Script: `tools/scripts/hallucination_check.py`

```python
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import anthropic

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

client = anthropic.Anthropic()
LOG_PATH = Path("outputs/logs/hallucination-checks.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

CLAIM_EXTRACTION_SYSTEM = """You are an audit quality control assistant..."""
CLAIM_VERIFICATION_SYSTEM = """You are an audit evidence verification assistant..."""
RISK_AGGREGATION_SYSTEM = """You are an audit quality gate..."""

def extract_claims(finding_text: str) -> list[dict]:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=CLAIM_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": f"Finding:\n{finding_text}"}]
    )
    return json.loads(response.content[0].text)

def verify_claim(claim: dict, rag_context: str) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=CLAIM_VERIFICATION_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Claim: {claim['claim']}\n"
            f"Claim type: {claim['claim_type']}\n\n"
            f"Retrieved context:\n{rag_context}"
        )}]
    )
    return json.loads(response.content[0].text)

def aggregate_risk(claim_results: list[dict]) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=RISK_AGGREGATION_SYSTEM,
        messages=[{"role": "user", "content": json.dumps(claim_results)}]
    )
    return json.loads(response.content[0].text)

def check_finding(finding: dict) -> dict:
    text = f"{finding.get('title', '')} {finding.get('observation', '')} {finding.get('recommendation', '')}"
    claims = extract_claims(text)
    log.info(f"Extracted {len(claims)} claims from finding {finding.get('id')}")

    results = []
    for claim in claims:
        if claim.get("verifiable"):
            rag_context = "(RAG lookup placeholder — integrate with saaf-rag-knowledge-base)"
            verdict = verify_claim(claim, rag_context)
            results.append({"claim": claim["claim"], **verdict})

    risk = aggregate_risk(results)

    finding["hallucination_check"] = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model": "claude-sonnet-4-6",
        **risk
    }

    with LOG_PATH.open("a") as f:
        f.write(json.dumps({
            "timestamp": finding["hallucination_check"]["run_at"],
            "finding_id": finding.get("id"),
            "claims_checked": len(results),
            "overall_risk": risk["overall_risk"],
            "blocked": risk["blocked"]
        }) + "\n")

    return finding

if __name__ == "__main__":
    import sys
    finding_path = Path(sys.argv[1])
    finding = json.loads(finding_path.read_text())
    annotated = check_finding(finding)
    out_path = finding_path.with_stem(finding_path.stem + "_checked")
    out_path.write_text(json.dumps(annotated, indent=2))
    log.info(f"Written: {out_path} | Risk: {annotated['hallucination_check']['overall_risk']}")
```

---

## 10. Collaboration & Cross-References

**Dependencies (this skill consumes):**
- `saaf-rag-knowledge-base.md` — regulatory corpus for claim verification
- `outputs/schemas/finding-schema.json` — input format

**Dependents (plans that should call this skill):**
- All agent plans that produce findings: `frank-van-dissel-uc4-fraud-risk-assessment.md`, `the-control-freaks-uc7-rcm-builder.md`, `document-evidence-extraction-agent.md`, `audit-subagent-coordination-framework.md`, `robeminem94-gdpr-ai-audit-agent.md`

**Related plans:**
- `ellert-van-der-vecht-llm-owasp.md` — OWASP LLM Top 10 includes hallucination (LLM06); this skill addresses that risk operationally
- `audit-memory-knowledge-system.md` — semantic search layer can supplement RAG for local audit-specific knowledge

**WhatsApp source attribution:**
> This plan was initiated from a discussion in the **"AI Innovators: Hub • General"** WhatsApp group (April 2026) where participants (including Jan Schipper, accountant, and Terrence, data governance analyst) discussed Anthropic's mechanistic interpretability research on detecting when LLMs generate false claims. The concern was raised that AI-generated audit evidence must be validated before entering the audit dossier. The **"AI als tool voor audit"** group independently raised the same reliability concern for audit use cases.

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | Pending | Build at Hackathon #3 |
| **Check** | Not started | Test on 5 real H2 findings; measure precision (how many flagged claims were actually wrong) |
| **Act** | Not started | Tune confidence thresholds based on false-positive rate from Check phase |

**Hackathon #3 task (Engineer role):**
Run `hallucination_check.py` against 3 findings from `example-synthetic-access-review.md` and 2 from `frank-van-dissel-uc4-fraud-risk-assessment.md`. Count: how many claims were flagged? How many were false positives?

---

## 12. Open Questions

1. **RAG integration**: The script currently has a placeholder for RAG lookup. Should it use the shared `saaf-rag-knowledge-base.md` ChromaDB instance, or a separate lightweight index?
2. **Blocking threshold**: Is it acceptable to block a finding automatically (not allow it in the dossier)? Or should the skill always warn without blocking, leaving the decision to the auditor?
3. **Performance**: Claim extraction + per-claim verification = multiple API calls per finding. For a 50-finding audit, this adds latency and cost. Is the quality gain worth it?
4. **Scope creep**: Should the skill also check logical consistency (finding X says A, finding Y says not-A)? Or keep it to factual citation verification only?
