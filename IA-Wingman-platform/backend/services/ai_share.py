"""How much of an audit file IA Wingman proposed, and what people did with it.

Two sources, kept apart because they know different things:

- **The records themselves.** Every item says who made it (`origin`, `source`,
  `is_ai_generated`, a run column) and, where there is a decision step, whether
  a person accepted it. That covers the whole file, including everything made
  before the edit register existed — but it cannot say whether a person later
  changed what the platform proposed.
- **The edit register** (`services/edit_register.profile`), which can — for
  what happened since it started, and nothing before.

"Proposed by IA Wingman" and not "by the model": `origin='ai'` also covers the
deterministic scoping engine, which proposes nodes without any model call.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import func, select

from models.interview import InterviewGuide
from models.planning import (
    ApplicableFramework, AuditNotificationLetter, BackgroundRiskAssessment, FieldworkObservation,
    KeyAuditQuestion, KickoffAgenda, ProcessNotes, RegRequirement, ScopeItem, ScopeObjectives,
    TopicIntelligence, WorkProgram,
)
from models.racm import RacmControl, RacmEvidence, RacmObjective, RacmRisk, RacmTest, ScopeDecision
from models.reporting import AuditReport, Finding


@dataclass(frozen=True)
class Kind:
    """Items an audit file holds many of."""
    key: str                 # the table — also the register's `entity`
    label: str
    model: Any
    proposed: Callable       # model -> SQL expression: the platform made this item
    decided: Callable | None  # model -> SQL expression: a person accepted it; None = no decision step
    # True when "not proposed" means a person made it. False when the marker is
    # only a run column: an item without one may be seeded or older, so it is
    # counted as "no AI run recorded" instead of claimed as a person's work.
    absent_means_person: bool = True
    via_scope: bool = False  # no engagement column; belongs to the audit through its scope


KINDS: tuple[Kind, ...] = (
    Kind("racm_objectives", "Audit objectives", RacmObjective,
         lambda m: m.origin == "ai", lambda m: m.accepted.is_(True)),
    Kind("racm_risks", "Risks", RacmRisk,
         lambda m: m.origin == "ai", lambda m: m.accepted.is_(True)),
    Kind("racm_controls", "Controls", RacmControl,
         lambda m: m.origin == "ai", lambda m: m.accepted.is_(True)),
    Kind("racm_tests", "Tests", RacmTest,
         lambda m: m.origin == "ai", lambda m: m.accepted.is_(True)),
    Kind("racm_evidence", "Evidence", RacmEvidence,
         lambda m: m.origin == "ai", lambda m: m.accepted.is_(True)),
    Kind("scope_decisions", "Scope decisions", ScopeDecision,
         lambda m: m.origin == "ai", lambda m: m.status != "proposed"),
    Kind("applicable_frameworks", "Frameworks", ApplicableFramework,
         lambda m: m.source != "manual", lambda m: m.is_accepted.is_(True)),
    Kind("scope_items", "Scope items", ScopeItem,
         lambda m: m.source != "manual", lambda m: m.is_accepted.is_(True), via_scope=True),
    Kind("key_audit_questions", "Key audit questions", KeyAuditQuestion,
         lambda m: m.source != "manual", lambda m: m.is_accepted.is_(True), via_scope=True),
    Kind("fieldwork_observations", "Fieldwork observations", FieldworkObservation,
         lambda m: m.is_ai_generated.is_(True), None),
    Kind("findings", "Findings", Finding,
         lambda m: m.drafter_run_id.isnot(None), None, absent_means_person=False),
)


@dataclass(frozen=True)
class Document:
    """Things an audit file holds one of. Listed, not counted."""
    key: str
    label: str
    model: Any
    run: Callable                     # row -> the AI run that drafted it, or None
    step: str | None = None           # the decision a person takes on it
    done: Callable | None = None      # row -> whether that decision is taken


DOCUMENTS: tuple[Document, ...] = (
    Document("topic_intelligence", "Topic Intelligence memo", TopicIntelligence,
             lambda r: r.lens1_run_id or r.lens2_run_id or r.lens3_run_id or r.regulatory_run_id,
             "memo acceptance", lambda r: bool(r.memo_accepted)),
    Document("reg_requirements", "Regulatory requirements", RegRequirement,
             lambda r: r.analyser_run_id, "agreement", lambda r: r.status == "agreed"),
    Document("process_notes", "Process understanding", ProcessNotes,
             lambda r: r.analyser_run_id, "agreement", lambda r: r.status == "agreed"),
    Document("background_risk_assessments", "Background risk assessment", BackgroundRiskAssessment,
             lambda r: r.drafter_run_id),
    Document("audit_notification_letters", "Audit notification letter", AuditNotificationLetter,
             lambda r: r.drafter_run_id, "Head of IA approval", lambda r: r.head_ia_status == "approved"),
    Document("kickoff_agendas", "Kick-off agenda", KickoffAgenda, lambda r: r.drafter_run_id),
    Document("work_programs", "Work program", WorkProgram,
             lambda r: r.generator_run_id, "sign-off", lambda r: r.signed_off_at is not None),
    Document("interview_guides", "Interview guide", InterviewGuide, lambda r: r.generator_run_id),
    Document("audit_reports", "Audit report", AuditReport, lambda r: r.drafter_run_id),
)

LABELS = {k.key: k.label for k in KINDS} | {d.key: d.label for d in DOCUMENTS}


async def _count_kind(db, kind: Kind, engagement_id: str, scope_ids: list[str]) -> dict:
    m = kind.model
    proposed = kind.proposed(m)
    decided = kind.decided(m) if kind.decided else None
    cols = [proposed.label("p")] + ([decided.label("d")] if decided is not None else [])
    q = select(*cols, func.count().label("n")).group_by(*[c for c in cols])
    if kind.via_scope:
        if not scope_ids:
            return _empty(kind)
        q = q.where(m.scope_id.in_(scope_ids))
    else:
        q = q.where(m.engagement_id == engagement_id)

    out = _empty(kind)
    for row in (await db.execute(q)).all():
        n = row.n
        if row.p:
            out["proposed"] += n
            if decided is not None:
                out["accepted" if row.d else "open"] += n
        elif kind.absent_means_person:
            out["by_person"] += n
        else:
            out["no_run_recorded"] += n
    return out


def _empty(kind: Kind) -> dict:
    return {"key": kind.key, "label": kind.label, "has_decision": kind.decided is not None,
            "proposed": 0, "accepted": 0, "open": 0, "by_person": 0, "no_run_recorded": 0}


async def _documents(db, engagement_id: str) -> list[dict]:
    out = []
    for doc in DOCUMENTS:
        row = (await db.execute(
            select(doc.model).where(doc.model.engagement_id == engagement_id).limit(1)
        )).scalars().first()
        if row is None or getattr(row, "status", None) == "not_started":
            continue
        out.append({
            "key": doc.key, "label": doc.label,
            "written_by": "ai" if doc.run(row) else "no_run_recorded",
            "decision": {"step": doc.step, "done": bool(doc.done(row))} if doc.step else None,
        })
    return out


async def scope_item_ids(db, engagement_id: str) -> tuple[list[str], list[str]]:
    """The scope ids of an audit, and the ids of the scope items and key audit
    questions under them — the two tracked tables without an engagement column."""
    scope_ids = list((await db.execute(
        select(ScopeObjectives.id).where(ScopeObjectives.engagement_id == engagement_id)
    )).scalars().all())
    if not scope_ids:
        return [], []
    item_ids = []
    for model in (ScopeItem, KeyAuditQuestion):
        item_ids += (await db.execute(select(model.id).where(model.scope_id.in_(scope_ids)))).scalars().all()
    return scope_ids, item_ids


async def ai_share(engagement_id: str) -> dict:
    from database import AsyncSessionLocal
    from services.edit_register import profile

    async with AsyncSessionLocal() as db:
        scope_ids, _ = await scope_item_ids(db, engagement_id)
        kinds = [await _count_kind(db, k, engagement_id, scope_ids) for k in KINDS]
        documents = await _documents(db, engagement_id)

    register = await profile(engagement_id)
    for k in register["kinds"]:
        k["label"] = LABELS.get(k["key"], k["key"])

    headline = {f: sum(k[f] for k in kinds)
                for f in ("proposed", "accepted", "open", "by_person", "no_run_recorded")}
    return {
        "headline": headline,
        "kinds": [k for k in kinds if any(k[f] for f in ("proposed", "by_person", "no_run_recorded"))],
        "documents": documents,
        "register": register,
        "basis": "records+register" if register["kinds"] else "records",
    }
