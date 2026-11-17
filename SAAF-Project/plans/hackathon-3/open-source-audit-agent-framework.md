# Open-Source Audit Agent Framework

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Skill |
| **Status** | Draft |

---

## 2. Problem Statement

Claude API costs are a barrier for smaller audit teams and organizations in the public sector. A single audit run (RCM building, vendor assessments, policy review) can cost €5-20 in Claude Sonnet tokens — multiplied across 50 audits per year, this becomes a significant budget item.

Smaller firms and public sector audit departments cannot justify recurring API costs for exploratory AI agent work. They need a cost-free audit agent stack that runs entirely locally, without sending data to external APIs.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Agent Infrastructure / Accessibility

**Applicable standards:**

- GDPR — Art. 32 (Security of processing) — local-first ensures no data leaves the organization
- IIA IPPF — Standard 1200 (Proficiency)
- EU AI Act — Art. 4 (AI Literacy) — accessible tooling enables broader adoption

**In scope:**

- Cost-free (~€0 API cost) audit agent stack using local open-source models
- GLM 4.7 via Ollama as primary reasoning model (strong multilingual, strong at structured output)
- Claude Code Router: route simple tasks to GLM 4.7 (local), complex tasks to Claude Sonnet (API)
- Pre-configured prompt templates for core SAAF use cases
- Setup guide: Mac/Linux install in under 30 minutes

**Out of scope:**

- GPU server infrastructure (targets M-series Mac and modern Intel/AMD laptops)
- Real-time performance at scale (local models are slower — batch/overnight use is primary)
- Proprietary model fine-tuning (uses base Ollama models only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Port of existing SAAF prompts optimized for GLM 4.7 instruction format |
| **Tools** | `tools/scripts/local-audit-agent.py` — Ollama-based agent runner; router config |
| **Regulatory** | GDPR Art. 32 compliance documentation for local-first stack |
| **Outputs** | Same finding-schema.json output as Claude-based agents |

---

## 5. Prompts

### System prompt (draft — GLM 4.7 optimized)

```
[SYSTEM]
You are an internal audit assistant. You help auditors identify control gaps and draft findings.
Rules:
- Always cite the specific standard (ISO 27001, DORA, GDPR) with article/section
- Use the finding format: Condition | Criterion | Cause | Effect
- Never make up facts — say "I don't know" if you lack information
- Keep responses structured and concise
[/SYSTEM]
```

### Example user prompts

**Prompt 1 — Local policy analysis:**
```
[USER]
Analyze the attached Information Security Policy excerpt.
Identify control gaps against ISO 27001 Annex A.9 (Access Control).
List each gap as: Gap | Missing control | ISO ref | Risk rating (H/M/L)
[/USER]
```

**Prompt 2 — Cost comparison query:**
```
[USER]
We have 50 vendor contracts to review against DORA Art. 28-30.
Estimate: how many can the local GLM 4.7 model handle vs. what needs Claude Sonnet?
[/USER]
```

**Intended file location:** `prompts/audit-use-cases/local-audit-agent.md`

---

## 6. Tools and Techniques

### Approach

The Claude Code Router pattern: a lightweight Python wrapper intercepts agent calls and routes them based on complexity:
- Simple tasks (classification, template fill, short lookups) → GLM 4.7 via Ollama API (€0)
- Complex tasks (multi-document reasoning, nuanced regulatory interpretation) → Claude Sonnet API

Routing heuristic: token count of input + task type tag. If input < 2,000 tokens and task type is "classify", "extract", or "template" → local model. Otherwise → Claude API.

The router is transparent to the audit agent — it exposes the same OpenAI-compatible API on localhost.

### Example script or pseudocode

```python
import anthropic
import httpx
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "glm4:latest"
LOCAL_TASK_TYPES = {"classify", "extract", "template", "lookup"}

anthropic_client = anthropic.Anthropic()

def route_and_run(
    system: str,
    prompt: str,
    task_type: str = "reason",
    max_tokens: int = 2048
) -> str:
    token_estimate = len(prompt.split()) + len(system.split())

    if task_type in LOCAL_TASK_TYPES and token_estimate < 2000:
        # Route to local GLM 4.7
        response = httpx.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": f"[SYSTEM]\n{system}\n[/SYSTEM]\n[USER]\n{prompt}\n[/USER]",
            "stream": False,
            "options": {"num_predict": max_tokens}
        }, timeout=120)
        return response.json()["response"]
    else:
        # Route to Claude Sonnet
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

# Example usage
result = route_and_run(
    system="You are an audit assistant...",
    prompt="Classify this vendor risk level: [vendor data]",
    task_type="classify"
)
print(result)
```

**Setup instructions:**

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
# Pull GLM 4.7
ollama pull glm4
# Test
ollama run glm4 "What is ISO 27001 A.9.2.6?"
```

**Tech stack used:** Python 3.9+, Ollama (GLM 4.7), Claude API (claude-sonnet-4-6, complex tasks only), httpx

**Intended file location:** `tools/scripts/local-audit-agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GDPR Art. 32 | Security of processing — local model processes all data on-device; no data egress |
| EU AI Act Art. 4 | AI Literacy — accessible local tooling enables broader adoption without budget barriers |
| IIA IPPF 1200 | Proficiency — local model provides auditors with AI augmentation without cloud dependency |

### Claude / AI tool usage notes

GLM 4.7 (local) processes all sensitive audit data. Claude Sonnet API is called only for complex reasoning tasks — with synthetic or anonymized data only. Organizations with strict data residency requirements (e.g., government sector) can disable the Claude API fallback entirely and run 100% locally.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Same as Claude-based agents — JSON findings, Markdown reports

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output (vendor risk classification — local model)

```json
{
  "vendor": "Contoso B.V.",
  "task_type": "classify",
  "model_used": "glm4 (local)",
  "risk_level": "Medium",
  "rationale": "Vendor provides non-critical SaaS service. No DORA ICT third-party dependencies identified. GDPR DPA in place. Missing: SLA with defined RTO.",
  "cost_eur": 0.00
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] Ollama (GLM 4.7) — local LLM
- [x] Claude API (claude-sonnet-4-6) — complex tasks only
- [x] httpx (Ollama API client)
- [ ] Router config file (YAML) for customizing routing rules

**Stretch goals:**

- [ ] GUI router dashboard: show cost per task and model routing decisions
- [ ] Fine-tune GLM 4.7 on SAAF plan corpus for domain-specific accuracy
- [ ] Docker container: one-click local deployment for non-technical auditors

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `local-audit-agent.py` router + runner
- Routing configuration YAML
- Ported SAAF prompts in GLM 4.7 format
- Setup guide for Mac/Linux

**Help requested:**

- Organizations with strict data residency requirements: validate the 100% local configuration
- Auditors: benchmark GLM 4.7 output quality against Claude Sonnet for their specific use cases
- ML engineers: explore fine-tuning on SAAF domain corpus

**Cross-org interest:**

Public sector and smaller organizations cannot always use cloud AI. A zero-cost local stack unlocks AI audit capability for organizations that would otherwise be excluded from the SAAF community's tools.

**Ecosystem Developments (April 2026):**

Several developments strengthen the case for the open-source / local-first approach:

- **LibreChat** (`librechat.ai`): open-source multi-model chat UI that supports Ollama, OpenAI, Claude, and Anthropic APIs through a single interface. LibreChat can serve as the UI layer for the SAAF local agent framework — auditors interact via a familiar chat UI while the router selects the appropriate model backend. This avoids building a custom UI and is actively maintained.

- **Kimi K2.5 (May 2025)**: Moonshot AI's Kimi K2.5 model benchmarks comparably to Claude Opus on reasoning tasks at approximately 15× lower API cost (at May 2025 pricing). For SAAF organizations that cannot self-host but need cost-effective complex reasoning, Kimi K2.5 is a viable alternative to routing complex tasks to Claude Sonnet. The router in this plan should add `kimi-k2.5` as a third routing option alongside `glm4` (local) and `claude-sonnet-4-6` (cloud).

- **TurboQuant / 4-bit Quantization**: modern quantization techniques (GPTQ, AWQ, GGUF 4-bit) reduce model memory requirements by ~4× with <5% quality loss for most audit tasks. GLM 4.7 at 4-bit quantization fits in 8GB VRAM (consumer GPU or Apple Silicon M-series). This removes the hardware barrier for most SAAF participants — an M2 MacBook Pro with 16GB unified memory can run a competent local audit LLM. Document the recommended quantization settings in the setup guide.

- **ZeroClaw** (`zeroclaw.org`): open-source agent harness that supports Ollama backends. ZeroClaw's scheduled tool execution and output streaming patterns are directly reusable for the always-on and overnight batch use cases. Consider forking ZeroClaw's Ollama integration rather than building from scratch.

**Related SAAF plans:**

- [`always-on-audit-agent.md`](always-on-audit-agent.md) — uses same Ollama fallback pattern
- [`overnight-audit-batch-processing-agent.md`](overnight-audit-batch-processing-agent.md) — can run overnight batches entirely locally
- [`audit-workflow-automation-levels.md`](audit-workflow-automation-levels.md) — local model fits Level 1 automation
- [`on-premise-ai-compute-decision-framework.md`](on-premise-ai-compute-decision-framework.md) — hardware decision framework for organizations considering dedicated GPU compute

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Router architecture designed; model selection validated |
| **Do** | In progress | Hackathon #3: install GLM 4.7, run 5 SAAF prompts, compare output to Claude Sonnet |
| **Check** | Not started | Benchmark: quality delta between GLM 4.7 and Claude Sonnet per task type |
| **Act** | Not started | Publish router + routing config as SAAF infrastructure component |

---

## 12. Open Questions

1. What is the actual quality delta between GLM 4.7 and Claude Sonnet for Dutch regulatory text analysis?
2. Should the router use a simple heuristic (token count + task type) or a classifier model to decide routing?
3. Is GLM 4.7 the best local model for this use case, or should we benchmark Mistral, Qwen, or Phi-4?
4. How do we ensure the local model version is documented for reproducibility (same as documenting which Claude model was used)?
