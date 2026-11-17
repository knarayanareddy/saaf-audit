"""
Sequential PBC Audit Workflow Orchestrator.

Runs the five agents in order, passing outputs as inputs to the next stage:

    PBC_Creation_Agent
        ↓ pbc_list
    PBC_Distribution_Agent
        ↓ delivery_status
    Document_Validation_Agent
        ↓ validation_status
    Status_Dashboard_Agent
        ↓ dashboard_report
    Reminder_Agent
        ↓ reminder_log
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from .agents import (
    run_pbc_creation_agent,
    run_pbc_distribution_agent,
    run_document_validation_agent,
    run_status_dashboard_agent,
    run_reminder_agent,
)
from .models import (
    AuditeeContact,
    DashboardReport,
    DeliveryStatus,
    PBCList,
    ReceivedDocument,
    ReminderLog,
    ValidationStatus,
)


class WorkflowResult:
    """Holds all agent outputs produced during a workflow run."""

    def __init__(
        self,
        pbc_list: PBCList,
        delivery_status: DeliveryStatus,
        validation_status: ValidationStatus,
        dashboard_report: DashboardReport,
        reminder_log: ReminderLog,
    ) -> None:
        self.pbc_list = pbc_list
        self.delivery_status = delivery_status
        self.validation_status = validation_status
        self.dashboard_report = dashboard_report
        self.reminder_log = reminder_log


def run_pbc_workflow(
    audit_scope: str,
    audit_period: str,
    required_documents: List[str],
    auditee_contact: AuditeeContact,
    received_documents: Optional[List[ReceivedDocument]] = None,
    current_date: Optional[str] = None,
) -> WorkflowResult:
    """
    Execute the full PBC Audit Workflow sequentially.

    Parameters
    ----------
    audit_scope        : description of what is being audited
    audit_period       : period under audit, e.g. "FY 2024"
    required_documents : list of document types needed for the audit
    auditee_contact    : who to send the PBC list to
    received_documents : documents already submitted by the auditee
                         (pass an empty list or None to simulate a fresh engagement)
    current_date       : ISO date string for today — defaults to the real today
    """
    if received_documents is None:
        received_documents = []
    if current_date is None:
        current_date = date.today().isoformat()

    print("\n" + "█" * 60)
    print("  PBC AUDIT WORKFLOW  —  Starting")
    print("█" * 60)
    print(f"  Scope  : {audit_scope}")
    print(f"  Period : {audit_period}")
    print(f"  Date   : {current_date}")
    print("█" * 60)

    # ── Stage 1 ──────────────────────────────────────────────────────────────
    pbc_list = run_pbc_creation_agent(
        audit_scope=audit_scope,
        audit_period=audit_period,
        required_documents=required_documents,
    )

    # ── Stage 2 ──────────────────────────────────────────────────────────────
    delivery_status = run_pbc_distribution_agent(
        pbc_list=pbc_list,
        auditee_contact=auditee_contact,
    )

    # ── Stage 3 ──────────────────────────────────────────────────────────────
    validation_status = run_document_validation_agent(
        pbc_list=pbc_list,
        received_documents=received_documents,
        current_date=current_date,
    )

    # ── Stage 4 ──────────────────────────────────────────────────────────────
    dashboard_report = run_status_dashboard_agent(
        pbc_list=pbc_list,
        validation_status=validation_status,
    )

    # ── Stage 5 ──────────────────────────────────────────────────────────────
    reminder_log = run_reminder_agent(
        pbc_list=pbc_list,
        validation_status=validation_status,
        current_date=current_date,
        auditee_contact=auditee_contact,
    )

    print("\n" + "█" * 60)
    print("  PBC AUDIT WORKFLOW  —  Complete")
    print("█" * 60)

    return WorkflowResult(
        pbc_list=pbc_list,
        delivery_status=delivery_status,
        validation_status=validation_status,
        dashboard_report=dashboard_report,
        reminder_log=reminder_log,
    )
