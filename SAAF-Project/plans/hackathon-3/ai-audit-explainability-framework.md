# Plan: AI Audit Explainability Framework

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `ai-audit-explainability-framework.md` |
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Framework + Workflow |
| **Primary domain** | AI governance / Evidence quality |
| **Source** | WhatsApp: "AI Innovators: Hub • General" (April 2026) — extended discussion on mechanistic interpretability (Anthropic research), Explainable AI (xAI), and neurosymbolic AI; concern raised that AI explanations may be post-hoc rationalizations rather than genuine reasoning traces; "AI als tool voor audit" — auditor (Jan Schipper) asked: "how do we defend an AI-generated finding when challenged by the auditee?" |

---

## 2. Problem Statement

Internal auditors using AI to generate findings face a challenge that has no analogue in traditional audit: **the AI cannot explain, in audit-defensible terms, why it reached a conclusion.** When an auditee challenges a finding, the auditor must be able to explain the reasoning chain — but AI models produce outputs without a transparent step-by-step trace.

Three related gaps:

1. **No reasoning trace**: Claude generates "Control B4 is ineffective because..." but there is no record of which evidence caused that conclusion vs. what the model already "knew" from training.
2. **Post-hoc rationalization risk**: AI models can generate plausible-sounding explanations after the fact that do not reflect the actual computational process (a documented risk in xAI research).
3. **No audit framework for AI explanations**: IIA and regulatory guidance (EU AI Act) requires transparency for high-risk AI outputs, but no SAAF plan yet defines *how* to operationalize this for audit findings.

---

## 3. Use-Case Type & Scope

**Type:** Framework + Workflow

**Scope:**
- Define an explainability standard for SAAF-generated audit findings (what does "explainable" mean in an audit context?)
- Produce a 3-level explainability hierarchy: Evidence trace → Reasoning trace → Conclusion justification
- Provide prompts that force the model to produce explicit reasoning chains (Chain-of-Thought with audit anchoring)
- Define an auditee challenge response template: how to defend an AI-generated finding in a management response discussion
- Reference EU AI Act Art. 13 and IIA guidance for regulatory anchoring

**Out of scope:**
- Mechanistic interpretability research (this is academic; practical audit procedures only)
- Full neural network interpretability tooling (Anthropic's internal research, not production tools)
- Replacing auditor judgment with explainable AI output

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Chain-of-Thought audit reasoning prompt; evidence anchoring prompt; challenge response template |
| **Tools** | Claude API (Sonnet for complex reasoning), audit trail logger, `finding-schema.json` |
| **Regulatory** | EU AI Act Art. 13 (transparency), IIA Standard 2420 (quality of communications), IIA GTAG AI, DORA Art. 9 (ICT risk management — reasoning traceability for AI-driven decisions) |
| **Outputs** | Explainability annex (JSON) appended to each finding; challenge response brief (Markdown) |

---

## 5. Prompts

### Prompt 1 — Chain-of-Thought Audit Reasoning
```
System: You are a senior internal auditor producing a finding for an audit dossier.
Your finding must be explicitly traceable to evidence. Follow this structure:

1. EVIDENCE: List every piece of evidence that informed this finding (document names,
   data points, interview quotes). Do not cite knowledge not present in the provided context.
2. REASONING: For each piece of evidence, explain what audit risk or control weakness it indicates.
   Reference the specific norm, standard, or criterion being violated.
3. CONCLUSION: State the finding. The conclusion must be directly derivable from the
   evidence and reasoning above — do not introduce new information at this step.
4. CONFIDENCE: Rate your confidence (High / Medium / Low) and explain why.
   If Low, state what additional evidence would be needed to increase confidence.

User: Draft a finding based on the following evidence:

Evidence context:
[EVIDENCE_TEXT]

Applicable criteria (norm/standard/control):
[CRITERIA_TEXT]

Produce output in the structure above, then format the conclusion as a finding-schema.json object.
```

### Prompt 2 — Explainability Annex Generation
```
System: You are an audit documentation specialist. Given a completed audit finding and its
reasoning trace, produce an explainability annex suitable for the audit dossier.

The annex must answer these five questions that an auditee might ask:
1. What specific evidence did you look at?
2. Which rule, standard, or control criterion was violated?
3. How did you determine the violation? (step-by-step logic)
4. What would a compliant situation look like?
5. How confident are you, and what could change your assessment?

User: Produce an explainability annex for the following finding and reasoning trace:

Finding:
[FINDING_JSON]

Reasoning trace:
[REASONING_TRACE]

Output as structured Markdown with the five questions as headers.
```

### Prompt 3 — Auditee Challenge Response
```
System: You are an audit quality reviewer. An auditee has challenged an AI-assisted audit
finding. Your task is to prepare a response brief that the auditor can use in the
management response discussion.

The response must:
- Acknowledge the challenge without defensiveness
- Restate the evidence base (what was observed, not what the AI concluded)
- Confirm that a qualified auditor reviewed and validated the AI output
- Cite the applicable criterion/norm
- Separate AI-generated content from auditor judgment (what did the AI flag? what did the auditor decide?)

User: Prepare a challenge response brief for the following situation:

Finding: [FINDING_TEXT]
Auditee challenge: [CHALLENGE_TEXT]
Auditor validation notes: [AUDITOR_NOTES]
```

---

## 6. Tools & Techniques

| Tool | Role |
|---|---|
| Claude API (Sonnet) | Chain-of-Thought reasoning; explainability annex generation |
| `outputs/schemas/finding-schema.json` | Finding format (extended with `explainability_annex` field) |
| Markdown template | Auditee challenge response brief |
| `llm-hallucination-detection-agent.md` | Companion skill — checks factual claims in the reasoning trace |

**Key design principle — evidence anchoring:**
The reasoning prompt explicitly prohibits the model from introducing knowledge not present in the provided context. This is the audit equivalent of "cite your sources." It does not eliminate hallucination risk (hence the companion hallucination detection skill) but makes evidence leakage visible.

**Chain-of-Thought is not mechanistic interpretability:**
The reasoning traces produced by these prompts are the model's stated reasoning, not a view into the model's weights or attention patterns. Anthropic's mechanistic interpretability research (referenced in the WhatsApp discussion that originated this plan) is a research field, not a production tool. This framework uses CoT as the practical approximation for audit purposes.

---

## 7. Regulatory Framework

| Standard | Requirement |
|---|---|
| **EU AI Act Article 13** | High-risk AI systems must enable users to interpret outputs; providers must ensure outputs are "sufficiently interpretable" for the intended users |
| **EU AI Act Article 14** | Human oversight — AI outputs must not be acted upon without human review; audit documentation must evidence this review |
| **IIA Standard 2420** | Quality of communications — findings must be accurate, objective, clear, concise, constructive, complete, and timely. AI-generated content must meet all seven criteria |
| **IIA Standard 2330** | Documenting information — sufficient, reliable, relevant, useful information must be documented; reasoning traces satisfy the "relevant" and "reliable" requirements |
| **DORA Article 9(4)(c)** | ICT risk management must include "traceability and monitoring" — reasoning traces enable auditability of AI-assisted ICT risk decisions |

**Regulatory gap:** The IIA's 2024 GTAG on Artificial Intelligence acknowledges that AI introduces transparency challenges but does not yet prescribe specific explainability standards. This framework is an attempt to operationalize EU AI Act Art. 13 requirements in an audit context ahead of formal IIA guidance.

---

## 8. Output Format

### Extended Finding Schema (with explainability annex)
```json
{
  "id": "F-0017",
  "title": "Inadequate segregation of duties in payment approval workflow",
  "risk_rating": "High",
  "observation": "...",
  "recommendation": "...",
  "explainability_annex": {
    "evidence_sources": [
      {"type": "data", "description": "Access rights export from Strapi (200 users)", "date": "2026-04-20"},
      {"type": "document", "description": "Payment policy v2.3, Section 4.2", "date": "2025-11-01"}
    ],
    "applicable_criterion": "IIA IPPF 2310 — Identifying Information; COSO 2013 Control Activity CC5.2",
    "reasoning_steps": [
      "Step 1: Identified 12 users with both initiator and approver roles (evidence: access rights export)",
      "Step 2: Cross-referenced against payment policy Section 4.2 which prohibits this combination",
      "Step 3: Confirmed 3 payment transactions in audit period where initiator = approver (evidence: transaction log)"
    ],
    "compliant_scenario": "Initiator and approver roles are held by different individuals; no user has both permissions simultaneously",
    "confidence": "High",
    "confidence_rationale": "Finding supported by system data and policy text; no contradicting evidence observed",
    "ai_role": "Claude identified the 12 conflicting users from the access rights data; auditor confirmed by spot-checking 3 transactions manually",
    "auditor_reviewed_by": "[Auditor name]",
    "auditor_review_date": "2026-04-21"
  }
}
```

### Auditee Challenge Response Brief (Markdown)
```markdown
# Challenge Response: F-0017 — Segregation of Duties

**Auditee challenge:** "The AI made this finding, it's not a real audit conclusion."

## Our response

**Evidence base (independent of AI):**
The finding is based on an export of access rights from [system name] dated 2026-04-20
showing 12 users with simultaneous initiator and approver roles, and on payment transactions
from the audit period confirming 3 instances where the same user initiated and approved a payment.

**AI role in this finding:**
AI was used to process the 200-user access rights dataset and flag users with conflicting roles.
The auditor independently verified 3 flagged users by reviewing transaction records manually.

**Criterion:**
Payment policy Section 4.2 explicitly prohibits one person from both initiating and approving payments.
This is also supported by COSO 2013 Control Activity CC5.2 (segregation of duties).

**Auditor judgment:**
The conclusion that this constitutes a control weakness is the auditor's judgment, not the AI's.
The AI performed data analysis; the auditor determined the audit significance.
```

---

## 9. Tech Stack

```
Language:     Python 3.9+ (for annex generation script)
Dependencies: anthropic (Claude API)
Config:       ANTHROPIC_API_KEY from environment
Input:        Finding JSON + reasoning trace + auditor notes
Output:       Extended finding JSON + Markdown challenge response brief
```

### Script: `tools/scripts/generate_explainability_annex.py`

```python
import json
import logging
from pathlib import Path
import anthropic

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

client = anthropic.Anthropic()

ANNEX_SYSTEM = "You are an audit documentation specialist producing explainability annexes..."
CHALLENGE_SYSTEM = "You are an audit quality reviewer preparing challenge response briefs..."

def generate_annex(finding: dict, reasoning_trace: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=ANNEX_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Finding:\n{json.dumps(finding, indent=2)}\n\n"
            f"Reasoning trace:\n{reasoning_trace}"
        )}]
    )
    return response.content[0].text

def generate_challenge_response(finding: dict, challenge: str, auditor_notes: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=CHALLENGE_SYSTEM,
        messages=[{"role": "user", "content": (
            f"Finding: {finding.get('title')}\n"
            f"Observation: {finding.get('observation')}\n\n"
            f"Auditee challenge: {challenge}\n\n"
            f"Auditor validation notes: {auditor_notes}"
        )}]
    )
    return response.content[0].text

if __name__ == "__main__":
    import sys
    finding = json.loads(Path(sys.argv[1]).read_text())
    reasoning_trace = Path(sys.argv[2]).read_text()
    annex = generate_annex(finding, reasoning_trace)
    out = Path(sys.argv[1]).with_stem(Path(sys.argv[1]).stem + "_explainability")
    out.write_text(annex)
    log.info(f"Explainability annex written to {out}")
```

---

## 10. Collaboration & Cross-References

**Dependencies (this framework consumes):**
- `outputs/schemas/finding-schema.json` — extended with `explainability_annex` field
- `llm-hallucination-detection-agent.md` — validates factual claims in the reasoning trace
- `saaf-rag-knowledge-base.md` — regulatory corpus for criterion retrieval

**Plans that benefit most from this framework:**
- `frank-van-dissel-uc4-fraud-risk-assessment.md` — high-stakes findings that will face auditee challenge
- `the-control-freaks-uc7-rcm-builder.md` — RCM control assessments need defensible reasoning
- `audit-subagent-coordination-framework.md` — multi-agent consensus findings need a clear reasoning trace showing how consensus was reached
- `robeminem94-gdpr-ai-audit-agent.md` — GDPR findings are subject to regulatory scrutiny; explainability is critical

**Related plans:**
- `ellert-van-der-vecht-llm-owasp.md` — OWASP LLM08 (Excessive Agency) and LLM09 (Overreliance) directly motivate this framework
- `audit-workflow-automation-levels.md` — Level 2 and 3 agents need explainability by design; this framework provides the "how"

**WhatsApp source attribution:**
> This plan originated from the **"AI Innovators: Hub • General"** WhatsApp group (April 2026) where participants discussed Anthropic's mechanistic interpretability research and the distinction between genuine AI reasoning and post-hoc rationalization. Jan Schipper (registered accountant) raised the practical question: "how do we defend an AI-generated finding when the auditee pushes back?" This question is the direct origin of the auditee challenge response template in Section 8. The **"AI als tool voor audit"** group confirmed this is a live concern in practice — auditors feel exposed when AI is part of the evidence chain.

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | Pending | Build at Hackathon #3 |
| **Check** | Not started | Present 3 AI-assisted findings to a vaktechniek reviewer; measure whether the explainability annex answered their questions without further clarification |
| **Act** | Not started | Update the 5-question structure based on which questions the reviewer still needed to ask |

**Hackathon #3 task (Vaktechniek role):**
Take one finding from `the-control-freaks-uc7-rcm-builder.md` and one from `robeminem94-gdpr-ai-audit-agent.md`. Run `generate_explainability_annex.py` on each. Review the output: does the annex answer the 5 questions? Mark which questions needed improvement.

---

## 12. Open Questions

1. **Evidence anchoring enforcement**: The prompt says "do not cite knowledge not present in the provided context" — but models can still hallucinate. Should we require that every evidence item in the annex maps to a specific chunk in the provided context (verifiable at runtime)?
2. **Auditor field in schema**: The `auditor_reviewed_by` field requires the auditor's name. Should this be a free text field, or should it be linked to the SAAF skills registry?
3. **Regulatory classification**: Is an AI-assisted audit finding a "high-risk AI system output" under EU AI Act Annex III? If yes, Art. 13 obligations are mandatory. Legal advice needed.
4. **Adversarial challenge scenarios**: Should we pre-define common auditee challenges (e.g., "your data was wrong", "the AI doesn't understand our context") and prepare template responses for each?
