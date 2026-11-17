# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | P. Papen |
| **Organisation** | TBD |
| **Session** | Hackathon 4 (Session 5) |
| **Type** | Agent |
| **Status** | Draft |
| **Claimed By** | P. Papen |

---

## 2. Problem Statement

The Mollie audit-planning pipeline already has well-designed individual agents: the
[RCM Builder (UC7)](../hackathon-2/frank-van-dissel-uc7-rcm-builder.md) synthesises a Risk and
Control Matrix, the [Work Program Agent (UC8)](../hackathon-2/frank-van-dissel-uc8-audit-work-program.md)
turns that RCM into detailed test procedures and resource assignments, and the
[Quality & Resource Guard (UC9)](../hackathon-2/frank-van-dissel-uc9-quality-resource-guard.md)
performs a GIAS compliance and Go/No-Go review. Today these run as **separate manual steps**: an
auditor invokes UC7, hand-carries its JSON into UC8, then hand-carries UC8's output into UC9, and
if UC9 returns a "No-Go" the auditor manually decides which upstream agent to re-run and with what
correction. The hand-offs are error-prone (schema drift between stages, lost traceability), the
ordering logic lives in a human's head, and there is no single artifact that records the whole run.

This plan builds an **Audit Planning Orchestrator**: a single LLM "command" agent that runs and
commands UC7, UC8 and UC9 as sub-agents. It decides the order, passes each stage's structured output
to the next, validates the schema at every hand-off, and — when UC9 flags a No-Go — routes control
back to the right upstream agent instead of stopping. The output is one auditable planning package
plus a run log of every agent call, directly answering the Hackathon design questions: *which agent
runs in which order, how they communicate, what the input/intermediate/output are, and where the
quality criteria are enforced.*

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Multi-Agent Orchestration (GIAS 13.2–13.6)

**Applicable standards:**

- GIAS 13.2–13.6 — Risk assessment, RCM, work program, resources, and CAE approval (enforced by the sub-agents)
- IIA IPPF Standard 2340 — Engagement Supervision (the orchestrator produces the supervision audit trail)
- ISO/IEC 42001 — AI management systems (traceable, reviewable AI decisions)

**In scope:**

- An LLM orchestrator agent that drives three sub-agents via tool-calls: UC7 → UC8 → UC9
- A tool interface (one tool per sub-agent) that each wraps a single Claude API call with that
  agent's system prompt
- Structured JSON hand-off between stages with schema validation at every boundary
- Conditional control flow: on a UC9 "No-Go", route back to UC7 or UC8 with the specific gap, and
  re-run (bounded retry, e.g. max 2 loops)
- A per-run audit trail (JSONL) recording every agent call, input digest, output digest, and verdict
- A single combined output package (RCM + Work Program + CAE Approval/No-Go)

**Out of scope:**

- The internal logic of UC7/UC8/UC9 themselves — they are consumed as designed, not redesigned here
- Upstream UC1–UC6 (the orchestrator starts from a provided risk-input bundle; UC1–UC6 integration
  is a stretch goal)
- Fieldwork execution and evidence testing
- A GUI orchestration dashboard (see [`audit-agent-gamified-ui`](../hackathon-3/audit-agent-gamified-ui.md))

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New orchestrator system prompt (`prompts/audit-use-cases/audit-planning-orchestrator.md`); reuse the UC7/UC8/UC9 system prompts as the sub-agent prompts |
| **Tools** | New Python package `tools/scripts/audit_planning_orchestrator/`: orchestrator loop, three sub-agent tool wrappers, schema validator, run logger |
| **Regulatory** | Reuse GIAS 13.2–13.6 as the compliance benchmark inside UC9; reuse `regulatory/control-mappings/` for taxonomy |
| **Outputs** | Combined planning package (JSON) + per-run audit trail (JSONL); RCM rows and work-program tasks align with `outputs/schemas/finding-schema.json` conventions |

---

## 5. Prompts

### System prompt (draft — Orchestrator)

```
You are the Audit Planning Orchestrator. You do not perform audit analysis yourself.
Your job is to plan and control a pipeline of three specialist sub-agents to turn a set of
risk inputs into a CAE-ready audit planning package, and to record what you did.

Available sub-agents (call them as tools, one at a time):
- run_rcm_builder(inputs)      -> UC7: builds the Risk and Control Matrix (RCM)
- run_work_program(rcm)        -> UC8: builds the engagement Work Program from an RCM
- run_quality_guard(package)   -> UC9: reviews the package for GIAS 13.2-13.6 compliance and
                                  returns a Go / No-Go verdict with specific gaps

Rules of orchestration:
1. Default order is UC7 -> UC8 -> UC9. Never call UC8 before a valid RCM exists; never call UC9
   before a Work Program exists.
2. After every sub-agent call, check the returned status. If a tool reports a schema or validation
   error, do not pass the bad output downstream — stop and report it.
3. If UC9 returns "No-Go", read its "gaps" list. Decide which upstream agent must be re-run:
   - Gap about a risk/control that is missing, orphaned, or mis-scored  -> re-run run_rcm_builder
   - Gap about a test procedure, methodology, evidence, or resourcing   -> re-run run_work_program
   Re-run only the smallest necessary part, passing UC9's gap text as a correction instruction.
4. Do not loop forever. Allow at most 2 correction cycles; if still No-Go, hand the package back to
   the human auditor with UC9's outstanding gaps clearly listed.
5. Explain each decision in one short sentence before you act (which agent, why now).

You succeed when UC9 returns "Go", or when you have exhausted the retry budget and produced a clear
No-Go summary for human review. Maintain full traceability: every risk in the RCM must trace to a
source input, and every work-program task must trace to an RCM control.
```

### Example user prompts

**Prompt 1 — full run from a risk-input bundle:**
```
Run the audit planning pipeline for the "Accounts Payable" engagement.
Inputs (already consolidated from UC1-UC6):
- process_map: 3 sub-processes (Invoice Receipt, Approval, Payment) with business objectives
- risks: [historical findings, incident clusters, fraud scenarios, DORA regulatory criteria]
- auditor_directory: [Data Specialist (Python/SQL), Senior Auditor (process)]
- available_hours: 160
Produce the full planning package and tell me the final UC9 verdict.
```

**Prompt 2 — resumed run after a known gap:**
```
UC9 previously returned No-Go with gap: "Sub-process 'Payment' has no associated risk (scoping gap)."
Re-run only what is needed to close this gap and re-review. Do not rebuild the whole work program
if the RCM fix does not change the existing tasks.
```

**Intended file location:** `prompts/audit-use-cases/audit-planning-orchestrator.md`

---

## 6. Tools and Techniques

### Approach

The orchestrator is an **LLM agent that uses tool-calls** (Claude API tool use / an agentic loop).
It is deliberately *not* a hard-coded pipeline: the model receives the three sub-agents as tools and
the system prompt above, and chooses which to call and when. This makes the ordering, the schema
gate, and the No-Go recovery loop explicit and inspectable — exactly the "how do agents communicate
and in which order do they run" questions from the brief.

Each sub-agent is a **thin tool wrapper** around a single Claude API call:

1. `run_rcm_builder(inputs)` — loads the UC7 system prompt, sends `inputs`, parses the JSON RCM,
   validates it against `rcm.schema.json`, returns `{status, rcm}` or `{status: "error", detail}`.
2. `run_work_program(rcm)` — loads the UC8 system prompt, sends the validated RCM, returns
   `{status, work_program, resource_report}`.
3. `run_quality_guard(package)` — loads the UC9 system prompt, sends RCM + work program, returns
   `{status, verdict: "Go"|"No-Go", gaps: [...], approval_package?}`.

**Communication contract (how agents talk to each other):** every hand-off is a JSON document
written to a per-run directory `runs/<run_id>/` (e.g. `01_rcm.json`, `02_work_program.json`,
`03_quality.json`). Tools return the same JSON to the orchestrator. This gives both machine hand-off
and a human-readable artifact of the intermediate results.

**Quality criteria and where they live:** two layers. (a) *Structural* — a JSON-schema validator runs
at every boundary, so a malformed RCM can never reach UC8. (b) *Substantive* — UC9 is the audit
quality gate (GIAS 13.2–13.6, resource sufficiency, traceability); its verdict drives the retry loop.

### Example script or pseudocode

```python
# tools/scripts/audit-planning-orchestrator/orchestrator.py
from typing import Optional

def run_pipeline(inputs: dict, run_id: str, max_retries: int = 2) -> dict:
    """LLM orchestrator loop. The model decides the calls; this loop executes them
    and enforces the retry budget and schema gates."""
    tools = [RCM_BUILDER_TOOL, WORK_PROGRAM_TOOL, QUALITY_GUARD_TOOL]
    messages = [{"role": "user", "content": build_kickoff(inputs, run_id)}]
    retries = 0

    while True:
        response = claude_call(system=ORCHESTRATOR_PROMPT, messages=messages, tools=tools)
        log_agent_turn(run_id, response)                      # audit trail (JSONL)

        if response.stop_reason != "tool_use":
            return finalize(run_id, response)                 # orchestrator is done

        for call in response.tool_calls:
            result = dispatch(call, run_id)                   # runs UC7/UC8/UC9 wrapper
            validate_schema(call.name, result)                # structural quality gate
            if is_quality_guard(call) and result["verdict"] == "No-Go":
                retries += 1
                if retries > max_retries:
                    result["escalate_to_human"] = True        # bounded loop
            messages.append(tool_result_message(call, result))

def dispatch(call, run_id) -> dict:
    inputs = call.arguments
    system = load_subagent_prompt(call.name)                  # UC7 / UC8 / UC9 system prompt
    raw = claude_call(system=system, messages=[{"role": "user", "content": inputs}])
    out = parse_json(raw)
    write_artifact(run_id, call.name, out)                    # runs/<run_id>/*.json hand-off
    return out
```

**Tech stack used:** Python 3.9+ (`pathlib`, `typing.Optional`, `logging` at INFO),
Claude API — `claude-opus-5` for the orchestrator and UC7/UC8 synthesis,
`claude-sonnet-5` for UC9 validation. Dependency-free structural validation at each
boundary (pure Python, no `pip install` needed). API keys from environment variables only.

**Intended file location:** `tools/scripts/audit_planning_orchestrator/` (built — see its README)

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2–13.6 | Risk assessment, RCM, work program, resources, CAE approval — enforced inside UC7/UC8/UC9 |
| IIA IPPF 2340 | Engagement supervision — the orchestrator's run log is the supervision trail |
| ISO/IEC 42001 | Traceable, reviewable AI decision-making across the multi-agent run |

### Claude / AI tool usage notes

All inputs are planning documents — no real audit evidence or personal data. Risk inputs from
UC1–UC6 must be anonymised before entering the pipeline. The auditor directory holds role-based
skill tags and availability only, never personal information. The orchestrator writes only to its
own `runs/` directory under `tools/scripts/`.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (combined planning package) + JSONL (audit trail)

**Schema reference:** RCM rows and work-program tasks follow the UC7/UC8 schemas; findings/gaps
align with `outputs/schemas/finding-schema.json` conventions.

### Synthetic example output

```json
{
  "run_id": "ap-2026-09-08-001",
  "engagement": "Accounts Payable",
  "final_verdict": "Go",
  "cycles": 2,
  "stages": {
    "uc7_rcm": "runs/ap-2026-09-08-001/01_rcm.json",
    "uc8_work_program": "runs/ap-2026-09-08-001/02_work_program.json",
    "uc9_quality": "runs/ap-2026-09-08-001/03_quality.json"
  },
  "orchestrator_log": [
    {"turn": 1, "action": "run_rcm_builder", "reason": "No RCM exists yet", "status": "ok"},
    {"turn": 2, "action": "run_work_program", "reason": "Valid RCM available", "status": "ok"},
    {"turn": 3, "action": "run_quality_guard", "reason": "Package complete", "verdict": "No-Go",
     "gaps": ["Sub-process 'Payment' has no associated risk (scoping gap)"]},
    {"turn": 4, "action": "run_rcm_builder", "reason": "UC9 gap is a scoping/risk issue", "status": "ok"},
    {"turn": 5, "action": "run_quality_guard", "reason": "Re-review after RCM fix", "verdict": "Go"}
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (`claude-opus-5`) with tool use
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [x] Dependency-free structural validation at each boundary
- [ ] Strapi (synthetic AP dataset for the demo — optional)

**Stretch goals:**

- [ ] Wire in UC1–UC6 as upstream sub-agents (full 9-agent pipeline)
- [ ] Swap the custom loop for the [Audit Loop Orchestration SDK](../hackathon-3/audit-loop-orchestration-sdk.md) primitives
- [ ] Live run view / progress UI for the 3-minute demo

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The orchestrator system prompt and the three sub-agent tool definitions
- The JSON hand-off contract and per-boundary schemas (reusable by any UC7/UC8/UC9 implementation)
- A synthetic Accounts Payable input bundle for end-to-end testing

**What help I'm looking for:**

- The UC7/UC8/UC9 authors (Mollie — Frank van Dissel & Lauren Browne) to confirm the tool
  input/output contracts match their agents
- Alignment with [Floris Stokkers](../hackathon-2/floris-stokkers-work-program-agent.md) and
  [Inge Garretsen](../hackathon-2/inge-garretsen-audit-work-program-agent.md) on the work-program schema

**Cross-org interest:**

This is infrastructure any team chaining audit agents needs. Related:
[Audit Loop Orchestration SDK](../hackathon-3/audit-loop-orchestration-sdk.md),
[Audit Subagent Coordination Framework](../hackathon-3/audit-subagent-coordination-framework.md).

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | This document |
| **Do** | In progress | Working prototype built: `tools/scripts/audit_planning_orchestrator/` (LLM loop + schema gates + bounded No-Go recovery + audit trail) |
| **Check** | In progress | Offline `--simulate` run confirms the No-Go loop closes the seeded "Payment" scoping gap and reaches Go; API-backed run to be validated at Hackathon 4 |
| **Act** | Not started | Target: adopt as the standard chaining layer for the Mollie planning pipeline |

---

## 12. Open Questions

1. Should the orchestrator re-run a full upstream agent on a No-Go, or pass the gap as a targeted
   "patch this only" instruction to keep the untouched parts stable?
2. Where is the exact input/output contract for UC7/UC8/UC9 authoritative — do we freeze JSON schemas
   in this repo so any implementation is swappable behind the tool wrappers?
3. Should the retry budget and the UC7-vs-UC8 routing rule be model-decided (as drafted) or hard-coded
   for auditability? Trade-off: flexibility vs. a deterministic, reviewable control flow.
