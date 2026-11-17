"""Web search service — E2.

Runs Tavily queries in parallel (asyncio.gather) rather than sequentially.
Each query can target a different primary domain for better precision.
Returns richer result objects that include the angle and domain so the
synthesis prompt can attribute each finding to its source correctly.

Key improvements over the old version:
- All queries run in parallel → 5 queries in ~5s instead of ~15s
- Each result carries angle + domain for source attribution
- Domain filter is per-query, not global, so legislation queries hit law sites
  while supervisory queries hit the regulator's site
- Progress callback lets the caller update a progress tracker in real time
- Up to 20 unique results (was 8) for more comprehensive coverage
"""
import asyncio
import httpx
from config import settings
from services.prompt_safety import wrap_untrusted


async def search_regulatory(
    engagement_name: str,
    entity: str,
    extra_queries: list[str] | None = None,
    structured_queries: list[dict] | None = None,
    on_query_complete: "callable | None" = None,
) -> list[dict]:
    """Run regulatory web searches and return a deduplicated result list.

    Accepts either:
    - structured_queries: [{query_text, angle, primary_domain, description}] (new, preferred)
    - extra_queries: [str] (legacy simple list — converted to structured)

    Returns [] silently if TAVILY_API_KEY is not configured.
    Never raises — search failure must never block an agent run.
    """
    if not settings.TAVILY_API_KEY:
        return []

    # Build the query list
    if structured_queries:
        queries = structured_queries
    else:
        from services.query_generator import ENTITY_DOMAINS
        entity_info = ENTITY_DOMAINS.get(entity, ENTITY_DOMAINS["GRP"])
        base_q = (
            f"{engagement_name} supervisory regulatory requirements "
            f"{entity.replace('_', ' ').replace('TB ', 'the organisation ')}"
        )
        all_q_texts = [base_q] + ([q[:200] for q in (extra_queries or [])[:5]])
        queries = [
            {
                "query_text": q,
                "angle": "legislation" if i == 0 else "guidance",
                "primary_domain": entity_info["domains"][0],
                "description": "",
            }
            for i, q in enumerate(all_q_texts[:7])
        ]

    try:
        # Run all queries in parallel
        tasks = [
            _single_search(q, on_query_complete)
            for q in queries[:7]
        ]
        all_result_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten, deduplicate by URL, keep first occurrence
        seen: set[str] = set()
        unique: list[dict] = []
        for result_list in all_result_lists:
            if isinstance(result_list, Exception):
                continue
            for r in result_list:
                if r["url"] not in seen:
                    seen.add(r["url"])
                    unique.append(r)

        return unique[:20]  # cap at 20 unique results

    except Exception:  # noqa: BLE001
        return []


async def _single_search(query: dict, on_complete: "callable | None") -> list[dict]:
    """Execute one Tavily query and return results with angle/domain attribution."""
    query_text = query.get("query_text", "")
    angle = query.get("angle", "guidance")
    domain = query.get("primary_domain", "")

    try:
        domain_filter = [domain] if domain else []

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query_text,
                    "search_depth": "advanced",
                    "max_results": 5,
                    "include_domains": domain_filter,
                },
            )
            resp.raise_for_status()
            raw_results = resp.json().get("results", [])

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:1500],
                "angle": angle,
                "query_used": query_text,
                "domain": domain,
                "score": r.get("score", 0),
            }
            for r in raw_results
        ]

        if on_complete:
            try:
                on_complete(query_text, angle, len(results))
            except Exception:  # noqa: BLE001
                pass

        return results

    except Exception:  # noqa: BLE001
        if on_complete:
            try:
                on_complete(query_text, angle, 0)
            except Exception:  # noqa: BLE001
                pass
        return []


def format_results_for_prompt(results: list[dict]) -> str:
    """Format search results for injection into a Claude prompt.

    Groups by angle so the synthesis prompt can reason about each research
    dimension separately rather than treating all results as equivalent.
    """
    if not results:
        return "(No live search results — using built-in knowledge only.)"

    by_angle: dict[str, list[dict]] = {}
    for r in results:
        angle = r.get("angle", "guidance")
        by_angle.setdefault(angle, []).append(r)

    angle_labels = {
        "legislation": "LEGISLATION (primary law text)",
        "supervisory": "SUPERVISORY FOCUS (regulator expectations)",
        "developments": "RECENT DEVELOPMENTS (2024-2026)",
        "enforcement": "ENFORCEMENT & FINDINGS",
        "guidance": "REGULATORY GUIDANCE (EBA/ECB/ESMA)",
        "keyword": "KEYWORD-SPECIFIC RESEARCH",
    }

    sections = []
    for angle, label in angle_labels.items():
        items = by_angle.get(angle, [])
        if not items:
            continue
        lines = [f"\n[{label}]"]
        for r in items[:4]:  # max 4 per angle to keep prompt manageable
            lines.append(
                f"  • {r['title']}\n"
                f"    URL: {r['url']}\n"
                f"    {r['content'][:800]}"
            )
        sections.append("\n".join(lines))

    # Search results are untrusted web content — a page could contain injected
    # instructions. Fence them so the synthesis model treats them as data.
    return wrap_untrusted("\n\n".join(sections), "web search results")
