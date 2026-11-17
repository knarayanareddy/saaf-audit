"""
Goal:
- Reduce the full incident population to the subset relevant for the audit scope.

Input:
- Structured audit context object
- Validated and anonymized incident dataset

Output:
- Audit-relevant incident subset
- Inclusion/exclusion rationale per incident

Code:
- Filter by process, team, system, incident type, date window, and tags
- Apply deterministic inclusion/exclusion rules
- Keep track of why a record was included or excluded

AI:
- Haiku 4.5: perform high-volume relevance triage on incident descriptions
- Sonnet 4.6: assess relevance where the description is ambiguous or only indirectly linked to scope
"""
