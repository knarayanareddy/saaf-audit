# Hallucination Detection Agent

A post-processing skill that validates AI-generated audit findings against a regulatory knowledge base, flagging unsupported or hallucinated claims before they enter the audit dossier.

Parent plan: [llm-hallucination-detection-agent.md](../../../../plans/hackathon-3/llm-hallucination-detection-agent.md)
Execution plan: [table-9-execution-plan.md](../../../../plans/hackathon-3/table-9-execution-plan.md)

## Pipeline

```
                +----------------+
  finding.json  |                |
  ------------->| finding_io     |
                |  load_finding  |
                +--------+-------+
                         |
                         v
                +--------+-------+
                | extractor      |   1 Haiku 4.5 call
                |  extract_claims|   -> list[Claim]
                +--------+-------+
                         |
                         v
                +--------+-------+
                | rag            |   ChromaDB (if available)
                | retrieve_ctx   |   else markdown corpus
                +--------+-------+
                         |
                         v
                +--------+-------+
                | verifier       |   1 Sonnet 4.6 call
                |  verify_claims |   -> list[ClaimVerdict]
                +--------+-------+
                         |
                         v
                +--------+-------+
                | aggregator     |   pure Python rules
                |  aggregate     |   -> RiskAssessment
                +--------+-------+
                         |
                         v
                +--------+-------+
                | annotator      |   write back + JSONL log
                |  check_finding |
                +--------+-------+
                         |
                         v
                annotated finding JSON
                + outputs/logs/hallucination-checks.jsonl (appended)
```

Total: **2 API calls per finding**, regardless of claim count (D3).

## Claim types (extractor output)

| Type | Example | Verifiable via RAG? |
|---|---|---|
| `standard_reference` | "ISO 27001 clause 8.2.3" | Yes |
| `control_name` | "Access Control Policy A.9.1" | Yes |
| `date_threshold` | "patches must be applied within 30 days" | Sometimes |
| `numeric_value` | "95% uptime SLA" | Sometimes |
| `system_name` | "SAP SuccessFactors" | Name-existence only (usually skipped) |
| `other` | narrative text | No — skipped |

## Risk scoring (aggregator)

| Condition | Overall risk | Warning? | Blocked? |
|---|---|---|---|
| Any claim `LIKELY_HALLUCINATED` with `confidence=High` | HIGH | Yes | **No (D2)** |
| `>= 2` claims `UNVERIFIED` | MEDIUM | Yes | No |
| All claims `SUPPORTED` (or no verifiable claims) | LOW | No | No |

**Decision D2**: HIGH risk triggers a warning only. It does not block the finding from the dossier. The auditor decides what to do. This matches IIA Standard 2310 — auditor retains responsibility for evidence.

## Decision log

| ID | Decision | Rationale |
|---|---|---|
| D1 | Markdown RAG fallback ships with the code | ChromaDB (Track 0) may not be ready. Tool must work standalone. |
| D2 | HIGH risk = warn, never block | Auditor judgement is final; matches "second pair of eyes" track mission. |
| D3 | 2 calls per finding (Haiku extract, Sonnet batched verify) | ~70% cost reduction vs. naive per-claim verification. |
| D4 | Documentation-first; prompts as markdown files | Track mandate. Every commit is a handoff to another SAAF org. |
| D7 | BYOK — zero keys committed, env var only | OWASP A02. Enforced in `claude_client.get_api_key()`. |

Full rationale in [table-9-execution-plan.md §0.2](../../../../plans/hackathon-3/table-9-execution-plan.md).

## Running

```bash
cd tools/scripts/track-5
cp .env.example .env       # edit .env, paste your Anthropic key
pip install -r requirements.txt
python -m hallucination dummy_data/sample_findings/F-0001.json
```

Expected output: `F-0001_checked.json` next to the input (original + `hallucination_check` field) and a new line in `outputs/logs/hallucination-checks.jsonl`.

## Testing against seeded hallucinations

The `dummy_data/sample_findings/` folder contains 5 findings:

- **F-0001, F-0002** — contain deliberate hallucinations. The tool MUST flag at least one claim in each (`overall_risk=HIGH`). If not, something is broken (prompt, RAG, or model).
- **F-0003, F-0004, F-0005** — clean findings. The tool should return `overall_risk=LOW` (may return MEDIUM if RAG lookup is weak; never HIGH).

See [`dummy_data/sample_findings/README.md`](./dummy_data/sample_findings/README.md) for the specific seeded hallucinations.

## Module index

| File | Role |
|---|---|
| `cli.py` | CLI entry point (`python -m hallucination <finding.json>`) |
| `annotator.py` | Orchestrator + JSONL logger. Main programmatic entry: `check_finding()`. |
| `extractor.py` | S2 — claim extraction via Haiku |
| `verifier.py` | S3 — batched claim verification via Sonnet |
| `aggregator.py` | S4 — rule-based risk score (pure Python) |
| `rag.py` | RAG lookup (ChromaDB + markdown fallback) |
| `claude_client.py` | Anthropic SDK wrapper with prompt caching + API-key enforcement |
| `finding_io.py` | Load / save finding-schema.json files |
