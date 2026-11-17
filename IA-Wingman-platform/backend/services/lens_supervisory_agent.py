"""Lens 2: Supervisory & Enforcement — Topic Intelligence v2.

Focuses on what the primary supervisor is currently emphasising:
thematic reviews, Dear CEO letters, enforcement actions, SREP public outputs.
Claude uses built-in web search (Anthropic API) to find current supervisory material.
Output: 150-200 word synthesis with cited sources.
"""
import json
import logging

from database import AsyncSessionLocal
from services.agent_contract import failure_message
from models.agent_run import AgentRun
from models.engagement import Engagement, jurisdictions_or_default
from services.agent_schemas import LensSynthesis
from services.lens_call import audited_organisation, no_search_report, synthesise
from services.document_service import fetch_url_text
from services.prompt_safety import wrap_untrusted, safe_label
from services.query_generator import ENTITY_DOMAINS


LENS2_SYSTEM = """You are a senior regulatory analyst for the organisation's Internal Audit function.
Your task is to identify what the primary supervisor is currently emphasising for the audit topic:
thematic reviews, Dear CEO letters, SREP outputs, enforcement actions, and publicly stated priorities.

ORGANISATION CONTEXT:
- TB NL: Primary supervisor DNB (prudential) — SSM via ECB
- TB UK: Primary supervisors PRA (prudential) and FCA (conduct)
- TB BE: Primary supervisor NBB (prudential), FSMA (conduct) — SSM via ECB
- TB ES: Primary supervisor Banco de España, SEPBLAC (AML) — SSM via ECB
- AM: Primary supervisor AFM, ESMA framework

WHAT TO LOOK FOR:
- Thematic reviews the supervisor has conducted or announced on this topic
- Dear CEO / Dear CFO letters or supervisory communications
- Public enforcement actions (fines, formal orders, public statements)
- SREP findings or public statements on this risk area
- Upcoming supervisory focus areas or planned inspections

CITATION RULES:
- Name the specific document where possible (e.g. "DNB Thematic Review on CDD, June 2025")
- Note the year and source type clearly
- If only built-in knowledge is available, state that explicitly"""


def _build_lens2_prompt(
    eng_name: str,
    entity: str,
    audit_type: str,
    url_context: str,
    manual_keyword: str | None,
    use_web_search: bool,
    jurisdictions: list[str] | None = None,
    extra_context: str | None = None,
) -> str:
    entity_info = ENTITY_DOMAINS.get(entity, ENTITY_DOMAINS["GRP"])
    juris = ", ".join(jurisdictions) if jurisdictions else "NL, EU"
    jurisdiction_note = (
        f"\nJURISDICTIONS IN SCOPE: {juris}. STAY STRICTLY WITHIN THESE JURISDICTIONS — cover ONLY the "
        f"supervisors of the jurisdictions listed (e.g. DNB/AFM for NL, NBB/FSMA for BE, FCA/PRA for UK, "
        f"CNMV/Banco de España for ES) plus the EU supervisors (EBA/ESMA/ECB) where they apply to those "
        f"jurisdictions. Do NOT bring in supervisors or thematic priorities of any country NOT in scope "
        f"(e.g. if only NL is in scope, do not discuss BaFin, the SEC or other foreign supervisors). "
        f"Note where priorities differ across the in-scope jurisdictions.\n"
    )
    keyword_note = (
        f"\nAUDITOR FOCUS KEYWORD: '{manual_keyword}' — give this extra attention.\n"
        if manual_keyword else ""
    )
    # Concrete searches, asked for directly — see lens 1 for why.
    search_instruction = (
        f"\nBEFORE YOU WRITE, run these web searches and use what they return:\n"
        f"1. {entity_info['primary_regulator']} supervisory priorities and thematic reviews "
        f"(2024-2026) touching '{eng_name}'.\n"
        f"2. Recent enforcement actions, fines or Dear CEO letters on '{eng_name}' from "
        f"{entity_info['primary_regulator']} and the EU supervisors (ECB/EBA/ESMA).\n"
        f"3. Recent press releases from {entity_info['primary_regulator']} on this topic.\n"
    ) if use_web_search else ""

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

    return f"""Produce a Lens 2 (Supervisory & Enforcement) synthesis for this internal audit.

ENGAGEMENT: {eng_name}
{audited_organisation(entity, entity_info)}
AUDIT TYPE: {audit_type}
{jurisdiction_note}{keyword_note}{context_note}
{f"USER-PROVIDED CONTENT:{chr(10)}{url_context}" if url_context else ""}

The answer has this shape (the format itself is enforced for you):
{{
  "summary": "Write for a busy auditor, scannable: ONE short lead sentence, then 4-6 bullet lines each starting with '- '. Cover what the supervisor is emphasising now, specific enforcement actions or thematic reviews found, and what this means for the audit scope (what the supervisor is likely to scrutinise). Every bullet on its own line prefixed with '- '.",
  "sources": [
    {{
      "title": "Name of supervisory document, enforcement action, or communication",
      "url": "official URL or null if not available",
      "date": "year or null"
    }}
  ]
}}

Rules:
- summary: 1 lead sentence + 4-6 '- ' bullets, focus on CURRENT supervisor priorities (2024-2026)
- sources: list 2-6 specific supervisory documents or actions found
- Never invent URLs — use null if you don't have a real URL
- If no current information found, state what the supervisor generally focuses on
  for this entity type based on built-in knowledge
{search_instruction}
"""


async def run_lens_supervisory_agent(
    run_id: str,
    engagement_id: str,
    urls: list[str] | None = None,
    use_web_search: bool = True,
    manual_keyword: str | None = None,
    extra_context: str | None = None,
):
    """Lens 2 agent: Supervisory & Enforcement.

    Stage 1: Fetch user-provided URLs
    Stage 2: Synthesise via Claude (with built-in web search when enabled)
    """
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        run.status = "running"
        run.search_progress = json.dumps({"stage": "starting"})
        await db.commit()

    try:
        # ── Stage 1: Fetch user-provided URLs ──────────────────────────────
        url_context = ""
        if urls:
            fetched = []
            for url in urls:
                try:
                    text = await fetch_url_text(url)
                    fetched.append(f"--- Content from {safe_label(url)} ---\n{text[:8000]}")
                except Exception as exc:  # noqa: BLE001
                    fetched.append(f"--- Could not fetch {safe_label(url)}: {exc} ---")
            url_context = wrap_untrusted("\n\n".join(fetched), "user-provided URLs")

        # ── Stage 2: Synthesise ─────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.search_progress = json.dumps({
                    "stage": "searching" if use_web_search else "synthesising"
                })
                await db.commit()

        synthesis_prompt = _build_lens2_prompt(
            eng_name=eng.name,
            entity=eng.entity,
            audit_type=eng.audit_type,
            url_context=url_context,
            manual_keyword=manual_keyword,
            use_web_search=use_web_search,
            jurisdictions=jurisdictions_or_default(eng),
            extra_context=extra_context,
        )

        # Starts as "did not search", so a run with live search off reads as
        # that rather than as an empty report that could mean anything.
        report = no_search_report()
        result = await synthesise(LENS2_SYSTEM, synthesis_prompt, LensSynthesis,
                                  use_web_search, report, run_id=run_id)

        # ── Save results ────────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.raw_output = json.dumps(result)
            run.status = "complete"
            run.input_summary = (
                f"Lens 2 — Supervisory & Enforcement for {eng.name} ({eng.entity})"
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
