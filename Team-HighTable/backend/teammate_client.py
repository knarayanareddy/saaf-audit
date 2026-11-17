from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def _field(obj: Dict[str, Any], *keys: str) -> Any:
    """Return the first non-None, non-empty value found among the given keys.

    TeamMate+ may return fields in either camelCase or PascalCase, so callers
    should pass all plausible variants, e.g. _field(obj, 'title', 'Title').
    """
    for key in keys:
        value = obj.get(key)
        if value is not None and value != "":
            return value
    return None


class TeamMateClient:
    """Async client for the TeamMate+ REST API."""

    DEFAULT_BASE_URL = "https://br1ght8.teammatehosting.com/TeamMate"
    PAGE_SIZE = 100

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

        auth_scheme = os.environ.get("TEAMMATE_AUTH_SCHEME", "")
        self._auth_header = f"{auth_scheme} {api_key}".strip() if auth_scheme else api_key

        cache_ttl_hours = float(os.environ.get("CACHE_TTL_HOURS", "6"))
        self._cache_ttl_seconds = cache_ttl_hours * 3600

        self._cached_issues: Optional[List[Dict[str, Any]]] = None
        self._cache_timestamp: float = 0.0
        self._cache_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _get_all_pages(
        self, client: httpx.AsyncClient, path: str
    ) -> List[Dict[str, Any]]:
        """Iterate through all pages of a paginated endpoint and return combined results."""
        all_results: List[Dict[str, Any]] = []
        page_number = 1  # TeamMate+ API uses 1-based pageNumber

        while True:
            params = {"pageNumber": page_number, "pageSize": self.PAGE_SIZE}
            url = f"{self.base_url}{path}"
            response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()

            data = response.json()

            # TeamMate+ wraps results in a "results" key with a "metadata" sibling
            if isinstance(data, list):
                page_items = data
                total_pages = 1
            elif isinstance(data, dict):
                page_items = (
                    data.get("results")
                    or data.get("value")
                    or data.get("items")
                    or data.get("data")
                    or []
                )
                metadata = data.get("metadata") or {}
                total_pages = metadata.get("pageCount") or 1
            else:
                page_items = []
                total_pages = 1

            logger.info(
                "Page %d/%d: status=%d, keys=%s, items=%d",
                page_number,
                total_pages,
                response.status_code,
                list(data.keys()) if isinstance(data, dict) else "list",
                len(page_items),
            )

            all_results.extend(page_items)

            if page_number >= total_pages:
                break

            page_number += 1

        return all_results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Fetch a single issue by ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}/api/v1/Issues/{issue_id}"
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def get_effective_issues(self) -> List[Dict[str, Any]]:
        """Return all issues with their recommendations.

        Results are cached in memory for CACHE_TTL_HOURS hours.
        """
        async with self._cache_lock:
            now = time.monotonic()
            if (
                self._cached_issues is not None
                and (now - self._cache_timestamp) < self._cache_ttl_seconds
            ):
                logger.info("Returning %d issues from cache", len(self._cached_issues))
                return self._cached_issues

            logger.info("Cache miss — fetching issues from TeamMate+")
            issues = await self._fetch_all_issues()
            self._cached_issues = issues
            self._cache_timestamp = time.monotonic()
            logger.info("Cached %d issues", len(issues))
            return issues

    async def _fetch_all_issues(self) -> List[Dict[str, Any]]:
        """Build the issue corpus from individual recommendation fetches.

        The /api/v1/Issues paginated list returns no results in this instance,
        so we derive issue data from the ``parent`` field on each recommendation.
        Each recommendation is fetched individually (async, 20 concurrent) to
        retrieve its full payload including parent issue id/title and text fields.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Step 1: get all recommendation stubs (id + href from list)
            rec_stubs = await self._get_all_pages(client, "/api/v1/Recommendations")
            logger.info(
                "Found %d recommendation stubs; fetching full details", len(rec_stubs)
            )

            # Step 2: fetch each recommendation individually
            semaphore = asyncio.Semaphore(20)

            async def fetch_rec(stub: Dict[str, Any]) -> Optional[Dict[str, Any]]:
                async with semaphore:
                    rec_id = stub.get("id")
                    try:
                        resp = await client.get(
                            f"{self.base_url}/api/v1/Recommendations/{rec_id}",
                            headers=self._headers(),
                        )
                        resp.raise_for_status()
                        data: Dict[str, Any] = resp.json()
                        # Normalise text fields so the embedding service finds them
                        if not data.get("description"):
                            data["description"] = (
                                data.get("text1") or data.get("text2") or ""
                            )
                        return data
                    except Exception as exc:
                        logger.warning(
                            "Failed to fetch recommendation %s: %s", rec_id, exc
                        )
                        return None

            results = await asyncio.gather(*[fetch_rec(s) for s in rec_stubs])
            full_recs = [r for r in results if r is not None]
            logger.info("Fetched %d full recommendations", len(full_recs))

        # Step 3: group by parent issue
        issues_map: Dict[str, Dict[str, Any]] = {}
        for rec in full_recs:
            parent = rec.get("parent") or {}
            if parent.get("type") != "Issue":
                continue
            parent_id = str(parent.get("id", ""))
            if not parent_id:
                continue
            if parent_id not in issues_map:
                issues_map[parent_id] = {
                    "id": parent_id,
                    "title": parent.get("title", ""),
                    "_recommendations": [],
                }
            issues_map[parent_id]["_recommendations"].append(rec)

        issues = list(issues_map.values())
        logger.info(
            "Built %d issues from %d recommendations", len(issues), len(full_recs)
        )
        return issues

    def invalidate_cache(self) -> None:
        """Invalidate the in-memory cache so the next call fetches fresh data."""
        self._cached_issues = None
        self._cache_timestamp = 0.0
        logger.info("Cache invalidated")
