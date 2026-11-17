"""
Example: run the full PBC Audit Workflow with sample data.

Usage:
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."
    python example_run.py
"""

from pbc_workflow import run_pbc_workflow, AuditeeContact, ReceivedDocument

# ── 1. Define the audit engagement ───────────────────────────────────────────

AUDIT_SCOPE = "Annual statutory audit of financial statements"
AUDIT_PERIOD = "Year ended 31 December 2024"

REQUIRED_DOCUMENTS = [
    "Signed trial balance",
    "General ledger (full year)",
    "Bank statements for all accounts",
    "Bank reconciliation statements",
    "Accounts receivable ageing report",
    "Accounts payable ageing report",
    "Fixed asset register",
    "Board minutes for the year",
    "Management accounts (monthly)",
    "Payroll summary and reconciliation",
]

# ── 2. Define who receives the PBC list ──────────────────────────────────────

AUDITEE = AuditeeContact(
    name="Sarah Johnson",
    email="sarah.johnson@acme-corp.com",
    organization="ACME Corporation Ltd",
)

# ── 3. Simulate partial document submission by the auditee ───────────────────
#
#  Suppose the auditee has already uploaded three files.
#  (Leave this list empty to simulate a brand-new engagement with nothing received yet.)

RECEIVED = [
    ReceivedDocument(filename="Trial_Balance_Dec2024_signed.xlsx", pbc_id="PBC-001"),
    ReceivedDocument(filename="General_Ledger_FY2024.pdf",         pbc_id="PBC-002"),
    ReceivedDocument(filename="Bank_Statements_All_Accounts.zip",  pbc_id="PBC-003"),
]

# ── 4. Set a reference date (override to test overdue logic) ─────────────────
#
#  Use a date well past your expected deadlines to trigger overdue reminders.
#  Set to None to use today's real date.

CURRENT_DATE = "2025-03-10"   # well after any 14-day deadline from today

# ── 5. Run the workflow ───────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_pbc_workflow(
        audit_scope=AUDIT_SCOPE,
        audit_period=AUDIT_PERIOD,
        required_documents=REQUIRED_DOCUMENTS,
        auditee_contact=AUDITEE,
        received_documents=RECEIVED,
        current_date=CURRENT_DATE,
    )

    # All outputs are available on the result object for downstream use
    print("\n\nFinal dashboard data (machine-readable):")
    import json, dataclasses
    print(json.dumps(dataclasses.asdict(result.dashboard_report), indent=2))
