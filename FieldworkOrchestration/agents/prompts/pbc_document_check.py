"""Prompts for the pbc_document_check agent.

Deliberately holds no fixed ``SYSTEM_PROMPT`` — the whole point of this
agent (see agents/pbc_document_check.py) is that the system prompt is
supplied by the caller at run time (typically the output of
``pbc_validation_prompt_proposal``, after an auditor has reviewed or edited
it), not a static module constant. ``DEFAULT_SYSTEM_PROMPT`` is a
reasonable generic fallback a caller can pass explicitly when no tailored
proposal exists yet (e.g. re-checking an item that predates this feature) —
the agent never substitutes it silently.
"""

USER_PROMPT_TEMPLATE = (
    "PBC request: {pbc_description}\n\n"
    "Document filename: {filename}\n"
    "Document content:\n{document_text}\n\n"
    "Assess this document against the request."
)

DEFAULT_SYSTEM_PROMPT = (
    "You are an audit document reviewer. Given a PBC (Prepared-By-Client) "
    "request and the content of a delivered document, assess whether the "
    "document satisfies the request.\n\n"
    "Output ONLY a JSON object: "
    '{"status": "validated | received | insufficient", "notes": '
    '"<specific, grounded explanation>"}. '
    "'validated' = the document clearly and fully satisfies the request. "
    "'received' = a relevant document was provided but has notable gaps or "
    "needs human judgement to confirm. 'insufficient' = the document does "
    "not satisfy the request at all (wrong document, empty, unrelated)."
)
