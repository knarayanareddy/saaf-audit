# Always-On Audit Agent

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten \| SAAF Project |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Audit agents today are "on-demand" — the auditor manually starts a Claude session, provides context, and gets a one-time output. When the auditor is in the field (client site, interview, physical walkthrough), there is no easy way to invoke an AI agent for quick lookups: "What does DORA say about this?" or "We found a segregation of duties issue — what's the standard finding template?"

Field auditors use smartphones. A 24/7 agent running on a local machine, accessible via text message or messaging app, would give field auditors instant access to audit intelligence without requiring a laptop or a cloud subscription.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Agent Infrastructure / Fieldwork Support

**Applicable standards:**

- IIA IPPF — Standard 1200 (Proficiency), 2310 (Identifying Information)
- GDPR — Art. 32 (Security of processing) — local-first architecture protects audit data

**In scope:**

- Always-on Claude agent running locally on the audit lead's machine (Clawdbot pattern)
- Accessible via text interface: SMS gateway, WhatsApp Business API, Telegram bot, or local web chat
- Queries: regulatory lookups, finding templates, past audit precedents (via audit memory system)
- Agent runs 24/7 without requiring the auditor to open a laptop
- Local model fallback (Ollama) when Claude API is unavailable

**Out of scope:**

- Multi-user shared agent (one agent per audit lead, not team-wide)
- Real-time system monitoring (separate agent type — see `saaf-intelligence-monitor.md`)
- Voice interface (future: Parakeet 3 integration)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Field-auditor system prompt; regulatory lookup prompt; finding template prompt |
| **Tools** | `tools/scripts/always-on-agent.py` — webhook server that receives messages and routes to Claude |
| **Regulatory** | GDPR Art. 32 — local processing; no audit data sent to external services |
| **Outputs** | Text responses to field queries; finding drafts sent back to auditor via same channel |

---

## 5. Prompts

### System prompt (draft)

```
You are a personal audit assistant running 24/7 on the audit lead's local machine.
You assist field auditors with:
- Quick regulatory lookups (DORA, GDPR, ISO 27001, NIS2)
- Finding templates and standard observations
- Precedent lookups from the audit knowledge base
- Criteria checklists for common control tests

Keep responses concise — the auditor is reading on a smartphone.
Limit answers to 3-5 sentences unless asked for detail.
Always cite the source standard with article/section number.
When generating finding text, use Condition / Criterion / Cause / Effect format.
You have no access to real client systems — respond only from your knowledge and the knowledge base.
```

### Example user prompts

**Prompt 1 — Regulatory lookup:**
```
DORA RTO requirements for critical ICT services — what exactly does the regulation say?
```

**Prompt 2 — Finding template:**
```
We found that system access is not removed within 24h after employee departure.
Draft a finding in C/C/C/E format citing ISO 27001 and any Dutch regulation that applies.
Keep it under 100 words.
```

**Intended file location:** `prompts/audit-use-cases/always-on-field-assistant.md`

---

## 6. Tools and Techniques

### Approach

A lightweight Python HTTP server runs on the audit lead's machine (port 5001). It receives POST requests from a messaging gateway (Telegram bot API, WhatsApp Business webhook, or simple SMS-to-HTTP bridge). On each message:

1. The server appends the message to a conversation history file (per day)
2. Calls the Claude API with the system prompt + recent conversation history
3. Returns Claude's response to the messaging channel

For offline scenarios (poor field connectivity), the server falls back to a local Ollama model (llama3 or GLM 4.7).

The Clawdbot pattern: the agent is "always listening" because the HTTP server runs as a system service (launchd on macOS, systemd on Linux).

### Example script or pseudocode

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, anthropic, subprocess
from pathlib import Path
from datetime import date

client = anthropic.Anthropic()
HISTORY_FILE = Path(f"data/agent-history-{date.today()}.jsonl")

class AuditAgentHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        user_message = body.get("message", "")

        # Load today's history
        history = []
        if HISTORY_FILE.exists():
            history = [json.loads(l) for l in HISTORY_FILE.read_text().splitlines()]

        history.append({"role": "user", "content": user_message})

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                system=FIELD_AUDITOR_SYSTEM_PROMPT,
                messages=history[-20:],  # last 20 turns
            )
            reply = response.content[0].text
        except Exception:
            # Fallback to local Ollama
            result = subprocess.run(
                ["ollama", "run", "llama3", user_message],
                capture_output=True, text=True, timeout=60
            )
            reply = result.stdout.strip()

        history.append({"role": "assistant", "content": reply})
        with open(HISTORY_FILE, "a") as f:
            f.write(json.dumps({"role": "user", "content": user_message}) + "\n")
            f.write(json.dumps({"role": "assistant", "content": reply}) + "\n")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"reply": reply}).encode())

    def log_message(self, *args):
        pass  # Suppress HTTP request logs

HTTPServer(("localhost", 5001), AuditAgentHandler).serve_forever()
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6), Ollama (fallback), Telegram Bot API or equivalent webhook

**Intended file location:** `tools/scripts/always-on-agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 1200 | Proficiency — the always-on agent supplements auditor knowledge, does not replace it |
| IIA IPPF 2310 | Identifying information — all agent responses are logged locally for audit trail |
| GDPR Art. 32 | Security of processing — agent runs locally; no client data or personal data is sent |

### Claude / AI tool usage notes

The always-on agent uses the Claude API for cloud access and Ollama locally as fallback. The agent has no access to client systems or databases — it answers from its own knowledge and the audit knowledge base (if integrated). Conversation logs are stored locally and should be treated as audit working papers.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Plain text (SMS/chat-optimized, ≤3-5 sentences unless asked for more)

**Schema reference:** `outputs/schemas/finding-schema.json` (when generating full findings)

### Synthetic example output (field lookup)

**Auditor input:** "DORA RTO for critical services?"

**Agent response:**
```
DORA Art. 11(4) requires ICT RTO for critical functions to be "as short as possible."
DORA's implementing technical standards (EBA/ITS/2024) specify maximum RTO of 2h for
Tier-1 critical services and 4h for Tier-2. Document your classification and agreed RTO
in the contract and BCP. Cite DORA Art. 11 + EBA ITS in any finding.
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] Claude API (claude-sonnet-4-6)
- [x] Simple HTTP server (stdlib `http.server`)
- [x] Telegram Bot API (webhook trigger — free, no app installation required)
- [x] Ollama (local fallback — llama3)

**Stretch goals:**

- [ ] Integration with audit memory system (query past findings from the field)
- [ ] Voice interface: Parakeet 3 STT → always-on agent → TTS response
- [ ] Multi-user: team-shared agent with per-user conversation isolation

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `always-on-agent.py` server script
- Field auditor system prompt
- Setup guide for Telegram bot integration and macOS launchd configuration

**Help requested:**

- Field auditors: what are the 10 most common questions you ask during fieldwork? (prompt library seed)
- Engineers: build a proper daemon setup (Docker container with restart policy)
- Security reviewers: validate that local HTTP server is acceptably secure for this use case

**Cross-org interest:**

Any organization with field auditors (physical walkthroughs, client site visits, remote locations) can benefit from a 24/7 pocket audit assistant. The pattern is platform-agnostic — swap Telegram for WhatsApp or Teams.

**KAIROS Pattern (April 2026 context engineering developments):**

The KAIROS architecture pattern — identified from Anthropic's advanced agent research — directly maps to this plan:

- **Append-only daily logs**: instead of reloading full conversation history, the agent maintains a rolling daily log file (`audit-agent-YYYY-MM-DD.log`) and appends new exchanges. On restart, only the last N lines are reloaded into context. This keeps context lean and restart-fast.
- **15-second blocking budget**: the always-on agent should respond within 15 seconds or return a "processing" acknowledgement followed by an async reply. This prevents the field auditor from waiting and keeps the tool feel instant.
- **Push notifications over polling**: instead of the auditor checking the agent, the agent can push proactive alerts (e.g., "Your DORA Art. 11 filing window opens in 3 days"). Telegram Bot API supports this natively.
- **ZeroClaw pattern** (`zeroclaw.org`): the always-on agent is the natural anchor for a persistent "sentinel" process that monitors for incoming events (new intelligence articles, deadline alerts, colleague queries) and surfaces them to the auditor during downtime. ZeroClaw's open-source harness demonstrates this with scheduled tool calls and output streaming.
- **Anthropic Managed Agents**: as Anthropic's managed agent infrastructure matures, the always-on pattern becomes deployable without managing a local HTTP server — reducing operational overhead for audit departments without dedicated engineering support.

**Related SAAF plans:**

- [`audit-memory-knowledge-system.md`](audit-memory-knowledge-system.md) — knowledge base for precedent lookups
- [`diyve-garg-pbc-assistant-isabelle.md`](../hackathon-2/diyve-garg-pbc-assistant-isabelle.md) — PBC assistant (complementary fieldwork tool)
- [`saaf-intelligence-monitor.md`](saaf-intelligence-monitor.md) — always-on monitoring (separate pattern)
- [`audit-loop-orchestration-sdk.md`](audit-loop-orchestration-sdk.md) — KAIROS and ULTRAPLAN SDK patterns for orchestrating the always-on lifecycle

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Architecture defined; Clawdbot pattern validated |
| **Do** | In progress | Hackathon #3: implement HTTP server + Telegram integration; test 5 field queries |
| **Check** | Not started | Test with field auditor during actual fieldwork (pilot) |
| **Act** | Not started | Target: production deployment for 1 pilot org post-H3 |

---

## 12. Open Questions

1. Which messaging channel is most appropriate for Dutch audit teams — Telegram, WhatsApp Business, or Teams?
2. Should the agent log conversations to a local file (audit trail) or keep them ephemeral (privacy)?
3. How do we handle the agent responding outside working hours — should there be a do-not-disturb mode?
4. What is the acceptable latency for field queries — is Claude API fast enough, or is Ollama always required?
