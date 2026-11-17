# AI Tools and Techniques — Layers of AI

> **Source:** `SAAF Project Drive/AI Tools & Techniques (Layers of AI).xlsx`  
> **Maintained by:** SAAF Project Organisation  
> **Purpose:** Reference catalog of AI tools, frameworks, and techniques organized by layer and category. Use this when selecting technology for a SAAF plan.

---

## Layers of AI

The SAAF community uses a six-layer model to describe where different AI techniques operate.

| Layer | Techniques / Concepts |
|---|---|
| **Classical AI** | Logic & Reasoning, Knowledge Representation, Expert Systems, Symbolic AI |
| **Machine Learning** | Supervised Learning, Unsupervised Learning, Reinforcement Learning, Classification, Regression |
| **Neural Networks** | Perceptrons, Cost Functions, Backpropagation, Activation Functions, Hidden Layers |
| **Deep Learning** | Transformers, LSTMs, RNNs, CNNs, Autoencoders |
| **Generative AI** | LLMs, Diffusion Models, Audio/Video/Photos, Multimodal Models, VAEs |
| **Agentic AI** | Memory, Planning, Tool Use, Autonomous Execution |

---

## RAG Ecosystem

RAG (Retrieval-Augmented Generation) is the primary architecture for most SAAF audit agents. Below are the tools by sub-category.

### LLMs (Models)

| Tool | Notes |
|---|---|
| **Claude** (Anthropic) | Primary SAAF model. Recommended: `claude-sonnet-4-6` |
| OpenAI (GPT series) | Alternative / comparison |
| Gemini (Google) | Alternative / comparison |
| Llama (Meta) | Open-source, runs locally via Ollama |
| Phi-4 (Microsoft) | Small but capable open model |
| Gemma 3 (Google) | Open-source |
| Qwen 2.5 (Alibaba) | Open-source, strong multilingual |
| Mistral | European open-source LLM |
| Deepseek | Chinese open-source, strong coding |
| Cohere | Enterprise-focused |

### Frameworks

| Tool | Notes |
|---|---|
| **LangChain** | Most widely used agent/RAG framework |
| **Llama Index** | Specialized for document indexing and retrieval |
| Haystack | Open-source NLP pipelines |
| txtai | Lightweight semantic search |

### Vector Databases

| Tool | Notes |
|---|---|
| **Chroma** | Simple, Python-native, good for prototyping |
| **Qdrant** | Production-ready, Rust-based, self-hostable |
| Pinecone | Managed cloud vector DB |
| Weaviate | Graph-enhanced vector DB |
| Milvus | High-performance, large-scale |

### Data Extraction — Web

| Tool | Notes |
|---|---|
| Crawl4AI | AI-native web crawler |
| FireCrawl | LLM-ready web scraping |
| ScrapeGraphAI | Graph-based scraping with LLMs |

### Data Extraction — Documents

| Tool | Notes |
|---|---|
| **LlamaParse** | Best-in-class PDF/document parsing for RAG |
| Extract Thinker | Document intelligence extraction |
| MegaParser | Multi-format parsing |
| Docling | IBM open-source document conversion |

### Open LLM Access Platforms

| Tool | Notes |
|---|---|
| **Ollama** | Run LLMs locally on Mac/Linux. Supports Llama, Mistral, Deepseek, Phi-4 |
| HuggingFace | Model hub + Inference API |
| Groq | Ultra-fast inference (LPU hardware) |
| Together AI | Managed open-model inference |

### Text Embeddings — Open

| Tool | Notes |
|---|---|
| **Nomic** | Best open embedding model for RAG |
| SBERT (sentence-transformers) | Widely used, good multilingual |
| BGE (BAAI) | Strong performance on retrieval benchmarks |
| Ollama | Can run embedding models locally |

### Text Embeddings — Closed (API)

| Tool | Notes |
|---|---|
| OpenAI Embeddings | `text-embedding-3-small/large` |
| Voyage AI | High-quality retrieval embeddings |
| Google Embeddings | Vertex AI |
| Cohere Embeddings | Multilingual support |

### Evaluation / Observability

| Tool | Notes |
|---|---|
| Giskard | Open-source LLM testing and red-teaming |
| RAGAS | RAG-specific evaluation metrics |
| TruLens | LLM app evaluation and tracking |

---

## Search, Web, and Crawling

| Tool | Type | Notes |
|---|---|---|
| Sequential Thinking | Technique | Chain-of-thought reasoning for complex multi-step tasks |
| TaskManager MCP Server | MCP Tool | Task management via Model Context Protocol |
| Toolrouter MCP Server | MCP Tool | Route between multiple MCP tools |

---

## AI Tools (General)

| Tool | URL | Notes |
|---|---|---|
| **Claude** (Anthropic) | claude.ai | Primary tool for SAAF |
| ChatGPT | chatgpt.com | OpenAI, alternative |
| Gemini | — | Google, alternative |
| Google Labs / Antigravity | labs.google / antigravity.google | Experimental Google tools |
| Perplexity | — | Research and news tool |
| GitHub Copilot | — | Code completion, used alongside Claude Code |
| Microsoft Copilot | — | M365 integration |
| Cursor | — | AI-native code editor |
| Kiro | — | AI coding assistant |
| Kimi | — | Long-context model |
| Grok (xAI) | — | Elon Musk / Twitter AI |
| Nano Banana Pro | — | Experimental AI tool |
| Midjourney | — | Image generation |
| Stable Diffusion | — | Open-source image generation |
| Notion AI | — | AI-powered workspace |
| Replit Ghostwriter | — | Browser-based AI coding |
| LLaMA (Meta) | — | Open-source LLM |
| Mistral | — | European LLM |
| JetBrains AI | — | IDE-integrated AI |

---

## Usage Guidance for SAAF Plans

When selecting technology for a plan, consider:

1. **For prototyping (Phase 1):** Claude via browser + Python scripts = no API needed
2. **For production agents (Phase 2):** `claude-sonnet-4-6` via API + Python 3.11
3. **For RAG pipelines:** LlamaIndex or LangChain + Chroma (dev) or Qdrant (prod) + Nomic embeddings
4. **For local/private data:** Ollama + local Llama/Mistral + Chroma (no data leaves the machine)
5. **For document parsing:** LlamaParse (best quality) or pdfplumber (simple, no API needed)
6. **For evaluation:** RAGAS for RAG quality, Giskard for safety/red-teaming
7. **For synthetic test data:** Strapi (SAAF-sponsored instance) — see `plans/hackathon-3/saaf-strapi-synthetic-data.md`
