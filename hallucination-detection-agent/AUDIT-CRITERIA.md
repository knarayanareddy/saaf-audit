# AUDIT-CRITERIA.md — Hallucination Detection Agent

> Draft prepared 6 October 2026 from the agent's own README, the Track 5 lessons-learned document (21 April 2026) and a code read of the pipeline. Status Draft: criteria marked ☐ are not yet verified by a run or a test. Edit freely; the structure follows `docs/conventions/audit-criteria-template.md` in SAAF-Project.

## Metadata

| Field | Value |
|---|---|
| **Agent** | Hallucination Detection Agent (SAAF Track 5, Table 9) |
| **Repository** | https://github.com/SAAF-Project/hallucination-detection-agent (moved from `SAAF-Project/SAAF-Project/tools/scripts/track-5/`) |
| **Maintainer(s)** | Jim / furyknl |
| **Last reviewed** | 2026-10-06 |
| **Status** | Draft |
| **Sources used to draft this document** | `tools/scripts/track-5/hallucination/README.md`; `docs/lessons-learned/track-5-hackathon-3.md`; `prompts/audit-use-cases/hallucination-claim-{extractor,verifier}.md`; the live run of 21 April 2026 on five sample findings |
| **Makes model calls at runtime?** | Yes: two Claude calls per finding (Haiku for claim extraction, Sonnet for batched verification). AI-specific frameworks therefore apply. |

## 1. What the agent does

The agent is a post-processing check for AI-generated audit findings. It takes one finding in the SAAF finding schema, extracts the factual claims in it (standard references, control names, thresholds, numbers), looks each claim up in a regulatory knowledge base (ISO 27001, GDPR, DORA, NIS2, EU AI Act, IIA standards), and returns the finding annotated with a verdict per claim: supported, unverified, or likely hallucinated. It never blocks a finding; it warns, and the auditor decides. Every check is appended to a log.

## 2. Control objectives and framework mapping

| Control objective | Framework and clause | Why relevant |
|---|---|---|
| **CO-1 — Grounded verdicts.** A claim is marked SUPPORTED only when the retrieved source text explicitly contains it; the model's own knowledge is never the basis. | IIA Global Internal Audit Standards 14.1 (gathering sufficient, reliable, relevant information) · OWASP LLM Top 10 2025, LLM09 Misinformation | The agent exists to stop invented citations entering the dossier. If it could itself "know" a clause, it would reproduce the failure it is meant to catch. |
| **CO-2 — Conservative flagging.** When in doubt between UNVERIFIED and LIKELY_HALLUCINATED, the agent chooses UNVERIFIED; a HALLUCINATED verdict requires the source to make the error unambiguous. | IIA GIAS 15.1 (accurate, objective, clear communication) · EU AI Act art. 13 (transparency: output the user can interpret) | False hallucination flags destroy the auditor's trust in the tool faster than misses do. |
| **CO-3 — The auditor decides.** A HIGH risk result is a warning, never a block; the original finding is returned unchanged with the annotation added. | IIA GIAS 14.1 and 14.3 (the internal auditor evaluates and concludes) · EU AI Act art. 14 (human oversight) | Responsibility for evidence stays with the auditor. The tool is a second pair of eyes, not a gate. |
| **CO-4 — Traceability of every check.** Each run writes one log line with finding id, claims, verdicts, confidence and model used, and the annotated finding carries the same data. | IIA GIAS 14.6 (engagement documentation) · ISO/IEC 27001:2022 clause 7.5 (documented information) | An auditor or a reviewer can re-perform or dispute any verdict later. |
| **CO-5 — No secrets, no leakage.** The API key comes from the environment only; nothing in the repository holds a key; finding text is sent only to the configured model provider. | ISO/IEC 27001:2022 Annex A 5.17 (authentication information), A 8.24 (use of cryptography) · OWASP LLM Top 10 2025, LLM02 Sensitive Information Disclosure | Audit findings can contain client-sensitive facts; a leaked key or a stray endpoint would expose them. |

## 3. Acceptance criteria

**CO-1**
- Given a claim whose referenced clause is present in the retrieved context, the agent returns SUPPORTED with a `reason` that cites the context fragment.
- Given a claim whose clause is absent from the retrieved context, the agent does not return SUPPORTED, even when the claim is true in the real standard.
- Given an empty or irrelevant context, every verifiable claim is UNVERIFIED, none SUPPORTED.

**CO-2**
- Given the seeded hallucinations in `dummy_data/sample_findings/F-0001.json` and `F-0002.json` (a non-existent ISO clause, a GDPR article misattributed), the agent returns `overall_risk = HIGH` and names the offending claim text.
- Given the clean findings F-0003, F-0004 and F-0005, the agent never returns HIGH.
- Given a claim the context neither confirms nor denies, the verdict is UNVERIFIED, not LIKELY_HALLUCINATED.

**CO-3**
- Given any result, including HIGH, the output file contains the complete original finding plus a `hallucination_check` field; no field of the original is altered or removed.
- Given a HIGH result, the agent sets `warning = true` and `blocked = false`.

**CO-4**
- Given one run, exactly one line is appended to `outputs/logs/hallucination-checks.jsonl` with finding id, timestamp, claim count, verdicts and overall risk.
- Given a verdict in the annotated finding, the same verdict with the same reason is present in the log line.

**CO-5**
- Given no `ANTHROPIC_API_KEY` in the environment, the agent exits with a clear error before any network call.
- Given a search of the repository for `sk-ant-`, there are zero matches in tracked files.
- Given a run, the only outbound host is `api.anthropic.com` (verifiable with a network trace in CI).

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ The original finding, byte for byte, plus one `hallucination_check` object | ✕ Mark a claim SUPPORTED from the model's own knowledge |
| ✓ One verdict per extracted claim, in input order, each with confidence and a reason citing context | ✕ Block, delete or rewrite a finding |
| ✓ `overall_risk` in {LOW, MEDIUM, HIGH} derived by the fixed rules in `aggregator.py`, not by the model | ✕ Return HIGH for a clean finding (F-0003 to F-0005) |
| ✓ A log line per check | ✕ Read a key from a file in the repository or print it |
| ✓ Findings conforming to `outputs/schemas/finding-schema.json` | ✕ Send finding text to any host other than the configured model provider |

## 5. Coverage gaps

- **The extractor over-flags operational facts.** Numbers and dates about a specific company ("47 critical findings", "monthly Qualys scan") are marked verifiable and come back UNVERIFIED, so clean findings score MEDIUM instead of LOW. Logged as P0 on 21 April 2026; not yet fixed. Limitation, stated honestly: a MEDIUM today may mean "operational facts not in the regulatory corpus", not "suspect finding".
- **The knowledge base is ten hand-written markdown files.** Verdicts are only as good as that corpus. The ChromaDB path exists in code but has never been run against a live instance.
- **No automated tests.** The pure-Python aggregator and file reader have no test suite; the seeded sample findings are the only check, and they are run by hand.
- **Only regulatory claims are checked.** Internal policies, workpaper references and system names are skipped by design; the agent says nothing about them.
- **Repository hygiene.** The lessons-learned document's team-roles section is empty; the agent moved to its own repository in October 2026 and the removal PR in SAAF-Project must list the files moved.
- **Cost and latency are not logged.** Token counts per run were planned (P2) and are not written to the log.

## 6. Status / validation

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-2, seeded F-0001 and F-0002 → HIGH | ☑ | Live run 21 April 2026, `docs/lessons-learned/track-5-hackathon-3.md`, results table |
| CO-2, clean F-0003 to F-0005 never HIGH | ☑ | Same run: all three MEDIUM, none HIGH |
| CO-3, original finding unchanged, warn only | ☑ | Design decision D2 and `annotator.py`; verified by inspection of `_checked.json` files |
| CO-4, one log line per run | ☑ | `outputs/logs/hallucination-checks.jsonl` after the April run |
| CO-5, key from environment only | ☑ | `claude_client.get_api_key()` fails fast; `.env` gitignored (decision D7) |
| CO-1, SUPPORTED only from context | ☐ | Needs a test with a true claim and an empty context |
| CO-5, zero keys in tracked files | ☐ | Needs a `git grep` in CI |
| CO-5, single outbound host | ☐ | Needs a network trace in CI |

## 7. Observability

Logged today: one JSONL line per check with finding id, claims, verdicts, confidence, overall risk. Not logged: token counts, cost, latency, model version per call, retrieval hits per claim. Adding model version and retrieval hits to the log line would make every verdict re-performable; that is the first observability change to make.
