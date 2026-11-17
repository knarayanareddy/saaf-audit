# Audit Domains and Frameworks

> **Source:** `SAAF Project Drive/Hand-out folder/Session 3 - Hackathon 2 (24-03-2026)/Domains.xlsx`  
> **Maintained by:** SAAF Project Organisation  
> **Purpose:** Reference taxonomy of 53 audit domains organized across 12 main categories, each with relevant frameworks. Used as input for the gap analysis (`plans/gap-analysis.md`) and plan scoping.

---

## Domain Taxonomy

### 1. IT Governance & Strategy

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| IT Governance Framework | Alignment of IT with business goals, IT strategy, investment decisions | COBIT, ISO 38500 |
| IT Risk Management | Identification, analysis, and mitigation of IT risks | ISO 31000, ISO 27005, NIST SP 800-30 |
| IT Resource Management | IT personnel, skills development, outsourcing | COBIT |
| Performance Measurement | IT KPIs, management reporting, benchmarking | ITIL, COBIT |

### 2. Information Security (Cyber)

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Information Security Policy | Presence, currency, completeness, adherence | ISO 27001, NIST CSF |
| Identity & Access Management (IAM) | Authorization matrix, passwords, MFA, user right reviews (GITC) | ISO 27002, NIST SP 800-63 |
| Network Security | Firewalls, IDS/IPS, network segmentation, VPN | NIST SP 800-53 |
| Physical Security | Data center access, clean desk/screen policies | ISO 27002 |
| Incident Management | Detection, response, reporting, post-incident evaluation | ISO 27035, NIST SP 800-61 |
| Vulnerability Management | Patch management, vulnerability scanning, penetration testing | NIST SP 800-40, CIS Controls |
| Cryptography & Encryption | Key management, data-at-rest and data-in-transit encryption | ISO 27002 |
| Security Awareness & Training | Awareness programs, phishing simulations | ISO 27002 |

### 3. IT Operations & Infrastructure

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Change Management (GITC) | Requesting, testing, approving, implementing IT changes | ITIL, COBIT |
| Patch Management | Timeliness and completeness of security patches | NIST SP 800-40 |
| Backup & Recovery | Backup schedules, storage, restoration testing (GITC) | ISO 27002 |
| Data Center Operations | Environmental controls, hardware monitoring, physical access | TIA-942 |
| Asset Management | IT asset inventory, license management, lifecycle | ISO 19770 |
| Problem & Incident Management (Ops) | Service disruptions, root cause analysis | ITIL |
| Capacity Management | CPU, memory, storage capacity planning | ITIL |
| Cloud Governance & Security | AWS/Azure/GCP, shared responsibility model | CSA CCM, ISO 27017 |

### 4. Systems & Software

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Software Development Life Cycle (SDLC) | Agile/Waterfall, requirements, testing, code review | ISO 12207, OWASP |
| Application Controls | Input/processing/output validations, error handling | ISAE 3402, AICPA SOC |
| Database Security & Management | Hardening, table-level access, audit logging | CIS Benchmarks |

### 5. Business Continuity & DR

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Business Continuity Management (BCM) | BIA, currency of BCP | ISO 22301 |
| Disaster Recovery (DR) | DR plans, RTO/RPO definitions, DR testing | ISO 27031 |

### 6. Third-Party & Vendor Risk

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Vendor Selection & Due Diligence | Security, financial stability, service capabilities | ISO 27001, COBIT |
| Service Level Agreements (SLA) | Monitoring and enforcing SLAs | ITIL |
| Third-Party Assurance (TPRM) | Review of SOC1/SOC2/ISAE 3402 from critical vendors | ISAE 3000, AICPA SOC |

### 7. Data & Privacy

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Privacy Governance | DPO role, data inventory, processing registers | GDPR |
| Data Lifecycle Management | Classification, storage, retention, archiving, disposal | ISO 27001 |
| GDPR Compliance | Data subject rights, DPIAs, breach notification | GDPR |
| Data Quality & Integrity | Accuracy, completeness, timeliness of critical data | DAMA-DMBOK |

### 8. Compliance & Regulatory

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| General Laws & Regulations | Local and international laws (SOx, HIPAA) | Regulatory frameworks |
| Industry-Specific Regulations | DORA (Financial Services), BIO (Government), NEN 7510 (Healthcare) | DORA, BIO, NEN 7510 |
| Sanctions & Export Controls | Trade restrictions, sanctioned party lists | OFAC, EU Sanctions |

### 9. Financial & Accounting

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Internal Control over Financial Reporting (ICOFR) | Key controls, financial close process | COSO, SOx |
| Procure-to-Pay (P2P) | Purchasing, invoices, payments, SoD | Internal Control |
| Order-to-Cash (O2C) | Sales orders, invoicing, accounts receivable | Internal Control |
| Treasury & Cash Management | Cash flow, bank reconciliation, FX risk | Internal Control |

### 10. Operational & Business

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Human Resources (HR) Security | Joiners/movers/leavers, background checks | ISO 27002, Internal Control |
| Inventory Management | Physical inventory, valuation, obsolete stock | Internal Control |
| Manufacturing & Production | Process efficiency, quality control, waste | ISO 9001 |
| Marketing & Sales | Advertising compliance, customer data | GDPR, Internal Control |

### 11. Projects & Programmes

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Project Governance | Initiation, budget, steering committee reporting | PRINCE2, PMBOK |
| Project Risk Management | Risk identification and mitigation in projects | ISO 31000 |
| Post-Implementation Review (PIR) | Evaluation of project goals and benefits after go-live | COBIT |

### 12. Emerging Technology

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| Artificial Intelligence (AI) Governance | Ethical use, data bias, explainability | EU AI Act, NIST AI RMF |
| AI Security | Adversarial ML, model attacks | OWASP for AI |
| Blockchain / Distributed Ledger | Smart contracts, private key management | Emerging frameworks |
| Internet of Things (IoT) Security | Connected devices, firmware, network segmentation | NIST IR 8228 |

---

## Specialized Audits

| Subcategory | Specific Focus | Frameworks |
|---|---|---|
| ESG / Sustainability Reporting | Non-financial KPIs (environmental, social, governance) | CSRD / GRI |
| Fraud Risk Assessment | Proactive identification of fraud risks | COSO Fraud Risk Management |
| Forensic Audit | Investigation of fraud allegations or financial irregularities | Forensic standards |

---

## Summary Statistics

- **Total domains:** 53
- **Main categories:** 12 + Specialized
- **See:** [`plans/gap-analysis.md`](../../plans/gap-analysis.md) for coverage mapping against existing SAAF plans
