# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of TheMonteCristo) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Procurement audits require three-way matching: verifying that a purchase order (PO), goods receipt, and vendor invoice are consistent before a payment is approved. This matching is repetitive, data-intensive, and error-prone when done manually — especially at scale across hundreds of transactions. The ASML Procurement Audit Agent automates this: it generates synthetic procurement data, validates invoices against PO registers, runs a 14-step security-hardened pipeline with OWASP controls, flags mismatches and anomalies, and produces a structured audit trail. The demo pipeline traces two invoices through the full cycle — one that passes all checks, one that triggers an escalation.

---

## 3. Use-Case Type and Scope

**Audit domain:** Procurement / Accounts Payable Audit — Three-Way Matching

**Applicable standards:**

- IIA IPPF — Standard 2300 (Performing the Engagement)
- ISO 9001 — Clause 8.4 (Control of externally provided processes, products and services)
- OWASP Top 10 Security Controls (applied to the audit pipeline itself)

**In scope:**

- Synthetic procurement data generation (suppliers, parts, purchase orders, invoices, goods receipts)
- Invoice intake and validation (required fields, VAT format, PO reference cross-check)
- Three-way matching: PO vs. goods receipt vs. invoice (quantity, price, totals)
- Decision agent: approve, flag, or escalate per invoice
- Payment scheduling for approved invoices
- Escalation reporting for failed or suspicious invoices
- Immutable audit logging throughout the pipeline
- OWASP security controls embedded in every pipeline step

**Out of scope:**

- Integration with live ERP systems (SAP, Oracle) — demo uses synthetic data only
- Real payment processing
- Continuous monitoring (batch pipeline, not real-time)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | TBD — pipeline is rules-based with structured validation; Claude integration for anomaly detection and escalation narrative is a stretch goal |
| **Tools** | Python pipeline in [threewaysecurity repo](https://github.com/SAAF-Project/threewaysecurity): `src/agent/` (7 agent modules), `src/generators/`, `src/evaluator/`, `src/security/secure_pipeline.py` |
| **Regulatory** | OWASP security controls applied to pipeline; `regulatory/guardrails/allowed-commands.md` referenced for pipeline execution |
| **Outputs** | Structured audit trail (JSONL), decision log (approve/flag/escalate per invoice), payment schedule, escalation report |

---

## 5. Prompts

### System prompt (draft — anomaly detection / escalation narrative)

```
You are an internal audit specialist in procurement fraud detection.
Given a set of invoice mismatches and anomalies flagged by the three-way matching pipeline,
produce a structured escalation report: describe each anomaly, its risk rating, and a
recommended next step for the audit team.
Base your findings only on the data provided — do not infer intent or name individuals.
Never include real IBAN numbers, VAT numbers, or supplier identities in the report.
```

### Example user prompts

**Prompt 1 — escalation narrative:**
```
Flagged invoice: INV-2025-0142
Anomalies detected:
- Quantity mismatch: PO quantity 100 units, GR quantity 100 units, invoice quantity 120 units
- Unit price deviation: PO price €45.00, invoice price €52.00 (+15.6%)
- VAT number format invalid: "NL123456789"

Generate an escalation report with risk rating and recommended actions.
```

**Prompt 2 — pattern analysis:**
```
The following supplier has had 3 escalated invoices in the past 90 days:
[summary of past escalations]

Identify any patterns and recommend whether this warrants a deeper supplier audit.
```

**Intended file location:** `prompts/audit-use-cases/procurement-three-way-match.md`

---

## 6. Tools and Techniques

### Approach

14-step sequential pipeline with OWASP security controls at each step:

| Step | Agent | Function |
|---|---|---|
| 1–4 | Generators | Synthetic suppliers, parts, purchase orders, invoices, goods receipts |
| 5 | intake_agent | Parse and validate invoice JSON (required fields, VAT format, PO reference) |
| 6 | contract_agent | Cross-check invoice against contract terms |
| 7 | threeway_agent | Three-way match: PO vs. goods receipt vs. invoice (qty, price, totals) |
| 8 | decision_agent | Approve, flag, or escalate per invoice |
| 9 | payment_agent | Schedule payment for approved invoices |
| 10 | escalation_agent | Generate escalation report for flagged invoices |
| 11 | audit_logger | Write immutable audit trail entry |
| 12–14 | Evaluator | Score pipeline output; generate evaluation report |

All steps run through `SecurePipeline` wrapper (OWASP controls: input validation, output sanitization, rate limiting, audit logging).

### Example script or pseudocode

```python
# python run_pipeline.py
from src.security.secure_pipeline import SecurePipeline
from src.agent import intake_agent, threeway_agent, decision_agent, audit_logger

secure = SecurePipeline(settings)

# Step 5: validate invoices
parsed = secure.run_step("intake", intake_agent.run, settings)

# Step 7: three-way match
matched = secure.run_step("threeway", threeway_agent.run, settings)

# Step 8: approve / flag / escalate
decisions = secure.run_step("decision", decision_agent.run, settings)
```

**Tech stack used:** Python 3.11+, `pandas` (data processing), YAML (config), OWASP security wrapper

**Intended file location:** `tools/scripts/procurement-audit-agent/` (reference [threewaysecurity repo](https://github.com/SAAF-Project/threewaysecurity))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF Standard 2300 | Evidence collection — three-way matching as audit procedure |
| ISO 9001 Clause 8.4 | Verification of externally provided products/services |
| OWASP Top 10 | Applied to the audit pipeline itself (input validation, output sanitization) |

### Claude / AI tool usage notes

The MVP pipeline is rules-based — no Claude API calls in the core matching logic. Claude is a stretch goal for anomaly narrative generation. All data is synthetic; no real procurement data, IBAN numbers, or supplier information committed.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (audit trail, decisions), CSV (payment schedule, evaluation)

**Schema reference:** Escalation findings map to `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
{
  "id": "F-PROC-001",
  "title": "Three-way match failure — quantity and price deviation on INV-2025-0142",
  "risk_rating": "High",
  "observation": "Invoice INV-2025-0142 claims 120 units at €52.00 each. PO-2025-0088 authorised 100 units at €45.00. Goods receipt confirms 100 units received. Overpayment risk: €1,290.",
  "recommendation": "Place payment on hold pending supplier clarification. Request a corrected invoice for 100 units at €45.00. Escalate to procurement manager if not resolved within 5 business days."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.11+
- [x] `pandas` (data processing)
- [x] OWASP security wrapper (custom)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Claude API for escalation narrative generation
- [ ] Integration with ERP test environment (SAP sandbox)
- [ ] Web UI for pipeline monitoring and manual review

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Full 14-step pipeline with OWASP security wrapper
- Synthetic procurement data generators
- Evaluator and audit logging modules

**What help I'm looking for:**

- Auditors with procurement audit experience to validate the matching logic and escalation thresholds
- Organizations using SAP or Oracle ERP to explore real data integration
- Review of OWASP control implementation in the pipeline

**Video Transcription Insights (Hackathon #3 analysis):**

A presentation on AI-powered Excel analysis at scale revealed a pattern directly applicable to this plan: **AI can process 1,000+ Excel rows across multiple tabs simultaneously** — a task that takes an auditor 3-4 hours takes AI 30 seconds.

For three-way matching specifically:
- Instead of loading PO, GRN, and invoice into separate DataFrames and merging programmatically, consider using Claude Vision or document extraction to process multi-tab Excel files directly — especially when ERP exports have inconsistent column names or merged header rows
- The 1,000× speed factor is most valuable when the exception list is large: instead of reviewing all exceptions, the auditor reviews only the AI-flagged high-risk exceptions (e.g., amount discrepancy >€10K, new vendor, first-time approver combination)
- Extend the pipeline with a "materiality filter": exceptions below materiality threshold are auto-closed with a standard note; only material exceptions require auditor review

**Cross-org interest:**

Three-way matching is a standard procedure in any procurement audit. The OWASP-hardened pipeline pattern is reusable for other data-processing audit agents in the SAAF community. Strong candidate for cross-org adoption by organizations auditing accounts payable processes.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Full 14-step pipeline built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned: validate against real procurement audit data |
| **Act** | Not started | Target: Hackathon 3 — share results and add Claude anomaly detection |

---

## 12. Open Questions

1. What tolerance thresholds are appropriate for price deviations before flagging — is a 5% deviation a flag or an escalation?
2. How should the pipeline handle invoices where the goods receipt is missing entirely (no delivery confirmation)?
3. Is there interest in a shared synthetic procurement dataset that all SAAF organizations can use to test their own audit agents?
