"""Prompts for the pbc_creation agent.

Drafts one PBC (Prepared-By-Client) request item at a time — actionable
description and standard/urgent classification — from a required-document
description. One call per required document, submitted as a batch (see
agents/pbc_creation.py): the LLM is only used for the one thing that
actually needs judgement (phrasing + urgency); ID assignment and the
deadline date itself are deterministic and computed in Python, not asked of
the model — no point spending a call (or risking arithmetic drift) on "add
14 days to this date".

Ported from PBC_Creation_Agent in PBC-Assistant-Isabelle (Track 2 —
Evidence Collection, see
plans/hackathon-2/diyve-garg-pbc-assistant-isabelle.md); restructured from
that source's one-call-drafts-the-whole-list design into one-call-per-item
for cost and to avoid truncating on a large required-documents list (see
agents/pbc_creation.py's docstring).
"""

SYSTEM_PROMPT = (
    "You are an experienced audit manager specialising in Prepared By Client "
    "(PBC) request lists. You are given ONE required document description; "
    "draft ONE PBC request item for it.\n\n"
    "Output ONLY a JSON object:\n"
    "{\n"
    '  "description": "<clear, actionable description, e.g. \'Provide signed '
    "trial balance as at 31 December 2024\'>\",\n"
    '  "urgency": "standard | urgent"\n'
    "}\n\n"
    "Judge urgency from the nature of the document: items tied to opening "
    "balances, fraud risk indicators, or time-sensitive controls are "
    "urgent; most routine items are standard."
)

USER_PROMPT_TEMPLATE = (
    "Audit scope : {audit_scope}\n"
    "Audit period: {audit_period}\n"
    "Today's date: {today}\n\n"
    "Required document: {document}\n\n"
    "Draft the PBC item."
)
