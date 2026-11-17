"""Tests for model tiering and reasoning room (services/model_tiers.py).

    venv/Scripts/python.exe -m tests.test_model_tiers

No API calls: the client is replaced with scripted replies and the request that
would have been sent is inspected. That is the only way to check the parts that
matter here — which model was chosen, whether thinking was enabled, and whether
the request respects the constraints extended thinking imposes — without paying
for a round trip to find out.
"""
import asyncio
import json
import sys
from types import SimpleNamespace

from services import ai_service
from services.agent_ledger import agent_context
from services.agent_contract import run_agent
from services.agent_schemas import FindingDraft, GovernanceAssessment, PeerReview, RatingChallenge
from services.model_tiers import (
    DRAFT, JUDGE, PREVIOUS, PRICES, QUICK, TIERS, cost_usd, estimate_cost, format_cost,
    request_params, tier_for,
)

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


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
GOOD_CHALLENGE = {"agrees": False, "suggested_rating": "medium", "rationale": "The sample was small."}


def _msg(tool_input, thinking: str = "", stop_reason="end_turn"):
    content = []
    if thinking:
        content.append(SimpleNamespace(type="thinking", thinking=thinking))
    content.append(SimpleNamespace(type="text", text=json.dumps(tool_input)))
    return SimpleNamespace(
        content=content, stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=9000, output_tokens=1200, cache_read_input_tokens=7000),
    )


class Script:
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


def test_the_tiers_say_what_they_are_for():
    print("the tiers:")
    check(set(TIERS) == {"quick", "draft", "judge"}, "three tiers, named for the job not the model")
    check(QUICK.model != DRAFT.model != JUDGE.model, "each one is a different model")
    check(not QUICK.thinks and not DRAFT.thinks and JUDGE.thinks,
          "only the judge tier gets reasoning room")
    check(JUDGE.effort and JUDGE.max_tokens >= 8_000,
          f"the judge's ceiling leaves room for an answer after the reasoning "
          f"({JUDGE.max_tokens:,} tokens, effort {JUDGE.effort})")
    check(all(t.note for t in TIERS.values()), "each tier records why it exists")


def test_the_judgements_are_on_the_judge_tier():
    print("who gets what:")
    check(tier_for("PeerReview") is JUDGE, "the GIAS peer review rates a whole engagement")
    check(tier_for("RatingChallenge") is JUDGE, "the rating challenge exists to disagree well")
    check(tier_for("coherence") is JUDGE, "the engagement coherence check")
    check(tier_for("report_opinion") is JUDGE, "the overall audit opinion")
    check(tier_for("GovernanceAssessment") is DRAFT, "a draft a human reviews stays on draft")
    check(tier_for("title_suggestion") is QUICK, "a title suggestion is a quick job")
    check(tier_for("something_nobody_registered") is DRAFT,
          "an unregistered agent falls back to draft — reviewed by a human either way")


def test_a_draft_run_sends_structured_outputs_and_no_thinking():
    print("the draft tier, on the wire:")
    script = Script(_msg(GOOD_FINDING))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "draft it", FindingDraft)))
    sent = script.calls[0]
    extra = sent.get("extra_body") or {}
    check(sent["model"] == DRAFT.model, f"model is {DRAFT.model}")
    # Thinking is off, in the one form this model accepts. `disabled` — what this
    # test asserted before the migration — is a 400 on Sonnet 5.5. Left unsaid,
    # the model reasons anyway and `max_tokens` pays for it, which is how the
    # governance assessor once truncated on every run.
    check(extra.get("thinking") == {"type": "between_tools"},
          f"thinking is off as Sonnet 5.5 spells it: {extra.get('thinking')}")
    fmt = (extra.get("output_config") or {}).get("format") or {}
    check(fmt.get("type") == "json_schema" and fmt.get("schema", {}).get("additionalProperties") is False,
          "the answer is constrained by structured outputs, closed at every object")
    check((extra.get("output_config") or {}).get("effort") == "high",
          "and the effort the off-setting requires (high or below) is stated, not defaulted")
    # A forced tool is a 400 on this model, and nothing needs one any more.
    check("tools" not in sent and "tool_choice" not in sent, "no tool, and no forced tool_choice")
    check(extra.get("fallbacks") == "default"
          and (sent.get("extra_headers") or {}).get("anthropic-beta") == "server-side-fallback-2026-07-01",
          "a safety decline is retried server-side instead of becoming an outage")
    check(sent["max_tokens"] == DRAFT.max_tokens, "the tier's ceiling is used when none is given")
    check(result.meta.tier == "draft", "the run records which tier produced it")


def test_a_judge_run_asks_for_reasoning_and_obeys_the_api_constraints():
    print("the judge tier, on the wire:")
    script = Script(_msg(GOOD_CHALLENGE, thinking="Weighing the sample size against the rate…" * 40))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "challenge it", RatingChallenge)))
    sent = script.calls[0]

    check(sent["model"] == JUDGE.model, f"model is {JUDGE.model}")
    extra = sent.get("extra_body") or {}
    # On Opus 5.5 thinking cannot be switched off — `disabled` and a token budget
    # are both 400s — so nothing is sent for it, which means adaptive. Effort is
    # the only control, and its default on this model is one level lower than
    # the judge wants, so it is stated.
    check((extra.get("thinking") or {}).get("type") != "disabled",
          f"thinking is not switched off, which this model refuses: {extra.get('thinking')}")
    check((extra.get("output_config") or {}).get("effort") == JUDGE.effort,
          f"the effort comes from the tier: {extra.get('output_config', {}).get('effort')}")
    check("tool_choice" not in sent, "no forced tool — a 400 on this model")
    check(sent["max_tokens"] >= JUDGE.max_tokens,
          f"max_tokens ({sent['max_tokens']:,}) is at least the tier's own ceiling")
    check("temperature" not in sent, "no temperature is set, which thinking also requires")

    check(result.meta.thinking_tokens > 0,
          f"the reasoning is measured and reported ({result.meta.thinking_tokens:,} tokens)")
    check("thinking" in result.meta.sentence(),
          f"and it shows up in the receipt: {result.meta.sentence()}")


def test_a_judge_repair_does_not_replay_a_thinking_turn():
    print("repairing a judge run:")
    bad = dict(GOOD_CHALLENGE, suggested_rating="severe")
    script = Script(_msg(bad, thinking="first pass"), _msg(GOOD_CHALLENGE, thinking="second pass"))
    result = with_script(script, lambda: asyncio.run(
        run_agent("sys", "challenge it", RatingChallenge)))
    check(result.data.suggested_rating == "medium", "the correction round still works")
    second = script.calls[1]["messages"]
    check(all(m["role"] == "user" for m in second),
          "no assistant turn is replayed — a thinking turn would need its signature back")
    check(any("did not meet these constraints" in str(m["content"]) for m in second),
          "the model is still told exactly what was wrong")


def test_the_untyped_path_honours_a_tier_too():
    print("the untyped path:")
    from services.ai_service import run_agent_to_json

    text_msg = SimpleNamespace(
        content=[SimpleNamespace(type="text", text='{"observations": []}')],
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=500, output_tokens=40, cache_read_input_tokens=0),
    )
    script = Script(text_msg)
    with_script(script, lambda: asyncio.run(
        run_agent_to_json("sys", "check coherence", max_tokens=3000, tier=JUDGE)))
    sent = script.calls[0]
    extra = sent.get("extra_body") or {}
    check(sent["model"] == JUDGE.model, "the coherence check reaches the judge model")
    check((extra.get("output_config") or {}).get("effort") == JUDGE.effort
          and (extra.get("thinking") or {}).get("type") != "disabled",
          "and reasons at the judge's effort")
    check(sent["max_tokens"] >= JUDGE.max_tokens,
          f"its ceiling is raised to leave room for an answer ({sent['max_tokens']:,})")

    script = Script(text_msg)
    with_script(script, lambda: asyncio.run(
        run_agent_to_json("sys", "suggest a title", max_tokens=60, tier=QUICK)))
    check(script.calls[0]["model"] == QUICK.model, "and a quick job reaches the quick model")

    # A tier that does not think says so — each model in its own words, because
    # the word that works on one is a 400 on the other.
    expected_off = {DRAFT.name: "between_tools", QUICK.name: "disabled"}
    for tier in (DRAFT, QUICK):
        script = Script(text_msg)
        with_script(script, lambda: asyncio.run(
            run_agent_to_json("sys", "draft rows", max_tokens=5000, tier=tier)))
        thinking = (script.calls[0].get("extra_body") or {}).get("thinking") or {}
        check(thinking.get("type") == expected_off[tier.name],
              f"{tier.name} ({tier.model}) turns thinking off as '{expected_off[tier.name]}'")
        check(script.calls[0]["max_tokens"] == 5000,
              f"and {tier.name}'s ceiling is left where the caller put it")


def test_the_previous_generation_still_gets_a_valid_request():
    print("pinning an agent back:")
    # An agent that measures worse on 5.5 is pinned to PREVIOUS by name. Those
    # models predate between_tools and server-side fallback; sending either would
    # make the rollback itself fail.
    old_draft = request_params(PREVIOUS["draft"])
    check(old_draft["extra_body"].get("thinking") == {"type": "disabled"},
          "the previous draft model is switched off with 'disabled', which it accepts")
    check("fallbacks" not in old_draft["extra_body"] and not old_draft["extra_headers"],
          "and is not sent a fallback it does not support")
    check(request_params(QUICK)["extra_headers"] == {},
          "Haiku 5.5 has no server-side fallback, so none is asked for")


def test_the_schema_the_api_sees():
    print("structured outputs schema:")
    from services.agent_contract import structured_schema
    from services.agent_schemas import GovernanceAssessment
    import json

    sent = json.dumps(structured_schema(GovernanceAssessment))
    unsupported = [k for k in ("maxLength", "minLength", "maxItems", "minItems", "minimum", "maximum")
                   if f'"{k}"' in sent]
    check(not unsupported, f"no keyword the API rejects is sent ({unsupported or 'none'})")
    check("additionalProperties" in sent, "every object is closed")
    # The constraints still hold — Pydantic enforces them on the reply.
    from pydantic import ValidationError
    try:
        GovernanceAssessment.model_validate({"items": [{"requirement": "x", "coverage": "covered",
                                                        "evidence": "", "confidence": "high"}] * 7})
        held = False
    except ValidationError:
        held = True
    check(held, "and a constraint removed from what is sent is still enforced on what comes back")

    # Both found by the first 5.5 eval run, both in this migration rather than in
    # the model. With structured outputs an optional field is simply left out:
    # frameworks came back without their article numbers, lenses without sources.
    from services.agent_schemas import Frameworks, RcsaMappingProposal
    item = structured_schema(Frameworks)["properties"]["frameworks"]["items"]
    check("specific_provision" in item["required"] and set(item["required"]) == set(item["properties"]),
          "every field is asked for, so the article number is not dropped as optional")
    # And a limit taken out of the schema has to be said in words, or the model
    # never knows it exists — a 200+ character `why` failed validation twice.
    why = structured_schema(RcsaMappingProposal)["properties"]["columns"]["items"]["properties"]["why"]
    check("at most 200 characters" in str(why.get("description")),
          f"a removed limit is restated in the field's description: {str(why.get('description'))[-40:]!r}")


def test_money_is_reported_or_declared_unknown():
    print("cost:")
    judge = cost_usd(JUDGE.model, 14_000, 3_000, 9_000)
    draft = cost_usd(DRAFT.model, 14_000, 3_000, 9_000)
    quick = cost_usd(QUICK.model, 900, 60)
    check(judge and draft and judge > draft > quick,
          f"the tiers cost what their order implies: {format_cost(judge)} > "
          f"{format_cost(draft)} > {format_cost(quick)}")
    check(cost_usd("a-model-nobody-priced", 1000, 100) is None,
          "an unpriced model returns None, not a comforting zero")
    check(format_cost(None) == "cost not priced",
          "and the UI is told so in words rather than shown $0.00")

    # The API reports uncached input, cache reads and cache writes separately;
    # they are added. The same 10,000-token prompt, three ways:
    fresh = cost_usd(DRAFT.model, 10_000, 1_000)
    read = cost_usd(DRAFT.model, 0, 1_000, cached_tokens=10_000)
    written = cost_usd(DRAFT.model, 0, 1_000, cache_write_tokens=10_000)
    check(read < fresh < written,
          f"read from cache < fresh < written to cache ({format_cost(read)} < "
          f"{format_cost(fresh)} < {format_cost(written)})")
    # The measured call that exposed the old formula: 87 uncached tokens and
    # 10,836 read from cache. `input - cached` went negative, was floored at
    # zero, and those 87 tokens were counted as free.
    measured = cost_usd(DRAFT.model, 87, 0, cached_tokens=10_836)
    check(abs(measured - (87 * 2.0 + 10_836 * 0.20) / 1_000_000) < 1e-9,
          f"uncached input and cache reads are both paid for ({measured:.6f})")
    opus = cost_usd("claude-opus-5-5", 0, 0, cached_tokens=1_000_000)
    check(abs(opus - 0.20) < 1e-9, "Opus 5.5 reads from cache at its own rate ($0.20/MTok, 0.05x)")

    check(estimate_cost(DRAFT, 40_000) is not None, "a run can be costed before it happens")
    check({t.model for t in TIERS.values()} <= set(PRICES),
          "every tier's model has a price configured")

    # Pinned, because the table once carried a previous generation's prices for
    # months and every cost on screen was 1.5x to 3x too high. A price change is
    # a deliberate edit to this test as well, not something that drifts.
    known = {
        "claude-opus-5": (5.0, 25.0), "claude-sonnet-5": (2.0, 10.0),
        "claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0),
        "claude-haiku-5-5": (0.10, 0.50),
    }
    wrong = {m: (PRICES.get(m) or {}) for m, (i, o) in known.items()
             if (PRICES.get(m) or {}).get("input") != i or (PRICES.get(m) or {}).get("output") != o}
    check(not wrong, f"the prices are the published ones ({wrong or 'all match'})")


def main():
    test_the_tiers_say_what_they_are_for()
    test_the_judgements_are_on_the_judge_tier()
    test_a_draft_run_sends_structured_outputs_and_no_thinking()
    test_a_judge_run_asks_for_reasoning_and_obeys_the_api_constraints()
    test_a_judge_repair_does_not_replay_a_thinking_turn()
    test_the_untyped_path_honours_a_tier_too()
    test_the_previous_generation_still_gets_a_valid_request()
    test_the_schema_the_api_sees()
    test_money_is_reported_or_declared_unknown()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
