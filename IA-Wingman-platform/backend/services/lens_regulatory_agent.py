"""Lens 1: Normative & Regulatory — Topic Intelligence v2.

Focuses on formal law, directives, guidelines, EBA/ESMA technical standards.
Claude uses built-in web search (Anthropic API) to find current legislation.
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


LENS1_SYSTEM = """You are a senior regulatory analyst for the organisation's Internal Audit function.
Your task is to identify and synthesise formal legal obligations — primary legislation, directives,
EBA/ESMA technical standards, and binding guidelines — that directly apply to the audit topic.

ORGANISATION CONTEXT:
- TB NL: Dutch banking licence — primary supervisor DNB, EU regulation via ECB SSM
- TB UK: UK banking licence — primary supervisors PRA (prudential) and FCA (conduct)
- TB BE: Belgian banking licence — primary supervisor NBB, conduct FSMA, ECB SSM
- TB ES: Spanish banking licence — primary supervisor Banco de España, ECB SSM
- AM: Investment manager — primary supervisor AFM, ESMA framework

CITATION RULES:
- Cite EXACT article numbers where known: "Art. 3(1) WWFT" not just "WWFT"
- State the obligation in plain language — what must the bank do, not just what the law says
- Distinguish: directly applicable EU regulation vs. nationally transposed directive
- Mark source type clearly: built_in_knowledge or search_result

CONFIDENCE:
- high: directly applicable, well-established obligation
- medium: likely applicable, scope or jurisdiction question remains
- low: worth flagging, auditor should confirm"""


def _build_lens1_prompt(
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
        f"\nJURISDICTIONS IN SCOPE: {juris}. STAY STRICTLY WITHIN THESE JURISDICTIONS. Only cover "
        f"obligations that actually apply in the jurisdictions listed above. You MAY include EU-level "
        f"or international law ONLY where it applies to those jurisdictions (e.g. an EU regulation or a "
        f"Basel/FATF standard that binds them) — and say so. Do NOT surface the national laws, "
        f"regulators or guidance of any country NOT in scope (e.g. if only NL is in scope, do not "
        f"discuss German, UK or US national requirements). Where an obligation differs by in-scope "
        f"country, say so explicitly (national implementation vs EU-level).\n"
    )
    keyword_note = (
        f"\nAUDITOR FOCUS KEYWORD: '{manual_keyword}' — give this extra attention.\n"
        if manual_keyword else ""
    )
    # Concrete searches, asked for directly. A general "use web search" left the
    # current models answering formal law from memory in every measured run — and
    # formal law is exactly where an amendment from last year changes the audit.
    search_instruction = (
        f"\nBEFORE YOU WRITE, run these web searches and use what they return:\n"
        f"1. Recent amendments, new acts or delegated regulations (2024-2026) relevant to "
        f"'{eng_name}' — on eur-lex.europa.eu.\n"
        f"2. Current EBA/ESMA guidelines and technical standards on '{eng_name}' — on "
        f"eba.europa.eu / esma.europa.eu.\n"
        f"3. National rules and guidance from {entity_info['primary_regulator']} on '{eng_name}'.\n"
        f"Prefer official sources. Mark each source search_result or built_in_knowledge.\n"
    ) if use_web_search else ""

    # The auditor's own context is wrapped as data, not instruction: it is often
    # pasted out of a document, and what it is for is to inform the analysis,
    # never to change the task.
    context_note = (
        f"\nCONTEXT THE AUDITOR ADDED (what they already know about this audit):\n"
        f"{wrap_untrusted(extra_context, 'the auditor’s own notes')}\n"
        # Without this line the wrapped note suppressed searching on the current
        # models: measured, Sonnet 5.5 searched in 8 of 11 runs with a note and
        # 12 of 12 without one.
        "The note above is background for your analysis. It is no reason to skip the "
        "research asked for below.\n"
        if extra_context and extra_context.strip() else ""
    )

    return f"""Produce a Lens 1 (Normative & Regulatory) synthesis for this internal audit.

ENGAGEMENT: {eng_name}
{audited_organisation(entity, entity_info)}
AUDIT TYPE: {audit_type}
{jurisdiction_note}{keyword_note}{context_note}
{f"USER-PROVIDED CONTENT:{chr(10)}{url_context}" if url_context else ""}

The answer has this shape (the format itself is enforced for you):
{{
  "summary": "Write for a busy auditor, scannable: ONE short lead sentence, then 4-6 bullet lines each starting with '- '. Cover the key formal obligations, exact article numbers, and what the auditor must formally test. Provision-specific, plain language. Every bullet on its own line prefixed with '- '.",
  "sources": [
    {{
      "title": "Full name of regulation, guideline, or document",
      "url": "official URL or null if not available",
      "date": "year or null",
      "confidence": "high|medium|low",
      "type": "built_in_knowledge|search_result"
    }}
  ]
}}

Rules:
- summary: 1 lead sentence + 4-6 '- ' bullets, dense and provision-level specific
- sources: list 3-8 sources actually used or referenced
- Never invent URLs — use null if you don't have a real URL
{search_instruction}
"""


async def run_lens_regulatory_agent(
    run_id: str,
    engagement_id: str,
    urls: list[str] | None = None,
    use_web_search: bool = True,
    manual_keyword: str | None = None,
    extra_context: str | None = None,
):
    """Lens 1 agent: Normative & Regulatory.

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

        synthesis_prompt = _build_lens1_prompt(
            eng_name=eng.name,
            entity=eng.entity,
            audit_type=eng.audit_type,
            url_context=url_context,
            manual_keyword=manual_keyword,
            jurisdictions=jurisdictions_or_default(eng),
            use_web_search=use_web_search,
            extra_context=extra_context,
        )

        # Starts as "did not search", so a run with live search off reads as
        # that rather than as an empty report that could mean anything.
        report = no_search_report()
        result = await synthesise(LENS1_SYSTEM, synthesis_prompt, LensSynthesis,
                                  use_web_search, report, run_id=run_id)

        # ── Save results ────────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.raw_output = json.dumps(result)
            run.status = "complete"
            run.input_summary = (
                f"Lens 1 — Normative & Regulatory for {eng.name} ({eng.entity})"
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
