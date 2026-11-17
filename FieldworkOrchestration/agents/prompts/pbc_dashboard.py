"""Prompts for the pbc_dashboard agent.

Turns PBC (Prepared-By-Client) validation results into a completion
dashboard and a short narrative summary. Ported from the
Status_Dashboard_Agent in PBC-Assistant-Isabelle (Track 2 — Evidence
Collection, see plans/hackathon-2/diyve-garg-pbc-assistant-isabelle.md).
"""

SYSTEM_PROMPT = (
    "You are an audit status reporting analyst.  Given PBC validation results, "
    "produce a dashboard summary.\n\n"
    "Output ONLY a JSON object with this exact schema:\n"
    "{\n"
    '  "total_items": <int>,\n'
    '  "received_count": <int>,\n'
    '  "validated_count": <int>,\n'
    '  "pending_count": <int>,\n'
    '  "overdue_count": <int>,\n'
    '  "completion_percentage": <float, 0-100>,\n'
    '  "missing_items": ["PBC-002", …],\n'
    '  "summary_text": "<2-3 sentence narrative>"\n'
    "}\n\n"
    "completion_percentage = (validated + received) / total * 100.\n"
    "missing_items = all PBC IDs with status pending or overdue."
)

USER_PROMPT_TEMPLATE = (
    "Generate the status dashboard.\n\n"
    "Audit scope : {audit_scope}\n"
    "Audit period: {audit_period}\n"
    "Total PBC items: {total_items}\n\n"
    "Validation results:\n{val_json}"
)
