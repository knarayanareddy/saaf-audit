"""
Five PBC Audit Workflow agents.  Each agent calls Claude (claude-opus-4-6)
and returns a typed result object.

Email delivery is mocked: the generated email is printed to the console
instead of sent via SMTP.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, date
from typing import List

import anthropic

from .models import (
    AuditeeContact,
    DashboardReport,
    DeliveryStatus,
    PBCItem,
    PBCList,
    ReceivedDocument,
    ReminderLog,
    ReminderMessage,
    ValidationResult,
    ValidationStatus,
    OVERDUE,
    PENDING,
    RECEIVED,
    VALIDATED,
)

# ── Shared client ────────────────────────────────────────────────────────────

_client = anthropic.Anthropic()
MODEL = "claude-opus-4-6"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stream_text(system: str, user: str, max_tokens: int = 4096) -> str:
    """Stream a Claude response and return the full text."""
    full_text = ""
    with _client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text
    print()  # newline after streaming
    return full_text


def _extract_json(text: str) -> dict | list:
    """Extract the first JSON block from a text response."""
    # Try fenced code block first
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    # Fall back to raw JSON detection
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No JSON found in response:\n{text}")


# ── Agent 1 – PBC_Creation_Agent ─────────────────────────────────────────────

def run_pbc_creation_agent(
    audit_scope: str,
    audit_period: str,
    required_documents: List[str],
) -> PBCList:
    """
    Creates a structured PBC request list.

    Returns a PBCList with IDs, descriptions, and deadlines assigned.
    """
    print("\n" + "=" * 60)
    print("AGENT 1 — PBC_Creation_Agent")
    print("=" * 60)

    system = (
        "You are an experienced audit manager specialising in Prepared By Client "
        "(PBC) request lists. Your task is to produce a structured, professional "
        "PBC list as a JSON object.\n\n"
        "Output ONLY a JSON object with this exact schema (no prose before/after):\n"
        "{\n"
        '  "audit_scope": "<string>",\n'
        '  "audit_period": "<string>",\n'
        '  "items": [\n'
        '    {\n'
        '      "id": "PBC-001",\n'
        '      "description": "<clear, actionable description>",\n'
        '      "deadline": "YYYY-MM-DD",\n'
        '      "status": "pending"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Assign sequential IDs: PBC-001, PBC-002, …\n"
        "- Set deadlines 14 days from today for standard items, 7 days for urgent.\n"
        "- Descriptions must be actionable (e.g. 'Provide signed trial balance as at …').\n"
        "- All statuses start as 'pending'."
    )

    today = date.today().isoformat()
    user = (
        f"Create a PBC list for the following audit engagement.\n\n"
        f"Audit scope : {audit_scope}\n"
        f"Audit period: {audit_period}\n"
        f"Today's date: {today}\n\n"
        f"Required documents:\n"
        + "\n".join(f"- {doc}" for doc in required_documents)
    )

    raw = _stream_text(system, user)
    data = _extract_json(raw)
    pbc_list = PBCList.from_dict(data)

    print(f"\n[PBC_Creation_Agent] Created {len(pbc_list.items)} PBC items.")
    return pbc_list


# ── Agent 2 – PBC_Distribution_Agent ─────────────────────────────────────────

def run_pbc_distribution_agent(
    pbc_list: PBCList,
    auditee_contact: AuditeeContact,
) -> DeliveryStatus:
    """
    Drafts a formal email with the PBC list attached and 'sends' it
    (prints to console).

    Returns a DeliveryStatus with the generated email content.
    """
    print("\n" + "=" * 60)
    print("AGENT 2 — PBC_Distribution_Agent")
    print("=" * 60)

    system = (
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

    pbc_summary = "\n".join(
        f"  {item.id}: {item.description} (deadline: {item.deadline})"
        for item in pbc_list.items
    )

    user = (
        f"Draft the distribution email.\n\n"
        f"Recipient : {auditee_contact.name} ({auditee_contact.email})\n"
        f"Organisation: {auditee_contact.organization}\n"
        f"Audit scope : {pbc_list.audit_scope}\n"
        f"Audit period: {pbc_list.audit_period}\n\n"
        f"PBC items:\n{pbc_summary}"
    )

    raw = _stream_text(system, user)
    data = _extract_json(raw)

    sent_at = datetime.utcnow().isoformat() + "Z"
    status = DeliveryStatus(
        recipient_name=auditee_contact.name,
        recipient_email=auditee_contact.email,
        sent_at=sent_at,
        email_subject=data["email_subject"],
        email_body=data["email_body"],
        confirmed=True,  # mocked
    )

    # Mock delivery — print instead of SMTP send
    print("\n" + "-" * 60)
    print("📧  [MOCK EMAIL — not actually sent]")
    print(f"To     : {status.recipient_name} <{status.recipient_email}>")
    print(f"Subject: {status.email_subject}")
    print(f"Sent at: {status.sent_at}")
    print("-" * 60)
    print(status.email_body)
    print("-" * 60)
    print(f"\n[PBC_Distribution_Agent] Email drafted and logged at {sent_at}.")
    return status


# ── Agent 3 – Document_Validation_Agent ──────────────────────────────────────

def run_document_validation_agent(
    pbc_list: PBCList,
    received_documents: List[ReceivedDocument],
    current_date: str,
) -> ValidationStatus:
    """
    Validates received documents against the PBC list.

    Checks matching, completeness, and marks overdue items.
    Returns a ValidationStatus.
    """
    print("\n" + "=" * 60)
    print("AGENT 3 — Document_Validation_Agent")
    print("=" * 60)

    system = (
        "You are an audit document controller validating received files against "
        "a PBC request list.\n\n"
        "Output ONLY a JSON array.  Each element must follow this schema:\n"
        "[\n"
        "  {\n"
        '    "pbc_id": "PBC-001",\n'
        '    "status": "validated | received | pending | overdue",\n'
        '    "matched_file": "<filename or null>",\n'
        '    "notes": "<brief validation note>"\n'
        "  }\n"
        "]\n\n"
        "Status rules:\n"
        "- 'validated'  : file received AND filename is appropriate for the request.\n"
        "- 'received'   : file received but filename/format may need review.\n"
        "- 'overdue'    : no file received AND today's date is past the deadline.\n"
        "- 'pending'    : no file received AND deadline has not yet passed.\n\n"
        "Return one entry per PBC item."
    )

    pbc_json = json.dumps(
        [
            {"id": i.id, "description": i.description, "deadline": i.deadline}
            for i in pbc_list.items
        ],
        indent=2,
    )
    docs_json = json.dumps(
        [{"filename": d.filename, "claimed_pbc_id": d.pbc_id} for d in received_documents],
        indent=2,
    )

    user = (
        f"Validate the received documents against the PBC list.\n\n"
        f"Today's date: {current_date}\n\n"
        f"PBC list:\n{pbc_json}\n\n"
        f"Received documents:\n{docs_json}"
    )

    raw = _stream_text(system, user)
    data = _extract_json(raw)

    results = [
        ValidationResult(
            pbc_id=item["pbc_id"],
            status=item["status"],
            matched_file=item.get("matched_file"),
            notes=item.get("notes", ""),
        )
        for item in data
    ]

    v_status = ValidationStatus(results=results)
    print(f"\n[Document_Validation_Agent] Validated {len(results)} PBC items.")
    return v_status


# ── Agent 4 – Status_Dashboard_Agent ─────────────────────────────────────────

def run_status_dashboard_agent(
    pbc_list: PBCList,
    validation_status: ValidationStatus,
) -> DashboardReport:
    """
    Generates a completion dashboard and narrative summary.

    Returns a DashboardReport.
    """
    print("\n" + "=" * 60)
    print("AGENT 4 — Status_Dashboard_Agent")
    print("=" * 60)

    system = (
        "You are an audit status reporting analyst.  Given PBC validation results, "
        "produce a dashboard summary.\n\n"
        "Output ONLY a JSON object with this exact schema:\n"
        "{\n"
        '  "total_items": <int>,\n'
        '  "received_count": <int>,\n'
        '  "validated_count": <int>,\n'
        '  "pending_count": <int>,\n'
        '  "overdue_count": <int>,\n'
        '  "completion_percentage": <float, 0-100>,\n'
        '  "missing_items": ["PBC-002", …],\n'
        '  "summary_text": "<2-3 sentence narrative>"\n'
        "}\n\n"
        "completion_percentage = (validated + received) / total * 100.\n"
        "missing_items = all PBC IDs with status pending or overdue."
    )

    val_json = validation_status.to_json()
    user = (
        f"Generate the status dashboard.\n\n"
        f"Audit scope : {pbc_list.audit_scope}\n"
        f"Audit period: {pbc_list.audit_period}\n"
        f"Total PBC items: {len(pbc_list.items)}\n\n"
        f"Validation results:\n{val_json}"
    )

    raw = _stream_text(system, user)
    data = _extract_json(raw)

    report = DashboardReport(
        total_items=data["total_items"],
        received_count=data["received_count"],
        validated_count=data["validated_count"],
        pending_count=data["pending_count"],
        overdue_count=data["overdue_count"],
        completion_percentage=data["completion_percentage"],
        missing_items=data["missing_items"],
        summary_text=data["summary_text"],
    )

    # Pretty-print the dashboard
    print("\n" + "=" * 60)
    print("📊  PBC STATUS DASHBOARD")
    print("=" * 60)
    print(f"  Total items       : {report.total_items}")
    print(f"  Validated         : {report.validated_count}")
    print(f"  Received (review) : {report.received_count}")
    print(f"  Pending           : {report.pending_count}")
    print(f"  Overdue           : {report.overdue_count}")
    print(f"  Completion        : {report.completion_percentage:.1f}%")
    if report.missing_items:
        print(f"  Outstanding IDs   : {', '.join(report.missing_items)}")
    print(f"\n  {report.summary_text}")
    print("=" * 60)

    return report


# ── Agent 5 – Reminder_Agent ──────────────────────────────────────────────────

def run_reminder_agent(
    pbc_list: PBCList,
    validation_status: ValidationStatus,
    current_date: str,
    auditee_contact: AuditeeContact,
) -> ReminderLog:
    """
    Detects overdue items, generates reminder/escalation messages,
    and prints them to the console (mock send).

    Returns a ReminderLog.
    """
    print("\n" + "=" * 60)
    print("AGENT 5 — Reminder_Agent")
    print("=" * 60)

    # Build a lookup of PBC item descriptions
    desc_map = {item.id: item.description for item in pbc_list.items}
    deadline_map = {item.id: item.deadline for item in pbc_list.items}

    # Find outstanding items
    outstanding = [
        r for r in validation_status.results
        if r.status in (OVERDUE, PENDING)
    ]

    if not outstanding:
        print("[Reminder_Agent] No outstanding items — no reminders needed.")
        return ReminderLog(activity_log="No outstanding items on " + current_date)

    system = (
        "You are an audit engagement manager sending reminder emails for outstanding "
        "PBC documents.\n\n"
        "Output ONLY a JSON array.  Each element covers ONE outstanding PBC item:\n"
        "[\n"
        "  {\n"
        '    "pbc_id": "PBC-002",\n'
        '    "subject": "<email subject line>",\n'
        '    "body": "<full email body — professional, firm but polite>"\n'
        "  }\n"
        "]\n\n"
        "Rules:\n"
        "- If days_overdue > 7, mark as ESCALATED in the subject and escalate tone.\n"
        "- Address the contact by name.\n"
        "- State the specific document, its ID, original deadline, and days overdue.\n"
        "- Request immediate submission."
    )

    today = date.fromisoformat(current_date)
    items_info = []
    for r in outstanding:
        dl = date.fromisoformat(deadline_map[r.pbc_id])
        days_overdue = (today - dl).days if today > dl else 0
        items_info.append(
            {
                "pbc_id": r.pbc_id,
                "description": desc_map.get(r.pbc_id, r.pbc_id),
                "deadline": deadline_map[r.pbc_id],
                "days_overdue": days_overdue,
                "status": r.status,
            }
        )

    user = (
        f"Generate reminder emails for the following outstanding PBC items.\n\n"
        f"Recipient     : {auditee_contact.name} ({auditee_contact.email})\n"
        f"Organisation  : {auditee_contact.organization}\n"
        f"Today's date  : {current_date}\n\n"
        f"Outstanding items:\n{json.dumps(items_info, indent=2)}"
    )

    raw = _stream_text(system, user)
    data = _extract_json(raw)

    # Build days_overdue lookup from items_info
    overdue_map = {i["pbc_id"]: i["days_overdue"] for i in items_info}

    messages: list[ReminderMessage] = []
    for entry in data:
        pid = entry["pbc_id"]
        days = overdue_map.get(pid, 0)
        msg = ReminderMessage(
            pbc_id=pid,
            description=desc_map.get(pid, pid),
            days_overdue=days,
            escalated=days > 7,
            subject=entry["subject"],
            body=entry["body"],
        )
        messages.append(msg)

        # Mock send
        print("\n" + "-" * 60)
        flag = "🔴 [ESCALATED]" if msg.escalated else "🟡 [REMINDER]"
        print(f"{flag}  PBC ID: {msg.pbc_id}  |  {msg.days_overdue} days overdue")
        print(f"To     : {auditee_contact.name} <{auditee_contact.email}>")
        print(f"Subject: {msg.subject}")
        print("-" * 60)
        print(msg.body)

    activity_log = (
        f"{current_date} — Reminder_Agent sent {len(messages)} reminder(s). "
        f"Escalated: {sum(1 for m in messages if m.escalated)}."
    )

    log = ReminderLog(messages=messages, activity_log=activity_log)
    print(f"\n[Reminder_Agent] {activity_log}")
    return log
