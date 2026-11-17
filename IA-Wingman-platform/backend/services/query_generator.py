"""Regulatory query generator — E1.

Asks Claude to produce a targeted set of 5-7 search queries from the audit
topic. Each query covers a different research angle so that the parallel
Tavily search returns a comprehensive picture rather than five variations
of the same question.

This is a fast, small call (~100 tokens in, ~300 out) that runs before the
main web search. It costs almost nothing but dramatically improves search
quality by letting Claude reason about WHAT to look for before looking.
"""
import logging

from services.agent_contract import AgentContractError, AgentTruncated, run_agent
from services.agent_schemas import SearchQueries

logger = logging.getLogger("ia.wingman")

# Per-entity domain hints fed into query generation so Claude knows which
# authoritative sources to anchor queries on.
ENTITY_DOMAINS = {
    "GRP": {
        "primary_regulator": "DNB (De Nederlandsche Bank)",
        "secondary": "EBA, ECB",
        "law_source": "wetten.overheid.nl / EUR-Lex",
        "domains": ["dnb.nl", "eba.europa.eu", "eur-lex.europa.eu", "wetten.overheid.nl", "fatf-gafi.org"],
    },
    "INT": {
        "primary_regulator": "FCA (Financial Conduct Authority) and PRA (Prudential Regulation Authority)",
        "secondary": "Bank of England",
        "law_source": "legislation.gov.uk",
        "domains": ["fca.org.uk", "pra.org.uk", "bankofengland.co.uk", "legislation.gov.uk", "hmtreasury.gov.uk"],
    },
    "RET": {
        "primary_regulator": "NBB (National Bank of Belgium) and FSMA",
        "secondary": "EBA, ECB",
        "law_source": "ejustice.just.fgov.be / EUR-Lex",
        "domains": ["nbb.be", "fsma.be", "eba.europa.eu", "eur-lex.europa.eu", "ecb.europa.eu"],
    },
    "BUS": {
        "primary_regulator": "Banco de España and SEPBLAC",
        "secondary": "EBA, ECB",
        "law_source": "boe.es / EUR-Lex",
        "domains": ["bde.es", "sepblac.es", "eba.europa.eu", "eur-lex.europa.eu", "boe.es"],
    },
    "AM": {
        "primary_regulator": "ESMA (European Securities and Markets Authority) and AFM",
        "secondary": "EBA, ECB",
        "law_source": "EUR-Lex",
        "domains": ["esma.europa.eu", "afm.nl", "eba.europa.eu", "eur-lex.europa.eu", "ecb.europa.eu"],
    },
}

QUERY_GEN_SYSTEM = """You are a regulatory research specialist for the organisation's Internal Audit function.
You design targeted web search queries for regulatory intelligence gathering.
Your queries must be specific, diverse in angle, and anchored to official regulatory sources.
Never produce vague or generic queries — every query must be actionable for a professional researcher."""


async def generate_search_queries(
    engagement_name: str,
    entity: str,
    audit_type: str,
    manual_keyword: str | None = None,
    target_count: int = 5,
) -> list[dict]:
    """Generate 5-7 targeted regulatory search queries for this engagement.

    Returns list of:
      {query_text, angle, primary_domain, description}

    Angles covered:
      legislation    — primary law text and article references
      supervisory    — regulator's current focus and expectations
      developments   — recent changes, consultations, upcoming rules
      enforcement    — enforcement actions, fines, inspection findings
      guidance       — EBA/ECB/ESMA technical standards and guidelines
      (keyword)      — 1-2 extra queries anchored on the manual keyword if provided
    """
    entity_info = ENTITY_DOMAINS.get(entity, ENTITY_DOMAINS["GRP"])
    extra_count = min(2, target_count - 5) + 2 if manual_keyword else 0
    total = min(target_count + extra_count, 7)

    keyword_instruction = ""
    if manual_keyword:
        keyword_instruction = f"""
MANUAL KEYWORD — the auditor specifically asked about: "{manual_keyword}"
Generate at least 2 of your queries centred on this keyword.
These keyword-specific queries get angle = "keyword".
"""

    prompt = f"""Generate {total} targeted search queries for a regulatory intelligence search.

AUDIT CONTEXT:
- Engagement: {engagement_name}
- Entity: {entity} ({entity_info["primary_regulator"]})
- Audit type: {audit_type}
- Primary regulatory sources: {entity_info["law_source"]}
- Available domains: {", ".join(entity_info["domains"])}
{keyword_instruction}
REQUIRED ANGLES (one query per angle, in this order):
1. legislation   — the primary law/regulation text: exact law name + article numbers in scope
2. supervisory   — {entity_info["primary_regulator"]} current focus, thematic reviews, expectations for this topic
3. developments  — regulatory changes, consultations, new rules for this area in 2024-2026
4. enforcement   — enforcement actions, fines, inspection findings, supervisory letters for this topic
5. guidance      — {entity_info["secondary"]} technical standards, guidelines, Q&A for this topic
{f"6. keyword     — specific angle on '{manual_keyword}' (first query)" if manual_keyword else ""}
{f"7. keyword     — specific angle on '{manual_keyword}' (second angle, different from query 6)" if manual_keyword else ""}

RULES for each query:
- Maximum 12 words per query
- Use the EXACT regulatory name where applicable (e.g. "WWFT Art 3" not "Dutch AML law")
- Include the year range "2024 2025" in queries about recent developments
- primary_domain must be one of: {", ".join(entity_info["domains"])}

An example of the first query: "WWFT Art 3 8 CDD identification verification
obligations banks", angle legislation, on wetten.overheid.nl."""

    # Short search strings with a deterministic fallback right below if they come
    # back unusable — the definition of a job for the quick tier.
    #
    # The first call site the ledger ranked, and it earned the place: it returned
    # its array inside a markdown fence on 4 of 4 measured calls, against a prompt
    # that said "no markdown" in those words. Every one of those was recorded as a
    # clean success, because the fence was stripped before anyone could notice.
    # Asking for a bare JSON array is asking for the shape a chat model is most
    # inclined to decorate; a tool call has nowhere to put the decoration.
    try:
        result = await run_agent(QUERY_GEN_SYSTEM, prompt, SearchQueries, max_tokens=800,
                                 description="Return the search queries.")
        items = [q.model_dump() for q in result.data.queries]
    except (AgentContractError, AgentTruncated) as exc:
        # The fallback used to be reached only when the reply parsed into
        # something that was not a list; a reply that did not parse at all raised
        # out of here into whatever had called it. Both now land on the queries
        # this module can write without a model.
        logger.warning("Query generation fell back to fixed queries: %s", exc)
        return _fallback_queries(engagement_name, entity, entity_info, manual_keyword)

    # The domain is the one field the schema cannot pin down: the allowed values
    # differ per entity, so it is checked here against the list the prompt named.
    for item in items:
        if item["primary_domain"] not in entity_info["domains"]:
            item["primary_domain"] = entity_info["domains"][0]

    return items[:7] or _fallback_queries(engagement_name, entity, entity_info, manual_keyword)


def _fallback_queries(
    engagement_name: str,
    entity: str,
    entity_info: dict,
    manual_keyword: str | None,
) -> list[dict]:
    """Hardcoded fallback when Claude query generation fails."""
    reg = entity_info["primary_regulator"].split(" ")[0]
    queries = [
        {
            "query_text": f"{engagement_name} regulatory requirements {entity.replace('_', ' ')}",
            "angle": "legislation",
            "primary_domain": entity_info["domains"][0],
            "description": "Primary legislation applicable to this audit topic",
        },
        {
            "query_text": f"{reg} supervisory focus {engagement_name} 2024 2025",
            "angle": "supervisory",
            "primary_domain": entity_info["domains"][0],
            "description": "Current supervisory expectations",
        },
        {
            "query_text": f"{engagement_name} regulatory developments consultation 2025",
            "angle": "developments",
            "primary_domain": entity_info["domains"][1] if len(entity_info["domains"]) > 1 else entity_info["domains"][0],
            "description": "Recent and upcoming regulatory changes",
        },
        {
            "query_text": f"EBA guidelines {engagement_name} technical standards",
            "angle": "guidance",
            "primary_domain": "eba.europa.eu",
            "description": "EBA technical standards and guidelines",
        },
        {
            "query_text": f"{reg} enforcement findings {engagement_name} banks",
            "angle": "enforcement",
            "primary_domain": entity_info["domains"][0],
            "description": "Enforcement actions and supervisory findings",
        },
    ]
    if manual_keyword:
        queries.append({
            "query_text": f"{manual_keyword} {entity.replace('_', ' ')} requirements 2024 2025",
            "angle": "keyword",
            "primary_domain": entity_info["domains"][0],
            "description": f"Specific research on: {manual_keyword}",
        })
    return queries
