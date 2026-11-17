# GDPR AI Audit Agent — SAAF Hackathon 2 Plan (v2)

> **Use-case type:** Agent
> **SAAF pillars:** Prompts · Tools · Regulatory · Outputs
> **PDCA phase:** Plan → Do

---

## 1. Problem Statement

We receive large volumes of audit data (e.g., reimbursement documents) containing an unknown amount of personal data that we are not permitted to process in the clear. An AI audit agent must **detect, classify, and mask PII** before any human auditor interacts with the data — while preserving the ability to reproduce results and maintain a verifiable audit trail.

### Key Constraints

- Data must be encrypted/masked **without loss of reproducibility**
- Chain-of-thought tracking required to verify legitimacy (Mattermost integration)
- Consent-based processing — mask everything not covered by a legal basis

---

## 2. Audit Workflow (4-Step Pipeline)

| Step | Action | SAAF Pillar | Description |
|------|--------|-------------|-------------|
| **2a** | Request | Prompts | Auditor submits a data access request via the audit portal |
| **2b** | Identify PII | Tools | AI agent detects personal/sensitive fields (NER + pattern matching) |
| **2c** | Map to Legal Basis | Regulatory | Match each field to a legitimate interest; flag fields without basis |
| **2d** | Mask Unneeded PII | Tools | Pseudonymize or tokenize fields not required for the audit purpose |
| **3** | Automated Control | Tools | AI applies dynamic masking rules based on context, role, and purpose |
| **4** | Human Check | Outputs | Auditor / DPO reviews masked output for correctness and completeness |

---

## 3. SAAF Pillar Mapping

### 📝 Prompts (`prompts/`)

| Prompt | Purpose |
|--------|---------|
| `pii-detection-system.md` | System instruction for NER-based PII detection |
| `field-classification.md` | Classify fields as Required / Optional / Excessive |
| `masking-decision.md` | Decide masking level per role and legal basis |
| `explainability-report.md` | Generate human-readable explanation of AI decisions |

### 🔧 Tools (`tools/`)

| Script / Integration | Purpose |
|----------------------|---------|
| `pii_detector.py` | NER + regex pattern matching for PII |
| `dynamic_masker.py` | Context-aware masking engine |
| `pseudonymizer.py` | Reversible tokenization (reproducibility) |
| `audit_logger.py` | Immutable audit trail with chain-of-thought |
| Mattermost webhook | Chain-of-thought tracking for legitimacy checks |

### 📜 Regulatory (`regulatory/`)

| Mapping | GDPR Article |
|---------|-------------|
| Right of Access | Art. 15 |
| Data Minimization | Art. 5(1)(c) |
| Breach Investigation | Art. 33 & 34 |
| Third-Party Sharing | Art. 28 |
| Data Retention | Art. 5(1)(e) |
| Right to Erasure | Art. 17 |
| Automated Decision-Making | Art. 22 |
| Cross-Border Transfers | Chapter V |
| Logging & Accountability | Art. 5(2) |
| Access Control | Art. 32 |

### 📊 Outputs (`outputs/`)

| Output | Description |
|--------|-------------|
| Masked dataset | PII replaced with tokens/pseudonyms |
| Data categories summary | What types of data were processed |
| Audit log | Who requested, what was masked, when |
| Explainability report | AI reasoning per masking decision |
| Compliance report | Control-by-control GDPR assessment |

---

## 4. User Stories by GDPR Article

### 4.1 Access to Personal Data (Art. 15)

**As an** auditor, **I want to** request access to personal data, **so that** I can verify GDPR compliance while sensitive fields are masked by AI.

**Acceptance Criteria:**
- AI identifies personal/sensitive fields (name, email, IBAN, SSN)
- Data is masked (e.g., `john.doe@email.com` → `j***@email.com`)
- Original data never exposed unless explicitly authorized
- Audit log records: who requested, what was masked, when shared

---

### 4.2 Data Minimization (Art. 5(1)(c))

**As an** auditor, **I want to** review datasets, **so that** I can verify only necessary data is collected.

**Acceptance Criteria:**
- AI classifies fields: **Required** / **Optional** / **Excessive**
- Excessive fields auto-masked or excluded
- Auditor sees data categories + masked samples only
- System flags minimization violations

---

### 4.3 Breach Investigation (Art. 33 & 34)

**As an** auditor, **I want to** review breach data, **so that** I can assess impact without exposing identities.

**Acceptance Criteria:**
- AI anonymizes affected individuals
- Dataset shows: record count, data categories
- Direct identifiers removed or tokenized
- Re-identification impossible from shared dataset

---

### 4.4 Third-Party Data Sharing (Art. 28)

**As an** auditor, **I want to** review data shared with processors, **so that** I can verify compliance.

**Acceptance Criteria:**
- AI detects personal data fields and sensitive categories (health, financial)
- Shared datasets masked or aggregated
- Auditor sees: sharing purpose, data categories, processor agreements

---

### 4.5 Data Retention (Art. 5(1)(e))

**As an** auditor, **I want to** review retained data, **so that** I can verify retention policies without accessing identifiable data.

**Acceptance Criteria:**
- AI masks identifiers in historical data
- Data grouped by retention period and expiry status
- Flags data exceeding retention period
- Masking is irreversible for the auditor

---

### 4.6 Right to Erasure (Art. 17)

**As an** auditor, **I want to** verify deletion requests are honored.

**Acceptance Criteria:**
- AI shows deletion logs and before/after states (masked)
- Residual data fully anonymized
- Auditor sees proof without accessing original identity

---

### 4.7 Automated Decision-Making (Art. 22)

**As an** auditor, **I want to** review AI-driven decisions, **so that** I can ensure fairness.

**Acceptance Criteria:**
- AI replaces identifiers with tokens
- Auditor sees: decision logic, input categories (not raw data)
- Explainability report generated without exposing identities

---

### 4.8 Cross-Border Transfers (Chapter V)

**As an** auditor, **I want to** review data transfers outside the EU.

**Acceptance Criteria:**
- AI masks identifiers and tags geographic metadata
- Auditor sees: destination country, legal mechanism (SCCs, adequacy, etc.)
- No raw personal data exposed

---

### 4.9 Logging & Accountability (Art. 5(2))

**As an** auditor, **I want to** review access logs, **so that** all access is controlled and masked.

**Acceptance Criteria:**
- Logs include: masking applied (yes/no + type), user role
- AI ensures logs contain no personal data
- Immutable audit trail maintained

---

### 4.10 Role-Based Access Control (Art. 32)

**As an** auditor, **I want to** validate that AI enforces masking based on role.

**Acceptance Criteria:**
- Role-based masking levels:
  - **Auditor** → fully masked
  - **DPO** → partially masked
  - **Admin** → full access (if justified)
- AI dynamically applies masking rules
- Unauthorized access attempts blocked and logged

---

## 5. AI Agent Capabilities

| Capability | Description |
|------------|-------------|
| **PII Detection** | NER + pattern matching |
| **Dynamic Masking** | Context-aware, role-based |
| **Pseudonymization** | Reversible tokenization for reproducibility |
| **Policy Enforcement** | Driven by role + purpose + legal basis |
| **Audit Logging** | Immutable trail with chain-of-thought explainability |
| **Re-identification Prevention** | Irreversible masking for auditor-facing outputs |

---

## 6. End-to-End Test Scenario

**Scenario:** Auditor requests a customer reimbursement dataset.

| Phase | Details |
|-------|---------|
| **Input** | Full dataset with names, emails, IBANs |
| **AI Processing** | Detect PII → classify fields → apply masking rules |
| **Output** | Masked dataset + data categories summary + audit log |
| **Validation** | ✅ No raw PII exposed · ✅ Masking consistent · ✅ Logs complete |

---

## 7. PDCA Roadmap

| Phase | Hackathon | Activities |
|-------|-----------|------------|
| **Plan** | H2 (now) | Design agent, define user stories, map GDPR controls |
| **Do** | H2 (now) | Build PII detector + masking engine prototype |
| **Check** | Between H2–H3 | Validate in private adoption at own organization |
| **Act** | H3 | Share learnings, improvements, and control mappings |

---

## 8. Future Extensions

- Convert user stories to **Gherkin** (Given/When/Then) test cases
- Map controls to **ISO 27001 / NIS2 / DORA**
- Build automated **API-level test scripts**
- Integrate with existing GRC tooling

---

## 9. Security Reminders

- ⛔ Never commit real audit evidence, personal data, or credentials
- 🔑 Use environment variables for API keys
- 🧪 Use synthetic/anonymized data for all testing
- 📋 Review `regulatory/guardrails/allowed-commands.md` before running agent scripts
