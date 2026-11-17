"""The one call the three Topic Intelligence lenses make.

Shared, so that the lenses and the eval suite send exactly the same request: a
lens is its system prompt, its prompt and its schema — everything else (model,
search, structure, ceiling) is the same for all three and lives here.

The lenses used to ask for "JSON in prose" on the untyped path. The phase-0
baseline measured what that cost: three of twelve runs returned the summary's
bullet lines as keys of the object, or a bare list of sources, and the summary
was lost. On the typed path the schema is enforced by the API, so that shape
cannot come back.
"""
from __future__ import annotations

import re

from services.agent_contract import run_agent
from services.ai_service import LENS_SEARCH_BUDGET
from services.model_tiers import DRAFT

#: The lenses were first pinned to the previous draft model (Sonnet 5) on
#: evidence, per the phase-0 rule that an agent measuring worse on the new model
#: goes back with the reason beside it. Measured on 2026-10-22, live search ON:
#:
#:   Sonnet 5.5 (thinking off)        lens 1: 0 searches in 6 of 7 runs;
#:                                     lens 2: 0 in every run that carried the
#:                                     auditor's extra context
#:   Sonnet 5.5 (adaptive, medium)    lens 1: 0 of 2 · lens 2: 8 and 8
#:   Sonnet 5 (thinking off)          lens 1: 8 and 7 · lens 2: 8 and 8
#:
#: A lens that does not search writes a "current developments" summary from
#: training data and it reads exactly like one that searched.
#:
#: The prompts were then reworked for 5.5 (2026-10-22/23): the search asked for
#: as concrete numbered steps at the end of the prompt, "no text before the
#: JSON" removed, and one line after the auditor's note saying it is no reason
#: to skip the research. Measured with those prompts:
#:
#:   searches, Sonnet 5.5     lens 1 searched in every run (was never);
#:                            with the auditor's note 9 of 9, without 12 of 12
#:   eval, 3 runs per case    Sonnet 5.5: 54/54 (100%) · Sonnet 5: 53/54 (98%)
#:
#: So the lenses move to the draft tier with everything else, and get the
#: server-side fallback Sonnet 5 never had. PREVIOUS["draft"] stays one line
#: away if a later measurement says otherwise.
LENS_TIER = DRAFT

#: The web search tool the lenses use: the basic one, not the dynamic-filtering
#: variant (web_search_20260209). Measured live on 2026-10-25, same prompts, the
#: same audit, the current Sonnet 5.5, seven runs:
#:
#:   web_search_20260209   8 of 8 searches, 38-53 s. The model runs its searches in
#:                         code, a block fails, the same query is run again, and the
#:                         allowance is gone before the lens is done ("Server tool
#:                         use limit exceeded during code execution"). Lens 1 came back
#:                         with no sources, lens 2 said search was unavailable, and
#:                         lens 3 failed in one run of two (one result, then cut off).
#:   web_search_20250305   3 searches (one per angle asked for), 18-24 s. Lens 2 and 3:
#:                         6-8 sources, every one with a link; no failures.
#:
#: Small numbers, and the lens 1 results do not separate the two. Revisit on a larger
#: measurement, not on a feeling: the constant is the only place this is set.
SEARCH_TOOL = "web_search_20250305"

#: Room for a summary of six bullets plus up to eight sources — and, with live
#: search on, for the short progress notes the model writes between searches,
#: which count as output too. 4,096 truncated one lens run in twelve once the
#: lenses searched eight times; unused ceiling costs nothing.
LENS_MAX_TOKENS = 8000


#: Added to the system prompt when live search is on. Measured on 2026-10-22:
#: with search enabled, Sonnet 5.5 ran zero searches in five of six lens runs and
#: wrote from its training knowledge instead — a scan that reads as current and
#: is not. Sonnet 5 searched every time. This is the instruction Anthropic's
#: migration guidance gives for exactly that shift; the search report on each
#: lens card shows whether it holds.
SEARCH_INSTRUCTION = (
    "\n\nUse the web search tool to check specifics that may have changed since your training, "
    "such as what is required, which supervisory priorities or enforcement actions are current, "
    "and recent incidents — even when you feel confident. This is researched work: gather current "
    "sources rather than writing from your training knowledge."
)


#: How long one lens may take before the scan stops waiting for it. Measured on
#: 2026-10-22: lenses with eight live searches finish in about 45 seconds, and
#: one smoke-test call took 848 — while the SDK's own timeout and three retries
#: allow up to half an hour. Without this a single stuck search held the whole
#: scan on "Agents running…" for that long. A timed-out request may still be
#: billed for what the model produced before it was cut off; the ledger cannot
#: see that call, because it never returned.
LENS_TIMEOUT_S = 300


def no_search_report() -> dict:
    """What a lens reports when live search was off — said, not left blank."""
    return {"web_search": False, "searches_used": 0, "searches_allowed": 0, "search_errors": []}


def audited_organisation(entity: str, entity_info: dict) -> str:
    """Who is being audited, said so that it cannot be read the other way round.

    The lenses used to get `ENTITY: GRP (DNB)`. The bracket is the supervisor,
    and lens 3 read it as the organisation: its summary opened with "the audit
    sits at DNB, a supervisor and central bank", wrote about a public authority's
    own AI use, and that misreading reached the memo's second risk area.
    """
    return (f"ORGANISATION BEING AUDITED: a bank (entity {entity}). Its supervisor is "
            f"{entity_info['primary_regulator']}. The supervisor is not the auditee: this audit does "
            f"not take place at the supervisor.")


_MARKUP = re.compile(r"</?br\s*/?>", re.IGNORECASE)


def clean_markup(text: str | None, *, joiner: str = "\n") -> str | None:
    """Line breaks a model wrote as HTML become real ones. A `</br>` came through
    in a stored lens verdict and shows as that text on the page."""
    if text is None:
        return None
    return _MARKUP.sub(joiner, text).strip()


#: Appended on the one retry for a lens that had search on and ran none. The
#: summary it wrote the first time came from memory, and a second look at that
#: summary does not change where it came from — only searching does.
SEARCH_REQUIRED = (
    "\n\nYour previous attempt ran no web search at all, so what it said came from memory. Searching is "
    "the task: run the searches listed above BEFORE you write anything, and state incidents, dates, "
    "amounts and names only where a search result supports them."
)


async def synthesise(system: str, prompt: str, schema, use_web_search: bool,
                     report: dict | None = None, tier=None, run_id: str | None = None) -> dict:
    """Run one lens and return its answer as a plain dict, ready to store.

    `tier` exists for measurement: the lenses are pinned to LENS_TIER, and moving
    them is decided by running the same call on another tier first.

    `run_id` is the lens's own AgentRun. It goes into the ledger context so the
    calls carry it — which is what lets the edit register say which model and
    which prompt version wrote a lens summary. The scan ran without one before.
    """
    from contextlib import nullcontext

    from services.agent_ledger import agent_context

    import asyncio

    from services.agent_contract import AgentTimedOut

    tier = tier or LENS_TIER
    with agent_context(run_id=run_id) if run_id else nullcontext():
        try:
            return await asyncio.wait_for(
                _synthesise(system, prompt, schema, use_web_search, report, tier),
                timeout=LENS_TIMEOUT_S,
            )
        except asyncio.TimeoutError as exc:
            raise AgentTimedOut(
                f"The lens was stopped after {LENS_TIMEOUT_S // 60} minutes without an answer. "
                "Run the scan again; a lens normally finishes in under a minute."
            ) from exc


async def _synthesise(system, prompt, schema, use_web_search, report, tier) -> dict:
    tools = ([{"type": SEARCH_TOOL, "name": "web_search", "max_uses": LENS_SEARCH_BUDGET}]
             if use_web_search else None)
    if use_web_search:
        system = system + SEARCH_INSTRUCTION
    outcome = await run_agent(system, prompt, schema, max_tokens=LENS_MAX_TOKENS, tier=tier,
                              server_tools=tools, report=report)

    # A lens that had search on and ran none wrote from memory — and says so in
    # its own text, which then reads as a verdict. Ask once more, with the
    # instruction to search spelled out; if it still does not search, the report
    # keeps saying 0 searches and the page says so beside the lens.
    if use_web_search and report is not None and report.get("searches_used", 0) == 0 \
            and not report.get("search_errors"):
        outcome = await run_agent(system, prompt + SEARCH_REQUIRED, schema, max_tokens=LENS_MAX_TOKENS,
                                  tier=tier, server_tools=tools, report=report)
        report["retried"] = True

    result = outcome.data.model_dump()
    # The model sometimes hands back no sources although its searches returned
    # pages (measured: lens 1 returned none in three of five runs, seven or eight
    # in the next three). The pages the search itself returned are not the model's
    # to forget, so they stand in, typed as search results and nothing more.
    if use_web_search and report and not result.get("sources") and report.get("results"):
        result["sources"] = [
            {"title": hit["title"], "url": hit["url"], "date": None, "confidence": None, "type": "search_result"}
            for hit in report["results"][:8]
        ]
        report["sources_from_search"] = True
    for key in ("summary", "materiality_signal"):
        if key in result:
            result[key] = clean_markup(result[key], joiner="\n" if key == "summary" else " ")
    return result
