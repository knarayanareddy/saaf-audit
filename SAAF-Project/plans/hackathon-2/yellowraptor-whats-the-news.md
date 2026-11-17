# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Yellowraptor) |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Skill |
| **Status** | Draft |

---

## 2. Problem Statement

Auditors in the financial sector need to stay current with regulatory developments from supervisors such as DNB (De Nederlandsche Bank), AFM (Autoriteit Financiële Markten), and the FD (Financieel Dagblad). Manually scanning multiple news sources every week is time-consuming and results in relevant updates being missed. WhatsTheNews solves this: a lightweight Node.js app that fetches the past week's news from configurable RSS feeds, groups items by audit-relevant topic, and presents a structured HTML overview — giving auditors a single, weekly briefing on regulatory developments relevant to their work.

---

## 3. Use-Case Type and Scope

**Audit domain:** Regulatory Intelligence / Compliance Monitoring

**Applicable standards:**

- IIA IPPF — Standard 2010 (Planning — risk-based audit plan informed by regulatory changes)
- DORA / NIS2 / GDPR — monitoring supervisory updates relevant to these frameworks

**In scope:**

- Fetching news from DNB, AFM, and FD RSS feeds (past 7 days, configurable)
- Grouping articles by topic/category (configurable keyword filters + custom categories)
- Presenting a structured HTML overview in the browser
- Configurable feed selection and category filtering via web form

**Out of scope:**

- AI-powered summarization or sentiment analysis (current version is RSS aggregation only)
- Email distribution of the briefing
- Historical archive / search across past briefings

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | TBD — stretch goal: add Claude summarization of grouped articles per category |
| **Tools** | Node.js app (no external dependencies) in [WhatsTheNews repo](https://github.com/SAAF-Project/WhatsTheNews): `server.js`, `package.json`; configurable via environment variables |
| **Regulatory** | Directly monitors regulatory sources (DNB, AFM) — complements `regulatory/control-mappings/` by surfacing new guidance |
| **Outputs** | HTML briefing page grouped by topic, accessible at `http://localhost:3000/` |

---

## 5. Prompts

### System prompt (draft — AI summarization, stretch goal)

```
You are a regulatory intelligence assistant for internal auditors in the financial sector.
Given a list of news articles from DNB, AFM, and FD grouped by topic, produce a concise
summary for each topic group: what changed, why it matters for auditors, and which audit
areas or controls may be affected.
Keep each summary to 3–5 sentences. Be factual — do not speculate beyond what the articles state.
```

### Example user prompts

**Prompt 1 — topic summary:**
```
Topic: DORA
Articles this week:
- [article 1 title + summary]
- [article 2 title + summary]

Summarize what changed and what auditors working on DORA compliance should note.
```

**Prompt 2 — audit impact assessment:**
```
The following regulatory update was published by DNB this week:
[article content]

Which audit areas or internal controls might be affected by this update?
```

**Intended file location:** `prompts/audit-use-cases/regulatory-news-monitor.md`

---

## 6. Tools and Techniques

### Approach

A lightweight Node.js HTTP server (no external npm dependencies):

1. Fetches RSS feeds from DNB, AFM, and FD on each request
2. Filters articles published within `REPORT_WINDOW_DAYS` (default: 7)
3. Groups articles by category using configurable keyword matching + user-defined custom categories
4. Returns an HTML page with grouped results — accessible in the browser at `localhost:3000`
5. Users can select which feeds to include and filter categories via a web form

### Example script or pseudocode

```javascript
// server.js (simplified)
const feeds = [DNB_FEED_URL, AFM_FEED_URL, FD_FEED_URL];
const articles = await Promise.all(feeds.map(fetchRSS));
const filtered = articles.flat().filter(isWithinWindow);
const grouped = groupByCategory(filtered, userCategories);
res.end(renderHTML(grouped));
```

**Tech stack used:** Node.js (built-in modules only — no npm dependencies), RSS/Atom parsing, HTML rendering

**Intended file location:** `tools/scripts/whats-the-news/` (reference [WhatsTheNews repo](https://github.com/SAAF-Project/WhatsTheNews))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF Standard 2010 | Risk-based audit planning informed by regulatory change |
| DORA / NIS2 | Monitoring supervisory guidance from DNB/AFM relevant to these frameworks |

### Claude / AI tool usage notes

Current version makes no API calls. Stretch goal AI summarization would send article text (public news content, no PII) to Claude API.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install` (Node.js, no external dependencies)
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only (FD_FEED_URL configurable)

---

## 8. Output Format and Examples

**Format:** HTML (browser) — grouped by topic, with article titles, dates, and links

**Schema reference:** Not a findings schema. Articles flagged as high-impact could be converted to `outputs/schemas/finding-schema.json` findings in a stretch goal.

### Synthetic example output

```
Week of 6 April 2026 — Regulatory Briefing

DORA (3 articles)
• DNB: "Guidance on ICT incident classification thresholds" — 7 April 2026
• AFM: "DORA implementation update for investment firms" — 5 April 2026
• FD: "Dutch banks prepare for DORA go-live" — 4 April 2026

NIS2 / CBW (1 article)
• DNB: "Cyberbeveiligingswet: eerste meldingen ontvangen" — 6 April 2026
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Node.js (built-in modules, no npm dependencies)
- [x] GitHub (fork + PR)
- [ ] Claude API (stretch — AI summarization)

**Stretch goals:**

- [ ] AI summarization per topic group (Claude API)
- [ ] Email distribution of the weekly briefing
- [ ] Additional feeds (ECB, EBA, ESMA, ENISA)
- [ ] Historical archive and keyword search

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The Node.js server (zero dependencies — runs anywhere with Node installed)
- Category keyword configuration
- RSS feed configuration guide for DNB, AFM, and FD

**What help I'm looking for:**

- Additional regulatory RSS feeds relevant to SAAF organizations (ECB, EBA, ESMA, sector-specific supervisors)
- Input on useful topic categories from auditors across different domains
- Interest in AI summarization integration

**Cross-org interest:**

Regulatory monitoring is a universal need for internal auditors in the financial sector. This skill is immediately deployable by any of the 45+ SAAF organizations — it requires only Node.js and takes under a minute to set up. Strong candidate for extending with Claude summarization to become a full regulatory intelligence skill.

**Related SAAF plans:**

- [`plans/hackathon-3/saaf-intelligence-monitor.md`](../hackathon-3/saaf-intelligence-monitor.md) — extends this skill with Claude-powered relevance classification, digest generation, and GitHub Actions scheduling across all 30 sources below

---

### SAAF Curated Feed List (30 Sources)

The following sources are maintained in [`docs/reference/ai-sources-registry.md`](../../docs/reference/ai-sources-registry.md). Add these to the WhatsTheNews feed configuration to extend beyond DNB/AFM/FD.

**Mail Newsletters**

| Short name | URL |
|---|---|
| TAAFT (There's An AI for That) | `https://theresanaiforthat.com/` |
| Alpha Signal | `https://alphasignal.ai/` |
| The Decoder | `https://the-decoder.com` |
| TLDR AI | `https://tldr.tech/ai` |

**AI Portals & Research**

| Short name | URL |
|---|---|
| Anthropic Research | `https://www.anthropic.com/research` |
| Perplexity Discover | `https://www.perplexity.ai/discover` |
| HuggingFace Blog | `https://huggingface.co/blog` |
| HuggingFace Daily Papers | `https://huggingface.co/papers/date/` |

**Tech News (EN)**

| Short name | URL |
|---|---|
| The Verge — AI | `https://www.theverge.com/ai-artificial-intelligence` |
| Business Insider — AI | `https://www.businessinsider.com/artificial-intelligence` |
| Nvidia News | `https://nvidianews.nvidia.com/` |
| Microsoft AI News | `https://news.microsoft.com/source/` |

**Tech News (NL)**

| Short name | URL |
|---|---|
| Tweakers — AI | `https://tweakers.net/tag/Kunstmatige%20intelligentie/nieuws/` |
| Bright NL — AI | `https://www.bright.nl/onderwerpen/AI` |

**Academic / Institutional**

| Short name | URL |
|---|---|
| MIT News — AI | `https://news.mit.edu/topic/artificial-intelligence2` |
| Berkeley News — AI | `https://news.berkeley.edu/topics/artificial-intelligence/` |
| Princeton AI | `https://ai.princeton.edu/news` |
| Stanford HAI | `https://hai.stanford.edu/news` |
| UN AI News | `https://news.un.org/en/tags/artificial-intelligence` |

**Community / Social**

| Short name | URL |
|---|---|
| r/singularity | `https://www.reddit.com/r/singularity` |
| AI Coalitie NL | `https://aic4nl.nl/nieuws/` |

**Security & Compliance**

| Short name | URL |
|---|---|
| Merge.dev — MCP Security | `https://www.merge.dev/blog/model-context-protocol-security` |

**Prompting & Education**

| Short name | URL |
|---|---|
| Learn Prompting | `https://learnprompting.org/blog` |

**GitHub**

| Short name | URL |
|---|---|
| Anthropic Skills | `https://github.com/anthropics/skills` |

**YouTube Channels** *(no RSS — manual or scraping required)*

| Channel | Focus |
|---|---|
| AI Code King | Claude Code focus |
| AI Jason | AI agents and tooling |
| AI Engineer | AI engineering concepts |
| AI Explained | AI explanations |
| Rational Animations | AI concepts |
| Training Data (Sequoia Capital) | AI industry |

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Working app built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned: use in weekly regulatory monitoring at submitter's organization |
| **Act** | Not started | Target: Hackathon 3 — add AI summarization and share learnings |

---

## 12. Open Questions

1. Which additional regulatory RSS feeds are most relevant to the SAAF community (ECB, EBA, ESMA, sector-specific)?
2. Should the Claude summarization stretch goal run per-article or per-topic-group? Per-group is more concise; per-article allows finer-grained filtering.
3. Is there interest in a shared, maintained list of regulatory RSS feeds and category keywords for the financial sector — maintained collectively by the SAAF community?
