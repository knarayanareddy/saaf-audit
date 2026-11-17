"""Tests for the agent output contract (services/agent_contract.py).

Run from the backend dir:
    venv/Scripts/python.exe -m tests.test_agent_contract

No API calls: the Anthropic client is replaced with scripted replies, so every
failure mode can be produced on demand — including the ones that are rare in
practice and catastrophic when they happen.
"""
import asyncio
import json
import sys
from types import SimpleNamespace

from pydantic import ValidationError

from services import ai_service
from services.agent_ledger import agent_context
from services.agent_contract import (
    AgentContractError, AgentTruncated, run_agent, schema_for,
)
from services.agent_schemas import FindingDraft, GovernanceAssessment, PeerReview

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


# ── A stand-in for the Anthropic client ──────────────────────────────────────
def _msg(tool_input=None, stop_reason="end_turn", text=None):
    """A reply as structured outputs returns it: the answer is JSON text."""
    content = []
    if tool_input is not None:
        content.append(SimpleNamespace(type="text", text=json.dumps(tool_input)))
    if text is not None:
        content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=1200, output_tokens=340, cache_read_input_tokens=900),
    )


class Script:
    """Replies in order, recording what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies.pop(0) if self.replies else _msg({})


def with_script(script, fn):
    """Run `fn` against a scripted client, and keep it out of the spend ledger:
    these calls never happened, and a record of what was spent must not contain
    them."""
    original = ai_service._call_with_retry
    ai_service._call_with_retry = script
    try:
        with agent_context(record=False):
            return fn()
    finally:
        ai_service._call_with_retry = original


GOOD_FINDING = {
    "title": "Absence of periodic re-screening",
    "condition": "Customers are not re-screened after onboarding.",
    "criteria": "AML law requires ongoing due diligence.",
    "cause": "No control was designed for it.",
    "effect": "Sanctions status changes go undetected.",
    "recommendation": "Design a risk-based periodic re-screening control.",
    "rating": "high",
    "rating_rationale": "High inherent risk with no mitigating control.",
}


def test_the_model_fills_a_form_instead_of_writing_json():
    print("the happy path — a typed answer, not a parsed one:")
    script = Script(_msg(GOOD_FINDING))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "draft it", FindingDraft, max_tokens=2000)))

    check(result.data.rating == "high", "the answer comes back as a typed object")
    check(result.data.title.startswith("Absence"), "its fields are addressable without .get()")
    sent = script.calls[0]
    fmt = ((sent.get("extra_body") or {}).get("output_config") or {}).get("format") or {}
    check(fmt.get("type") == "json_schema",
          "the answer is constrained by structured outputs, so there is no prose path to parse around")
    check(fmt["schema"]["properties"]["rating"]["enum"] == ["high", "medium", "low"],
          "the schema the model is held to is the schema that validates the answer")
    check("tool_choice" not in sent, "no forced tool — the current models reject one (400)")


def test_a_cut_off_answer_is_never_returned_as_a_whole_one():
    print("truncation — the failure that used to be invisible:")
    partial = dict(GOOD_FINDING)
    partial.pop("recommendation")
    script = Script(_msg(partial, stop_reason="max_tokens"))

    def run():
        try:
            asyncio.run(run_agent("sys", "draft it", FindingDraft, max_tokens=50))
            return None
        except AgentTruncated as exc:
            return exc

    exc = with_script(script, run)
    check(exc is not None, "hitting the token ceiling raises rather than returning what fitted")
    check("cut off" in str(exc) and "Nothing partial" in str(exc),
          f"and says so in terms an operator can act on: {exc}")
    check(len(script.calls) == 1, "it does not burn a second call trying to rescue it")


def test_a_wrong_shape_gets_one_correction_round():
    print("repair — the model is shown its own error, once:")
    broken = dict(GOOD_FINDING, rating="severe")      # not one of the three
    script = Script(_msg(broken), _msg(GOOD_FINDING))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "draft it", FindingDraft, max_tokens=2000)))

    check(result.data.rating == "high", "the second attempt succeeds")
    check(result.meta.repaired, "and the result records that it needed correcting")
    check(len(script.calls) == 2, "exactly one correction round, not a loop")

    second = script.calls[1]["messages"]
    check(all(m["role"] == "user" for m in second),
          "the correction is asked for afresh — no assistant turn is replayed")
    check("rating" in str(second[-1]["content"]) and "constraints" in str(second[-1]["content"]),
          "and it names the field that was wrong rather than repeating the schema")


def test_a_model_that_will_not_comply_fails_honestly():
    print("giving up — a failure is a failure, not an empty object:")
    broken = dict(GOOD_FINDING, rating="severe")
    script = Script(_msg(broken), _msg(broken))

    def run():
        try:
            asyncio.run(run_agent("sys", "draft it", FindingDraft, max_tokens=2000))
            return None
        except AgentContractError as exc:
            return exc

    exc = with_script(script, run)
    check(exc is not None, "two failed attempts raise instead of returning something empty")
    check("did not validate" in str(exc), "the error says what went wrong")

    # And a reply that is not JSON at all.
    prose = Script(_msg(None, stop_reason="end_turn", text="Sure! Here is the finding..."),
                   _msg(None, stop_reason="end_turn", text="Here it is again..."))

    def run_prose():
        try:
            asyncio.run(run_agent("sys", "draft it", FindingDraft))
            return None
        except AgentContractError as exc:
            return exc

    exc = with_script(prose, run_prose)
    check(exc is not None and "not JSON" in str(exc),
          "a reply that is not JSON is caught rather than parsed")


def test_every_call_records_what_it_cost():
    print("the receipt — usage stops being thrown away:")
    script = Script(_msg(GOOD_FINDING))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "draft it", FindingDraft, max_tokens=2000)))
    m = result.meta
    check(m.input_tokens == 1200 and m.output_tokens == 340, "tokens are captured")
    check(m.cached_tokens == 900, "and so is what the cache saved")
    check(m.duration_ms >= 0 and m.model, "duration and model are recorded")
    check(m.schema == "FindingDraft", "the meta says which contract was in force")
    check("in /" in m.sentence() and "s ·" in m.sentence(),
          f"and it renders as one line for a run summary: {m.sentence()}")

    d = m.as_dict()
    check(set(d) >= {"model", "input_tokens", "output_tokens", "duration_ms", "stop_reason"},
          "the dict form carries everything a stored run needs")


def test_the_schemas_the_agents_actually_use():
    print("the live schemas — what the migrated agents are held to:")
    for model in (FindingDraft, GovernanceAssessment, PeerReview):
        sch = schema_for(model)
        check("$defs" not in sch, f"{model.__name__}: nested models are inlined")
        check(bool(sch.get("required")), f"{model.__name__}: required fields are declared")

    # The cases that used to be silently patched over at the call sites.
    try:
        PeerReview.model_validate({"summary": "ok", "criteria": [{"nr": "twelve", "rating": "gc",
                                                                  "comment": "c", "evidence": "e"}]})
        ok = False
    except ValidationError:
        ok = True
    check(ok, "a non-numeric criterion number is rejected, not filtered out in silence")

    try:
        GovernanceAssessment.model_validate({"summary": "s", "items": [
            {"requirement": "r", "coverage": "gap", "evidence": "e",
             "proposed_risk": {"description": "no title"}}]})
        ok = False
    except ValidationError:
        ok = True
    check(ok, "a proposed risk with no title is rejected, not dropped at the write step")

    parsed = FindingDraft.model_validate(GOOD_FINDING)
    check(parsed.rating == "high", "a well-formed finding validates")
    try:
        FindingDraft.model_validate({k: v for k, v in GOOD_FINDING.items() if k != "cause"})
        ok = False
    except ValidationError:
        ok = True
    check(ok, "a finding missing a C is a failed run, not a finding with a blank field")


def test_the_work_program_is_no_longer_parsed_out_of_prose():
    print("the work program — the last big free-form answer:")
    from pathlib import Path as _Path

    from services.agent_schemas import WorkProgram

    sch = schema_for(WorkProgram)
    check("$defs" not in sch, "nested rows and evidence are inlined")
    check(bool(sch.get("required")), "required fields are declared")

    # The generator asks for 8-14 rows of test steps and evidence. On the
    # untyped path that answer came back as valid-looking JSON that would not
    # parse about one time in two, and a whole generation was lost with it.
    src = (_Path(__file__).resolve().parent.parent / "services" / "work_program_generator.py").read_text(encoding="utf-8")
    check("run_agent_to_json" not in src, "the generator no longer parses JSON out of prose")
    check("run_agent(" in src, "and asks for a typed answer instead")

    # The call sites migrated since, each one because the ledger measured what it
    # was losing rather than because its prompt looked risky. A module that slips
    # back onto the untyped path fails here.
    for module, schema, measured in (
        ("query_generator.py", "SearchQueries", "a markdown fence on 4 of 4 calls"),
        ("drl_generator.py", "DocumentRequestList", "a markdown fence on 3 of 3 calls"),
    ):
        src = (_Path(__file__).resolve().parent.parent / "services" / module).read_text(encoding="utf-8")
        check("run_agent_to_json" not in src and schema in src,
              f"{module} stays on the typed path — it returned {measured}")

    try:
        WorkProgram.model_validate({"rows": [{"process": "P", "risk_description": "r",
                                              "control_objective": "c", "test_steps": []}]})
        ok = False
    except ValidationError:
        ok = True
    check(ok, "a row with no test step is rejected, not written as a control nobody tests")

    try:
        WorkProgram.model_validate({"rows": [{"process": "P", "risk_description": "r",
                                              "control_objective": "c", "test_steps": ["s"],
                                              "evidence": [{"title": "t", "kind": "rumour"}]}]})
        ok = False
    except ValidationError:
        ok = True
    check(ok, "an evidence kind outside the four is rejected — the DRL depends on that split")

    good = WorkProgram.model_validate({"rows": [{"process": "Onboarding", "risk_description": "No UBO check",
                                                 "control_objective": "Verify UBO", "test_steps": ["Obtain population"],
                                                 "answers": ["Q1"]}]})
    check(good.rows[0].answers == ["Q1"] and good.rows[0].priority == "medium",
          "a well-formed row validates, and priority defaults rather than being asked for")


def test_an_answer_handed_over_as_text_is_not_paid_for_twice():
    print("the tool input that arrived as a string:")
    import json as _json
    from services.agent_contract import _unstringify
    from services.agent_schemas import Frameworks

    one = {"framework_code": "SFDR", "framework_name": "Regulation (EU) 2019/2088",
           "jurisdiction": "EU"}

    # What the model actually does: the whole object, stringified, inside the one
    # property the schema has. Measured on every run of three prompts.
    whole = {"frameworks": _json.dumps({"frameworks": [one]})}
    payload, repair = _unstringify(whole, Frameworks)
    check(payload == {"frameworks": [one]} and repair == "unstringified",
          "the copy of the whole object is unwrapped to the field's own value")

    # And the narrower version: only the field's value as text.
    payload, repair = _unstringify({"frameworks": _json.dumps([one])}, Frameworks)
    check(payload == {"frameworks": [one]} and repair == "unstringified",
          "a stringified list is parsed in place")

    payload, repair = _unstringify({"frameworks": [one]}, Frameworks)
    check(payload == {"frameworks": [one]} and repair == "",
          "a structure that arrived as a structure is left alone, and reports no repair")

    payload, repair = _unstringify({"frameworks": "not json at all"}, Frameworks)
    check(payload == {"frameworks": "not json at all"} and repair == "",
          "and text that is not JSON is not guessed at — it fails validation instead")

    # End to end: one call, not two. Every one of those runs used to pay for a
    # correction round on a reply that had arrived complete the first time.
    script = Script(_msg({"frameworks": _json.dumps({"frameworks": [one]})}))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "identify them", Frameworks, max_tokens=3000)))
    check(len(script.calls) == 1, f"the model is asked once ({len(script.calls)})")
    check(result.data.frameworks[0].framework_code == "SFDR", "and the answer is complete")
    check(result.meta.repair == "unstringified" and result.meta.repaired,
          f"recorded as a repair, by name ({result.meta.repair!r})")


def main():
    test_the_model_fills_a_form_instead_of_writing_json()
    test_a_cut_off_answer_is_never_returned_as_a_whole_one()
    test_a_wrong_shape_gets_one_correction_round()
    test_a_model_that_will_not_comply_fails_honestly()
    test_every_call_records_what_it_cost()
    test_the_schemas_the_agents_actually_use()
    test_the_work_program_is_no_longer_parsed_out_of_prose()
    test_an_answer_handed_over_as_text_is_not_paid_for_twice()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
