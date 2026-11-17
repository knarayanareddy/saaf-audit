# Mini RAG Corpus — Fallback Regulatory Knowledge Base

10 hand-curated markdown snippets used by `rag.py` when ChromaDB (the intended primary backend) is unavailable.

**Provenance:** Synthesised during Hackathon 3 (21 April 2026) by the Track 5 build pod. Content is paraphrased from publicly available regulatory texts (ISO/IEC standards, EU regulations, IIA Standards). Not a substitute for authoritative texts — **this corpus is a demo fixture, not a compliance reference**.

---

## Inventory

| File | Covers | Purpose in the test set |
|---|---|---|
| [`iso-27001-clause-8-structure.md`](./iso-27001-clause-8-structure.md) | ISO/IEC 27001:2022 clause 8 main-body structure + note that clauses like 8.9.4 do NOT exist | **Defeats the F-0001 seeded hallucination** (fake clause 8.9.4). Also clarifies that 24-hour incident-reporting mandates come from GDPR/NIS2/DORA, not ISO 27001. |
| [`iso-27001-annex-a-8-8.md`](./iso-27001-annex-a-8-8.md) | Annex A.8.8 (Management of technical vulnerabilities) — control text + ISO 27002 guidance | Supports clean finding F-0003 (vulnerability management). Notes that ISO does NOT prescribe 30/60/90-day SLAs — those are organisational. |
| [`gdpr-article-5.md`](./gdpr-article-5.md) | GDPR Article 5 (Principles), with explicit note that **data minimisation is in Article 5(1)(c)** | Provides the correct location of the data-minimisation principle — key to catching the F-0002 seeded hallucination which misattributes it to Article 47. |
| [`gdpr-article-32.md`](./gdpr-article-32.md) | GDPR Article 32 (Security of processing — encryption, confidentiality, integrity, availability) | Supports clean finding F-0004 (encryption at rest). Notes Article 32 does NOT prescribe specific algorithms or review cycles. |
| [`gdpr-article-47.md`](./gdpr-article-47.md) | GDPR Article 47 (Binding Corporate Rules) — actual scope + explicit note that it is NOT the data-minimisation article | **Defeats the F-0002 seeded hallucination** by explicitly refuting the wrong attribution of data minimisation to Article 47. |
| [`dora-article-9.md`](./dora-article-9.md) | DORA (Reg. (EU) 2022/2554) Article 9 — ICT protection and prevention for financial entities | Reference framework for ICT risk-management findings that may cite DORA. Clarifies that breach notification is in Art 19, not Art 9. |
| [`iia-standard-2310.md`](./iia-standard-2310.md) | IIA Standard 2310 — Identifying Information (sufficient, reliable, relevant, useful) + application to AI-generated findings | Supports clean finding F-0005 (audit workpaper evidence traceability). Provides the audit-defensibility anchor for the whole tool. |
| [`iia-standard-1220.md`](./iia-standard-1220.md) | IIA Standard 1220 — Due Professional Care + application to AI-assisted work | Referenced by the parent plan's regulatory pillar; ensures verifier understands IIA citation context. |
| [`eu-ai-act-article-13.md`](./eu-ai-act-article-13.md) | EU AI Act (Reg. (EU) 2024/1689) Article 13 — transparency and instructions for use of high-risk AI | Directly relevant to the hallucination detector itself (it is a transparency/quality control for high-risk AI audit output). |
| [`owasp-llm-top-10.md`](./owasp-llm-top-10.md) | OWASP Top 10 for LLM Applications (2025) — the 10 categories with short descriptions | Context for Track 5's OWASP run task, and makes explicit that this tool is an operational control for LLM09 (Misinformation). |

---

## Selection rationale

Every snippet in this corpus exists for one of three reasons:

1. **To defeat a specific seeded hallucination.** The `iso-27001-clause-8-structure.md` and `gdpr-article-47.md` files explicitly refute the two seeded claims — their inclusion is mandatory for the demo to succeed.
2. **To cover the regulatory citations used in the clean sample findings.** `iso-27001-annex-a-8-8.md` (F-0003), `gdpr-article-32.md` (F-0004), `iia-standard-2310.md` (F-0005).
3. **To provide broader coverage relevant to the SAAF community.** DORA, IIA 1220, EU AI Act, OWASP — included so auditors from different domains see their framework represented. Not all are exercised by the current sample findings; they are there to make the corpus useful for future findings.

## What this corpus is NOT

- **Not authoritative.** Paraphrased for readability; always consult the real standards for compliance work.
- **Not comprehensive.** ~10 snippets covering the small set of frameworks the sample findings reference. Real-world deployment needs hundreds of documents (full ISO 27001 annex A, full GDPR, full DORA, etc.) ingested via ChromaDB.
- **Not a substitute for Track 0's ChromaDB.** When Track 0's regulatory RAG is available, `RAG_BACKEND=chromadb` should be preferred — semantic search significantly beats keyword matching on ambiguous queries.

## Adding new snippets

1. Create `<framework>-<identifier>.md` in this folder (one file per logical unit — a clause, an article, a standard).
2. Write short, faithful paraphrase of the source. Include explicit "is / is NOT" notes where relevant — those are the most useful anchors for the verifier.
3. No need to register the file anywhere — `rag.py` globs `*.md` in this folder automatically.
4. Update this README's inventory table.

## Replacing with ChromaDB

See `rag.py::_chromadb_lookup`. Set `RAG_BACKEND=chromadb` plus `CHROMADB_HOST` / `CHROMADB_PORT` env vars; the rest of the pipeline is untouched. Ensure the ChromaDB collection is named `saaf-regulatory` (matches the `_chromadb_lookup` code) or update the constant in one place.
