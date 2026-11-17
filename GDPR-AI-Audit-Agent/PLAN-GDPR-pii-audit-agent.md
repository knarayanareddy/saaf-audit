# Plan: GDPR PII Audit Agent

| Field | Value |
|---|---|
| **Submitter** | Robert |
| **Organisation** | TBD |
| **Session** | Session 2 |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

We receive large volumes of audit data (e.g., reimbursement documents) containing an unknown amount of personal data that we are not permitted to process in the clear. An AI audit agent must **detect, classify, and mask PII** before any human auditor interacts with the data — while preserving the ability to reproduce results and maintain a verifiable audit trail.

**Key constraints:**
- Data must be encrypted/masked **without loss of reproducibility**
- Chain-of-thought tracking required to verify legitimacy
- Consent-based processing — mask everything not covered by a legal basis

---

## 3. Use-Case Type and Scope

**Audit domain:** Data Privacy / GDPR Compliance

**Applicable standards:**

- GDPR (Regulation 2016/679)
- ISO 27001 (A.18.1 — Compliance)
- SOC 2 (CC6 — Logical and Physical Access Controls)

**In scope:**

- PII detection using NER + regex pattern matching
- Field classification (Required / Optional / Excessive)
- Role-based dynamic masking (Auditor / DPO / Admin)
- GDPR legal basis mapping per article
- Immutable audit logging with chain-of-thought

**Out of scope:**

- Real-time data streaming processing
- Non-European regulatory frameworks
- Automated decision-making compliance (Art. 22 appeals)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompts: `pii-detection-system.md`, `masking-decision.md`, `field-classification.md`, `explainability-report.md` |
| **Tools** | New Python scripts: `pii_detector.py`, `dynamic_masker.py`, `pseudonymizer.py`, `audit_logger.py`, `pipeline.py` |
| **Regulatory** | New mapping: `regulatory/gdpr_legal_bases.json` with Article 5, 6, 15, 17, 22, 28, 32, 33 |
| **Outputs** | Masked datasets, audit logs (JSONL), explainability reports, compliance summaries |

---

## 5. Prompts

### System prompt (draft)

```
You are a GDPR-compliant PII detection agent. Your task is to analyze data records and identify all fields containing personal data.

## Categories

- **Identifier**: Names, SSN, ID numbers, passport numbers
- **Financial**: IBAN, credit card numbers, bank account details
- **Contact**: Email, phone, physical address, IP address
- **Special Category**: Health data, religious beliefs, political opinions, ethnic origin, biometric data

## Rules

1. Err on the side of caution — if uncertain, flag as PII
2. Consider indirect identifiers (e.g., "department" + "job title" could identify someone)
3. Return structured JSON with field name, category, and confidence score (0.0-1.0)
4. Never include the actual PII values in your reasoning output
```

### Example user prompts

**Prompt 1:**
```
Process this reimbursement record and detect all PII fields:
{"id": "RMB-001", "employee_name": "Hans Mueller", "email": "hans.mueller@example.com", "iban": "DE89370400440532013000", "amount": 245.50}
```

**Prompt 2:**
```
For role=AUDITOR and purpose=reimbursement_review, determine masking decisions for these detected fields: employee_name, email, iban, ssn
```

**Intended file location:** `prompts/audit-use-cases/gdpr-pii-audit-agent.md`

---

## 6. Tools and Techniques

### Approach

The agent implements a 4-step pipeline:
1. **Detect PII** — regex patterns + field-name heuristics find emails, IBANs, names, phones, SSNs
2. **Classify fields** — marks each as Required, Optional, or Excessive per audit purpose
3. **Map legal basis** — resolves GDPR articles (Art. 5, 6, 15, 17, 22, 28, 32, 33, Chapter V)
4. **Mask dynamically** — role-based masking (Auditor = full, DPO = partial, Admin = raw access)

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
masked = pipeline.process_records([{"id": "RMB-001", "employee_name": "Hans Mueller", ...}])

for entry in pipeline.get_audit_log():
    print(f"{entry.action}: {entry.reasoning}")
```

**Tech stack used:** Python 3.10+, Pydantic, HMAC (pseudonymization), JSONL logging

**Intended file location:** `tools/scripts/gdpr_pii_audit_agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GDPR | Art. 5(1)(c) — Data Minimization |
| GDPR | Art. 6(1)(f) — Legitimate Interest |
| GDPR | Art. 15 — Right of Access |
| GDPR | Art. 17 — Right to Erasure |
| GDPR | Art. 22 — Automated Decision-Making |
| GDPR | Art. 28 — Processor Obligations |
| GDPR | Art. 32 — Security of Processing |
| GDPR | Art. 33 — Breach Notification |
| GDPR | Art. 5(1)(e) — Data Retention |
| GDPR | Chapter V — Cross-Border Transfers |

### Claude / AI tool usage notes

No real PII will be sent to the API. All training and testing uses synthetic/anonymized data only.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON + JSONL (audit logs)

**Schema reference:** `outputs/schemas/finding-schema.json` (for compliance findings)

### Synthetic example output

```json
{
  "id": "RMB-001",
  "employee_name": "[REDACTED]",
  "email": "h***@***.com",
  "iban": "PSE-a1b2c3d4e5f6",
  "amount": 245.50,
  "_audit": {
    "masking_applied": true,
    "role": "AUDITOR",
    "fields_masked": ["employee_name", "email", "iban"]
  }
}
```

**Audit log entry:**
```json
{"timestamp": "2026-03-29T10:00:00Z", "action": "MASK", "field": "email", "method": "partial", "reasoning": "Contact category, not required for audit purpose"}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.10+
- [x] Pydantic (data validation)
- [x] GitHub (fork + PR)
- [x] Synthetic test data

**Stretch goals:**

- [ ] Claude API integration for NER
- [ ] Mattermost webhook for chain-of-thought tracking
- [ ] Integration with existing GRC tooling

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- System prompts for PII detection and masking decisions
- Python library for GDPR-aware data masking
- GDPR legal basis mapping (JSON)
- Synthetic test datasets

**What help I'm looking for:**

- Someone with SOC 2 expertise to review the control mappings
- Feedback on the pseudonymization approach for reproducibility

**Cross-org interest:**

Other organizations processing personal data in audit workflows would benefit from this agent.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Template filled in, user stories defined |
| **Do** | In progress | Prototype built at hackathon |
| **Check** | Not started | Planned for private adoption |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. Should pseudonymization keys be organization-specific or shared?
2. How to handle cross-border data residency requirements?
3. Best approach for explaining AI masking decisions to auditors?
