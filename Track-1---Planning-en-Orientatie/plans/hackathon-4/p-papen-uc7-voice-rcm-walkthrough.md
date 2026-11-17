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

Building a Risk and Control Matrix (RCM) starts with a **process walkthrough** — an
auditor interviews a process owner to learn how a process works and what can go
wrong. Today this is a manual interview: the auditor talks, scribbles notes,
and later re-types risks and controls into a spreadsheet. The re-typing is slow,
notes lose nuance, and the structured RCM is only produced hours later, away from
the person who has the answers.

The [RCM Builder (UC7)](../hackathon-2/frank-van-dissel-uc7-rcm-builder.md)
already turns structured risk inputs into an RCM. This plan puts a **voice
front-end** on it: an ElevenLabs Conversational-AI agent conducts the walkthrough
interview by voice — asking audit-grade probing questions ("who approves this?",
"is that control automated?"), capturing each risk/control pair as it is spoken,
and, at the end of the conversation, calling UC7 to synthesise the structured,
deduplicated RCM and reading the result back for confirmation. The auditor gets a
validated RCM by the time the interview ends, in the room, hands-free.

This is the **ElevenLabs track** entry ("prize for the best integration"): two AI
systems working together — ElevenLabs owns the real-time voice conversation
(STT + TTS + turn-taking), Claude (UC7) owns the audit synthesis — connected
through ElevenLabs **client tools** that call the UC7 pipeline live.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit Planning — Process Walkthrough & RCM (GIAS 13.2, 13.6)

**Applicable standards:**

- GIAS 13.2 — Evaluating and prioritising risks by linking them to business objectives
- GIAS 13.6 — RCM as the foundation ("Criteria" and "Tasks") for the work program
- IIA IPPF 2340 — Engagement supervision (the conversation transcript + tool log is the trail)

**In scope:**

- An ElevenLabs Conversational-AI agent configured as an internal-audit walkthrough interviewer
- Two **client tools** that call local Python during the live conversation:
  `capture_control` (records a risk/control pair as it is elicited) and
  `build_rcm` (hands the captured items to UC7, validates, returns a spoken summary)
- Reuse of the UC7 RCM Builder (`claude-opus-5`) for deduplication, scoring, and RCM shaping
- Structural validation of the produced RCM (reuse the orchestrator's schema gate)
- A per-session artifact + transcript log; a spoken read-back of the RCM and any scoping gaps
- An offline `--simulate` harness that drives the same tool bridge from a scripted
  synthetic walkthrough (no microphone, no ElevenLabs, no API key)

**Out of scope:**

- The downstream Work Program (UC8) and Quality gate (UC9) — this front-ends UC7 only
  (it plugs into the [orchestrator](p-papen-audit-planning-orchestrator.md) as the input stage)
- Voice cloning or custom-voice design (use a stock ElevenLabs voice)
- Recording or processing **real** interviews (personal data — synthetic scripts only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | ElevenLabs agent system prompt (audit walkthrough interviewer) + client-tool declarations; reuse the UC7 RCM Builder prompt |
| **Tools** | New Python package `tools/scripts/uc7_voice_walkthrough/`: ElevenLabs conversation runner, `capture_control` / `build_rcm` client tools, offline simulate harness; reuse `audit_planning_orchestrator` (UC7 wrapper + schema gate) |
| **Regulatory** | GIAS 13.2, 13.6; IIA 2340 supervision trail |
| **Outputs** | RCM JSON (UC7 schema) + a session transcript/tool log; a spoken summary |

---

## 5. Prompts

### System prompt (draft — ElevenLabs walkthrough agent)

```
You are an internal audit assistant conducting a process walkthrough by voice.
You are interviewing the owner of the [process] process to build a Risk and
Control Matrix. Speak in short, natural spoken turns — one question at a time.

Walk through the process sub-process by sub-process. For each step:
1. Ask how the step works and what its objective is.
2. Ask what could go wrong (the risk).
3. Ask what prevents or detects that (the control): who performs it, is it
   manual or automated, how often.
When you have a clear risk + control pair, call the `capture_control` tool.
If a step has no control, say so and still call `capture_control` with an empty
control so the gap is recorded.

Do not invent risks the owner did not confirm. When the owner says the
walkthrough is complete, confirm the number of items captured, then call
`build_rcm`. Read back the summary it returns — the risk count and any
sub-process with no control — and ask the owner to confirm or correct it.
```

### Example user prompts (spoken turns the agent will hear)

**Prompt 1 — process owner describing a step:**
```
"When an invoice comes in, it lands in a shared mailbox. Someone in AP keys it
into the ERP and matches it to the purchase order and the goods receipt."
```

**Prompt 2 — process owner answering a control probe:**
```
"The duplicate-payment check is automatic — the system blocks anything with the
same supplier, amount and date. But for approvals, honestly, it's whoever is
around; there's no hard segregation between who raises the PO and who approves."
```

**Intended file location:** `prompts/audit-use-cases/uc7-voice-walkthrough-agent.md`

---

## 6. Tools and Techniques

### Approach

ElevenLabs runs the voice loop; our Python provides the two **client tools** the
agent calls. Client tools (not webhooks) let the agent invoke functions in the
running process, so the prototype is fully local — no public endpoint or tunnel.

1. **Conversation runner** — builds `ElevenLabs(api_key=...)`, registers the two
   tools on a `ClientTools()`, and starts a `Conversation(..., client_tools=...,
   audio_interface=DefaultAudioInterface())` session against the agent id.
2. **`capture_control(parameters)`** — appends `{sub_process, business_objective,
   risk_description, control_description, control_type, source}` to the session
   and returns a one-line spoken confirmation.
3. **`build_rcm(parameters)`** — assembles a candidate RCM from the captured
   items, validates it against the schema gate, and (when an Anthropic key is
   present) refines it through **UC7** for deduplication and scoring. Writes the
   RCM + transcript artifact and returns a spoken summary (risk count, scoping
   gaps) — `expects_response: true` so the agent voices it back.

**Offline path:** `--simulate` replays a scripted synthetic walkthrough
(`sample_data/walkthrough_accounts_payable.json`) through the *same* two tool
functions — proving the wiring, the schema gate, and the read-back summary with
no microphone, no ElevenLabs and no API key.

### Example script or pseudocode

```python
from elevenlabs import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation, ClientTools
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

session = RcmSession(process_map)                 # holds captured items + state
tools = ClientTools()
tools.register("capture_control", session.capture_control)   # params -> confirmation
tools.register("build_rcm", session.build_rcm)               # params -> spoken summary

Conversation(
    client=ElevenLabs(api_key=EL_KEY),
    agent_id=AGENT_ID,
    requires_auth=True,
    client_tools=tools,
    audio_interface=DefaultAudioInterface(),
).start_session()
```

**Tech stack used:** Python 3.9+, ElevenLabs Agents Python SDK (`elevenlabs[pyaudio]`),
Claude API (`claude-opus-5`) via the reused UC7 wrapper, dependency-free schema
validation. ElevenLabs and Anthropic API keys from environment variables only.

**Intended file location:** `tools/scripts/uc7_voice_walkthrough/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GIAS 13.2 | Risk evaluation and prioritisation, linked to objectives |
| GIAS 13.6 | RCM as the work-program foundation |
| IIA IPPF 2340 | Supervision — transcript + tool log as the engagement trail |

### Claude / AI tool usage notes

**Personal data is the key risk here:** a real walkthrough recording contains
voices and names (personal data) and confidential process detail. This
prototype records and processes **synthetic, scripted** interviews only. Audio
is streamed to ElevenLabs and captured risk text to the Claude API, so no real
audit evidence or interviewee data may be used. Both API keys come from the
environment; nothing is hardcoded or committed.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** RCM JSON (UC7 schema) + a session transcript/tool log (JSONL)

**Schema reference:** the RCM conforms to the UC7 RCM schema validated by
`audit_planning_orchestrator/schemas.py`.

### Synthetic example output (spoken read-back, then the RCM row it summarises)

> "I captured 4 risks across 3 sub-processes. One gap: the *Payment* step has a
> risk but no control. Shall I flag that for follow-up?"

```json
{
  "rcm": [
    {
      "risk_id": "R-P01-001",
      "sub_process": "Invoice Approval",
      "business_objective": "Ensure only valid, authorized invoices are approved",
      "risk_description": "Invoices may be approved without segregation of duties",
      "risk_sources": ["Walkthrough — process owner, AP"],
      "inherent_risk": {"impact": "High", "likelihood": "Medium", "rating": "High"},
      "control_id": "C-P01-001",
      "control_description": "Automated duplicate-payment check on supplier + amount + date",
      "control_type": "Automated",
      "control_frequency": "Every transaction",
      "residual_risk": {"impact": "High", "likelihood": "Low", "rating": "Medium"}
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] ElevenLabs Agents Python SDK (Conversational AI + client tools)
- [x] Claude API (`claude-opus-5`) via the reused UC7 wrapper
- [x] Python 3.9+
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Configure the ElevenLabs agent's LLM to be Claude, so the whole voice stack is Claude-driven
- [ ] Feed the produced RCM straight into the [orchestrator](p-papen-audit-planning-orchestrator.md) (UC7 → UC8 → UC9) for an end-to-end voice-to-work-program demo
- [ ] TTS read-back of the UC9 No-Go gaps

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The ElevenLabs agent system prompt + client-tool declarations
- The `capture_control` / `build_rcm` tool bridge and the offline simulate harness
- A synthetic Accounts Payable walkthrough script for end-to-end testing

**What help I'm looking for:**

- Auditors to validate that the agent's probing questions are walkthrough-appropriate
- Anyone with ElevenLabs agent experience to review the tool schema and turn-taking

**Cross-org interest:**

Voice front-ends are reusable across every SAAF agent. Related:
[UC7 RCM Builder](../hackathon-2/frank-van-dissel-uc7-rcm-builder.md),
[Audit Planning Orchestrator](p-papen-audit-planning-orchestrator.md).

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | This document |
| **Do** | In progress | Working prototype: `tools/scripts/uc7_voice_walkthrough/` (client-tool bridge + offline simulate; live voice path pending an ElevenLabs key + mic on the day) |
| **Check** | In progress | Offline `--simulate` confirms capture → build_rcm → validated RCM + spoken summary; live voice run to be validated at Hackathon 4 |
| **Act** | Not started | Target: chain the voice front-end into the full UC7 → UC8 → UC9 orchestrator |

---

## 12. Open Questions

1. Should `capture_control` store the risk exactly as spoken and leave all
   dedup/scoring to UC7, or pre-structure during the interview? (Trade-off:
   fidelity to the owner's words vs. a cleaner live read-back.)
2. Should the agent's own LLM be Claude (via ElevenLabs' LLM config) for a fully
   Claude-driven stack, or is the default agent LLM sufficient for turn-taking?
3. How do we handle multi-speaker walkthroughs (several process owners) — does
   the transcript need speaker attribution for the supervision trail?
