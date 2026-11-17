# Document Validity Rules

Task: for each vendor document, extract the date fields below and judge whether the document is recent enough to rely on. Do not assess compliance in this step.

## Document types and date to extract (ISO 8601, YYYY-MM-DD; "unknown" if not stated; never infer)

| Document type | Date to extract | Standard |
|---|---|---|
| SOC 2 Type II | audit period end | AICPA AT-C 320 / IAASB ISAE 3402 |
| SOC 2 Type I | report date | AICPA AT-C 320 |
| ISO 27001 / ISO 9001 certificate | certificate expiry ("Valid until") and last surveillance audit date | IAF MD 5 / ISO/IEC 17021-1 |
| DORA questionnaire | completion or last updated date | EBA/GL/2022/09 ICT TPRM Guidelines |
| Vendor questionnaire | completion or last updated date | ISACA Third-Party Risk Management |
| Other | completion date, if any | General due diligence standard |

## Thresholds (age = assessment date minus extracted date, in days)

SOC 2 Type I and II, DORA questionnaire, vendor questionnaire, other:
- date unknown: Partial, Low. Evidence: the date could not be extracted, currency cannot be confirmed. Recommendation: confirm the date and the 12-month reliance window.
- age > 365 days: Gap, High. Recommendation: request an updated document dated within the last 12 months.
- age <= 365 days: Compliant, Info. Recommendation: No action required.

ISO 27001 / ISO 9001 certificate expiry:
- expiry unknown: Partial, Low. Recommendation: provide the certificate with a clear Valid Until date.
- expiry before assessment date: Gap, High. State how many days ago it expired. Recommendation: obtain a valid certificate; vendor must recertify or renew.
- expiry within 90 days: Partial, Medium. State days remaining. Recommendation: confirm recertification has started.
- expiry later than 90 days: Compliant, Info. State days remaining.

ISO surveillance audit (only if a surveillance date is stated):
- more than 365 days ago: Gap, High, control ID ISO-SURVEILLANCE, per IAF MD 5 surveillance audits must be annual.
- otherwise: no finding.

## Finding fields

framework: Document Validity. Control IDs: SOC 2 Type II = SOC2-PERIOD; SOC 2 Type I = SOC2-TYPE1-DATE; ISO certificates = ISO-CERT-EXPIRY; DORA questionnaire = DORA-Q-CURRENCY; vendor questionnaire = VENDOR-Q-CURRENCY; other = DOC-CURRENCY.

Calculate day counts carefully and show the two dates used in the evidence text.
