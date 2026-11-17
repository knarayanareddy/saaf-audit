# Audit Loop Orchestration SDK

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

Building multi-agent audit workflows today requires every team to solve the same infrastructure problems: managing agent state across context windows, routing messages between agents, tracking progress across long-running tasks, and handling partial failures gracefully.

This overhead means teams spend 60% of hackathon time on plumbing and 40% on actual audit logic. A shared SDK abstracts the loop control infrastructure, so teams can focus on writing audit prompts and business logic.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Agent Infrastructure

**Applicable standards:**

- IIA IPPF — Standard 2010 (Planning), 2340 (Engagement Supervision)
- ISO 42001 — AI management systems

**In scope:**

- Python SDK exposing: `Agent`, `Task`, `Loop`, `Mailbox` primitives
- State persistence: task progress survives Python process restarts
- Progress tracking: per-task completion percentage, estimated time remaining
- Error handling: retry with backoff; partial failure recovery
- Context window management: agent detects approaching limit and saves state before stopping
- Multi-agent coordination: task routing between specialized agents

**Out of scope:**

- Distributed execution across multiple machines (single machine only for now)
- GUI orchestration dashboard (see `audit-agent-gamified-ui.md`)
- Cloud deployment (local execution only in MVP)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | SDK provides prompt injection utilities (context window status, task list formatting) |
| **Tools** | `tools/scripts/audit_sdk/` — Python package with Agent, Task, Loop, Mailbox classes |
| **Regulatory** | IIA 2340 (supervision) — SDK produces structured audit trail for all agent actions |
| **Outputs** | Task progress JSON + audit trail JSONL per orchestration run |

---

## 5. Prompts

### System prompt injection (draft — SDK-managed)

```
[SDK CONTEXT INJECTION]
Current task: {task.id} — {task.description}
Progress: {task.completed_steps}/{task.total_steps} steps complete
Remaining tasks in queue: {len(loop.pending_tasks)}
Context budget remaining: approximately {context_remaining}% of context window
State file: {state_file_path}

If you are approaching context limits (budget < 10%), save your current state to the task file
and output: CHECKPOINT_SAVE. The orchestrator will restart you with the updated state.
[/SDK CONTEXT INJECTION]
```

### Example user prompts

**Prompt 1 — SDK usage:**
```python
from audit_sdk import Loop, Task, Agent

loop = Loop("vendor-assessment-batch")
for vendor in vendor_list:
    loop.add_task(Task(
        id=f"assess-{vendor['id']}",
        description=f"Assess {vendor['name']} against DORA Art. 28-30",
        input_data=vendor,
        output_schema="finding-schema.json"
    ))

agent = Agent(model="claude-sonnet-4-6", system_prompt=DORA_ASSESSMENT_PROMPT)
loop.run(agent, max_parallel=1, checkpoint_interval=5)
```

**Prompt 2 — Multi-agent routing:**
```python
from audit_sdk import Loop, Task, Agent, Router

router = Router({
    "classify": Agent(model="claude-haiku-4-5-20251001", system_prompt=CLASSIFIER_PROMPT),
    "assess":   Agent(model="claude-sonnet-4-6", system_prompt=ASSESSOR_PROMPT),
    "report":   Agent(model="claude-sonnet-4-6", system_prompt=REPORTER_PROMPT),
})

loop = Loop("full-audit-pipeline")
loop.add_task(Task(id="classify-01", type="classify", input_data=evidence_batch))
loop.run_routed(router)
```

**Intended file location:** `prompts/audit-use-cases/sdk-usage.md`

---

## 6. Tools and Techniques

### Approach

The SDK provides four primitive classes:

- **`Task`**: represents one unit of work; has id, description, input_data, output_schema, status, progress
- **`Loop`**: manages a task queue; persists state to a JSON file; supports checkpoint/resume
- **`Agent`**: wraps the Claude API; auto-injects context window status; detects CHECKPOINT_SAVE signal
- **`Mailbox`**: enables message passing between agents (used in multi-agent patterns)

The loop's state file is the single source of truth. If the Python process dies, the loop resumes from the last checkpoint on the next run.

### Example script or pseudocode

```python
# audit_sdk/core.py
import json, anthropic, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

@dataclass
class Task:
    id: str
    description: str
    input_data: dict
    output_schema: str = "finding-schema.json"
    status: str = "pending"   # pending | in_progress | complete | failed
    result: Optional[dict] = None
    attempts: int = 0

class Loop:
    def __init__(self, name: str, state_dir: Path = Path("data/loops")):
        self.name = name
        self.state_file = state_dir / f"{name}.json"
        state_dir.mkdir(parents=True, exist_ok=True)
        self._load_or_init()

    def _load_or_init(self):
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            self.tasks = [Task(**t) for t in data["tasks"]]
            print(f"  Resumed: {sum(1 for t in self.tasks if t.status=='complete')} / {len(self.tasks)} complete")
        else:
            self.tasks = []

    def add_task(self, task: Task):
        self.tasks.append(task)
        self._save()

    def _save(self):
        self.state_file.write_text(json.dumps(
            {"name": self.name, "tasks": [t.__dict__ for t in self.tasks]},
            indent=2
        ))

    def run(self, agent: "Agent", max_retries: int = 3):
        for task in self.tasks:
            if task.status == "complete":
                continue
            task.status = "in_progress"
            task.attempts += 1
            self._save()
            try:
                result = agent.run_task(task)
                task.result = result
                task.status = "complete"
                print(f"  ✓ {task.id}")
            except Exception as e:
                task.status = "failed" if task.attempts >= max_retries else "pending"
                print(f"  ✗ {task.id}: {e}")
            self._save()

class Agent:
    def __init__(self, model: str, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt
        self.client = anthropic.Anthropic()

    def run_task(self, task: Task) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=[{"role": "user", "content": json.dumps(task.input_data)}]
        )
        return json.loads(response.content[0].text)
```

**Tech stack used:** Python 3.9+, Claude API (claude-sonnet-4-6 and claude-haiku-4-5-20251001), dataclasses, pathlib, JSON

**Intended file location:** `tools/scripts/audit_sdk/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2340 | Engagement supervision — SDK audit trail documents all agent actions and task outcomes |
| ISO 42001 | AI management — SDK enforces consistent agent design (model versioning, output schema) |

### Claude / AI tool usage notes

The SDK enforces that all agent runs use the configured model version (not latest — explicit version). All inputs and outputs are persisted to the state file for the audit trail. Agents run against synthetic data only in SAAF hackathon context.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON state file (progress tracking) + per-task result JSON

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output (loop state after 3/5 tasks complete)

```json
{
  "name": "vendor-assessment-batch",
  "tasks": [
    {"id": "assess-001", "status": "complete", "result": {"risk_rating": "High"}, "attempts": 1},
    {"id": "assess-002", "status": "complete", "result": {"risk_rating": "Medium"}, "attempts": 1},
    {"id": "assess-003", "status": "complete", "result": {"risk_rating": "Low"}, "attempts": 1},
    {"id": "assess-004", "status": "in_progress", "result": null, "attempts": 1},
    {"id": "assess-005", "status": "pending", "result": null, "attempts": 0}
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] Claude API (claude-sonnet-4-6, claude-haiku-4-5-20251001)
- [x] JSON state files
- [x] dataclasses (stdlib — no external dependencies for core SDK)

**Stretch goals:**

- [ ] Async execution: asyncio-based parallel task runner
- [ ] SQLite state backend (instead of JSON files) for larger task queues
- [ ] SDK metrics: total API cost per loop run, tokens per task, time per task

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `audit_sdk/` Python package
- Usage examples for 3 use cases (batch vendor assessment, multi-agent RCM building, overnight evidence collection)

**Help requested:**

- Engineers: add async/parallel execution capability
- Auditors: propose new use cases that benefit from loop orchestration
- All SAAF teams: migrate an existing plan to use the SDK and report the experience

**Cross-org interest:**

Any team building multi-step audit workflows in Python can benefit from the SDK. Goal: make the SDK the default infrastructure layer for all future SAAF agent plans.

**Advanced SDK Patterns: ULTRAPLAN and KAIROS (April 2026):**

Two advanced patterns from Anthropic's agent research should be added to the SDK as optional modules:

**ULTRAPLAN pattern** — async deep planning:
```python
class UltraplanAgent:
    """Long-horizon planning using Opus with extended think time."""
    def __init__(self, model: str = "claude-opus-4-6", think_seconds: int = 1800):
        self.model = model
        self.think_seconds = think_seconds  # 30-minute think budget
        self.client = anthropic.Anthropic()

    def plan(self, audit_scope: dict) -> dict:
        """Generate a deep audit plan. Runs asynchronously; returns a plan file path."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            thinking={"type": "enabled", "budget_tokens": self.think_seconds * 1000 // 6},
            system="You are a senior audit planning agent with access to all SAAF plans and regulatory frameworks.",
            messages=[{"role": "user", "content": json.dumps(audit_scope)}]
        )
        plan = {"scope": audit_scope, "plan": response.content[0].text, "model": self.model}
        plan_path = Path(f"data/plans/{audit_scope['engagement_id']}-ultraplan.json")
        plan_path.write_text(json.dumps(plan, indent=2))
        return plan
```

**KAIROS pattern** — always-on loop with blocking budget:
```python
class KairosLoop:
    """Always-on agent with append-only log and 15-second blocking budget."""
    BLOCKING_BUDGET_SECONDS = 15
    LOG_FILE = Path("data/logs/audit-agent-{date}.log")

    def handle_query(self, query: str, agent: Agent) -> str:
        """Respond within blocking budget; log to append-only daily file."""
        start = time.time()
        result = agent.run_task(Task(id=str(uuid4()), description=query, input_data={"query": query}))
        elapsed = time.time() - start
        log_entry = {"ts": datetime.now().isoformat(), "query": query, "elapsed_s": elapsed, "result": result}
        log_path = self.LOG_FILE.with_name(self.LOG_FILE.name.format(date=date.today()))
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        if elapsed > self.BLOCKING_BUDGET_SECONDS:
            return f"[Processing] {query} — full response in {elapsed:.0f}s"
        return result.get("answer", str(result))
```

Both patterns are optional SDK modules (`audit_sdk.ultraplan`, `audit_sdk.kairos`) that build on the core `Task`, `Loop`, and `Agent` primitives.

**Related SAAF plans:**

- [`overnight-audit-batch-processing-agent.md`](overnight-audit-batch-processing-agent.md) — primary consumer of the SDK
- [`audit-subagent-coordination-framework.md`](audit-subagent-coordination-framework.md) — multi-agent pattern using Mailbox
- [`audit-agent-gamified-ui.md`](audit-agent-gamified-ui.md) — potential SDK frontend
- [`always-on-audit-agent.md`](always-on-audit-agent.md) — KAIROS pattern implementation target

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | SDK primitives designed; API surface defined |
| **Do** | In progress | Hackathon #3: implement Task, Loop, Agent; run vendor assessment batch |
| **Check** | Not started | Compare developer experience vs. raw API calls |
| **Act** | Not started | Publish as installable Python package for SAAF community |

---

## 12. Open Questions

1. Should the SDK be a standalone Python package (pip installable) or just a set of scripts in `tools/scripts/`?
2. How do we handle tasks with different output schemas — enforce schema validation in the SDK or leave to the caller?
3. Should the Mailbox pattern be synchronous (agents run one at a time, pass state) or async?
4. What is the minimum SDK surface area that covers 80% of SAAF use cases?
