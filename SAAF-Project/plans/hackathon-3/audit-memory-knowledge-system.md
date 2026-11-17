# Audit Memory and Knowledge System

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

Audit knowledge lives in individual auditors' heads and disconnected document stores. When an auditor encounters a control weakness, there is no easy way to check: "Have we seen this before? What did we recommend last time? Which framework does this map to?"

The result: duplicate findings, inconsistent recommendations, and failure to detect cross-audit patterns — for example, the same access management weakness appearing in three separate audits across two years, never recognized as a systemic issue.

This plan builds a personal/team audit knowledge system where audit notes, findings, and transcriptions are automatically indexed and queryable by Claude agents.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Knowledge Management / Cross-Audit Intelligence

**Applicable standards:**

- IIA IPPF — Standard 2050 (Coordination and Reliance), 2600 (Communicating the Acceptance of Risks)
- ISO 27001 — A.7.2.2 (Information security awareness and training)

**In scope:**

- Obsidian vault as structured audit note store (markdown files, linked by tag and backlink)
- Vector database (ChromaDB) for semantic search over the vault
- Claude querying the knowledge system during active audits
- Auto-indexing: new notes pushed to vector DB on save (via Obsidian plugin or watcher script)
- Pattern detection: identify recurring findings across audits

**Out of scope:**

- Centralized multi-org knowledge sharing (each org runs their own vault; federation is future)
- Real-time collaborative editing (Obsidian is single-user or small team)
- Legal/compliance document management (use a DMS for that)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Query prompt for pattern detection; note-to-finding extraction prompt |
| **Tools** | `tools/scripts/index-audit-vault.py` — watches vault, embeds new/modified notes into ChromaDB |
| **Regulatory** | IIA 2050 coordination — knowledge system supports cross-audit reliance |
| **Outputs** | Pattern report: recurring findings across audits; cross-audit risk heatmap |

---

## 5. Prompts

### System prompt (draft)

```
You are an audit knowledge assistant with access to a vector database of past audit notes and findings.
When an auditor asks a question, search the knowledge base for relevant precedents and patterns.
Always cite the source note (file name and date) for any retrieved information.
If multiple notes describe similar findings, identify the pattern explicitly.
Never fabricate precedents — only report what is in the knowledge base.
Flag when a question has no relevant precedent (knowledge gap).
```

### Example user prompts

**Prompt 1 — Precedent lookup:**
```
We found that Vendor X has no formal offboarding process for system access.
Have we raised a similar finding before? If yes, what was our recommendation and what framework did we cite?
```

**Prompt 2 — Pattern detection:**
```
Analyze the last 24 months of audit notes tagged #access-management.
Identify any recurring themes or findings that appear in 3 or more audits.
Produce a pattern summary with risk rating and recommended systemic response.
```

**Intended file location:** `prompts/audit-use-cases/audit-memory-query.md`

---

## 6. Tools and Techniques

### Approach

Obsidian stores audit notes as markdown files with YAML frontmatter (audit name, date, domain, risk tags). A Python watcher script monitors the vault directory for new or modified files. When a change is detected, the script embeds the file content using Nomic embed text v1.5 (local) and upserts it into ChromaDB with metadata.

Claude queries the ChromaDB collection using semantic search, retrieves the top-k relevant notes, and synthesizes a response with source citations.

Pattern detection runs as a weekly batch: Claude retrieves all notes for a given domain tag, clusters findings semantically, and flags recurring patterns with a count and risk assessment.

### Example script or pseudocode

```python
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
import time, hashlib, yaml, re

VAULT_PATH = Path.home() / "ObsidianVault" / "Audit"
DB_PATH = Path("data/audit-memory-db")

chroma = chromadb.PersistentClient(path=str(DB_PATH))
collection = chroma.get_or_create_collection("audit-notes")
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

def embed_note(path: Path):
    text = path.read_text()
    # Extract YAML frontmatter
    meta = {}
    if text.startswith("---"):
        end = text.index("---", 3)
        meta = yaml.safe_load(text[3:end])
        text = text[end+3:].strip()
    doc_id = hashlib.md5(str(path).encode()).hexdigest()
    embedding = model.encode(text).tolist()
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"file": str(path), "audit": meta.get("audit", ""), "domain": meta.get("domain", "")}]
    )
    print(f"  Indexed: {path.name}")

def watch_vault():
    seen = {}
    while True:
        for f in VAULT_PATH.rglob("*.md"):
            mtime = f.stat().st_mtime
            if seen.get(str(f)) != mtime:
                embed_note(f)
                seen[str(f)] = mtime
        time.sleep(30)

def query(question: str, n: int = 5) -> list[dict]:
    emb = model.encode(question).tolist()
    results = collection.query(query_embeddings=[emb], n_results=n)
    return [{"text": d, "meta": m}
            for d, m in zip(results["documents"][0], results["metadatas"][0])]
```

**Tech stack used:** Python 3.9+, ChromaDB, Nomic embed text v1.5 (local), Obsidian (markdown vault), Claude API (query synthesis)

**Intended file location:** `tools/scripts/index-audit-vault.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2050 | Coordination and Reliance — knowledge system enables cross-audit reliance with traceability |
| IIA IPPF 2600 | Communicating acceptance of risks — pattern detection surfaces systemic risks to management |
| ISO 27001 A.8.19 | Installation of software on operational systems — vault watcher runs as user-space script |

### Claude / AI tool usage notes

The Obsidian vault is a local-first system. ChromaDB runs locally. Embeddings are computed by Nomic embed text v1.5 running on-device — no data leaves the machine. Claude queries are made against retrieved text snippets only; the full vault never leaves the local environment unless the auditor explicitly shares it.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown (pattern report) + JSON (finding list with precedent citations)

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output (pattern report)

```markdown
## Pattern: User Access Not Revoked on Departure

**Occurrences:** 4 audits (2024-Q3, 2025-Q1, 2025-Q2, 2025-Q4)
**Domains:** Access Management, HR Integration
**Risk rating:** High (recurring, not remediated)

**Observed pattern:** In all 4 audits, terminated employees retained active system access for
more than 30 days after HR offboarding. The root cause in 3 of 4 cases was the absence of
automated provisioning integration between the HRIS and identity provider.

**Previous recommendation (2024-Q3):** Implement automated deprovisioning trigger via HRIS API.
**Current status:** Not implemented in 3 of 4 organizations.

**Framework references:** ISO 27001 A.9.2.6, DORA Art. 8(5), IIA GTAG Access Management
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] ChromaDB (local vector store)
- [x] Nomic embed text v1.5 (local embedding model)
- [x] Obsidian (note-taking — optional; any markdown folder works)
- [x] Claude API (pattern synthesis queries)

**Stretch goals:**

- [ ] Obsidian plugin that embeds notes on save (no separate watcher script)
- [ ] Cross-org federation: encrypted vault sync between participating SAAF organizations
- [ ] Automated pattern alert: email/Slack when a new finding matches a known pattern

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `index-audit-vault.py` watcher and query script
- Obsidian vault template (folder structure, YAML frontmatter schema for audit notes)
- System prompt for knowledge base queries

**Help requested:**

- Auditors with Obsidian experience: validate that the note structure fits real audit workflows
- Engineers: build the Obsidian plugin variant (JavaScript/TypeScript)
- Vaktechniek: validate that pattern detection output meets IIA quality requirements

**Cross-org interest:**

This plan complements `saaf-rag-knowledge-base.md` (which focuses on regulatory documents). The audit memory system focuses on organizational experience — findings, precedents, and patterns from past audits. These are complementary layers.

**Related SAAF plans:**

- [`saaf-rag-knowledge-base.md`](saaf-rag-knowledge-base.md) — shared regulatory document RAG (complementary)
- [`the-control-freaks-uc7-rcm-builder.md`](../hackathon-2/the-control-freaks-uc7-rcm-builder.md) — RCM outputs become audit memory inputs
- [`frank-van-dissel-uc2-previous-audit-intelligence.md`](../hackathon-2/frank-van-dissel-uc2-previous-audit-intelligence.md) — predecessor pattern

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Architecture designed; vault schema defined |
| **Do** | In progress | Hackathon #3: implement watcher + ChromaDB indexing on sample vault |
| **Check** | Not started | Validate retrieval quality: does semantic search return relevant precedents? |
| **Act** | Not started | Target: daily vault indexing for one pilot organization post-H3 |

---

## 12. Open Questions

1. Should the vault be a shared team resource or remain per-auditor? Privacy implications differ.
2. How do we handle finding confidentiality — can patterns be shared across organizations without revealing client data?
3. What is the minimum vault size (number of notes) before semantic search becomes useful?
4. Should ChromaDB be replaced with a hosted vector DB (Pinecone, Weaviate) for team sharing?
