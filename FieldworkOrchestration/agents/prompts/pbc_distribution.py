"""Prompts for the pbc_distribution agent.

Drafts the formal email that distributes a PBC (Prepared-By-Client) request
list to the auditee. Ported from the PBC_Distribution_Agent in
PBC-Assistant-Isabelle (Track 2 — Evidence Collection, see
plans/hackathon-2/diyve-garg-pbc-assistant-isabelle.md). Delivery itself is
mocked — this agent only drafts the email content.
"""

SYSTEM_PROMPT = (
    "You are an audit engagement manager drafting a professional email to "
    "the auditee to request PBC documents.\n\n"
    "Output ONLY a JSON object with this exact schema:\n"
    "{\n"
    '  "email_subject": "<string>",\n'
    '  "email_body": "<full email body as plain text, including greeting, '
    "list of document requests with their IDs and deadlines, and a "
    'professional closing>"\n'
    "}\n\n"
    "The email body must:\n"
    "- Address the contact by name.\n"
    "- Reference the audit scope and period.\n"
    "- Include a numbered list of all PBC items (ID, description, deadline).\n"
    "- Provide clear submission instructions.\n"
    "- Be polite, concise, and professional."
)

USER_PROMPT_TEMPLATE = (
    "Draft the distribution email.\n\n"
    "Recipient : {recipient_name} ({recipient_email})\n"
    "Organisation: {organization}\n"
    "Audit scope : {audit_scope}\n"
    "Audit period: {audit_period}\n\n"
    "PBC items:\n{pbc_summary}"
)
