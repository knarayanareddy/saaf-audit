# Plan: On-Premise AI Compute Decision Framework for Audit Departments

## 1. Metadata

| Field | Value |
|---|---|
| **Plan file** | `on-premise-ai-compute-decision-framework.md` |
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organization** | SAAF |
| **Session** | Hackathon 3 (Session 4) |
| **Date** | April 21, 2026 |
| **Status** | Draft |
| **Type** | Framework + Reference |
| **Primary domain** | AI Infrastructure / AI Governance |
| **Source** | SAAF community discussion (Hackathon #3 preparation, April 2026) — question raised: when does an audit department justify acquiring dedicated AI compute (e.g., NVIDIA DGX system) rather than relying on cloud API calls? |

---

## 2. Problem Statement

Most SAAF agents call Claude or GPT-4o via API — fast to prototype, but raises three structural concerns as audit AI usage matures:

1. **Data sovereignty**: Real audit data (client transactions, personnel data, financial statements) cannot be sent to external cloud APIs under GDPR Art. 28 without DPA agreement and data transfer controls. Cloud APIs constrain which data agents can process.
2. **Cost at scale**: At production volume (500+ agent runs/month, 100K+ tokens per run), API costs exceed €10K/month per mid-size audit department. On-premise compute has high upfront cost but near-zero marginal cost per run.
3. **Availability and latency**: Cloud APIs have rate limits, service interruptions, and latency that make overnight batch processing unreliable at scale. Local inference has no rate limits and deterministic availability.

**The unanswered question:** At what point does an audit department cross the threshold where purchasing dedicated GPU infrastructure (NVIDIA DGX, GB200 NVL72 rack, or RTX workstation) is more cost-effective and compliant than API usage — and what does the procurement, setup, and governance process look like?

---

## 3. Use-Case Type & Scope

**Type:** Framework + Reference

**Scope:**
- Define the decision criteria for on-premise vs. cloud AI for audit departments
- Provide a TCO model (3-year total cost of ownership: hardware vs. API)
- Map hardware tiers (workstation → server → rack) to audit workload sizes
- Define which models run on which hardware (Llama 3.3, Mistral, Qwen, DeepSeek, Gemma 3)
- Define the governance, procurement, and security requirements for an on-premise AI system in an audit context
- Provide a step-by-step evaluation checklist (15 questions) for the buy decision

**Out of scope:**
- Procurement contracts or vendor negotiations
- Full IT infrastructure design
- Hardware comparison of GPU architectures (this is reference material, not an audit tool)

---

## 4. Four-Pillar Mapping

| Pillar | Contribution |
|---|---|
| **Prompts** | Decision-support prompts for the TCO analysis; model selection guidance prompt |
| **Tools** | TCO calculator (Python script); Ollama model benchmark runner; hardware sizing matrix |
| **Regulatory** | GDPR Art. 28 (processor agreements), GDPR Art. 32 (security of processing), EU AI Act Art. 15 (accuracy and robustness — quality requirements for high-risk AI), IIA Standard 1210 (proficiency — understanding AI tool limitations) |
| **Outputs** | Decision brief (Markdown/PDF); TCO comparison table; hardware selection matrix |

---

## 5. Decision Framework: On-Premise vs. Cloud API

### 5.1 Decision Trigger Checklist

Answer YES/NO to each question. Scoring at the end:

| # | Question | Weight |
|---|---|---|
| 1 | Do you process real (non-synthetic) client data in AI agents? | HIGH |
| 2 | Do you lack a GDPR Art. 28 DPA with your current AI API provider? | HIGH |
| 3 | Do your agents run >200 sessions/month at >50K tokens/session? | HIGH |
| 4 | Do you require 24/7 availability without rate-limit risk? | MEDIUM |
| 5 | Do you need to fine-tune models on your organization's audit methodology? | MEDIUM |
| 6 | Is your cloud API bill >€3,000/month and growing >30%/quarter? | MEDIUM |
| 7 | Do you need offline operation (air-gapped network, client site)? | MEDIUM |
| 8 | Does your organization have existing GPU infrastructure (IT/data science team)? | LOW |
| 9 | Is there internal IT capacity to manage GPU servers? | LOW |
| 10 | Is the 3-year hardware budget >€50K approved or approvable? | LOW |

**Scoring:**
- 3+ HIGH answers → Strong case for on-premise
- 2 HIGH + 2 MEDIUM → Evaluate hybrid (local inference for sensitive data, cloud for synthetic)
- <2 HIGH answers → Stay on cloud API; revisit in 12 months

### 5.2 Hardware Tiers

| Tier | Hardware | VRAM | Models that fit | Audit workload | Approx. price (2026) |
|---|---|---|---|---|---|
| **Workstation** | NVIDIA RTX 4090 (24 GB) | 24 GB | Llama 3.1 8B, Mistral 7B, Gemma 3 9B, DeepSeek R1 8B | Solo auditor, <50 sessions/month | €4,000–€6,000 |
| **Workstation** | NVIDIA RTX 6000 Ada (48 GB) | 48 GB | Llama 3.1 70B (quantized), Qwen 32B, Mistral 22B | Small team, <200 sessions/month | €8,000–€12,000 |
| **Server** | NVIDIA A100 (80 GB) | 80 GB | Llama 3.1 70B (full), Mixtral 8×7B | Mid-size audit dept, <1,000 sessions/month | €15,000–€25,000 (used market) |
| **Server** | NVIDIA H100 (80 GB) | 80 GB | Llama 3.1 70B, Qwen 72B, DeepSeek V3 | Large audit team, production batch processing | €30,000–€50,000 |
| **System** | NVIDIA DGX H100 (640 GB total, 8× H100) | 640 GB | Any open model including 405B, fine-tuning | Department-level production; fine-tuning capability | €300,000–€400,000 |
| **Rack** | NVIDIA GB200 NVL72 | 13.5 TB | Full 405B+ models, multi-model parallel | Enterprise / shared service; multi-department | €3M+ (rack, cooling, power) |

**Recommendation for most audit departments (2026):** Start with RTX 6000 Ada workstation (€10K) running Llama 3.1 70B quantized via Ollama. This handles all SAAF use cases for sensitive-data agents. Upgrade to H100 server when monthly sessions exceed 500.

### 5.3 Three-Year TCO Model

```
Inputs:
  monthly_sessions       = number of agent runs per month
  avg_tokens_per_session = average token count (input + output)
  cloud_price_per_1k     = € per 1,000 tokens (Claude Sonnet ≈ €0.003, Haiku ≈ €0.00025)
  hardware_cost          = one-time hardware purchase
  hardware_power_kwh     = kWh per hour (RTX 4090 ≈ 0.45 kWh, H100 ≈ 0.7 kWh)
  electricity_price      = €/kWh (NL average 2026 ≈ €0.35)
  it_hours_per_month     = hours of IT admin per month
  it_hourly_rate         = €/hour

Cloud 3-year cost:
  monthly_sessions × avg_tokens_per_session / 1000 × cloud_price_per_1k × 36

On-premise 3-year cost:
  hardware_cost
  + (hardware_power_kwh × 24 × 365 × 3 × electricity_price)     # power
  + (it_hours_per_month × it_hourly_rate × 36)                   # IT admin

Breakeven month:
  hardware_cost / (monthly_cloud_cost - monthly_on_premise_cost)
```

**Example — mid-size audit department:**
- 500 sessions/month, 80K tokens/session = 40M tokens/month
- Cloud (Claude Sonnet): €0.003/1K → €120/month → €4,320/3 years
- Cloud (Claude Haiku): €0.00025/1K → €10/month → €360/3 years
- On-premise (RTX 6000 Ada, €10K + power + IT): ≈ €13,000/3 years

At this volume (500 sessions × 80K tokens), cloud (Haiku) is cheaper. On-premise only wins when:
- Volume is 5,000+ sessions/month at 80K tokens
- OR you require Sonnet-quality reasoning (which costs 12× more)
- OR data sovereignty makes cloud off-limits (then cloud cost is irrelevant — you must use on-premise)

### 5.4 Model Selection for Audit Use Cases

| Audit task | Recommended local model | Why |
|---|---|---|
| Document classification (policy type, risk level) | Llama 3.1 8B | Fast, low VRAM, adequate for classification |
| RCM building, finding drafting | Llama 3.1 70B or Qwen 72B | Complex reasoning required; matches Sonnet quality at lower cost |
| Regulatory text extraction | Mistral 22B or Qwen 32B | Strong instruction following; good at structured output |
| Code analysis (OWASP, SDLC) | DeepSeek Coder 33B | Trained on code; better than general models for code audit |
| Interview summarization (Dutch audio) | Whisper large-v3 (STT) + Llama 70B | Whisper handles Dutch; Llama summarizes |
| Fine-tuned audit methodology | Custom fine-tune on Llama 8B | Requires 24+ GB VRAM; DGX-tier for 70B fine-tuning |

---

## 6. Tools & Techniques

| Tool | Role |
|---|---|
| **Ollama** | Model serving on local hardware; supports all open models; simple REST API |
| **Open WebUI** | Browser-based chat interface for Ollama; auditor-friendly |
| **LM Studio** | Windows/macOS GUI for model management and benchmarking |
| **NVIDIA NIM** | Enterprise-grade inference microservices for DGX and H100 systems |
| **vLLM** | High-throughput production inference server (recommended for H100+) |
| **TCO script** | `tools/scripts/tco_calculator.py` (see Section 9) |
| **Benchmark script** | `tools/scripts/benchmark_local_model.py` — runs 10 standard audit prompts, records tokens/second and output quality |

---

## 7. Regulatory Framework

| Standard | Requirement |
|---|---|
| **GDPR Article 28** | Data processor agreements required when using cloud AI APIs to process personal data. On-premise avoids this — the model is a tool, not a processor |
| **GDPR Article 32** | Security of processing: on-premise allows full control over data-in-transit (no external API calls), encryption at rest, and network isolation |
| **GDPR Article 44** | Transfers of personal data to third countries: cloud API providers in the US require SCCs or adequacy decision. On-premise eliminates this entirely |
| **EU AI Act Article 15** | Accuracy, robustness and cybersecurity: high-risk AI systems must have adequate measures; on-premise allows air-gapped deployment for highest-risk audit contexts |
| **IIA Standard 1210** | Proficiency: internal auditors must understand the tools they use, including the limitations of locally-deployed models (hallucination rates, context window limits, outdated training data) |
| **NIS2 Directive** | Organizations in scope must protect critical systems; on-premise AI reduces the attack surface compared to cloud-connected inference |

**Key compliance point:** GDPR Art. 28 applies the moment real personal data (employee names, client transactions, HR records) is processed by a cloud AI API. This is the single strongest driver for on-premise adoption in audit departments that process real data.

---

## 8. Output Format

### Decision Brief (Markdown, 1-2 pages)
```markdown
# On-Premise AI Compute Decision Brief — [Department Name]

## Decision trigger score
HIGH criteria met: X/3 → [Strong case / Evaluate hybrid / Stay on cloud]

## TCO summary
| | Cloud (Sonnet) | Cloud (Haiku) | On-Premise (RTX 6000 Ada) |
|---|---|---|---|
| 3-year cost | € | € | € |
| Breakeven | — | — | Month X |
| Data sovereignty | ❌ | ❌ | ✅ |
| Rate limits | ❌ | ❌ | ✅ |
| Fine-tuning | ❌ | ❌ | ✅ |

## Recommended hardware tier
[Hardware] at approx. [Price]

## Recommended models
[List]

## Next steps
1. ...
2. ...
```

### TCO Comparison Table (CSV export from script)

---

## 9. Tech Stack

```
Language:     Python 3.9+
Dependencies: None (stdlib only for TCO calculator)
Config:       Input parameters via command line or JSON config
Output:       Markdown decision brief + CSV TCO table
```

### Script: `tools/scripts/tco_calculator.py`

```python
import json
import sys
from pathlib import Path

def calculate_tco(params: dict) -> dict:
    sessions = params["monthly_sessions"]
    tokens = params["avg_tokens_per_session"]
    monthly_tokens_k = sessions * tokens / 1000

    # Cloud costs (per 1K tokens)
    cloud_sonnet = monthly_tokens_k * 0.003 * 36
    cloud_haiku  = monthly_tokens_k * 0.00025 * 36

    # On-premise costs
    hw = params["hardware_cost"]
    power_kwh = params.get("hardware_power_kwh", 0.45)
    electricity = params.get("electricity_price", 0.35)
    it_hours = params.get("it_hours_per_month", 2)
    it_rate = params.get("it_hourly_rate", 75)

    power_3yr = power_kwh * 24 * 365 * 3 * electricity
    it_3yr    = it_hours * it_rate * 36
    onprem    = hw + power_3yr + it_3yr

    # Breakeven (vs Sonnet — cheapest cloud that matches quality)
    monthly_saving = monthly_tokens_k * 0.003 - (power_kwh * 24 * 30 * electricity + it_hours * it_rate)
    breakeven = hw / monthly_saving if monthly_saving > 0 else float("inf")

    return {
        "cloud_sonnet_3yr": round(cloud_sonnet, 0),
        "cloud_haiku_3yr":  round(cloud_haiku, 0),
        "onprem_3yr":       round(onprem, 0),
        "breakeven_months_vs_sonnet": round(breakeven, 1) if breakeven != float("inf") else "never",
        "data_sovereignty": "Cloud: ❌ (GDPR Art.28 DPA required) | On-premise: ✅"
    }

if __name__ == "__main__":
    config = json.loads(Path(sys.argv[1]).read_text())
    result = calculate_tco(config)
    for k, v in result.items():
        print(f"{k}: {v}")
```

**Example config (`tco_config.json`):**
```json
{
  "monthly_sessions": 500,
  "avg_tokens_per_session": 80000,
  "hardware_cost": 10000,
  "hardware_power_kwh": 0.45,
  "electricity_price": 0.35,
  "it_hours_per_month": 2,
  "it_hourly_rate": 75
}
```

---

## 10. Collaboration & Cross-References

**Dependencies:**
- `open-source-audit-agent-framework.md` — software stack (Ollama + router) that runs on the hardware described here; this plan is the hardware complement to that plan
- `always-on-audit-agent.md` — Clawdbot's Ollama fallback becomes primary when on-premise hardware is available
- `saaf-strapi-synthetic-data.md` — Strapi sandbox can run on the same on-premise server

**This plan should be read before:**
- Any SAAF participant considering replacing cloud API calls with local inference
- Any organization that wants to process real (non-synthetic) data in SAAF agents

**NVIDIA hardware references:**
- NVIDIA DGX H100: https://www.nvidia.com/en-us/data-center/dgx-h100/
- NVIDIA GB200 NVL72 (Blackwell rack): https://www.nvidia.com/en-us/data-center/gb200-nvl72/
- NVIDIA RTX 6000 Ada Generation: workstation GPU for SMB audit teams
- NVIDIA NIM inference microservices: https://www.nvidia.com/en-us/ai/

---

## 11. PDCA

| Phase | Status | Notes |
|---|---|---|
| **Plan** | ✅ Complete | This document |
| **Do** | Pending | Hackathon #3 task: run the TCO calculator for your own organization's usage profile |
| **Check** | Not started | Validate TCO model against actual invoices from organizations that have already purchased GPU hardware |
| **Act** | Not started | Update hardware price table annually (GPU prices drop ~30%/year); update recommended models as open-source model quality improves |

**Hackathon #3 task (Analyst or Auditor role):**
Fill in `tco_config.json` with your organization's actual API usage from the last 3 months. Run `tco_calculator.py`. Report: what is your breakeven month? Does the data sovereignty trigger (GDPR Art. 28) apply to your agents?

---

## 12. Open Questions

1. **Leasing vs. purchase**: Major vendors (Dell, HP, NVIDIA partners) offer GPU server leasing at €2,000–€5,000/month. For organizations that cannot make a €50K+ capital purchase, is leasing a viable route? What are the data sovereignty implications of leased hardware?
2. **Shared service**: Should IIA Nederland facilitate a shared GPU inference service for member organizations (like a "SAAF Compute Cooperative")? Members pay per month; data stays in NL data center; eliminates per-organization procurement.
3. **Model quality gap**: For complex audit reasoning (finding drafts, regulatory assessment), Llama 3.1 70B approaches but does not match Claude Sonnet quality. At what model size / quantization level is the quality gap acceptable for audit use?
4. **Fine-tuning vs. RAG**: Fine-tuning a local model on organization-specific audit methodology requires DGX-tier hardware. Is fine-tuning worth the cost, or is RAG (ChromaDB + retrieval) a sufficient alternative that works on RTX workstation-tier hardware?
5. **Power and cooling**: A DGX H100 draws 10 kW continuously. Most office environments cannot support this without data center infrastructure. What are the minimum facility requirements, and should this be co-located in an existing data center?
