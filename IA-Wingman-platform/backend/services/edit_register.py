"""Recording who proposed and who decided — at the one moment nothing can skip.

Every change to an auditable value reaches the database through a flush, so the
register writes there: a `before_flush` listener looks at what is about to be
inserted, changed or deleted, and adds the matching `FieldEdit` rows to the same
flush. Two consequences follow, and they are the reason for doing it this way
rather than with a call at each place that edits data:

- **No call site can forget.** At least four different agents write into the
  risk matrix today, and the next one will not have to know this module exists.
- **The register and the data cannot disagree.** The rows go into the same
  transaction as the change; if the change rolls back, so does its record.

**Who did it** comes from context, never from the payload:

- inside an agent run (the ledger's `agent_context`, set by `attributed` for
  every background agent) the actor is that agent — an AI write;
- inside an HTTP request the actor is the person, from the `X-IA-Actor`
  header (`actor_from_request`), recorded as unverified until real sign-in;
- anywhere else (startup seeding, recovery) the actor is the system.

The agent check comes first on purpose: background agents run after the
request that started them, still inside its context, and a model's write must
never be recorded under the name of the person who pressed the button.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime
from urllib.parse import unquote

from fastapi import Request
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from models.edit_register import FieldEdit

#: The person behind the current HTTP request, as they identified themselves.
_HUMAN: ContextVar[str | None] = ContextVar("ia_edit_actor", default=None)

#: Header the frontend sends with every request.
ACTOR_HEADER = "X-IA-Actor"

#: Set while startup seeds the demo. Seeding is not an edit by anyone: on a host
#: without a persistent disk it runs at every start, and recording it made the
#: register say that "system" created the demo — and an agent proposed parts of
#: it — that very morning.
_PAUSED: ContextVar[bool] = ContextVar("ia_edit_register_paused", default=False)


@contextmanager
def paused():
    """Run a block without recording it in the register. For startup seeding only."""
    token = _PAUSED.set(True)
    try:
        yield
    finally:
        _PAUSED.reset(token)


# ── What is tracked ──────────────────────────────────────────────────────────
# Per table: the fields whose history matters, and — for a record that carries
# AI output for several runs at once — which column names the run behind each
# field, so a lens summary links to the lens that wrote it.
#: Never tracked: identity, ownership, ordering and timestamps the database keeps.
_HOUSEKEEPING = {"id", "engagement_id", "sort_order", "created_at", "updated_at"}
_RACM_SKIP = {"provenance", "accepted", "accepted_by", "confidence"}

#: Per table, one of:
#:   "fields":  an explicit list, or
#:   "all_but": every column except housekeeping and these — so a field added to
#:              the table later is tracked without anyone remembering to list it.
#: Optional:
#:   "accept_flag":  the column whose turning true is a person's decision
#:                   (accepted, confirmed, signed off) rather than an edit;
#:   "run_column":   the column naming the AI run behind the record's content;
#:   "run_columns":  the same per field, for a record several runs write into;
#:   "ai_flag":      for a table without `origin`, the column that marks a row
#:                   as written by a model.
TRACKED: dict[str, dict] = {
    "findings": {
        "fields": ("title", "condition", "criteria", "cause", "effect", "recommendation",
                   "rating", "rating_rationale"),
    },
    "topic_intelligence": {
        "fields": ("lens1_summary", "lens2_summary", "lens3_summary", "conclusion",
                   "key_risk_areas", "excluded_areas", "interview_agenda", "topic_primer",
                   "regulatory_summary", "internal_framework_summary", "external_developments",
                   "lens4_notes", "extra_context"),
        "accept_flag": "memo_accepted",
        "run_columns": {"lens1_summary": "lens1_run_id", "lens2_summary": "lens2_run_id",
                        "lens3_summary": "lens3_run_id"},
    },
    # Planning
    "scope_objectives": {"all_but": ("progress_pct",)},
    "scope_items": {"all_but": (), "accept_flag": "is_accepted"},
    "key_audit_questions": {"all_but": (), "accept_flag": "is_accepted"},
    "scope_decisions": {"all_but": ("provenance",)},
    "applicable_frameworks": {"all_but": (), "accept_flag": "is_accepted"},
    "reg_requirements": {"all_but": (), "run_column": "analyser_run_id"},
    "process_notes": {"all_but": (), "run_column": "analyser_run_id"},
    "background_risk_assessments": {"all_but": (), "run_column": "drafter_run_id"},
    "audit_notification_letters": {"all_but": ("review_run_id", "head_ia_approved_at"),
                                   "run_column": "drafter_run_id"},
    "kickoff_agendas": {"all_but": (), "run_column": "drafter_run_id"},
    "resource_plans": {"all_but": ()},
    "work_programs": {"all_but": (), "run_column": "generator_run_id",
                      "accept_flag": "signed_off_at"},
    "rcsa_templates": {"all_but": ("confirmed_at",)},
    "rcsa_reliance_decisions": {"all_but": ("decided_at",)},
    # Gathering and fieldwork
    "drl_documents": {"all_but": ("generated_at", "reminder_log")},
    "interview_guides": {"all_but": (), "run_column": "generator_run_id"},
    "interview_sessions": {"all_but": (), "run_column": "companion_run_id"},
    "fieldwork_observations": {"all_but": (), "ai_flag": "is_ai_generated"},
    # Reporting
    "audit_reports": {"all_but": (), "run_column": "drafter_run_id"},
    "board_reports": {"all_but": ("based_on_sig",)},
}
#: The risk-matrix tables: every column except housekeeping and governance.
RACM_TABLES = ("racm_objectives", "racm_risks", "racm_controls", "racm_tests", "racm_evidence")
for _t in RACM_TABLES:
    TRACKED[_t] = {"all_but": tuple(_RACM_SKIP), "accept_flag": "accepted"}

_RESOLVED: dict[str, dict] = {}


def _spec_for(obj) -> dict | None:
    """The tracking spec for this object's table, with "all_but" resolved to
    the actual column list once per table."""
    table = getattr(obj, "__tablename__", None)
    spec = TRACKED.get(table)
    if spec is None:
        return None
    if "all_but" not in spec:
        return spec
    if table not in _RESOLVED:
        exclude = (_HOUSEKEEPING | set(spec["all_but"])
                   | {spec.get("accept_flag"), spec.get("run_column"), spec.get("ai_flag")})
        cols = tuple(c.key for c in inspect(obj).mapper.column_attrs if c.key not in exclude)
        _RESOLVED[table] = {**spec, "fields": cols}
    return _RESOLVED[table]


def _is_ai_record(obj, spec) -> bool:
    if getattr(obj, "origin", None) == "ai":
        return True
    flag = spec.get("ai_flag")
    return bool(flag and getattr(obj, flag, False))


def _run_for(obj, spec, field=None) -> str | None:
    col = (spec.get("run_columns") or {}).get(field) or spec.get("run_column")
    return getattr(obj, col, None) if col else None


# ── Who ──────────────────────────────────────────────────────────────────────
async def actor_from_request(request: Request) -> None:
    """FastAPI dependency: remember who this request says it is.

    Async on purpose — a sync dependency runs in a worker thread, and the
    context variable it set would never reach the endpoint.
    """
    raw = request.headers.get(ACTOR_HEADER) or ""
    actor = unquote(raw).strip()[:100]
    _HUMAN.set(actor or "unknown")


def _who() -> tuple[str, str, bool, str | None]:
    """(actor_kind, actor, verified, run_id) for the write happening now."""
    from services.agent_ledger import current_context

    ctx = current_context()
    if ctx.get("agent"):
        return "ai", str(ctx["agent"]), False, ctx.get("run_id")
    human = _HUMAN.get()
    if human:
        return "human", human, False, None
    return "system", "system", False, ctx.get("run_id")


def current_human() -> str | None:
    """The person behind the current request, for code that has to name them —
    `accepted_by` on a spine node — rather than trusting a payload to."""
    return _HUMAN.get()


# ── The listener ─────────────────────────────────────────────────────────────
def _value(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _dump(v) -> str | None:
    return None if v is None else json.dumps(_value(v), ensure_ascii=False, default=str)


def _same(a, b) -> bool:
    """None and "" are the same nothing; surrounding whitespace is not a change."""
    norm = lambda x: "" if x is None else (x.strip() if isinstance(x, str) else x)  # noqa: E731
    return norm(a) == norm(b)


def _row(obj, field, before, after, decision, kind, actor, verified, run_id) -> FieldEdit:
    return FieldEdit(
        engagement_id=getattr(obj, "engagement_id", None),
        entity=obj.__tablename__, entity_id=str(obj.id), field=field,
        before=_dump(before), after=_dump(after),
        actor_kind=kind, actor=actor, actor_verified=verified,
        decision=decision, run_id=run_id,
    )


def _snapshot(obj, fields) -> dict:
    return {f: _value(getattr(obj, f, None)) for f in fields
            if getattr(obj, f, None) not in (None, "", "[]", "{}")}


def _before_flush(session: Session, _flush_context, _instances) -> None:
    if _PAUSED.get():
        return
    kind, actor, verified, ctx_run = _who()
    rows: list[FieldEdit] = []

    for obj in list(session.new):
        spec = _spec_for(obj)
        if spec is None or getattr(obj, "id", None) is None:
            continue
        snap = _snapshot(obj, spec["fields"])
        if not snap:
            continue  # an empty shell (e.g. a scan's status row) is not a decision
        is_ai = _is_ai_record(obj, spec) or kind == "ai"
        run_id = ctx_run or _provenance_run(obj) or _run_for(obj, spec)
        if is_ai:
            # A node marked origin='ai' outside any agent run (the deterministic
            # scoping engine runs inside the request) is still a machine's
            # proposal — named as unattributed rather than as the person.
            who = actor if kind == "ai" else "unattributed agent"
            rows.append(_row(obj, "*", None, snap, "proposed", "ai", who, False, run_id))
        else:
            rows.append(_row(obj, "*", None, snap, "created", kind, actor, verified, run_id))

    for obj in list(session.dirty):
        spec = _spec_for(obj)
        if spec is None or not session.is_modified(obj, include_collections=False):
            continue
        state = inspect(obj)
        for field in spec["fields"]:
            hist = state.attrs[field].history
            if not hist.has_changes():
                continue
            before = hist.deleted[0] if hist.deleted else None
            after = hist.added[0] if hist.added else None
            if _same(before, after):
                continue
            # For an AI write, the record's own run column is the more specific
            # answer (a lens summary belongs to its lens, not the whole scan).
            run_id = ctx_run
            if kind == "ai":
                run_id = _run_for(obj, spec, field) or run_id
            # A model writing a value is a proposal, even into an existing
            # record: the finding drafter replaces what the auditor typed, and
            # what it replaced is kept as `before`.
            rows.append(_row(obj, field, before, after,
                             "proposed" if kind == "ai" else "modified",
                             kind, actor, verified, run_id))
        flag = spec.get("accept_flag")
        if flag:
            hist = state.attrs[flag].history
            if hist.has_changes() and hist.added and hist.added[0] and not (hist.deleted and hist.deleted[0]):
                rows.append(_row(obj, "*", None, None, "accepted", kind, actor, verified, None))

    for obj in list(session.deleted):
        spec = _spec_for(obj)
        if spec is None:
            continue
        snap = _snapshot(obj, spec["fields"])
        flag = spec.get("accept_flag")
        decided = bool(getattr(obj, flag, None)) if flag else True
        unaccepted_ai = _is_ai_record(obj, spec) and not decided
        if unaccepted_ai:
            # A person removing a proposal rejects it; an agent clearing its own
            # earlier proposals on a re-run supersedes them. Different events.
            decision = "superseded" if kind == "ai" else "rejected"
        else:
            decision = "deleted"
        rows.append(_row(obj, "*", snap, None, decision, kind, actor, verified, ctx_run))

    for row in rows:
        session.add(row)


def _provenance_run(obj) -> str | None:
    """A spine node written by an agent names its run in its provenance JSON."""
    raw = getattr(obj, "provenance", None)
    if not raw:
        return None
    try:
        return (json.loads(raw) or {}).get("run_id")
    except (ValueError, TypeError, AttributeError):
        return None


_INSTALLED = False


def install() -> None:
    """Attach the listener to every session. Idempotent; called at import of main."""
    global _INSTALLED
    if not _INSTALLED:
        event.listen(Session, "before_flush", _before_flush)
        _INSTALLED = True


# ── Reading it back ──────────────────────────────────────────────────────────
async def history(entity: str, entity_id: str) -> dict:
    """Every recorded change to one record, oldest first, with what the ledger
    says about the AI runs behind them."""
    from database import AsyncSessionLocal
    from models.agent_call import AgentCall

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(FieldEdit).where(FieldEdit.entity == entity, FieldEdit.entity_id == entity_id)
            .order_by(FieldEdit.created_at, FieldEdit.id)
        )).scalars().all()
        run_ids = {r.run_id for r in rows if r.run_id}
        calls = (await db.execute(
            select(AgentCall).where(AgentCall.run_id.in_(run_ids))
        )).scalars().all() if run_ids else []
        first = (await db.execute(select(FieldEdit.created_at).order_by(FieldEdit.created_at).limit(1))).scalar()

    by_run: dict[str, list] = {}
    for c in calls:
        by_run.setdefault(c.run_id, []).append(c)

    def run_info(run_id):
        if not run_id:
            return None
        mine = by_run.get(run_id)
        if not mine:
            # Said, not left blank: an AI proposal whose run never reached the
            # ledger cannot name its model, and the reader should know that.
            return {"run_id": run_id, "linked": False}
        return {
            "run_id": run_id, "linked": True,
            "models": sorted({c.model for c in mine if c.model}),
            "prompt_versions": sorted({c.prompt_version for c in mine if getattr(c, "prompt_version", None)}),
            "calls": len(mine),
            "cost_usd": round(sum(c.cost_usd or 0 for c in mine), 5),
        }

    return {
        "entity": entity, "entity_id": entity_id,
        "recorded_since": first.isoformat() if first else None,
        "rows": [{
            "at": r.created_at.isoformat() if r.created_at else None,
            "field": r.field, "decision": r.decision,
            "actor_kind": r.actor_kind, "actor": r.actor, "actor_verified": r.actor_verified,
            "before": json.loads(r.before) if r.before else None,
            "after": json.loads(r.after) if r.after else None,
            "run": run_info(r.run_id),
        } for r in rows],
    }


_OUTCOMES = ("unchanged", "changed_by_person", "rejected", "superseded", "created_by_person")


def _outcome(rows) -> str | None:
    """What became of one record, from its register rows oldest first.

    Order matters: a person's edit counts only if it came after the platform's
    last proposal — when the drafter rewrites a field a person changed, what
    stands is the drafter's text again. A record with no decision step (a
    finding, an observation) is "unchanged" while it stands, never "open".
    """
    ai = human_created = changed = False
    end = None
    for r in rows:
        if r.decision == "proposed" and r.actor_kind == "ai":
            ai, changed = True, False
        elif r.decision == "created" and r.actor_kind == "human":
            human_created = True
        elif r.decision == "modified" and r.actor_kind == "human":
            changed = True
        elif r.decision == "rejected" or (r.decision == "deleted" and r.actor_kind == "human"):
            end = "rejected"
        elif r.decision in ("superseded", "deleted"):
            end = "superseded"
    if ai:
        return end or ("changed_by_person" if changed else "unchanged")
    if human_created and end is None:
        return "created_by_person"
    return None  # made by the system, or a person's own record they removed


async def profile(engagement_id: str) -> dict:
    """What happened to each record of this audit since the register started,
    per kind: the platform's proposals kept unchanged, changed by a person,
    rejected or replaced by a re-run, and the records people made themselves.

    Replaced proposals are reported but are not part of the file any more.
    Scope items and key audit questions have no engagement column, so their
    rows are found through the audit's scope — those still in it, that is: a
    deleted item's rows can no longer be tied to an audit.
    """
    from database import AsyncSessionLocal
    from services.ai_share import scope_item_ids

    async with AsyncSessionLocal() as db:
        _, item_ids = await scope_item_ids(db, engagement_id)
        cond = FieldEdit.engagement_id == engagement_id
        if item_ids:
            cond = cond | FieldEdit.entity_id.in_(item_ids)
        rows = (await db.execute(
            select(FieldEdit).where(cond).order_by(FieldEdit.created_at, FieldEdit.id)
        )).scalars().all()
        first = (await db.execute(select(FieldEdit.created_at).order_by(FieldEdit.created_at).limit(1))).scalar()

    per_record: dict[tuple, list] = {}
    for r in rows:
        per_record.setdefault((r.entity, r.entity_id), []).append(r)

    kinds: dict[str, dict] = {}
    for (entity, _), record_rows in per_record.items():
        outcome = _outcome(record_rows)
        if outcome:
            bucket = kinds.setdefault(entity, {"key": entity, **{o: 0 for o in _OUTCOMES}})
            bucket[outcome] += 1
    return {"recorded_since": first.isoformat() if first else None, "kinds": list(kinds.values())}
