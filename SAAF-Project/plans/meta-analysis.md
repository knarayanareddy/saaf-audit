# SAAF Meta-Analysis — Cross-Plan Synthesis

> **Last updated:** April 2026 (post video + chat + URL analysis — 59 plans)  
> **Audience:** SAAF facilitators, vaktechniek, and experienced participants  
> **See also:** [`plans/overview.md`](overview.md) | [`plans/gap-analysis.md`](gap-analysis.md) | [`plans/hackathon-3-workstreams.md`](hackathon-3-workstreams.md)

---

## 1. PDCA Status Across All Plans

| Phase | H2 Plans (26) | H3 Plans (29) | Alignment (4) |
|---|---|---|---|
| **Plan** | All complete | All complete | All complete |
| **Do** | 20/26 complete; 6 in progress | 29/29 in progress (Hackathon #3 day) | 2/4 complete |
| **Check** | 2/26 started (ellert, the-control-freaks) | 0/22 started | 0/4 started |
| **Act** | 0/26 | 0/22 | 0/4 |

**Key insight:** The SAAF portfolio has a **Do-heavy bias** — most plans describe what will be built but few have been validated (Check) or improved based on evidence (Act). Hackathon #3 is the first moment where H1/H2 outputs can be validated against real agent runs.

**H3 split:** 8 original plans (infrastructure focus) + 14 new plans from video transcription analysis + 7 new plans from WhatsApp chat + URL analysis (hallucination detection, explainability, OWASP AI testing, EU AI Act monitor, shadow AI scanner, audit report generator, on-premise GPU framework). The 21 new plans are at Plan stage only — no Do yet.

**Recommended action for Hackathon #3:** Designate 30 minutes for validation runs on H2 agents using Strapi synthetic data, and log results in the Check column of each plan.

---

## 2. Hackathon #3 Assignments (April 21, 2026 — Wolters Kluwer)

The following plans are ready for active work on hackathon day. Assignments are role-based:

### Auditor Role (no coding required)

| Plan | Task | Expected output |
|---|---|---|
| `audit-automation-overview.md` | Validate the 5-phase lifecycle overview against your own audit practice; add missing use cases | Updated lessons-learned and do's/don'ts section |
| `grc-copilot-mindshift-agent.md` | Test 6 Copilot prompt templates in real M365 Copilot; note what works and what needs refinement | Annotated cheat sheet with "tested / needs work" flags |
| `frank-van-dissel-uc4-fraud-risk-assessment.md` | Run the fraud risk agent against Strapi synthetic incident data; review the output | Finding list with auditor-added risk classifications |
| `robeminem94-gdpr-ai-audit-agent.md` | Use the agent to assess a synthetic DPIA document (from Strapi); annotate gaps | GDPR assessment finding with Condition/Criterion/Cause/Effect |
| `audit-workflow-automation-levels.md` | Rate your organization's current automation level (1/2/3) for 5 audit tasks; validate the level descriptions | Completed maturity assessment for your org; suggested edits to level definitions |
| `audit-skills-transformation-curriculum.md` | Complete the self-assessment; place yourself at Stage 1–4; identify your biggest skill gap | Completed self-assessment + 3 recommended next activities |
| `always-on-audit-agent.md` | Define the 10 most common questions you ask during fieldwork (these become the agent's prompt library) | Prompt library seed: 10 field audit questions with expected answer format |

### Vaktechniek Role (audit + technical)

| Plan | Task | Expected output |
|---|---|---|
| `johannesiv-policy-to-controls-extractor.md` | Test the extractor against a synthetic ISO 27001 policy; validate control mappings against IPPF | Annotated control mapping with vaktechniek sign-off |
| `the-control-freaks-uc7-rcm-builder.md` | Build an RCM for the Change Management domain using the agent + Strapi change ticket data | Populated RCM with risk ratings |
| `icfcop-control-testing-agent.md` | Map one of your organization's controls into the ICFCOP mega-control framework | Cross-framework mapping JSON for one control domain |
| `frank-van-dissel-uc5-regulatory-criteria.md` | Retrieve DORA Article 13 requirements via the skill; validate against official DORA text | Validated criterion list with source citations |
| `document-evidence-extraction-agent.md` | Run the extraction agent on a synthetic policy PDF (from Strapi); validate extracted controls against manual review | Side-by-side comparison: AI extraction vs. manual; precision and recall score |
| `audit-subagent-coordination-framework.md` | Run 3-agent debate on one vendor contract finding; compare consensus to your own assessment | Consensus finding JSON + note on where agents agreed/disagreed with you |
| `ai-audit-explainability-framework.md` | Take one completed finding from UC7 or GDPR agent; run `generate_explainability_annex.py`; review whether the 5-question annex is defensible in a management response | Annotated annex with vaktechniek feedback: which questions were answered well, which need improvement |

### Analyst Role (data + Python)

| Plan | Task | Expected output |
|---|---|---|
| `saaf-intelligence-monitor.md` | Run the monitor script against 5 feeds from the 30-source list; review classification output | Relevance-scored digest for 5 sources |
| `saaf-skills-registry-and-matching.md` | Complete the skills questionnaire; run the matching algorithm against today's plan list | Suitability scores for 5 participants |
| `example-synthetic-access-review.md` | Analyze the 200-record Strapi access review dataset; produce exception report | Exception list with 15-20% false positive analysis |
| `themontechristo-threewaysecurity.md` | Run 3-way match on Strapi vendor contract + PO + GRN synthetic data | 3-way match exception report |
| `overnight-audit-batch-processing-agent.md` | Run the batch orchestrator on a 5-task RCM build queue; verify checkpoint recovery by killing and restarting mid-batch | Completed batch run + proof that resume from checkpoint works |
| `audit-memory-knowledge-system.md` | Index 10 synthetic audit notes into ChromaDB; run 3 semantic queries; compare to keyword search | Retrieval comparison: semantic vs. keyword for 3 audit questions |
| `open-source-audit-agent-framework.md` | Run 3 SAAF prompts through GLM 4.7 (local); compare output to Claude Sonnet; document quality delta | Side-by-side output comparison for 3 prompts; cost: €0 vs. €X |

### Engineer Role (TypeScript / Python / Docker)

| Plan | Task | Expected output |
|---|---|---|
| `saaf-jira-confluence-mcp.md` | Stand up both MCP servers; test `jira_search` and `confluence_search` against Strapi | Working MCP + successful test script output |
| `saaf-strapi-synthetic-data.md` | Deploy Strapi Docker instance; seed all 5 content types; verify API responses | Running Strapi at `localhost:1337` with 1,000 records |
| `saaf-rag-knowledge-base.md` | Ingest the DORA + GDPR + ISO 27001 summary corpus into ChromaDB; run 5 benchmark queries | Retrieval results for 5 queries with relevance scores |
| `ellert-van-der-vecht-llm-owasp.md` | Run the OWASP audit pipeline against another SAAF agent's codebase | Scored audit report for a community agent |
| `audit-loop-orchestration-sdk.md` | Implement Task + Loop + Agent primitives; run a 3-task vendor assessment batch | Working SDK + batch run output; state file showing 3/3 complete |
| `power-bi-audit-dashboard-mcp.md` | Stand up MCP server with Strapi mock; push 5 synthetic findings; verify dataset row count | MCP running + 5 findings in mock Power BI dataset |
| `cli-audit-system-wrapper.md` | Add 2 approved commands to the allowlist (e.g., dsquery, dir); test with synthetic AD data | Allowlist config + 2 test command runs with output |
| `audit-agent-gamified-ui.md` | Run the fleet dashboard alongside the batch orchestrator; verify live progress display | Browser showing live agent fleet status during overnight batch demo |
| `llm-hallucination-detection-agent.md` | Run `hallucination_check.py` against 3 findings from the access review agent and 2 from the fraud risk agent; count flagged claims and measure false positive rate | Validation log with per-finding risk scores; note on which claims were correctly vs. incorrectly flagged |

---

## 3. Cross-Plan Overlap Analysis

### Work Program Cluster (High overlap — merge candidates)

Three plans independently address audit work program generation from an audit objective:

1. `frank-van-dissel-uc8-audit-work-program.md`
2. `floris-stokkers-work-program-agent.md`
3. `inge-garretsen-audit-work-program-agent.md`

**Recommended action:** Consolidate into one canonical plan (`canonical-audit-work-program-agent.md`) that synthesizes the best prompts from all three. Keep the originals as contributor attribution stubs.

### RCM Cluster (Moderate overlap — differentiation exists)

Three plans address Risk & Control Matrix building:

1. `frank-van-dissel-uc7-rcm-builder.md`
2. `the-control-freaks-uc7-rcm-builder.md` ← best quality
3. `the-rcm-rangers-audit-work-program-agent.md` (combined RCM + work program)

**Recommended action:** Elevate `the-control-freaks-uc7-rcm-builder.md` as the canonical RCM plan. Frank UC7 becomes a pointer. The RCM Rangers plan covers a unique combined workflow — keep separate.

### Policy-to-Controls Cluster (Complementary)

Three plans extract controls from policy documents:

1. `frank-van-dissel-uc1-policy-process-intake.md` — intake and gap identification
2. `johannesiv-policy-to-controls-extractor.md` — GDPR + EU AI Act mapping
3. `robeminem94-gdpr-ai-audit-agent.md` — GDPR audit agent

These are differentiated enough to remain separate but should cross-reference each other bidirectionally.

### Monitoring Cluster (Sequential evolution)

1. `yellowraptor-whats-the-news.md` (H1 MVP — RSS aggregation, no AI)
2. `saaf-intelligence-monitor.md` (H3 — AI-powered classification, GitHub Actions, 30 sources)

These are explicitly a v1 → v2 progression. The Intelligence Monitor plan already cross-references WhatsTheNews. Both plans should be retained.

---

## 4. Do's, Don'ts, and Lessons Learned

### Do's (from H1 and H2 experience)

1. **Start with the output schema** — Plans that define their output format first (e.g., `finding-schema.json`) produce more useful agents. Agents without a defined output format produce free-text that is hard to post-process.
2. **Use synthetic data from the start** — Teams that had synthetic data at H2 could demonstrate their agent live. Teams without test data could not.
3. **Prompts > models** — Prompt quality predicted output quality far better than model choice. The difference between a well-structured prompt and a vague one was larger than the difference between Claude Sonnet and Claude Haiku.
4. **RAG beats long system prompts** — Agents with a knowledge base (even a small one) outperformed agents that tried to put regulatory text in the system prompt.
5. **Validate against real auditor judgment** — The best H2 outputs were those where an auditor reviewed and annotated the AI output, not where the AI was the final word.
6. **Document what you did and why** — The most reusable H2 plans have clear rationale in Section 7 (Regulatory). Plans without regulatory grounding are hard to extend.

### Don'ts (from H1 and H2 experience)

1. **Don't send real audit data to external APIs** — Even in demo context, use Strapi synthetic data. GDPR Art. 28 applies.
2. **Don't treat agent output as authoritative** — AI findings must be reviewed by a qualified auditor before entering the audit dossier.
3. **Don't build without a test case** — An agent with no example input/output cannot be demonstrated and cannot be validated. Always include at least one synthetic example.
4. **Don't skip the Regulatory section** — Plans that skip Section 7 often build technically impressive agents that fail audit quality standards (no audit trail, no norm citation, no exception flagging).
5. **Don't overbuild for the hackathon** — An agent that does one thing well is more valuable than a partial multi-function agent. Scope down ruthlessly.

### Lessons Learned (by session)

**Hackathon 1 (March 10, 2026):**
- `yellowraptor-whats-the-news.md`: RSS aggregation without AI is immediately useful but limited — auditors still had to read all articles to identify relevance
- Whisper transcription: 88 video files; processing time ~3h on M-series Mac with `whisper base`; quality acceptable for keyword search, less accurate for proper nouns and Dutch content

**Hackathon 2 (March 24, 2026):**
- The Frank van Dissel UC series (9 plans) demonstrates that a structured use-case approach produces consistent, high-quality plans — the template works
- `the-control-freaks-uc7-rcm-builder.md` was the highest-quality single plan (Score 5): complete prompts, clear tool design, regulatory mapping, and output schema linked
- Three work program plans (UC8 / Floris / Inge) emerged independently with similar approaches — a signal that the community needs a coordination mechanism (see `saaf-skills-registry-and-matching.md`)
- Jira evidence collection was the most common manual step auditors reported in walkthroughs — motivating `saaf-jira-confluence-mcp.md`
- Most agents ran well in Claude Code but had no repeatable test harness — motivating `saaf-strapi-synthetic-data.md`

---

## 5. Model Comparison: Local vs. Cloud

| Criterion | Whisper (local) | Ollama / local LLM | Claude Haiku | Claude Sonnet |
|---|---|---|---|---|
| **Primary use** | Audio → text transcription | Offline reasoning, sensitive data | Classification, routing, simple extraction | Complex reasoning, finding drafting |
| **Privacy** | ✅ Ideal (no data leaves device) | ✅ Ideal | ⚠️ Cloud (use with synthetic data only) | ⚠️ Cloud (use with synthetic data only) |
| **Quality** | Good for English; Dutch accuracy ~80% | Varies by model size; smaller models miss nuance | Fast; adequate for classification tasks | Highest reasoning quality in SAAF tests |
| **Cost** | Hardware only | Hardware only | $0.00025/1K input tokens | $0.003/1K input tokens (10× Haiku) |
| **Setup** | `pip install openai-whisper` + `ffmpeg` | `ollama pull llama3` | `ANTHROPIC_API_KEY` + 1 pip install | Same as Haiku |
| **When to use** | Transcribing Teams/Zoom audit meetings | Offline tests, sensitive document analysis | Article classification, routing, short extractions | Finding drafts, regulatory assessments, complex reasoning |
| **SAAF examples** | 88 video transcriptions; Teams meeting minutes | Local policy analysis without cloud exposure | `saaf-intelligence-monitor.md` (article classifier) | All agent analysis, icfcop, llm-owasp, access review |

**Rule of thumb:** Use local (Whisper/Ollama) when the data is real and sensitive. Use Claude API when the data is synthetic or when reasoning quality matters most.

---

## 6. SAAF Governance Framework Direction

### What SAAF is becoming (observed trajectory)

**H1 (March 2026):** Individual agents for individual tasks. RSS reader, first fraud risk drafts.

**H2 (March 2026):** Structured plan template introduced. 26 plans submitted covering most IT audit domains. Quality varies.

**H3 (April 2026):** Shared infrastructure introduced (Strapi, RAG, MCP). ICFCOP multi-framework alignment. audit lifecycle meta-overview. First community matching algorithm.

**H4+ (target):** Agents by design — permanent, scheduled agents that run without human trigger. Shared agent registry. Cross-org agent sharing. Validation framework.

### Agents by Design vs. Agents on Demand

The `audit-automation-overview.md` plan articulates this distinction. In governance terms:

| | Agents by Design | Agents on Demand |
|---|---|---|
| **Governance requirement** | Change control, validation, audit trail, periodic review | Human-in-the-loop review per use |
| **IIA standard** | 2010 (risk-based planning), 2050 (coordination) | 1200 (proficiency), 2310 (identifying information) |
| **SAAF readiness** | 0 agents in production today (targets for H4+) | ~10 agents demonstrated and reusable today |
| **First candidates** | `saaf-intelligence-monitor.md` (weekly cron), `yellowraptor-whats-the-news.md` (RSS scheduler) | All current H2/H3 agent plans |

### Skills and Role Taxonomy

Based on 45+ organizations and 4 session patterns, SAAF participants fall into 4 roles:

| Role | Profile | Primary contribution | Plans best suited |
|---|---|---|---|
| **Auditor** | Knows audit process, limited coding | Validates outputs, writes prompts, defines criteria | `frank-van-dissel-uc*`, `grc-copilot-mindshift-agent` |
| **Vaktechniek** | Deep domain knowledge (DORA, GDPR, ISO) | Writes regulatory criteria, validates control mappings | `frank-van-dissel-uc5`, `johannesiv`, `robeminem94-gdpr` |
| **Analyst** | Can write Python, thinks in data | Builds data pipelines, runs analysis scripts | `example-synthetic-access-review`, `themontechristo`, `saaf-intelligence-monitor` |
| **Engineer** | Full-stack, API experience | Builds MCP servers, Docker, GitHub Actions, TypeScript | `saaf-jira-confluence-mcp`, `saaf-strapi-synthetic-data`, `saaf-rag-knowledge-base` |

The `saaf-skills-registry-and-matching.md` plan formalizes this taxonomy with a 15-question questionnaire and algorithmic matching.

---

## 7. Open Questions for Hackathon #3 Discussion

1. **Merge strategy**: Should we merge the work-program cluster and RCM cluster into canonical plans before Hackathon #4, or keep originals and add a "canonical" pointer?
2. **Agents by design governance**: What change control process should SAAF adopt before deploying the first "always-on" agent (e.g., `saaf-intelligence-monitor.md` on GitHub Actions)?
3. **Cross-org sharing**: Which completed H2 plans are ready to be shared with organizations outside SAAF (via IIA Nederland)? Proposed: `ellert-van-der-vecht-llm-owasp.md`, `the-control-freaks-uc7-rcm-builder.md`, `audit-automation-overview.md`.
4. **Language**: Should the canonical SAAF reference documents be bilingual (NL + EN) or English-first with a Dutch summary?
5. **Data sandbox**: Should the Strapi instance be hosted centrally (one URL for all participants) or run locally (Docker, each participant)? Central is more convenient; local is more private.
6. **RAG quality benchmark**: What is the minimum acceptable retrieval precision@5 before the shared RAG knowledge base can be recommended to all participants?
