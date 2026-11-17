"""Manifest collection where a failed fetch is visible instead of silently using seed data.

Pattern fixed: HTTP errors only printed to stderr, then a fallback to seed content with
a green build.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from ..guard import Guard

MAX_BYTES = 256 * 1024


def assess_fetches(results: Iterable[Mapping[str, Any]], max_bytes: int = MAX_BYTES) -> Guard:
    """Each result: {"repo": str, "status": int | None, "body": str | None}."""
    g = Guard("manifest-fetch")
    for r in results:
        repo = r.get("repo", "<unknown>")
        status, body = r.get("status"), r.get("body")
        if status != 200:
            g.not_assessed(f"fetch returned status {status}; no fallback data used", repo)
        elif not body:
            g.not_assessed("empty manifest body", repo)
        elif len(body.encode("utf-8")) > max_bytes:
            g.not_assessed(f"manifest larger than {max_bytes} bytes", repo)
        else:
            g.check("manifest_fetched", True, repo)
            g.mark_assessed(repo)
    return g
