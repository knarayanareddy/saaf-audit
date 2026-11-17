"""What the web search did, as the tool says it, not as the model says it.

    venv/Scripts/python.exe -m tests.test_search_report

A Topic Intelligence lens wrote "live web search was unavailable this session",
and another quoted the tool's own limit error. There was no way to tell, after
the fact, whether search had failed, had been switched off, or had simply been
used up: the code kept the model's text and discarded every result block.

Measured, and not as simple as it first looked: the lenses used their whole
allowance of five every time, and given eight, one used eight. The model spends
what it is offered, so a fully used budget proves nothing about it being too
small. What would is a *refused* search — which is exactly what was never kept.

So the searching is now counted and its errors kept. This checks the reading of
the reply — the part that has to be right for the screen to tell the truth —
against replies shaped like the real ones. No API calls.
"""
import sys
from types import SimpleNamespace

from services.ai_service import search_report

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _hits():
    return SimpleNamespace(type="web_search_tool_result", content=[SimpleNamespace(url="https://x", title="X")])


def _refused(code):
    return SimpleNamespace(type="web_search_tool_result", content=SimpleNamespace(error_code=code))


def _message(blocks, searches, as_dict=True):
    usage = {"web_search_requests": searches, "web_fetch_requests": 0} if as_dict \
        else SimpleNamespace(web_search_requests=searches)
    return SimpleNamespace(content=blocks, usage=SimpleNamespace(server_tool_use=usage))


def test_a_clean_run_reports_its_count():
    report = search_report(_message([_hits()] * 4, 4), allowed=8)
    check(report["searches_used"] == 4, "it counts the searches that ran")
    check(report["searches_allowed"] == 8, "and says how many it was allowed")
    check(report["search_errors"] == [], "and no errors when there were none")
    check(report["web_search"] is True, "and that live search was on")


def test_the_tools_own_errors_are_kept():
    report = search_report(
        _message([_hits(), _hits(), _refused("max_uses_exceeded"), _refused("max_uses_exceeded")], 2),
        allowed=2,
    )
    check(report["search_errors"] == ["max_uses_exceeded", "max_uses_exceeded"],
          "a refused search keeps the code the tool gave, not the model's paraphrase of it")
    check(report["searches_used"] == 2, "and the count still says how far it got")


def test_a_code_execution_error_is_not_lost():
    # This search version also runs code; a failure there ends the searching
    # just as surely and must not read as a clean run.
    block = SimpleNamespace(type="code_execution_tool_result",
                            content=SimpleNamespace(error_code="unavailable"))
    report = search_report(_message([_hits(), block], 1), allowed=8)
    check(report["search_errors"] == ["unavailable"], "errors from the code-execution half are kept too")


def test_both_shapes_of_usage_are_read():
    # The API returned the usage as a plain dict in the measurement; the typed
    # SDK object is the other shape. Either must give the same answer.
    as_dict = search_report(_message([], 5, as_dict=True), allowed=8)["searches_used"]
    as_object = search_report(_message([], 5, as_dict=False), allowed=8)["searches_used"]
    check(as_dict == 5 and as_object == 5, "the count is the same whichever shape the usage arrives in")


def test_a_reply_without_usage_does_not_crash_or_invent_a_count():
    bare = SimpleNamespace(content=[], usage=None)
    report = search_report(bare, allowed=8)
    check(report["searches_used"] == 0 and report["search_errors"] == [],
          "no usage means zero searches reported, not an exception and not a guess")


def test_other_blocks_are_ignored():
    text = SimpleNamespace(type="text", content="a paragraph")
    report = search_report(_message([text, _hits()], 1), allowed=8)
    check(report["search_errors"] == [], "ordinary text blocks are never mistaken for errors")


def test_a_paused_turn_is_counted_in_full():
    """A long search turn can pause and be resumed. Each part is a billed request
    with its own searches; counting only the last part hid both. Found when a
    smoke-test lens call took 848 seconds and the ledger could not say whether it
    had been one request or several."""
    import asyncio
    import json
    from services import agent_contract, ai_service
    from services.agent_contract import run_agent
    from services.agent_ledger import agent_context
    from services.agent_schemas import LensSynthesis

    def reply(stop, searches, text=None):
        content = [_hits()] * searches + ([SimpleNamespace(type="text", text=text)] if text else [])
        return SimpleNamespace(content=content, stop_reason=stop, model="claude-sonnet-5",
                               usage=SimpleNamespace(input_tokens=900, output_tokens=300,
                                                     cache_read_input_tokens=0,
                                                     cache_creation_input_tokens=0,
                                                     server_tool_use={"web_search_requests": searches}))

    answer = json.dumps({"summary": "A lead sentence." + "\n- a bullet long enough to read like a finding of the research." * 4,
                         "sources": [{"title": "DORA", "url": None, "date": None,
                                      "confidence": None, "type": "search_result"}]})
    replies = [reply("pause_turn", 3), reply("end_turn", 5, answer)]
    rows, sent = [], []

    async def create(**kwargs):
        sent.append(kwargs)
        return replies.pop(0)

    async def record(meta, ok=True, error=None, **_):
        rows.append(meta)

    original_create, original_record = ai_service.client.messages.create, agent_contract.record_call
    ai_service.client.messages.create, agent_contract.record_call = create, record
    report = {}
    try:
        with agent_context(record=False):
            asyncio.run(run_agent("sys", "research it", LensSynthesis, server_tools=[
                {"type": "web_search_20260209", "name": "web_search", "max_uses": 8}], report=report))
    finally:
        ai_service.client.messages.create, agent_contract.record_call = original_create, original_record

    check(len(sent) == 2, f"the paused turn is resumed ({len(sent)} requests)")
    check(sent[1]["messages"][-1]["role"] == "assistant",
          "by sending the paused reply back unchanged — append-only")
    check(len(rows) == 2, f"each part is its own ledger row ({len(rows)} rows)")
    check(report.get("searches_used") == 8 and report.get("parts") == 2,
          f"and the searches of both parts are counted ({report.get('searches_used')} over {report.get('parts')})")
    check(report.get("results") == [{"title": "X", "url": "https://x"}],
          f"a page returned in both parts is kept once ({report.get('results')})")


def main():
    test_a_paused_turn_is_counted_in_full()
    test_a_clean_run_reports_its_count()
    test_the_tools_own_errors_are_kept()
    test_a_code_execution_error_is_not_lost()
    test_both_shapes_of_usage_are_read()
    test_a_reply_without_usage_does_not_crash_or_invent_a_count()
    test_other_blocks_are_ignored()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
