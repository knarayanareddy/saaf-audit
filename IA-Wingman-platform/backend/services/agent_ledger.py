"""Writing and reading the spend ledger.

Two jobs, and they are opposite sides of the same question.

Writing: every call to a model leaves a row, whether it succeeded or not. A run
that was cut off still cost what it cost, and a ledger that only records the
successes would understate the bill exactly when it matters — when something is
going wrong repeatedly.

Reading: what has this engagement spent, and on what. That is what turns the
copilot's budget from "twenty tasks, whatever those cost" into a number an
auditor recognises, and what lets the run receipt in the UI survive a refresh.

The engagement a call belongs to is carried on a ContextVar rather than threaded
through fifty signatures. Callers open `agent_context(...)` around the work; a
call made outside one is still recorded, just without an owner.
"""
from __future__ import annotations

import json
import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_call import AgentCall

logger = logging.getLogger("ia.wingman")

_CONTEXT: ContextVar[dict] = ContextVar("ia_agent_context", default={})


@contextmanager
def agent_context(engagement_id: str | None = None, agent: str | None = None,
                  run_id: str | None = None, task_id: str | None = None,
                  record: bool | None = None):
    """Say who the next model calls are for, so the ledger can attribute them.

    Nested contexts merge rather than replace, so a service can name itself
    without having to know the engagement its caller already established.

    `record=False` suppresses writing altogether. That exists for the test
    suites, which drive the agents with a scripted client: those calls never
    happened and must not appear in a record of what was spent.
    """
    current = dict(_CONTEXT.get())
    for key, value in (("engagement_id", engagement_id), ("agent", agent),
                       ("run_id", run_id), ("task_id", task_id), ("record", record)):
        if value is not None:
            current[key] = value
    token = _CONTEXT.set(current)
    try:
        yield current
    finally:
        _CONTEXT.reset(token)


def current_context() -> dict:
    return dict(_CONTEXT.get())


#: Modules that carry a model call rather than make one. A frame inside these is
#: plumbing, and naming it would attribute every call in the platform to
#: `ai_service.run_agent_to_json`.
_PLUMBING = ("services.ai_service", "services.agent_contract", "services.agent_ledger")


def attributed(fn, engagement_id: str | None, agent: str | None = None,
               run_id: str | None = None):
    """Wrap a background task so the model calls inside it have an owner.

    Every agent in this platform runs as a background task, and the router that
    launches it knows both facts — it has just written an `AgentRun` naming the
    engagement and the agent_type. Neither reached the ledger: 27 of the first 34
    calls had no engagement, so "N calls on this audit · $X" counted about one
    call in five and looked like the whole bill.

    A wrapper rather than a `with` block inside each agent, because the
    declaration belongs where the launch is: next to the AgentRun row that says
    the same thing, so a reader sees both at once and a new agent that forgets
    one has forgotten the other too.

    The context lives inside the coroutine, so two tasks launched from the same
    request cannot inherit each other's owner — which a ContextVar set at the top
    of a task body, with no block to leave, is exactly how it would happen.
    """
    async def runner(*args, **kwargs):
        with agent_context(engagement_id=engagement_id, agent=agent, run_id=run_id):
            return await fn(*args, **kwargs)

    runner.__name__ = getattr(fn, "__name__", "task")
    return runner


def caller_of(limit: int = 25) -> str:
    """`module.function` of the first frame outside the model plumbing.

    Recorded on every row, beside whatever `agent_context` declared. Three
    callers in the whole platform open that context, so the ledger could name
    the agent behind 1 of its first 20 untyped calls — leaving a record of what
    was spent that could not say on whose behalf, which is most of its job.

    This is an observation, not a declaration: it says where the call was made,
    which is a fact, and does not infer an agent key from it. A module that wants
    to be named as an agent still says so itself.
    """
    frame = sys._getframe(1)
    for _ in range(limit):
        if frame is None:
            break
        module = frame.f_globals.get("__name__", "")
        if module and not module.startswith(_PLUMBING):
            return f"{module.rsplit('.', 1)[-1]}.{frame.f_code.co_name}"[:80]
        frame = frame.f_back
    return ""


async def record_call(meta, ok: bool = True, error: str | None = None,
                      sources: dict | None = None) -> None:
    """Write one row. Best-effort: never breaks the agent it was recording."""
    ctx = _CONTEXT.get()
    if ctx.get("record") is False:
        return
    # Read before the session opens, so the frame walked is the caller's and not
    # SQLAlchemy's.
    caller = caller_of()
    try:
        async with AsyncSessionLocal() as db:
            db.add(AgentCall(
                id=str(uuid4()),
                engagement_id=ctx.get("engagement_id"),
                agent=ctx.get("agent"),
                schema=getattr(meta, "schema", None) or None,
                tier=getattr(meta, "tier", None) or None,
                model=getattr(meta, "model", None) or None,
                duration_ms=getattr(meta, "duration_ms", 0) or 0,
                input_tokens=getattr(meta, "input_tokens", 0) or 0,
                output_tokens=getattr(meta, "output_tokens", 0) or 0,
                cached_tokens=getattr(meta, "cached_tokens", 0) or 0,
                cache_write_tokens=getattr(meta, "cache_write_tokens", 0) or 0,
                prompt_version=getattr(meta, "prompt_version", None) or None,
                reasoned=bool(getattr(meta, "reasoned", False)),
                thinking_tokens=getattr(meta, "thinking_tokens", 0) or 0,
                cost_usd=getattr(meta, "cost_usd", None),
                stop_reason=(getattr(meta, "stop_reason", None) or None),
                repaired=bool(getattr(meta, "repaired", False)),
                repair=(getattr(meta, "repair", "") or None),
                caller=caller or None,
                ok=ok,
                error=(error or None) and str(error)[:200],
                sources=json.dumps(sources) if sources else None,
                run_id=ctx.get("run_id"),
                task_id=ctx.get("task_id"),
            ))
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not record an agent call in the ledger: %s", exc)


async def reprice() -> dict:
    """Recompute every stored cost from its tokens and the current price table.

    A row's cost is not a fact the way its tokens are: it is arithmetic on a
    price somebody typed in. When that price was wrong — and it was, for months,
    1.5x to 3x too high — the stored figures are wrong with it, and nothing reads
    them back except to repeat the error. So they are recomputed from the
    tokens, which were measured, and never edited.

    Rows for a model with no price stay None rather than becoming a guess.
    Returns the totals before and after, so the correction is a number someone
    can check rather than something that silently happened.
    """
    from services.model_tiers import cost_usd

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(AgentCall))).scalars().all()
        before = sum(r.cost_usd or 0.0 for r in rows)
        changed = 0
        for r in rows:
            # Rows from before cache writes were recorded carry NULL there; they
            # are repriced with what was measured, and stay an under-count by
            # exactly the writes nobody recorded.
            new = cost_usd(r.model or "", r.input_tokens or 0, r.output_tokens or 0,
                           r.cached_tokens or 0, r.cache_write_tokens or 0)
            if new != r.cost_usd:
                r.cost_usd = new
                changed += 1
        await db.commit()
        after = sum(r.cost_usd or 0.0 for r in rows)
    return {"rows": len(rows), "changed": changed,
            "total_before": round(before, 4), "total_after": round(after, 4)}


async def spend_for(engagement_id: str, since: timedelta | None = None) -> dict:
    """What this engagement has spent, and how confident that figure is.

    `unpriced` is reported alongside the total rather than folded into it: a
    total that silently treats unpriced calls as free would be the same class of
    comfortable falsehood this codebase has spent several layers removing.
    """
    async with AsyncSessionLocal() as db:
        q = select(AgentCall).where(AgentCall.engagement_id == engagement_id)
        if since is not None:
            q = q.where(AgentCall.started_at >= datetime.now(timezone.utc) - since)
        rows = (await db.execute(q)).scalars().all()

    priced = [r for r in rows if r.cost_usd is not None]
    total = sum(r.cost_usd for r in priced)
    by_tier: dict[str, float] = {}
    for r in priced:
        by_tier[r.tier or "unknown"] = by_tier.get(r.tier or "unknown", 0.0) + r.cost_usd

    return {
        "calls": len(rows),
        "failed": sum(1 for r in rows if not r.ok),
        # Reported rather than folded into the successes: a reply that had to be
        # cut into shape before it would parse is a call that nearly failed, and
        # counting it as clean is how a path losing one run in two looked healthy.
        "repaired": sum(1 for r in rows if r.repaired),
        "total_usd": round(total, 4),
        "unpriced_calls": len(rows) - len(priced),
        "by_tier": {k: round(v, 4) for k, v in sorted(by_tier.items())},
        "input_tokens": sum(r.input_tokens for r in rows),
        "output_tokens": sum(r.output_tokens for r in rows),
        "thinking_tokens": sum(r.thinking_tokens for r in rows),
    }


async def recent_calls(engagement_id: str, limit: int = 20) -> list[dict]:
    """The last calls on this engagement, newest first — the run history."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(AgentCall)
            .where(AgentCall.engagement_id == engagement_id)
            .order_by(AgentCall.started_at.desc())
            .limit(min(limit, 100))
        )).scalars().all()

    out = []
    for r in rows:
        try:
            sources = json.loads(r.sources) if r.sources else None
        except (ValueError, TypeError):
            sources = None
        out.append({
            "id": r.id, "agent": r.agent, "schema": r.schema, "tier": r.tier, "model": r.model,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "duration_ms": r.duration_ms,
            "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
            "cached_tokens": r.cached_tokens, "thinking_tokens": r.thinking_tokens,
            "reasoned": r.reasoned, "prompt_version": r.prompt_version,
            "cost_usd": r.cost_usd, "stop_reason": r.stop_reason, "repaired": r.repaired,
            "repair": r.repair, "caller": r.caller,
            "ok": r.ok, "error": r.error, "sources": sources,
        })
    return out


async def repair_report(since: timedelta | None = None) -> list[dict]:
    """Per call site: how many of its replies had to be fixed, and how many were lost.

    This is the list the remaining untyped call sites are migrated in the order
    of. Forty of them still ask for JSON in prose, and rebuilding all forty on
    the strength of what happened to the work program would be the same guess in
    the other direction — some of those prompts ask for three fields and have
    never failed.

    `typed` says whether the call already goes through a schema. A typed row that
    still shows repairs is a different finding: there the model corrected itself,
    which the contract is for.
    """
    async with AsyncSessionLocal() as db:
        q = select(AgentCall)
        if since is not None:
            q = q.where(AgentCall.started_at >= datetime.now(timezone.utc) - since)
        rows = (await db.execute(q)).scalars().all()

    sites: dict[str, dict] = {}
    for r in rows:
        site = sites.setdefault(r.caller or "<unrecorded>", {
            "caller": r.caller or "<unrecorded>", "calls": 0, "repaired": 0,
            "failed": 0, "typed": 0, "untyped": 0, "repairs": {}, "agents": set(),
        })
        site["calls"] += 1
        site["repaired"] += bool(r.repaired)
        site["failed"] += (not r.ok)
        site["typed" if r.schema else "untyped"] += 1
        if r.repair:
            site["repairs"][r.repair] = site["repairs"].get(r.repair, 0) + 1
        if r.agent:
            site["agents"].add(r.agent)

    out = []
    for site in sites.values():
        site["agents"] = sorted(site["agents"])
        out.append(site)
    # Most carried first, then most used: the order to spend effort in.
    out.sort(key=lambda s: (s["repaired"] + s["failed"], s["calls"]), reverse=True)
    return out
