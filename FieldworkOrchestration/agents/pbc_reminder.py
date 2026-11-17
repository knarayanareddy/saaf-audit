"""pbc_reminder agent — drafts reminder/escalation emails for outstanding PBC items.

Ported from Reminder_Agent in PBC-Assistant-Isabelle (Track 2 — Evidence
Collection). Takes the PBC list produced by ``pbc_creation``, the validation
results produced by ``pbc_validation``, and the auditee's contact details;
drafts one reminder email per outstanding (pending/overdue) item, marking
items more than 7 days overdue as escalated. Returns no messages (and makes
no Claude call) if nothing is outstanding.
"""

from __future__ import annotations

import json
from datetime import date

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.pbc_reminder import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.pbc_reminder import SETTINGS

_OUTSTANDING_STATUSES = ("overdue", "pending")
_ESCALATION_THRESHOLD_DAYS = 7


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_reminder agent and return its structured result.

    ``inputs`` keys:
        pbc_list (dict — the output of ``pbc_creation.run``),
        validation_status (dict — the output of ``pbc_validation.run``:
        ``{"results": [...]}``), auditee_contact (dict: name, email,
        organization), current_date (str, ISO date, optional — defaults to
        today).
    """
    pbc_list = inputs["pbc_list"]
    validation_status = inputs["validation_status"]
    current_date = inputs.get("current_date") or date.today().isoformat()

    desc_map = {item["id"]: item["description"] for item in pbc_list["items"]}
    deadline_map = {item["id"]: item["deadline"] for item in pbc_list["items"]}

    outstanding = [
        r for r in validation_status["results"] if r["status"] in _OUTSTANDING_STATUSES
    ]
    if not outstanding:
        return {"messages": [], "activity_log": f"No outstanding items on {current_date}"}

    today = date.fromisoformat(current_date)
    items_info = []
    for r in outstanding:
        pid = r["pbc_id"]
        deadline = date.fromisoformat(deadline_map[pid])
        days_overdue = (today - deadline).days if today > deadline else 0
        items_info.append(
            {
                "pbc_id": pid,
                "description": desc_map.get(pid, pid),
                "deadline": deadline_map[pid],
                "days_overdue": days_overdue,
                "status": r["status"],
            }
        )

    contact = inputs["auditee_contact"]
    user_prompt = USER_PROMPT_TEMPLATE.format(
        recipient_name=contact["name"],
        recipient_email=contact["email"],
        organization=contact["organization"],
        current_date=current_date,
        items_json=json.dumps(items_info, indent=2),
    )

    client = client or ClaudeClient()
    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="pbc_reminder",
    )
    data = extract_json_block(text_from_message(message))

    overdue_map = {i["pbc_id"]: i["days_overdue"] for i in items_info}
    messages = []
    for entry in data:
        pid = entry["pbc_id"]
        days = overdue_map.get(pid, 0)
        messages.append(
            {
                "pbc_id": pid,
                "description": desc_map.get(pid, pid),
                "days_overdue": days,
                "escalated": days > _ESCALATION_THRESHOLD_DAYS,
                "subject": entry["subject"],
                "body": entry["body"],
            }
        )

    escalated_count = sum(1 for m in messages if m["escalated"])
    activity_log = (
        f"{current_date} — Reminder_Agent sent {len(messages)} reminder(s). "
        f"Escalated: {escalated_count}."
    )

    return {"messages": messages, "activity_log": activity_log}
