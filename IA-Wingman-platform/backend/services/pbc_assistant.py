"""PBC ("Isabelle") assistant — Prepared-by-Client workflow on top of the DRL.

Ported and trimmed from the SAAF `PBC-Assistant-Isabelle` hackathon workflow and
adapted to the IA Wingman doctrine:

- `compute_dashboard` is DETERMINISTIC (pure Python, no AI): status counts,
  completion %, and derived overdue detection. Free.
- `draft_distribution_email`, `draft_reminders`, and `validate_document` are the
  opt-in AI steps (one `run_agent_to_json` call each). They draft text or judge a
  document — nothing is ever sent. Untrusted document text is fenced via
  `prompt_safety.wrap_untrusted`, with the task/JSON instruction placed AFTER the
  fenced block (recency).

Statuses stay the DRL's own (not_requested | requested | received | not_needed);
"overdue" is derived, never a stored status. Document validation is a per-item
result, not a status.
"""

from __future__ import annotations

from datetime import date

from services.ai_service import run_agent_to_json
from services.prompt_safety import safe_label, wrap_untrusted
from services.retrieval import retrieve

AGENT_TYPE = "pbc_assistant"
PROVENANCE_SOURCE = "pbc_assistant"

# DRL statuses that mean the item is still outstanding (can go overdue).
_OUTSTANDING = ("not_requested", "requested")
_ESCALATION_DAYS = 7
_MAX_DOC_CHARS = 40_000


# ── Deterministic dashboard ──────────────────────────────────────────────────

def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _days_overdue(deadline: str | None, today: date) -> int:
    d = _parse_date(deadline)
    if d is None or today <= d:
        return 0
    return (today - d).days


def compute_dashboard(items: list[dict], today: date | None = None) -> dict:
    """Deterministic PBC status roll-up. Pure function, no I/O, no AI.

    An item is *overdue* when it is still outstanding and its deadline has
    passed. `completion_pct` = received / total * 100.
    """
    if today is None:
        today = date.today()

    total = len(items)
    received = requested = not_requested = not_needed = 0
    overdue: list[dict] = []
    outstanding: list[dict] = []

    for it in items:
        status = (it.get("status") or "not_requested").lower()
        if status == "received":
            received += 1
        elif status == "requested":
            requested += 1
        elif status == "not_needed":
            not_needed += 1
        else:
            not_requested += 1

        if status in _OUTSTANDING:
            days = _days_overdue(it.get("deadline"), today)
            ref = {
                "id": it.get("id"),
                "document": it.get("document"),
                "deadline": it.get("deadline"),
                "requested_from": it.get("requested_from"),
                "days_overdue": days,
            }
            outstanding.append(ref)
            if days > 0:
                overdue.append(ref)

    # Total that still needs a decision/document (everything except not_needed).
    in_scope = total - not_needed
    completion_pct = round((received / in_scope) * 100, 1) if in_scope else 0.0

    return {
        "total_items": total,
        "received_count": received,
        "requested_count": requested,
        "not_requested_count": not_requested,
        "not_needed_count": not_needed,
        "outstanding_count": len(outstanding),
        "overdue_count": len(overdue),
        "completion_pct": completion_pct,
        "outstanding": sorted(outstanding, key=lambda r: -r["days_overdue"]),
        "overdue": sorted(overdue, key=lambda r: -r["days_overdue"]),
        "as_of": today.isoformat(),
    }


def _contact_line(contact: dict | None) -> str:
    if not contact:
        return "Recipient: the auditee (address the relevant document owner generically)."
    name = safe_label(contact.get("name")) if contact.get("name") else "the auditee"
    email = safe_label(contact.get("email")) if contact.get("email") else "(no email on file)"
    org = safe_label(contact.get("organization")) if contact.get("organization") else ""
    return f"Recipient: {name} <{email}>" + (f" — {org}" if org else "")


def _items_summary(items: list[dict]) -> str:
    lines = []
    for it in items:
        if (it.get("status") or "").lower() == "not_needed":
            continue
        dl = it.get("deadline") or "no deadline set"
        lines.append(f"- {it.get('id')}: {it.get('document')} "
                     f"(from {it.get('requested_from') or 'auditee'}; deadline {dl})")
    return "\n".join(lines)


# ── AI: distribution email (opt-in) ──────────────────────────────────────────

async def draft_distribution_email(engagement, items: list[dict], contact: dict | None) -> dict:
    """Draft the PBC request email to the auditee. Modelled — never sent."""
    system = (
        "You are an internal-audit engagement manager drafting a professional email to the auditee "
        "requesting Prepared-by-Client (PBC) documents. Return ONLY a JSON object: "
        '{"subject": "<string>", "body": "<full plain-text email: greeting, reference to the audit '
        "scope/period, a numbered list of the requested documents with their deadlines, submission "
        'instructions, and a professional closing>"}. Be polite, concise and specific.'
    )
    user = (
        f"Audit: {safe_label(engagement.name)} ({safe_label(engagement.audit_code) or '—'})\n"
        f"Scope period: {safe_label(engagement.scope_period) or 'not specified'}\n"
        f"{_contact_line(contact)}\n\n"
        f"PBC items:\n{_items_summary(items)}\n\n"
        "Draft the distribution email now."
    )
    result = await run_agent_to_json(system_prompt=system, user_prompt=user, max_tokens=2000)
    if isinstance(result, dict):
        return {"subject": result.get("subject", ""), "body": result.get("body", "")}
    return {"subject": "", "body": ""}


# ── AI: reminders for outstanding items (opt-in) ─────────────────────────────

async def draft_reminders(engagement, items: list[dict], contact: dict | None,
                          today: date | None = None) -> dict:
    """Draft reminder messages for overdue / at-risk PBC items.

    The set of outstanding items and their days-overdue are computed
    deterministically; the AI only writes the message prose.
    """
    if today is None:
        today = date.today()

    dash = compute_dashboard(items, today)
    outstanding = dash["outstanding"]
    if not outstanding:
        return {"messages": [], "activity_log": f"{today.isoformat()} — no outstanding items; no reminders needed."}

    by_id = {it.get("id"): it for it in items}
    lines = []
    for r in outstanding:
        it = by_id.get(r["id"], {})
        state = "OVERDUE" if r["days_overdue"] > 0 else "at risk (deadline approaching)"
        lines.append(
            f"- {r['id']}: {it.get('document')} — deadline {r.get('deadline') or 'none'}, "
            f"{r['days_overdue']} days overdue ({state})"
        )

    system = (
        "You are an internal-audit engagement manager writing reminder emails for outstanding PBC "
        "documents. Return ONLY a JSON array; one object per item: "
        '{"item_id": "<id>", "subject": "<subject>", "body": "<professional, firm-but-polite email '
        'body naming the document, its deadline and how many days overdue, requesting prompt '
        f'submission>"}}. If an item is more than {_ESCALATION_DAYS} days overdue, escalate the tone and '
        "mark the subject as ESCALATED."
    )
    user = (
        f"Audit: {safe_label(engagement.name)}\n"
        f"{_contact_line(contact)}\n"
        f"Today: {today.isoformat()}\n\n"
        f"Outstanding items:\n" + "\n".join(lines) + "\n\n"
        "Write one reminder per item."
    )
    result = await run_agent_to_json(system_prompt=system, user_prompt=user, max_tokens=2500)

    overdue_map = {r["id"]: r["days_overdue"] for r in outstanding}
    messages = []
    if isinstance(result, list):
        for entry in result:
            if not isinstance(entry, dict):
                continue
            iid = entry.get("item_id")
            days = overdue_map.get(iid, 0)
            messages.append({
                "item_id": iid,
                "document": (by_id.get(iid) or {}).get("document"),
                "days_overdue": days,
                "escalated": days > _ESCALATION_DAYS,
                "subject": entry.get("subject", ""),
                "body": entry.get("body", ""),
            })
    activity_log = (
        f"{today.isoformat()} — drafted {len(messages)} reminder(s); "
        f"escalated {sum(1 for m in messages if m['escalated'])}. Not sent (modelled)."
    )
    return {"messages": messages, "activity_log": activity_log}


# ── AI: validate a received document against a PBC item (opt-in) ──────────────

async def validate_document(item: dict, uploaded_doc) -> dict:
    """Judge whether an uploaded document satisfies a specific PBC request.

    Reuses the document's already-extracted text; fences it as untrusted.

    The PBC request itself is the query: asked for "the UBO register extract for
    Q1", what matters is the part of a 60-page submission that carries it, not
    the part that happens to come first.
    """
    found = retrieve(
        [(uploaded_doc.id, uploaded_doc.original_filename, uploaded_doc.extracted_text)],
        f"{item.get('document') or ''} {item.get('description') or ''}",
        budget_chars=_MAX_DOC_CHARS,
    )
    text = found.block
    if not text.strip():
        return {
            "conclusion": "insufficient",
            "summary": "No extractable text — the document may be empty, scanned, or unreadable.",
            "key_information": [], "potential_issues": ["No text could be extracted."],
            "missing_information": [], "comments": "Review the document manually.",
            "document_id": uploaded_doc.id, "filename": uploaded_doc.original_filename,
        }

    fenced = wrap_untrusted(text, source_label=uploaded_doc.original_filename)
    coverage_note = ("" if found.coverage.complete else
                     f"\nNote: {found.coverage.sentence()}. Judge only what you can see, and say so "
                     f"when something you would expect was simply not in the passages shown.")
    system = (
        "You are a senior audit manager reviewing a document submitted for a Prepared-by-Client (PBC) "
        "request. Decide whether it satisfies the request. Return ONLY a JSON object with this schema: "
        '{"conclusion": "sufficient | partially sufficient | insufficient", '
        '"summary": "<2-4 sentences>", "key_information": ["<figure/date/entity found>"], '
        '"potential_issues": ["<concern>"], "missing_information": ["<expected but absent>"], '
        '"comments": "<3-5 sentences of professional commentary>"}. '
        "Reference actual figures/dates/entities where possible. If the text is empty or errored, "
        "conclude 'insufficient'."
    )
    user = (
        f"PBC request: {safe_label(item.get('document'))} — {safe_label(item.get('description'))}\n"
        f"Submitted file: {safe_label(uploaded_doc.original_filename)}\n\n"
        f"{fenced}{coverage_note}\n\n"
        "Produce your validation as the JSON object described above."
    )
    result = await run_agent_to_json(system_prompt=system, user_prompt=user, max_tokens=1800)

    valid = {"sufficient", "partially sufficient", "insufficient"}
    if not isinstance(result, dict):
        result = {}
    conclusion = result.get("conclusion")
    if conclusion not in valid:
        conclusion = "insufficient"
    return {
        "conclusion": conclusion,
        "summary": result.get("summary", ""),
        "key_information": result.get("key_information", []) or [],
        "potential_issues": result.get("potential_issues", []) or [],
        "missing_information": result.get("missing_information", []) or [],
        "comments": result.get("comments", ""),
        "document_id": uploaded_doc.id,
        "filename": uploaded_doc.original_filename,
    }
