# Audit Sub-Agent Coordination Framework

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

Single-agent audit analysis is subject to model bias: a single Claude instance will consistently produce similar findings, miss the same blind spots, and apply the same interpretation of ambiguous criteria. In high-stakes audit domains (fraud risk, DORA ICT risk, vendor assessment), a single AI assessment is insufficient.

Real audit teams use multiple reviewers for a reason: different perspectives, different risk weightings, different interpretations of gray areas. This plan replicates that pattern with AI: multiple independent agents assess the same risk, then reconcile their differences, and produce a consensus finding.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Agent Infrastructure / High-Stakes Findings

**Applicable standards:**

- IIA IPPF — Standard 1200 (Proficiency and Due Professional Care), 2340 (Engagement Supervision)
- ISO 42001 — AI system risk management

**In scope:**

- Orchestrated execution of 3-5 independent Claude agents assessing the same audit risk or control
- Each agent uses a different system prompt persona (strict auditor, risk-skeptic, business-side perspective)
- Debate round: agents receive each other's assessments and are asked to identify disagreements
- Consensus synthesis: orchestrator produces a final finding that incorporates all perspectives
- Shared task list + mailbox pattern for inter-agent communication

**Out of scope:**

- Real-time agent communication (agents run sequentially, not in parallel threads)
- Human-in-the-loop mid-debate (agent personas are fixed; human review is post-consensus)
- More than 5 agents per assessment (diminishing returns above 5)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | 5 distinct agent persona system prompts; debate round prompt; consensus synthesis prompt |
| **Tools** | `tools/scripts/multi-agent-audit.py` — orchestrator that runs agents, routes debate messages, synthesizes consensus |
| **Regulatory** | IIA 1200 (due professional care) — multi-agent debate raises the quality bar for AI findings |
| **Outputs** | Consensus finding (finding-schema.json) with attached dissenting notes from individual agents |

---

## 5. Prompts

### System prompt (draft) — Agent A (Strict Risk Auditor)

```
You are a strict internal audit risk assessor.
Your bias: err on the side of risk. When in doubt, rate higher.
When assessing the evidence provided:
1. Identify all control gaps, no matter how minor
2. Rate each gap using: High / Medium / Low / Informational
3. Cite the specific standard or criterion violated for each gap
4. Do not consider business context or mitigating factors in your initial assessment
Return your assessment as JSON: {findings: [{control_gap, risk_rating, criterion, observation}]}
```

### System prompt (draft) — Agent B (Risk-Skeptic Auditor)

```
You are a pragmatic internal audit risk assessor.
Your bias: challenge risk over-ratings. Ask: is there evidence of actual harm?
When assessing the evidence provided:
1. Evaluate only control gaps with evidence of operational impact
2. Distinguish design gaps (policy says nothing) from operating gaps (policy exists but not followed)
3. Apply professional skepticism to claimed mitigating controls
4. Rate conservatively — only High if evidence clearly supports it
Return your assessment as JSON: {findings: [{control_gap, risk_rating, criterion, observation}]}
```

### Example user prompts

**Prompt 1 — Initial assessment:**
```
Assess the following vendor contract excerpt against DORA ICT third-party risk requirements (Art. 28-30).
[Attach synthetic vendor contract]
Identify all control gaps. Return structured JSON.
```

**Prompt 2 — Debate round:**
```
Agent A assessed this risk as High. Agent B assessed it as Medium.
Agent A's rationale: [paste]
Agent B's rationale: [paste]
You are Agent C (Business Perspective). Review both assessments.
Where do you agree? Where do you disagree and why?
What additional information would resolve the disagreement?
```

**Intended file location:** `prompts/audit-use-cases/multi-agent-audit-debate.md`

---

## 6. Tools and Techniques

### Approach

The orchestrator runs agents sequentially:
1. **Round 1**: All agents receive the same evidence and produce independent assessments (no communication)
2. **Round 2 (Debate)**: Each agent receives all Round 1 assessments and flags disagreements
3. **Round 3 (Consensus)**: A synthesis agent (different system prompt) receives all Round 1 + 2 outputs and produces the final consensus finding, noting any unresolved disagreements

The shared task list (JSON file) tracks which rounds are complete and stores each agent's output. The mailbox pattern: each agent has an inbox (list of messages from other agents) in the task file.

### Example script or pseudocode

```python
import anthropic, json
from pathlib import Path

client = anthropic.Anthropic()

AGENT_PERSONAS = {
    "strict":    STRICT_AUDITOR_PROMPT,
    "skeptic":   SKEPTIC_AUDITOR_PROMPT,
    "business":  BUSINESS_PERSPECTIVE_PROMPT,
    "technical": TECHNICAL_SPECIALIST_PROMPT,
    "regulator": REGULATOR_PROMPT,
}

def run_round1(evidence: str, task_file: Path) -> dict:
    task = json.loads(task_file.read_text())
    task["round1"] = {}
    for name, persona in AGENT_PERSONAS.items():
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=2048,
            system=persona,
            messages=[{"role": "user", "content": f"Assess this evidence:\n{evidence}"}]
        )
        task["round1"][name] = json.loads(response.content[0].text)
        print(f"  Round 1 — {name}: {len(task['round1'][name]['findings'])} findings")
    task_file.write_text(json.dumps(task, indent=2))
    return task["round1"]

def run_debate(round1: dict, task_file: Path) -> dict:
    task = json.loads(task_file.read_text())
    task["round2"] = {}
    for name, persona in AGENT_PERSONAS.items():
        others = {k: v for k, v in round1.items() if k != name}
        prompt = f"Your assessment: {json.dumps(round1[name])}\n" \
                 f"Other agents: {json.dumps(others)}\n" \
                 "Identify disagreements. What would you update and why?"
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=1024,
            system=persona,
            messages=[{"role": "user", "content": prompt}]
        )
        task["round2"][name] = response.content[0].text
    task_file.write_text(json.dumps(task, indent=2))
    return task["round2"]

def synthesize_consensus(round1: dict, round2: dict) -> dict:
    prompt = (
        f"Round 1 assessments: {json.dumps(round1)}\n"
        f"Debate round: {json.dumps(round2)}\n"
        "Produce the consensus finding. Note any unresolved disagreements."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=2048,
        system=CONSENSUS_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.content[0].text)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), JSON task files

**Intended file location:** `tools/scripts/multi-agent-audit.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 1200 | Proficiency and due professional care — multi-agent debate raises the quality and rigor of AI-assisted findings |
| IIA IPPF 2340 | Engagement supervision — consensus finding includes dissenting notes for supervisor review |
| ISO 42001 | AI system risk management — multi-agent debate is a bias-mitigation technique |

### Claude / AI tool usage notes

All agents run against synthetic or anonymized evidence. The consensus finding must be reviewed by a human auditor before entering the dossier. Multi-agent debate is a quality enhancement — it does not replace auditor judgment.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON consensus finding + Markdown debate summary

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output (consensus finding)

```json
{
  "id": "F-2026-042",
  "title": "DORA ICT Third-Party Risk: Missing SLA for Critical Vendor",
  "risk_rating": "High",
  "observation": "Vendor contract does not specify RTO/RPO for critical ICT services. Three of five agents rated this High; two rated Medium citing the vendor's informal SLA commitment in email.",
  "recommendation": "Negotiate a formal SLA addendum specifying RTO ≤ 4h and RPO ≤ 1h for Tier-1 services, per DORA Art. 30(2)(b).",
  "agent_agreement": "3/5 High, 2/5 Medium",
  "unresolved_disagreement": "Agents 'skeptic' and 'business' argue the email commitment is a valid mitigating control pending contract renewal. Auditor review required."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.9+
- [x] JSON task files (state management)
- [x] Strapi (synthetic vendor contracts and evidence)

**Stretch goals:**

- [ ] Parallel agent execution (asyncio) instead of sequential for faster runs
- [ ] Web UI showing each agent's assessment and disagreements in real time
- [ ] Configurable agent persona library (domain-specific personas per audit type)

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `multi-agent-audit.py` orchestrator
- 5 agent persona system prompts
- Consensus synthesis prompt
- Synthetic vendor contract test case

**Help requested:**

- Auditors: design additional agent personas (compliance officer, CFO perspective, data protection officer)
- Vaktechniek: validate that multi-agent consensus findings meet IIA quality standards
- Engineers: implement parallel execution for faster runtime

**Cross-org interest:**

Multi-agent debate is applicable to any high-stakes audit finding: DORA vendor assessments, GDPR DPIAs, fraud risk assessments. Organizations using this pattern for the same domain can compare their agent configurations.

**Market Precedents for Multi-Agent Coordination (April 2026):**

Several platforms are emerging that validate the multi-agent coordination approach and provide reference architectures:

- **AgentCraft** (`getagentcraft.com`): commercial multi-agent orchestration platform with a visual "agent market" where specialized agents are composed into workflows. AgentCraft's architecture — agent registry, capability matching, task routing — is a direct precedent for the SAAF coordination framework. Open-source elements from AgentCraft can be adapted for the SAAF context.
- **Robin's Rust Cockpit** (discussed in SAAF community, April 2026): Robin van der Werf demonstrated a Rust-based agent cockpit that runs multiple specialized sub-agents in parallel and aggregates their outputs via a consensus prompt. The Rust implementation achieves significantly lower latency than Python-based equivalents — relevant for audit use cases where response time matters (field queries, real-time control testing).
- **Paperclip.ing**: multi-agent marketplace where agents can be chained and their outputs composed. Demonstrated the "agent pipeline as API" pattern — each agent exposes a typed interface, and the orchestrator composes them without knowing their internals. This is the target architecture for SAAF: a `multi-agent-audit.py` orchestrator that treats each agent persona as a black-box API.

**Implication for SAAF:** The market is converging on standardized agent interfaces. SAAF's multi-agent debate framework should adopt a typed persona interface (`PersonaAgent.assess(finding: dict) -> PersonaAssessment`) now, so that future integration with AgentCraft or similar platforms requires only a thin adapter.

**Related SAAF plans:**

- [`overnight-audit-batch-processing-agent.md`](overnight-audit-batch-processing-agent.md) — multi-agent runs can be wrapped in batch overnight execution
- [`frank-van-dissel-uc4-fraud-risk-assessment.md`](../hackathon-2/frank-van-dissel-uc4-fraud-risk-assessment.md) — prime candidate for multi-agent debate
- [`icfcop-control-testing-agent.md`](icfcop-control-testing-agent.md) — multi-framework control testing benefits from agent debate
- [`audit-loop-orchestration-sdk.md`](audit-loop-orchestration-sdk.md) — SDK patterns for orchestrating multi-agent debates within a loop

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | 3-round debate architecture designed |
| **Do** | In progress | Hackathon #3: run 3-agent debate on DORA vendor contract assessment |
| **Check** | Not started | Compare consensus finding against expert auditor judgment |
| **Act** | Not started | Refine persona prompts based on debate quality assessment |

---

## 12. Open Questions

1. How many agents is optimal? 3 is fast; 5 gives more diversity but costs more and takes longer.
2. Should the debate round be a single pass or iterative (agents can update their assessment multiple times)?
3. How do we handle unanimous agreement — does the debate round add value, or should we skip it?
4. What confidence threshold makes the multi-agent pattern worth the 3-5× API cost?
