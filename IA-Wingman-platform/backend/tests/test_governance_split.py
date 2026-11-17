"""The governance assessment, one framework at a time.

    venv/Scripts/python.exe -m tests.test_governance_split

Ten frameworks in one call produced ~6,500 tokens of structured answer, and that
is where it came apart: truncated outright at the old ceiling, and with room to
finish it still needed a correction round most runs — once the model drifted out
of JSON into `<parameter name=...>` markup and the run failed. Split up, each call
answers about one framework and has nothing to drift out of.

What the split then costs is honesty about the parts: no single call sees the
whole assessment any more, so the summary is composed here, and a framework whose
call failed has to be named rather than quietly missing from the list.

No API calls: the client is scripted.
"""
import json
import asyncio
import sys
from types import SimpleNamespace

from services import ai_service
from services.agent_contract import AgentMeta
from services.agent_ledger import agent_context
from services.governance_assessor import _assess_one, _cost_line, _summarise

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _msg(tool_input):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps(tool_input))],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=5_400, output_tokens=1_600, cache_read_input_tokens=0),
    )


def with_replies(replies, fn):
    """Run `fn` against a scripted client, out of the spend ledger."""
    queue = list(replies)

    async def client(**kwargs):
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    original = ai_service._call_with_retry
    ai_service._call_with_retry = client
    try:
        with agent_context(record=False):
            return fn()
    finally:
        ai_service._call_with_retry = original


ITEM = {"requirement": "Board-approved ESG risk appetite", "coverage": "gap",
        "evidence": "Not visible in the passages given [P2]", "confidence": "medium",
        "proposed_risk": {"title": "No ESG risk appetite", "inherent_rating": "high"}}


def test_each_item_carries_the_framework_it_was_asked_about():
    print("one framework per call:")
    # The model is given one framework and nothing else, so it has no reason to
    # name it — and every reason not to be believed if it does. Here it names the
    # wrong one on purpose.
    answer = dict(ITEM, framework_ref="SOMETHING_ELSE", framework_name="Invented")
    fw = {"ref": "EBA_GL_ESG_2025_01", "name": "EBA Guidelines on ESG risk management",
          "category": "guidance", "provision": "Art. 4", "rationale": "ESG in scope"}

    items, meta, error = with_replies([_msg({"items": [answer]})], lambda: asyncio.run(
        _assess_one(fw, "docs", [])))

    check(not error and len(items) == 1, f"the call produced its item ({error or 'no error'})")
    check(items[0]["framework_ref"] == "EBA_GL_ESG_2025_01",
          f"stamped from the row that was sent, not from the answer ({items[0]['framework_ref']})")
    check(items[0]["framework_name"] == "EBA Guidelines on ESG risk management",
          "and so is the name")
    check(meta is not None and meta.output_tokens == 1_600, "the call's cost comes back with it")


def test_a_framework_that_failed_is_named_not_dropped():
    print("a framework whose call fails:")
    boom = RuntimeError("upstream said no")
    items, meta, error = with_replies([boom, boom], lambda: asyncio.run(
        _assess_one({"ref": "NBB_CIRC", "name": "NBB circulaire", "category": "guidance"},
                    "docs", [])))

    check(items == [] and meta is None, "nothing is invented for it")
    check("NBB_CIRC" in error, f"and it is named in the error ({error})")

    line = _summarise([ITEM], fw_count=3, failed=["NBB_CIRC: RuntimeError"])
    # Two of three: the count is frameworks *attempted minus failed*, not the
    # number of items, so one framework that produced nothing does not read as
    # one framework with nothing to report.
    check("2 of 3 frameworks" in line, f"the summary counts what was assessed ({line})")
    check("could not be assessed" in line and "NBB_CIRC" in line,
          "and says which framework is missing from it — silence would read as 'nothing to report'")


def test_the_summary_is_counted_not_written():
    print("the summary:")
    items = [dict(ITEM, coverage=c) for c in ("covered", "partial", "gap", "gap")]
    line = _summarise(items, fw_count=2, failed=[])
    check("4 requirements assessed across 2 of 2 frameworks" in line, f"({line})")
    check("1 covered, 1 partial, 2 gap" in line,
          "the tally comes from the items, so it cannot disagree with the list under it")
    check("could not be assessed" not in line, "and nothing is said about failures when there are none")


def test_the_receipt_adds_the_calls_up():
    print("the receipt:")
    metas = [AgentMeta(model="claude-sonnet-5", tier="draft", input_tokens=5_400,
                       output_tokens=1_600, duration_ms=4_000),
             AgentMeta(model="claude-sonnet-5", tier="draft", input_tokens=5_400,
                       output_tokens=900, duration_ms=9_000)]
    line = _cost_line(metas)
    check("2 calls" in line, f"it says how many calls there were ({line})")
    check("10,800 in / 2,500 out" in line,
          "and adds them up — one call's sentence would show a fraction of the bill")
    # The first framework runs alone to write the cache; the rest run together.
    # So the wait is the first call plus the slowest of the rest — 4.0 + 9.0.
    check("13.0s" in line, f"the wait is the first call plus the slowest of the rest ({line})")
    check(_cost_line([]) == "no call completed", "and no calls is said in words, not as $0.00")

    cached = [AgentMeta(model="claude-sonnet-5-5", tier="draft", input_tokens=90,
                        output_tokens=800, cached_tokens=10_800, duration_ms=5_000)]
    check("(+10,800 from cache)" in _cost_line(cached),
          "and what came from cache is shown beside the uncached input, not hidden in it")


def main():
    test_each_item_carries_the_framework_it_was_asked_about()
    test_a_framework_that_failed_is_named_not_dropped()
    test_the_summary_is_counted_not_written()
    test_the_receipt_adds_the_calls_up()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
