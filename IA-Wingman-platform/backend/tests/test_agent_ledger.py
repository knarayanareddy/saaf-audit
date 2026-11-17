"""Tests for the spend ledger (services/agent_ledger.py, models/agent_call.py).

    venv/Scripts/python.exe -m tests.test_agent_ledger

Writes to the database and cleans up after itself — the rows it creates carry a
recognisable engagement id and are deleted at the end, so a failed run leaves at
most a handful of orphans in one engagement that does not exist.

No API calls: the client is scripted, as in the other agent tests.
"""
import json
import asyncio
import sys
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import delete, select

from database import AsyncSessionLocal
from models.agent_call import AgentCall
from services import agent_ledger, ai_service
from services.agent_contract import AgentMeta, repair_phrase, run_agent
from services.agent_ledger import (
    agent_context, attributed, caller_of, current_context, record_call,
    recent_calls, repair_report, spend_for,
)
from services.agent_schemas import RatingChallenge
from services.model_tiers import AUTO_SPEND_BUDGET_USD, DRAFT, JUDGE, QUICK

failures: list[str] = []
ENG = "test-ledger-engagement"
ORPHAN = "test-ledger-orphan"
#: Callers this suite invents, so `repair_report` — which reads every row in the
#: ledger — can be checked without the real ones being mistaken for them.
_TAG = "zz-test-ledger."
#: What `caller_of` will write for this suite's own undeclared call. Derived
#: rather than typed, because run as `-m tests.test_agent_ledger` this module is
#: `__main__` and the recorded name follows.
_MINE = f"{__name__.rsplit('.', 1)[-1]}.write"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


async def _ensure_table():
    """Base.metadata only knows the models that have been imported, so a test
    run in isolation has to say so before it can create anything.

    The migrations run too: `create_all` leaves an existing table alone, so a
    column added to the model after this database was created — `repair` and
    `caller` were — exists in Python and not in SQLite until they do.
    """
    import models  # noqa: F401  — registers every table on Base.metadata
    from database import create_tables, run_migrations
    await create_tables()
    await run_migrations()


async def _clean():
    async with AsyncSessionLocal() as db:
        # Both the attributed rows and the one this suite deliberately files with
        # no engagement — a test that checks the orphan case still has to clear
        # the orphan afterwards.
        await db.execute(delete(AgentCall).where(AgentCall.engagement_id == ENG))
        await db.execute(delete(AgentCall).where(AgentCall.agent == ORPHAN))
        await db.execute(delete(AgentCall).where(AgentCall.caller.like(_TAG + "%")))
        await db.commit()


async def _clean_callers():
    """The rows written with no engagement at all, which `_clean` cannot find."""
    async with AsyncSessionLocal() as db:
        await db.execute(delete(AgentCall).where(AgentCall.caller == _MINE))
        await db.commit()


def _meta(model, tier, inp=10_000, out=1_000, cached=0, thinking=0, repaired=False):
    return AgentMeta(model=model, tier=tier, input_tokens=inp, output_tokens=out,
                     cached_tokens=cached, thinking_tokens=thinking, duration_ms=1234,
                     stop_reason="tool_use", repaired=repaired, schema="Test")


def test_a_call_is_attributed_to_whoever_owns_it():
    print("context:")
    check(current_context() == {}, "outside a context there is no owner")

    with agent_context(engagement_id=ENG, agent="governance_assessor"):
        inner = current_context()
        check(inner["engagement_id"] == ENG and inner["agent"] == "governance_assessor",
              "inside one, the call knows whose it is")
        with agent_context(agent="quality_review", run_id="r1"):
            nested = current_context()
            check(nested["engagement_id"] == ENG,
                  "a nested context keeps the engagement its caller established")
            check(nested["agent"] == "quality_review" and nested["run_id"] == "r1",
                  "and overrides only what it names")
        check(current_context()["agent"] == "governance_assessor",
              "leaving the inner context restores the outer one")
    check(current_context() == {}, "and leaving the outer one clears it")


def test_every_call_leaves_a_row_including_the_failures():
    print("writing:")
    asyncio.run(_clean())

    async def write():
        with agent_context(engagement_id=ENG, agent="peer_review", run_id="run-1"):
            await record_call(_meta(JUDGE.model, "judge", thinking=1_500),
                              sources={"passages": ["P1", "P3"], "coverage": "read 2 passages"})
            await record_call(_meta(DRAFT.model, "draft"))
            await record_call(_meta(DRAFT.model, "draft"), ok=False, error="cut off at 4,096 tokens")
        # Outside any engagement: still money, still recorded.
        with agent_context(agent=ORPHAN):
            await record_call(_meta(QUICK.model, "quick", inp=800, out=50))

    asyncio.run(write())

    rows = asyncio.run(recent_calls(ENG, 20))
    check(len(rows) == 3, f"three calls are attributed to this engagement ({len(rows)})")
    async def orphans():
        async with AsyncSessionLocal() as db:
            return (await db.execute(select(AgentCall).where(AgentCall.agent == ORPHAN))).scalars().all()
    check(len(asyncio.run(orphans())) == 1,
          "a call made outside any engagement is still recorded — it still cost money")
    check(any(not r["ok"] for r in rows),
          "the failed call is in the ledger too — it cost what it cost")
    failed = next(r for r in rows if not r["ok"])
    check("cut off" in (failed["error"] or ""), "and carries why it failed")

    judged = next(r for r in rows if r["tier"] == "judge")
    check(judged["thinking_tokens"] == 1_500, "reasoning is recorded")
    check(judged["sources"] == {"passages": ["P1", "P3"], "coverage": "read 2 passages"},
          "and so is what the call read")
    check(all(r["agent"] == "peer_review" for r in rows), "each row names its agent")


def test_the_total_says_what_it_does_not_cover():
    print("reading:")
    asyncio.run(_clean())

    async def write():
        with agent_context(engagement_id=ENG, agent="x"):
            await record_call(_meta(JUDGE.model, "judge"))
            await record_call(_meta(DRAFT.model, "draft"))
            # A model nobody priced: cost_usd is None, not zero.
            await record_call(_meta("some-unpriced-model", "draft"))

    asyncio.run(write())
    spend = asyncio.run(spend_for(ENG))

    check(spend["calls"] == 3, "every call is counted")
    check(spend["unpriced_calls"] == 1,
          "the unpriced one is reported separately rather than counted as free")
    check(spend["total_usd"] > 0, f"the total is money: ${spend['total_usd']}")
    check(set(spend["by_tier"]) == {"judge", "draft"}, f"broken down by tier: {spend['by_tier']}")
    check(spend["by_tier"]["judge"] > spend["by_tier"]["draft"],
          "and the judge tier costs more than the draft tier, as it should")

    asyncio.run(_clean())
    empty = asyncio.run(spend_for(ENG))
    check(empty["calls"] == 0 and empty["total_usd"] == 0,
          "an engagement that has spent nothing reads as nothing")


def test_a_real_run_records_itself():
    print("end to end:")
    asyncio.run(_clean())

    good = {"agrees": True, "suggested_rating": "high", "rationale": "The control is absent."}
    bad = dict(good, suggested_rating="severe")

    def _msg(tool_input):
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=json.dumps(tool_input))],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=5_000, output_tokens=400, cache_read_input_tokens=0),
        )

    replies = [_msg(bad), _msg(good)]

    async def fake(**kwargs):
        return replies.pop(0)

    async def run():
        original = ai_service._call_with_retry
        ai_service._call_with_retry = fake
        try:
            with agent_context(engagement_id=ENG, agent="finding_drafter"):
                return await run_agent("sys", "challenge it", RatingChallenge)
        finally:
            ai_service._call_with_retry = original

    result = asyncio.run(run())
    check(result.data.agrees is True, "the run produced its answer")

    rows = asyncio.run(recent_calls(ENG, 10))
    check(len(rows) == 2,
          f"a run that needed a correction left TWO rows — it made two calls ({len(rows)})")
    check(any(r["repaired"] for r in rows), "and the second one is marked as the correction")
    spend = asyncio.run(spend_for(ENG))
    check(spend["calls"] == 2 and spend["total_usd"] > 0,
          f"both are in the bill: {spend['calls']} calls, ${spend['total_usd']}")
    asyncio.run(_clean())


# ── What the untyped path admits to ──────────────────────────────────────────
# The ledger read 31 calls, 1 repaired, 0 with a reason for failing. That was not
# the truth about the platform but the shape of what the ledger could see: the
# repair routine lives on the untyped path and only the typed path set `repaired`,
# the row was written before the parse so a call that produced no JSON was filed
# as a success, and `agent` is set only by the three callers that open a context.
def _text_msg(text, stop_reason="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=900, output_tokens=120, cache_read_input_tokens=0),
    )


class _Captured:
    """Stands in for record_call and keeps what would have been written."""

    def __init__(self):
        self.rows = []

    async def __call__(self, meta, ok=True, error=None, sources=None):
        self.rows.append({"repair": getattr(meta, "repair", ""),
                          "repaired": getattr(meta, "repaired", False),
                          "ok": ok, "error": error})

    @property
    def only(self):
        assert len(self.rows) == 1, f"expected one ledger row, got {len(self.rows)}"
        return self.rows[0]


def _untyped(reply, **kw):
    """One scripted untyped call: returns (value or exception, captured rows)."""
    captured = _Captured()
    client, record = ai_service._call_with_retry, ai_service.record_call

    async def fake(**_):
        return reply

    ai_service._call_with_retry = fake
    ai_service.record_call = captured
    try:
        out = asyncio.run(ai_service.run_agent_to_json("sys", "do it", **kw))
    except Exception as exc:  # noqa: BLE001 — the failure is the subject here
        out = exc
    finally:
        ai_service._call_with_retry = client
        ai_service.record_call = record
    return out, captured


def test_the_repair_has_a_name():
    print("the repair routine:")
    for raw, expected, label in (
        ('{"a": 1}', "", "clean JSON needed nothing"),
        ('```json\n{"a": 1}\n```', "fence", "a code fence is named"),
        ('Here you go:\n{"a": 1}\nHope that helps.', "sliced",
         "braces cut out of a paragraph are named"),
        ('{"a": 1,}', "commas", "a trailing comma is named"),
    ):
        value, repair = ai_service._extract_json(raw)
        check(value == {"a": 1} and repair == expected, f"{label} ({repair!r})")

    check(repair_phrase("sliced") != repair_phrase("schema-retry"),
          "a regex cutting prose into shape and a model correcting itself read differently")
    check(repair_phrase("") == "", "and a clean reply gets no phrase at all")


def test_a_reply_that_could_not_be_read_is_a_failed_call():
    print("failures:")
    out, captured = _untyped(_text_msg("I am afraid I cannot help with that."))
    check(isinstance(out, ValueError), "the caller still gets the exception")
    check(captured.only["ok"] is False,
          "and the row says the call failed — it was filed as a success before")
    check("No JSON found" in (captured.only["error"] or ""), "with the reason on the row")

    out, captured = _untyped(_text_msg('[{"id": "wp_1"', stop_reason="max_tokens"),
                             max_tokens=12_000)
    from services.agent_contract import AgentTruncated
    check(isinstance(out, AgentTruncated), "truncation is still raised")
    check("12,000 tokens" in (captured.only["error"] or ""),
          "and now says at what ceiling — `error` was null on all five truncated calls")


def test_a_carried_reply_says_it_was_carried():
    print("repairs:")
    out, captured = _untyped(_text_msg('Certainly:\n{"id": "wp_1"}'))
    check(out == {"id": "wp_1"}, "the value still comes back")
    check(captured.only["repaired"] and captured.only["repair"] == "sliced",
          f"and the row names the surgery ({captured.only['repair']!r})")

    out, captured = _untyped(_text_msg('[{"id": "wp_1"}]'))
    check(out == [{"id": "wp_1"}] and not captured.only["repaired"],
          "a reply that parsed as it stood is recorded as clean")

    # What giving the extractor a voice turned up. Slicing tried {} before [],
    # so a single-row array with a sentence in front of it came back as the bare
    # object inside it — and every caller guards with `isinstance(rows, list)`,
    # which turned one row into none while the ledger recorded a clean success.
    out, captured = _untyped(_text_msg('Certainly:\n[{"id": "wp_1"}]'))
    check(out == [{"id": "wp_1"}] and captured.only["repair"] == "sliced",
          "a one-row array wrapped in prose keeps its shape, and says it was sliced")
    out, _ = _untyped(_text_msg('[{"id": "wp_1"},]'))
    check(out == [{"id": "wp_1"}],
          "and so does one with a trailing comma — it used to arrive as a bare object")


def test_the_call_site_is_recorded_even_when_nobody_declared_an_agent():
    print("attribution:")
    here = caller_of()
    check(here.endswith(".test_the_call_site_is_recorded_even_when_nobody_declared_an_agent"),
          "the calling function names itself")
    check(here.split(".")[0] == __name__.rsplit(".", 1)[-1], f"with its module ({here.split('.')[0]})")

    def through_a_helper():
        return caller_of()

    check(through_a_helper().endswith(".through_a_helper"),
          "and it is the frame that called, not the one that was called")
    check(agent_ledger._PLUMBING == ("services.ai_service", "services.agent_contract",
                                     "services.agent_ledger"),
          "the three plumbing modules are skipped — every call passes through those")

    async def write():
        # No agent_context at all: the case 19 of the first 20 untyped calls were in.
        await record_call(_meta(DRAFT.model, "draft"))
        async with AsyncSessionLocal() as db:
            return (await db.execute(
                select(AgentCall).where(AgentCall.caller == _MINE)
            )).scalars().all()

    rows = asyncio.run(write())
    check(len(rows) == 1, f"the undeclared call left a row ({len(rows)})")
    check(rows and rows[0].agent is None,
          "with no agent — an owner nobody declared is not invented")
    check(rows and rows[0].caller == _MINE,
          f"but the ledger knows where it came from ({rows[0].caller if rows else '—'})")
    asyncio.run(_clean_callers())


def test_the_report_ranks_the_call_sites_by_what_they_lose():
    print("the list to migrate, in order:")

    async def run():
        async with AsyncSessionLocal() as db:
            for caller, schema, repair, ok in (
                (_TAG + "quiet.draft", None, None, True),
                (_TAG + "quiet.draft", None, None, True),
                (_TAG + "carried.generate", None, "sliced", True),
                (_TAG + "carried.generate", None, "commas", True),
                (_TAG + "carried.generate", None, None, False),
                (_TAG + "typed.run", "WorkProgram", "schema-retry", True),
            ):
                db.add(AgentCall(id=str(uuid4()), engagement_id=ENG, caller=caller,
                                 schema=schema, repair=repair, repaired=bool(repair),
                                 ok=ok, model=DRAFT.model, tier="draft"))
            await db.commit()
        return await repair_report()

    report = asyncio.run(run())
    mine = [r for r in report if r["caller"].startswith(_TAG)]
    check(len(mine) == 3, f"one row per call site ({len(mine)})")
    check(mine[0]["caller"].endswith("carried.generate"),
          f"the site being carried comes first ({mine[0]['caller']})")
    check(mine[0]["repairs"] == {"sliced": 1, "commas": 1},
          f"with the repairs it needed, by name ({mine[0]['repairs']})")
    check(mine[0]["failed"] == 1 and mine[0]["untyped"] == 3,
          "its lost run and its untyped calls counted")

    typed = next(r for r in mine if r["caller"].endswith("typed.run"))
    check(typed["typed"] == 1 and typed["untyped"] == 0,
          "a call already on a schema is marked as such, not as a candidate")
    quiet = next(r for r in mine if r["caller"].endswith("quiet.draft"))
    check(quiet["repaired"] == 0 and mine.index(quiet) == len(mine) - 1,
          "and a site that never needed help sinks to the bottom of the list")
    asyncio.run(_clean())


def test_a_launched_agent_carries_its_owner():
    print("launching:")
    seen = []

    async def work(marker):
        seen.append((marker, dict(current_context())))

    async def both():
        # Two tasks from one request. A ContextVar set at the top of a task body,
        # with no block to leave, would let the second inherit the first's owner.
        await asyncio.gather(
            attributed(work, "eng-a", "bra", "run-a")("a"),
            attributed(work, "eng-b", "kickoff")("b"),
        )
        await work("after")

    asyncio.run(both())
    by_marker = dict(seen)
    check(by_marker["a"] == {"engagement_id": "eng-a", "agent": "bra", "run_id": "run-a"},
          "the launched task knows its engagement, agent and run")
    check(by_marker["b"]["agent"] == "kickoff" and by_marker["b"]["engagement_id"] == "eng-b",
          "and the one beside it knows its own")
    check(by_marker["after"] == {}, "nothing leaks out to what runs afterwards")


def test_every_launched_agent_declares_one():
    print("every launch site, read out of the source:")
    from services.agent_registry import resolve

    routers = (__import__("pathlib").Path(__file__).resolve().parents[1] / "routers")
    # The board narrative is portfolio-wide: it belongs to no engagement, so
    # there is nothing to declare and inventing one would be worse than the gap.
    allowed_without = {"draft_board_narrative_task"}

    undeclared, unknown = [], []
    for path in sorted(routers.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        for chunk in src.split("add_task(")[1:]:
            first = chunk.strip().split("\n")[0].strip().rstrip(",)")
            if first.startswith("attributed("):
                name = first.split('"')[1] if '"' in first else ""
                if name and resolve(name) is None:
                    unknown.append(f"{path.name}: {name}")
            elif not first.startswith("attributed"):
                target = first.split(",")[0].strip()
                if target and target not in allowed_without:
                    undeclared.append(f"{path.name}: {target}")

    check(not undeclared, f"no launch site left without an owner ({undeclared})")
    check(not unknown, f"and every declared agent exists in the registry ({unknown})")

    # The same for the calls a request makes itself rather than handing over.
    inline = []
    for path in sorted(routers.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        for chunk in src.split("run_agent_to_json(")[1:]:
            before = src[:src.index(chunk)]
            if "agent_context(" not in before[-400:]:
                inline.append(path.name)
    check(not inline, f"and an in-request agent call declares one too ({sorted(set(inline))})")


def test_the_budget_is_expressed_in_money():
    print("the budget:")
    check(AUTO_SPEND_BUDGET_USD > 0, f"there is one: ${AUTO_SPEND_BUDGET_USD:.2f}")
    src = (__import__("pathlib").Path(__file__).resolve().parents[1]
           / "services" / "copilot_orchestrator.py").read_text(encoding="utf-8")
    check("_spend_room(engagement_id, \"stages\")" in src, "stage auto-fire checks it")
    check("_spend_room(engagement_id, \"items\")" in src, "item auto-fire checks it")
    check("_MAX_AUTO_TASKS_PER_ENGAGEMENT" in src,
          "the task-count caps are kept as well — a cheap runaway loop is still a runaway loop")


def main():
    asyncio.run(_ensure_table())
    try:
        test_a_call_is_attributed_to_whoever_owns_it()
        test_every_call_leaves_a_row_including_the_failures()
        test_the_total_says_what_it_does_not_cover()
        test_a_real_run_records_itself()
        test_the_repair_has_a_name()
        test_a_reply_that_could_not_be_read_is_a_failed_call()
        test_a_carried_reply_says_it_was_carried()
        test_the_call_site_is_recorded_even_when_nobody_declared_an_agent()
        test_the_report_ranks_the_call_sites_by_what_they_lose()
        test_a_launched_agent_carries_its_owner()
        test_every_launched_agent_declares_one()
        test_the_budget_is_expressed_in_money()
    finally:
        asyncio.run(_clean())
        asyncio.run(_clean_callers())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
