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

The Risk and Control Matrix (RCM) is the central artifact of any internal audit — connecting identified risks to control activities. Building it today is manual: auditors take outputs from multiple sources (prior audits, incident data, fraud scenarios, regulatory requirements), deduplicate them by hand, categorize them into process areas, draft control descriptions, and assign risk scores. The result is often a bloated, inconsistent RCM where risks from different sources are duplicated, orphaned risks exist without controls, and the link to business objectives is weak. The RCM Builder Agent automates this synthesis: it ingests multi-source risk data from UC1–UC6, deduplicates and clusters intelligently, maps every risk to a process objective, drafts mitigating controls, and produces a complete, GIAS-compliant RCM ready for the Work Program Agent (UC8).

This is **Use Case 7 of 9** in a complete AI-assisted audit planning pipeline developed by Mollie. It is the central aggregator of the pipeline — consuming outputs from all Phase 1 (UC1–UC2) and Phase 2 (UC3–UC5) agents plus the IT Dependency Matrix (UC6), and producing the RCM that drives [UC8 (Work Program)](frank-van-dissel-uc8-audit-work-program.md).

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Risk and Control Matrix (GIAS 13.2, 13.6)

**Applicable standards:**

- GIAS 13.2 — "Evaluating the significance of the risks and prioritizing them for review" by linking them to business objectives
- GIAS 13.6 — Provides the foundational "Criteria" and "Tasks" required for the Work Program

**In scope:**

- Ingesting and aligning the process map and business objectives from UC1
- Consolidating and deduplicating risk outputs from UC2, UC3, UC4, and UC5
- Categorizing each risk to the specific Sub-Process and Business Objective it threatens
- Drafting mitigating controls (Preventive vs. Detective) for each risk
- Assigning inherent and residual risk scores based on synthesized intelligence
- Flagging sub-processes with no associated risks (potential scoping error)
- Flagging orphaned risks (no control) and orphaned controls (no risk)

**Out of scope:**

- Testing controls (that is the role of UC8)
- Producing the Work Program or assigning auditors (UC8)
- Quality and GIAS compliance review of the completed RCM (UC9)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Risk deduplication and clustering prompt; control drafting prompt; risk scoring prompt |
| **Tools** | Data synthesis pipeline across JSON/Markdown sources; deduplication and semantic grouping logic; weighted risk scoring |
| **Regulatory** | GIAS 13.2, 13.6; standard risk and control taxonomy from `regulatory/control-mappings/`; reuse `outputs/schemas/finding-schema.json` |
| **Outputs** | Full RCM: Process/Sub-Process Reference, Business Objective, Risk ID/Description, Control ID/Description, Control Type (Manual/Automated), Frequency, Risk Significance (Impact/Likelihood) |

---

## 5. Prompts

### System prompt (draft — Risk Consolidator)

```
You are an internal audit Risk and Control Matrix architect.
Given risk inputs from multiple sources (historical findings, incident clusters,
fraud scenarios, regulatory requirements) and a process map with business objectives:

1. Deduplicate and cluster semantically similar risks into single, comprehensive risk statements
2. Map each consolidated risk to the specific Sub-Process and Business Objective it threatens
3. Draft a mitigating control for each risk (specify: Preventive or Detective, Manual or Automated, Frequency)
4. Assign inherent risk scores (Impact: High/Medium/Low × Likelihood: High/Medium/Low)
5. Apply residual risk scoring based on the effectiveness of the proposed control

Flag: (a) sub-processes with no associated risks, (b) risks without controls, (c) controls without risks.
Maintain traceability: every risk must reference its source (UC2/UC3/UC4/UC5).
```

### Example user prompts

**Prompt 1 — Risk consolidation:**
```
Process map: [from UC1 — 3 sub-processes: Invoice Receipt, Approval, Payment]
Risk inputs:
- UC2 (historical): "Duplicate payments" (recurrence: 3 audits), "Unauthorized vendor approvals"
- UC3 (incidents): Cluster "duplicate payments" (42 incidents), "missing GR" (19 incidents)
- UC4 (fraud): "Ghost vendor scheme", "Invoice splitting below approval threshold"
- UC5 (regulatory): DORA — "No documented ICT incident classification"

Consolidate, deduplicate, categorize to sub-processes, draft controls, score risks.
```

**Prompt 2 — Deduplication:**
```
Risk A (from UC3): "Unauthorized access to vendor master data" — IT incident cluster
Risk B (from UC4): "Ghost vendor fraud — unauthorized vendor creation" — fraud scenario

These appear to describe overlapping root causes. Should they be merged?
If yes, draft a consolidated risk statement. If no, explain the distinction.
```

**Intended file location:** `prompts/audit-use-cases/uc7-rcm-builder.md`

---

## 6. Tools and Techniques

### Approach

Multi-source aggregation pipeline with three quality gates:

1. **Ingest & Align:** Import process map and business objectives from UC1; tag all risk inputs with their source (UC2/3/4/5)
2. **Deduplicate & Cluster:** Semantic grouping to prevent "Risk Bloat" — multiple risks from different sources describing the same underlying weakness are merged into one comprehensive statement
3. **Categorize & Score:** Map each consolidated risk to sub-process and business objective; draft control (Preventive/Detective, Manual/Automated); assign inherent and residual risk scores
4. **Quality Gates:** Three structural integrity checks (see below)

### Quality Safeguards

**Safeguard 1 — Structural Integrity Agent:** Ensures every sub-process identified in UC1's Context Brief has at least one associated risk. Empty sub-processes are flagged as potential scoping errors.

**Safeguard 2 — Mapping Integrity Agent:** Ensures no orphaned risks (risks without controls) or orphaned controls (controls not addressing a documented risk) exist in the final RCM.

**Safeguard 3 — Taxonomy Validator:** Verifies that risk and control descriptions match the organization's professional language and level of granularity — preventing inconsistent or overly generic descriptions.

### Example script or pseudocode

```python
def run_rcm_builder(context_brief: dict, uc2: dict, uc3: dict, uc4: dict, uc5: dict, uc6: dict) -> dict:
    all_risks = consolidate_risks(uc2, uc3, uc4, uc5)       # Tag sources
    deduplicated = deduplicate_and_cluster(all_risks)         # Semantic grouping
    
    rcm = categorize_and_score(deduplicated, context_brief)  # Map to sub-processes + objectives
    rcm = draft_controls(rcm, uc6)                           # Include IT dependency context
    
    # Quality gates
    rcm = structural_integrity_check(rcm, context_brief)
    rcm = mapping_integrity_check(rcm)
    rcm = taxonomy_validator(rcm)
    
    return rcm
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6 for synthesis, claude-sonnet-4-6 for validation)

**Intended file location:** `tools/scripts/uc7-rcm-builder/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | Evaluating the significance of risks and prioritizing them for review |
| GIAS 13.6 | Criteria and tasks required for the Work Program — RCM is the foundation |

### Claude / AI tool usage notes

Risk inputs from UC2–UC5 must be anonymized if they contain real audit findings or incident data. The RCM output is a planning document — it does not contain evidence. No real personal data should be included.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON + XLSX (full RCM)

**Schema reference:** Each RCM row maps to `outputs/schemas/finding-schema.json` structure; risk ID follows `R-{PROCESS}-{NNN}` pattern; control ID follows `C-{PROCESS}-{NNN}`

### Test Scenario 1 — Process-Risk Alignment

- **Input:** Context Brief with 3 sub-processes + 10 mixed risks from UC2–UC5
- **Expected:** RCM where all 10 risks are categorized under correct sub-processes; no orphaned risks
- **Validation:** Manual review confirms Business Objective assigned to each risk logically matches the risk description

### Test Scenario 2 — Deduplication

- **Input:** UC3 finds "access issue" in Jira incidents; UC4 identifies "unauthorized access" as fraud scenario
- **Expected:** Agent merges these into one comprehensive risk statement rather than two separate lines
- **Validation:** Lead auditor confirms merged statement captures both dimensions

### Synthetic example output

```json
{
  "rcm": [
    {
      "risk_id": "R-P01-001",
      "sub_process": "Invoice Approval",
      "business_objective": "Ensure only valid, authorized invoices are approved for payment",
      "risk_description": "Invoices may be approved without adequate review, enabling duplicate or fraudulent payments",
      "risk_sources": ["UC2: 3 recurring findings", "UC3: 42 duplicate payment incidents", "UC4: FR-001 ghost vendor scenario"],
      "inherent_risk": {"impact": "High", "likelihood": "High", "rating": "High"},
      "control_id": "C-P01-001",
      "control_description": "System-generated duplicate payment check blocks invoices with matching supplier + amount + date",
      "control_type": "Automated",
      "control_frequency": "Every transaction",
      "residual_risk": {"impact": "High", "likelihood": "Low", "rating": "Medium"}
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] XLSX export of the RCM for import into TeamMate+ or other audit management systems
- [ ] Interactive RCM review UI for auditors to accept, reject, or modify AI-generated rows

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Risk deduplication and clustering prompt
- Three quality gate agent prompts (Structural Integrity, Mapping Integrity, Taxonomy Validator)
- RCM JSON schema (compatible with UC8 input)

**What help I'm looking for:**

- Auditors to review the deduplication logic and validate that merged risk statements are audit-appropriate
- Organizations with mature RCM templates to contribute to a shared risk taxonomy

**Related SAAF plans:**

- [UC1](frank-van-dissel-uc1-policy-process-intake.md), [UC2](frank-van-dissel-uc2-previous-audit-intelligence.md), [UC3](frank-van-dissel-uc3-incident-issue-intelligence.md), [UC4](frank-van-dissel-uc4-fraud-risk-assessment.md), [UC5](frank-van-dissel-uc5-regulatory-criteria.md), [UC6](frank-van-dissel-uc6-it-dependency-identifier.md) — all provide input to this agent
- [UC8 — Work Program Agent](frank-van-dissel-uc8-audit-work-program.md) — consumes the RCM output
- [UC9 — Quality & Resource Guard](frank-van-dissel-uc9-quality-resource-guard.md) — validates the completed RCM
- [Floris Stokkers — Work Program Agent](floris-stokkers-work-program-agent.md) — builds on the same RCM concept; coordinate on output schema
- [Inge Garretsen — Audit Work Program Agent](inge-garretsen-audit-work-program-agent.md) — related approach; potential alignment
- [The Control Freaks — UC7 RCM Builder](the-control-freaks-uc7-rcm-builder.md) — parallel submission addressing the same use case; coordinate on three-stage lifecycle design and UC6 validation loop

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Use case designed by Frank van Dissel & Lauren Browne (Mollie); presented at Hackathon 2 |
| **Do** | Not started | Prototype to be built |
| **Check** | Not started | Planned: validate against Mollie RCM templates |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. What is the standard risk taxonomy / control taxonomy that the SAAF community should adopt — so RCMs from different organizations are comparable?
2. How should the agent handle risks that span multiple sub-processes — should they appear once (in the primary sub-process) or be replicated?
3. How do we align the RCM output schema with the input format expected by [Floris Stokkers' Work Program Agent](floris-stokkers-work-program-agent.md)?
