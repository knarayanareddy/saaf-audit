# Prompt: Policy Analysis for Audit Planning

**Use case:** Analyze a policy document (any format) to produce a structured audit planning package compliant with GIAS 13.2 — covering process flow, four-area analysis, risk-control matrix, audit program, and attention points.
**Applicable standards:** GIAS 13.2 (Engagement Risk Assessment), GIAS 13.6 (Engagement Work Program)
**Intended AI tool:** Claude Code (slash command / skill) — also usable as a standalone prompt with any instruction-following LLM

---

## Overview

This skill transforms an unstructured policy document into a complete audit planning package. It is the implementation of **UC1 (Policy/Process Intake Agent)** from the Mollie SAAF pipeline.

**Supported input formats:** PDF, Markdown, plain text (read directly). Word (.docx): extracted via the `docx_to_text.py` helper script.

**Outputs — two documents per run:**

| File | Contents |
|------|----------|
| `[filename]-analysis.md` | Concise analysis summary (target ≤10 pages): process overview, laws & regulations, governance, risk management summary, internal controls summary, "Always to Consider" checklist, Annex 1 risk assessment, key attention points |
| `[filename]-audit-program.md` | Full working document: policy-stated risk register (RS-xx), AI-inferred risk register (RI-xx), control register (C-xx), and audit work program with Test of Design and Test of Operating Effectiveness for each control |

An optional Excel workbook (`[filename]-audit-program.xlsx`) can be generated from the audit program using `tools/scripts/audit_program_to_excel.py`.

---

## System Context

```
You are a senior internal auditor performing an engagement risk assessment under GIAS Standard 13.2.

You will be given a policy document and asked to produce a complete audit planning package. Your analysis must be:
- Exhaustive: every section of the policy must be reflected in the output
- Traceable: every extracted element must include a source quote (section reference + quoted text)
- Clearly labelled: policy-stated risks use prefix RS-xx; AI-inferred risks use prefix RI-xx and require auditor validation
- Honest about limitations: mark all AI-suggested risk ratings as [AI-suggested]; flag placeholder fields in the policy

Do not invent content not present in the document. Do not omit sections. Flag ambiguous or implied steps explicitly.
```

---

## Workflow (8 phases)

### Phase 1 — Document Intake

Determine the file format and read the document content:

```
IF the file extension is .docx:
  Run: python3 tools/scripts/docx_to_text.py "<path-to-file>"
  Read the output .txt file produced by the script.

IF the file extension is .pdf:
  Use the Read tool to read the PDF directly.
  If longer than 50 pages, read in chunks of 20 pages.

IF the file extension is .md, .txt, or .text:
  Use the Read tool to read the file directly.
```

Extract and note: document title, version/date, owner/author, classification, table of contents / section headings (save for Phase 8 completeness check).

---

### Phase 2 — Process Flow

Generate a **text narrative** (2–4 paragraphs) covering:
- Stages of the process described in the document
- Key decision points and branching conditions
- Role handoffs and approval authorities
- Parallel activities
- Start points, end points, and exit paths
- Any steps that are ambiguous or implied rather than explicitly described

> **Note for Claude Code users:** A Mermaid flowchart (`flowchart TD`) can optionally be generated for use in GitHub/Confluence viewers, but should be omitted from PDF output as it does not render in typst.

---

### Phase 3 — Four-Area Analysis

Run a single comprehensive analysis pass covering all four GIAS 13.2 areas.

**Area 1 — Applicable Laws and Regulations**

For each identified framework:

| Framework | Type | Jurisdiction | Key Requirements Applied | Implementation Completeness |
|-----------|------|-------------|--------------------------|----------------------------|

Types: Binding Law / Regulatory Directive / Supervisory Guidance / Industry Standard / Internal Policy
Completeness: Full / Partial (explain) / Referenced only / **Not implemented** (flag as gap)

**Area 2 — Governance**

- Three Lines of Defense mapping table (Line | Roles | Functions | Source)
- Roles and Responsibilities table (Role | Responsibilities | Reports To | Qualifications | Source)
- Decision authority and escalation matrix
- Governance quality observations: segregation of duties, independence, key person dependencies, reporting lines

**Area 3 — Risk Management**

3a. Risk framework summary (risk appetite, scoring methodology, risk categories, EWRA)

3b. Policy-stated risks (RS-xx):

| Risk ID | Risk Description | Category | Process / Activity | Source Quote |
|---------|-----------------|----------|--------------------|--------------|

3c. AI-inferred risks (RI-xx) — analyze each process and activity and reason about risks NOT stated in the policy:

| Risk ID | Risk Description | Rationale | Process Affected | Category |
|---------|-----------------|-----------|-----------------|----------|

Risk categories: Operational / Compliance / Financial / Legal / Reputational / Technology / Third Party / Fraud / Data / People / Model

Fraud risks must be explicitly considered (GIAS 13.2): manipulation, misappropriation, collusion, management override.

3d. Risk completeness assessment by process area.

**Area 4 — Internal Controls**

| Control ID | Control Description | Type | Nature | Process | Risks Mitigated | Threshold / SLA | Testability | Source |
|-----------|--------------------|----|--------|---------|-----------------|----------------|-------------|--------|

Types: Preventive / Detective / Corrective / Directive
Nature: Manual / Automated / Semi-automated
Testability: High (quantified threshold/SLA) / Medium (defined procedure) / Low (qualitative)

Flag: risks with no control (unmitigated gaps), controls with no corresponding risk, key person dependencies.

---

### Phase 4 — "Always to Consider" Checklist

Assess whether the policy addresses the 8 mandatory P&O template topics:

| Topic | Addressed | Relevant Sections | Observations / Gaps |
|-------|-----------|-------------------|---------------------|
| Sustainability | | | |
| Fraud | | | |
| Culture & Behaviour | | | |
| Compliance | | | |
| Duty of Care | | | |
| Privacy / Data Protection | | | |
| Data Quality | | | |
| Data Analytics | | | |

Topics assessed as "No" or "Partially" are automatically added to Attention Points.

---

### Phase 5 — Engagement Risk Assessment (Annex 1)

Map findings to the P&O template Annex 1 structure — 13 banking risk types:

| Risk Type | Applicable (Y/N/A) | Inherent Risk [AI-suggested] | Risk Description & Audit Response | Work Program Ref |
|-----------|-------------------|------------------------------|----------------------------------|-----------------|
| Credit Risk | | | | |
| Market Risk — Banking Book | | | | |
| Market Risk — Trading Book | | | | |
| Liquidity Risk | | | | |
| Business Risk (incl. strategic) | | | | |
| Sustainability Risk | | | | |
| NFR / ICT Risk | | | | |
| NFR / Change Risk | | | | |
| NFR / Legal & Compliance Risk | | | | |
| NFR / HR, Tax, Model & Behavioural Risk | | | | |
| NFR / Fraud Risk | | | | |
| NFR / Data Risk | | | | |
| NFR / Third Party & Outsourcing Risk | | | | |

Mark N/A with rationale for risk types clearly not relevant to the policy's subject matter. All ratings are [AI-suggested — subject to auditor review].

---

### Phase 6 — Audit Work Program

Transform the control register (Phase 3, Area 4) into a complete audit program:

| # | Process | Activity (Sub-Process) | Risk (RS/RI-xx) | Control | Test of Design (ToD) | Test of Operating Effectiveness (ToE) |
|---|---------|----------------------|----------------|---------|---------------------|--------------------------------------|

**Test of Design**: How would an auditor verify the control is adequately designed (if followed, it mitigates the risk)? Focus on: reviewing policy/procedure documentation, confirming approval framework is defined, checking control parameters are specified.

**Test of Operating Effectiveness**: How would an auditor verify the control actually operates as intended? Focus on: sampling transactions/cases, re-performance, observation, inspection of evidence.

For AI-inferred risks with no existing control: include a row with Control = "[No control identified — gap]" and ToD/ToE = "[Auditor to design test procedure for this gap]".

---

### Phase 7 — Attention Points

**7.1 Policy Gaps and Weaknesses** — flag each of:
- Risks with no mitigating control
- Controls referenced but not defined in sufficient detail to be testable
- Regulatory obligations mentioned without implementation detail
- Inconsistencies between sections (conflicting thresholds, timelines, approval levels)
- Placeholder fields (`[...]`, `[TBD]`, or similar) indicating incomplete policy content
- Cross-references to other policies not available for review
- "Always to Consider" topics not addressed (from Phase 4)
- Single points of failure or key person dependencies

Format: `[Severity] Description | Policy section(s) | Why it matters for the audit`

**7.2 Professional Judgment Areas** — flag areas where auditor expertise is required:
- Controls relying on qualitative assessment ("adequate", "appropriate") without measurable criteria
- Risk ratings involving subjective scoring factors
- Governance arrangements where independence should be independently assessed
- AI-inferred risks (RI-xx) requiring auditor validation before inclusion in scope

---

### Phase 8 — Completeness Guard

Compare the document's table of contents / section headings (captured in Phase 1) against the analysis output. For each section: confirm it is reflected somewhere in the output. Flag and re-process any uncovered sections.

| Document Section | Covered? | Where Covered | Notes |
|-----------------|---------|---------------|-------|

---

## Output Assembly

**Document 1 — Analysis Summary** (`[filename]-analysis.md`, target ≤10 pages):
- Executive summary (3–5 sentences: overall risk profile, critical findings, recommended focus areas)
- Document overview (metadata table)
- Process overview (text narrative — no Mermaid)
- Laws & regulations (condensed — top frameworks + key gaps)
- Governance (3LoD table + key observations)
- Risk management summary (risk framework + top 8 most significant risks as a table)
- Internal controls summary (statistics + unmitigated risks table)
- "Always to Consider" checklist (full 8-topic table)
- Annex 1 (full 13 risk types table)
- Key attention points (top 8 gaps + top 5 professional judgment areas)

**Document 2 — Audit Program / RCM** (`[filename]-audit-program.md`):
- Part 1: Policy-stated risk register (RS-xx)
- Part 2: AI-inferred risk register (RI-xx)
- Part 3: Control register (C-xx)
- Part 4: Audit work program (WP-xx with ToD and ToE)

---

## Usage

```bash
# As a Claude Code skill (if SKILL.md is configured in your project):
/analyze-policy "path/to/policy.md" "Audit Engagement Name 2026"

# As a standalone prompt: paste Phase 1–8 instructions into your preferred LLM
# with the policy document appended.

# Generate Excel workbook from the audit program markdown:
python3 tools/scripts/audit_program_to_excel.py "path/to/[filename]-audit-program.xlsx"
```

---

## Helper Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `tools/scripts/docx_to_text.py` | Extract text from Word (.docx) documents | `.docx` file path | `.txt` file with Markdown headings preserved |
| `tools/scripts/audit_program_to_excel.py` | Generate formatted Excel workbook from audit program data | Output path | `.xlsx` with 5 sheets: Legend, Risk Register, AI-Inferred Risks, Control Register, Audit Work Program |

Both scripts require Python 3.9+ and run standalone. Install dependencies:
```bash
pip3 install python-docx openpyxl
```

---

## GIAS 13.2 Compliance Mapping

| GIAS 13.2 Requirement | How This Skill Addresses It |
|------------------------|---------------------------|
| Gather reliable, relevant, and sufficient information | All four areas extracted from the policy with source quotes |
| Understand governance, risk management, and control processes | Areas 2, 3, and 4 directly |
| Identify applicable frameworks and criteria | Area 1 (Laws & Regulations) |
| Understand how processes are intended to operate | Phase 2 (Process Flow) + Phase 6 (Audit Program) |
| Identify potentially significant risks | Area 3: policy-stated (RS-xx) + AI-inferred (RI-xx) |
| Consider fraud risks specifically | Phase 4 Always-to-Consider checklist; Area 3 fraud inference |
| Evaluate and prioritize risks for review | Phase 7 Attention Points |
| Identify management's criteria for measuring objective achievement | Area 4: controls with SLAs, thresholds, KPIs |

---

## Limitations

1. **Policy-only view**: Analysis is based solely on the document provided. It does not capture actual process execution, deviations from policy, or findings from prior audits.
2. **AI-inferred risks (RI-xx)**: Require professional auditor validation. They are starting points for discussion, not conclusions.
3. **Annex 1 ratings**: Applicability and ratings for Credit, Market, Liquidity, and Business Risk depend on organizational context not available in the policy document alone.
4. **No external data**: Previously identified risks (prior audit issues, regulator comments, operational losses) require integration with external data sources — a planned future MCP capability.
5. **Placeholder fields**: Unresolved placeholders in the source policy (e.g. `[National Regulator]`, `[TBD]`) cannot be completed by AI analysis — these are flagged as attention points.
