# UC7 Voice Walkthrough (ElevenLabs → UC7 RCM Builder)

A voice front-end for the [UC7 RCM Builder](../../../plans/hackathon-2/frank-van-dissel-uc7-rcm-builder.md).
An **ElevenLabs Conversational-AI agent** conducts an internal-audit process
walkthrough by voice, asks audit-grade probing questions, and calls UC7 to build
the Risk and Control Matrix live — then reads the result back for confirmation.

Two AI systems, one integration: **ElevenLabs** owns the real-time voice loop
(STT + TTS + turn-taking); **Claude (UC7)** owns the audit synthesis. They are
connected through ElevenLabs **client tools** — the agent calls local Python
functions during the conversation, so no public webhook or tunnel is needed.

Design + rationale:
[`plans/hackathon-4/p-papen-uc7-voice-rcm-walkthrough.md`](../../../plans/hackathon-4/p-papen-uc7-voice-rcm-walkthrough.md).

## Run it

All commands run from the **repo root**.

### Offline — no API key, no microphone (start here)

```bash
python -m tools.scripts.uc7_voice_walkthrough.walkthrough --simulate
```

Replays a scripted synthetic walkthrough
([`sample_data/walkthrough_accounts_payable.json`](sample_data/walkthrough_accounts_payable.json))
through the **same two client tools** the live agent uses. You see each captured
risk/control, then the built RCM and the spoken summary — including the seeded
control gaps on *Invoice Approval* and *Payment*. Output lands in
`runs/<session>/` (`rcm.json` + `transcript.jsonl`).

### Live — talk to the agent

```bash
export ELEVENLABS_API_KEY=...            # PowerShell: $env:ELEVENLABS_API_KEY="..."
export ELEVENLABS_AGENT_ID=agent_...     # the agent you created (see below)
export ANTHROPIC_API_KEY=sk-ant-...      # optional: enables UC7 refine (dedup + scoring)
python -m tools.scripts.uc7_voice_walkthrough.walkthrough --live
```

Speak the process-owner side of the walkthrough; the agent interviews you,
captures risks/controls, builds the RCM, and voices the summary back. `Ctrl+C`
ends the session.

## Create the ElevenLabs agent

Print the agent definition and create it in the ElevenLabs dashboard (or push it
with the ElevenLabs CLI), then set `ELEVENLABS_AGENT_ID`:

```bash
python -m tools.scripts.uc7_voice_walkthrough.agent_config
```

The definition includes the interviewer system prompt and the two **client
tools** (`capture_control`, `build_rcm`) that this package registers by name.

## Files

| File | Role |
|---|---|
| `walkthrough.py` | Runner — `--simulate` (offline) and `--live` (ElevenLabs voice), CLI |
| `rcm_tools.py` | `RcmSession`: the `capture_control` / `build_rcm` client tools, RCM assembly, schema gate, UC7 refine, transcript log |
| `agent_config.py` | ElevenLabs agent system prompt + client-tool declarations (print to set up the agent) |
| `sample_data/` | Synthetic Accounts Payable walkthrough script |

## How UC7 is reused

`build_rcm` assembles a candidate RCM from the captured items and validates it
with the orchestrator's schema gate
([`audit_planning_orchestrator/schemas.py`](../audit_planning_orchestrator/schemas.py)).
When an `ANTHROPIC_API_KEY` is present, it then refines that RCM through the UC7
wrapper ([`audit_planning_orchestrator/sub_agents.py`](../audit_planning_orchestrator/sub_agents.py))
for deduplication and scoring. Offline `--simulate` skips the refine and stays on
the deterministic local assembly, so it needs no key.

## Notes

- `--simulate` uses only the Python standard library (plus the local schema
  module). `elevenlabs[pyaudio]` is needed only for `--live`; `anthropic` only
  for UC7 refine.
- **Synthetic data only.** A real walkthrough recording is personal data — this
  package records and processes scripted synthetic interviews only. Audio goes to
  ElevenLabs and captured risk text to the Claude API; both keys come from the
  environment.
- `runs/` is gitignored — it holds generated RCM + transcript output.
