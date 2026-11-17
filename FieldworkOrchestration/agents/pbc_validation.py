"""pbc_validation agent — computes each PBC item's basic delivery status.

Ported from Document_Validation_Agent in PBC-Assistant-Isabelle (Track 2 —
Evidence Collection), then simplified: the source (and an earlier version of
this port) asked Claude, per item with a delivered file, to judge whether
the filename looked appropriate — a single generic prompt that could not
reflect what actually matters for a specific risk/control (see
agents/pbc_document_check.py's docstring). That judgement has moved to a
dedicated, per-item flow: ``pbc_validation_prompt_proposal`` drafts a
tailored prompt, an auditor reviews/approves (or edits) it, and
``pbc_document_check`` runs the actual content-based check with it.

What's left here is purely deterministic — no Claude call at all:
- no file delivered yet -> "pending" or "overdue" (today vs. the deadline)
- a file has been delivered -> "received" (delivered, awaiting the
  auditor-driven detailed review above)

A caller that already has a ``pbc_document_check`` result for an item
should keep using that item's real status ("validated"/"received"/
"insufficient") instead of this function's "received" placeholder — this
agent only establishes the basic pending/overdue/received split, it does
not know about or override a detailed review that has already happened.
"""

from __future__ import annotations

from datetime import date


def run(inputs: dict, client: object | None = None) -> dict:
    """Run the pbc_validation agent and return its structured result.

    ``inputs`` keys:
        pbc_list (dict — the output of ``pbc_creation.run``),
        received_documents (list[dict] — each with ``filename`` and
        ``pbc_id``, the claimed PBC ID for that file),
        current_date (str, ISO date, optional — defaults to today).

    ``client`` is accepted (and ignored) only to keep the same call shape
    every other agent uses — this one makes no Claude call.
    """
    pbc_list = inputs["pbc_list"]
    received_documents = inputs.get("received_documents", [])
    current_date = inputs.get("current_date") or date.today().isoformat()
    today = date.fromisoformat(current_date)

    filenames_by_pbc_id: dict[str, list[str]] = {}
    for doc in received_documents:
        filenames_by_pbc_id.setdefault(doc["pbc_id"], []).append(doc["filename"])

    results = []
    for item in pbc_list["items"]:
        filenames = filenames_by_pbc_id.get(item["id"])
        if not filenames:
            deadline = date.fromisoformat(item["deadline"])
            status = "overdue" if today > deadline else "pending"
            results.append({"pbc_id": item["id"], "status": status, "matched_file": None, "notes": ""})
        else:
            results.append(
                {
                    "pbc_id": item["id"],
                    "status": "received",
                    "matched_file": filenames[-1],
                    "notes": "Delivered; awaiting detailed review.",
                }
            )

    return {"results": results}
