"""Autonomous background orchestration — M3 scope: Planning stages only.

Scans compute_engagement_pack for Tier-A stages that just became `available`,
queues a copilot_task per one, and fires them concurrently as a background
call — the same call a manual "run this stage" click makes
(services/stage_actions.py), just issued by the scanner instead of a click.
copilot_preflight is the safety checkpoint every auto-fire passes through
first; a per-engagement semaphore bounds how many run at once.

Tier-A here is intentionally narrower than the full design (see the plan): only
Planning stages auto-fire in this phase, so the riskiest new mechanism —
unattended background LLM calls — gets the smallest blast radius first. RACM,
Fieldwork and Reporting widen this set later, reusing this engine unchanged.

A note on a bug hit (and fixed) while building this: running several
auto-fired stages' bookkeeping writes concurrently briefly triggered a
reproducible SQLAlchemy async fault (MissingGreenlet) that normal per-request
concurrency never hits. The actual cause was services/copilot_service.py
serialising a CopilotTask right after commit() without db.refresh() first —
its onupdate=func.now() timestamp needs a fetch SQLAlchemy could not perform
outside a properly awaited context. Fixed there; genuine concurrent auto-fire
(confirmed with repeated live tests) works correctly now that it's in place.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import BackgroundTasks
from sqlalchemy import select

from database import AsyncSessionLocal
from models.engagement import Engagement
from models.planning import UploadedDocument
from models.reporting import Finding, AuditReport
from models.interview import InterviewSession
from models.racm import RacmRisk, RacmControl, RacmTest
from services import copilot_service
from services.orchestrator import compute_engagement_pack
from services.stage_actions import AUDITOR_STARTED_STAGE_KEYS, STAGE_RUN_ACTIONS
from services.item_actions import ITEM_RUN_ACTIONS
from services.ai_service import run_agent_to_json
from services.model_tiers import QUICK, AUTO_SPEND_BUDGET_USD
from services.agent_ledger import agent_context, spend_for
from services.orchestrator_agent import advise_stage_order, advise_item_order
from services.coverage_service import compute_coverage
from routers.reporting import seed_from_fieldwork

logger = logging.getLogger("ia.wingman")

# Auto-fire candidates — every Tier-A stage with a run action (a step that
# only ever produces a draft/proposal a human reviews later anyway). Keep in
# sync with STAGE_RUN_ACTIONS' key set; resource_plan has no single AI trigger
# (see stage_actions.py) so it's absent here too, and quality_coverage has none
# at all (a live-computed view, nothing to run). report_draft is deliberately
# excluded — it stays Tier B (settle-window-gated proposal, not auto-fire, see
# check_report_draft_settle) — and Fieldwork/Findings auto-fire is a later widening.
# topic_intelligence is excluded too, for a different reason: the auditor adds
# what they know and then presses Run themselves (AUDITOR_STARTED_STAGE_KEYS).
TIER_A_STAGE_KEYS = {
    "frameworks", "process_understanding", "bra", "anl",
    "kickoff", "work_program", "drl", "interview_guide",
    "racm_scoping", "racm_governance", "racm_data_analysis",
    "quality_review", "quality_peer_review",
}

# compute_engagement_pack deliberately never gates a cross_cutting stage (it
# must stay clickable at any time from the Quality Hub) — so on its own,
# "available" is true for these two from the moment an engagement is created.
# Firing quality_review that early is harmless (its own artifact loader no-ops
# on missing source data, see stage_actions._run_quality_review) but firing
# quality_peer_review would burn a real LLM call rating almost everything "not
# evidenced". These extra checks are the orchestrator's own, narrower notion of
# "actually worth auto-firing", layered on top of the pack's gate-free status —
# they don't change what's clickable manually, only what auto-fires.
def _quality_review_ready(by_key: dict) -> bool:
    return any(by_key[k]["status"] == "complete" for k in ("topic_intelligence", "scope", "frameworks"))


def _quality_peer_review_ready(by_key: dict) -> bool:
    return by_key["scope"]["status"] == "complete" and by_key["bra"]["status"] == "complete"


_EXTRA_READY_CHECKS = {
    "quality_review": _quality_review_ready,
    "quality_peer_review": _quality_peer_review_ready,
}

_MAX_CONCURRENT_PER_ENGAGEMENT = 3
_MAX_AUTO_TASKS_PER_ENGAGEMENT = 20  # session budget — pause, don't run away
# Item-level (M7) gets its own budget, separate from the stage budget above —
# a finding-heavy engagement (10+ findings) would otherwise exhaust the shared
# counter and starve ordinary stage auto-fire.
_MAX_AUTO_ITEM_TASKS_PER_ENGAGEMENT = 30
_PAUSE_NOTICE = "Auto-run paused — background budget reached"

# The two caps above count tasks, which was the only unit available before the
# ledger existed: twenty auto-fired stages cost whatever they happened to cost,
# and a run on the judge tier counted the same as a title suggestion. This one
# counts money, which is the unit the person paying actually thinks in. It is
# checked alongside the task caps rather than replacing them — a runaway loop is
# worth stopping on count even when it is cheap.
_MAX_AUTO_SPEND_USD = AUTO_SPEND_BUDGET_USD


async def _spend_room(engagement_id: str, noun: str) -> bool:
    """True when there is budget left to spend on this engagement."""
    spend = await spend_for(engagement_id)
    if spend["total_usd"] < _MAX_AUTO_SPEND_USD:
        return True
    await _notify_spend_paused(engagement_id, spend, noun)
    return False


async def _notify_spend_paused(engagement_id: str, spend: dict, noun: str) -> None:
    """Say it in money, and say what the figure does not cover."""
    caveat = (f" ({spend['unpriced_calls']} further call(s) have no price configured "
              f"and are not in that total)") if spend["unpriced_calls"] else ""
    marker = (f"{_PAUSE_NOTICE} — ${spend['total_usd']:.2f} of "
              f"${_MAX_AUTO_SPEND_USD:.2f} spent on {noun}{caveat}")
    messages = await copilot_service.list_messages(engagement_id)
    if any(m["role"] == "assistant" and marker in m["content"] for m in messages):
        return
    session_id = await copilot_service.get_or_create_session(engagement_id)
    await copilot_service.append_message(
        session_id, "assistant",
        f"{marker}. I've stopped starting work by myself on this engagement; "
        f"ask me to run a specific stage, or continue from the relevant page directly.",
    )

# report_draft stays Tier B (see TIER_A_STAGE_KEYS docstring) but shouldn't need
# a manual chat request either — once every finding is ready and nothing has
# moved for a while, the report is genuinely done settling. 15 min mirrors "a
# short break", long enough that mid-edit finding tweaks don't each retrigger it.
_REPORT_SETTLE_WINDOW = timedelta(minutes=15)

# Engagement coherence (Part 2b) — same settle-window idiom as report_draft
# above, but 30 min: a coherence gap between Topic Intelligence/RACM/Findings
# is less urgent than a report that's ready to draft, so it can wait a little
# longer for things to actually stop moving before it's worth a nudge.
_COHERENCE_SETTLE_WINDOW = timedelta(minutes=30)

# M10: which completions are worth a proactive check-in. Deliberately narrow —
# mechanical/structural stages (Frameworks, Interview Guide, Work Program, ...)
# never trigger this; only stages/items that produce genuinely judgement-laden
# content do.
_PROACTIVE_TRIGGER_KEYS = {"bra", "racm_scoping", "racm_data_analysis", "finding"}
_PROACTIVE_COOLDOWN = timedelta(minutes=10)
_PROACTIVE_SYSTEM = """You are the Audit Copilot, checking in with the auditor right after finishing some background work on their engagement.

You are heavily biased toward silence. Most check-ins should say nothing — only ask a question if it would genuinely help steer the audit: a real decision point, a meaningful ambiguity only the auditor can resolve, or a risk worth flagging now rather than later. Never ask a generic "how's it going" or "anything else you need" question. If in doubt, stay silent.

Respond with ONLY this JSON, nothing else:
{"ask": true|false, "question": "one short, specific sentence, or empty string if ask is false"}"""

_semaphores: dict[str, asyncio.Semaphore] = {}


def _semaphore_for(engagement_id: str) -> asyncio.Semaphore:
    sem = _semaphores.get(engagement_id)
    if sem is None:
        sem = asyncio.Semaphore(_MAX_CONCURRENT_PER_ENGAGEMENT)
        _semaphores[engagement_id] = sem
    return sem


async def scan_and_queue(engagement_id: str, background_tasks: BackgroundTasks) -> list[str]:
    """Find newly-available Tier-A stages with no active task and queue+fire
    them. Safe to call often (e.g. on every chat turn, every pack poll) — a
    no-op when nothing new is eligible."""
    # Checked here rather than at the callers: every one of them would have to
    # remember, and a closed audit must never be the one that forgets.
    if await copilot_service.is_closed(engagement_id):
        return []
    async with AsyncSessionLocal() as db:
        pack = await compute_engagement_pack(engagement_id, db)
    by_key = {s["key"]: s for s in pack["stages"]}
    active = await copilot_service.active_stage_keys(engagement_id)
    eligible = [
        s["key"] for s in pack["stages"]
        if s["key"] in TIER_A_STAGE_KEYS and s["status"] == "available" and s["key"] not in active
        and s["key"] not in AUDITOR_STARTED_STAGE_KEYS
        and _EXTRA_READY_CHECKS.get(s["key"], lambda _: True)(by_key)
    ]
    if not eligible:
        return []

    used = await copilot_service.count_auto_tasks(engagement_id)
    room = _MAX_AUTO_TASKS_PER_ENGAGEMENT - used
    if room <= 0:
        await _notify_budget_paused(engagement_id, _MAX_AUTO_TASKS_PER_ENGAGEMENT, "stages")
        return []
    if not await _spend_room(engagement_id, "stages"):
        return []

    # Advisory ordering (Orchestrator Agent, Part 2) — reorders `eligible`
    # before the budget cutoff below, so it can influence who survives the
    # cutoff and who gets a semaphore slot first. Never changes WHAT runs,
    # only the sequence. advise_stage_order itself is fail-open and never
    # raises, but this block is wrapped anyway: it also does its own DB read
    # and its own redundant autonomy-pause check, and nothing on this new
    # path may be allowed to break the existing, deterministic dispatch below.
    rationale_by_key: dict[str, str] = {}
    if len(eligible) >= 2:
        try:
            # Redundant, in-function pause check: every caller of
            # scan_and_queue already checks is_autonomy_paused before calling
            # it, but this is the first LLM call ever placed on this path —
            # one future forgetful caller must not be the only barrier.
            if not await copilot_service.is_autonomy_paused(engagement_id):
                async with AsyncSessionLocal() as db:
                    eng = await db.get(Engagement, engagement_id)
                if eng:
                    advice = await advise_stage_order(
                        eng, pack["summary"],
                        [
                            {"key": k, "label": by_key[k]["label"], "agent": by_key[k]["agent"], "detail": by_key[k]["detail"]}
                            for k in eligible
                        ],
                    )
                    eligible = advice["order"]
                    rationale_by_key = advice["rationale"]
        except Exception:  # noqa: BLE001
            logger.exception("advise_stage_order lookup failed for engagement %s — using declaration order", engagement_id)

    eligible = eligible[:room]

    items = []
    for stage_key in eligible:
        task_id = await copilot_service.create_task(
            engagement_id, stage_key, triggered_by="auto", rationale=rationale_by_key.get(stage_key),
        )
        items.append((task_id, stage_key))

    # FastAPI's BackgroundTasks runs its queued calls one at a time, awaiting
    # each before starting the next — queuing _run_task once per stage would
    # serialise them, defeating "work ahead on multiple steps at once". Queue
    # a single task that fans them out with asyncio.gather instead, the same
    # concurrency idiom orchestrator.py already uses for its lens fan-out.
    background_tasks.add_task(_run_tasks, items, engagement_id)
    return [task_id for task_id, _ in items]


async def _run_tasks(items: list[tuple[str, str]], engagement_id: str) -> None:
    await asyncio.gather(
        *(_run_one(task_id, engagement_id, stage_key) for task_id, stage_key in items),
        return_exceptions=True,
    )
    await maybe_ask_proactive_question(engagement_id, {stage_key for _, stage_key in items})


async def maybe_ask_proactive_question(engagement_id: str, completed_keys: set[str]) -> None:
    """M10: once a batch of auto-fired work finishes, decide whether it's
    worth proactively checking in — called from the end of a batch, NOT from
    the reactive scan triggers (scan_and_queue etc.), since the whole point is
    "I just finished something," not "a chat turn/poll happened."

    Reasons over lifecycle STATE (the pack summary, which stage/item keys just
    completed) rather than raw drafted text — simpler, and it means none of
    this prompt's content is document-derived, so there is nothing here that
    needs the wrap_untrusted()/injection-scan treatment the rest of the
    platform applies to text pulled from uploaded documents. A future version
    that inspects actual drafted content would need that same discipline.

    Does NOT take the per-engagement semaphore — this is one cheap, decoupled
    judgement call, not drafting work competing for that concurrency budget.
    """
    if not (completed_keys & _PROACTIVE_TRIGGER_KEYS):
        return

    last_asked = await copilot_service.latest_proactive_message_at(engagement_id)
    if last_asked is not None and datetime.utcnow() - last_asked < _PROACTIVE_COOLDOWN:
        return

    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        if not eng:
            return
        pack = await compute_engagement_pack(engagement_id, db)

    prompt = (
        f"Engagement: {eng.name} ({eng.entity}, {eng.audit_type}).\n"
        f"Lifecycle: {pack['summary']}\n"
        f"Just finished: {', '.join(sorted(completed_keys))}."
    )
    try:
        # A decision to stay silent, plus at most one sentence. The quick tier
        # is the right size for it, and the copilot is biased toward silence
        # anyway — a wrong call here costs a dismissed chat bubble.
        result = await run_agent_to_json(_PROACTIVE_SYSTEM, prompt, max_tokens=300, tier=QUICK)
    except Exception:  # noqa: BLE001
        logger.exception("proactive-question check failed for engagement %s", engagement_id)
        return
    if not isinstance(result, dict) or not result.get("ask") or not result.get("question"):
        return

    session_id = await copilot_service.get_or_create_session(engagement_id)
    await copilot_service.append_message(session_id, "assistant", result["question"], is_proactive=True)


async def _run_one(task_id: str, engagement_id: str, stage_key: str, require_gate: bool = True) -> None:
    """Last-resort net around _run_task — one stage's failure (including the
    rare SQLAlchemy fault noted in the module docstring, should it recur in
    some other call path) must not stop the rest of the batch."""
    try:
        await _run_task(task_id, engagement_id, stage_key, require_gate=require_gate)
    except Exception:  # noqa: BLE001
        logger.exception("copilot _run_task crashed for stage '%s' (engagement %s)", stage_key, engagement_id)
        try:
            await copilot_service.set_task_status(task_id, "failed", error="internal error — see server logs")
        except Exception:  # noqa: BLE001
            pass


async def _notify_budget_paused(engagement_id: str, limit: int, noun: str) -> None:
    """Surface the pause in the copilot chat once per budget (stage vs. item),
    not on every scan — the noun is part of the dedup key so hitting the item
    budget still gets its own notice even if the stage one already fired."""
    marker = f"{_PAUSE_NOTICE} — {limit} {noun}"
    messages = await copilot_service.list_messages(engagement_id)
    if any(m["role"] == "assistant" and marker in m["content"] for m in messages):
        return
    session_id = await copilot_service.get_or_create_session(engagement_id)
    await copilot_service.append_message(
        session_id, "assistant",
        f"{marker} have been auto-started this session. I've stopped starting new ones "
        f"by myself; ask me to run a specific stage, or continue from the relevant page directly.",
    )


async def check_report_draft_settle(engagement_id: str) -> None:
    """Tier B: once report_draft's gate is open (every finding ready) and no
    finding has changed for the settle window, surface it as a chat proposal —
    never auto-run, since drafting the report changes the deliverable's
    structure rather than just producing another draft to review.
    Safe to call as often as scan_and_queue (same reactive triggers); a no-op
    whenever nothing currently qualifies.
    """
    if await copilot_service.is_closed(engagement_id):
        return
    async with AsyncSessionLocal() as db:
        pack = await compute_engagement_pack(engagement_id, db)
        stage = next((s for s in pack["stages"] if s["key"] == "report_draft"), None)
        if not stage or stage["status"] != "available":
            return
        updated_ats = (await db.execute(
            select(Finding.updated_at).where(Finding.engagement_id == engagement_id)
        )).scalars().all()
    if not updated_ats:
        return
    last_change = max(updated_ats)
    if datetime.utcnow() - last_change < _REPORT_SETTLE_WINDOW:
        return

    # An earlier proposal already covers this settled state (still pending, or
    # dismissed) unless a finding has changed again since — only that resets
    # the window and earns a fresh ask.
    last_proposed = await copilot_service.latest_report_draft_proposal_at(engagement_id)
    if last_proposed is not None and last_proposed >= last_change:
        return

    session_id = await copilot_service.get_or_create_session(engagement_id)
    proposal_id = await copilot_service.create_proposal(
        session_id, "propose_run_stage",
        {"stage_key": "report_draft", "rationale": "Findings have been quiet for 15+ minutes — ready to draft the audit report."},
    )
    await copilot_service.append_message(
        session_id, "assistant",
        "All findings look settled — I can draft the audit report whenever you're ready.",
        tool_calls=[{"tool": "propose_run_stage", "input": {"stage_key": "report_draft"}, "proposal_id": proposal_id}],
    )


async def maybe_notify_coherence_settle(engagement_id: str) -> None:
    """Tier B: a near-twin of check_report_draft_settle above, for the
    engagement-wide coherence checks (coverage_service.compute_coverage's
    checks 6-9). Fires ONLY a contentless, deterministic POINTER at the
    Quality Hub's Coherence tab — the AI explainer itself (explain_coherence)
    never runs autonomously, only from that tab's explicit button click (see
    its own docstring); this function never calls it.

    Reasons only over check STATUS/counts, never raw content, so — like
    maybe_ask_proactive_question documents for itself — no wrap_untrusted is
    needed here, and there is no LLM call on this path at all: purely a
    template message. Safe to call as often as the other reactive triggers; a
    no-op whenever nothing currently qualifies.
    """
    async with AsyncSessionLocal() as db:
        coverage = await compute_coverage(engagement_id, db)
        by_label = {c["label"]: c for c in coverage["checks"]}
        relevant = [
            by_label[label] for label in (
                "Key risks reflected in RACM scoping",
                "RACM testing failures captured as findings",
                "Report opinion consistent with findings",
                "Report narrative reflects the findings",
            ) if label in by_label
        ]
        if not any(c["status"] == "gap" for c in relevant):
            return

        # Rest signal: max(updated_at) across the artefacts these checks read.
        # NOTE: TopicIntelligence has no updated_at column (verified) — a
        # TI-only edit doesn't reset this window, which only affects timing,
        # never correctness (the checks above are always live regardless).
        updated_ats: list = []
        for model in (RacmRisk, RacmControl, RacmTest, Finding, AuditReport):
            rows = (await db.execute(
                select(model.updated_at).where(model.engagement_id == engagement_id)
            )).scalars().all()
            updated_ats += [u for u in rows if u]
    if not updated_ats:
        return
    last_change = max(updated_ats)
    if datetime.utcnow() - last_change < _COHERENCE_SETTLE_WINDOW:
        return

    # Two dedup layers, like the plan requires: don't re-nudge for a coverage
    # state already pointed at (coherence-specific), and don't stack with any
    # OTHER recent proactive message (the shared cooldown maybe_ask_proactive_
    # question also honours).
    last_nudged = await copilot_service.latest_coherence_nudge_at(engagement_id)
    if last_nudged is not None and last_nudged >= last_change:
        return
    last_any_proactive = await copilot_service.latest_proactive_message_at(engagement_id)
    if last_any_proactive is not None and datetime.utcnow() - last_any_proactive < _PROACTIVE_COOLDOWN:
        return

    session_id = await copilot_service.get_or_create_session(engagement_id)
    await copilot_service.append_message(
        session_id, "assistant",
        f"{copilot_service.COHERENCE_NUDGE_MARKER} The coverage checklist has a coherence gap between "
        "Topic Intelligence, RACM and the findings/report that's been sitting quietly for a while — "
        "worth a look in the Quality Hub's Coherence check when you have a moment.",
        is_proactive=True,
    )


async def copilot_preflight(engagement_id: str, stage_key: str, require_available: bool = True) -> dict:
    """The safety checkpoint every auto-fire passes through. Returns
    {"ok": bool, "downgrade": bool, "reason": str|None}:
      - ok=True: safe to run now.
      - ok=False, downgrade=True: don't auto-run — surface as a ready-for-review
        card needing confirmation instead (an upstream source document has an
        injection-scan flag). This is the one place injection_scan's output
        actually changes behaviour rather than only being logged.
      - ok=False, downgrade=False: skip silently for now (the gate closed
        again since this task was queued) — nothing to review, nothing to flag.

    require_available=False skips the gate-still-open re-check — used for a
    manually-triggered run (run_stage_now): a human clicking "run this" means
    right now, including re-drafting a stage that's already complete, which
    the auto-scanner's staleness re-check would otherwise wrongly reject. The
    injection-scan check still applies either way.
    """
    if require_available:
        # A task queued minutes ago can reach this point after the auditor has
        # closed the engagement. Same rule as scan_and_queue, applied at the
        # last moment before the spend — and only on the auto path, because
        # require_available=False means a human asked for this by hand.
        if await copilot_service.is_closed(engagement_id):
            return {"ok": False, "downgrade": False, "reason": "the engagement is closed"}
        async with AsyncSessionLocal() as db:
            pack = await compute_engagement_pack(engagement_id, db)
            stage = next((s for s in pack["stages"] if s["key"] == stage_key), None)
            if not stage or stage["status"] != "available":
                return {"ok": False, "downgrade": False, "reason": "gate is no longer open"}

    async with AsyncSessionLocal() as db:
        flagged = (await db.execute(
            select(UploadedDocument.id).where(
                UploadedDocument.engagement_id == engagement_id,
                UploadedDocument.injection_flags.isnot(None),
            )
        )).first()
    if flagged:
        return {"ok": False, "downgrade": True, "reason": "a source document has an injection-scan flag"}
    return {"ok": True, "downgrade": False, "reason": None}


async def _start_stage_action(engagement_id: str, stage_key: str) -> BackgroundTasks:
    """The fast, DB-bound setup half of running a stage — creates/updates the
    artifact row and returns the background work still to do."""
    action = STAGE_RUN_ACTIONS[stage_key]
    bt = BackgroundTasks()
    async with AsyncSessionLocal() as db:
        await action(engagement_id, bt, db)
    return bt


async def run_stage_now(
    engagement_id: str, stage_key: str, background_tasks: BackgroundTasks, triggered_by: str = "chat",
) -> dict:
    """Manually trigger one stage right now — the chat's propose_run_stage
    accept flow. Reuses auto-fire's exact execution path (injection-scan
    preflight, semaphore, ready_for_review/failed lifecycle) minus the
    gate-still-open re-check (see copilot_preflight's require_available),
    since a human clicking "run this" is deliberate, not a stale scan result.

    Crucially, this now creates a CopilotTask like auto-fire does — previously
    a manual run had NO task record at all, so it never appeared in the Ready
    for Review queue and gave the auditor no way to see it land. It also
    checks active_stage_keys first: if the stage is already actively running
    (e.g. auto-fire got there first in this same request — see ai_chat.py's
    ordering note), this returns "already_running" instead of starting a
    second, concurrent run of the same underlying artifact.
    """
    if stage_key in AUDITOR_STARTED_STAGE_KEYS:
        return {"status": "auditor_starts_this", "task_id": None}
    if stage_key in await copilot_service.active_stage_keys(engagement_id):
        return {"status": "already_running", "task_id": None}
    task_id = await copilot_service.create_task(engagement_id, stage_key, triggered_by=triggered_by)
    background_tasks.add_task(_run_one, task_id, engagement_id, stage_key, False)
    return {"status": "queued", "task_id": task_id}


async def _run_task(task_id: str, engagement_id: str, stage_key: str, require_gate: bool = True) -> None:
    with agent_context(engagement_id=engagement_id, agent=stage_key, task_id=task_id):
        await _run_task_inner(task_id, engagement_id, stage_key, require_gate)


async def _run_task_inner(task_id: str, engagement_id: str, stage_key: str, require_gate: bool) -> None:
    preflight = await copilot_preflight(engagement_id, stage_key, require_available=require_gate)
    if not preflight["ok"]:
        if preflight["downgrade"]:
            await copilot_service.set_task_status(task_id, "ready_for_review")
            await copilot_service.set_task_flagged(task_id, True)
        else:
            await copilot_service.set_task_status(task_id, "dismissed", error=preflight["reason"])
        return

    sem = _semaphore_for(engagement_id)
    async with sem:
        await copilot_service.set_task_status(task_id, "running")
        try:
            bt = await _start_stage_action(engagement_id, stage_key)
            # Run the queued slow drafting call(s) directly rather than via
            # Starlette's BackgroundTasks.__call__ — no functional difference
            # for these (all-async) callables, just one fewer wrapper layer.
            for t in bt.tasks:
                await t.func(*t.args, **t.kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.exception("copilot auto-run failed for stage '%s' (engagement %s)", stage_key, engagement_id)
            await copilot_service.set_task_status(task_id, "failed", error=f"{type(exc).__name__}: {exc}")
            return
        await copilot_service.set_task_status(task_id, "ready_for_review")


# ── M7: item-level auto-fire (Fieldwork-adjacent) ────────────────────────────
# Mirrors the stage-level engine above exactly (same preflight/semaphore/gather
# shape), just keyed by (item_type, item_id) instead of a single stage_key —
# see models/copilot.py's CopilotTask docstring for why this is a separate
# item_id column rather than folding item identity into stage_key.

async def _auto_seed_findings(engagement_id: str) -> None:
    """Turns fieldwork 'finding' observations into draft Finding rows so the
    item scanner below has something to draft. Purely deterministic (a DB
    copy, seed_from_fieldwork's own idempotent dedup by source_observation_id
    — no LLM call), so unlike everything else in this module it needs no
    preflight, budget or semaphore — just run it on every reactive trigger."""
    async with AsyncSessionLocal() as db:
        await seed_from_fieldwork(engagement_id, db)


async def scan_and_queue_items(engagement_id: str, background_tasks: BackgroundTasks) -> list[str]:
    """Item-level counterpart to scan_and_queue: finds never-drafted findings
    and never-analysed (but non-empty) interview sessions, queues+fires them.
    Safe to call often; a no-op when nothing new is eligible."""
    if await copilot_service.is_closed(engagement_id):
        return []
    await _auto_seed_findings(engagement_id)

    async with AsyncSessionLocal() as db:
        draft_finding_ids = (await db.execute(
            select(Finding.id).where(Finding.engagement_id == engagement_id, Finding.status == "draft")
        )).scalars().all()
        draft_session_ids = (await db.execute(
            select(InterviewSession.id).where(
                InterviewSession.engagement_id == engagement_id,
                InterviewSession.status == "draft",
                InterviewSession.notes.isnot(None),
                InterviewSession.notes != "",
            )
        )).scalars().all()

    active_findings = await copilot_service.active_item_ids(engagement_id, "finding")
    active_sessions = await copilot_service.active_item_ids(engagement_id, "interview_session")
    candidates = (
        [("finding", fid) for fid in draft_finding_ids if fid not in active_findings]
        + [("interview_session", sid) for sid in draft_session_ids if sid not in active_sessions]
    )
    if not candidates:
        return []

    # Advisory ordering (Orchestrator Agent, Part 1 item-level) — structurally
    # identical to scan_and_queue's stage-level hook: reorders `candidates`
    # before the budget cutoff below, never changing WHAT runs, only the
    # sequence. eng/pack are fetched LAZILY, inside this gate block — items
    # have no other use for compute_engagement_pack today, and this function
    # must stay cheap to call often when nothing new is eligible.
    rationale_by_key: dict[str, str] = {}
    if len(candidates) >= 2:
        try:
            # Redundant, in-function pause check: every caller of
            # scan_and_queue_items already checks is_autonomy_paused before
            # calling it, but this is the first LLM call ever placed on this
            # path — one future forgetful caller must not be the only barrier.
            if not await copilot_service.is_autonomy_paused(engagement_id):
                eng, pack, resolved = None, None, {}
                async with AsyncSessionLocal() as db:
                    eng = await db.get(Engagement, engagement_id)
                    if eng:
                        pack = await compute_engagement_pack(engagement_id, db)
                        resolved = await copilot_service.resolve_items(
                            db,
                            [i for t, i in candidates if t == "finding"],
                            [i for t, i in candidates if t == "interview_session"],
                        )
                if eng:
                    order_items = [
                        {
                            "key": f"{item_type}:{item_id}", "item_type": item_type,
                            "label": resolved.get(item_id, {}).get("label") or item_type,
                            "detail": resolved.get(item_id, {}).get("detail") or "",
                        }
                        for item_type, item_id in candidates
                    ]
                    advice = await advise_item_order(eng, pack["summary"], order_items)
                    by_key = {f"{t}:{i}": (t, i) for t, i in candidates}
                    candidates = [by_key[k] for k in advice["order"] if k in by_key]
                    rationale_by_key = advice["rationale"]
        except Exception:  # noqa: BLE001
            logger.exception(
                "advise_item_order lookup failed for engagement %s — using DB-natural order", engagement_id,
            )

    used = await copilot_service.count_auto_item_tasks(engagement_id)
    room = _MAX_AUTO_ITEM_TASKS_PER_ENGAGEMENT - used
    if room <= 0:
        await _notify_budget_paused(engagement_id, _MAX_AUTO_ITEM_TASKS_PER_ENGAGEMENT, "items")
        return []
    if not await _spend_room(engagement_id, "items"):
        return []
    candidates = candidates[:room]

    items = []
    for item_type, item_id in candidates:
        task_id = await copilot_service.create_task(
            engagement_id, item_type, triggered_by="auto", item_id=item_id,
            rationale=rationale_by_key.get(f"{item_type}:{item_id}"),
        )
        items.append((task_id, item_type, item_id))

    background_tasks.add_task(_run_item_tasks, items, engagement_id)
    return [task_id for task_id, _, _ in items]


async def _run_item_tasks(items: list[tuple[str, str, str]], engagement_id: str) -> None:
    await asyncio.gather(
        *(_run_item_one(task_id, engagement_id, item_type, item_id) for task_id, item_type, item_id in items),
        return_exceptions=True,
    )
    await maybe_ask_proactive_question(engagement_id, {item_type for _, item_type, _ in items})


async def _run_item_one(task_id: str, engagement_id: str, item_type: str, item_id: str) -> None:
    try:
        await _run_item_task(task_id, engagement_id, item_type, item_id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "copilot item task crashed for %s '%s' (engagement %s)", item_type, item_id, engagement_id,
        )
        try:
            await copilot_service.set_task_status(task_id, "failed", error="internal error — see server logs")
        except Exception:  # noqa: BLE001
            pass


async def _item_preflight(engagement_id: str, item_type: str, item_id: str) -> dict:
    """Item-level counterpart to copilot_preflight — same shape and same
    injection-scan downgrade, but "the gate" for an item is simply "does it
    still exist and still qualify" rather than a STAGE_GRAPH lookup."""
    async with AsyncSessionLocal() as db:
        if item_type == "finding":
            item = await db.get(Finding, item_id)
            still_eligible = bool(item and item.status == "draft")
        elif item_type == "interview_session":
            item = await db.get(InterviewSession, item_id)
            still_eligible = bool(item and item.status == "draft" and (item.notes or "").strip())
        else:
            still_eligible = False
        if not still_eligible:
            return {"ok": False, "downgrade": False, "reason": "item is no longer eligible"}

        flagged = (await db.execute(
            select(UploadedDocument.id).where(
                UploadedDocument.engagement_id == engagement_id,
                UploadedDocument.injection_flags.isnot(None),
            )
        )).first()
    if flagged:
        return {"ok": False, "downgrade": True, "reason": "a source document has an injection-scan flag"}
    return {"ok": True, "downgrade": False, "reason": None}


async def _run_item_task(task_id: str, engagement_id: str, item_type: str, item_id: str) -> None:
    with agent_context(engagement_id=engagement_id, agent=item_type, task_id=task_id):
        await _run_item_task_inner(task_id, engagement_id, item_type, item_id)


async def _run_item_task_inner(task_id: str, engagement_id: str, item_type: str, item_id: str) -> None:
    preflight = await _item_preflight(engagement_id, item_type, item_id)
    if not preflight["ok"]:
        if preflight["downgrade"]:
            await copilot_service.set_task_status(task_id, "ready_for_review")
            await copilot_service.set_task_flagged(task_id, True)
        else:
            await copilot_service.set_task_status(task_id, "dismissed", error=preflight["reason"])
        return

    sem = _semaphore_for(engagement_id)
    async with sem:
        await copilot_service.set_task_status(task_id, "running")
        try:
            action = ITEM_RUN_ACTIONS[item_type]
            bt = BackgroundTasks()
            async with AsyncSessionLocal() as db:
                await action(engagement_id, item_id, bt, db)
            for t in bt.tasks:
                await t.func(*t.args, **t.kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "copilot item auto-run failed for %s '%s' (engagement %s)", item_type, item_id, engagement_id,
            )
            await copilot_service.set_task_status(task_id, "failed", error=f"{type(exc).__name__}: {exc}")
            return
        await copilot_service.set_task_status(task_id, "ready_for_review")
