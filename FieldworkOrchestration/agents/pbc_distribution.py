"""pbc_distribution agent — drafts the PBC distribution email.

Ported from PBC_Distribution_Agent in PBC-Assistant-Isabelle (Track 2 —
Evidence Collection). Takes the PBC list produced by ``pbc_creation`` and the
auditee's contact details, and drafts a formal request email. Actual delivery
is mocked — this agent only produces the drafted content and a "sent"
timestamp; the orchestrator decides how (or whether) it is actually sent.
"""

from __future__ import annotations

from datetime import datetime

from agents.claude_init import ClaudeClient, extract_json_block, text_from_message
from agents.prompts.pbc_distribution import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.pbc_distribution import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the pbc_distribution agent and return its structured result.

    ``inputs`` keys:
        pbc_list (dict — the output of ``pbc_creation.run``: audit_scope,
        audit_period, items), auditee_contact (dict: name, email,
        organization).
    """
    client = client or ClaudeClient()

    pbc_list = inputs["pbc_list"]
    contact = inputs["auditee_contact"]
    pbc_summary = "\n".join(
        f"  {item['id']}: {item['description']} (deadline: {item['deadline']})"
        for item in pbc_list["items"]
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(
        recipient_name=contact["name"],
        recipient_email=contact["email"],
        organization=contact["organization"],
        audit_scope=pbc_list["audit_scope"],
        audit_period=pbc_list["audit_period"],
        pbc_summary=pbc_summary,
    )

    message = client.message(
        user_prompt,
        system=SYSTEM_PROMPT,
        model=SETTINGS["model"],
        max_tokens=SETTINGS["max_tokens"],
        thinking=SETTINGS["thinking"],
        agent="pbc_distribution",
    )

    data = extract_json_block(text_from_message(message))

    return {
        "recipient_name": contact["name"],
        "recipient_email": contact["email"],
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "email_subject": data["email_subject"],
        "email_body": data["email_body"],
        "confirmed": True,  # delivery is mocked — no real email is sent
    }
