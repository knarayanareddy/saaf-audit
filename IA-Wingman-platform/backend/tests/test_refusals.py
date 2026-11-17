"""A declined request has to look like a declined request.

    venv/Scripts/python.exe -m tests.test_refusals

The current models decline some requests on safety grounds, and they do it with
an ordinary 200: `stop_reason: "refusal"`, a category such as `cyber`, and no
answer. This platform audits IT security and cyber controls, so that is an
expected event here. Before this, it fell through to the JSON parser and came
out as "No JSON found" — a broken-looking agent, an invitation to retry, and a
ledger row that blamed the parser.

Only the lowest layer is scripted — `client.messages.create` — so the real
`_call_with_retry` runs. The other suites replace `_call_with_retry` itself, and
a check living inside it would be invisible to them, which is exactly how the
judge-tier 400s went unnoticed. No API calls.
"""
import asyncio
import sys
from types import SimpleNamespace

from services import ai_service
from services.agent_contract import AgentRefused, failure_message, refusal_of, run_agent
from services.agent_schemas import FindingDraft

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _refusal(category="cyber", as_dict=True, explanation="Request touches exploit development."):
    details = {"type": "refusal", "category": category, "explanation": explanation}
    message = SimpleNamespace(
        content=[], stop_reason="refusal",
        usage=SimpleNamespace(input_tokens=1200, output_tokens=8, cache_read_input_tokens=0),
    )
    if as_dict:
        message.model_extra = {"stop_details": details}
    else:
        message.stop_details = SimpleNamespace(**details)
    return message


class Harness:
    """Scripts the API and captures what the ledger would have been told."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = 0
        self.rows = []

    async def create(self, **kwargs):
        self.calls += 1
        return self.replies.pop(0)

    async def record(self, meta, ok=True, error=None, **_):
        self.rows.append({"ok": ok, "error": error, "stop_reason": meta.stop_reason})

    def run(self, coro_fn):
        original_create = ai_service.client.messages.create
        original_record = ai_service.record_call
        ai_service.client.messages.create = self.create
        ai_service.record_call = self.record
        try:
            return asyncio.run(coro_fn())
        finally:
            ai_service.client.messages.create = original_create
            ai_service.record_call = original_record


def _raises(harness, coro_fn):
    try:
        harness.run(coro_fn)
    except Exception as exc:  # noqa: BLE001
        return exc
    return None


def test_reading_a_refusal():
    print("reading:")
    check(refusal_of(_refusal()) == ("cyber", "Request touches exploit development."),
          "the category and explanation are read from an untyped extra (old SDK)")
    check(refusal_of(_refusal(as_dict=False))[0] == "cyber",
          "and from a typed attribute (newer SDK) — same answer either way")
    ok = SimpleNamespace(content=[], stop_reason="end_turn", usage=None)
    check(refusal_of(ok) is None, "an ordinary reply is not a refusal")
    bare = SimpleNamespace(content=[], stop_reason="refusal", usage=None)
    check(refusal_of(bare) == (None, None),
          "a refusal without details is still a refusal, with the category unknown")


def test_the_untyped_path_reports_a_refusal():
    print("untyped path:")
    h = Harness(_refusal())
    exc = _raises(h, lambda: ai_service.run_agent_to_json("sys", "assess the firewall rules"))
    check(isinstance(exc, AgentRefused), f"it raises AgentRefused ({type(exc).__name__})")
    check(exc is not None and "No JSON found" not in str(exc),
          "and not the parser's 'No JSON found', which blamed the wrong thing")
    check(getattr(exc, "category", None) == "cyber", "naming the category")
    check(h.calls == 1, f"a refusal is not retried — it would be declined again ({h.calls} call)")
    check(len(h.rows) == 1 and h.rows[0]["error"] == "refused: cyber" and h.rows[0]["ok"] is False,
          f"one ledger row says what happened: {h.rows}")


def test_the_typed_path_reports_a_refusal():
    print("typed path:")
    h = Harness(_refusal(category="bio"))
    exc = _raises(h, lambda: run_agent("sys", "draft a finding", FindingDraft))
    check(isinstance(exc, AgentRefused) and exc.category == "bio",
          f"the typed path raises it too, with its category ({type(exc).__name__})")
    check(h.calls == 1, "and does not spend its correction round on it")


def test_what_the_auditor_is_shown():
    print("message:")
    refused = AgentRefused("cyber", "Request touches exploit development.")
    check("cyber" in failure_message(refused), "a refusal is stored in words, with its category")
    check(failure_message(ValueError("internal detail")) == "Agent run failed. Check server logs.",
          "any other failure stays generic — internal text is for the log, not the screen")


def test_a_stuck_lens_is_stopped_in_words():
    """A lens call once took 848 seconds; the SDK's own timeout and retries
    allow half an hour. The scan now stops waiting, and says so."""
    print("a stuck lens:")
    from services import lens_call
    from services.agent_contract import AgentTimedOut
    from services.agent_schemas import LensSynthesis

    async def stuck(*args, **kwargs):
        await asyncio.sleep(5)

    original_run, original_limit = lens_call.run_agent, lens_call.LENS_TIMEOUT_S
    lens_call.run_agent, lens_call.LENS_TIMEOUT_S = stuck, 0.05
    try:
        exc = None
        try:
            asyncio.run(lens_call.synthesise("sys", "prompt", LensSynthesis, use_web_search=True))
        except Exception as e:  # noqa: BLE001
            exc = e
    finally:
        lens_call.run_agent, lens_call.LENS_TIMEOUT_S = original_run, original_limit
    check(isinstance(exc, AgentTimedOut), f"the lens is stopped, not waited on ({type(exc).__name__})")
    check(exc is not None and "stopped after" in failure_message(exc),
          "and the lens card says it was stopped, not 'Agent run failed'")


def test_hidden_reasoning_is_not_reported_as_none():
    """The current models withhold their reasoning by default: thinking blocks
    arrive empty. The count was 0 and the screens then said nothing at all."""
    print("hidden reasoning:")
    import json as _json
    from services import ai_service as _ai
    from services.agent_contract import run_agent as _run_agent
    from services.agent_ledger import agent_context
    from services.agent_schemas import RatingChallenge

    reply = SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""),
                 SimpleNamespace(type="text", text=_json.dumps(
                     {"agrees": False, "suggested_rating": "low", "rationale": "Small amounts, two of 25."}))],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=10, output_tokens=900, cache_read_input_tokens=0,
                              cache_creation_input_tokens=0))

    async def script(**kwargs):
        return reply

    original = _ai._call_with_retry
    _ai._call_with_retry = script
    try:
        with agent_context(record=False):
            result = asyncio.run(_run_agent("sys", "x", RatingChallenge))
    finally:
        _ai._call_with_retry = original
    m = result.meta
    check(m.reasoned and m.thinking_tokens == 0,
          "the model reasoned, and the visible count is 0 — both are recorded")
    check("reasoning not shown" in m.sentence(),
          f"and the receipt says so instead of staying silent ({m.sentence()})")


def main():
    test_a_stuck_lens_is_stopped_in_words()
    test_hidden_reasoning_is_not_reported_as_none()
    test_reading_a_refusal()
    test_the_untyped_path_reports_a_refusal()
    test_the_typed_path_reports_a_refusal()
    test_what_the_auditor_is_shown()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
