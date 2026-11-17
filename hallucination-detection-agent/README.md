# Track 5 — AI Governance & QA Tools

Tools for the SAAF Track 5 mission: validate outputs from other tracks for accuracy, security, and auditor-defensibility.

## What's here

| Tool | Purpose | Status |
|---|---|---|
| [`hallucination/`](./hallucination/) | Claim-extract → RAG-verify pipeline. Flags unsupported or hallucinated claims in AI-generated audit findings. | Built at Hackathon 3 |

## Prerequisites

- Python 3.10+
- An **Anthropic API key** — this tool is BYOK (Bring Your Own Key). See [API Key Setup](#api-key-setup) below.
- `pip install -r requirements.txt`

## Quickstart

```bash
cd tools/scripts/track-5
cp .env.example .env              # then edit .env and paste your key
pip install -r requirements.txt
python -m hallucination dummy_data/sample_findings/F-0001.json
```

## API Key Setup

**This code does not ship with an API key. You must provide your own.**

The code reads `ANTHROPIC_API_KEY` from the environment. If missing, it fails fast with a clear error.

Two ways to set it:

**Option A — `.env` file (recommended for local dev):**
1. `cp .env.example .env`
2. Edit `.env`, replace the placeholder with your real key (`sk-ant-...`).
3. The file is already in `.gitignore` — it will never be committed.

**Option B — shell environment variable:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```
Add to `~/.zshrc` or `~/.bashrc` to persist across sessions.

### Get a key

Go to [console.anthropic.com](https://console.anthropic.com) → Settings → API Keys → Create key. Note: API usage is billed separately from your Claude Pro/Max subscription.

### For organizations adopting this tool

You (the adopting org) must supply your own `ANTHROPIC_API_KEY` via your secrets manager, CI variable, or environment. **This tool ships with zero embedded credentials.** This is a deliberate security posture (OWASP A02 — Cryptographic Failures).

## Folder layout

```
tools/scripts/track-5/
├── README.md                       This file
├── requirements.txt
├── .env.example                    Placeholder env file (safe to commit)
└── hallucination/                  Hallucination-detection pipeline
    ├── README.md                   Architecture, claim types, decision log
    ├── __init__.py
    ├── cli.py                      python -m hallucination <finding.json>
    ├── extractor.py                S2 — claim extraction (Haiku)
    ├── verifier.py                 S3 — batched claim verification (Sonnet)
    ├── aggregator.py               S4 — rule-based risk scoring
    ├── annotator.py                S5 — write-back + JSONL log
    ├── rag.py                      RAG lookup (ChromaDB + markdown fallback)
    ├── claude_client.py            Claude API wrapper w/ prompt caching
    ├── finding_io.py               Load/save finding-schema.json
    └── dummy_data/
        ├── sample_findings/        5 findings — 2 with seeded hallucinations
        └── mini_rag_corpus/        Markdown regulatory snippets (fallback RAG)
```

## Related plans

- [plans/hackathon-3/table-9-execution-plan.md](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-3/table-9-execution-plan.md) — execution plan for Hackathon 3 Table 9.
- [plans/hackathon-3/llm-hallucination-detection-agent.md](https://github.com/SAAF-Project/SAAF-Project/blob/main/plans/hackathon-3/llm-hallucination-detection-agent.md) — parent plan (architecture + prompts).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `EnvironmentError: ANTHROPIC_API_KEY not set` | No key in env | See [API Key Setup](#api-key-setup) |
| `401 Unauthorized` from the API | Invalid / expired key | Rotate at console.anthropic.com |
| `429 Rate limit` | Too many calls in short window | Retry with back-off; batching reduces call count |
| RAG returns no context for known terms | ChromaDB not running → fallback to markdown; markdown corpus missing file | Check `hallucination/dummy_data/mini_rag_corpus/` |
