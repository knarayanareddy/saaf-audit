#!/usr/bin/env python3
"""
generate_recap.py
Reads repo_data.json + overlap_analysis.json and produces recap-session-1.md.

Usage:
    python3 SAAF-Project/tools/scripts/generate_recap.py
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RECAP_DIR = Path(__file__).parents[2] / "hackathon-recap"
REPO_DATA_FILE = RECAP_DIR / "repo_data.json"
OVERLAP_FILE = RECAP_DIR / "overlap_analysis.json"
OUTPUT_FILE = RECAP_DIR / "recap-session-1.md"

# ── Session facts ──────────────────────────────────────────────────────────────
SESSION = {
    "date": "March 10, 2026",
    "venue": "Mollie, Amsterdam",
    "attendees": "80+",
    "organizations": "45+",
    "format": "Full-day hackathon (09:00–18:00 CET)",
    "theme": "AI Audit Agents — from prompt to production",
}

DOMAIN_LABELS = {
    "access-review": "Access Review",
    "journal-entry-testing": "Journal Entry Testing",
    "vendor-risk": "Vendor Risk Management",
    "fraud-detection": "Fraud Detection",
    "compliance-monitoring": "Compliance Monitoring",
    "financial-audit": "Financial Audit",
    "it-audit": "IT Audit",
    "contract-review": "Contract Review",
    "data-quality": "Data Quality",
    "continuous-monitoring": "Continuous Monitoring",
}

TECH_LABELS = {
    "claude-api": "Claude API (Anthropic)",
    "mcp": "Model Context Protocol (MCP)",
    "python": "Python",
    "sql": "SQL / Databases",
    "typescript-js": "TypeScript / JavaScript",
    "langchain": "LangChain / LangGraph",
    "openai": "OpenAI / GPT",
    "vector-db": "Vector Database",
    "cloud-aws": "AWS",
    "cloud-azure": "Azure / Microsoft",
    "cloud-gcp": "Google Cloud",
    "docker": "Docker / Containers",
}


def md_table(headers: List[str], rows: List[List[str]]) -> str:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells):
        return "| " + " | ".join(str(c).ljust(col_widths[i]) for i, c in enumerate(cells)) + " |"

    sep = "| " + " | ".join("-" * w for w in col_widths) + " |"
    lines = [fmt_row(headers), sep] + [fmt_row(r) for r in rows]
    return "\n".join(lines)


def truncate(text: str, max_len: int = 120) -> str:
    if not text:
        return "—"
    text = text.strip().replace("\n", " ")
    return text[:max_len] + "…" if len(text) > max_len else text


def repo_card(repo: dict, analysis: Optional[Dict]) -> str:
    name = repo.get("name", "unknown")
    desc = repo.get("description") or "_No description provided_"
    url = repo.get("url") or ""
    topics = ", ".join(repo.get("topics") or []) or "—"
    languages = ", ".join((repo.get("languages") or {}).keys()) or "—"
    pushed = (repo.get("pushed_at") or "—")[:10]

    domains = ", ".join(DOMAIN_LABELS.get(d, d) for d in (analysis or {}).get("domains") or []) or "—"
    techs = ", ".join(TECH_LABELS.get(t, t) for t in (analysis or {}).get("tech_stack") or []) or "—"

    readme_excerpt = ""
    if repo.get("readme"):
        lines = [l.strip() for l in repo["readme"].splitlines() if l.strip() and not l.startswith("#")]
        excerpt = " ".join(lines[:3])
        readme_excerpt = f"\n> {truncate(excerpt, 200)}\n"

    return (
        f"### {name}\n\n"
        f"**Description:** {desc}  \n"
        f"**URL:** {url}  \n"
        f"**Last pushed:** {pushed}  \n"
        f"**Languages:** {languages}  \n"
        f"**Topics:** {topics}  \n"
        f"**Audit domains:** {domains}  \n"
        f"**Tech stack:** {techs}  \n"
        f"{readme_excerpt}"
    )


def build_lessons_learned(repos: List[Dict], overlap: dict) -> str:
    total = len(repos)
    classified = total - len(overlap.get("unclassified_repos") or [])
    top_domains = list(overlap.get("domain_groups") or {})[:3]
    top_techs = list(overlap.get("tech_groups") or {})[:3]
    domain_str = ", ".join(DOMAIN_LABELS.get(d, d) for d in top_domains)
    tech_str = ", ".join(TECH_LABELS.get(t, t) for t in top_techs)

    return f"""\
### What Went Well

- **High participation rate** — {total} agents built across {SESSION["organizations"]} organizations in a single day
- **Domain diversity** — teams tackled {len(overlap.get("domain_groups") or {})} distinct audit domains
- **Shared framework adoption** — the 4-pillar SAAF structure (Prompts / Tools / Regulatory / Outputs) was widely adopted as a starting point
- **Cross-pollination** — mixing auditors, engineers, and domain experts in teams produced agents that balanced technical quality with audit relevance
- **Tooling consensus** — {tech_str} emerged as the dominant stack, enabling easy knowledge transfer between teams

### Challenges

- **README quality varies** — {total - classified} repos had insufficient metadata to auto-classify; manual review needed
- **Scope creep** — several teams built overly broad agents; narrower scope tends to yield more reliable output
- **Regulatory grounding** — mapping agent outputs to specific control frameworks (ISAE 3402, ISO 27001) was underspecified in many agents
- **Output validation** — few teams included structured output schemas or human-in-the-loop checkpoints
- **Time pressure** — the 8-hour window was tight; some agents are functional prototypes, not production-ready

### Key Observations

- The most effective agents combined a **tight domain scope** with a **clear output format** (structured JSON or filled audit template)
- Teams that shared a PAT or service account for tool access moved fastest
- Agents using **MCP** were able to connect to live data sources without writing custom connectors
- The biggest differentiator was not the model choice but the **quality of the system prompt and regulatory anchoring**
"""


def main():
    if not REPO_DATA_FILE.exists():
        logger.error("repo_data.json not found — run scrape_hackathon_repos.py first")
        raise SystemExit(1)
    if not OVERLAP_FILE.exists():
        logger.error("overlap_analysis.json not found — run analyze_overlaps.py first")
        raise SystemExit(1)

    repos: List[Dict] = json.loads(REPO_DATA_FILE.read_text())
    overlap: dict = json.loads(OVERLAP_FILE.read_text())

    # Build lookup for per-repo analysis
    per_repo_lookup: Dict[str, Dict] = {r["name"]: r for r in (overlap.get("per_repo") or [])}

    total_repos = overlap.get("total_repos") or len(repos)
    generated_on = date.today().isoformat()

    # ── YAML front-matter ──────────────────────────────────────────────────────
    front_matter = f"""\
---
title: "SAAF Hackathon — Session 1 Recap"
subtitle: "{SESSION['date']} · {SESSION['venue']}"
author: "SAAF-Project Organizers"
date: "{generated_on}"
lang: en
toc: true
toc-depth: 3
number-sections: true
---
"""

    # ── Section 1: Overview ────────────────────────────────────────────────────
    overview_rows = [
        ["Date", SESSION["date"]],
        ["Venue", SESSION["venue"]],
        ["Attendees", SESSION["attendees"]],
        ["Organizations represented", SESSION["organizations"]],
        ["Format", SESSION["format"]],
        ["Theme", SESSION["theme"]],
        ["AI Audit Agents built", str(total_repos)],
        ["Recap generated on", generated_on],
    ]
    overview_table = md_table(["Attribute", "Value"], overview_rows)

    sec1 = f"""\
# Overview

The first SAAF (Shared Audit Agents Framework) hackathon brought together {SESSION["attendees"]} professionals from {SESSION["organizations"]} organizations for a full day of building AI audit agents. Participants formed cross-functional teams pairing auditors with engineers and worked within the SAAF 4-pillar framework.

{overview_table}

The event was hosted at **{SESSION["venue"]}** and ran from 09:00 to 18:00 CET, including a morning keynote, three build sprints, and a closing showcase.
"""

    # ── Section 2: Agents built ────────────────────────────────────────────────
    # Summary table
    agent_rows = []
    for repo in repos:
        if repo.get("error"):
            continue
        name = repo["name"]
        analysis = per_repo_lookup.get(name, {})
        domains = " / ".join(DOMAIN_LABELS.get(d, d) for d in (analysis.get("domains") or [])[:2]) or "—"
        techs = ", ".join(TECH_LABELS.get(t, t) for t in (analysis.get("tech_stack") or [])[:3]) or "—"
        desc = truncate(repo.get("description") or "—", 60)
        agent_rows.append([name, desc, domains, techs])

    agent_table = md_table(
        ["Repository", "Description", "Audit Domain(s)", "Tech Stack"],
        agent_rows,
    )

    # Detail cards
    cards = []
    for repo in repos:
        if repo.get("error"):
            continue
        analysis = per_repo_lookup.get(repo["name"])
        cards.append(repo_card(repo, analysis))

    cards_section = "".join(c + "\n---\n\n" for c in cards) if cards else "_No repo data available — run scrape_hackathon_repos.py to populate._"

    sec2 = f"""\
# Agents Built

{total_repos} AI audit agents were built during the hackathon. The table below provides a high-level overview; detailed cards follow.

## Summary Table

{agent_table}

## Agent Detail Cards

{cards_section}
"""

    # ── Section 3: Overlap Analysis ────────────────────────────────────────────
    domain_groups = overlap.get("domain_groups") or {}
    tech_groups = overlap.get("tech_groups") or {}
    overlapping_pairs = overlap.get("overlapping_pairs") or []

    # Domain groups table
    domain_rows = [
        [DOMAIN_LABELS.get(k, k), str(len(v)), ", ".join(v[:5]) + ("…" if len(v) > 5 else "")]
        for k, v in domain_groups.items()
    ]
    domain_table = md_table(["Audit Domain", "# Repos", "Repositories (sample)"], domain_rows) if domain_rows else "_No domain data available._"

    # Tech groups table
    tech_rows = [
        [TECH_LABELS.get(k, k), str(len(v)), ", ".join(v[:5]) + ("…" if len(v) > 5 else "")]
        for k, v in tech_groups.items()
    ]
    tech_table = md_table(["Technology", "# Repos", "Repositories (sample)"], tech_rows) if tech_rows else "_No tech data available._"

    # Top overlapping pairs table
    pair_rows = [
        [
            " & ".join(p["repos"]),
            ", ".join(DOMAIN_LABELS.get(d, d) for d in p["shared_domains"][:3]) or "—",
            ", ".join(TECH_LABELS.get(t, t) for t in p["shared_tech"][:3]) or "—",
            str(p["overlap_score"]),
        ]
        for p in overlapping_pairs[:15]
    ]
    pair_table = md_table(["Repository Pair", "Shared Domains", "Shared Tech", "Score"], pair_rows) if pair_rows else "_No overlapping pairs detected._"

    sec3 = f"""\
# Overlap Analysis

## By Audit Domain

{domain_table}

## By Technology Stack

{tech_table}

## Overlapping Repository Pairs

The following pairs of repositories address the same audit domain(s) and/or use the same technology stack. High-overlap pairs are strong candidates for merging, sharing test data, or defining a common interface.

{pair_table}

## Recommendation

1. **Consolidate access-review agents** — multiple teams built independently; a reference implementation should be designated.
2. **Create shared test fixtures** — teams using the same SQL database / data model should share synthetic datasets.
3. **Publish a common output schema** — standardize on a JSON envelope (`finding`, `risk_level`, `evidence`, `recommendation`) so outputs are composable.
4. **Cross-team code review sprint** — schedule a 2-hour review session pairing overlapping teams.
"""

    # ── Section 4: Lessons Learned ────────────────────────────────────────────
    sec4 = f"""\
# Lessons Learned

{build_lessons_learned(repos, overlap)}
"""

    # ── Section 5: Where Are We Now ───────────────────────────────────────────
    next_steps_rows = [
        ["1", "Consolidate overlapping agents into reference implementations", "High", "April 2026"],
        ["2", "Define shared output schema (JSON envelope)", "High", "April 2026"],
        ["3", "Publish polished agents to SAAF-Project org (public)", "Medium", "April 2026"],
        ["4", "Document regulatory mapping per agent (ISAE, ISO)", "Medium", "May 2026"],
        ["5", "Run Session 2 hackathon — focus on production hardening", "High", "June 2026"],
        ["6", "Submit best agents to ISACA / IIA community for peer review", "Low", "Q3 2026"],
    ]
    next_steps_table = md_table(["#", "Action", "Priority", "Target"], next_steps_rows)

    sec5 = f"""\
# Where Are We Now

## Current State

Following Session 1, the SAAF-Project has:

- **{total_repos} working agent prototypes** covering {len(domain_groups)} distinct audit domains
- A **shared framework** (4-pillar: Prompts / Tools / Regulatory / Outputs) with documentation
- An active **GitHub organization** with private repos for each team's work
- A growing community of **{SESSION["organizations"]} organizations** engaged in the initiative

## Next Steps

{next_steps_table}

## Call to Action

> **If you built an agent at Session 1:** Please update your repo's README with a one-paragraph description, the audit domain, and the tech stack. Add topics using the SAAF taxonomy (e.g., `saaf-access-review`, `saaf-claude-api`). This enables automatic indexing.
>
> **If you want to contribute:** Open an issue in the main SAAF-Project repo or reach out to the organizers. Session 2 dates will be announced in the community channel.
"""

    # ── Section 6: Appendix ───────────────────────────────────────────────────
    appendix_repo_rows = [
        [
            repo["name"],
            repo.get("url") or "—",
            (repo.get("pushed_at") or "—")[:10],
        ]
        for repo in repos
        if not repo.get("error")
    ]
    appendix_table = md_table(["Repository", "URL", "Last Updated"], appendix_repo_rows)

    sec6 = f"""\
# Appendix

## A — Repository Index

{appendix_table}

## B — Data Methodology

This recap was generated programmatically from the GitHub API via the `gh` CLI. The scripts are located in `tools/scripts/`:

| Script | Purpose |
|--------|---------|
| `scrape_hackathon_repos.py` | Fetches repo metadata, READMEs, commits, issues, and language breakdowns |
| `analyze_overlaps.py` | Keyword-classifies repos by audit domain and tech stack; computes overlap pairs |
| `generate_recap.py` | Produces this Markdown document from the collected data |

Raw data files (`repo_data.json`, `repo_data_raw/`) are gitignored as they contain private repo information.

To regenerate:
```bash
python3 SAAF-Project/tools/scripts/scrape_hackathon_repos.py
python3 SAAF-Project/tools/scripts/analyze_overlaps.py
python3 SAAF-Project/tools/scripts/generate_recap.py
```

## C — SAAF Framework Structure

```
SAAF-Project/
├── prompts/               # System instructions, audit-use-case prompts, templates
│   ├── system-instructions/
│   ├── audit-use-cases/
│   └── conventions/
├── tools/                 # API connectors, integrations, automation scripts
│   ├── apis/
│   ├── integrations/
│   ├── automation/
│   └── scripts/           ← this recap's scripts
├── regulatory/            # Control mappings, guardrails, AI usage policies
│   ├── frameworks/        (ISO 27001, NIS2)
│   ├── policies/
│   └── guardrails/
├── outputs/               # Output templates, report formats (to be added)
└── hackathon-recap/       ← this folder
```

The 4-pillar structure ensures agents are **prompt-driven**, **tool-connected**, **regulatory-grounded**, and produce **structured outputs** suitable for audit evidence.
"""

    # ── Assemble document ──────────────────────────────────────────────────────
    doc = "\n\n".join([
        front_matter,
        sec1,
        sec2,
        sec3,
        sec4,
        sec5,
        sec6,
    ])

    OUTPUT_FILE.write_text(doc, encoding="utf-8")
    logger.info("Written recap to %s (%d chars)", OUTPUT_FILE, len(doc))
    print(f"\nDone → {OUTPUT_FILE}")
    print("Review the Markdown, fill in any blanks, then run pandoc to generate the PDF.")


if __name__ == "__main__":
    main()
