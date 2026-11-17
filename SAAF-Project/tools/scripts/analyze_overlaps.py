#!/usr/bin/env python3
"""
analyze_overlaps.py
Reads repo_data.json and produces overlap_analysis.json.

Usage:
    python3 SAAF-Project/tools/scripts/analyze_overlaps.py
"""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RECAP_DIR = Path(__file__).parents[2] / "hackathon-recap"
INPUT_FILE = RECAP_DIR / "repo_data.json"
OUTPUT_FILE = RECAP_DIR / "overlap_analysis.json"

# ── Domain keyword taxonomy ────────────────────────────────────────────────────
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "access-review": [
        "access review", "access control", "iam", "user access", "privilege",
        "rbac", "entitlement", "sod", "segregation of duties", "provisioning",
    ],
    "journal-entry-testing": [
        "journal entry", "journal entries", "general ledger", "gl testing",
        "je testing", "month-end", "accrual", "posting",
    ],
    "vendor-risk": [
        "vendor risk", "third party", "third-party", "supplier", "procurement",
        "vendor assessment", "due diligence",
    ],
    "fraud-detection": [
        "fraud", "anomaly detection", "unusual transaction", "red flag",
        "suspicious", "forensic",
    ],
    "compliance-monitoring": [
        "compliance", "regulatory", "gdpr", "sox", "iso27001", "nis2",
        "control testing", "audit trail", "evidence collection",
    ],
    "financial-audit": [
        "financial audit", "balance sheet", "income statement", "p&l",
        "reconciliation", "financial statement", "materiality",
    ],
    "it-audit": [
        "it audit", "change management", "patch management", "vulnerability",
        "penetration", "itgc", "it general control",
    ],
    "contract-review": [
        "contract", "agreement", "clause", "legal review", "nda",
    ],
    "data-quality": [
        "data quality", "data lineage", "data governance", "master data",
        "data validation",
    ],
    "continuous-monitoring": [
        "continuous monitoring", "real-time", "dashboard", "kri", "kpi",
        "alert", "threshold",
    ],
}

# ── Tech stack taxonomy ────────────────────────────────────────────────────────
TECH_KEYWORDS: dict[str, list[str]] = {
    "claude-api": ["claude api", "anthropic", "claude-3", "claude-sonnet", "claude-haiku", "claude-opus"],
    "mcp": ["mcp", "model context protocol"],
    "python": ["python", ".py"],
    "sql": ["sql", "postgresql", "sqlite", "mysql", "bigquery", "snowflake", "duckdb"],
    "typescript-js": ["typescript", "javascript", "node.js", "nodejs", "react", "next.js"],
    "langchain": ["langchain", "langgraph"],
    "openai": ["openai", "gpt-4", "gpt-3"],
    "vector-db": ["vector", "embedding", "pinecone", "weaviate", "chroma", "qdrant", "faiss"],
    "cloud-aws": ["aws", "lambda", "s3", "dynamodb", "bedrock"],
    "cloud-azure": ["azure", "microsoft", "teams"],
    "cloud-gcp": ["gcp", "google cloud", "bigquery", "vertex"],
    "docker": ["docker", "container", "kubernetes"],
}


def text_for_repo(repo: dict) -> str:
    parts = [
        repo.get("name") or "",
        repo.get("description") or "",
        repo.get("readme") or "",
        " ".join(repo.get("topics") or []),
    ]
    return " ".join(parts).lower()


def match_keywords(text: str, taxonomy: Dict[str, List[str]]) -> List[str]:
    matched = []
    for category, keywords in taxonomy.items():
        for kw in keywords:
            if kw in text:
                matched.append(category)
                break
    return matched


def main():
    if not INPUT_FILE.exists():
        logger.error("repo_data.json not found at %s — run scrape_hackathon_repos.py first", INPUT_FILE)
        raise SystemExit(1)

    repos: List[Dict] = json.loads(INPUT_FILE.read_text())
    logger.info("Loaded %d repos", len(repos))

    domain_groups: dict[str, list[str]] = defaultdict(list)
    tech_groups: dict[str, list[str]] = defaultdict(list)
    repo_analysis: List[Dict] = []

    for repo in repos:
        if repo.get("error"):
            continue
        name = repo["name"]
        text = text_for_repo(repo)

        domains = match_keywords(text, DOMAIN_KEYWORDS)
        techs = match_keywords(text, TECH_KEYWORDS)

        # Language fallback into tech groups
        for lang in (repo.get("languages") or {}):
            lang_lower = lang.lower()
            if lang_lower == "python" and "python" not in techs:
                techs.append("python")
            elif lang_lower in ("typescript", "javascript") and "typescript-js" not in techs:
                techs.append("typescript-js")
            elif lang_lower == "sql" and "sql" not in techs:
                techs.append("sql")

        for d in domains:
            domain_groups[d].append(name)
        for t in techs:
            tech_groups[t].append(name)

        repo_analysis.append({
            "name": name,
            "description": repo.get("description"),
            "domains": domains,
            "tech_stack": techs,
            "languages": list((repo.get("languages") or {}).keys()),
            "topics": repo.get("topics") or [],
        })

    # ── Overlapping pairs ──────────────────────────────────────────────────────
    overlapping_pairs = []
    seen = set()
    for domain, names in domain_groups.items():
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                key = tuple(sorted([a, b]))
                if key not in seen:
                    seen.add(key)
                    # Shared domains
                    a_domains = next((r["domains"] for r in repo_analysis if r["name"] == a), [])
                    b_domains = next((r["domains"] for r in repo_analysis if r["name"] == b), [])
                    shared_domains = list(set(a_domains) & set(b_domains))
                    a_techs = next((r["tech_stack"] for r in repo_analysis if r["name"] == a), [])
                    b_techs = next((r["tech_stack"] for r in repo_analysis if r["name"] == b), [])
                    shared_techs = list(set(a_techs) & set(b_techs))
                    overlapping_pairs.append({
                        "repos": [a, b],
                        "shared_domains": shared_domains,
                        "shared_tech": shared_techs,
                        "overlap_score": len(shared_domains) + len(shared_techs),
                    })

    # Sort by overlap score descending
    overlapping_pairs.sort(key=lambda x: x["overlap_score"], reverse=True)

    # ── Unclassified ──────────────────────────────────────────────────────────
    unclassified = [r["name"] for r in repo_analysis if not r["domains"]]

    result = {
        "total_repos": len(repo_analysis),
        "domain_groups": {k: v for k, v in sorted(domain_groups.items(), key=lambda x: -len(x[1]))},
        "tech_groups": {k: v for k, v in sorted(tech_groups.items(), key=lambda x: -len(x[1]))},
        "overlapping_pairs": overlapping_pairs[:50],  # top 50
        "unclassified_repos": unclassified,
        "per_repo": repo_analysis,
    }

    OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    logger.info("Written overlap analysis to %s", OUTPUT_FILE)

    # Summary
    print(f"\nDone. {len(repo_analysis)} repos analyzed.")
    print(f"Domain groups: {', '.join(f'{k}({len(v)})' for k, v in result['domain_groups'].items())}")
    print(f"Tech groups: {', '.join(f'{k}({len(v)})' for k, v in result['tech_groups'].items())}")
    print(f"Overlapping pairs found: {len(overlapping_pairs)}")
    print(f"Unclassified repos: {len(unclassified)}")


if __name__ == "__main__":
    main()
