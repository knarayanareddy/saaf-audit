# n8n-to-Claude Audit Workflow Migration

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

Several audit teams built automation workflows in n8n — a visual workflow automation tool — for tasks like evidence collection reminders, control testing triggers, and regulatory monitoring. n8n is approachable (visual, no-code) but has limitations: complex logic is painful to build visually, AI integration is shallow, and workflows are hard to test systematically.

Claude agents can replace n8n for most audit automation use cases with: shorter build time, better AI integration, full testability via Python unit tests, and more modular, reusable components. But teams have existing n8n workflows and need a migration path, not a greenfield rewrite.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Workflow Automation / Agent Infrastructure

**Applicable standards:**

- IIA IPPF — Standard 2010 (Planning), 2340 (Engagement Supervision)

**In scope:**

- Pattern for migrating n8n audit workflows to Claude agent equivalents
- Mapping of n8n node types to Claude agent constructs
- Migration template for 3 common audit workflow patterns: reminders, data collection, classification
- Side-by-side comparison: n8n workflow vs. Claude agent for same use case
- Testability: unit tests for Claude agent equivalent of each n8n workflow

**Out of scope:**

- Workflows that are genuinely better in n8n (simple HTTP triggers with no AI logic)
- n8n platform administration or deployment
- Non-audit workflows (IT ops, marketing automation, etc.)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Claude agent prompts for each migrated workflow type |
| **Tools** | `tools/scripts/audit-workflow-agent.py` — Claude-based replacement for n8n audit workflows |
| **Regulatory** | IIA 2340 (supervision) — Claude agent produces audit trail; n8n workflows often do not |
| **Outputs** | Python scripts + unit tests that replace n8n workflow JSON exports |

---

## 5. Prompts

### System prompt (draft — PBC reminder agent)

```
You are an audit evidence collection agent.
Your task is to send PBC (Provided By Client) reminders to auditees.
For each open PBC item:
1. Check if the due date has passed
2. Determine the appropriate escalation level (first reminder / second reminder / escalation to manager)
3. Draft a professional, concise reminder email
4. Log the reminder action (to, subject, escalation level, timestamp)

Never send aggressive or threatening language.
Always include the specific document/data requested and the original due date.
If escalating to manager, add: "This request has been outstanding for [N] days."
```

### Example user prompts

**Prompt 1 — n8n migration assessment:**
```
I have an n8n workflow that:
1. Triggers daily at 09:00
2. Reads a Google Sheet of open PBC items
3. Filters items where due date < today
4. Sends a reminder email via Gmail
5. Updates the Google Sheet status column

How do I migrate this to a Claude agent? What are the equivalent Claude components?
```

**Prompt 2 — Claude agent equivalent:**
```
Read the open PBC items from the attached CSV.
Today is {today}.
For each overdue item, draft a reminder email in the following format:
Subject: Audit Evidence Request — [Item Name] — OVERDUE
Body: [Professional reminder text]
Also flag any items overdue by more than 14 days for manager escalation.
```

**Intended file location:** `prompts/audit-use-cases/pbc-reminder-agent.md`

---

## 6. Tools and Techniques

### Approach

The migration follows a three-step pattern:

**Step 1 — Identify the n8n workflow's core logic:** What does it decide or produce? (The AI-adjacent decision is what Claude replaces; simple HTTP calls can stay in Python.)

**Step 2 — Replace n8n nodes with Python equivalents:**

| n8n Node | Python/Claude equivalent |
|---|---|
| Cron trigger | `schedule` library or GitHub Actions cron |
| HTTP Request | `httpx.get()` |
| Code (JavaScript) | Python function |
| AI Agent node | `anthropic.messages.create()` |
| Email (Gmail/SMTP) | `smtplib` or email API |
| Google Sheets | `gspread` library or CSV |
| IF (condition) | Python `if` statement |
| Loop | Python `for` loop |

**Step 3 — Add unit tests:** n8n workflows cannot be unit tested. Python functions can.

### Example script or pseudocode

```python
# n8n equivalent: daily PBC reminder workflow
import anthropic
import csv
from datetime import date, datetime
from pathlib import Path

client = anthropic.Anthropic()
TODAY = date.today()

def load_pbc_items(csv_path: Path) -> list[dict]:
    with open(csv_path) as f:
        return list(csv.DictReader(f))

def is_overdue(item: dict) -> bool:
    due_date = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
    return due_date < TODAY

def draft_reminder(item: dict, days_overdue: int) -> str:
    prompt = (
        f"Draft a professional audit evidence reminder for:\n"
        f"Item: {item['description']}\n"
        f"Requested from: {item['contact_name']}\n"
        f"Due date: {item['due_date']}\n"
        f"Days overdue: {days_overdue}\n"
        f"Escalate to manager: {'yes' if days_overdue > 14 else 'no'}\n"
        "Keep the email under 100 words. Professional and clear."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Cost-efficient for short drafts
        max_tokens=256,
        system="You are a professional audit communication assistant.",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def run_pbc_reminders(csv_path: Path):
    items = load_pbc_items(csv_path)
    for item in items:
        if not is_overdue(item):
            continue
        due = datetime.strptime(item["due_date"], "%Y-%m-%d").date()
        days_overdue = (TODAY - due).days
        reminder = draft_reminder(item, days_overdue)
        print(f"  Reminder for {item['contact_name']}: {reminder[:60]}...")
        # In production: send via smtplib or email API

# Unit test equivalent (pytest)
def test_is_overdue():
    assert is_overdue({"due_date": "2020-01-01"}) is True
    assert is_overdue({"due_date": "2099-01-01"}) is False
```

**Tech stack used:** Python 3.9+, Claude API (claude-haiku-4-5-20251001 for cost efficiency), csv, datetime (all stdlib)

**Intended file location:** `tools/scripts/audit-workflow-agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2340 | Engagement supervision — Python script with logging provides audit trail that n8n does not |
| IIA IPPF 2010 | Planning — scheduled agent runs must be documented in the audit plan |

### Claude / AI tool usage notes

PBC reminders contain auditee names and context. Use synthetic names in testing. Production reminders are low-risk (reminder text, no confidential data) — Claude API use is acceptable.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Python script + pytest unit tests + migration guide Markdown

**Schema reference:** Not applicable (workflow migration)

### Synthetic example output (PBC reminder)

```
Reminder for: J. de Vries (Finance Controller)
Subject: Audit Evidence Request — Q4 Vendor Payment Approvals — OVERDUE (7 days)

Dear J. de Vries,

This is a reminder that the Q4 Vendor Payment Approvals listing
was due on 14 April 2026 and remains outstanding (7 days overdue).

Please provide the export in CSV format to enable timely completion
of the vendor payments audit.

Thank you for your cooperation.
[Audit Team]
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] Claude API (claude-haiku-4-5-20251001 — cost-efficient)
- [x] CSV input (from Strapi synthetic data export)
- [x] pytest for unit tests

**Stretch goals:**

- [ ] GitHub Actions: schedule the Python script to replace n8n's cron trigger
- [ ] Migration tool: input n8n JSON workflow → output skeleton Python script
- [ ] Integration with `diyve-garg-pbc-assistant-isabelle.md` for full PBC lifecycle

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `audit-workflow-agent.py` (PBC reminder example)
- n8n node → Python migration reference table
- pytest test templates for audit workflow agents

**Help requested:**

- Teams with n8n audit workflows: share your workflow description (not the JSON) so we can build migration patterns
- Engineers: build a script that reads n8n workflow JSON and generates Python skeleton
- Auditors: validate that the reminder email quality meets professional standards

**Cross-org interest:**

n8n is used by several SAAF participant organizations. A migration pattern reduces the cost of moving to a more testable, AI-native workflow approach.

**Related SAAF plans:**

- [`diyve-garg-pbc-assistant-isabelle.md`](../hackathon-2/diyve-garg-pbc-assistant-isabelle.md) — PBC management agent (complementary)
- [`saaf-intelligence-monitor.md`](saaf-intelligence-monitor.md) — GitHub Actions scheduling pattern
- [`audit-loop-orchestration-sdk.md`](audit-loop-orchestration-sdk.md) — SDK for more complex multi-step workflows

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Migration pattern defined; node mapping table complete |
| **Do** | In progress | Hackathon #3: migrate PBC reminder workflow; add unit tests |
| **Check** | Not started | Compare output quality: n8n reminder vs. Claude agent reminder |
| **Act** | Not started | Publish migration guide + 3 workflow templates |

---

## 12. Open Questions

1. Are there n8n audit workflows that genuinely cannot be migrated to Python/Claude (e.g., complex visual integrations)?
2. Should the migration guide recommend GitHub Actions as the n8n cron replacement, or is there a simpler option for non-technical auditors?
3. How do we handle n8n workflows that depend on n8n-specific nodes (e.g., n8n's built-in Jira integration) that have no direct Python equivalent?
4. Is it worth building a tool that auto-converts n8n JSON exports to Python skeleton code?
