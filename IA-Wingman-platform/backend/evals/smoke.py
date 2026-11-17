"""Does the API accept what the platform sends? One real call per request shape.

    venv/Scripts/python.exe -m evals.smoke

The unit suites check the shape of a request against a scripted client, and a
script answers whatever it is handed. That is how the judge tier spent weeks
sending a thinking configuration the model had stopped accepting: every test
was green and every real call was a 400. This sends the real thing, as small as
possible, once per shape the platform uses:

    draft typed · judge typed · quick untyped · lens with live search · chat stream

It costs a few cents. It is the gate in front of a model change: a shape the API
rejects shows up here, not in production.
"""
import asyncio
import sys

from services.agent_ledger import agent_context

failures: list[str] = []


def report(name, ok, detail):
    print(f"  {'PASS' if ok else 'FAIL'}  {name} — {detail}")
    if not ok:
        failures.append(name)


async def _shape(name, coro_fn):
    try:
        detail = await coro_fn()
        report(name, True, detail)
    except Exception as exc:  # noqa: BLE001
        report(name, False, f"{type(exc).__name__}: {str(exc)[:300]}")


async def draft_typed():
    from services.agent_contract import run_agent
    from services.agent_schemas import FindingDraft
    r = await run_agent("You draft internal-audit findings.",
                        "Observation: 2 of 25 expense claims lacked a second signature.",
                        FindingDraft, max_tokens=1200)
    return f"{r.meta.model}, rating {r.data.rating}, repair '{r.meta.repair or 'none'}'"


async def judge_typed():
    from services.agent_contract import run_agent
    from services.agent_schemas import RatingChallenge
    r = await run_agent("You give an independent second opinion on a finding's rating.",
                        "Finding: 2 of 25 expense claims lacked a second signature, both under EUR 200. "
                        "Proposed rating: high.", RatingChallenge)
    return f"{r.meta.model}, agrees={r.data.agrees}, {r.meta.thinking_tokens:,} thinking tokens"


async def quick_untyped():
    from services.ai_service import last_call_meta, run_text
    from services.model_tiers import QUICK
    text = await run_text("You suggest short titles.", "Suggest a 4-word title for an audit of expense claims.",
                          max_tokens=200, tier=QUICK)
    meta = last_call_meta()
    return f"{getattr(meta, 'model', '?')}: {text[:60]!r}"


async def lens_with_search():
    from services import lens_supervisory_agent as l2
    from services.agent_schemas import LensSynthesis
    from services.lens_call import synthesise
    prompt = l2._build_lens2_prompt(eng_name="IT Security Management Review", entity="GRP", audit_type="it",
                                    url_context="", manual_keyword=None, use_web_search=True,
                                    jurisdictions=["NL", "EU"])
    found = {}
    result = await synthesise(l2.LENS2_SYSTEM, prompt, LensSynthesis, use_web_search=True, report=found)
    return (f"summary {len(result['summary'])} chars, {len(result['sources'])} sources, "
            f"{found.get('searches_used')}/{found.get('searches_allowed')} searches, "
            f"errors {found.get('search_errors') or 'none'}")


async def chat_stream():
    from services.ai_service import client, _tier_kwargs
    from services.model_tiers import DRAFT
    kwargs = _tier_kwargs(DRAFT, 200, "You are brief.", [{"role": "user", "content": "Say hello in three words."}])
    async with client.messages.stream(**kwargs) as stream:
        async for _ in stream.text_stream:
            pass
        final = await stream.get_final_message()
    text = "".join(b.text for b in final.content if b.type == "text")
    return f"{final.model}: {text[:40]!r}"


async def main():
    with agent_context(agent="smoke"):
        print("request shapes the platform sends — accepted by the API?")
        await _shape("draft tier, structured outputs", draft_typed)
        await _shape("judge tier, structured outputs + adaptive thinking", judge_typed)
        await _shape("quick tier, plain text", quick_untyped)
        await _shape("lens, live search + structured outputs", lens_with_search)
        await _shape("chat stream, draft tier", chat_stream)
    print(f"\n{'ALL ACCEPTED' if not failures else str(len(failures)) + ' REJECTED: ' + str(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
