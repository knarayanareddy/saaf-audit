"""pbc_scope_from_work_program agent — Track 1 -> Track 2 bridge.

Consolidates a UC8 (Audit Work Program Agent) work program into a
deduplicated PBC required-documents list, with traceability back to the
risk/control/test step that needs each item. This is the bridge between
Track 1 (Planning: UC7 RCM -> UC8 Work Program) and Track 2 (Fieldwork:
this repo) — see agents/prompts/pbc_scope_from_work_program.py for the
UC8 schema this was built against
(Audit-Work-Program-Agent-UC-8-/outputs*/work_program.json) and for why
this runs as two phases (cost and reliability on a real-size program).

The result's ``required_documents`` is meant to be passed straight into
``pbc_creation.run()`` / ``orchestrator.run_pbc_workflow()`` unchanged —
this agent does not call pbc_creation itself, to keep "what evidence do we
need" and "draft the PBC list" as separate concerns, same as
``pbc_intake``.
"""

from __future__ import annotations

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.pbc_scope_from_work_program import (
    CONSOLIDATE_SYSTEM_PROMPT,
    CONSOLIDATE_USER_PROMPT_TEMPLATE,
    EXTRACT_SYSTEM_PROMPT,
    EXTRACT_USER_PROMPT_TEMPLATE,
)
from agents.settings.pbc_scope_from_work_program import CONSOLIDATE_SETTINGS, EXTRACT_SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_scope_from_work_program agent and return its structured result.

    ``inputs`` keys:
        work_program (list[dict] — the ``work_program`` array from a UC8
        run, e.g. ``json.load(open("work_program.json"))["work_program"]``).

    Returns ``{"required_documents": [...], "traceability": [...]}`` — same
    length, same order. A caller that feeds ``required_documents`` into
    ``pbc_creation.run()`` (which assigns PBC-001, PBC-002, ... in the
    order given) can zip the two positionally to recover which
    risk/control/test step each PBC item supports — see
    ``orchestrator.control_coverage`` for that join. This is a best-effort
    mapping, not a hard guarantee: it relies on ``pbc_creation``'s
    documented sequential-ID-assignment behaviour rather than an explicit
    reference id round-tripped through it.
    """
    client = client or ClaudeClient()
    work_program = inputs["work_program"]

    atomic_items = _extract_atomic_items(work_program, client)
    return _consolidate(atomic_items, client)


def _extract_atomic_items(work_program: list[dict], client: ClaudeClient) -> list[dict]:
    """Phase 1: one call per control, splitting evidence strings into atoms.

    Uses ``ClaudeClient.message_many`` — fast individual calls for a small
    work program, batched (~half the per-token cost) once there are enough
    controls that the wait is worth it; see that method's docstring for why
    batching isn't simply always-on.

    Returns a flat list of ``{item, risk_id, control_id, test_ref}`` dicts
    across every control, in a stable order (controls in input order, then
    the order each control's own extraction call returned its items).
    """
    requests = [
        {
            "prompt": EXTRACT_USER_PROMPT_TEMPLATE.format(
                risk_id=control["risk_id"],
                risk=control["risk"],
                control_id=control["control_id"],
                control=control["control"],
                tod_evidence=control["test_of_design"]["evidence"],
                toe_evidence_list="\n".join(
                    f"  [{i}] evidence: {toe['evidence']}"
                    for i, toe in enumerate(control.get("tests_of_effectiveness", []))
                ),
            ),
            "system": EXTRACT_SYSTEM_PROMPT,
            "model": EXTRACT_SETTINGS["model"],
            "max_tokens": EXTRACT_SETTINGS["max_tokens"],
            "thinking": EXTRACT_SETTINGS["thinking"],
            "agent": "pbc_scope_from_work_program:extract",
        }
        for control in work_program
    ]

    messages = client.message_many(requests)

    atomic_items: list[dict] = []
    for control, message in zip(work_program, messages):
        try:
            items = extract_json_block(text_from_message(message))
        except ValueError:
            # A malformed/truncated response for this one control must not
            # crash the whole work program — and evidence must not be
            # silently dropped either. Fall back to one un-split item per
            # test step (the raw evidence string, not atomized) so nothing
            # is lost; it will just consolidate less finely for this control.
            items = _fallback_items(control)
        for item in items:
            atomic_items.append(
                {
                    "item": item["item"],
                    "risk_id": control["risk_id"],
                    "control_id": control["control_id"],
                    "test_ref": item["test_ref"],
                }
            )
    return atomic_items


def _fallback_items(control: dict) -> list[dict]:
    """One un-split item per test step, used when a control's extraction call
    couldn't be parsed — the raw ``evidence`` string stands in for the atoms
    it would otherwise have been split into."""
    items = [{"item": control["test_of_design"]["evidence"], "test_ref": "test_of_design"}]
    for i, toe in enumerate(control.get("tests_of_effectiveness", [])):
        items.append({"item": toe["evidence"], "test_ref": f"tests_of_effectiveness[{i}]"})
    return items


def _consolidate(atomic_items: list[dict], client: ClaudeClient) -> dict:
    """Phase 2: group the atomized items by which underlying document they are.

    The model returns groups as *indices* into ``atomic_items``, not
    re-transcribed risk/control IDs — traceability is built from the
    already-known tags at those indices, so a model transcription slip
    can't silently corrupt a control_id.
    """
    numbered_items = "\n".join(f"[{i}] {ai['item']}" for i, ai in enumerate(atomic_items))
    user_prompt = CONSOLIDATE_USER_PROMPT_TEMPLATE.format(numbered_items=numbered_items)

    message = client.message(
        user_prompt,
        system=CONSOLIDATE_SYSTEM_PROMPT,
        model=CONSOLIDATE_SETTINGS["model"],
        max_tokens=CONSOLIDATE_SETTINGS["max_tokens"],
        thinking=CONSOLIDATE_SETTINGS["thinking"],
        agent="pbc_scope_from_work_program",
    )
    try:
        data = extract_json_block(text_from_message(message))
    except ValueError:
        # A malformed/truncated response here must not lose every item
        # extracted so far — fall back to one PBC item per atomic item,
        # unmerged (no cross-control deduplication), rather than crashing.
        data = {"groups": [{"description": ai["item"], "item_indices": [i]} for i, ai in enumerate(atomic_items)]}

    required_documents = []
    traceability = []
    for group in data["groups"]:
        required_documents.append(group["description"])
        sources = [
            {
                "risk_id": atomic_items[i]["risk_id"],
                "control_id": atomic_items[i]["control_id"],
                "test_ref": atomic_items[i]["test_ref"],
            }
            for i in group["item_indices"]
        ]
        traceability.append({"document": group["description"], "sources": sources})

    return {"required_documents": required_documents, "traceability": traceability}
