"""
RAG Lookup
==========

Retrieves regulatory / audit context for a given claim.

Two backends:
    1. ChromaDB (primary, semantic) — only if ``RAG_BACKEND=chromadb`` env
       var is set AND the ``chromadb`` package is importable AND the server
       is reachable. Falls back to markdown on any failure (logs a warning).
    2. Markdown corpus (default) — keyword scoring over
       ``dummy_data/mini_rag_corpus/*.md``. Always works, zero dependencies.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path


CORPUS_ROOT = Path(__file__).parent / "dummy_data" / "mini_rag_corpus"

_STOPWORDS = {
    "the", "and", "or", "of", "in", "to", "a", "an", "is", "are", "be", "for",
    "on", "at", "by", "with", "as", "that", "this", "it", "from", "was", "were",
    "has", "have", "had", "but", "not", "no", "if", "than", "then", "so", "do",
    "does", "did", "must", "shall", "should", "all", "any", "can", "may",
}

log = logging.getLogger(__name__)


def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieve up to ``top_k`` regulatory snippets relevant to the query.

    Args:
        query: The claim text (or concatenation of claims) to look up.
        top_k: Maximum number of snippets to return. Default 3.

    Returns:
        A single string with retrieved snippets separated by ``\n\n---\n\n``.
        Empty string if nothing matched or corpus is missing.

    Raises:
        Does not raise — missing corpus / unreachable ChromaDB returns "".
        The verifier treats empty context as "UNVERIFIED" signal.
    """
    backend = os.environ.get("RAG_BACKEND", "markdown").lower()
    if backend == "chromadb":
        try:
            return _chromadb_lookup(query, top_k)
        except Exception as e:  # noqa: BLE001 — explicit broad fallback
            log.warning("ChromaDB lookup failed (%s); falling back to markdown.", e)
    return _markdown_lookup(query, top_k)


def _chromadb_lookup(query: str, top_k: int) -> str:
    """ChromaDB-backed semantic retrieval (optional).

    Falls back to markdown if chromadb is not installed or server unreachable.
    """
    try:
        import chromadb  # type: ignore[import-not-found]
    except ImportError:
        log.warning("chromadb not installed; falling back to markdown.")
        return _markdown_lookup(query, top_k)

    host = os.environ.get("CHROMADB_HOST", "localhost")
    port = int(os.environ.get("CHROMADB_PORT", "8000"))
    client = chromadb.HttpClient(host=host, port=port)
    collection = client.get_collection("saaf-regulatory")
    result = collection.query(query_texts=[query], n_results=top_k)
    docs = (result.get("documents") or [[]])[0]
    return "\n\n---\n\n".join(docs) if docs else ""


def _markdown_lookup(query: str, top_k: int) -> str:
    """Keyword-based markdown retrieval (always works, fallback)."""
    if not CORPUS_ROOT.is_dir():
        log.warning("RAG corpus not found at %s", CORPUS_ROOT)
        return ""

    keywords = _tokenize(query)
    if not keywords:
        return ""

    scored: list[tuple[int, Path, str]] = []
    for md_file in sorted(CORPUS_ROOT.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        content_lower = content.lower()
        score = sum(content_lower.count(k) for k in keywords)
        if score > 0:
            scored.append((score, md_file, content))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    if not top:
        return ""
    return "\n\n---\n\n".join(c for _, _, c in top)


def _tokenize(query: str) -> list[str]:
    """Extract content keywords from the query (lowercased, 3+ chars, no stopwords)."""
    words = re.findall(r"[A-Za-z0-9]{3,}", query.lower())
    return [w for w in words if w not in _STOPWORDS]
