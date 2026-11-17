# Lessons Learned — Track 5, Hackathon 3 (21 April 2026)

Table 9 · AI Governance & Quality Assurance · Wolters Kluwer, Amsterdam

---

## What we built

A working Hallucination Detection Agent — a post-processing skill that takes any SAAF audit finding (conforming to `outputs/schemas/finding-schema.json`) and returns an annotated version with a `hallucination_check` field flagging potentially fabricated or unverifiable factual claims.

**Pipeline:** 2 Claude API calls per finding (Haiku for claim extraction, Sonnet for batched verification against a regulatory RAG corpus), followed by rule-based risk aggregation. Full implementation shipped, tested, committed.

**Location in repo:** `tools/scripts/track-5/hallucination/`

**Prompts:** `prompts/audit-use-cases/hallucination-claim-{extractor,verifier}.md`

**Parent plan:** [`plans/hackathon-3/llm-hallucination-detection-agent.md`](../../plans/hackathon-3/llm-hallucination-detection-agent.md)
**Execution plan:** [`plans/hackathon-3/table-9-execution-plan.md`](../../plans/hackathon-3/table-9-execution-plan.md)

---

## Test results (live run on 5 sample findings)

| Finding | Type | Expected | Actual | Correct? |
|---|---|---|---|---|
| F-0001 | Seeded hallucination — fake "ISO 27001 clause 8.9.4" + fake "24-hour mandate" | HIGH | **HIGH** — 2 claims flagged incl. the fake clause | ✅ |
| F-0002 | Seeded hallucination — wrong attribution of data minimisation to GDPR Art 47 | HIGH | **HIGH** — 1 claim flagged ("GDPR Article 47") | ✅ |
| F-0003 | Clean — correctly cites ISO 27001 Annex A.8.8 | LOW | MEDIUM — 4 claims UNVERIFIED (all operational, not regulatory) | ⚠ |
| F-0004 | Clean — correctly cites GDPR Article 32 | LOW or MEDIUM | MEDIUM — same pattern | ⚠ |
| F-0005 | Clean — correctly cites IIA Standard 2310 | LOW | MEDIUM — same pattern | ⚠ |

**Primary success criterion met:** seeded hallucinations are reliably flagged HIGH with the correct offending claim text. No false positives on the HIGH flag.

**Observed tuning target:** clean findings return MEDIUM rather than LOW. Root cause (see next section) is well understood.

---

## What worked

- **2-call batched design (D3)** — total API cost across the 5-finding run was under €0.20. The Haiku-for-extraction + Sonnet-for-verification split held up.
- **Prompt caching** — system prompts cached on first call; subsequent calls ran noticeably faster.
- **Markdown RAG fallback (D1)** — worked out of the box. ChromaDB dependency never kicked in because Track 0 infrastructure wasn't needed.
- **BYOK model (D7)** — `.env` handling, fail-fast key check, and the `.gitignore` kept us safe. No key appeared in any diff.
- **Warn-only scoring (D2)** — leaves auditor judgement intact, which is defensible under IIA Std 2310.
- **Seeded hallucinations in sample data** — having deliberately-wrong findings in `dummy_data/sample_findings/` meant the demo couldn't silently pass. This was a high-value design choice.

---

## What needs tuning (discovered during the live run)

### Extractor is marking observational claims as `verifiable=true`

**Symptom:** clean findings F-0003/4/5 come back MEDIUM because 4 of ~5 claims return UNVERIFIED. On inspection (see `_checked.json` files), the UNVERIFIED claims are things like:

- "monthly Qualys scan"
- "47 critical-severity findings"
- "three ancillary databases containing personal data"
- "Review of 12 completed audit engagements"

These are **operational / observational facts about a specific company**, not regulatory claims. They cannot be verified against any regulatory RAG corpus — they should only be verifiable against the audit workpapers.

**Root cause:** the extractor prompt is over-inclusive on `verifiable`. The instruction *"standard_reference, control_name are always verifiable"* is right, but the heuristic *"date_threshold, numeric_value are usually verifiable"* is too permissive — it catches numeric observations ("47 vulnerabilities") as well as regulatory thresholds ("30 days to patch").

**The verifier's reasons are correct**: e.g. *"The retrieved context contains no reference to Qualys or any specific vulnerability scanning tool — this is an internal operational detail."* The downstream logic is fine; the upstream classification is noisy.

**Arguably this is a feature, not a bug.** An auditor reviewing the MEDIUM warning sees: "these operational facts aren't in the regulatory knowledge base; trace them to workpaper evidence." That is a legitimate auditor reminder, aligned with IIA Std 2310 ("sufficient, reliable, relevant, useful information"). We chose to ship as-is and flag tuning as P1 follow-up rather than post-hoc-optimise during the hackathon.

### Secondary observations

- **`finding-schema.json` requires 5 fields** (`id`, `title`, `risk_rating`, `observation`, `recommendation`) — our sample findings include richer fields (`root_cause`, `impact`, `control_objective`, `ai_assisted`, `evidence_references`). The concatenation in `finding_io.finding_text()` currently only uses title + observation + recommendation — adding `root_cause` and `impact` to the input would likely improve claim extraction but also lengthen the prompt. Worth A/B testing.
- **RAG keyword scoring is crude** (file-level hit count, no position weighting). Adequate for the demo but a real deployment should upgrade to ChromaDB semantic retrieval.
- **JSON parser tolerates markdown fences** but still relies on Claude returning a well-formed `[...]`. One run during development produced an unclosed array (never repeated, but worth hardening).

---

## Decisions made in-flight (not pre-planned)

| # | Decision | Why |
|---|---|---|
| L1 | Ship MEDIUM-on-clean-findings result as-is rather than re-tune extractor prompt mid-session | Result is defensible (see above). Prompt tuning without measurement is a trap. Move tuning to P1 follow-up with a proper eval set. |
| L2 | Added a `__main__.py` to the package at runtime (missing in the first write) | Needed so `python -m hallucination` works from the CLI. |
| L3 | Set max_tokens to 4096 for the verifier call (initially 1024) | Verifier returns an array with one object per claim. For findings with 5–7 claims, 1024 was truncating. |

---

## Deferred (did not get to)

1. **ChromaDB backend.** Markdown fallback was sufficient. The hook in `rag.py` is in place (`RAG_BACKEND=chromadb`) but untested against a live ChromaDB instance.
2. **Message Batches API** (50% discount, async). Sync was fast enough for 5 findings; stretch goal in the plan.
3. **Multi-model comparison (Track 5 task 5).** Not built during the 90-minute hallucination slot; should be run next as its own task.
4. **Explainability annex (Track 5 task 4).** Same — a runtime task using the existing explainability plan, not a build.
5. **Integration with Track 1's actual output.** Fell back to our synthetic sample findings (planned fallback — D1 held).

---

## Follow-up — prioritised

### P0 — before the next hackathon

1. **Tune the extractor prompt to distinguish regulatory citations from operational observations.** Specific change: add explicit rule that `numeric_value` and `date_threshold` are only `verifiable=true` when the surrounding text references a standard/framework; otherwise `verifiable=false`. Build a 10-finding eval set and measure precision before + after.
2. **Write a small pytest suite** for `aggregator.py` and `finding_io.py` (pure Python, no API needed). Took 5 min to smoke-test manually; deserves permanent coverage.

### P1 — useful soon

3. **Real ChromaDB integration test.** Stand up the Track 0 ChromaDB instance, ingest the current `mini_rag_corpus/` markdown, confirm `RAG_BACKEND=chromadb` path works end-to-end.
4. **Expand `finding_text()` to include `root_cause` + `impact` fields** when present. Measure whether claim extraction improves.
5. **Add a "severity" dimension to the annotation.** Currently we emit `overall_risk` in {LOW, MEDIUM, HIGH} but an auditor also wants to know *which specific claim is most suspect*. We already carry this in `flagged_claims[0]` — make it a first-class field.

### P2 — nice to have

6. **Diff mode** — given two versions of a finding (pre- and post-revision), show which hallucinations were fixed.
7. **Cost telemetry** — every run writes token counts to the JSONL log so we can track API spend per org over time.
8. **Auto-generate a short human-readable markdown report** alongside the JSONL log for auditor review.

### P3 — research / post-hackathon

9. **Internal-consistency checking** (deliberately descoped by D5). Separate skill once this one is stable.
10. **Multi-model ensemble for verification.** Run the same claim through Sonnet + Haiku + (stretch) local LLM; flag disagreements as lower-confidence.

---

## Handoff notes for the next owner

- **BYOK is non-negotiable.** No key in repo, ever. `.env` is gitignored; `claude_client.get_api_key()` enforces this at runtime.
- **`mini_rag_corpus/` is the weakest link** for production readiness. 10 markdown files hand-curated during the hackathon. Any real adopter needs to replace these with a proper corpus (Track 0's ChromaDB or equivalent).
- **Two of the five sample findings are deliberately wrong** — don't "fix" the F-0001 / F-0002 sample files; they are fixtures. See [`sample_findings/README.md`](../../tools/scripts/track-5/hallucination/dummy_data/sample_findings/README.md).
- **The parent plan's Section 12 "Open Questions"** (Q1: shared vs local ChromaDB, Q3: performance/cost tradeoff) are still open. Q2 (blocking threshold) and Q4 (scope creep) were resolved here as D2 and D5.

---

## Team roles at Table 9 (actual, for retrospective)

_To be filled in post-session by the facilitator. Include: who was in the build pod, who in the run pod (OWASP scan), who did explainability, any role swaps during the day._
