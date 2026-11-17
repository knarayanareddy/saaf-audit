# SAAF Intelligence Monitor

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

The SAAF community has curated 30+ high-quality AI/audit news sources (newsletters, portals, research journals, regulatory feeds — see [`docs/reference/ai-sources-registry.md`](../../docs/reference/ai-sources-registry.md)), but monitoring them manually is impossible at scale. There is no automated way to:

- Surface relevant articles to SAAF participants based on their active audit domain
- Connect new regulatory developments (EU AI Act updates, DORA RTS publications) back to specific SAAF plans that are affected
- Produce a shareable weekly digest that keeps all 45+ organisations informed

Currently, each individual monitors their own selection of sources. This creates information asymmetry: some participants are well-informed about tool releases and regulatory changes; most are not. The result is that hackathon plans are built on outdated assumptions.

---

## 3. Use-Case Type and Scope

**Audit domain:** Regulatory Intelligence / AI Governance

**Applicable standards:**

- EU AI Act (Art. 9 — risk management systems, ongoing monitoring)
- IIA Standards — Standard 1210 (Proficiency; staying current with relevant developments)
- DORA (Art. 13 — ICT threat intelligence)

**In scope:**

- Automated scraping / RSS polling of 30 curated sources (see registry)
- Relevance classification per article against SAAF plan domains (IT Governance, InfoSec, Compliance, Emerging Tech, etc.)
- Weekly digest generation in Markdown, published to GitHub Pages
- Cross-referencing new articles with existing SAAF plans that share the same audit domain
- Leaderboard tracking contributions (GitHub username → plans, PRs, articles flagged)

**Out of scope:**

- Full-text paywall content (headlines + summaries only for gated sources)
- Real-time alerting (weekly batch is sufficient for v1)
- Translation (English-language sources prioritised in v1; Dutch sources as stretch)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt: relevance-classifier prompt that scores an article against a list of SAAF plan domains and returns JSON `{domain, relevance_score, affected_plans[]}` |
| **Tools** | New Python script: `tools/scripts/intelligence_monitor.py` — polls RSS feeds, calls Claude for classification, writes digest Markdown |
| **Regulatory** | Reuse `docs/reference/ai-sources-registry.md` as the feed registry; reuse `docs/reference/domains-and-frameworks.md` as the domain taxonomy for classification |
| **Outputs** | Weekly digest Markdown (`docs/intelligence/YYYY-WW.md`) + GitHub Pages dashboard at `website/intelligence/` |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI audit intelligence analyst for the SAAF Project (Shared Audit Agents Framework).
Your role is to evaluate news articles and research publications for relevance to internal audit
teams that are building AI audit agents.

You classify each article against the following audit domains:
[IT Governance, Information Security, IT Operations, Systems & Software, Business Continuity,
Third-Party Risk, Data & Privacy, Compliance & Regulatory, Financial Controls, Operational,
Projects, Emerging Technology (AI/ML), General AI Tooling]

You also check whether the article is relevant to any of the following active SAAF plans:
[list injected at runtime from plans/ directory]

Always respond with valid JSON only. Never include prose outside the JSON block.
Bias toward relevance — it is better to flag an article that turns out irrelevant than to miss
an important regulatory development.
```

### Example user prompts

**Prompt 1 — Article classification:**
```
Classify this article for SAAF relevance.

Title: "EU AI Act High-Risk System Registry Opens for Registration"
Source: euractiv.com
Published: 2026-04-14
Summary: "The European Commission has opened the public registry for high-risk AI systems
as required under Article 71 of the EU AI Act. Organizations deploying high-risk AI must
register by June 2026."

Return JSON: {
  "domain": "<primary domain>",
  "relevance_score": <0-10>,
  "affected_plans": ["<plan slug>", ...],
  "digest_headline": "<one sentence for weekly digest>",
  "tags": ["<tag1>", ...]
}
```

**Prompt 2 — Weekly digest synthesis:**
```
You have classified 47 articles this week. Below are the top-scored items (score >= 7).
Write a weekly digest in Markdown with:
1. An executive summary (3 sentences)
2. Top 5 articles with headline, source, score, and affected plans
3. One "watch next week" item based on regulatory calendar

[Articles JSON injected here]
```

**Intended file location:** `prompts/audit-use-cases/intelligence-monitor.md`

---

## 6. Tools and Techniques

### Approach

1. **Source polling** — Parse RSS feeds for all 30 sources in the registry. For sources without RSS (e.g. LinkedIn newsletters), use `requests` + `BeautifulSoup` for headline scraping.
2. **Deduplication** — SHA-256 hash of URL + title stored in `docs/intelligence/.seen.json` to avoid re-processing.
3. **Classification** — Each new article is sent to Claude (Haiku for speed/cost, Sonnet for complex regulatory content) using the relevance-classifier prompt.
4. **Digest generation** — Top articles (score ≥ 7) are compiled into a weekly Markdown digest.
5. **GitHub Actions** — Weekly cron job (Monday 07:00) runs the script, commits the digest, and deploys to GitHub Pages.

### Example script or pseudocode

```python
import feedparser, hashlib, json, anthropic
from pathlib import Path
from datetime import datetime

SOURCES = json.loads(Path("docs/reference/ai-sources-registry.md").read_text())
SEEN = json.loads(Path("docs/intelligence/.seen.json").read_text())
client = anthropic.Anthropic()

new_articles = []
for source in SOURCES:
    feed = feedparser.parse(source["rss_url"])
    for entry in feed.entries:
        uid = hashlib.sha256(entry.link.encode()).hexdigest()
        if uid not in SEEN:
            result = classify_article(client, entry.title, entry.summary, source["name"])
            if result["relevance_score"] >= 5:
                new_articles.append({**result, "url": entry.link, "source": source["name"]})
            SEEN[uid] = datetime.now().isoformat()

write_digest(new_articles, week=datetime.now().isocalendar()[:2])
```

**Tech stack used:** Python 3.9+, Claude API (claude-haiku-4-5 for classification, claude-sonnet-4-6 for digest), `feedparser`, `beautifulsoup4`, GitHub Actions, GitHub Pages

**Intended file location:** `tools/scripts/intelligence_monitor.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| EU AI Act | Art. 9 — ongoing risk management; Art. 13 — transparency |
| IIA Standard 1210 | Proficiency — auditors must stay current |
| DORA Art. 13 | ICT threat and vulnerability intelligence |

### Claude / AI tool usage notes

- No real audit evidence or personal data is processed — only public news articles.
- Article summaries are public content; no PII transmitted.
- Classification prompts use synthetic examples only during testing.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts (using `requests` library instead)
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (intermediate) + Markdown (weekly digest) + HTML (GitHub Pages dashboard)

**Schema reference:** N/A (news items, not audit findings)

### Synthetic example output — classified article

```json
{
  "title": "EU AI Act High-Risk System Registry Opens",
  "source": "euractiv.com",
  "url": "https://euractiv.com/...",
  "domain": "Emerging Technology (AI Governance)",
  "relevance_score": 9,
  "affected_plans": [
    "ellert-van-der-vecht-llm-owasp",
    "robeminem94-gdpr-ai-audit-agent",
    "frank-van-dissel-uc5-regulatory-criteria"
  ],
  "digest_headline": "EU AI Act high-risk registry opens June 2026 — affects plans using AI classification agents.",
  "tags": ["EU AI Act", "high-risk", "registry", "compliance deadline"]
}
```

### Synthetic example — weekly digest excerpt

```markdown
## SAAF Intelligence Digest — Week 16, 2026

**Summary:** The EU AI Act registry deadline approaches (June 2026), NIST released updated AI
RMF guidance, and two new open-source RAG evaluation frameworks were published this week.
Three SAAF plans are directly affected.

### Top Articles

1. **EU AI Act High-Risk Registry Opens** (euractiv.com, score: 9)
   - Affects: `ellert-van-der-vecht-llm-owasp`, `robeminem94-gdpr-ai-audit-agent`
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-haiku-4-5 for classification, claude-sonnet-4-6 for digest)
- [x] Python 3.9+
- [x] GitHub Actions (weekly cron)
- [x] GitHub Pages (digest hosting)
- [ ] `feedparser` (RSS parsing)
- [ ] `beautifulsoup4` (HTML scraping fallback)

**Stretch goals:**

- [ ] Relevance score threshold configurable per-participant via `plans/*.md` frontmatter
- [ ] Slack/Teams webhook for real-time alerts on score ≥ 9 articles
- [ ] Dutch-language source support (NRC, FD, Tweakers)
- [ ] Leaderboard: track which participants have flagged/responded to articles

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Full scraper + classifier script (`tools/scripts/intelligence_monitor.py`)
- GitHub Actions workflow (`.github/workflows/intelligence-monitor.yml`)
- Relevance classifier prompt template
- GitHub Pages dashboard template

**What help I'm looking for:**

- Regulatory experts to validate relevance-scoring rubric (especially for DORA and NEN 7510)
- Engineers to extend source coverage (Dutch sources, LinkedIn newsletter parsing)
- Analysts to define "affected plans" mapping rules

**Cross-org interest:**

The Yellowraptor WhatsTheNews approach (see [`plans/hackathon-2/yellowraptor-whats-the-news.md`](../hackathon-2/yellowraptor-whats-the-news.md)) is a direct predecessor. This plan extends it with domain-specific relevance scoring and plan cross-referencing. All organisations benefit equally — this is shared infrastructure.

**Related SAAF plans:**

- [`plans/hackathon-2/yellowraptor-whats-the-news.md`](../hackathon-2/yellowraptor-whats-the-news.md) — predecessor; RSS scraper sub-skill can be reused
- [`plans/hackathon-2/rohan-sobha-compliance-report-generator.md`](../hackathon-2/rohan-sobha-compliance-report-generator.md) — output format alignment
- [`docs/reference/ai-sources-registry.md`](../../docs/reference/ai-sources-registry.md) — the 30-source feed registry this plan consumes
- [`eu-ai-act-compliance-monitor.md`](eu-ai-act-compliance-monitor.md) — regulatory updates from this monitor feed directly into that plan's monitoring function

**Additional sources to add (identified from WhatsApp community chat scan, April 2026):**

*Regulatory / Audit-specific (Dutch focus):*
- **NCSC NL** (`ncsc.nl/nieuws`) — Dutch national cyber security center; actively publishing AI safety directives (Mythos case, April 2026). Critical for Dutch organizations.
- **AISI UK** (`aisi.gov.uk/blog`) — UK AI Safety Institute; publishes frontier model capability evaluations (Claude Mythos, GPT evaluations).
- **artificialintelligenceact.eu** — EU AI Act implementation tracker; updated as implementation dates approach.
- **NOREA.nl** — Dutch IT auditor body; publishes AI Act compliance guidance for IT auditors.
- **Audit Magazine NL** — Dutch audit profession publication; covers practical AI use cases for auditors.
- **IIA.nl evenementen** — IIA Netherlands training calendar; new AI-related courses being added regularly.
- **ISACA.nl** — ISACA Netherlands training calendar; AI Fundamentals + AAIA credential updates.

*AI Research / Capabilities:*
- **sakana.ai blog** — Novel AI architecture research (DGM, TTT); relevant for understanding next-generation AI capabilities before they reach production.
- **DeepMind blog** (`deepmind.google/discover/blog`) — AlphaEvolve, Genie 3, frontier research.
- **Cursor changelog** (`cursor.com/changelog`) — Agent harness evolution (real-time RL, Composer 2); signals where AI coding tools are heading.
- **Anthropic research page** (`anthropic.com/research`) — System cards, interpretability, safety evaluations.
- **arcprize.org** — ARC-AGI benchmark; tracks general reasoning capability as a proxy for when AI can handle novel audit situations.
- **philschmid.de** — Context engineering, agent patterns; practical techniques for SAAF builders.

*Tool / Security:*
- **OWASP AI Testing Guide** (`github.com/OWASP/www-project-ai-testing-guide`) — Living document; essential reference for AI audit methodology.
- **Akto** (`akto.io`) — Annual State of Agentic AI Security report; enterprise AI security statistics.
- **zeroclaw.org** — Open-source harness platform updates; signals what always-on agent patterns are becoming mainstream.
- **skills.sh** — MCP skill library; new audit-relevant MCP skills published here.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Feed registry documented; classifier prompt drafted; GitHub Actions pattern defined |
| **Do** | In progress | Script prototype at Hackathon #3 |
| **Check** | Not started | Measure: precision of domain classification vs. human baseline |
| **Act** | Not started | Target: automated weekly digest live by May 2026 |

---

## 12. Open Questions

1. Should the digest be pushed to the main repo or a separate `saaf-intelligence` repo to avoid cluttering the plan history?
2. For sources without RSS, is scraping permissible under their ToS? (IIA, Big4 blogs)
3. Should relevance scoring use a fixed taxonomy (53 domains from Domains.xlsx) or a free-form tag approach?
4. How do we handle articles in Dutch, German, or French? Auto-translate before classification?
