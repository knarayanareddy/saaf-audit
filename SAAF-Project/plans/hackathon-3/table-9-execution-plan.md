# Table 9 — Track 5 Execution Plan (Hackathon 3)
## Scope: Build the Hallucination Detector · Run everything else

| Field | Value |
|---|---|
| **Plan file** | `table-9-execution-plan.md` |
| **Session** | Hackathon 3 (Session 4) — **21 April 2026** |
| **Track** | Track 5: AI Governance & Quality Assurance |
| **Table** | Table 9 (OWASP, hallucination, explainability) |
| **Team** | 1× auditor · 2× vaktechniek · 1× analyst · 2× engineers (6 total) |
| **Status** | Working plan — to be committed to SAAF repo via fork + PR |
| **Build target** | Hallucination Detection Agent (90 min) — the only coding task |
| **Parent plan** | [llm-hallucination-detection-agent.md](./llm-hallucination-detection-agent.md) (our build) |
| **Tools we run (no code)** | [ellert-van-der-vecht-llm-owasp.md](../hackathon-2/ellert-van-der-vecht-llm-owasp.md) → [github.com/SAAF-Project/llm_owasp](https://github.com/SAAF-Project/llm_owasp) (prototype exists) · [ai-audit-explainability-framework.md](./ai-audit-explainability-framework.md) (prompt-only) · [ellert-van-der-vecht-multi-model-validation.md](../hackathon-2/ellert-van-der-vecht-multi-model-validation.md) (prompt-only) |

---

## 0. Scope & Decisions

This plan covers Table 9 for Hackathon 3. **We build exactly one thing**: the Hallucination Detection Agent. The other four tasks are **runtime activities** — we run existing tools, apply existing prompts, produce artefacts.

### 0.1 The five track tasks, classified

| Task | Time | Type | What we actually do |
|---|---|---|---|
| 1. Set up hallucination detection (claim extract → RAG verify) | 90m | **BUILD** | Write Python: claim extractor + claim verifier + risk aggregator. This is the only code we ship. |
| 2. OWASP LLM audit: 10-control scan on Track 1 agent | 60m | RUN | Clone `llm_owasp`, point at Track 1's codebase (or SAAF repo as fallback), review report |
| 3. Hallucination check: validate 5 findings from other tracks | 45m | RUN | Run *our* agent (from task 1) on 5 findings |
| 4. Explainability annex for 2 high-risk findings | 45m | APPLY | Run the explainability plan's Chain-of-Thought prompt on 2 selected findings via Claude directly |
| 5. Multi-model: same prompt through Claude + local LLM | 45m | COMPARE | Take a prompt from task 1 or 2, run through Sonnet + Haiku (and local Ollama if set up), diff the output |

### 0.2 Decisions made (so the team does not re-debate tomorrow)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Assume all external dependencies exist; use dummy fallback if not.** Includes RAG corpus and findings from other tracks. | Hackathon is 5 hours. Blocking on other tracks is failure. |
| D2 | **HIGH hallucination risk = warn only, never auto-block.** | Auditor judgement is final. Matches "second pair of eyes" mission. |
| D3 | **2 API calls per finding, not N+1.** Haiku for extraction, Sonnet for batched verification (see §3.4 for what each call does). Prompt caching on system prompts. | ~70% cost reduction. See §3. |
| D4 | **Documentation is first-class.** Per-module docstrings, per-folder READMEs, prompts as markdown files. | Track mandate + every commit is a handoff to another SAAF org. |
| D5 | **Scope is narrow: factual citation verification only.** No internal-consistency checking (finding X contradicts finding Y). | Keep 90-min build shippable. Out of scope from parent plan §12 Q4. |
| D6 | **PR committed before end of session.** Demo-ready, not polish-ready. | Track mandate: all code in the SAAF repo. Polish can follow as a second PR. |
| D7 | **Personal API keys for dev/test; zero keys committed to repo.** The SAAF org / any adopter brings their own key at integration time. Code loads only from env var; README makes this explicit. | OWASP A02 (cryptographic failures). Guardrail already mandated by parent plans. We are users of the code in dev, not providers of keys in production. |

### 0.3 Prerequisites for every team member (do this tonight)

1. **Anthropic API key** — required for running the agent. Python SDK calls Claude programmatically; this is *separate* from the Claude Code subscription. Get one at [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys. Billing is separate from Pro/Max plans.
2. Export as env var: `export ANTHROPIC_API_KEY=sk-ant-...` (or put in a local `.env` file — **already in `.gitignore`**, will never be committed).
3. Install SDK: `pip install anthropic`.
4. Verify: run `python -c "import anthropic; anthropic.Anthropic().messages.create(model='claude-haiku-4-5', max_tokens=10, messages=[{'role':'user','content':'ping'}]).content[0].text"` — should print something non-empty.

### 0.4 API key handling — dev vs. integration (D7)

| Phase | Who supplies the key | Where it lives | Our code does... |
|---|---|---|---|
| Dev & test (hackathon) | Each individual participant | Local `.env` file or shell env var | Reads `os.environ["ANTHROPIC_API_KEY"]`; fails fast with a helpful error if missing |
| Integration / adoption (post-hackathon, any SAAF org running our code) | The adopting organisation | Their own env var / secrets manager / CI | Identical to above — no change needed |

**What we commit:**
- ✅ `.env.example` at `tools/scripts/track-5/.env.example` — **template only**, placeholder values like `ANTHROPIC_API_KEY=sk-ant-PLACEHOLDER`.
- ✅ `tools/scripts/track-5/README.md` — explicit section: "**This code does not ship with an API key. You must provide your own.** See `.env.example`."
- ❌ Never: an actual key, a committed `.env`, a default fallback key in code.

**Code-level enforcement** (in `claude_client.py`):
```python
import os

def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. See tools/scripts/track-5/README.md "
            "for setup. This tool does not ship with a key — bring your own."
        )
    return key
```

This pattern matches `tools/apis/example_api_connector.py` (the repo's existing convention).

---

## 1. The Build — Hallucination Detection Agent

**Input:** One SAAF finding (conforming to [`outputs/schemas/finding-schema.json`](../../outputs/schemas/finding-schema.json)).
**Output:** Same finding JSON, annotated with `hallucination_check` object + one line appended to `outputs/logs/hallucination-checks.jsonl`.

### 1.1 Pipeline

```
S1 finding-loader  → parse input JSON; concat title + observation + recommendation
S2 claim-extractor → 1 Haiku 4.5 call → list of typed claims (see Appendix B)
S3 claim-verifier  → 1 Sonnet 4.6 call → batch-verify ALL claims with RAG context
S4 risk-aggregator → pure Python (no API call) → LOW / MEDIUM / HIGH (warn-only)
S5 annotator       → write annotation back into finding JSON + append JSONL log
```

### 1.2 Module layout (under `tools/scripts/track-5/hallucination/`)

```
tools/scripts/track-5/
├── README.md                       Overview, prerequisites, CLI usage, example output
├── requirements.txt                anthropic>=0.35, chromadb>=0.5 (optional)
└── hallucination/
    ├── __init__.py
    ├── cli.py                      python -m hallucination <finding.json>
    ├── extractor.py                S2 — claim extraction (Haiku)
    ├── verifier.py                 S3 — batched claim verification (Sonnet)
    ├── aggregator.py               S4 — rule-based risk aggregation
    ├── annotator.py                S5 — write-back + JSONL log
    ├── rag.py                      RAG lookup — ChromaDB primary, markdown fallback (D1)
    ├── claude_client.py            Claude API wrapper w/ prompt-caching helper
    ├── finding_io.py               Load/save finding-schema.json
    └── dummy_data/
        ├── sample_findings/        5 findings — 2 with deliberate hallucinations
        └── mini_rag_corpus/        ~10 regulatory snippets (ISO 27001, GDPR, DORA, IIA, EU AI Act)
```

Prompts live as **markdown files** in `prompts/audit-use-cases/` (not inline strings):
- `prompts/audit-use-cases/hallucination-claim-extractor.md`
- `prompts/audit-use-cases/hallucination-claim-verifier.md`

Python loads them via `Path.read_text()`.

---

## 2. Dependency Strategy (D1)

| Dependency | "Real" source | Fallback we ship | Swap mechanism |
|---|---|---|---|
| RAG KB | Track 0 ChromaDB ingest | `dummy_data/mini_rag_corpus/` + grep | `RAG_BACKEND=chromadb` env var |
| Findings to validate | Tracks 1/2/3 output | `dummy_data/sample_findings/` (5 findings, 2 with seeded hallucinations — the demo CANNOT silently pass if these aren't flagged) | `--finding <path>` CLI arg |
| Finding schema | `outputs/schemas/finding-schema.json` (✅ exists in repo) | Use as-is | — |

**Rule:** every fallback must be good enough for a convincing end-of-day demo. Not just "it runs."

---

## 3. Cost-Efficient API Design (D3)

### 3.1 Naïve approach (rejected)

Per finding: 1 extract + N verify + 1 aggregate = **N+2 calls**. For 5 findings × avg 4 claims: 30 Sonnet calls.

### 3.2 Chosen: 2 calls per finding + prompt caching

- **S2 Extraction — Claude Haiku 4.5.** Cheap (~$0.25/1M input, $1.25/1M output). Structured output task fits Haiku's strengths.
- **S3 Verification — Claude Sonnet 4.6.** One call per finding with ALL claims batched into a single prompt alongside the retrieved RAG context. Sonnet returns a JSON array of verdicts (one per claim).
- **S4 Aggregation — no API call.** Pure Python rules (see §4).
- **Prompt caching** on the system prompts (both ~2 KB, identical across runs): `cache_control: {"type": "ephemeral"}`. ~90% cost reduction on cached input tokens.

### 3.3 Cost estimate for hackathon demo

5 findings × 2 calls (1 Haiku + 1 Sonnet) = 10 calls. With caching, ~**$0.10–$0.20 total**.

### 3.4 What each call actually does (worked example)

**Finding text going in:**
> "Finding F-0042: ISO 27001 clause 8.2.3 requires critical patches to be applied within 30 days. Review of SAP SuccessFactors showed 12 unpatched critical vulnerabilities."

**Call 1 — Extraction (Haiku 4.5)**

Input sent to Claude: system prompt (claim-extractor prompt) + the finding text.
Output returned:
```json
[
  {"claim": "ISO 27001 clause 8.2.3", "type": "standard_reference", "verifiable": true},
  {"claim": "30 days", "type": "date_threshold", "verifiable": true},
  {"claim": "SAP SuccessFactors", "type": "system_name", "verifiable": false},
  {"claim": "12 unpatched critical vulnerabilities", "type": "numeric_value", "verifiable": false}
]
```

**Call 2 — Verification (Sonnet 4.6)**

Input sent to Claude: system prompt (claim-verifier prompt) + the 2 verifiable claims + the RAG context (retrieved text of ISO 27001 §8.2.3).
Output returned:
```json
[
  {"claim": "ISO 27001 clause 8.2.3", "verdict": "SUPPORTED", "confidence": "High",
   "reason": "Clause text matches the reference to patch management."},
  {"claim": "30 days", "verdict": "UNVERIFIED", "confidence": "High",
   "reason": "No 30-day timeframe appears in clause 8.2.3. May derive from internal policy."}
]
```

**S4 Aggregation (pure Python, no API call):**

0 hallucinated (High confidence) + 1 unverified → `overall_risk: LOW` (threshold is 2+ unverified for MEDIUM).

**Annotation written back to the finding JSON** under `hallucination_check`:
```json
"hallucination_check": {
  "run_at": "2026-04-21T14:32:00Z",
  "model": "claude-sonnet-4-6",
  "overall_risk": "LOW",
  "blocked": false,
  "warning": false,
  "flagged_claims": [],
  "unverified_claims": [{"claim": "30 days", "reason": "No 30-day timeframe in clause 8.2.3..."}],
  "summary": "1 claim supported, 1 unverified threshold."
}
```

The auditor reviewing the dossier sees the annotation and decides whether to chase the "30 days" source.

---

## 4. Risk Scoring (D2)

```python
# aggregator.py — pseudocode
def aggregate(claim_results: list[dict]) -> dict:
    hallucinated = [c for c in claim_results
                    if c["verdict"] == "LIKELY_HALLUCINATED" and c["confidence"] == "High"]
    unverified   = [c for c in claim_results if c["verdict"] == "UNVERIFIED"]

    if hallucinated:
        risk = "HIGH"
    elif len(unverified) >= 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "overall_risk": risk,
        "blocked": False,          # D2: never block
        "warning": risk in ("HIGH", "MEDIUM"),
        "flagged_claims": hallucinated,
        "unverified_claims": unverified,
        "summary": build_summary_string(risk, hallucinated, unverified),
    }
```

Matches IIA Std 2310 (auditor retains responsibility for evidence).

---

## 5. Hour-by-Hour Execution (6 people · 5 hours)

### Phase 0 — Kickoff (0:00 – 0:15)
All 6 at the table. Facilitator (auditor) walks through §0–§2. Team confirms D1–D4. Everyone forks SAAF-Project/SAAF-Project, clones their fork, creates branch `table-9/<name>-<task>`.

### Phase 1 — BUILD hallucination detector (0:15 – 1:45) · 90 min
**Build pod (3 people):** 1 engineer + 1 vaktechniek + 1 analyst.
- **Engineer:** writes `extractor.py`, `verifier.py`, `aggregator.py`, `annotator.py`, `cli.py`.
- **Vaktechniek:** writes the two prompt markdown files in `prompts/audit-use-cases/` and curates the 10 regulatory snippets in `dummy_data/mini_rag_corpus/`.
- **Analyst:** hand-writes 5 sample findings — 2 with deliberate hallucinations, 3 clean — in `dummy_data/sample_findings/`.

**Checkpoint at 1:00 (mid-pod):** engineer runs the CLI end-to-end on one sample finding. If it doesn't work, everyone huddles for 10 minutes to unblock.

**Deliverable by 1:45:** `python -m hallucination dummy_data/sample_findings/finding-01.json` produces annotated output + JSONL log line.

### Phase 1 (parallel) — RUN OWASP scan (0:15 – 1:15) · 60 min
**Run pod (3 people):** 1 engineer + 1 vaktechniek + 1 auditor.
- Clone `github.com/SAAF-Project/llm_owasp`, install, run against Track 1 codebase (or SAAF repo as fallback).
- Review the generated `audit_report.md`. Auditor validates findings read as audit-defensible.
- Save report to `outputs/table-9/owasp-audit-report-<timestamp>.md`.

**Deliverable by 1:15:** one committed audit report in `outputs/table-9/`.

### Phase 2 — RUN hallucination check on 5 findings (1:45 – 2:30) · 45 min
**Whole team:** pick 5 findings to validate. Priority order:
1. If other tracks (1/2/3) have produced real findings — use those.
2. Else: use our 2 seeded hallucinated + 3 clean samples from `dummy_data/`.

Run `python -m hallucination` on each. Review the JSONL log. The 2 seeded hallucinations **must be flagged** — if not, fix the prompt or the RAG lookup. Save results to `outputs/table-9/hallucination-results.jsonl`.

### Phase 3 — APPLY explainability annex (2:30 – 3:15) · 45 min
**2 people (vaktechniek + analyst):** pick 2 "HIGH-risk" findings from Phases 1–2 (one from OWASP report, one hallucination-flagged). Use the Chain-of-Thought prompt from [`ai-audit-explainability-framework.md`](./ai-audit-explainability-framework.md) §5 — copy-paste into `claude` CLI, paste the finding, save the response.

Output: `outputs/table-9/explainability-annex-<finding-id>.md` × 2.

**Parallel (remaining 4):** start §6 documentation sweep.

### Phase 4 — COMPARE multi-model (3:15 – 4:00) · 45 min
**1 engineer:** take ONE claim from Phase 2 results. Run the exact same `verifier.py` prompt through:
1. Claude Sonnet 4.6 (baseline — already used)
2. Claude Haiku 4.5 (swap `model=` string)
3. Local Ollama + Llama 3.1 8B — **stretch goal, skip if no local setup in 10 minutes**

Capture all outputs in `outputs/table-9/multi-model-comparison.md`. Note disagreements in 3 bullet points. Don't over-engineer — this is 45 minutes.

### Phase 5 — Documentation + PR (4:00 – 4:45) · 45 min
Everyone writes. See §6 for the checklist.

### Phase 6 — Demo (4:45 – 5:00) · 15 min
5-minute team demo. Run `python -m hallucination` live on a seeded hallucinated finding. Show the flagged claim. Show the OWASP report. Open the PR on screen.

---

## 6. Repo Commit Plan

Fork + PR workflow — direct pushes to `main` are blocked.

### 6.1 Files to commit (one combined PR)

| File / Folder | Pillar | Owner |
|---|---|---|
| `tools/scripts/track-5/hallucination/**` | Tools | Build-pod engineer |
| `tools/scripts/track-5/README.md` (incl. API-key setup section, D7) | Tools | Build-pod engineer |
| `tools/scripts/track-5/.env.example` (placeholders only, D7) | Tools | Build-pod engineer |
| `prompts/audit-use-cases/hallucination-claim-extractor.md` | Prompts | Build-pod vaktechniek |
| `prompts/audit-use-cases/hallucination-claim-verifier.md` | Prompts | Build-pod vaktechniek |
| `outputs/table-9/owasp-audit-report-<ts>.md` | Outputs | Run-pod auditor |
| `outputs/table-9/hallucination-results.jsonl` | Outputs | Whole team |
| `outputs/table-9/explainability-annex-*.md` (×2) | Outputs | Phase 3 pair |
| `outputs/table-9/multi-model-comparison.md` | Outputs | Phase 4 engineer |
| `outputs/examples/hallucination-check-example.json` | Outputs | Build-pod analyst |
| `docs/lessons-learned/track-5-hackathon-3.md` | Docs | Facilitator |
| `plans/hackathon-3/table-9-execution-plan.md` (this file) | Plans | Facilitator |

### 6.2 PR metadata
- **Title:** `Track 5 / Table 9 — Hallucination Detector + OWASP audit output (Hackathon 3)`
- **Body:** links to parent plans, list of files, screenshot of the demo.

### 6.3 Commit hygiene
- Conventional commits: `feat(track-5):`, `docs(track-5):`, `test(track-5):`
- One logical change per commit. Do not bundle code + docs + prompts.

---

## 7. Documentation Requirements (D4)

### 7.1 In-code
- Every module: docstring at top (purpose · inputs · outputs · example — 3–10 lines).
- Every public function: `Args:` / `Returns:` / `Raises:` sections.
- No "what" comments. Only "why" when non-obvious.

### 7.2 Folder READMEs
| File | Content |
|---|---|
| `tools/scripts/track-5/README.md` | Overview, prereqs, how to run, example output, troubleshooting |
| `tools/scripts/track-5/hallucination/README.md` | Pipeline diagram (mermaid), claim types (Appendix B here), risk scoring table, decision log (D1–D4) |

### 7.3 Prompts as files
Each prompt file starts with a metadata block:
```
# Prompt: <name>
Purpose: <one line>
Inputs:  <placeholders>
Outputs: <JSON schema or shape>
Model:   claude-haiku-4-5 | claude-sonnet-4-6
Version: 1.0
---
<prompt body>
```

### 7.4 Lessons-learned
End-of-day, append 3–5 bullets to `docs/lessons-learned/track-5-hackathon-3.md`. 10 minutes, massive value for Hackathon 4.

---

## 8. Risks & Mitigations

| Risk | Prob. | Impact | Mitigation |
|---|---|---|---|
| Track 0 ChromaDB not ready | High | Medium | Markdown fallback RAG (ships in `dummy_data/`) |
| Prompt caching behaves unexpectedly | Low | Low | Degrades gracefully (costs more, still works) |
| Scope creep into OWASP build | High | High | §0.1 classification table is law. If tempted to "also build a little OWASP thing," stop and read §0.1 aloud. |
| 6 people, git conflicts | Medium | Medium | Each person: own branch. One combined PR. |
| Wifi / API rate limits | Low | High | Pre-cache 3 sample API responses in `dummy_data/api_fixtures/` as last-resort demo |
| Accidental key commit during rushed PR | Medium | **Critical** | `.gitignore` already excludes `.env`; pre-commit scan `git diff --staged | grep -E 'sk-ant-\|sk-[a-zA-Z0-9]{40,}'` before pushing. If a key IS pushed: rotate immediately at console.anthropic.com, force-remove from history. |
| Ollama / local LLM setup eats 45 min | Medium | Low | Phase 4 explicitly allows skipping local — Sonnet vs. Haiku is sufficient |

---

## 9. Success criteria (end of day)

- [ ] Hallucination CLI runs end-to-end: `python -m hallucination <finding.json>` produces annotated JSON + JSONL log.
- [ ] The 2 seeded-hallucination sample findings are flagged (TP > 0).
- [ ] The 3 clean sample findings are NOT all flagged (FP < 3).
- [ ] OWASP audit report in `outputs/table-9/`.
- [ ] 2 explainability annexes in `outputs/table-9/`.
- [ ] Multi-model comparison in `outputs/table-9/`.
- [ ] Combined PR opened, with body + screenshot.
- [ ] `README.md`s and prompt markdown files meet §7 standard.
- [ ] Lessons-learned note committed.

9 boxes ticked = Table 9 shipped.

---

## Appendix A — OWASP LLM Top 10 (2025) reference card (for Phase 1 run-pod)

| ID | Name | 1-line test question |
|---|---|---|
| LLM01 | Prompt Injection | Does the agent sanitize / isolate user input from system prompt? |
| LLM02 | Sensitive Info Disclosure | Can the agent leak secrets, PII, or training data? |
| LLM03 | Supply Chain | Are model weights, datasets, and dependencies verified? |
| LLM04 | Data and Model Poisoning | Is training/fine-tuning data provenance documented? |
| LLM05 | Improper Output Handling | Is model output validated before being executed or rendered? |
| LLM06 | Excessive Agency | Are the agent's tool permissions least-privilege? |
| LLM07 | System Prompt Leakage | Can the system prompt be extracted by the user? |
| LLM08 | Vector and Embedding Weaknesses | Can RAG corpus be poisoned or extracted? |
| LLM09 | Misinformation | Are hallucinations detected and flagged? *(← our hallucination detector is an operational control for this!)* |
| LLM10 | Unbounded Consumption | Is there a rate-limit / cost-cap on model usage? |

## Appendix B — Claim types (for the extractor prompt)

| Type | Example | Verifiable via RAG? |
|---|---|---|
| `standard_reference` | "ISO 27001 clause 8.2.3" | Yes |
| `control_name` | "Access Control Policy A.9.1" | Yes |
| `date_threshold` | "patches must be applied within 30 days" | Sometimes (check policy) |
| `numeric_value` | "95% uptime SLA" | Sometimes (check contract) |
| `system_name` | "SAP SuccessFactors" | Name-existence only |
| `other` | narrative text | No — skip |

---

## 10. Open questions (surface at kickoff)

Resolved on 20 April 2026:
- ~~Does anyone have `anthropic` SDK + API key ready?~~ → Each team member provisions their own. See §0.3.
- ~~Is Track 1 pushing their agent to a public path?~~ → Transparent / not relevant. OWASP run uses dummy target (SAAF repo itself as meta-audit).
- ~~PR timing?~~ → D6: committed before end of session.
- ~~Block vs. warn on HIGH risk?~~ → D2: warn only.
- ~~Scope creep into internal-consistency checking?~~ → D5: narrow. Factual citation verification only.

Still open for kickoff:

1. Does anyone on the team have an Ollama + local LLM setup already? If no-one does, Phase 4 runs Sonnet-vs-Haiku only (skip local model — keep it a stretch goal).
2. Who fills each role? (1 facilitator/auditor, 2 vakt split across build + run pods, 1 analyst on build pod, 2 engineers split across build + run pods.)
