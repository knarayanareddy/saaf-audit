"""Supervisory Guidance Agent.

Sibling of the Framework Requirements ("Laws & Regulations") agent, but where that
one identifies binding LAWS with article references, this one searches the relevant
supervisory authorities' own publications for applicable *soft law*: policy rules
(beleidsregels), guidelines/guidance (richtlijnen/leidraden), good-practice papers,
thematic reviews, Q&As and "Dear CEO" letters that shape supervisory expectations
without being statute.

It reuses the same `ApplicableFramework` table, tagging rows with category='guidance'
and source='guidance_analysed' so they live alongside — but never collide with — the
category='law' rows written by the Laws & Regulations agent. Both categories flow
downstream (scope, work program) unchanged.

Design notes:
- Web search is fail-safe: without a TAVILY_API_KEY it returns [] and the agent falls
  back to Claude's built-in knowledge. Search failure never blocks a run.
- The synthesis prompt is deliberately steered AWAY from statute — laws belong to the
  other module — and towards named supervisory publications with issuer + type.
- Deletes only its own (category='guidance', source='guidance_analysed') rows before
  re-inserting, so re-running never touches laws or manually added guidance.
"""
import json
import logging

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from services.framework_rows import GUIDANCE, replace_rows
from models.engagement import Engagement, jurisdictions_or_default
from models.planning import ApplicableFramework
from services.agent_contract import run_agent
from services.agent_schemas import SupervisoryGuidance
from services.web_search_service import search_regulatory, format_results_for_prompt

logger = logging.getLogger("ia_wingman.supervisory_guidance")

GUIDANCE_SOURCE = "guidance_analysed"

# Per-jurisdiction supervisory authorities and their publication domains. Guidance is a
# per-country concept (which regulator issues it), unlike the entity-keyed ENTITY_DOMAINS
# used for the legislation search.
JURISDICTION_SUPERVISORS = {
    "NL": {"authorities": "DNB and AFM", "domains": ["dnb.nl", "afm.nl"]},
    "BE": {"authorities": "NBB and FSMA", "domains": ["nbb.be", "fsma.be"]},
    "UK": {"authorities": "FCA and PRA", "domains": ["fca.org.uk", "bankofengland.co.uk"]},
    "ES": {"authorities": "Banco de España and CNMV", "domains": ["bde.es", "cnmv.es"]},
    "EU": {"authorities": "EBA, ECB, ESMA and EIOPA", "domains": ["eba.europa.eu", "ecb.europa.eu", "esma.europa.eu"]},
}

GUIDANCE_SYSTEM = (
    "You are an expert internal audit regulatory analyst for the organisation's Internal Audit function. "
    "You specialise in SUPERVISORY GUIDANCE — the soft law published by financial supervisors: "
    "policy rules (beleidsregels), guidelines and guidance (richtlijnen/leidraden), good-practice papers, "
    "thematic reviews, Q&As and supervisory letters. "
    "You never confuse guidance with statute: you cite the issuing authority and the exact publication, "
    "not article numbers of primary law."
)


def _build_guidance_queries(engagement_name: str, jurisdictions: list[str]) -> list[dict]:
    """Two supervisory-guidance queries per in-scope jurisdiction, anchored to that
    jurisdiction's regulator domains. Capped at 7 (the search service's own cap)."""
    queries: list[dict] = []
    for juris in jurisdictions:
        info = JURISDICTION_SUPERVISORS.get(juris)
        if not info:
            continue
        domain = info["domains"][0]
        queries.append({
            "query_text": f"{engagement_name} supervisory guidance guidelines good practices {info['authorities']} 2024 2025",
            "angle": "guidance",
            "primary_domain": domain,
            "description": f"{juris} supervisory guidance",
        })
        queries.append({
            "query_text": f"{engagement_name} thematic review expectations supervisory letter {info['authorities']}",
            "angle": "supervisory",
            "primary_domain": domain,
            "description": f"{juris} supervisory expectations",
        })
    return queries[:7]


async def _fail(agent_run_id: str, message: str) -> None:
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, agent_run_id)
        if run:
            run.status = "failed"
            run.raw_output = message[:2000]
        await db.commit()


async def run_supervisory_guidance_analysis(agent_run_id: str, engagement_id: str) -> None:
    """Background task: search supervisory authorities' publications for applicable guidance."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, agent_run_id)
        if not run:
            return
        run.status = "running"
        run.search_progress = json.dumps({"stage": "searching_supervisors"})
        await db.commit()

    async with AsyncSessionLocal() as db:
        eng = await db.get(Engagement, engagement_id)
        if not eng:
            await _fail(agent_run_id, "Engagement not found")
            return
        eng_name, eng_entity, eng_type = eng.name, eng.entity, eng.audit_type
        eng_jurisdictions = jurisdictions_or_default(eng)

    try:
        # ── Web search over supervisory authority sites (fail-safe) ──────────
        queries = _build_guidance_queries(eng_name, eng_jurisdictions)
        search_results = await search_regulatory(eng_name, eng_entity, structured_queries=queries)
        search_ctx = format_results_for_prompt(search_results)

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, agent_run_id)
            if run:
                run.search_progress = json.dumps({"stage": "synthesising_guidance"})
                await db.commit()

        guidance_prompt = f"""Identify the applicable SUPERVISORY GUIDANCE for this internal audit engagement.

Audit name: {eng_name}
Audit type: {eng_type}
Jurisdictions in scope: {", ".join(eng_jurisdictions)}

Focus ONLY on supervisory soft law — NOT statute. That means, per jurisdiction, the publications of its
supervisory authorities:
- NL: DNB (beleidsregels, Q&A, good practices), AFM (leidraden)
- BE: NBB circulaires, FSMA guidance
- UK: FCA/PRA guidance, "Dear CEO" letters, thematic reviews
- ES: Banco de España / CNMV guías y circulares
- EU: EBA guidelines, ECB guides & supervisory expectations, ESMA/EIOPA guidelines

Do NOT return primary legislation (that is handled by a separate "Laws & Regulations" module).
Return named guidance documents only.

{search_ctx}

Return the guidance in the JSON format this request requires. Its schema carries each
field's meaning, so what follows is only the judgement it cannot express.

Rules:
- Prefer specific, named publications with a reference/number over generic themes
- If live search results are provided above, ground your answer in them and reuse their URLs
"""

        # Fenced on 2 of 3 measured runs, none of which failed. Same reason for
        # moving as the frameworks agent beside it: the strip was doing the work
        # and nothing said so.
        result = await run_agent(GUIDANCE_SYSTEM, guidance_prompt, SupervisoryGuidance,
                                 max_tokens=3000,
                                 description="Return the supervisory guidance.")
        gd_result = [item.model_dump() for item in result.data.guidance]

        async with AsyncSessionLocal() as db:
            # Replace only our own auto-analysed guidance rows — never touch laws or
            # manually added guidance.
            saved = await replace_rows(db, engagement_id, GUIDANCE, gd_result)
            await db.commit()

    except Exception as exc:  # noqa: BLE001
        await _fail(agent_run_id, f"Supervisory guidance search failed: {exc}")
        return

    try:
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, agent_run_id)
            if run:
                run.status = "complete"
                run.search_progress = json.dumps({"stage": "complete", "count": saved})
            await db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to mark supervisory_guidance run %s complete", agent_run_id)
