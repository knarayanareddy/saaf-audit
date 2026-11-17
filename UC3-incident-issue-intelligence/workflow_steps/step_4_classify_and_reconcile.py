"""
Goal:
- Assign each relevant incident to a risk/control taxonomy with defensible output.

Input:
- Audit-relevant incident subset
- Risk taxonomy and control failure taxonomy

Output:
- Classified incident dataset
- Reconciled final classification per incident
- Classification rationale and audit trail

Code:
- Run rule-based classification for risk type, severity, and control failure mode
- Compare rule-based output with AI output
- Reconcile differences using confidence scores or decision rules
- Store final classification plus rationale/audit trail

AI:
- Sonnet 4.6: perform semantic classification on free-text descriptions
- Sonnet 4.6: infer likely control failure modes where wording is inconsistent
- Opus 4.7: act as second-level reviewer for difficult or disputed classifications
"""
