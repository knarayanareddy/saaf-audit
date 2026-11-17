# ISO/IEC 27001:2022 — Clause 8 structure reference

The main body of ISO/IEC 27001:2022 contains 10 numbered clauses (0-10). Clause 8 is titled **"Operation"** and has a very small structure in the main body:

- **8.1 Operational planning and control** — only one sub-clause exists here in the main body.
- **8.2 Information security risk assessment** — performs risk assessments at planned intervals.
- **8.3 Information security risk treatment** — implements the risk treatment plan.

**There is NO clause 8.9 and NO clause 8.9.4 in ISO/IEC 27001:2022.** Claims that cite "ISO 27001 clause 8.9.4" or similar deep-nested main-body clauses are factually wrong — these clause numbers do not exist in the standard.

Specific security controls live in **Annex A** of ISO/IEC 27001:2022, which has its own numbering (A.5 through A.8). For example:
- A.5.* — Organizational controls
- A.6.* — People controls
- A.7.* — Physical controls
- A.8.* — Technological controls (including A.8.8 Vulnerability management, A.8.15 Logging, A.8.24 Cryptography, etc.)

Auditors citing a specific technical control should reference the Annex A clause (e.g. "Annex A.8.8"), not a fabricated deep-main-body clause (e.g. "clause 8.9.4").

Incident reporting: ISO/IEC 27001 does not mandate a specific 24-hour notification window. Incident-reporting timeframes come from other frameworks — e.g. GDPR Article 33 (72 hours to supervisory authority), DORA (varies by severity), NIS2 (24 hours early warning, 72 hours initial notification).
