"""Prompts for the pbc_validation_prompt_proposal agent.

Drafts a tailored validation prompt for one specific PBC item — a "prompt
about writing a prompt": the output is a complete system prompt meant to be
reviewed/edited by an auditor and then handed to ``pbc_document_check`` to
actually run. A single generic validation prompt does not scale to the
range of controls/risks a real work program covers (this is the reason this
agent exists at all — see agents/pbc_document_check.py's docstring); this
agent's job is to work out, for one specific risk/control/request/document,
what actually needs to be checked.
"""

SYSTEM_PROMPT = (
    "You are an audit methodology assistant. Your job is to draft a "
    "complete, ready-to-use system prompt for a DIFFERENT AI agent whose "
    "job will be to check whether one specific delivered document "
    "satisfies one specific PBC (Prepared-By-Client) request — in the "
    "context of the risk and control it exists to support, if given.\n\n"
    "Tailor the validation instructions to what actually matters for THIS "
    "document: what should it contain, what would make it insufficient, "
    "what specific things a reviewer should check (dates, approvals, "
    "signatures, calculations, population completeness, whatever is "
    "relevant here) given the risk being mitigated and the planned audit "
    "work it needs to support. Do not draft a generic checklist — be "
    "concrete about this control.\n\n"
    "The system prompt you draft MUST end with exactly this JSON output "
    "schema instruction, verbatim:\n\n"
    "\"Output ONLY a JSON object: {\\\"status\\\": \\\"validated | received "
    "| insufficient\\\", \\\"notes\\\": \\\"<specific, grounded "
    "explanation>\\\"}. 'validated' = the document clearly and fully "
    "satisfies the request. 'received' = a relevant document was provided "
    "but has notable gaps or needs human judgement to confirm. "
    "'insufficient' = the document does not satisfy the request at all "
    "(wrong document, empty, unrelated).\"\n\n"
    "Output ONLY a JSON object:\n"
    "{\n"
    '  "proposed_prompt": "<the complete system prompt you drafted, ending '
    'with the JSON schema instruction above verbatim>",\n'
    '  "rationale": "<2-3 sentences: why this prompt is tailored the way '
    'it is for this specific risk/control/request>"\n'
    "}"
)

USER_PROMPT_TEMPLATE = (
    "PBC request: {pbc_description}\n\n"
    "{context_section}"
    "Document filename: {filename}\n"
    "Document excerpt (first part):\n{document_excerpt}\n\n"
    "Draft a tailored validation prompt for checking this document against "
    "this request."
)

CONTEXT_SECTION_TEMPLATE = (
    "Risk: {risk}\n"
    "Control: {control}\n"
    "Control objective: {control_objective}\n"
    "Planned audit work for this control:\n{planned_work}\n\n"
)
