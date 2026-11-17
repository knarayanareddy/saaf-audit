"""
Hallucination Detection Agent
=============================

A post-processing skill that validates AI-generated audit findings against a
regulatory knowledge base, flagging unsupported or hallucinated claims before
they enter the audit dossier.

Pipeline (claim-extract -> RAG verify):

    finding-loader      parse input JSON (title + observation + recommendation)
    claim-extractor     Haiku call -> structured list of claims
    claim-verifier      Sonnet call -> per-claim verdict w/ RAG context
    risk-aggregator     pure-Python rules -> LOW / MEDIUM / HIGH (warn-only)
    annotator           write annotation + append JSONL audit log

Parent plan:
    plans/hackathon-3/llm-hallucination-detection-agent.md

Execution plan:
    plans/hackathon-3/table-9-execution-plan.md

Usage (CLI):
    python -m hallucination <finding.json>

Usage (programmatic):
    from hallucination import check_finding
    annotated = check_finding(finding_dict)
"""

from .annotator import check_finding  # noqa: F401

__version__ = "0.1.0"
