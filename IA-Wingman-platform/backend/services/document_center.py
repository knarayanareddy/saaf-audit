"""Document center — one availability-aware catalogue of every document the
platform can generate for an engagement. Deterministic (no AI): each entry
reports whether it can be produced yet and, if not, why. Download paths point at
the existing authenticated export endpoints.
"""
import json

from sqlalchemy import select
from models.planning import (
    AuditNotificationLetter, KickoffAgenda, BackgroundRiskAssessment,
    WorkProgram, DRLDocument,
)
from models.reporting import AuditReport
from models.interview import InterviewSession
from services.work_program_view import rows_for as _wp_rows


def _loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _entry(key, title, description, category, fmt, available, reason, path):
    return {
        "key": key, "title": title, "description": description, "category": category,
        "format": fmt, "available": available,
        "reason": None if available else reason, "download_path": path if available else None,
    }


async def list_generated_documents(engagement_id: str, db) -> list[dict]:
    eid = engagement_id
    docs: list[dict] = []

    anl = (await db.execute(select(AuditNotificationLetter).where(AuditNotificationLetter.engagement_id == eid))).scalar_one_or_none()
    anl_ok = bool(anl and (anl.background or anl.objectives or anl.scope_description))
    docs.append(_entry("anl", "Audit Notification Letter", "Formal notification to the auditee.",
                       "Planning", "word", anl_ok, "Draft the Audit Notification Letter first.",
                       f"/planning/{eid}/anl/export-word"))

    ko = (await db.execute(select(KickoffAgenda).where(KickoffAgenda.engagement_id == eid))).scalar_one_or_none()
    ko_ok = bool(ko and (ko.meeting_date or ko.notes_welcome or ko.notes_context or ko.notes_scope))
    docs.append(_entry("kickoff", "Kick-off Meeting Agenda", "Structured agenda for the kick-off meeting.",
                       "Planning", "word", ko_ok, "Prepare the kick-off agenda first.",
                       f"/planning/{eid}/kickoff/export-word"))

    bra = (await db.execute(select(BackgroundRiskAssessment).where(BackgroundRiskAssessment.engagement_id == eid))).scalar_one_or_none()
    bra_ok = bool(bra and _loads(bra.risk_items, []))
    docs.append(_entry("bra", "Background Risk Assessment", "Risk assessment workbook with the risk register.",
                       "Planning", "excel", bra_ok, "Complete the Background Risk Assessment first.",
                       f"/planning/{eid}/bra/export-xlsx"))

    wp_ok = bool(await _wp_rows(eid, db))
    docs.append(_entry("work_program", "Work Program", "Test procedures workbook.",
                       "Planning", "excel", wp_ok, "Generate the work program first.",
                       f"/planning/{eid}/work-program/export-xlsx"))

    drl = (await db.execute(select(DRLDocument).where(DRLDocument.engagement_id == eid))).scalar_one_or_none()
    drl_ok = bool(drl and _loads(drl.items, []))
    docs.append(_entry("drl", "Document Request List", "List of documents requested from the auditee.",
                       "Planning", "word", drl_ok, "Build the Document Request List first.",
                       f"/planning/{eid}/drl/export-word"))

    # Interview minutes — one per companion session that has been analysed.
    sessions = (await db.execute(
        select(InterviewSession).where(InterviewSession.engagement_id == eid).order_by(InterviewSession.created_at)
    )).scalars().all()
    analysed = [s for s in sessions if s.analysis]
    if analysed:
        for s in analysed:
            docs.append(_entry(f"minutes_{s.id}", f"Interview minutes — {s.label or s.persona or 'session'}",
                               "Minutes drafted from the interview companion.", "Interviews", "word", True, "",
                               f"/planning/{eid}/interview/sessions/{s.id}/minutes"))
    else:
        docs.append(_entry("minutes", "Interview minutes", "Minutes drafted from an interview companion session.",
                           "Interviews", "word", False, "Run an interview companion session first.", None))

    report = (await db.execute(select(AuditReport).where(AuditReport.engagement_id == eid))).scalar_one_or_none()
    rep_ok = bool(report and report.exec_summary)
    docs.append(_entry("report", "Internal Audit Report", "The full audit report with 5C findings.",
                       "Reporting", "word", rep_ok, "Draft the audit report first.",
                       f"/reporting/{eid}/report/export-word"))

    return docs
