# SAAF Shared RAG Knowledge Base

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Skill |
| **Status** | Draft |

---

## 2. Problem Statement

Every SAAF participant building an audit agent faces the same bootstrapping problem: they need a knowledge base of audit standards, frameworks, policies, and procedures that their agent can retrieve context from. Currently:

- Each participant builds their own RAG pipeline from scratch (ChromaDB, OpenAI embeddings, etc.)
- There is no shared corpus of audit documents — everyone embeds their own copy of ISO 27001, GDPR, DORA, etc.
- Embedding quality varies; some participants use keyword search, others use semantic search, without a shared baseline
- Participants at Mollie specifically want to test RAG with real (synthetic) audit documentation before Hackathon #3

The result: significant duplicated effort, inconsistent retrieval quality, and no shared benchmark.

This plan creates a **shared RAG infrastructure** for the SAAF community: a curated document corpus, a standardised embedding pipeline, and a simple retrieval API that any SAAF agent can query.

---

## 3. Use-Case Type and Scope

**Audit domain:** Cross-domain — shared RAG infrastructure

**Applicable standards:**

- All SAAF-relevant frameworks: ISO 27001, GDPR, DORA, COBIT, ITIL, SOx, NIS2, EU AI Act
- IIA Standards (IPPF)

**In scope:**

- Curated document corpus: publicly available regulatory texts, IIA standards summaries, SAAF reference documents
- Embedding pipeline: chunking strategy, embedding model selection (Nomic or OpenAI), vector DB setup (ChromaDB local, Qdrant cloud)
- Retrieval API wrapper: simple Python function `saaf_rag.query(question, domain_filter=None)` callable from any SAAF agent
- Test harness: 20 benchmark questions with expected answers to measure retrieval quality
- Mollie pilot: test RAG on a set of synthetic Mollie audit documents during Hackathon #3

**Out of scope:**

- Real customer data or internal Mollie audit reports (synthetic only)
- Production hosting (v1 = local ChromaDB, Qdrant cloud as stretch)
- Fine-tuning LLMs on the corpus (retrieval only, generation via Claude API)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | RAG-aware system prompt template: "You are an audit assistant. Answer based on the following retrieved context: {context}. If the context does not contain enough information, say so." |
| **Tools** | Python package/module: `tools/saaf_rag/` — ingest, embed, query functions; ChromaDB collection setup script; benchmark evaluation script |
| **Regulatory** | The corpus itself: publicly available regulatory texts (DORA, EU AI Act, ISO 27001 summaries, IIA Standards IPPF); `docs/reference/` documents as retrieval sources |
| **Outputs** | Retrieved context chunks (JSON) passed to generating LLM; benchmark report (retrieval precision@k, MRR) |

---

## 5. Prompts

### System prompt (draft)

```
You are a SAAF audit agent with access to a shared knowledge base of audit standards,
regulatory frameworks, and SAAF project documentation.

You will receive retrieved context chunks relevant to the user's question.
Use only the provided context to answer. If the context is insufficient, clearly state
what information is missing and what source it would typically come from.

When citing a retrieved chunk, always include: document name, section, and page number
(if available).

Never fabricate regulatory article numbers or control references.
```

### Example user prompts

**Prompt 1 — Regulatory question with RAG:**
```
[System: Retrieved context chunks injected here by RAG pipeline]

Question: What are the key requirements under DORA Article 13 for ICT-related incident
classification? How does this differ from NIS2 incident reporting obligations?
```

**Prompt 2 — Control mapping with RAG:**
```
[System: Retrieved context chunks for ISO 27001 A.9 and NIST SP 800-63 injected here]

An auditor found that 15% of user accounts have not had their access reviewed in the past
12 months. The organisation claims ISO 27001 certification. Draft a finding using the
Condition / Criterion / Cause / Effect structure.
```

**Intended file location:** `prompts/audit-use-cases/rag-knowledge-base.md`

---

## 6. Tools and Techniques

### Approach

**Step 1 — Document corpus assembly:**

```
corpus/
  regulatory/
    dora-full-text.txt            (public domain)
    eu-ai-act-full-text.txt       (public domain)
    iso27001-2022-summary.txt     (IIA-published summary, not full ISO text)
    gdpr-full-text.txt            (EUR-Lex public domain)
    ippf-standards-summary.txt    (IIA IPPF summaries)
  saaf/
    docs/reference/*.md           (symlinked from this repo)
    plans/hackathon-2/*.md        (all submitted plans)
    plans/hackathon-3/*.md        (all submitted plans)
  synthetic/
    mollie-access-review-policy.txt   (synthetic)
    mollie-change-management-sop.txt  (synthetic)
```

**Step 2 — Chunking strategy:**

- Chunk size: 512 tokens, 50-token overlap
- Metadata per chunk: `{source_file, section_heading, chunk_index, domain_tags[]}`
- Domain tagging: Claude classifies each chunk into 1-3 audit domains from the 53-domain taxonomy

**Step 3 — Embedding:**

```python
from chromadb import Client
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5")  # 768-dim, local

def ingest(chunks: list[dict]) -> None:
    collection = client.get_or_create_collection("saaf_kb")
    collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
        embeddings=[model.encode(c["text"]).tolist() for c in chunks],
        ids=[c["id"] for c in chunks],
    )

def query(question: str, domain_filter: str = None, n_results: int = 5) -> list[dict]:
    where = {"domain_tags": {"$contains": domain_filter}} if domain_filter else None
    results = collection.query(
        query_embeddings=[model.encode(question).tolist()],
        n_results=n_results,
        where=where,
    )
    return results["documents"][0]
```

**Tech stack used:** Python 3.9+, `chromadb` (local v1), `sentence-transformers` (Nomic embed text v1.5, local), Claude API (chunk domain tagging + answer generation), optionally `qdrant-client` for cloud deployment

**Intended file location:** `tools/saaf_rag/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GDPR Art. 32 | Processing security — ensure corpus contains no real PII |
| ISO 27001 A.8.10 | Information deletion — clear process for removing documents from corpus |

### Claude / AI tool usage notes

- Corpus contains only public domain regulatory texts and synthetic SAAF documents.
- No real audit evidence, personal data, or confidential customer information in the corpus.
- Embedding model (Nomic) runs locally — no data sent externally for embeddings.
- Answer generation uses Claude API — only retrieved chunks (public text) are sent.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (retrieved chunks) + Markdown (generated answer with citations)

**Schema reference:** N/A (retrieval infrastructure, not audit findings)

### Synthetic example — query result

```json
{
  "question": "What does DORA require for ICT incident classification?",
  "retrieved_chunks": [
    {
      "source": "dora-full-text.txt",
      "section": "Article 13 — Classification of ICT-related incidents",
      "text": "Financial entities shall classify ICT-related incidents and shall determine their impact...",
      "relevance_score": 0.94
    },
    {
      "source": "plans/hackathon-2/frank-van-dissel-uc3-incident-issue-intelligence.md",
      "section": "Section 7 — Regulatory",
      "text": "DORA Art. 13 requires classification by impact on (a) number of clients affected...",
      "relevance_score": 0.87
    }
  ],
  "generated_answer": "Under DORA Article 13, financial entities must classify ICT incidents by: (1) number of clients affected, (2) duration, (3) geographic spread, (4) data losses. Major incidents must be reported to competent authorities. [Source: DORA Art. 13]"
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] `chromadb` (local vector DB)
- [x] `sentence-transformers` (Nomic embed text v1.5, local)
- [x] Claude API (claude-sonnet-4-6 — answer generation)
- [x] Python 3.9+
- [ ] Corpus assembly script

**Stretch goals:**

- [ ] Qdrant cloud (shared instance accessible to all SAAF participants)
- [ ] LangChain or LlamaIndex abstraction layer
- [ ] Evaluation harness: 20 benchmark Q&A pairs with precision@k metric
- [ ] GitHub Actions: nightly corpus re-index when new plans are merged
- [ ] API endpoint (FastAPI) so non-Python agents can query the KB

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Corpus assembly script + document list
- ChromaDB ingest + query module (`tools/saaf_rag/`)
- Chunking strategy and metadata schema
- RAG-aware system prompt template
- 20-question benchmark dataset

**What help I'm looking for:**

- Mollie team: provide synthetic policy documents for the Mollie pilot (access review policy, change management SOP)
- Engineers: validate embedding model choice (Nomic vs. OpenAI vs. BGE)
- Vaktechniek: curate the benchmark Q&A pairs (authoritative answers to regulatory questions)

**Cross-org interest:**

This is the most cross-cutting infrastructure plan. Every SAAF agent that needs regulatory knowledge benefits from a shared, maintained knowledge base. This directly addresses one of the biggest barriers to building useful audit agents: the "where does the knowledge come from?" question.

**Video Transcription Insights (Hackathon #3 analysis):**

Three patterns from video analysis strengthen this plan:

1. **Content injection vs. RAG distinction**: Injecting large regulatory documents directly into the system prompt (context injection) is fragile — it consumes context window, cannot be updated dynamically, and forces every conversation to carry the full document. RAG is architecturally superior for PBC retrieval, regulatory lookups, and any knowledge that changes over time. Always prefer RAG over content injection for documents longer than 2,000 words.

2. **Obsidian vault as audit knowledge layer**: The `audit-memory-knowledge-system.md` plan shows that audit notes and past findings (stored in Obsidian) can be indexed into the same ChromaDB collection as the regulatory corpus. This creates a two-layer RAG: Layer 1 = regulatory standards (what should be done); Layer 2 = audit experience (what has been found). Combining both layers in a single retrieval call significantly improves finding quality.

3. **Harness layer > model choice**: Stanford research cited in transcriptions shows that the orchestration layer (tool calls, retrieval strategy, chunking, metadata filtering) explains 6× more variance in agent output quality than model selection. For this plan: invest in chunking strategy and metadata tagging before benchmarking different embedding models.

**Additional Corpus Sources (April 2026):**

Two new source types identified from the SAAF community should be added to the RAG corpus:

1. **Google Drive MCP Connector**: the SAAF community maintains a shared Google Drive with presentations, reference documents, and XLSX data (AI Sources, Domains, Skills). A Google Drive MCP server (available as an open-source MCP implementation) can automatically ingest new Drive files into the corpus whenever they are updated. This makes the Drive the live source-of-truth for SAAF reference material rather than requiring manual re-ingest.

2. **Vouch Web-of-Trust layer**: once the corpus contains contributions from multiple SAAF organizations, a quality signal is needed to weight sources. The "Vouch" web-of-trust pattern — where each organization cryptographically endorses chunks they have validated — provides this signal. Chunks endorsed by multiple organizations (e.g., a DORA Article 13 interpretation endorsed by 5 organizations) receive a higher retrieval weight than unvalidated chunks. This is a stretch goal for v2 but should be architected into the metadata schema now (`endorsers: list[str]` field in chunk metadata).

**Related SAAF plans:**

- [`plans/hackathon-3/saaf-strapi-synthetic-data.md`](saaf-strapi-synthetic-data.md) — synthetic Mollie documents can be included in the corpus
- [`plans/hackathon-3/saaf-jira-confluence-mcp.md`](saaf-jira-confluence-mcp.md) — Confluence pages (policies, SOPs) are candidate corpus sources
- [`plans/hackathon-2/linda-nyvelius-team-hightable.md`](../hackathon-2/linda-nyvelius-team-hightable.md) — TeamMate+ knowledge reuse is a related pattern
- [`docs/reference/ai-tools-and-techniques.md`](../../docs/reference/ai-tools-and-techniques.md) — RAG ecosystem overview with tool comparison
- [`plans/hackathon-3/audit-memory-knowledge-system.md`](audit-memory-knowledge-system.md) — complementary layer: past audit experience indexed alongside regulatory corpus

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Architecture defined; corpus assembled; embedding strategy chosen |
| **Do** | In progress | ChromaDB ingest + query wrapper at Hackathon #3; Mollie pilot |
| **Check** | Not started | Run 20-question benchmark; measure precision@5 |
| **Act** | Not started | Target: shared Qdrant instance live before Hackathon #4 |

---

## 12. Open Questions

1. Should the shared vector DB be Qdrant cloud (accessible to all participants) or ChromaDB local (each participant runs their own copy)?
2. Nomic embed text v1.5 runs fully locally (good for privacy) but requires ~270MB model download. Is this acceptable for all participants?
3. How do we handle corpus updates when new SAAF plans are merged? Manual re-ingest or automated?
4. What is the right chunking strategy for structured documents like ISO 27001 (which has hierarchical control numbering) vs. free-text like SAAF plans?
