# `AUDIT-CRITERIA.md` — RCM Builder

> The README says *what the agent does and how to run it*; this document says *what the agent must be judged against as an auditee* — its control objectives, testable acceptance criteria, and known limits.
>
> SAAF standard (A2 — Audit Criteria & Controls track). A1 stress-test teams verify RCM Builder against exactly the acceptance criteria below. Findings, where the pipeline produces them, conform to `outputs/schemas/finding-schema.json` in the main SAAF-Project repo; frameworks are drawn from `docs/reference/domains-and-frameworks.md`.

---

## Metadata

| Field | Value |
|---|---|
| **Agent** | RCM Builder |
| **Repository** | https://github.com/SAAF-Project/RCM-Builder |
| **Maintainer(s)** | RCM Builder team (SAAF Hackathon) |
| **Last reviewed** | 2026-09-15 |
| **Status** | Reviewed |

## 1. What the agent does

RCM Builder is a deterministic, three-stage Python pipeline — **no LLM in the scoring or control-design path**. It ingests raw audit risk data (UC2–UC5 collections: historical findings, incidents, fraud scenarios, regulatory risks) and a separate IT dependency matrix, and produces a Risk Control Matrix: risks normalized into Cause→Event→Impact form, mitigating controls drafted per risk, inherent and residual risk scored, and control reliability validated against IT General Controls (ITGC) and IPE (Information Produced by the Entity) evidence. Output is JSON (schema-validated) and Markdown, feeding the downstream Audit Work Program Agent (UC8). A separate prompt (`prompts/audit-use-cases/rcm-builder-agent.md`) documents the same logic for LLM-assisted use, but the shipped pipeline (`tools/scripts/rcm_builder.py`, `rcm_it_validator.py`) is pure rule-based code.

## 2. Control objectives & framework mapping (5)

| Control objective | Framework + clause/area | Why relevant |
|---|---|---|
| **CO-1 — Risk statements are complete and evidence-based, never fabricated.** The pipeline must refuse to synthesize a risk statement when the source item carries no risk content, rather than inventing one. | IIA Standards (sufficiency of evidence, Std. 13.3) | Auditors rely on the RCM as a record of what was actually reported, not model-generated content. A silently invented risk undermines the whole matrix. |
| **CO-2 — Deduplication preserves full source traceability.** Merging semantically overlapping risks (fuzzy match ≥65%, same process context) must never drop a contributing source's reference. | COSO ERM (risk identification & aggregation) / IIA Std. 2320 | An auditor tracing a control back to its origin (an incident ticket, a regulation) must be able to reconstruct every source that fed a merged risk. |
| **CO-3 — No orphan risks: every risk carries at least one mapped control.** Risks with zero controls must be explicitly flagged as a design gap, not silently included or dropped. | COSO 2013 Internal Control — Integrated Framework (control activities) / IIA Std. 2201 | An unmitigated risk hidden inside a "complete-looking" matrix is worse than one flagged as a gap — it gives false assurance. |
| **CO-4 — Control reliability never exceeds what IT evidence supports.** Reliability must downgrade to *Unreliable* when IPE validation is Weak/None, and to *Not Assessed* when no IT dependency matrix entry exists for an IT-dependent control — never silently default to a favorable rating. | COBIT (ITGC domains: Access, Change, Operations) / SOx ICFR & ISAE 3402 (IPE reliability) | Placing reliance on a control whose underlying system or report was never validated is a classic overstatement-of-assurance failure mode in IT-dependent controls testing. |
| **CO-5 — Scoring is deterministic and reproducible.** Given identical input and IT matrix, inherent risk, residual risk, and control reliability must be bit-for-bit identical across runs — no randomness, no model variance. | EU AI Act Art. 13 (transparency) / IIA Std. 13.3 (reliable evidence) | An audit workpaper that can't be reproduced from the same inputs cannot be relied upon or defended under review. This is also RCM Builder's core differentiator versus an LLM-scored matrix. |

## 3. Acceptance criteria (testable, pass/fail)

**CO-1**
- Given a use-case risk item with none of `cause`/`risk_description`/`description`/`summary`/`event`/`impact` populated, the agent raises `ValueError` identifying the offending use case and item index — it does not emit a risk statement.
- Given a risk item with only `cause`, `event`, `impact` populated (no free-text description), the agent still produces a valid Cause→Event→Impact statement built from those three fields.

**CO-2**
- Given two risk items from different `risk_source` values (e.g. an incident and a historical finding) describing the same underlying risk within the same sub-process, the output contains exactly one canonical risk entry whose `source_use_cases`, `risk_sources`, and `source_references` include both originals.
- Given two risks with high textual similarity but different `process_id`/`sub_process_id`, the agent does **not** merge them (context match is required alongside text similarity). Limitation, stated honestly: dedup merges across contexts when either risk has no `sub_process_id`, so this criterion holds only when both risks carry one.

**CO-3**
- Given a risk that resolves to zero drafted controls, `quality_checks.mapping_integrity.passed` is `false` and the risk's ID appears in `orphan_risk_ids`.
- Given a risk with only "Weak"-effectiveness controls, `stage2.design_gap` is `true` with `design_gap_type: "Weak"`.

**CO-4**
- Given an IT-dependent control with no matching entry in `it_dependency_matrix`, `control_reliability` is `"Not Assessed"` and `additional_itgc_control_required` is `true`.
- Given a matrix entry where `ipe_details.ipe_reliability` (or its computed equivalent) is `"Weak"` or `"None"`, the dependent control's `control_reliability` is `"Unreliable"` and `reliability_downgraded` is `true`, regardless of the control's design effectiveness.
- Given a non-IT-dependent control with `control_design_effectiveness: "Strong"`, `control_reliability` maps to `"Reliable"` without requiring an IT matrix entry.

**CO-5**
- Given the same `--input` and `--it-matrix` files run twice, the two `--out-json` outputs are identical except for the `generated_at` timestamp field.
- The output JSON validates against `outputs/schemas/rcm-schema.json` on every run when the schema file is present (enforced by `main()`; `test_run_pipeline_output_validates_against_schema`); if it is missing, `main()` warns and skips validation.

## 4. Good output / never do

| A correct output MUST contain | The agent must NEVER |
|---|---|
| ✓ Every risk expressed as "As a result of [Cause], there is a risk that [Event], leading to [Impact]." | ✕ Invent process context, risk content, or evidence not present in the source input |
| ✓ Every merged risk's full list of contributing `source_use_cases` / `risk_sources` / `source_references` | ✕ Create duplicate risk entries for semantically identical risks |
| ✓ At least one mapped control per risk, or an explicit `design_gap` flag when none exists | ✕ Leave an orphan risk (a risk with no linked control and no flag) |
| ✓ Control reliability consistent with the underlying IPE/ITGC evidence in the IT matrix (findings conform to `finding-schema.json` shape where the agent emits a UC6 finding) | ✕ Assume "Reliable" control reliability without explicit IT dependency evidence |
| ✓ Identical inherent/residual scores for identical inputs across repeated runs | ✕ Hard-code credentials, API keys, or secrets — none used or required by this pipeline |
| ✓ `--title` and all user-supplied CLI/report text HTML-escaped in `export_html.py` output | ✕ Emit raw, unescaped user-supplied text into HTML output (open gap: `--title` is not yet escaped on main; the fix is pending in #3) |

## 5. Coverage gaps

Honest limits an auditor would reasonably expect this agent to address, that it currently does not (or only partly does):

- **No prompt-injection guidance for the LLM-assisted companion prompt.** `prompts/audit-use-cases/rcm-builder-agent.md` instructs an LLM operator on RCM-building logic but has no explicit instruction to treat risk-description text as *data, not instructions* (OWASP LLM01 — Prompt Injection). If this prompt is ever used to feed an LLM with untrusted third-party risk text (e.g. scraped incident tickets), a crafted description could attempt to steer the model's classification or control design. The deterministic Python pipeline itself is not exposed to this risk — only the parallel prompt-based workflow is.
- **No automated CI enforcement of the 25-test suite.** Tests exist and pass locally (`pytest tests/ -v`), but there is no `.github/workflows/` — nothing blocks a PR that breaks scoring logic or schema conformance from being merged. An auditor would expect regression tests to run on every change (COBIT change management / SOx ICFR).
- **Dependencies are unpinned above a floor (`>=`).** `requirements.txt` sets minimum versions only (`jsonschema>=4.21.0`, `rapidfuzz>=3.6.0`, `pytest>=8.0.0`), with no upper bound or lockfile. A supply-chain or breaking-change risk if a dependency publishes an incompatible major version (ISO 27001 A.8.28 — secure coding / dependency management).
- **No access control or run-provenance logging.** As a local CLI tool this is by design, but there is nothing recording *who* ran the pipeline with *which* inputs and *when* — relevant if RCM Builder output is later relied upon as audit evidence (see Observability, below).
- **Fuzzy-dedup similarity threshold (0.65) is not independently stress-tested at the boundary.** Unit tests cover clear-merge and clear-no-merge cases; adversarial or near-threshold inputs (e.g. deliberately reworded risk text intended to dodge deduplication) are not covered.
- **UC6-derived risks use fixed placeholder scoring** (`inherent_impact: 4, inherent_likelihood: 3` always) rather than deriving severity from the specific IT gap found. This is a known simplification, not a bug — flagged here so it isn't mistaken for validated scoring.

## 6. Observability

**Logged/traced today:** Nothing beyond what's implicit in the output artifacts themselves — `warnings[]` (structural/mapping/taxonomy issues) and `quality_checks{}` inside the RCM JSON output, and print statements to stdout during a `main()` run ("Schema validation: PASSED", output file paths). There is no structured run log, no timestamped audit trail of individual pipeline decisions, and no record of which `--input`/`--it-matrix` file versions produced a given output beyond the single `generated_at` field.

**Missing:** A run manifest (input file hashes, matrix version, pipeline version, operator identity) that would let an auditor reproduce or attest to a specific RCM output later; structured logging of dedup-merge decisions (which risks were merged into which, and why) beyond what survives in `source_references`; and any record of `main()` invocations for accountability if the tool is used in a shared environment.

## 7. Status / validation

| Acceptance criterion | Verified? | Evidence |
|---|---|---|
| CO-1 #1 (raises `ValueError` on empty risk content) | ☑ | `parse_use_cases` explicit check; not directly unit-tested by name but exercised via required-field checks |
| CO-1 #2 (builds statement from cause/event/impact fields) | ☑ | `test_normalize_risk_produces_canonical_statement` |
| CO-2 #1 (dedup preserves traceability) | ☑ | `test_deduplicate_risks_merges_traceability_metadata` |
| CO-2 #2 (no merge across mismatched process context) | ☐ | Not independently unit-tested |
| CO-3 #1 (orphan risk flagged) | ☑ | `test_build_draft_rcm_flags_unmapped_control_design`, `_assess_mapping_integrity` logic |
| CO-3 #2 (weak-only controls → design gap) | ☑ | Covered by `_evaluate_design_gap` logic path; no dedicated named test |
| CO-4 #1 (missing matrix entry → Not Assessed) | ☑ | `test_apply_it_validation_creates_uc6_risk_for_missing_matrix_entry` |
| CO-4 #2 (weak/none IPE → Unreliable + downgrade flag) | ☑ | `test_derive_control_reliability_downgraded_on_weak_ipe` |
| CO-4 #3 (strong non-IT control → Reliable) | ☑ | `test_derive_control_reliability_reliable_for_strong_preventive_key_control` |
| CO-5 #1 (byte-identical repeat runs) | ☐ | Not directly tested; logically follows from absence of randomness in the code path — recommend adding an explicit idempotency test |
| CO-5 #2 (schema validation on every run) | ☑ | `test_run_pipeline_output_validates_against_schema` |
