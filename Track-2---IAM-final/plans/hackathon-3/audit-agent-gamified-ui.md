# Audit Agent Fleet Manager — Gamified UI

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

Running multiple parallel audit agents today requires watching terminal logs, manually checking output files, and mentally tracking which agent is doing what. There is no visual interface that shows the fleet of running agents, their progress, and their outputs in one place.

Without a visual overview, parallel agent execution is intimidating for non-technical auditors and error-prone for technical ones. Debugging a failed agent requires grep-ing log files. Progress is invisible until the batch completes.

A visual fleet manager — inspired by RTS (real-time strategy) game interfaces — makes multi-agent audit execution intuitive, transparent, and even engaging.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Agent Infrastructure / User Experience

**Applicable standards:**

- IIA IPPF — Standard 2340 (Engagement Supervision) — supervisor needs visibility into agent activity
- EU AI Act — Art. 14 (Human Oversight) — UI is a key human-in-the-loop mechanism

**In scope:**

- Real-time web dashboard showing all running/completed/failed audit agents
- Per-agent status: progress bar, task description, last output preview, cost so far
- Fleet overview: total tasks, completion percentage, estimated time to finish
- One-click: pause agent, view full output, mark finding as reviewed
- Reads state from `audit_sdk` loop JSON files (no additional infrastructure)
- Pure Python + browser (no React, no Node.js — runs on any machine)

**Out of scope:**

- Agent execution (the dashboard observes; the SDK executes)
- Mobile interface (desktop browser only in MVP)
- Multi-user collaboration (single audit lead view)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | No new prompts — this is a UI for existing agents |
| **Tools** | `tools/scripts/fleet-dashboard.py` — Python HTTP server + browser UI |
| **Regulatory** | IIA 2340 (supervision) — dashboard provides supervisor with real-time agent visibility |
| **Outputs** | HTML dashboard (live view of agent fleet status) |

---

## 5. Prompts

### System prompt (draft — agent progress narration)

```
You are an audit fleet status narrator.
Given the current state of all running audit agents (JSON), produce a one-paragraph
status update suitable for a supervisor checking in.
Include: how many agents are running, what they are working on, any errors or issues,
estimated completion time, and any findings that require immediate review.
Keep it under 100 words. Factual, no filler.
```

### Example user prompts

**Prompt 1 — Status brief:**
```
[Current fleet state JSON attached]
Give me a 60-second verbal briefing on where the overnight audit batch stands.
```

**Prompt 2 — Anomaly detection:**
```
[Fleet state JSON attached]
Agent "vendor-assess-012" has been running for 45 minutes with no progress.
What could cause this? What should I check?
```

**Intended file location:** `prompts/audit-use-cases/fleet-status-narrator.md`

---

## 6. Tools and Techniques

### Approach

A lightweight Python HTTP server reads the loop state JSON files produced by `audit_sdk`. It generates an HTML dashboard page on each request — no JavaScript framework, no websockets. The browser auto-refreshes every 5 seconds via a `<meta http-equiv="refresh">` tag.

The visual design draws from RTS game principles:
- Each agent is a "unit" card with health-bar-style progress
- Green = running, orange = waiting, red = failed, gray = complete
- Fleet overview shows aggregate progress like a mission completion percentage
- Findings that need review are highlighted in a sidebar

### Example script or pseudocode

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
from datetime import datetime

LOOPS_DIR = Path("data/loops")

def get_all_loop_states() -> list[dict]:
    states = []
    for f in LOOPS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            states.append(data)
        except Exception:
            pass
    return states

def render_dashboard(states: list[dict]) -> str:
    total_tasks = sum(len(s["tasks"]) for s in states)
    complete_tasks = sum(
        sum(1 for t in s["tasks"] if t["status"] == "complete")
        for s in states
    )
    pct = int(complete_tasks / total_tasks * 100) if total_tasks else 0

    agent_cards = ""
    for state in states:
        tasks = state["tasks"]
        n_complete = sum(1 for t in tasks if t["status"] == "complete")
        n_total = len(tasks)
        n_failed = sum(1 for t in tasks if t["status"] == "failed")
        running = next((t for t in tasks if t["status"] == "in_progress"), None)
        status_color = "#27AE60" if n_failed == 0 else "#C0392B"
        agent_cards += f"""
        <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin:8px;width:280px;display:inline-block;vertical-align:top">
          <h3 style="margin:0;color:{status_color}">{state['name']}</h3>
          <div style="background:#eee;border-radius:4px;height:12px;margin:8px 0">
            <div style="background:{status_color};width:{int(n_complete/n_total*100)}%;height:12px;border-radius:4px"></div>
          </div>
          <p style="margin:4px 0;font-size:13px">{n_complete}/{n_total} tasks complete{f' · {n_failed} failed' if n_failed else ''}</p>
          {f'<p style="margin:4px 0;font-size:12px;color:#555">Current: {running["description"][:50]}...</p>' if running else ''}
        </div>"""

    return f"""<!DOCTYPE html><html><head>
      <title>SAAF Audit Fleet</title>
      <meta http-equiv="refresh" content="5">
      <style>body{{font-family:system-ui,sans-serif;padding:24px;background:#f5f5f5}}</style>
    </head><body>
      <h1 style="margin:0">SAAF Audit Fleet Manager</h1>
      <p style="color:#555">Last updated: {datetime.now().strftime('%H:%M:%S')} · Auto-refresh: 5s</p>
      <div style="background:white;border-radius:8px;padding:16px;margin:16px 0">
        <h2 style="margin:0">Fleet Overview</h2>
        <p>{complete_tasks} / {total_tasks} tasks complete &nbsp;·&nbsp; {pct}% overall</p>
        <div style="background:#eee;border-radius:4px;height:20px">
          <div style="background:#27AE60;width:{pct}%;height:20px;border-radius:4px"></div>
        </div>
      </div>
      <h2>Active Agents</h2>
      {agent_cards}
      <p style="color:#888;font-size:12px;margin-top:24px">
        SAAF Audit Fleet Manager — review all agent outputs before using in audit dossier
      </p>
    </body></html>"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        states = get_all_loop_states()
        html = render_dashboard(states)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *args):
        pass

print("Fleet dashboard running at http://localhost:5002")
HTTPServer(("localhost", 5002), DashboardHandler).serve_forever()
```

**Tech stack used:** Python 3.9+, stdlib HTTP server, pure HTML/CSS (no JS framework, no Node.js)

**Intended file location:** `tools/scripts/fleet-dashboard.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2340 | Engagement supervision — dashboard gives supervisors real-time visibility into agent activity |
| EU AI Act Art. 14 | Human oversight — visual UI is a primary mechanism for humans to intervene in agent execution |

### Claude / AI tool usage notes

The dashboard itself does not call Claude. It reads state files produced by agents. The optional "status narration" feature calls Claude with aggregate state JSON (no per-finding content) for a briefing summary.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** HTML dashboard (browser-based, auto-refreshing)

**Schema reference:** Reads from audit_sdk loop state JSON files

### Synthetic example output description

Browser at `http://localhost:5002` shows:

- Header: "SAAF Audit Fleet Manager" · Last updated 09:14:22 · Auto-refresh 5s
- Fleet Overview: 45 / 120 tasks complete · 37% overall · green progress bar
- Agent cards (3 active):
  - "vendor-assessment-batch" — 18/50 tasks, green, current: "Assess Contoso B.V."
  - "rcm-build-access-mgmt" — 12/30 tasks, green, current: "Build RCM for Privilege Access"
  - "pbc-reminder-q1-2026" — 15/40 tasks, orange (2 failed), current: "Draft reminder for J. Bakker"
- Footer: "review all agent outputs before using in audit dossier"

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] Pure HTML/CSS dashboard (stdlib HTTP server — no external dependencies)
- [x] Reads audit_sdk loop state JSON files

**Stretch goals:**

- [ ] WebSocket-based live update (no page refresh)
- [ ] One-click agent actions: pause, resume, cancel (via SDK API)
- [ ] Finding review queue: findings flagged for human review shown in sidebar with approve/reject buttons
- [ ] Cost tracker: real-time API cost per agent and total fleet cost

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `fleet-dashboard.py` script
- Dashboard HTML/CSS template

**Help requested:**

- UX designers: improve the visual design (current version is functional, not beautiful)
- Engineers: add WebSocket live updates
- Auditors: validate that the information shown is what supervisors actually need

**Cross-org interest:**

Any organization running multiple parallel audit agents benefits from a fleet view. The dashboard is a low-cost addition to the `audit_sdk` infrastructure.

**Market Precedents and Design Inspiration (April 2026):**

Two market developments directly inform the design of the fleet manager dashboard:

- **AgentCraft** (`getagentcraft.com`): commercial agent orchestration platform with a visual "agent market" dashboard showing running agents, task queues, and output previews. AgentCraft's UI demonstrates that audit teams respond well to a card-based layout (one card per agent, status color, progress bar, current task description) — exactly what the SAAF fleet dashboard implements. AgentCraft's open-source UI components are a reference for the planned WebSocket live-update upgrade.

- **Robin van der Werf's Rust Cockpit** (SAAF community demo, April 2026): Robin demonstrated a low-latency agent cockpit built in Rust that renders agent status using a terminal-based TUI. The Rust implementation achieves <50ms refresh without WebSockets by using a terminal raw-mode renderer. For SAAF teams that prefer a terminal workflow over a browser, this is a viable alternative to the HTTP dashboard — particularly useful when the fleet runs on a remote server accessed via SSH.

**Gamification layer (v2 stretch goal):** Beyond fleet monitoring, the "gamified UI" concept extends to participant leaderboards — tracking which SAAF teams have produced the most findings, highest-scoring agents, and most reused prompts. AgentCraft's agent marketplace (where agents are rated and ranked by users) is a precedent for making agent quality visible and motivating contribution.

**Related SAAF plans:**

- [`audit-loop-orchestration-sdk.md`](audit-loop-orchestration-sdk.md) — produces the state files this dashboard reads
- [`overnight-audit-batch-processing-agent.md`](overnight-audit-batch-processing-agent.md) — primary use case for fleet monitoring
- [`audit-evidence-visualization.md`](audit-evidence-visualization.md) — complementary output visualization
- [`audit-subagent-coordination-framework.md`](audit-subagent-coordination-framework.md) — multi-agent debates produce fleet state readable by this dashboard

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Dashboard design defined; integration with audit_sdk specified |
| **Do** | In progress | Hackathon #3: implement dashboard; demo with overnight batch run |
| **Check** | Not started | Usability test: can a non-technical auditor understand fleet status from dashboard? |
| **Act** | Not started | Add finding review queue; improve visual design |

---

## 12. Open Questions

1. Should the dashboard run on a server (accessible to the whole audit team) or only on the audit lead's machine?
2. Is auto-refresh every 5 seconds acceptable, or do users need real-time updates (WebSocket)?
3. Should the dashboard include a "kill switch" — a button to immediately stop all agents?
4. How do we handle the dashboard when agents are running overnight (no one is watching)? Should it send a summary notification when the batch completes?
