"""Lens 3: Society, Trends & Incidents — Topic Intelligence v2.

Focuses on media coverage, political attention, NGO reports, peer incidents
(lawsuits, fines, operational failures at other banks), and emerging risks
not yet captured in formal regulation.
Claude uses built-in web search (Anthropic API) targeting financial media.
Output: 150-200 word synthesis + materiality_signal + cited sources.
"""
import json
import logging

from database import AsyncSessionLocal
from services.agent_contract import failure_message
from models.agent_run import AgentRun
from models.engagement import Engagement, jurisdictions_or_default
from services.agent_schemas import SocietyLensSynthesis
from services.lens_call import audited_organisation, no_search_report, synthesise
from services.prompt_safety import wrap_untrusted
from services.query_generator import ENTITY_DOMAINS


LENS3_SYSTEM = """You are a senior analyst for the organisation's Internal Audit function.
Your task is to capture what is happening in the WORLD around the audit topic:
media narrative, political and NGO attention, peer bank incidents, and emerging
trends not yet formally regulated.

SCOPE OF THIS LENS:
- Financial media coverage (FT, Reuters, Bloomberg, risk.net)
- Political attention (parliamentary questions, government reports)
- NGO and civil society reports (Global Witness, Transparency International, etc.)
- Peer incidents at other banks (fines, lawsuits, operational failures, scandals)
- Emerging risks or trends not yet captured in formal regulation

WHAT NOT TO INCLUDE:
- Formal legislation (that is Lens 1)
- Supervisor priorities and enforcement (that is Lens 2)

TONE:
- Name specific institutions, cases, and amounts where found
- Be clear about what is an incident vs. a trend vs. political attention
- Distinguish between things that happened TO peer banks vs. general trends"""


def _build_lens3_prompt(
    eng_name: str,
    entity: str,
    audit_type: str,
    manual_keyword: str | None,
    use_web_search: bool,
    jurisdictions: list[str] | None = None,
    extra_context: str | None = None,
) -> str:
    entity_info = ENTITY_DOMAINS.get(entity, ENTITY_DOMAINS["GRP"])
    juris = ", ".join(jurisdictions) if jurisdictions else "NL, EU"
    jurisdiction_note = (
        f"\nJURISDICTIONS IN SCOPE: {juris}. Anchor the societal, media and incident context to these "
        f"jurisdictions (and EU-/international-level developments that touch them). Prefer peer incidents, "
        f"NGO/political attention and enforcement in the in-scope jurisdictions; only mention a foreign "
        f"case when it is directly relevant to how this topic plays out in the jurisdictions above.\n"
    )
    keyword_note = (
        f"\nAUDITOR FOCUS KEYWORD: '{manual_keyword}' — give this extra attention.\n"
        if manual_keyword else ""
    )
    # Concrete searches, asked for directly, as lens 1 and 2 have: a general "use
    # web search" plus a "from built-in knowledge if nothing is found" let the
    # current models skip searching altogether (measured: 0 of 8 searches), and
    # they then wrote incidents and amounts from memory. The sources named are ones
    # that can be read without a subscription — the paywalled papers cannot.
    search_instruction = (
        f"\nBEFORE YOU WRITE, run these web searches and use what they return:\n"
        f"1. Peer incidents and enforcement: fines, sanctions, supervisory measures or scandals involving "
        f"banks on '{eng_name}' (2024-2026) — press releases of {entity_info['primary_regulator']} and the "
        f"other supervisors and data-protection authorities of the in-scope jurisdictions, and the "
        f"national and European financial press (reuters.com, and for NL for example fd.nl, nos.nl, nrc.nl).\n"
        f"2. Political and public attention: parliamentary questions, government and audit-office reports "
        f"and public registers on '{eng_name}' in the in-scope jurisdictions (for NL: tweedekamer.nl, "
        f"rekenkamer.nl, rijksoverheid.nl).\n"
        f"3. Civil-society and research attention: reports by NGOs, consumer organisations and research "
        f"institutes on '{eng_name}' in banking, and emerging risks not yet in regulation.\n"
        f"Name an incident, a fine, an amount or an institution only where a search result supports it, and "
        f"list that result in sources.\n"
    ) if use_web_search else ""
    # What the model may do when a search finds nothing differs with search on and
    # off. With search on there is no fallback to memory: it was the way out.
    nothing_found_rule = (
        "- If a search returns nothing for one of the points above, write 'nothing found' for that point. "
        "Never describe an incident, fine or amount from memory."
        if use_web_search else
        "- Live search is off: write from built-in knowledge, say so in the lead sentence, and name no "
        "incident, fine or amount you cannot attribute to a specific source."
    )

    # The auditor's own context is wrapped as data, not instruction: it is often
    # pasted out of a document, and what it is for is to inform the analysis,
    # never to change the task.
    context_note = (
        "\nCONTEXT THE AUDITOR ADDED (what they already know about this audit):\n"
        f"{wrap_untrusted(extra_context, 'the auditor’s own notes')}\n"
        # See lens 1: without this line the wrapped note suppressed searching.
        "The note above is background for your analysis. It is no reason to skip the "
        "research asked for below.\n"
        if extra_context and extra_context.strip() else ""
    )

    return f"""Produce a Lens 3 (Society, Trends & Incidents) synthesis for this internal audit.

ENGAGEMENT: {eng_name}
{audited_organisation(entity, entity_info)}
AUDIT TYPE: {audit_type}
{jurisdiction_note}{keyword_note}{context_note}
The answer has this shape (the format itself is enforced for you):
{{
  "summary": "Write for a busy auditor, scannable: ONE short lead sentence, then 4-6 bullet lines each starting with '- '. Cover what is happening around this topic: media narrative, peer incidents with names/amounts if found, NGO or political attention, emerging trends not yet regulated. Every bullet on its own line prefixed with '- '.",
  "materiality_signal": "One sentence: what this means for the urgency or scope of THIS audit at {entity}.",
  "sources": [
    {{
      "title": "Article or report title",
      "url": "URL or null if not available",
      "date": "year or null"
    }}
  ]
}}

Rules:
- summary: 1 lead sentence + 4-6 '- ' bullets, concrete and specific — name institutions and incidents where found
- materiality_signal: exactly one sentence that connects the external landscape to THIS audit
- sources: list 2-6 sources actually referenced; never invent URLs
{nothing_found_rule}
{search_instruction}
"""


async def run_lens_society_agent(
    run_id: str,
    engagement_id: str,
    use_web_search: bool = True,
    manual_keyword: str | None = None,
    extra_context: str | None = None,
):
    """Lens 3 agent: Society, Trends & Incidents.

    Stage 1: Synthesise via Claude (with built-in web search when enabled)
    """
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        run.status = "running"
        run.search_progress = json.dumps({"stage": "starting"})
        await db.commit()

    try:
        # ── Synthesise ──────────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.search_progress = json.dumps({
                    "stage": "searching" if use_web_search else "synthesising"
                })
                await db.commit()

        synthesis_prompt = _build_lens3_prompt(
            eng_name=eng.name,
            entity=eng.entity,
            audit_type=eng.audit_type,
            manual_keyword=manual_keyword,
            use_web_search=use_web_search,
            jurisdictions=jurisdictions_or_default(eng),
            extra_context=extra_context,
        )

        # Starts as "did not search", so a run with live search off reads as
        # that rather than as an empty report that could mean anything.
        report = no_search_report()
        result = await synthesise(LENS3_SYSTEM, synthesis_prompt, SocietyLensSynthesis,
                                  use_web_search, report, run_id=run_id)

        # ── Save results ────────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.raw_output = json.dumps(result)
            run.status = "complete"
            run.input_summary = (
                f"Lens 3 — Society, Trends & Incidents for {eng.name} ({eng.entity})"
                + (f" — keyword: {manual_keyword}" if manual_keyword else "")
            )
            run.search_progress = json.dumps({"stage": "complete", **report})
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        # The message said "check server logs" while nothing was logged. Now it
        # is, and a refusal or a truncation is stored in words instead of being
        # folded into the same generic sentence as a crash.
        logging.getLogger("ia.wingman").exception("Lens run %s failed", run_id)
        reason = failure_message(exc)
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.status = "failed"
            run.raw_output = json.dumps({"error": reason})
            run.search_progress = json.dumps({"stage": "failed", "error": reason})
            await db.commit()
