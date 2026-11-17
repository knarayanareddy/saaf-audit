# Explainability Report Prompt

Generate a human-readable report explaining the AI's masking decisions for auditor review.

## Report Structure

1. **Summary**: Number of fields detected, masked, and their categories
2. **Per-field decisions**: For each PII field, explain why it was masked and how
3. **Legal basis**: Which GDPR articles justify the processing
4. **Compliance status**: Whether the output meets data minimization requirements

## Rules

- Never include raw PII values in the report
- Reference GDPR articles by number
- Use clear, non-technical language where possible
- Flag any fields where the AI's confidence was below 0.8
