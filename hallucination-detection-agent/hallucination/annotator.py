"""
Annotator (S5) + End-to-End Orchestration
=========================================

Runs the full pipeline on one finding:
    finding_text -> extract_claims -> retrieve_context -> verify_claims
      -> aggregate -> attach annotation + append JSONL log
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .aggregator import aggregate
from .claude_client import MODEL_VERIFIER, REPO_ROOT
from .extractor import extract_claims
from .finding_io import finding_text
from .rag import retrieve_context
from .verifier import verify_claims


LOG_PATH = REPO_ROOT / "outputs" / "logs" / "hallucination-checks.jsonl"


def check_finding(finding: dict[str, Any]) -> dict[str, Any]:
    """Run the full hallucination-detection pipeline on one finding.

    Args:
        finding: A finding dict (finding-schema.json-conformant).

    Returns:
        The same finding dict with a ``hallucination_check`` key added.

    Raises:
        EnvironmentError: If ANTHROPIC_API_KEY is missing.
        anthropic.APIError: Propagated from SDK.
    """
    text = finding_text(finding)
    claims = extract_claims(text)

    rag_query = " ".join(c["claim"] for c in claims if c["verifiable"]) or text
    rag_context = retrieve_context(rag_query, top_k=3)

    verdicts = verify_claims(claims, rag_context)
    assessment = aggregate(verdicts)

    finding["hallucination_check"] = {
        "run_at": _utc_now_iso(),
        "model": MODEL_VERIFIER,
        "claims_checked": len(claims),
        "claims_verifiable": sum(1 for c in claims if c["verifiable"]),
        "rag_backend": "chromadb" if _rag_backend_is_chromadb() else "markdown",
        **assessment,
    }

    _append_log(str(finding.get("id", "unknown")), finding["hallucination_check"], len(claims))
    return finding


def _append_log(finding_id: str, check: dict[str, Any], claims_total: int) -> None:
    """Append one JSONL line to the audit log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": check["run_at"],
        "finding_id": finding_id,
        "claims_checked": claims_total,
        "overall_risk": check["overall_risk"],
        "blocked": check["blocked"],
        "warning": check["warning"],
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rag_backend_is_chromadb() -> bool:
    import os
    return os.environ.get("RAG_BACKEND", "markdown").lower() == "chromadb"
