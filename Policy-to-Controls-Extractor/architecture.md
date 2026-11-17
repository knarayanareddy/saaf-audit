The core idea is:

Large document
   ↓
Structural chunking
   ↓
Per-chunk extraction
   ↓
Central aggregation
   ↓
Normalization + deduplication
   ↓
Final control inventory

This is substantially more reliable than asking a model to process a 100-page policy corpus in one pass.

Why Chunking Works Better

Large-document single-pass extraction causes:

* context dilution
* missed controls
* merged controls
* hallucinated relationships
* inconsistent naming
* token pressure
* unstable outputs

Chunking improves:

* locality of reasoning
* atomic extraction
* evidence traceability
* deterministic behavior
* parallel processing
* deduplication quality

⸻

Recommended Architecture

Stage 0 — Preprocessing

Convert documents into structured sections.

Input:

* PDF
* DOCX
* HTML
* Wiki pages
* Process exports

Output:

* normalized text structure

Example:

{
  "document": "Access_Control_Policy",
  "sections": [
    {
      "section_id": "4.2",
      "heading": "User Access Reviews",
      "text": "User access rights must be reviewed quarterly..."
    }
  ]
}

⸻

Step 1 — Structural Chunking

Do NOT chunk arbitrarily by token count only.

Best practice:

Prefer Semantic/Structural Chunking

Chunk by:

* headings
* subheadings
* process stages
* control areas
* numbered sections

Good chunk:

4.2 User Access Reviews

Bad chunk:

Page 7, tokens 4000–6000

because controls get split across boundaries.

⸻

Recommended Chunk Size

Typical sweet spot:

* 500–2000 words
* or 1–5 logical sections

Too small:

* insufficient context

Too large:

* diluted extraction quality

⸻

Recommended Chunk Metadata

Every chunk should carry metadata.

Example:

{
  "chunk_id": "ACP-4.2",
  "document": "Access_Control_Policy",
  "section": "4.2",
  "heading": "User Access Reviews",
  "page_start": 12,
  "page_end": 13,
  "text": "..."
}

This becomes essential later for:

* evidence traceability
* audit defensibility
* deduplication
* citations

⸻

Step 2 — Per-Chunk Domain Extraction

Run Stage 1 prompt independently on each chunk.

Example:

Chunk 1 → IAM
Chunk 2 → IAM + Logging
Chunk 3 → Backup & Recovery

Do NOT try to globally normalize yet.

Just extract locally.

Output:

{
  "chunk_id": "ACP-4.2",
  "domains": [
    {
      "domain_name": "Identity and Access Management",
      "confidence": "High"
    }
  ]
}

⸻

Step 3 — Aggregate Domains

Combine all chunk-level domains.

You now have noisy duplicates like:

Identity and Access Management
Access Management
User Access Control
Authentication and Authorization

Aggregate them into a candidate set.

⸻

Step 4 — Domain Normalization

Now run a dedicated normalization pass.

This is important:
normalization should be a separate reasoning task.

Prompt objective:

Normalize semantically equivalent domains into canonical domain names.

Example output:

{
  "canonical_domain": "Identity and Access Management",
  "aliases": [
    "Access Management",
    "User Access Control",
    "Authentication and Authorization"
  ]
}

This stage is often where the real quality improvement happens.

⸻

Step 5 — Per-Chunk Control Extraction

Now rerun extraction per chunk using:

* chunk text
* normalized domains

This dramatically improves control mapping quality.

Example:

Chunk:
"User access rights must be reviewed quarterly."
Known domains:
- Identity and Access Management

The model now extracts much more accurately.

⸻

Step 6 — Aggregate Controls

Now collect all controls from all chunks.

At this point you will have:

* duplicates
* overlapping controls
* controls at different granularity levels

Example:

Quarterly access reviews are performed.
Management reviews user access quarterly.
User access must be periodically reviewed.

⸻

Step 7 — Control Normalization

This deserves its own agent/prompt.

Tasks:

* merge duplicates
* standardize wording
* preserve evidence references
* preserve source traceability

Example:

{
  "canonical_control": {
    "control_title": "Quarterly User Access Reviews",
    "control_statement": "Management performs quarterly reviews of user access rights."
  },
  "source_controls": [
    "CTRL-17",
    "CTRL-91",
    "CTRL-103"
  ]
}

⸻

Step 8 — Optional Enrichment

After normalization you can enrich controls with:

* ISO 27001 mappings
* NIST mappings
* risk statements
* control maturity
* ownership
* automation potential
* test procedures
* evidence expectations

This stage should happen AFTER normalization.

⸻

Strong Recommendation: Use Multi-Agent Separation

Do NOT create one mega-agent.

Best practice is specialized agents.

Example:

Agent	Responsibility
Chunking Agent	Structural segmentation
Domain Extraction Agent	Extract candidate domains
Domain Normalization Agent	Canonicalize domains
Control Extraction Agent	Extract controls
Control Normalization Agent	Merge duplicates
Framework Mapping Agent	Map to ISO/NIST/etc
Gap Analysis Agent	Identify missing controls

This dramatically improves:

* explainability
* debugging
* consistency
* maintainability

⸻

Important: Preserve Source Lineage

Every extracted object should retain:

{
  "source_document": "...",
  "source_section": "...",
  "source_chunk": "...",
  "source_excerpt": "..."
}

Without this:

* audit defensibility weakens
* deduplication worsens
* explainability suffers

⸻

Recommended Data Model

A graph structure works extremely well.

Example:

Document
  → Chunk
      → Domain
          → Control
              → Framework Mapping

Or relationally:

documents
chunks
domains
controls
control_evidence
framework_mappings

⸻

Recommended LLM Strategy

Extraction Tasks

Use:

* low temperature (0–0.2)
* strict JSON
* schema validation
* deterministic decoding

Normalization Tasks

Slightly higher reasoning flexibility can help:

* temperature 0.2–0.4

because semantic consolidation requires abstraction.

⸻

Recommended Practical Workflow

A very effective production workflow is:

1. Parse document structure
2. Chunk structurally
3. Extract domains per chunk
4. Normalize domains globally
5. Extract controls per chunk
6. Normalize controls globally
7. Enrich controls
8. Perform gap analysis

This scales far better than:

* giant prompts
* giant context windows
* single-pass extraction

even on very capable models.

⸻

What Usually Produces the Biggest Quality Gain

In practice, these matter most:

Improvement	Impact
Structural chunking	Very High
Separate normalization stage	Very High
Evidence requirements	Very High
Atomic controls	High
Controlled taxonomy	High
Schema validation	High
Large context windows	Moderate
Fancy prompt wording	Moderate

The normalization stages are usually underestimated. They often matter more than the extraction prompts themselves.