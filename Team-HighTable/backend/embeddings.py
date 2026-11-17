from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

from teammate_client import _field

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Sentence-transformer based embedding service for semantic similarity search."""

    def __init__(self) -> None:
        self._model_name: str = os.environ.get(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        self._model: Optional[Any] = None  # Lazy-loaded on first use

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self) -> Any:
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self._model_name)
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded")
        return self._model

    @staticmethod
    def _get_issue_text(issue: Dict[str, Any]) -> str:
        """Combine an issue's title, description, and recommendation texts into one string."""
        parts: List[str] = []

        title = _field(issue, "title", "Title") or ""
        description = _field(issue, "description", "Description") or ""

        if title:
            parts.append(title)
        if description:
            parts.append(description)

        recommendations: List[Dict[str, Any]] = issue.get("_recommendations", [])
        for rec in recommendations:
            rec_title = _field(rec, "title", "Title") or ""
            rec_desc = _field(rec, "description", "Description", "text", "Text") or ""
            if rec_title:
                parts.append(rec_title)
            if rec_desc:
                parts.append(rec_desc)

        return " ".join(parts)

    @staticmethod
    def _cosine_similarity_batch(
        query_vec: np.ndarray, corpus_vecs: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarities between a query vector and a matrix of corpus vectors.

        Both inputs are expected to be L2-normalised, so cosine similarity reduces to
        the dot product.
        """
        # query_vec shape: (dim,)  corpus_vecs shape: (N, dim)
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        corpus_norms = corpus_vecs / (
            np.linalg.norm(corpus_vecs, axis=1, keepdims=True) + 1e-10
        )
        return corpus_norms @ query_norm  # shape: (N,)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_similar(
        self,
        current_text: str,
        issues: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return the top_k most semantically similar issues to current_text.

        Each returned issue dict has an added '_similarity_score' float field (0.0–1.0).
        """
        if not issues:
            return []

        model = self._load_model()

        # Build corpus texts
        corpus_texts = [self._get_issue_text(issue) for issue in issues]

        # Encode all texts in one batch for efficiency
        all_texts = [current_text] + corpus_texts
        logger.info(
            "Encoding %d texts (1 query + %d corpus)", len(all_texts), len(corpus_texts)
        )
        embeddings = model.encode(all_texts, show_progress_bar=False, convert_to_numpy=True)

        query_vec: np.ndarray = embeddings[0]
        corpus_vecs: np.ndarray = embeddings[1:]

        similarities = self._cosine_similarity_batch(query_vec, corpus_vecs)

        # Pair each issue with its score and sort descending
        scored = sorted(
            zip(similarities.tolist(), issues),
            key=lambda x: x[0],
            reverse=True,
        )

        # Return top_k with similarity score attached
        results: List[Dict[str, Any]] = []
        for score, issue in scored[:top_k]:
            issue_copy = dict(issue)
            issue_copy["_similarity_score"] = float(max(0.0, min(1.0, score)))
            results.append(issue_copy)

        return results
