"""pbc_creation agent — drafts a structured PBC (Prepared-By-Client) request list.

Ported from PBC_Creation_Agent in PBC-Assistant-Isabelle (Track 2 — Evidence
Collection). Takes an audit scope, period, and required document types, and
returns a PBC list with sequential IDs, actionable descriptions, and deadlines.

One Claude call per required document — not one call drafting the whole
list. Two reasons: correctness at scale (the earlier whole-list design
silently truncated its JSON response once a real required-documents list
reached real-work-program size, ~100 items via
``pbc_scope_from_work_program``) and cost (via ``ClaudeClient.message_many``,
a small number of documents gets fast individual calls; a large one gets
batched at ~half the per-token cost — see that method's docstring for why
the switch is threshold-based rather than always batching: the Batches API
trades latency for cost, a bad trade for a handful of interactive-feeling
calls). Per-item calls also make PBC-ID assignment a Python-side guarantee
instead of trusting the model to number sequentially in order.
"""

from __future__ import annotations

from datetime import date, timedelta

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.pbc_creation import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.pbc_creation import SETTINGS

_STANDARD_DEADLINE_DAYS = 14
_URGENT_DEADLINE_DAYS = 7


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_creation agent and return its structured result.

    ``inputs`` keys:
        audit_scope (str), audit_period (str), required_documents (list[str]),
        today (str, ISO date, optional — defaults to today).
    """
    client = client or ClaudeClient()
    today = inputs.get("today") or date.today().isoformat()
    required_documents = inputs["required_documents"]

    # The PBC id is decided here, before the call, not after — so it can tag
    # the call as ``item_ref`` (see AuditTrail.entries_for_item) and so
    # nothing downstream has to trust the model to number sequentially in
    # order.
    pbc_ids = [f"PBC-{i:03d}" for i in range(1, len(required_documents) + 1)]
    requests = [
        {
            "prompt": USER_PROMPT_TEMPLATE.format(
                audit_scope=inputs["audit_scope"],
                audit_period=inputs["audit_period"],
                today=today,
                document=document,
            ),
            "system": SYSTEM_PROMPT,
            "model": SETTINGS["model"],
            "max_tokens": SETTINGS["max_tokens"],
            "thinking": SETTINGS["thinking"],
            "agent": "pbc_creation",
            "item_ref": pbc_id,
        }
        for document, pbc_id in zip(required_documents, pbc_ids)
    ]

    messages = client.message_many(requests) if requests else []

    today_date = date.fromisoformat(today)
    items = []
    for pbc_id, message in zip(pbc_ids, messages):
        data = extract_json_block(text_from_message(message))
        deadline_days = (
            _URGENT_DEADLINE_DAYS if data.get("urgency") == "urgent" else _STANDARD_DEADLINE_DAYS
        )
        items.append(
            {
                "id": pbc_id,
                "description": data["description"],
                "deadline": (today_date + timedelta(days=deadline_days)).isoformat(),
                "status": "pending",
            }
        )

    return {
        "audit_scope": inputs["audit_scope"],
        "audit_period": inputs["audit_period"],
        "items": items,
    }
