# GDPR AI Audit Agent

A Python-based AI agent that **detects, classifies, and masks PII** in audit data while maintaining GDPR compliance and a verifiable audit trail.

Built for the **SAAF Hackathon 2** — pillars: Prompts, Tools, Regulatory, Outputs.

## What It Does

1. **Detects PII** — regex patterns + field-name heuristics find emails, IBANs, names, phones, SSNs
2. **Classifies fields** — marks each as Required, Optional, or Excessive per audit purpose
3. **Maps legal basis** — resolves GDPR articles (Art. 5, 6, 15, 17, 22, 28, 32, 33, Chapter V)
4. **Masks dynamically** — role-based masking (Auditor = full, DPO = partial, Admin = raw access)
5. **Pseudonymizes** — Required fields get reversible HMAC tokens for reproducibility
6. **Logs everything** — immutable JSONL audit trail with chain-of-thought reasoning

## Quick Start

```bash
# Clone and install
cd GDPR
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"

# Generate a pseudonymisation key — required, there is no default
python -c "import secrets; print(secrets.token_urlsafe(32))"
# then put it in .env as GDPR_PSEUDONYM_KEY=...

# Run tests
pytest tests/ -v

# Launch the web demo
streamlit run app.py
```

## Web Demo (Streamlit)

```bash
streamlit run app.py
```

Opens a browser UI where you can:
- **Pick a role** (Auditor / DPO / Admin) and audit purpose
- **Upload JSON** or use the built-in sample data
- **See side-by-side** original vs masked data
- **Download** masked output and audit logs

## Python API

```python
from pathlib import Path
from gdpr_agent.models import AuditContext, Role
from gdpr_agent.pipeline import AuditPipeline

# Define who is requesting and why
ctx = AuditContext(
    role=Role.AUDITOR,
    purpose="reimbursement_review",
    legal_basis="legitimate_interest",
)

# Process records
pipeline = AuditPipeline(audit_context=ctx, log_dir=Path("./outputs"))
masked = pipeline.process_records([
    {
        "id": "RMB-001",
        "employee_name": "Hans Mueller",
        "email": "hans.mueller@example.com",
        "iban": "DE89370400440532013000",
        "amount": 245.50,
    }
])

print(masked[0])
# {'id': 'RMB-001',
#  'employee_name': '[REDACTED]',
#  'email': 'h***@***.com',
#  'iban': 'PSE-a1b2c3d4e5f6',   <-- pseudonymized (reversible)
#  'amount': 245.50}

# Get summary
print(pipeline.get_summary())
# {'records_processed': 1, 'total_pii_fields': 3, 'total_masked': 3, ...}

# Get audit trail
for entry in pipeline.get_audit_log():
    print(f"{entry.action}: {entry.reasoning}")
```

## Role-Based Masking

| Role | Required Fields | Optional Fields | Excessive Fields |
|------|----------------|-----------------|------------------|
| **Auditor** | Pseudonymized (PSE-xxx) | Fully masked | Fully masked |
| **DPO** | Partially masked | Partially masked | Fully masked |
| **Admin** | Raw (justification required and logged) | Raw | Raw |

## Supported Audit Purposes

| Purpose | GDPR Article |
|---------|-------------|
| Reimbursement Review | Art. 6(1)(f) — Legitimate Interest |
| Compliance Check | Art. 6(1)(f) — Legitimate Interest |
| Breach Investigation | Art. 33 — Breach Notification |
| Deletion Verification | Art. 17 — Right to Erasure |
| Data Access Request | Art. 15 — Right of Access |
| Third-Party Audit | Art. 28 — Processor Obligations |
| Retention Review | Art. 5(1)(e) — Data Retention |
| Cross-Border Audit | Chapter V — International Transfers |

## Project Structure

```
├── app.py                          # Streamlit web UI
├── src/gdpr_agent/
│   ├── models.py                   # Pydantic data models
│   ├── config.py                   # PII patterns, config
│   ├── pii_detector.py             # PII detection engine
│   ├── field_classifier.py         # Required/Optional/Excessive
│   ├── legal_basis_mapper.py       # GDPR article resolution
│   ├── dynamic_masker.py           # Role-based masking
│   ├── pseudonymizer.py            # Reversible HMAC tokenization
│   ├── audit_logger.py             # Immutable JSONL logging
│   └── pipeline.py                 # 4-step orchestrator
├── prompts/                        # AI system prompts
├── regulatory/                     # GDPR legal basis mappings
├── tests/                          # 43 tests, 96% coverage
└── data/                           # Synthetic sample data
```

## Security

- Never commit real audit data, PII, or credentials
- Use `.env` for API keys (see `.env.example`)
- All test data is synthetic
- Audit logs contain no raw PII

### Pseudonymisation key

`GDPR_PSEUDONYM_KEY` is **required** and has no default. It must be at least 32
characters and unique per deployment; the app and the pipeline both refuse to
start without it.

This matters because the tokens are `HMAC-SHA256(key, value)`. Anyone who knows
the key can compute the token for a guessed value and confirm a match, so a
shared or hardcoded key lets any holder of the source reverse every pseudonym by
precomputation. Data that anyone can re-identify is not pseudonymised in the
sense of GDPR Art. 4(5) — it is just obfuscated.

Rotating the key changes every token, so the same data subject will no longer
map to the same pseudonym across datasets produced before and after the change.

### Re-identification

The pipeline is **one-way by default**: nothing retains the original values.
Reversal requires explicitly constructing a `PseudonymVault` and passing it in:

```python
from gdpr_agent.pseudonymizer import PseudonymVault

vault = PseudonymVault()
pipeline = AuditPipeline(audit_context=ctx, log_dir=Path("./outputs"), vault=vault)
...
vault.resolve(token, role=Role.DPO, justification="SAR-2026-014")
```

The vault holds the Art. 4(5) "additional information" separately from the
tokens, checks the caller's role (auditors may not re-identify), and requires a
stated reason. Call `vault.clear()` when the session ends.

### Tamper-evident audit trail

Each audit entry stores the SHA-256 hash of its predecessor, so editing or
deleting any entry invalidates every hash after it:

```python
from gdpr_agent.audit_logger import AuditLogger

AuditLogger.verify_file(pipeline.audit_log_file)   # False if the trail was altered
```

This makes the trail verifiable by a third party rather than merely written in
append mode.

### Unmasked access

`Role.ADMIN` receives unmasked data, so `AuditContext` requires a
`justification` for it and records that reason in the audit trail against every
record accessed. Constructing an admin context without one raises.
