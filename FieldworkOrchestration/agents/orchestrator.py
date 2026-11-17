"""Fieldwork orchestrator — runs the registered fieldwork agents.

Only agents that have been ported into ``agents/<slug>.py`` are registered in
``REGISTERED_AGENTS``. Register new agents here as they land — see
agents/README.md for the agent contract and the checklist for adding one.

Quality scoring (``review_run``) and human approval (``require_approved`` /
``record_approval``) build on top of the audit trail. Nothing an agent
produces is final until an internal auditor has recorded an approval — any
action that would treat a run's output as final (see ``finalize_run`` for
the pattern) must call ``require_approved`` first.

Two ways to run agents:

- ``run_orchestrator`` — pass pre-built inputs per agent slug; agents run
  independently, nothing is passed between them. Use this for agents with no
  required dependency on another agent's output (currently
  ``pbc_document_analysis`` and ``pbc_intake`` — the latter accepts a
  ``pbc_list`` optionally, to suggest PBC-ID matches for unassigned intake
  files, but runs fine without one).
- ``run_pbc_workflow`` — the five PBC agents depend on each other's output
  (``pbc_distribution``, ``pbc_validation``, ``pbc_dashboard`` and
  ``pbc_reminder`` all need the PBC list from ``pbc_creation``; ``pbc_dashboard``
  and ``pbc_reminder`` also need the validation result from
  ``pbc_validation``). This function threads those outputs through in the
  order the source PBC-Assistant-Isabelle workflow used, per the "agents
  must not import each other — the orchestrator passes outputs along"
  contract in agents/README.md.
- ``run_evidence_audit_pipeline`` — the four Mollie Group X evidence-audit
  stages, same pattern: evidence_collection -> evidence_analysis ->
  quality_check (reused as-is, not a bespoke reviewer) -> findings_conclusion,
  with a bounded revision loop when quality_check returns
  "requires_revision".
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from agents import (
    cli_evidence_analysis,
    document_evidence_extraction,
    evidence_analysis,
    evidence_collection,
    findings_conclusion,
    grc_copilot_cheatsheet,
    pbc_creation,
    pbc_dashboard,
    pbc_distribution,
    pbc_document_analysis,
    pbc_document_check,
    pbc_intake,
    pbc_reminder,
    pbc_scope_from_work_program,
    pbc_upload_check,
    pbc_validation,
    pbc_validation_prompt_proposal,
    quality_check,
)
from agents.audit_trail import AuditTrail
from agents.claude_init import ClaudeClient

REGISTERED_AGENTS = {
    "pbc_creation": pbc_creation.run,
    "pbc_distribution": pbc_distribution.run,
    "pbc_validation": pbc_validation.run,
    "pbc_dashboard": pbc_dashboard.run,
    "pbc_reminder": pbc_reminder.run,
    "pbc_document_analysis": pbc_document_analysis.run,
    "pbc_intake": pbc_intake.run,
    "quality_check": quality_check.run,
    "grc_copilot_cheatsheet": grc_copilot_cheatsheet.run,
    "cli_evidence_analysis": cli_evidence_analysis.run,
    "document_evidence_extraction": document_evidence_extraction.run,
    "evidence_collection": evidence_collection.run,
    "evidence_analysis": evidence_analysis.run,
    "findings_conclusion": findings_conclusion.run,
    "pbc_scope_from_work_program": pbc_scope_from_work_program.run,
    "pbc_upload_check": pbc_upload_check.run,
    "pbc_validation_prompt_proposal": pbc_validation_prompt_proposal.run,
    "pbc_document_check": pbc_document_check.run,
}


def _client_and_trail(
    client: ClaudeClient | None, audit_trail: AuditTrail | None
) -> tuple[ClaudeClient, AuditTrail | None]:
    """Build a client wired to an audit trail when the caller didn't supply one.

    If ``client`` is supplied, its audit trail configuration is left as-is —
    the caller owns it, so the returned ``audit_trail`` is whatever was
    passed in (possibly ``None``), not whatever the client actually logs to.
    """
    if client is None:
        audit_trail = audit_trail or AuditTrail()
        client = ClaudeClient(audit_trail=audit_trail)
    return client, audit_trail


def run_orchestrator(
    agent_inputs: dict[str, dict],
    client: ClaudeClient | None = None,
    audit_trail: AuditTrail | None = None,
) -> dict[str, Any]:
    """Run every registered agent that has inputs and collect its result.

    ``agent_inputs`` maps an agent slug to the ``inputs`` dict that agent's
    ``run()`` expects. Slugs without a registered agent, or without inputs,
    are skipped. Agents run independently — nothing is passed between them;
    use ``run_pbc_workflow`` for the PBC agents, which depend on each other.

    If ``client`` is not supplied, a new one is created wired to
    ``audit_trail`` (a new ``AuditTrail`` if none is given either), so every
    Claude call made during this run is captured under one
    ``runs/<run_id>/audit_trail.jsonl``.
    """
    client, audit_trail = _client_and_trail(client, audit_trail)

    results = {
        slug: run_fn(agent_inputs[slug], client=client)
        for slug, run_fn in REGISTERED_AGENTS.items()
        if slug in agent_inputs
    }

    return {
        "run_id": audit_trail.run_id if audit_trail is not None else None,
        "results": results,
    }


def run_pbc_workflow(
    audit_scope: str,
    audit_period: str,
    required_documents: list[str],
    auditee_contact: dict,
    received_documents: list[dict] | None = None,
    current_date: str | None = None,
    today: str | None = None,
    client: ClaudeClient | None = None,
    audit_trail: AuditTrail | None = None,
) -> dict[str, Any]:
    """Run the PBC (Prepared-By-Client) pipeline end to end.

    Runs ``pbc_creation`` first, then feeds its PBC list into
    ``pbc_distribution`` and ``pbc_validation``, then feeds the validation
    result (together with the PBC list) into ``pbc_dashboard`` and
    ``pbc_reminder`` — mirroring the five-stage sequence in the source
    PBC-Assistant-Isabelle workflow.

    ``pbc_document_analysis`` is not part of this chain: it analyses one
    document against one PBC item's description and isn't a required input
    to any of the five stages above. Call it directly (or via
    ``run_orchestrator``) per received document.

    To source ``received_documents`` from the intake folder instead of
    building the list by hand, call ``pbc_intake.run({"engagement_id": ...,
    "pbc_list": pbc_creation.run(...)})`` first and pass its
    ``received_documents`` in here — this function does not scan the intake
    folder itself, to keep "where documents come from" and "run the
    pipeline" as separate concerns.

    ``received_documents``, ``current_date``, and ``today`` default the same
    way the individual agents do (empty list / today's date) when omitted.
    """
    client, audit_trail = _client_and_trail(client, audit_trail)

    pbc_list = pbc_creation.run(
        {
            "audit_scope": audit_scope,
            "audit_period": audit_period,
            "required_documents": required_documents,
            "today": today,
        },
        client=client,
    )

    delivery_status = pbc_distribution.run(
        {"pbc_list": pbc_list, "auditee_contact": auditee_contact},
        client=client,
    )

    validation_status = pbc_validation.run(
        {
            "pbc_list": pbc_list,
            "received_documents": received_documents or [],
            "current_date": current_date,
        },
        client=client,
    )

    dashboard_report = pbc_dashboard.run(
        {"pbc_list": pbc_list, "validation_status": validation_status},
        client=client,
    )

    reminder_log = pbc_reminder.run(
        {
            "pbc_list": pbc_list,
            "validation_status": validation_status,
            "auditee_contact": auditee_contact,
            "current_date": current_date,
        },
        client=client,
    )

    return {
        "run_id": audit_trail.run_id if audit_trail is not None else None,
        "pbc_list": pbc_list,
        "delivery_status": delivery_status,
        "validation_status": validation_status,
        "dashboard_report": dashboard_report,
        "reminder_log": reminder_log,
    }


def review_run(run_id: str, client: ClaudeClient | None = None) -> list[dict]:
    """Run ``quality_check`` on every entry of ``run_id``'s audit trail.

    Each entry is reviewed independently, in order. The ``quality_check``
    calls themselves are appended to the same
    ``runs/<run_id>/audit_trail.jsonl`` (tagged ``agent="quality_check"``,
    so they are fully traceable too), and each verdict is recorded in
    ``runs/<run_id>/quality.jsonl``, linked to the entry it reviews by
    ``entry_id``. ``quality_check`` entries are skipped — reviewing the
    reviewer isn't the point, and it keeps repeat calls from growing the
    trail unboundedly.

    Safe to call more than once on the same run: the audit trail (and the
    quality file) are append-only, so re-reviewing adds a second opinion
    rather than overwriting the first.

    Returns the list of quality entries recorded by this call.
    """
    trail = AuditTrail(run_id=run_id)
    client = client or ClaudeClient(audit_trail=trail)

    recorded = []
    for entry in trail.entries():
        if entry["agent"] == "quality_check":
            continue
        verdict = quality_check.run(
            {
                "agent": entry["agent"],
                "system_prompt": entry["system_prompt"],
                "user_prompt": entry["user_prompt"],
                "response_text": entry["response_text"],
                "item_ref": entry.get("item_ref"),
            },
            client=client,
        )
        recorded.append(trail.record_quality(entry_id=entry["entry_id"], verdict=verdict))

    return recorded


class ApprovalRequiredError(Exception):
    """Raised when a run (or specific entries) has not been approved yet.

    Not a bug — this is the expected outcome of calling ``require_approved``
    before an internal auditor has reviewed the run. Catch it, show the
    pending/rejected entries to the auditor, and retry after they record a
    decision with ``record_approval``.
    """


def approval_summary(run_id: str) -> list[dict]:
    """Per fieldwork-agent-call status for ``run_id``: quality verdict + approval.

    One row per audit trail entry, excluding ``quality_check`` calls
    themselves (their output is the ``quality`` field below, not a
    fieldwork result that itself needs approving). This is the data a
    monitoring view would render — see agents/README.md.
    """
    trail = AuditTrail(run_id=run_id)
    quality_by_entry = {q["entry_id"]: q["review"] for q in trail.quality_entries()}

    return [
        {
            "entry_id": entry["entry_id"],
            "agent": entry["agent"],
            "timestamp": entry["timestamp"],
            "quality": quality_by_entry.get(entry["entry_id"]),
            "approval_status": trail.approval_status(entry["entry_id"]),
            "approval": trail.latest_approval(entry["entry_id"]),
        }
        for entry in trail.entries()
        if entry["agent"] != "quality_check"
    ]


def record_approval(
    run_id: str,
    *,
    entry_id: str,
    decision: str,
    reviewer: str,
    role: str | None = None,
    comment: str | None = None,
) -> dict:
    """Record an internal auditor's approve/reject decision for one entry.

    Thin pass-through to ``AuditTrail.record_approval`` — kept here so
    run-level operations (review, approve, finalize) have one home.
    """
    return AuditTrail(run_id=run_id).record_approval(
        entry_id=entry_id, decision=decision, reviewer=reviewer, role=role, comment=comment
    )


def require_approved(run_id: str, entry_ids: list[str] | None = None) -> None:
    """Raise ``ApprovalRequiredError`` unless every entry is approved.

    ``entry_ids`` defaults to every fieldwork-agent entry in the run (see
    ``approval_summary`` — ``quality_check`` calls are excluded, they are
    never themselves approved). Call this before any action that would treat
    a run's output as final.
    """
    trail = AuditTrail(run_id=run_id)
    if entry_ids is None:
        entry_ids = [
            e["entry_id"] for e in trail.entries() if e["agent"] != "quality_check"
        ]

    not_approved = {
        entry_id: trail.approval_status(entry_id)
        for entry_id in entry_ids
        if trail.approval_status(entry_id) != "approved"
    }
    if not_approved:
        raise ApprovalRequiredError(
            f"run {run_id!r} is not fully approved: {not_approved}"
        )


def finalize_run(run_id: str, entry_ids: list[str] | None = None) -> dict:
    """Mark a run as finalized — the concrete example of using the gate.

    Raises ``ApprovalRequiredError`` (and writes nothing) unless every entry
    in scope has been approved. Any future action that makes a drafted
    result real — actually sending an email instead of mocking it, exporting
    a signed-off report, closing out an engagement — should follow this same
    shape: call ``require_approved`` first, only then do the real thing.

    ``entry_ids`` defaults to every fieldwork-agent entry ever recorded for
    the run (see ``require_approved``). Pass it explicitly to scope
    finalization to only the entries that are actually still relevant — e.g.
    the webapp only ever shows one entry per PBC item (the latest
    validation call if one exists, otherwise the original drafting call;
    see ``webapp/server.py``'s ``_pbc_item_rows``), so a superseded earlier
    entry for the same item shouldn't still block finalizing just because
    nobody has (or now can) act on it in the UI.
    """
    require_approved(run_id, entry_ids)

    finalized = {
        "run_id": run_id,
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "approved_entries": entry_ids
        if entry_ids is not None
        else [e["entry_id"] for e in approval_summary(run_id)],
    }
    trail = AuditTrail(run_id=run_id)
    finalized_path = trail.path.parent / "finalized.json"
    finalized_path.write_text(json.dumps(finalized, indent=2), encoding="utf-8")
    return finalized


def run_evidence_audit_pipeline(
    control_objective: str,
    evidence_items: list[str],
    client: ClaudeClient | None = None,
    audit_trail: AuditTrail | None = None,
    max_revisions: int = 1,
) -> dict[str, Any]:
    """Run the Mollie Group X evidence-audit pipeline end to end.

    Four stages: ``evidence_collection`` -> ``evidence_analysis`` ->
    ``quality_check`` (reused as-is — the source plan's own "Quality Check
    Agent" concept is what ``quality_check`` was already generalized from,
    so this pipeline uses that agent rather than a bespoke duplicate) ->
    ``findings_conclusion``. If ``quality_check`` returns
    "requires_revision", ``evidence_analysis`` is re-run (up to
    ``max_revisions`` times, default 1) with that feedback before
    ``findings_conclusion`` runs — mirroring the revision loop in the
    source plan's own pseudocode.

    Built from the Mollie Group X evidence-audit plan (Track 2 — Evidence
    Collection, plans/alignment/mollie-group-x-evidence-audit.md) — a draft
    plan (prompts + pseudocode only), not existing code.
    """
    client, audit_trail = _client_and_trail(client, audit_trail)

    collection = evidence_collection.run(
        {"control_objective": control_objective, "evidence_items": evidence_items},
        client=client,
    )

    analysis = evidence_analysis.run(
        {
            "control_objective": control_objective,
            "evidence_collected": collection["evidence_collected"],
        },
        client=client,
    )
    quality = review_last_entry(client, audit_trail)

    revisions = 0
    while (
        quality is not None
        and quality["verdict"] == "requires_revision"
        and revisions < max_revisions
    ):
        analysis = evidence_analysis.run(
            {
                "control_objective": control_objective,
                "evidence_collected": collection["evidence_collected"],
                "feedback": "; ".join(quality["issues"]) or quality["rationale"],
            },
            client=client,
        )
        quality = review_last_entry(client, audit_trail)
        revisions += 1

    finding = findings_conclusion.run(
        {
            "control_objective": control_objective,
            "analysis": analysis,
            "quality_verdict": quality["verdict"] if quality else "not reviewed",
        },
        client=client,
    )

    return {
        "run_id": audit_trail.run_id if audit_trail is not None else None,
        "evidence_collection": collection,
        "evidence_analysis": analysis,
        "quality": quality,
        "revisions": revisions,
        "finding": finding,
    }


def control_coverage(
    work_program: list[dict],
    traceability: list[dict],
    pbc_list: dict | None = None,
    validation_status: dict | None = None,
) -> list[dict]:
    """Join risk -> control -> planned work -> actual status into one row per control.

    The four-stage traceability chain: ``work_program`` (from UC8, Track 1)
    supplies "identified risk" and "internal control" plus the planned Test
    of Design / Tests of Effectiveness ("planned audit work"); the PBC
    pipeline supplies "actually performed work" once ``pbc_validation`` has
    run. This function does not call Claude — it is a pure join over data
    already produced elsewhere:

    - ``work_program`` — the UC8 array (risk/control/test-step detail).
    - ``traceability`` — ``pbc_scope_from_work_program.run(...)``'s
      ``traceability`` output (same length/order as the
      ``required_documents`` that were fed into ``pbc_creation``).
    - ``pbc_list`` (optional) — ``pbc_creation.run(...)``'s output. Zipped
      positionally with ``traceability`` to recover which PBC-ID each
      consolidated document became — see the caveat about this in
      ``pbc_scope_from_work_program.run``'s docstring. Omit to get
      per-control planned-work detail without PBC/validation linkage.
    - ``validation_status`` (optional) — ``pbc_validation.run(...)``'s
      output. Requires ``pbc_list`` to also be given (status is looked up
      by PBC-ID).

    Returns one row per work-program control:
    ``{risk_id, risk, control_id, control, control_objective,
    planned_steps, planned_hours, pbc_items: [{pbc_id, status}],
    coverage_status}``, where ``coverage_status`` is one of "no PBC items
    linked" (no ``pbc_list``, or no traceable items), "not yet validated"
    (linked but no ``validation_status``), or an "N/M validated" summary.
    """
    doc_to_pbc_id: dict[str, str] = {}
    if pbc_list is not None:
        for doc, item in zip(traceability, pbc_list["items"]):
            doc_to_pbc_id[doc["document"]] = item["id"]

    status_by_pbc_id: dict[str, str] = {}
    if validation_status is not None:
        status_by_pbc_id = {r["pbc_id"]: r["status"] for r in validation_status["results"]}

    # control_id -> set of PBC-IDs that supply evidence for it
    control_to_pbc_ids: dict[str, set] = {}
    for doc in traceability:
        pbc_id = doc_to_pbc_id.get(doc["document"])
        if pbc_id is None:
            continue
        for source in doc["sources"]:
            control_to_pbc_ids.setdefault(source["control_id"], set()).add(pbc_id)

    rows = []
    for control in work_program:
        control_id = control["control_id"]
        pbc_ids = sorted(control_to_pbc_ids.get(control_id, set()))
        pbc_items = [{"pbc_id": pid, "status": status_by_pbc_id.get(pid)} for pid in pbc_ids]

        if not pbc_ids:
            coverage_status = "no PBC items linked"
        elif not status_by_pbc_id:
            coverage_status = "not yet validated"
        else:
            validated = sum(1 for p in pbc_items if p["status"] == "validated")
            coverage_status = f"{validated}/{len(pbc_items)} validated"

        steps = [control["test_of_design"]] + control.get("tests_of_effectiveness", [])
        rows.append(
            {
                "risk_id": control["risk_id"],
                "risk": control["risk"],
                "control_id": control_id,
                "control": control["control"],
                "control_objective": control.get("control_objective"),
                "planned_steps": len(steps),
                "planned_hours": sum(s.get("estimated_hours") or 0 for s in steps),
                "pbc_items": pbc_items,
                "coverage_status": coverage_status,
            }
        )
    return rows


def review_last_entry(client: ClaudeClient, audit_trail: AuditTrail | None) -> dict | None:
    """Run ``quality_check`` on the most recently recorded audit-trail entry.

    Unlike ``review_run`` (which reviews a whole run's trail — call that once
    after a full run, not from a tight loop or per-request handler, or it
    keeps re-reviewing everything each time), this reviews only the single
    latest call. Used internally right after a pipeline stage runs, so
    earlier stages in the same pipeline aren't redundantly re-reviewed; also
    the right tool for a caller (e.g. the webapp, after ``pbc_document_check``
    runs for one item) that wants to review exactly the one fresh call it
    just made. Returns ``None`` if there's no audit trail to read from.
    """
    if audit_trail is None:
        return None
    entries = audit_trail.entries()
    if not entries:
        return None
    last = entries[-1]
    verdict = quality_check.run(
        {
            "agent": last["agent"],
            "system_prompt": last["system_prompt"],
            "user_prompt": last["user_prompt"],
            "response_text": last["response_text"],
            "item_ref": last.get("item_ref"),
        },
        client=client,
    )
    audit_trail.record_quality(entry_id=last["entry_id"], verdict=verdict)
    return verdict
