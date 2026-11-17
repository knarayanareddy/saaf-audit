"""Regulatory Intelligence agent — E3.

Two-stage architecture:
  Stage 1: Claude generates targeted search queries (query_generator.py)
  Stage 2: Parallel web search (web_search_service.py)
  Stage 3: Claude synthesises with chain-of-thought reasoning

The synthesis prompt instructs Claude to reason through 4 explicit steps
before producing output — this improves provision-level specificity and
source attribution significantly over a one-shot prompt.
"""
import json
import asyncio

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.engagement import Engagement
from models.planning import TopicIntelligence
from services.ai_service import run_agent_to_json
from services.document_service import fetch_url_text
from services.query_generator import generate_search_queries, ENTITY_DOMAINS
from services.web_search_service import search_regulatory, format_results_for_prompt
from services.prompt_safety import wrap_untrusted, safe_label
from sqlalchemy import select


# ── System prompt — regulatory synthesis ──────────────────────────────────────

REGULATORY_SYSTEM = """You are a senior regulatory analyst for the organisation's Internal Audit function.
Your output goes directly into the auditor's planning file and will be reviewed by the Head of IA.
It must be precise, provision-level specific, and source-attributed.

ORGANISATION CONTEXT:
- TB NL: Dutch banking licence — primary supervisor DNB, EU regulation via ECB SSM
- TB UK: UK banking licence — primary supervisors PRA (prudential) and FCA (conduct)
- TB BE: Belgian banking licence — primary supervisor NBB, conduct FSMA, ECB SSM
- TB ES: Spanish banking licence — primary supervisor Banco de España, ECB SSM
- AM: Investment manager — primary supervisor AFM, ESMA framework

CITATION RULES (non-negotiable):
- Always cite EXACT article numbers: "Art. 3(1) WWFT" not "WWFT"
- Distinguish: what the law SAYS vs. what the SUPERVISOR EXPECTS as evidence
- Mark source for every significant claim: BUILT-IN | SEARCH-RESULT | USER-URL
- Flag if a source is post-January 2026 (your training cutoff)

CONFIDENCE CALIBRATION:
- HIGH: directly applicable, no ambiguity, well-established
- MEDIUM: likely applicable, jurisdiction or scope question remains
- LOW: worth flagging, auditor should confirm before including in scope"""


# ── Chain-of-thought synthesis prompt ─────────────────────────────────────────

def _build_synthesis_prompt(
    eng_name: str,
    entity: str,
    audit_type: str,
    url_context: str,
    search_context: str,
    manual_keyword: str | None,
) -> str:
    entity_info = ENTITY_DOMAINS.get(entity, ENTITY_DOMAINS["GRP"])
    keyword_note = (
        f"\nAUDITOR FOCUS KEYWORD: '{manual_keyword}' — give this topic extra attention.\n"
        if manual_keyword else ""
    )

    return f"""You are producing a Regulatory Intelligence memo for this internal audit.

ENGAGEMENT: {eng_name}
ENTITY: {entity} ({entity_info["primary_regulator"]})
AUDIT TYPE: {audit_type}
{keyword_note}
SOURCES AVAILABLE TO YOU:
A. Built-in regulatory knowledge (training to January 2026)
B. Live web search results (grouped by research angle below)
C. User-provided URLs/documents (if any)

{f"USER-PROVIDED CONTENT:{chr(10)}{url_context}" if url_context else ""}

WEB SEARCH RESULTS:
{search_context}

━━━ REASONING CHAIN ━━━
Before writing the JSON output, reason through these four steps.
Write your reasoning as comments in the JSON (use a "reasoning" key that will be stripped).
Do NOT skip steps — the quality of the output depends on explicit reasoning.

STEP 1 — SCOPE (what is actually being audited):
  - What specific processes, controls, or obligations does this audit cover?
  - What is explicitly OUT of scope (even if related)?
  - Which regulatory regimes unambiguously apply (HIGH)?
  - Which require a scope decision (MEDIUM)?

STEP 2 — PROVISION EXTRACTION (what the law actually says):
  - For each HIGH/MEDIUM framework: cite the EXACT articles that create obligations
  - For each article: state the obligation in one sentence + what evidence proves compliance
  - Do NOT paraphrase law names — use exact titles (WWFT, Ley 10/2010, MLR 2017...)

STEP 3 — SUPERVISORY POSTURE (how the regulator is applying the law today):
  - Based on search results: what themes is {entity_info["primary_regulator"]} currently emphasising?
  - Any recent thematic reviews, Dear CEO letters, enforcement actions found in search?
  - Any upcoming regulatory changes that affect this audit period?

STEP 4 — KNOWLEDGE GAPS:
  - What important post-January-2026 developments might have occurred?
  - What should the auditor verify directly with the regulator's website?

━━━ OUTPUT FORMAT ━━━
Produce ONLY this JSON (no markdown, no explanation before or after):

{{
  "regulatory_summary": "3-4 sentences: what this topic is, why it matters for {entity}, and the primary regulatory framework. Plain language.",

  "applicable_frameworks": [
    {{
      "framework_code": "WWFT",
      "framework_name": "Wet ter voorkoming van witwassen en financieren van terrorisme (2024 consolidated)",
      "jurisdiction": "NL",
      "is_primary": true,
      "confidence": "high",
      "key_provisions": [
        {{
          "article": "Art. 3(1)",
          "obligation": "Identification and verification of client identity before establishing a business relationship",
          "supervisor_expects": "Client file with verified ID document, UBO register extract, risk classification documented"
        }}
      ],
      "applicability_rationale": "Why this framework applies to this specific audit",
      "source": "built_in_knowledge",
      "source_url": "https://wetten.overheid.nl/BWBR0024282/2024-01-01"
    }}
  ],

  "supervisory_focus": {{
    "current_themes": ["Theme 1 in 1 line", "Theme 2"],
    "recent_actions": "1-2 sentences on specific recent supervisory actions found (or null if none found)",
    "upcoming_changes": "1-2 sentences on upcoming regulatory changes affecting this audit period (or null)",
    "source": "search_result or built_in_knowledge",
    "source_urls": ["url1", "url2"]
  }},

  "recent_developments": [
    {{
      "title": "Name of the regulatory development",
      "description": "1-2 sentences on what it is and what changes",
      "effective_date": "2025 or 'expected 2026' or null",
      "impact_on_audit": "How this affects scope or approach for this engagement",
      "source": "search_result",
      "source_url": "https://..."
    }}
  ],

  "knowledge_gaps": [
    "Specific thing to verify — e.g. 'Check DNB website for updated CDD guidance published after January 2026'"
  ],

  "sources_used": [
    {{
      "type": "built_in_knowledge",
      "description": "Regulatory training data to January 2026",
      "used_for": "applicable_frameworks"
    }},
    {{
      "type": "web_search",
      "url": "https://dnb.nl/...",
      "title": "Page title",
      "angle": "supervisory",
      "used_for": "supervisory_focus"
    }}
  ]
}}

Rules:
- applicable_frameworks: list 3-6, ordered by is_primary then confidence
- key_provisions: list 2-4 per framework — the ones most relevant to THIS audit
- supervisory_focus.source: use "search_result" only if search results actually contained relevant content
- recent_developments: include only if genuinely relevant (0-4 items), not exhaustive
- sources_used: include one entry per search result URL that actually contributed to the output
- Never invent URLs — use null if you don't have a real URL
- If no web search results were returned, set all source fields to "built_in_knowledge"
"""


# ── Main agent function ────────────────────────────────────────────────────────

async def run_regulatory_agent(
    run_id: str,
    engagement_id: str,
    urls: list[str] | None = None,
    use_web_search: bool = True,
    custom_queries: list[str] | None = None,
    manual_keyword: str | None = None,
):
    """Regulatory Intelligence agent — two-stage execution.

    Stage 1: Generate targeted search queries (if web search enabled)
    Stage 2: Run parallel web search
    Stage 3: Synthesise with chain-of-thought
    """
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        eng = await db.get(Engagement, engagement_id)
        run.status = "running"
        # Initialise search progress tracker
        run.search_progress = json.dumps({
            "stage": "starting",
            "queries": [],
            "results_found": 0,
        })
        await db.commit()

    try:
        # ── Stage 1: Fetch user-provided URLs ────────────────────────────────
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

        # ── Stage 2: Generate search queries ─────────────────────────────────
        structured_queries = []
        if use_web_search:
            # Update progress: generating queries
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.search_progress = json.dumps({
                        "stage": "generating_queries",
                        "queries": [],
                        "results_found": 0,
                    })
                    await db.commit()

            try:
                structured_queries = await generate_search_queries(
                    engagement_name=eng.name,
                    entity=eng.entity,
                    audit_type=eng.audit_type,
                    manual_keyword=manual_keyword,
                    target_count=7 if manual_keyword else 5,
                )
            except Exception:  # noqa: BLE001
                # If Claude query generation fails (e.g. 401, rate limit), use
                # hardcoded fallback queries so the web search can still run
                from services.query_generator import ENTITY_DOMAINS, _fallback_queries
                entity_info = ENTITY_DOMAINS.get(eng.entity, ENTITY_DOMAINS["GRP"])
                structured_queries = _fallback_queries(eng.name, eng.entity, entity_info, manual_keyword)

            # Also fold in any legacy custom_queries as keyword-angle entries
            if custom_queries:
                for q in custom_queries[:2]:
                    structured_queries.append({
                        "query_text": q[:200],
                        "angle": "keyword",
                        "primary_domain": "",
                        "description": f"Auditor-defined query: {q[:100]}",
                    })

            # Update progress: queries ready, about to search
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.search_progress = json.dumps({
                        "stage": "searching",
                        "queries": [
                            {"text": q["query_text"], "angle": q["angle"],
                             "domain": q["primary_domain"], "status": "queued", "results": 0}
                            for q in structured_queries
                        ],
                        "results_found": 0,
                    })
                    await db.commit()

        # ── Stage 3: Run parallel web search ─────────────────────────────────
        search_results = []
        if use_web_search and structured_queries:
            # Progress callback — updates AgentRun.search_progress as each query completes
            completed_queries: list[dict] = []

            async def on_query_done(query_text: str, angle: str, result_count: int):
                completed_queries.append({
                    "text": query_text, "angle": angle,
                    "status": "complete", "results": result_count,
                })
                try:
                    async with AsyncSessionLocal() as db:
                        run_row = await db.get(AgentRun, run_id)
                        if run_row:
                            pending = [
                                {"text": q["query_text"], "angle": q["angle"],
                                 "domain": q["primary_domain"], "status": "queued", "results": 0}
                                for q in structured_queries
                                if not any(c["text"] == q["query_text"] for c in completed_queries)
                            ]
                            run_row.search_progress = json.dumps({
                                "stage": "searching",
                                "queries": completed_queries + pending,
                                "results_found": sum(c["results"] for c in completed_queries),
                            })
                            await db.commit()
                except Exception:  # noqa: BLE001
                    pass

            search_results = await search_regulatory(
                engagement_name=eng.name,
                entity=eng.entity,
                structured_queries=structured_queries,
                on_query_complete=on_query_done,
            )

        # Update progress: search complete, synthesising
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.search_progress = json.dumps({
                    "stage": "synthesising",
                    "queries": [
                        {"text": q["query_text"], "angle": q["angle"],
                         "domain": q["primary_domain"], "status": "complete", "results": 0}
                        for q in structured_queries
                    ],
                    "results_found": len(search_results),
                })
                await db.commit()

        # ── Stage 4: Synthesise with chain-of-thought ─────────────────────────
        search_context = format_results_for_prompt(search_results)

        synthesis_prompt = _build_synthesis_prompt(
            eng_name=eng.name,
            entity=eng.entity,
            audit_type=eng.audit_type,
            url_context=url_context,
            search_context=search_context,
            manual_keyword=manual_keyword,
        )

        result = await run_agent_to_json(REGULATORY_SYSTEM, synthesis_prompt, max_tokens=5000)

        # ── Save results ──────────────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.raw_output = json.dumps(result)
            run.status = "complete"
            run.input_summary = (
                f"Regulatory intelligence for {eng.name} ({eng.entity})"
                + (f" — keyword: {manual_keyword}" if manual_keyword else "")
            )
            run.search_progress = json.dumps({
                "stage": "complete",
                "queries": [
                    {"text": q["query_text"], "angle": q["angle"],
                     "domain": q["primary_domain"], "status": "complete", "results": 0}
                    for q in structured_queries
                ],
                "results_found": len(search_results),
            })

            # Save search results + query plan to TI row for Sources panel
            ti_res = await db.execute(
                select(TopicIntelligence).where(TopicIntelligence.engagement_id == engagement_id)
            )
            ti_row = ti_res.scalar_one_or_none()
            if ti_row:
                if search_results:
                    ti_row.search_results = json.dumps(search_results)
                # Save the query plan so the frontend can show what was searched
                ti_row.search_queries = json.dumps(structured_queries) if structured_queries else None

            await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.status = "failed"
            run.raw_output = json.dumps({"error": "Agent run failed. Check server logs."})
            # Preserve whatever query list was built — don't reset to [] on synthesis failure.
            # The queries are useful to show the user what was attempted even when synthesis fails.
            existing_progress: dict = {}
            if run.search_progress:
                try:
                    existing_progress = json.loads(run.search_progress)
                except Exception:  # noqa: BLE001
                    pass
            run.search_progress = json.dumps({
                "stage": "failed",
                "queries": existing_progress.get("queries", []),
                "results_found": existing_progress.get("results_found", 0),
                "error": "Processing failed",
            })
            await db.commit()
