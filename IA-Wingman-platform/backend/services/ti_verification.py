"""The verification round of a Topic Intelligence scan.

The three lenses research broadly and each leaves things open: "unconfirmed", "reportedly",
"expected to apply from". On the first run on 26-047 the memo repeated the word "unconfirmed"
in five places, and the one fact the whole audit turned on (which date the AI Act's
high-risk duties apply from) was one of them. Nothing went back to check.

This is that check, and it is deliberately narrow: one call, a few searches, and only the
statements that change the audit if they are wrong. It does not re-research the topic.

What it records is not taken on the model's word:
- a verdict is only kept if a search actually ran (`searches_used > 0`);
- a source link is only kept if it is one of the pages the search returned.
"""
from __future__ import annotations

import logging
import re

from services.agent_contract import run_agent
from services.agent_schemas import VerificationResult
from services.ai_service import BASE_SYSTEM_PROMPT
from services.lens_call import LENS_MAX_TOKENS, LENS_TIER, SEARCH_TOOL, no_search_report
from services.prompt_safety import wrap_untrusted

log = logging.getLogger("ia.wingman")

#: Searches the round may use per scan. Estimated at tens of cents a scan, and a ceiling
#: so that a round that wants to re-research the topic cannot.
VERIFY_SEARCH_BUDGET = 4

VERIFY_SYSTEM = BASE_SYSTEM_PROMPT + (
    "\n\nYou are the verification step of a research scan for an internal audit. You do not "
    "research the topic again. You check a few specific statements against official sources "
    "and report exactly what the source says. You never confirm something you did not find."
)


def build_verification_prompt(topic: str, lenses: dict[str, str | None]) -> str:
    parts = [f'The audit topic is "{topic}". Three research summaries follow.']
    for name, text in lenses.items():
        if text and text.strip():
            parts.append(wrap_untrusted(text, f"{name} summary"))
    parts.append(f"""From the summaries above choose at most 5 statements to check. Choose only statements that would change the audit if they were wrong:
1. anything the summaries themselves call unconfirmed, pending, proposed, expected or reported;
2. the date from which an obligation applies, or the date a rule was adopted or published;
3. a regulation number, a legal reference or an article number the audit would cite.
Skip general background and anything the summaries state with an official source.

For each statement, search for an official source (eur-lex.europa.eu, the regulator's own site, the Official Journal) and report:
- "confirmed": an official source says the same thing;
- "corrected": an official source says something different; state what it says;
- "not_found": your searches did not settle it. Say so. Never use "confirmed" for something you did not find.
You have at most {VERIFY_SEARCH_BUDGET} web searches; use them on the statements that matter most. If nothing in the summaries needs checking, return no checks.""")
    return "\n\n".join(parts)


#: Words with which the lenses mark a point as open. Their presence in a summary, with no
#: search run, is the sign that the round skipped what it was there for: measured, the
#: same summaries produced three checks in one run and none in the next.
_OPEN_MARKERS = re.compile(
    r"unconfirmed|not confirmed|to be confirmed|reportedly|reported to|expected to|pending|"
    r"proposed|unclear|yet to be|not yet", re.IGNORECASE)

#: Added on the one retry when the round ran no search although the summaries leave points open.
CHECK_REQUIRED = (
    "\n\nYour previous attempt ran no web search and checked nothing, but the summaries above leave points "
    "open (they use words like unconfirmed, expected or reported). Pick the most important of them and "
    "search for an official source before you answer."
)


def has_open_points(lenses: dict[str, str | None]) -> bool:
    return any(_OPEN_MARKERS.search(text or "") for text in lenses.values())


def clean_result(data: dict, report: dict) -> dict:
    """What may be stored from the model's answer, given what the search did."""
    searched = report.get("searches_used", 0) > 0
    returned = {hit["url"] for hit in report.get("results", [])}
    checks = []
    for item in data.get("checks", []):
        verdict = item["verdict"]
        if not searched and verdict != "not_found":
            # A verdict with no search behind it is the model's memory under a new label.
            verdict = "not_found"
            item = {**item, "finding": "No search ran, so this was not checked."}
        url = item.get("source_url")
        checks.append({**item, "verdict": verdict, "source_url": url if url in returned else None})
    return {
        "checks": checks,
        "searches_used": report.get("searches_used", 0),
        "searches_allowed": report.get("searches_allowed", VERIFY_SEARCH_BUDGET),
        "queries": report.get("queries", []),
        "errors": report.get("search_errors", []),
        "retried": bool(report.get("retried", False)),
    }


async def verify(topic: str, lenses: dict[str, str | None]) -> dict | None:
    """Run the round. Returns the stored form, or None when there was nothing to check or the
    round failed: the scan carries on without it, as it does without a primer."""
    if not any((text or "").strip() for text in lenses.values()):
        return None
    report = no_search_report()
    try:
        outcome = await run_agent(
            VERIFY_SYSTEM, build_verification_prompt(topic, lenses), VerificationResult,
            max_tokens=LENS_MAX_TOKENS, tier=LENS_TIER,
            server_tools=[{"type": SEARCH_TOOL, "name": "web_search", "max_uses": VERIFY_SEARCH_BUDGET}],
            report=report,
        )
        if report.get("searches_used", 0) == 0 and has_open_points(lenses):
            outcome = await run_agent(
                VERIFY_SYSTEM, build_verification_prompt(topic, lenses) + CHECK_REQUIRED, VerificationResult,
                max_tokens=LENS_MAX_TOKENS, tier=LENS_TIER,
                server_tools=[{"type": SEARCH_TOOL, "name": "web_search", "max_uses": VERIFY_SEARCH_BUDGET}],
                report=report,
            )
            report["retried"] = True
    except Exception:  # noqa: BLE001
        log.exception("Verification round failed — the scan carries on without it")
        return None
    return clean_result(outcome.data.model_dump(), report)


def format_for_prompt(verification: dict | None) -> str | None:
    """The round's findings as text for the primer and the synthesis, so what was settled
    is written as settled and what was not is still called open."""
    if not verification or not verification.get("checks"):
        return None
    labels = {"confirmed": "CONFIRMED", "corrected": "CORRECTED", "not_found": "NOT SETTLED"}
    lines = [f"- [{labels[c['verdict']]}] {c['claim']} — {c['finding']}" for c in verification["checks"]]
    return "\n".join(lines)
