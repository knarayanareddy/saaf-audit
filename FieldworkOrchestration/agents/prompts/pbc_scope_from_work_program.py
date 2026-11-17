"""Prompts for the pbc_scope_from_work_program agent.

Consolidates a UC8 (Audit Work Program Agent) work program's per-step
``evidence`` fields into a deduplicated PBC (Prepared-By-Client) required-
documents list, with full traceability back to the risk/control/test step
that needs each item. This is the bridge between Track 1 (Planning —
UC7 RCM -> UC8 Work Program) and Track 2 (Fieldwork — this repo): UC8's
output is the authoritative input shape (see
Audit-Work-Program-Agent-UC-8-/README.md's "RCM input format" and its
generated outputs/*/work_program.json for the schema this was built
against).

Two phases, two prompt pairs, for cost and reliability — a single call
trying to atomize *and* cross-reference-deduplicate an entire work program
at once burns most of its token budget on thinking before writing any
output, and fails outright on a real-size program:

- EXTRACT (one call per control — batched via ``ClaudeClient.message_batch``,
  independent of each other): split each control's ``test_of_design`` /
  ``tests_of_effectiveness`` evidence strings — often several distinct
  items joined in one comma-separated sentence — into atomic items.
- CONSOLIDATE (one call, over the much smaller atomized list): group items
  that describe the same underlying document across controls, by index —
  the agent module builds the final traceability from those indices rather
  than trusting the model to re-transcribe risk/control IDs.
"""

EXTRACT_SYSTEM_PROMPT = (
    "You are an audit evidence extraction assistant. You are given ONE "
    "control from a work program: its Test of Design step and its Test(s) "
    "of Effectiveness, each with an \"evidence\" field — often a "
    "comma-separated string naming several distinct documents or datasets.\n\n"
    "Split every \"evidence\" field into its individual, atomic evidence "
    "items (one single document/dataset/screenshot type each). Phrase each "
    "as a short, clear, client-facing description — no internal jargon, no "
    "control IDs.\n\n"
    "Output ONLY a JSON array:\n"
    "[\n"
    "  {\"item\": \"<atomic evidence description>\", \"test_ref\": "
    "\"test_of_design | tests_of_effectiveness[<n>]\"}\n"
    "]\n\n"
    "One entry per atomic item — if a step's evidence field names 4 "
    "distinct documents, return 4 entries with that same test_ref. Do not "
    "merge or deduplicate here; that happens in a later step. Do not drop "
    "or invent items."
)

EXTRACT_USER_PROMPT_TEMPLATE = (
    "Risk: {risk_id} — {risk}\n"
    "Control: {control_id} — {control}\n\n"
    "Test of Design:\n"
    "  evidence: {tod_evidence}\n\n"
    "Tests of Effectiveness:\n"
    "{toe_evidence_list}\n\n"
    "Extract the atomic evidence items."
)

CONSOLIDATE_SYSTEM_PROMPT = (
    "You are an audit evidence-scoping assistant. You are given a numbered "
    "list of atomic evidence items already extracted from a work program — "
    "each a short document/dataset description. Multiple items may "
    "describe the same underlying document, worded differently (e.g. "
    "\"ERP journal entry listing\" and \"GL journal entry extract\" both "
    "mean the same journal entry export).\n\n"
    "Group the items that refer to the same underlying document/dataset "
    "together, and give each group a single, clean, client-facing "
    "description (no internal jargon, no control IDs) suitable for a PBC "
    "(Prepared-By-Client) request.\n\n"
    "Output ONLY a JSON object:\n"
    "{\n"
    '  "groups": [\n'
    '    {"description": "<clean, client-facing description>", '
    '"item_indices": [<int>, ...]}\n'
    "  ]\n"
    "}\n\n"
    "Every item index (0-based, matching the numbered list given) must "
    "appear in exactly one group — do not drop any, and do not put the "
    "same index in two groups. An item with nothing else like it still "
    "becomes its own single-item group."
)

CONSOLIDATE_USER_PROMPT_TEMPLATE = (
    "Atomic evidence items:\n{numbered_items}\n\n"
    "Group these into consolidated PBC requests."
)
