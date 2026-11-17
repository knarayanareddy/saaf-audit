"""Topic Intelligence, the verification round.

    venv/Scripts/python.exe -m tests.test_ti_verification

The first scan on 26-047 said "unconfirmed" in five places about the one date the audit
turned on, and nothing went back to check. The round that does is narrow and cannot
confirm what it did not find:

- a verdict stands only if a search ran;
- a source link stands only if it is a page the search returned;
- what it settles reaches the primer and the proposal, what it does not stays open.

No API calls: the model is replaced by a script.
"""
import asyncio
import sys
from types import SimpleNamespace

import services.ti_verification as tv
from services.agent_schemas import VerificationCheck, VerificationResult
from services.orchestrator import _build_primer_prompt
from services.orchestrator_agent import _build_synthesis_prompt
from models.engagement import Engagement

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def item(verdict="confirmed", url="https://eur-lex.europa.eu/a"):
    return {"claim": "High-risk duties apply from 2 December 2027", "verdict": verdict,
            "finding": "Regulation (EU) 2026/1744 sets 2 December 2027.", "source_url": url}


def test_a_verdict_needs_a_search_and_a_link_needs_a_returned_page():
    print("what is kept:")
    searched = {"searches_used": 2, "searches_allowed": 4, "queries": ["q"], "search_errors": [],
                "results": [{"title": "t", "url": "https://eur-lex.europa.eu/a"}]}
    out = tv.clean_result({"checks": [item(), item(url="https://invented.example/x")]}, searched)
    check([c["verdict"] for c in out["checks"]] == ["confirmed", "confirmed"], "with a search behind it, the verdict stands")
    check([c["source_url"] for c in out["checks"]] == ["https://eur-lex.europa.eu/a", None],
          "a link that is not among the returned pages is dropped, one that is stays")

    none = {"searches_used": 0, "searches_allowed": 4, "queries": [], "search_errors": [], "results": []}
    out = tv.clean_result({"checks": [item("confirmed"), item("corrected")]}, none)
    check(all(c["verdict"] == "not_found" for c in out["checks"]) and all(c["source_url"] is None for c in out["checks"]),
          "no search ran: every verdict becomes 'not found', and no link survives")
    check(all("not checked" in c["finding"] for c in out["checks"]), "and says why")
    check(out["searches_used"] == 0 and out["searches_allowed"] == 4, "the report keeps the real number of searches")


def test_the_round_is_narrow():
    print("the prompt and the schema:")
    prompt = tv.build_verification_prompt("AI", {"Normative": "Omnibus is unconfirmed.", "Society": None})
    check("Omnibus is unconfirmed" in prompt and "Society summary" not in prompt, "it reads the lens summaries, and skips an empty one")
    check("at most 5" in prompt and f"at most {tv.VERIFY_SEARCH_BUDGET} web searches" in prompt,
          "at most 5 statements, within a search ceiling")
    check("Never use \"confirmed\" for something you did not find" in prompt, "and may not confirm what it did not find")
    check(tv.VERIFY_SEARCH_BUDGET <= 4, "the ceiling is small (a few searches, not a second scan)")
    try:
        VerificationResult(checks=[VerificationCheck(claim="x" * 12, verdict="confirmed", finding="y" * 12)] * 6)
        capped = False
    except Exception:  # noqa: BLE001
        capped = True
    check(capped, "more than 5 checks is refused by the schema")


async def run_verify(lenses, searches_used, data):
    calls = []

    async def fake(system, prompt, schema, **kwargs):
        calls.append(kwargs)
        kwargs["report"].update({"web_search": True, "searches_used": searches_used, "searches_allowed": 4,
                                 "search_errors": [], "queries": ["q1"],
                                 "results": [{"title": "t", "url": "https://eur-lex.europa.eu/a"}]})
        return SimpleNamespace(data=data)

    real = tv.run_agent
    tv.run_agent = fake
    try:
        return await tv.verify("AI", lenses), calls
    finally:
        tv.run_agent = real


def test_the_round_runs_only_when_there_is_something_to_read_and_never_breaks_the_scan():
    print("running it:")
    data = VerificationResult(checks=[VerificationCheck(**{k: v for k, v in item().items()})])
    out, calls = asyncio.run(run_verify({"Normative": "Some summary text about the topic."}, 2, data))
    check(out and out["checks"][0]["verdict"] == "confirmed" and calls[0]["server_tools"][0]["max_uses"] == tv.VERIFY_SEARCH_BUDGET,
          "it runs with the search tool and the ceiling")
    out, calls = asyncio.run(run_verify({"Normative": None, "Society": "  "}, 2, data))
    check(out is None and not calls, "no lens output: it does not run, and costs nothing")

    async def boom(*a, **k):
        raise RuntimeError("api down")

    real = tv.run_agent
    tv.run_agent = boom
    try:
        out = asyncio.run(tv.verify("AI", {"Normative": "Some summary text about the topic."}))
    finally:
        tv.run_agent = real
    check(out is None, "a failed round returns nothing instead of failing the scan")


def test_a_round_that_skipped_searching_is_asked_again():
    print("a round that did not search:")
    data = VerificationResult(checks=[VerificationCheck(**item())])

    async def run(lens_text, searches):
        queue = list(searches)
        prompts = []

        async def fake(system, prompt, schema, **kwargs):
            prompts.append(prompt)
            n = queue.pop(0)
            kwargs["report"].update({"web_search": True, "searches_used": n, "searches_allowed": 4, "search_errors": [],
                                     "queries": [], "results": []})
            return SimpleNamespace(data=data)

        real = tv.run_agent
        tv.run_agent = fake
        try:
            return await tv.verify("AI", {"Normative": lens_text}), prompts
        finally:
            tv.run_agent = real

    open_text = "The Omnibus is reportedly adopted; its date is unconfirmed."
    out, prompts = asyncio.run(run(open_text, [0, 3]))
    check(len(prompts) == 2 and tv.CHECK_REQUIRED in prompts[1] and out["retried"] is True and out["searches_used"] == 3,
          "open points and no search: asked once more, and the report says it searched on the second attempt")
    out, prompts = asyncio.run(run(open_text, [0, 0]))
    check(len(prompts) == 2 and out["searches_used"] == 0 and all(c["verdict"] == "not_found" for c in out["checks"]),
          "still no search: it stops, and nothing it says counts as checked")
    out, prompts = asyncio.run(run(open_text, [2]))
    check(len(prompts) == 1 and out["retried"] is False, "a round that searched is not asked again")
    out, prompts = asyncio.run(run("Everything here is stated with an official source.", [0]))
    check(len(prompts) == 1, "no open points in the summaries: nothing to retry")
    check(tv.has_open_points({"a": "Dates are Unconfirmed."}) and not tv.has_open_points({"a": "DORA applies since 2025.", "b": None}),
          "open points are recognised by the words the lenses use for them")


def test_what_it_settles_reaches_the_primer_and_the_proposal():
    print("what it feeds:")
    text = tv.format_for_prompt({"checks": [item("corrected"), item("not_found")]})
    check("[CORRECTED]" in text and "[NOT SETTLED]" in text, "the findings are written as settled, corrected or not settled")
    check(tv.format_for_prompt(None) is None and tv.format_for_prompt({"checks": []}) is None, "nothing to say: nothing is added")
    primer = _build_primer_prompt("AI", ["EU"], {"Normative": "x" * 30}, None, text)
    check("[CORRECTED]" in primer and "keep calling it unconfirmed" in primer, "the primer sees the verification")
    eng = Engagement(name="AI", entity="GRP", audit_type="it")
    synthesis = _build_synthesis_prompt(eng, "l1", "l2", "l3", None, text)
    check("[CORRECTED]" in synthesis and "follow the verification" in synthesis, "and so does the proposal")
    check("verification" not in _build_synthesis_prompt(eng, "l1", "l2", "l3", None).lower().replace("verification of", ""),
          "without a verification the prompts are unchanged")


def main_():
    test_a_verdict_needs_a_search_and_a_link_needs_a_returned_page()
    test_the_round_is_narrow()
    test_the_round_runs_only_when_there_is_something_to_read_and_never_breaks_the_scan()
    test_a_round_that_skipped_searching_is_asked_again()
    test_what_it_settles_reaches_the_primer_and_the_proposal()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
