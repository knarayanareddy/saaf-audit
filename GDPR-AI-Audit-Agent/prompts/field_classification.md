# Field Classification Prompt

Given a set of detected PII fields and an audit purpose, classify each field as:

- **Required**: Necessary for the stated audit purpose
- **Optional**: Useful but not essential — can be masked without impacting the audit
- **Excessive**: Not relevant to the purpose — must be masked or removed (Art. 5(1)(c) data minimization)

## Rules

1. Apply the principle of data minimization (Art. 5(1)(c))
2. Special category data (Art. 9) is always Excessive unless a specific exemption applies
3. Financial identifiers are Required only for financial audits
4. Names are typically Optional — use pseudonyms where possible

## Output Format

```json
{
    "classifications": [
        {"field_name": "...", "classification": "required|optional|excessive", "justification": "..."}
    ]
}
```
