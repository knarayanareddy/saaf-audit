# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Frank van Dissel & Lauren Browne) |
| **Organisation** | Mollie |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

The final step before fieldwork begins is a quality review of the entire planning package. Under GIAS 13.3, the CAE must approve objectives and scope; under 13.5, resources must be assessed as appropriate and sufficient; under 13.6, the CAE must review and approve the work program. In practice, this review is a manual checklist exercise performed under time pressure — it rarely catches all gaps. The Engagement Quality & Resource Guard Agent is the automated gatekeeper: it performs a rigorous QA review of the entire planning package (Context Brief, RCM, and Work Program), verifies 100% compliance with GIAS 13.2 through 13.6, assesses resource sufficiency, detects scope limitations, and produces a formal CAE Approval Package — or a "No-Go" with a draft Scope Limitation Memo.

This is **Use Case 9 of 9** — the final stage of the Mollie AI-assisted audit planning pipeline. It consumes all outputs from UC1 through UC8 and produces the definitive Go/No-Go and CAE Approval Package.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Quality Assurance — Engagement Quality & GIAS Compliance (GIAS 13.2–13.6)

**Applicable standards:**

- GIAS 13.3 — "The chief audit executive must approve the engagement objectives and scope... Scope limitations must be discussed with management."
- GIAS 13.5 — "Identify the types and quantity of resources... whether available financial, human, and technological resources are appropriate and sufficient."
- GIAS 13.6 — "The chief audit executive must review and approve the engagement work program before it is implemented."
- GIAS 13.2, 13.4 — Cross-check of risk assessment and evaluation criteria completeness

**In scope:**

- Line-by-line GIAS 13.2–13.6 compliance verification against the planning package
- Resource sufficiency assessment: required hours/skills vs. actual availability and budget
- Scope limitation detection: identifying conditions that prevent objective achievement
- Assurance vs. Advisory logic check: verifying documentation level matches service type
- Drafting formal Scope Limitation Memos for the Board
- Producing the CAE Approval Package with pending approval timestamp
- Objective-to-task traceability: ensuring 100% of objectives have corresponding work program tasks

**Out of scope:**

- Fieldwork execution or evidence review
- Post-fieldwork quality review (separate QA process)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | GIAS compliance check prompt; "Digital CAE" stress-test prompt; Scope Limitation Memo drafting prompt; Objective-to-Task Traceability prompt |
| **Tools** | Cross-reference engine (objectives from UC1 vs. tasks in UC8); resource gap calculator; GIAS standard text as RAG knowledge base |
| **Regulatory** | Full GIAS 13.2–13.6 text as compliance benchmark; reuse `regulatory/control-mappings/` |
| **Outputs** | Quality and Compliance Scorecard: GIAS Compliance Gap Analysis, Resource Sufficiency Verdict (Go/No-Go), Draft Scope Limitation Memo, CAE Approval Package |

---

## 5. Prompts

### System prompt (draft — GIAS Compliance Checker)

```
You are a Chief Audit Executive quality reviewer.
Given the complete audit planning package (Context Brief, RCM, Work Program, Criteria Matrix)
and the full text of GIAS Standards 13.2 through 13.6:

Perform a line-by-line compliance check:
1. For each GIAS requirement in Standards 13.2–13.6: is it satisfied by the planning package?
   Mark: Satisfied / Gap / Partial
2. For each Gap: identify which document should address it and what specifically is missing
3. Assess resource sufficiency: compare estimated hours and skill requirements from the Work Program
   against the auditor availability calendar and budget
4. Produce a Go/No-Go verdict: "Go" only if all GIAS requirements are Satisfied and resources are sufficient

If No-Go: list specific gaps preventing Go and draft a Scope Limitation Memo for the Board.
```

### System prompt (draft — "Digital CAE" Stress Tester)

```
You are a demanding Chief Audit Executive. You are reviewing the audit plan and will
challenge every weak point. For each element of the planning package, ask:
"Is the scope sufficient to achieve the stated objectives?"
"Why are we testing this low-significance risk if we are short on hours?"
"Is there an objective in the scope that has no corresponding test in the work program?"
"Is the methodology for this High-significance risk sufficient, or is Inquiry the only method?"

Produce a list of challenges. The audit team must be able to answer each one
before the plan is approved.
```

### Example user prompts

**Prompt 1 — Full GIAS compliance check:**
```
Planning package:
- Context Brief: [from UC1]
- Historical Risk Intelligence: [from UC2]
- Incident Intelligence: [from UC3]
- Fraud Risk Assessment: [from UC4]
- Evaluation Criteria Matrix: [from UC5]
- IT Dependency Matrix: [from UC6]
- RCM: [from UC7]
- Work Program: [from UC8]
- Auditor availability: 2 auditors × 80 hours = 160 hours total
- Required hours (from UC8): 320 hours

Perform GIAS 13.2–13.6 compliance check. Assess resource sufficiency. Produce Go/No-Go.
```

**Prompt 2 — Scope Limitation Memo:**
```
GIAS compliance check result: Go
Resource check result: No-Go — 160 hours available, 320 required.
Audit timeframe: 3 weeks.

Draft a formal Scope Limitation Memo for the Board and senior management.
Propose: (a) scope reduction options, or (b) additional resource request.
```

**Intended file location:** `prompts/audit-use-cases/uc9-quality-resource-guard.md`

---

## 6. Tools and Techniques

### Approach

Two-agent quality pipeline:

1. **GIAS Compliance Checker:** Line-by-line verification of GIAS 13.2–13.6 requirements against the planning package; produces Satisfied/Gap/Partial verdict per requirement
2. **Resource Gap Calculator:** Compares estimated hours and skill requirements (from UC8) against the auditor availability calendar and budget; produces quantified resource gap
3. **Objective-to-Task Traceability Check:** Ensures 100% of engagement objectives articulated in UC1 scope have corresponding tasks in UC8 work program
4. **"Digital CAE" Stress Tester:** Adversarial agent challenges the plan from a CAE perspective — asking hard questions about scope sufficiency, resource adequacy, and methodology appropriateness

### Quality Safeguards

**Safeguard 1 — "Digital CAE" Persona:** Stress-tests the plan by asking "Is the scope sufficient to achieve objectives?" and "Why are we testing this low-significance risk if we are short on hours?" — produces a challenge list that the audit team must resolve before approval.

**Safeguard 2 — Objective-to-Task Traceability:** Automated check that 100% of objectives in UC1's scope statement have corresponding test steps in UC8's work program. Any objective without a task is a GIAS 13.6 gap.

### Example script or pseudocode

```python
def run_quality_guard(planning_package: dict, auditor_availability: dict, budget: dict) -> dict:
    # GIAS compliance
    compliance_scorecard = gias_compliance_check(planning_package)   # 13.2-13.6
    
    # Resource sufficiency
    resource_gap = calculate_resource_gap(
        planning_package["work_program"]["resource_report"],
        auditor_availability, budget
    )
    
    # Traceability
    traceability = check_objective_to_task(
        planning_package["context_brief"]["objectives"],
        planning_package["work_program"]["tasks"]
    )
    
    # Stress test
    cae_challenges = digital_cae_agent(planning_package)
    
    # Go/No-Go
    verdict = "Go" if compliance_scorecard["all_satisfied"] and resource_gap["sufficient"] else "No-Go"
    
    if verdict == "No-Go":
        scope_memo = draft_scope_limitation_memo(compliance_scorecard, resource_gap)
    
    cae_package = build_cae_approval_package(planning_package, compliance_scorecard, resource_gap)
    
    return {"verdict": verdict, "scorecard": compliance_scorecard, "resource_gap": resource_gap,
            "traceability": traceability, "cae_challenges": cae_challenges,
            "scope_memo": scope_memo if verdict == "No-Go" else None,
            "cae_package": cae_package}
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6), GIAS text as RAG knowledge base

**Intended file location:** `tools/scripts/uc9-quality-resource-guard/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.3 | CAE approval of objectives and scope; scope limitations discussed with management |
| GIAS 13.5 | Resource appropriateness and sufficiency (financial, human, technological) |
| GIAS 13.6 | CAE review and approval of work program before implementation |
| GIAS 13.2 | Risk assessment completeness; criteria adequacy |
| GIAS 13.4 | Evaluation criteria adequacy |

### Claude / AI tool usage notes

The planning package processed contains no audit evidence or personal data — it is a set of planning documents. The GIAS text used as a RAG knowledge base is publicly available. No confidential data is sent to the API.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (Quality and Compliance Scorecard) + Markdown (Scope Limitation Memo, CAE Approval Package)

**Schema reference:** GIAS gaps map to `outputs/schemas/finding-schema.json` (risk_rating = High for Gaps, Medium for Partial)

### Test Scenario 1 — Resource Insufficiency Alert

- **Input:** Work program requiring 200 hours; timeline of 1 week with 1 auditor (40 hours)
- **Expected:** "High Priority" resource alert; No-Go verdict; draft Scope Limitation Memo citing GIAS 13.5
- **Validation:** Audit manager confirms alert and memo are accurate

### Test Scenario 2 — Missing CAE Sign-off

- **Input:** Completed work program without approval block
- **Expected:** Agent blocks Go verdict; provides "Submission for CAE Approval" action citing GIAS 13.6
- **Validation:** CAE confirms approval step was missing

### Synthetic example output

```json
{
  "verdict": "No-Go",
  "gias_scorecard": [
    {"standard": "GIAS 13.2", "requirement": "Fraud risk assessment performed", "status": "Satisfied"},
    {"standard": "GIAS 13.5", "requirement": "Resources appropriate and sufficient", "status": "Gap",
     "detail": "Work program requires 320 hours; only 160 hours available in timeframe."},
    {"standard": "GIAS 13.6", "requirement": "CAE approval of work program", "status": "Gap",
     "detail": "No CAE approval timestamp present in the work program document."}
  ],
  "resource_gap": {"required_hours": 320, "available_hours": 160, "gap": 160, "verdict": "Insufficient"},
  "cae_challenges": ["Why is Risk R-P01-003 (Low significance) in scope when we are 160 hours short?"],
  "scope_memo_drafted": true
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] GIAS text as RAG knowledge base
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Integration with audit management system for automated CAE approval workflow
- [ ] Dashboard showing GIAS compliance status across all active engagements

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- GIAS 13.2–13.6 compliance check prompt
- "Digital CAE" stress-test prompt
- Scope Limitation Memo template
- CAE Approval Package template

**What help I'm looking for:**

- CAEs and audit directors to validate the GIAS compliance check logic and stress-test quality
- Organizations with mature QA processes to compare against existing manual checklists

**Related SAAF plans:**

- [UC1](frank-van-dissel-uc1-policy-process-intake.md) through [UC8](frank-van-dissel-uc8-audit-work-program.md) — all provide input to this agent
- [Floris Stokkers — Work Program Agent](floris-stokkers-work-program-agent.md) — UC9 validates the work program that UC8 and Floris produce; coordinate on output format
- [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md) — same GIAS scope; potential alignment on quality gate approach

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie engagement QA process |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. Should the "Digital CAE" stress-test run before or after the GIAS compliance check — does the order matter for the quality of challenges raised?
2. How should the agent handle partial GIAS compliance — when is "Partial" sufficient for a Go verdict, and when does it require a No-Go?
3. Is there interest in maintaining a shared GIAS compliance check prompt across the SAAF community — so all organizations use a consistent QA standard for audit planning?
