# Infographics Catalog

> **Source:** `SAAF Project Drive/Handy Resources - Photos and Videos/`  
> **Purpose:** Visual reference catalog — text descriptions of 10 infographics relevant to AI concepts used across SAAF plans. Original PNG files are in the Drive but not committed to the repo.

---

## 1. Layers of AI (1)

**Filename:** `Layers of AI (1).png`  
**Type:** Conceptual illustration (artistic stacked-layer style)

**Description:**  
A stacked-platform diagram showing 6 hierarchical layers of AI from bottom to top:

| Layer | Key components |
|---|---|
| **Classical AI** (bottom) | Symbolic AI, Expert Systems, Knowledge Representation, Logic & Reasoning |
| **Machine Learning** | Supervised Learning, Unsupervised Learning, Classification, Reinforcement Learning, Regression |
| **Neural Networks** | Perceptrons, Cost Functions, Backpropagation, Activation Functions, Hidden Layers |
| **Deep Learning** | Transformers, LSTMs, RNNs, CNNs, Autoencoders |
| **Generative AI** | LLMs, Diffusion Models, Multimodal Models, VAEs |
| **Agentic AI** (top) | Memory, Planning, Tool Use, Autonomous Execution |

**SAAF relevance:** Foundational mental model for explaining what kind of AI is used in which SAAF plan. Claude API operates at the Generative AI + Agentic AI layers. Whisper operates at Deep Learning (ASR). Local Ollama models are Generative AI.

---

## 2. Layers of AI (2)

**Filename:** `Layers of AI (2).PNG`  
**Type:** LinkedIn post screenshot (Brian Reiff) — tabular pyramid version

**Description:**  
A LinkedIn post with a cleaner, tabular version of the same 6-layer hierarchy, listing specific technologies in each row:

| Layer | Technologies listed |
|---|---|
| **Artificial Intelligence** | Intelligent Robotics, Reinforcement Learning, Speech Recognition, Expert Systems, Algorithm-Building, AI Ethics, Cognitive Computing, Knowledge Representation |
| **Machine Learning** | K-Means, PCA, Decision Trees, Linear Regression, Logistic Regression, Neural Networks, SVMs, Naive Bayes |
| **Neural Networks** | Boltzmann Machine, CNNs, Backpropagation, Multi-Layer Perceptron, Feed-Forward Networks, Hybrid Networks, Recurrent Neural Networks |
| **Deep Learning** | GAN, CNN, RNN (Long Short-Term Memory), LSTM, Deep Belief Networks, Self-Organizing Maps |
| **Generative AI** | RLHF, LLM-large Language Models, Fine-Tuning, Diffusion Models, Generative Adversarial, Multimodal AI, LangChain |
| **Agentic AI** | Memory & Context Handling, Diffusion Models, Feedback Loops & Evaluators, Multi-Agent Systems, Tool Use & Integration, Workflow Automation, Autonomous Decision-Making |

**SAAF relevance:** Complementary to Layers of AI (1) — shows concrete technology names per layer. Useful when selecting which technology applies to a specific SAAF plan component.

---

## 3. Agentic AI: The Big Picture

**Filename:** `Agentic AI - The big picture.png`  
**Type:** Circular wheel diagram (comprehensive ecosystem map)

**Description:**  
A large nested-ring "wheel" diagram by @GH that maps the entire Agentic AI ecosystem from inner rings (foundational) to outer rings (advanced):

| Ring (inner → outer) | Tagline | Key concepts |
|---|---|---|
| **AI & ML** | Turn your data into decisions | Supervised/Unsupervised/Reinforcement Learning, Transformers, CNNs |
| **Deep Learning** | Multi-layered neural networks for complex tasks | Deep Belief Networks, RNNs & LSTMs, CNNs, Code/Image/Video Generation |
| **Gen AI** | Generate content and code at scale | LLMs, RAG, Speech Interfaces (TTS/ASR), Memory Systems, Output Validation, Prompt Engineering |
| **AI Agents** | Execute complex tasks autonomously | Tool Use & Function Calling, Context Management (state & history), Human-in-the-Loop Oversight, Failure Recovery & Replanning, Dynamic Tooling |
| **Agentic AI** (outer) | Automate entire processes with AI | Memory Governance, Delegation & Handoff Protocols, Observability & Tracing, Risk Management & Constraints, Agent Marketplaces & Contracts, Governance, Safety & Guardrails, Long-term Autonomy & Goal Chaining, Cost & Resource Management, Feedback Loops & Evaluators, Rollback Mechanisms, Self-Improving Agents, Intent Preservation, Agent Protocols |

**SAAF relevance:** The most comprehensive single-image reference for agentic AI concepts. Directly maps to the SAAF 4-pillar framework: Governance/Safety/Guardrails = Regulatory pillar; Tool Use & Function Calling = Tools pillar; Memory Systems + RAG = infrastructure for all plans; Human-in-the-Loop Oversight = mandatory auditor checkpoint in all SAAF plans.

---

## 4. How to Learn Agentic AI (Mind Map)

**Filename:** `Agentic AI.png`  
**Type:** LinkedIn screenshot — mind map (mobile)

**Description:**  
A "How to Learn Agentic AI" mind map (LinkedIn, 68 reposts) showing branches from a central "Agentic AI Basics" node:

- **Core Agent Components:** Memory (short-term/long-term), Planning, Reasoning, Tool Use & API Integration
- **Agent Design Patterns:** ReAct, Chain-of-Thought, Tree-of-Thought, reflection patterns
- **Safety & Sustainability:** Ethical constraints, privacy considerations, bias detection, hallucination mitigation
- **Key Agentic Frameworks:** LangChain, AutoGen, CrewAI, LlamaIndex, Semantic Kernel
- **Multi-Agent Systems:** Role-based agents, orchestration, inter-agent communication
- **Tool & API Integration:** Function calling, MCP, browser tools
- **Advanced Concepts:** Long-term memory, self-reflection, error recovery
- **Learning path:** From basics → frameworks → multi-agent → production

**SAAF relevance:** Learning roadmap for SAAF Engineer participants building agent infrastructure. The "Safety & Sustainability" branch maps directly to the Regulatory pillar requirements in each SAAF plan.

---

## 5. RAG Developer's Stack

**Filename:** `Rag systems.png`  
**Type:** Technology stack infographic (Brij Kishore Pandey)

**Description:**  
A layered funnel showing the full RAG (Retrieval-Augmented Generation) technology stack:

| Layer | Open options | Closed/Commercial options |
|---|---|---|
| **LLMs** | Llama 3.3, Phi-4, Gemma 3, Qwen 2.5, Mistral, DeepSeek | OpenAI, Claude, Gemini, Cohere, Amazon |
| **Frameworks** | LangChain, Llama Index, Haystack, txtai | — |
| **Vector Databases** | Chroma, Qdrant, Weaviate, Milvus | Pinecone |
| **Data Extraction (Web)** | Crawl4AI, FireCrawl, ScrapeSraphAI | — |
| **Data Extraction (Docs)** | MegaParser, Docling, LlamaParser, ExtractThinker | — |
| **Open LLMs Access** | HuggingFace, Ollama, Groq, Together AI | — |
| **Text Embeddings (Open)** | NOMIC, SBERT, BGE, Ollama | — |
| **Text Embeddings (Closed)** | — | OpenAI, Voyage AI, Google, Cohere |
| **Evaluation** | Giskard, Ragas, Trulens | — |

**SAAF relevance:** Direct technology reference for `saaf-rag-knowledge-base.md`. The plan uses ChromaDB (Vector DB) + Nomic embed text v1.5 (Text Embeddings, open) + Claude (LLM, closed) — all shown in this stack. Ragas and Trulens are the evaluation tools for the RAG benchmark (20-question test harness).

---

## 6. AI First vs. Foundations First

**Filename:** `AI First vs Foundations First.png`  
**Type:** Meme (two-panel comparison, @ordax on X/LinkedIn)

**Description:**  
Two-panel split image:

- **Left — AI First:** A luxurious modern house perched on rickety wooden stilts over a canyon. Caption: *"You moved fast. You built fancy stuff. But you'll collapse."*
- **Right — Foundations First:** A modest but solid house on reinforced concrete foundations. Caption: *"You don't care about AI and headlines... You care about value."*

**SAAF relevance:** Core tension in the SAAF philosophy. The SAAF approach is explicitly "Foundations First" — establish synthetic data, shared RAG, skills matching, and output schemas before building production agents. The meta-analysis section on "Do → Check → Act" bias reflects this risk: teams built (AI First) but did not validate (Foundations First). This infographic is useful in hackathon kick-off presentations to frame why infrastructure plans (Strapi, RAG, MCP) come before agent plans.

---

## 7. Security for Vibe Coding

**Filename:** `Security for vibe coding.png`  
**Type:** TikTok screenshot (@jackprice — "For You" feed)

**Description:**  
A TikTok video screenshot titled "How to not get hacked when vibe coding" listing three security anti-patterns to avoid:

1. **No rate limiting** — unprotected API endpoints that can be abused
2. **No input validation** — accepting untrusted user input directly
3. **Exposed API keys** — hardcoded credentials in code

**SAAF relevance:** Directly relevant to the guardrails checklist in every SAAF plan (`regulatory/guardrails/allowed-commands.md`). The three anti-patterns map to common risks when SAAF participants prototype agents rapidly during hackathons: API keys committed to GitHub, no input sanitization in agent prompts, no rate limiting on Strapi endpoints. This image is useful as a reminder in the hackathon briefing.

---

## 8. Alpha Signal Newsletter (Example)

**Filename:** `Alpha Signal Newsletter.png`  
**Type:** Email newsletter screenshot (Alpha Signal, daily AI briefing)

**Description:**  
A screenshot of an Alpha Signal daily briefing email ("Hey AI Innovator, Your daily briefing is ready"):

- **Top News:** Google adds Personal Intelligence for cross-app reasoning across Google apps
- **Top Repo:** Vercel ships React rules for agents to guide automated performance refactors
- **Top News:** Anthropic rolls out Tool Search in Claude Code to streamline MCP discovery
- **Top News:** OpenAI brings GPT-5.2-Codex to Responses API

Format: curated signal/noise separation with "Top News", "Top Repo", "Top Models", "Top Papers" sections. Read time ~4 minutes.

**SAAF relevance:** Alpha Signal is one of the 30 sources in the `docs/reference/ai-sources-registry.md` feed list. This screenshot shows what the newsletter looks like and what kind of content it provides. The `saaf-intelligence-monitor.md` plan's digest format is modelled on this structure (headline, link, one-line relevance note).

---

## 9. Search, Web and Crawling (MCP Tools List)

**Filename:** `Search, Web and Crawling.PNG`  
**Type:** App screenshot — partial MCP tools list

**Description:**  
A screenshot from a mobile app (appears to be a Claude Code MCP tools browser or similar) showing a partial list of tools under "Search, Web and Crawling":

- **#10 Sequential Thinking:** Makes the model plan in explicit steps, track progress, and run multi-step tool calls in a clear order
- **#11 TaskManager MCP Server:** Makes the model plan in explicit steps, track progress, and run multi-step tool calls in a clear order *(appears to have the same description as #10 — possibly a screenshot artifact)*
- **#12 Toclrouter MCP Server:** Sits in front of many MCP servers and routes each request to the right tool from a single endpoint

**SAAF relevance:** Directly relevant to `saaf-jira-confluence-mcp.md`. The Toclrouter MCP Server pattern (a single routing endpoint in front of multiple MCP servers) is the architecture the SAAF MCP plan should adopt in v2 — instead of maintaining separate MCP configs for Jira and Confluence, a single router endpoint would simplify Claude Code configuration.

---

## 10. PayOS — AI Agent Payment Infrastructure

**Filename:** `Pay os.png`  
**Type:** WhatsApp group screenshot (AI Innovators' Hub)

**Description:**  
A WhatsApp group chat in "AI Innovators' Hub" sharing a news post about **PayOS**:

> "PayOS | AI Agent Payment Infrastructure. PayOS announces the successful completion of a landmark agentic payment transaction using a Mastercard Agentic Token. This historic milestone in agentic commerce demonstrates the po[ssibility of] agents managing their own wallets."

The post links to `payos.ai`. The group discussion notes: *"Nu krijg je ook dit soort producten. https://payos.ai/ Een manier van agents om hun eigen portemonnee te managen"* (Dutch: "Now you're getting these kinds of products too. A way for agents to manage their own wallets").

A second message discusses using local Whisper for WhatsApp voice messages: an assistant can locally install Whisper to transcribe voice messages sent via WhatsApp.

**SAAF relevance:** 
- **PayOS:** Signals the emerging "agentic commerce" direction — agents that can transact autonomously. For the SAAF community, this is relevant to future P2P/O2C audit agents that may need to verify agentic payment transactions. Not yet in scope for any current plan.
- **Whisper for WhatsApp:** The Whisper transcription approach used for the 88 SAAF videos also applies to WhatsApp voice messages — a practical extension of `tools/scripts/transcribe_videos.py` with no code changes.

---

## Summary Table

| File | Category | SAAF Pillar | Most relevant plans |
|---|---|---|---|
| Layers of AI (1) | Conceptual model | All | All — educational reference |
| Layers of AI (2) | Conceptual model (tech names) | All | All — technology selection |
| Agentic AI: The Big Picture | Ecosystem map | All | `icfcop-control-testing-agent`, `saaf-rag-knowledge-base` |
| How to Learn Agentic AI | Learning roadmap | All | Onboarding for new participants |
| RAG Developer's Stack | Technology stack | Tools | `saaf-rag-knowledge-base` |
| AI First vs. Foundations First | Philosophy | Regulatory | Hackathon briefings, meta-analysis |
| Security for Vibe Coding | Security guardrails | Regulatory | All — guardrails checklist |
| Alpha Signal Newsletter | Source example | Tools | `saaf-intelligence-monitor`, `yellowraptor-whats-the-news` |
| Search, Web and Crawling | MCP tools | Tools | `saaf-jira-confluence-mcp` |
| PayOS | Emerging tech | Outputs | Future agentic commerce audit plans |
