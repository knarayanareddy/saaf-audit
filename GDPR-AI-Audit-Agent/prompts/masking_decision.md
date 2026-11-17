# Masking Decision Prompt

Determine the appropriate masking method for each PII field based on:

1. **Role** of the requester (Auditor, DPO, Admin)
2. **Legal basis** for processing
3. **Field classification** (Required, Optional, Excessive)

## Masking Rules

| Role | Required Fields | Optional Fields | Excessive Fields |
|------|----------------|-----------------|------------------|
| Auditor | Pseudonymize | Fully mask | Fully mask |
| DPO | Partially mask | Partially mask | Fully mask |
| Admin | Show (with justification) | Partially mask | Fully mask |

## Output Format

```json
{
    "decisions": [
        {"field_name": "...", "method": "redact|pseudonymize|partial|none", "justification": "..."}
    ]
}
```
