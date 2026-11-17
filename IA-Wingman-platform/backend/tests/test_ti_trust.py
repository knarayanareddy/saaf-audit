"""Topic Intelligence, the faults of the 25 October run.

    venv/Scripts/python.exe -m tests.test_ti_trust

The first run on 26-047 with live search showed four faults, each with a cause in
the code, and none of them visible to the suites that existed:

1. Lens 3 ran 0 of its 8 searches. Its prompt asked for search in general terms
   and offered "built-in knowledge if nothing is found" as a way out.
2. It also read `ENTITY: GRP (DNB)` as "the audit sits at DNB".
3. The plain-language primer stopped mid-sentence ("It also requires A"): a
   500-token ceiling on free text, and nothing looked at why it stopped.
4. The kick-off prompt called the audit team's still-to-do tasks "completed".

No API calls: the model is replaced by a script, and the prompts are read.
"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import services.lens_call as lens_call
from services.agent_schemas import SocietyLensSynthesis, TopicPrimer
from services.lens_regulatory_agent import _build_lens1_prompt
from services.lens_society_agent import _build_lens3_prompt
from services.lens_supervisory_agent import _build_lens2_prompt
from services.orchestrator import _build_primer_prompt, format_primer

failures: list[str] = []
# Long enough to pass the lens schema, which refuses a summary too short to hold a lead and bullets.
LONG_BULLETS = "\n- a bullet about what the research found, with enough words to read like one." * 4
BACKEND = Path(__file__).resolve().parent.parent


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def lens_prompts(web: bool = True):
    return {
        1: _build_lens1_prompt("Artificial Intelligence", "GRP", "it", "", None, web, ["NL", "EU"], "scoped to governance"),
        2: _build_lens2_prompt("Artificial Intelligence", "GRP", "it", "", None, web, ["NL", "EU"], "scoped to governance"),
        3: _build_lens3_prompt("Artificial Intelligence", "GRP", "it", None, web, ["NL", "EU"], "scoped to governance"),
    }


def test_the_organisation_is_not_the_supervisor():
    print("who is being audited:")
    for n, prompt in lens_prompts().items():
        check("ORGANISATION BEING AUDITED: a bank" in prompt and "not the auditee" in prompt,
              f"lens {n} says the audited organisation is a bank and its supervisor is not the auditee")
        check("ENTITY: GRP (DNB" not in prompt, f"and lens {n} no longer says 'ENTITY: GRP (DNB…)'")


def test_lens_3_searches_for_something_concrete():
    print("lens 3's prompt:")
    on, off = lens_prompts(True)[3], lens_prompts(False)[3]
    check("BEFORE YOU WRITE, run these web searches" in on and all(f"\n{i}. " in on for i in (1, 2, 3)),
          "asks for three numbered searches, like lens 1 and 2")
    check("built-in knowledge of the topic" not in on and "from memory" in on,
          "no longer offers memory as the way out when search is on")
    check("nothing found" in on, "and says what to write when a search finds nothing")
    check("BEFORE YOU WRITE" not in off and "Live search is off" in off,
          "with search off it asks for no search and names no unattributed incident")


async def test_a_lens_that_did_not_search_is_asked_again():
    print("a lens that ran no search:")
    calls: list[str] = []

    def script(searches_per_call: list[int]):
        queue = list(searches_per_call)

        async def fake(system, prompt, schema, **kwargs):
            calls.append(prompt)
            report = kwargs["report"]
            report.update({"web_search": True, "searches_used": queue.pop(0), "searches_allowed": 8,
                           "search_errors": []})
            return SimpleNamespace(data=SocietyLensSynthesis(
                summary="Lead sentence about the topic.<br>- first bullet" + LONG_BULLETS + "</br>- second bullet",
                materiality_signal="This matters for the audit.</br>"))
        return fake

    real = lens_call.run_agent
    try:
        calls.clear()
        lens_call.run_agent = script([0, 3])
        report = lens_call.no_search_report()
        result = await lens_call._synthesise("sys", "ask", SocietyLensSynthesis, True, report, lens_call.LENS_TIER)
        check(len(calls) == 2 and lens_call.SEARCH_REQUIRED in calls[1],
              "no search the first time: asked once more, with the instruction to search")
        check(report["searches_used"] == 3 and report["retried"] is True, "and the report says it searched on the second attempt")

        calls.clear()
        lens_call.run_agent = script([0, 0])
        report = lens_call.no_search_report()
        await lens_call._synthesise("sys", "ask", SocietyLensSynthesis, True, report, lens_call.LENS_TIER)
        check(len(calls) == 2 and report["searches_used"] == 0 and report["retried"] is True,
              "still none: it stops there, and the report keeps saying 0 searches (the page shows it)")

        calls.clear()
        lens_call.run_agent = script([4])
        report = lens_call.no_search_report()
        await lens_call._synthesise("sys", "ask", SocietyLensSynthesis, True, report, lens_call.LENS_TIER)
        check(len(calls) == 1 and "retried" not in report, "a lens that searched is not asked again")

        calls.clear()
        lens_call.run_agent = script([0])
        report = lens_call.no_search_report()
        await lens_call._synthesise("sys", "ask", SocietyLensSynthesis, False, report, lens_call.LENS_TIER)
        check(len(calls) == 1, "with live search off nothing is retried")

        lens_call.run_agent = script([2])
        report = lens_call.no_search_report()
        result = await lens_call._synthesise("sys", "ask", SocietyLensSynthesis, True, report, lens_call.LENS_TIER)
        check("</br>" not in result["summary"] and "<br>" not in result["summary"]
              and result["summary"].count("\n") == 2 + LONG_BULLETS.count("\n"), "line breaks written as HTML become real ones")
        check("</br>" not in result["materiality_signal"], "and the materiality signal is clean")
    finally:
        lens_call.run_agent = real


def test_the_primer_cannot_be_cut_off_and_knows_what_the_lenses_found():
    print("the primer:")
    primer = TopicPrimer(lead="AI in a bank means machine-based systems that decide or advise.",
                         in_practice="Auditors look at the inventory.", why_it_matters="Biased outcomes harm customers.",
                         rules="The EU AI Act applies; high-risk duties apply from 2 December 2027.",
                         what_surfaces="Shadow AI and vendor dependence.")
    text = format_primer(primer)
    check(text.count("\n- **") == 4 and text.endswith("vendor dependence."), "four bullets, ending on a full sentence")
    prompt = _build_primer_prompt("Artificial Intelligence", ["NL", "EU"],
                                  {"Normative & regulatory": "The Omnibus moved Annex III to 2 Dec 2027.",
                                   "Society": None}, "first AI audit")
    check("Omnibus moved Annex III" in prompt, "it is written from the lens summaries, so it can know what they found")
    check("Society summary" not in prompt, "a lens with no output is left out")
    check("only if a summary gives it" in prompt and "unconfirmed" in prompt,
          "and told not to state a date or status the summaries do not give")
    src = (BACKEND / "services" / "orchestrator.py").read_text(encoding="utf-8")
    check("max_tokens=500" not in src and "run_agent(_PRIMER_SYSTEM" in src, "free text with a 500-token ceiling is gone")


def test_the_search_tool_and_its_failures():
    print("the search tool:")
    from services.ai_service import search_report

    failed = SimpleNamespace(type="code_execution_tool_result", content=SimpleNamespace(
        stderr="Server tool use limit exceeded during code execution.", return_code=1))
    fine = SimpleNamespace(type="code_execution_tool_result", content=SimpleNamespace(stderr="", return_code=0))
    message = SimpleNamespace(content=[fine, failed], usage=SimpleNamespace(server_tool_use={"web_search_requests": 8}))
    report = search_report(message, 8)
    check(report["search_errors"] == ["tool_use_limit_exceeded"],
          f"a search lost to the code-execution limit is recorded, not read as 'used all 8' ({report['search_errors']})")
    check(not search_report(SimpleNamespace(content=[fine], usage=SimpleNamespace(server_tool_use={"web_search_requests": 3})), 8)["search_errors"],
          "and a clean code-execution result adds nothing")
    check(lens_call.SEARCH_TOOL == "web_search_20250305",
          "the lenses use the basic search tool (measured: the dynamic one lost its allowance to retried code)")

    sent = {}

    async def capture(system, prompt, schema, **kwargs):
        sent.update(kwargs)
        kwargs["report"].update({"web_search": True, "searches_used": 3, "searches_allowed": 8, "search_errors": []})
        return SimpleNamespace(data=SocietyLensSynthesis(
            summary="Lead sentence about the topic." + LONG_BULLETS))

    real = lens_call.run_agent
    lens_call.run_agent = capture
    try:
        asyncio.run(lens_call._synthesise("s", "p", SocietyLensSynthesis, True, lens_call.no_search_report(), lens_call.LENS_TIER))
    finally:
        lens_call.run_agent = real
    check(sent["server_tools"][0]["type"] == lens_call.SEARCH_TOOL, "and that is the tool the request actually carries")


def test_the_search_itself_is_recorded_and_stands_in_for_missing_sources():
    print("what the search returned:")
    from services.ai_service import search_report

    def hit(title, url):
        # The API returns each hit as a plain dict (checked live on 2026-11-06), so that is
        # the shape under test; the object shape is covered by test_search_report.
        return {"type": "web_search_result", "title": title, "url": url, "encrypted_content": "x"}

    blocks = [
        SimpleNamespace(type="server_tool_use", name="web_search", input={"query": "EU AI Act amendments 2026"}),
        SimpleNamespace(type="web_search_tool_result", content=[hit("AI Act", "https://eur-lex.europa.eu/a"),
                                                                 hit("Omnibus", "https://eur-lex.europa.eu/b")]),
        SimpleNamespace(type="server_tool_use", name="web_search", input={"query": "EBA guidelines AI"}),
        SimpleNamespace(type="web_search_tool_result", content=[hit("AI Act again", "https://eur-lex.europa.eu/a")]),
    ]
    message = SimpleNamespace(content=blocks, usage=SimpleNamespace(server_tool_use={"web_search_requests": 2}))
    report = search_report(message, 8)
    check(report["queries"] == ["EU AI Act amendments 2026", "EBA guidelines AI"], "the queries it ran are recorded, in order")
    check([r["url"] for r in report["results"]] == ["https://eur-lex.europa.eu/a", "https://eur-lex.europa.eu/b"],
          "and the pages the search returned, each once")

    async def run(sources):
        async def fake(system, prompt, schema, **kwargs):
            kwargs["report"].update({"web_search": True, "searches_used": 2, "searches_allowed": 8, "search_errors": [],
                                     "queries": report["queries"], "results": report["results"]})
            return SimpleNamespace(data=SocietyLensSynthesis(
                summary="Lead sentence about the topic." + LONG_BULLETS,
                sources=sources))
        real = lens_call.run_agent
        lens_call.run_agent = fake
        try:
            rep = lens_call.no_search_report()
            return await lens_call._synthesise("s", "p", SocietyLensSynthesis, True, rep, lens_call.LENS_TIER), rep
        finally:
            lens_call.run_agent = real

    result, rep = asyncio.run(run([]))
    check([s["url"] for s in result["sources"]] == ["https://eur-lex.europa.eu/a", "https://eur-lex.europa.eu/b"]
          and all(s["type"] == "search_result" for s in result["sources"]) and rep.get("sources_from_search") is True,
          "a lens that listed no sources gets the pages its searches returned, typed search_result and flagged")
    result, rep = asyncio.run(run([{"title": "Its own", "url": "https://example.org/x", "type": "search_result"}]))
    check([s["title"] for s in result["sources"]] == ["Its own"] and "sources_from_search" not in rep,
          "a lens that listed its own sources keeps them")


def test_the_kickoff_does_not_call_open_tasks_done():
    print("the kick-off prompt:")
    src = (BACKEND / "services" / "kickoff_drafter.py").read_text(encoding="utf-8")
    check("IA PRE-WORK COMPLETED" not in src and "STILL TO DO" in src,
          "the audit team's pre-work is called what it is: still to do")


def main_():
    test_the_organisation_is_not_the_supervisor()
    test_lens_3_searches_for_something_concrete()
    asyncio.run(test_a_lens_that_did_not_search_is_asked_again())
    test_the_primer_cannot_be_cut_off_and_knows_what_the_lenses_found()
    test_the_search_tool_and_its_failures()
    test_the_search_itself_is_recorded_and_stands_in_for_missing_sources()
    test_the_kickoff_does_not_call_open_tasks_done()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main_()
