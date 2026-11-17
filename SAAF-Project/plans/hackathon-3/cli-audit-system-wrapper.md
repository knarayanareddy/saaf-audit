# CLI Audit System Wrapper

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

Many audit-relevant systems (ERP exports, SIEM log tools, GRC platforms, Active Directory utilities) have strong command-line interfaces but weak or absent REST APIs. Building an MCP server for these systems requires API access that doesn't exist.

The gap: audit teams want Claude to query these systems, but MCP assumes an HTTP/JSON interface. Legacy systems (SAP CLI tools, AD PowerShell modules, Splunk CLI, ServiceNow CLI) only expose a command-line interface.

A CLI wrapper pattern exposes these tools to Claude without requiring API development — Claude runs shell commands, parses CLI output, and produces structured audit findings.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Evidence Collection / Tool Integration

**Applicable standards:**

- IIA IPPF — Standard 2310 (Identifying Information)
- GDPR — Art. 32 (Security of processing)

**In scope:**

- Pattern for wrapping any CLI tool as a Claude-callable audit skill
- Pre-built wrappers for: Active Directory (AD PowerShell / dsquery), Splunk CLI, ServiceNow CLI export, SAP audit log export
- Output: structured JSON from CLI output parsing
- Guardrailed execution: only pre-approved CLI commands can be called; no arbitrary shell access

**Out of scope:**

- MCP server development (use `saaf-jira-confluence-mcp.md` for REST API systems)
- Elevated privilege commands (`sudo`, `runas`)
- Live production system modification (read-only audit evidence collection only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | CLI result interpretation prompt; evidence extraction prompt per system type |
| **Tools** | `tools/scripts/cli-wrapper.py` — command allowlist + runner; per-system parsers |
| **Regulatory** | IIA 2310 (identifying information) — CLI evidence collection with audit trail |
| **Outputs** | Structured JSON evidence records per CLI query |

---

## 5. Prompts

### System prompt (draft)

```
You are an audit evidence collection assistant with access to CLI tools via the run_command tool.
You may only run commands from the approved command list.
For each command you run:
1. Log the exact command executed and its timestamp
2. Parse the output into structured JSON
3. Identify any audit-relevant exceptions (anomalies, policy violations, access risks)
4. Cite the evidence source (system name, command, timestamp) in your finding

Never run commands that modify system state.
Never run commands outside the approved list.
If a command fails, log the error and continue — do not retry with elevated permissions.
```

### Example user prompts

**Prompt 1 — Active Directory user review:**
```
Query Active Directory for all user accounts that have not logged in for more than 90 days.
Use the approved dsquery command.
Return results as JSON: [{username, last_login, account_status, department}]
Flag any accounts belonging to former employees (check against the HR export in context).
```

**Prompt 2 — Splunk log review:**
```
Query Splunk for all failed login attempts in the last 30 days with more than 5 failures per user.
Use the approved Splunk CLI command.
Return: [{user, failure_count, last_failure_time, source_ip}]
Flag any users with failure_count > 20.
```

**Intended file location:** `prompts/audit-use-cases/cli-evidence-collection.md`

---

## 6. Tools and Techniques

### Approach

A Python script maintains an allowlist of approved CLI commands (JSON config file). Claude calls the `run_command` function with a command name and parameters. The script validates the command against the allowlist, executes it via `subprocess.run()` with a timeout, and returns the raw output. Claude then parses the output into structured evidence.

The allowlist is the security control: no command outside the allowlist can be executed, regardless of what Claude requests.

### Example script or pseudocode

```python
import subprocess
import json
import shlex
from pathlib import Path
from datetime import datetime

ALLOWLIST_FILE = Path("regulatory/guardrails/cli-allowlist.json")

def load_allowlist() -> dict:
    return json.loads(ALLOWLIST_FILE.read_text())

def run_command(command_name: str, params: dict) -> dict:
    allowlist = load_allowlist()

    if command_name not in allowlist:
        return {"error": f"Command '{command_name}' not in allowlist", "output": None}

    template = allowlist[command_name]["template"]

    # Safe parameter substitution (no shell injection)
    try:
        cmd = template.format(**{k: shlex.quote(str(v)) for k, v in params.items()})
    except KeyError as e:
        return {"error": f"Missing parameter: {e}", "output": None}

    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    )

    audit_log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "command_name": command_name,
        "command_executed": cmd,
        "exit_code": result.returncode,
        "output_lines": len(result.stdout.splitlines()),
    }
    append_audit_log(audit_log_entry)

    return {
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }

def append_audit_log(entry: dict):
    log_path = Path("outputs/cli-audit-log.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

**Allowlist configuration (`cli-allowlist.json`):**

```json
{
  "ad_inactive_users": {
    "description": "Query AD for users inactive for N days",
    "template": "dsquery user -inactive {days} -limit 500",
    "parameters": ["days"],
    "system": "Active Directory"
  },
  "splunk_failed_logins": {
    "description": "Query Splunk for failed logins in last N days",
    "template": "splunk search 'index=security failed login earliest=-{days}d | stats count by user' -output rawdata",
    "parameters": ["days"],
    "system": "Splunk"
  }
}
```

**Tech stack used:** Python 3.9+, subprocess (stdlib), shlex (injection prevention), JSON allowlist

**Intended file location:** `tools/scripts/cli-wrapper.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2310 | Identifying information — CLI evidence has full audit trail (command, timestamp, output) |
| GDPR Art. 32 | Security of processing — allowlist prevents unauthorized command execution |

### Claude / AI tool usage notes

Claude is constrained to the allowlist — it cannot execute arbitrary shell commands. All commands are read-only (evidence collection, not system modification). The allowlist file itself must be reviewed and approved by the system owner before use in any production environment.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (per-command output) + JSONL audit log

**Schema reference:** `outputs/schemas/finding-schema.json` (for findings derived from CLI evidence)

### Synthetic example output (AD inactive user query)

```json
{
  "command": "dsquery user -inactive 90 -limit 500",
  "executed_at": "2026-04-21T09:14:02Z",
  "results": [
    {
      "username": "j.doe",
      "last_login": "2025-10-15",
      "days_inactive": 187,
      "department": "Finance",
      "account_status": "Enabled"
    },
    {
      "username": "a.smith",
      "last_login": "2025-09-01",
      "days_inactive": 232,
      "department": "IT",
      "account_status": "Enabled"
    }
  ],
  "total_inactive": 23,
  "flagged": 23,
  "finding_seed": "23 user accounts inactive >90 days remain enabled in Active Directory."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Python 3.9+
- [x] subprocess (stdlib — no external dependencies)
- [x] JSON allowlist configuration
- [x] JSONL audit log

**Stretch goals:**

- [ ] MCP tool wrapper: expose `run_command` as an MCP tool for Claude Code integration
- [ ] Pre-built parser library: parsers for AD, Splunk, ServiceNow, SAP CLI output formats
- [ ] GUI allowlist editor: validate allowlist entries without editing JSON directly

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- `cli-wrapper.py` script
- Example allowlist configurations for AD, Splunk, ServiceNow
- Security review checklist for adding new commands to the allowlist

**Help requested:**

- Systems administrators: contribute allowlist entries for your audit-relevant CLI tools
- Security engineers: review subprocess execution for any injection risks not covered by shlex
- Auditors with SAP access: validate the SAP audit log CLI command set

**Cross-org interest:**

Legacy system CLI wrappers are needed by virtually every large enterprise audit team. A shared allowlist library (contributed by SAAF organizations) reduces per-org effort to onboard new CLI tools.

**Related SAAF plans:**

- [`saaf-jira-confluence-mcp.md`](saaf-jira-confluence-mcp.md) — MCP alternative for REST API systems
- [`frank-van-dissel-uc6-it-dependency-identifier.md`](../hackathon-2/frank-van-dissel-uc6-it-dependency-identifier.md) — IT dependency use case
- [`example-synthetic-access-review.md`](../hackathon-2/example-synthetic-access-review.md) — access review use case

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | Allowlist pattern designed; subprocess security validated |
| **Do** | In progress | Hackathon #3: implement wrapper; test with `dsquery` mock against Strapi |
| **Check** | Not started | Security review: validate allowlist enforcement against injection attempts |
| **Act** | Not started | Publish allowlist library for 3 systems (AD, Splunk, ServiceNow) |

---

## 12. Open Questions

1. How should organizations handle CLI tools that require domain credentials (AD, SAP)? Service account pattern?
2. Should the allowlist be per-organization or shared across SAAF? Sharing creates risk if a command is unsafe for some environments.
3. Is `shlex.quote()` sufficient injection protection, or do we need additional input validation per parameter?
4. How do we handle CLI tools that produce non-standard output formats (not JSON, not CSV)?
