# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of robeminem94) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Auditors working with datasets that contain personal data face a double challenge: they need access to the data to perform the audit, but they must simultaneously protect data subjects' rights under GDPR. Manually identifying and masking PII is time-consuming and error-prone — especially when the same field (e.g. an IBAN or employee name) may be required for one audit purpose and excessive for another. The GDPR AI Audit Agent automates PII detection, classification, and role-based masking while maintaining a verifiable audit trail. Auditors get structured, pseudonymized data; DPOs get a full compliance log; and nothing leaves the system without a documented GDPR legal basis.

---

## 3. Use-Case Type and Scope

**Audit domain:** GDPR Compliance / Data Privacy Audit

**Applicable standards:**

- GDPR (Regulation (EU) 2016/679) — Art. 5, 6, 15, 17, 22, 28, 32, 33, Chapter V
- ISO 27001 (A.18.1 — Compliance with legal and contractual requirements)

**In scope:**

- Detecting PII in audit datasets (emails, IBANs, names, phone numbers, SSNs) via regex + field-name heuristics
- Classifying each field as Required, Optional, or Excessive per audit purpose
- Mapping GDPR legal basis per field and audit purpose
- Role-based dynamic masking (Auditor / DPO / Admin)
- Pseudonymization of Required fields with reversible HMAC tokens
- Immutable JSONL audit trail with chain-of-thought reasoning
- Streamlit web UI for interactive use

**Out of scope:**

- Automated DPIA generation (described in repo description but marked as stretch)
- Integration with data warehouse or GRC systems
- Real-time streaming data processing

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | System prompts in `prompts/` within the repo for PII classification reasoning |
| **Tools** | Full Python pipeline in [GDPR-AI-Audit-Agent repo](https://github.com/SAAF-Project/GDPR-AI-Audit-Agent): `pipeline.py`, `pii_detector.py`, `field_classifier.py`, `legal_basis_mapper.py`, `dynamic_masker.py`, `pseudonymizer.py`, `audit_logger.py`; Streamlit web UI (`app.py`) |
| **Regulatory** | GDPR article mappings in `regulatory/` within the repo; reusable from `regulatory/control-mappings/` in SAAF-Project repo |
| **Outputs** | Masked JSON dataset, JSONL audit trail with GDPR reasoning per field |

---

## 5. Prompts

### System prompt (draft)

```
You are a GDPR compliance specialist assisting internal auditors.
Given a dataset field and the audit purpose, determine:
1. Whether this field is Required, Optional, or Excessive for this audit purpose
2. The applicable GDPR legal basis (Art. 5, 6, 15, 17, 22, 28, 32, 33, or Chapter V)
3. A brief chain-of-thought reasoning explaining your decision.
Base your decision only on GDPR provisions — do not invent legal justifications.
Never output raw PII in your reasoning.
```

### Example user prompts

**Prompt 1 — field classification:**
```
Audit purpose: reimbursement_review (legal basis: Art. 6(1)(f) — Legitimate Interest)
Field name: employee_name
Field value type: full name (PII)
Classify this field as Required, Optional, or Excessive for this audit purpose.
Provide GDPR article reference and reasoning.
```

**Prompt 2 — legal basis mapping:**
```
Audit purpose: breach_investigation (GDPR Art. 33 — Breach Notification)
Fields present: email, iban, ip_address, transaction_amount
For each field, determine the GDPR article that governs processing in this context.
```

**Intended file location:** `prompts/audit-use-cases/gdpr-ai-audit-agent.md`

---

## 6. Tools and Techniques

### Approach

The agent processes audit records through a 4-step pipeline:

1. **PII detection** — regex patterns and field-name heuristics identify sensitive fields (emails, IBANs, names, phone numbers, SSNs, IP addresses)
2. **Field classification** — each field is classified as Required, Optional, or Excessive relative to the stated audit purpose using Claude
3. **Legal basis mapping** — GDPR article resolved per field/purpose combination
4. **Role-based masking** — Auditor sees pseudonymized Required fields and masked Optional/Excessive; DPO sees partial masking; Admin sees raw data with justification logged

All decisions are written to an immutable JSONL audit trail including chain-of-thought reasoning.

### Example script or pseudocode

```python
from pathlib import Path
from gdpr_agent.models import AuditContext, Role
from gdpr_agent.pipeline import AuditPipeline

ctx = AuditContext(
    role=Role.AUDITOR,
    purpose="reimbursement_review",
    legal_basis="legitimate_interest",
)

pipeline = AuditPipeline(audit_context=ctx, log_dir=Path("./outputs"))
masked = pipeline.process_records(records)

# Required fields pseudonymized: "Hans Mueller" -> "PSE-a1b2c3d4"
# Excessive fields fully masked:  "123456789" -> "[REDACTED]"
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), Streamlit, Pydantic, HMAC (stdlib)

**Intended file location:** `tools/scripts/gdpr-ai-audit-agent/` (reference [GDPR-AI-Audit-Agent repo](https://github.com/SAAF-Project/GDPR-AI-Audit-Agent))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GDPR Art. 5 | Data minimization, purpose limitation |
| GDPR Art. 6 | Lawful basis for processing |
| GDPR Art. 15 | Right of access |
| GDPR Art. 17 | Right to erasure |
| GDPR Art. 22 | Automated decision-making |
| GDPR Art. 28 | Processor obligations |
| GDPR Art. 32 | Security of processing |
| GDPR Art. 33 | Breach notification |
| GDPR Chapter V | International transfers |

### Claude / AI tool usage notes

All test data is synthetic. No real PII or audit data is sent to the API. The repo uses `.env` for API key management — see `.env.example`. The audit trail logs reasoning but never raw PII.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (masked dataset), JSONL (audit trail)

**Schema reference:** Not a findings schema — outputs masked records with GDPR metadata. Partially maps to `outputs/schemas/finding-schema.json` for the audit trail entries.

### Synthetic example output

```json
{
  "id": "RMB-001",
  "employee_name": "PSE-a1b2c3d4e5f6",
  "email": "h***@***.com",
  "iban": "PSE-b2c3d4e5f6a1",
  "amount": 245.50,
  "_gdpr_meta": {
    "purpose": "reimbursement_review",
    "legal_basis": "Art. 6(1)(f)",
    "role": "AUDITOR",
    "fields_masked": ["employee_name", "email", "iban"],
    "fields_pseudonymized": ["employee_name", "iban"]
  }
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] Streamlit (web UI)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Automated DPIA generation from audit trail
- [ ] Integration with data warehouse connectors (SQL, CSV bulk)
- [ ] Real-time streaming masking for live audit sessions

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Full Python pipeline (7 modules) with 43 tests (96% coverage)
- GDPR legal basis mapping table (reusable by any SAAF organization)
- Synthetic test dataset
- Streamlit web UI

**What help I'm looking for:**

- Review from DPOs or privacy lawyers on GDPR article mapping accuracy
- Input on additional PII field types relevant to specific sectors (insurance, banking, healthcare)
- Extension: CCPA, UK GDPR, or other jurisdiction mappings

**Cross-org interest:**

Any organization that audits data-processing activities or handles audit evidence containing PII will benefit from this agent. The role-based masking model (Auditor / DPO / Admin) is directly applicable to most internal audit functions across the 45+ SAAF organizations.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Full prototype with 43-test suite built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned for internal adoption in data privacy audit engagements |
| **Act** | Not started | Target: Hackathon 3 — share learnings and extend to DPIA generation |

---

## 12. Open Questions

1. Should pseudonymization tokens (HMAC) be scoped per engagement or per field type? — affects reproducibility across audit cycles
2. How should the agent handle fields where GDPR classification is genuinely ambiguous (e.g. an employee ID that is sometimes PII and sometimes not)?
3. Is there interest in a shared GDPR legal basis mapping table that all SAAF organizations maintain collectively?
