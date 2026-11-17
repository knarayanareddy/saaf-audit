# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Example Participant (synthetic — for illustration only) |
| **Organisation** | Synthetic Corp B.V. |
| **Session** | Session 2 |
| **Type** | Agent |
| **Status** | Finalised |

---

## 2. Problem Statement

User access reviews are conducted quarterly. The current process requires an IT auditor to manually export an Active Directory export, cross-reference it against the HR system, and flag accounts belonging to departed employees or role changes. This takes 2–3 days per entity and is error-prone when exports are misaligned in timing.

The goal is an agent that ingests both exports, identifies mismatches automatically, and produces a structured finding list ready for auditor review.

---

## 3. Use-Case Type and Scope

**Audit domain:** Access Management

**Applicable standards:**

- ISO/IEC 27001:2022 — A.5.18 Access rights
- SOC 2 Type II — CC6.2, CC6.3
- ISAE 3402 — relevant for outsourced processing environments

**In scope:**

- Matching user accounts from an AD export to an HR active-employee list
- Flagging orphaned accounts (no HR record) and privilege escalations (role change not approved)
- Producing findings conforming to `outputs/schemas/finding-schema.json`

**Out of scope:**

- Privileged access workstations (PAW) review
- Service accounts and non-human identities
- Real-time Active Directory querying (batch export only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt in `prompts/audit-use-cases/access-review-agent.md` |
| **Tools** | New Python script `tools/scripts/access_review_agent.py` |
| **Regulatory** | Reuse `regulatory/control-mappings/iso27001.md`; add SOC 2 CC6 rows |
| **Outputs** | JSON findings conforming to `outputs/schemas/finding-schema.json` |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI audit assistant specialised in user access management.
Your role is to compare an Active Directory user export against an HR active-employee list
and identify access control exceptions that require auditor review.

Always:
- Report findings in the standard SAAF finding format (id, title, risk_rating, observation, recommendation).
- Assign risk ratings conservatively: orphaned accounts = High, role mismatch = Medium, stale accounts = Low.
- Use only the data provided; do not infer or hallucinate account details.

Never:
- Suggest remediation actions that involve direct system changes.
- Include real names, email addresses, or personal identifiers in your output.
  Replace with synthetic placeholders (USER-001, USER-002, etc.) before outputting.
```

### Example user prompts

**Prompt 1:**
```
Here is an AD export (CSV) and an HR active-employee list (CSV).
Identify all AD accounts with no matching HR record and return findings.

AD export:
username,department,last_login
jdoe,Finance,2025-11-01
asmith,IT,2025-12-15
bwilliams,Finance,2024-03-10

HR active employees:
employee_id,username,department,status
E001,jdoe,Finance,Active
E002,asmith,IT,Active
```

**Prompt 2:**
```
The following accounts have not been logged into for more than 90 days.
Rate the risk and produce findings for each.

Stale accounts:
bwilliams,Finance,last_login=2024-03-10
```

**Intended file location:** `prompts/audit-use-cases/access-review-agent.md`

---

## 6. Tools and Techniques

### Approach

1. Load AD export and HR export from CSV (or from Strapi synthetic API).
2. Inner-join on `username`; left-join remainder = orphaned accounts.
3. Compare `department` fields to detect role changes not reflected in HR.
4. Flag accounts with `last_login` older than 90 days as stale.
5. For each exception, call the Claude API with the system prompt above and the account details.
6. Collect structured JSON findings and write to `outputs/`.

### Example script or pseudocode

```python
import csv
import json
from pathlib import Path
from typing import Optional
import anthropic

def load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def find_orphaned_accounts(ad_users: list[dict], hr_users: list[dict]) -> list[dict]:
    hr_usernames = {u["username"] for u in hr_users}
    return [u for u in ad_users if u["username"] not in hr_usernames]

def build_prompt(orphaned: list[dict]) -> str:
    rows = "\n".join(f"{u['username']},{u['department']},{u['last_login']}" for u in orphaned)
    return f"Orphaned AD accounts (no HR record):\n{rows}\nProduce findings in SAAF JSON format."

def call_claude(system: str, user: str) -> Optional[str]:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text

# Main
ad = load_csv(Path("tools/scripts/test_data/ad_export.csv"))
hr = load_csv(Path("tools/scripts/test_data/hr_export.csv"))
orphaned = find_orphaned_accounts(ad, hr)
system_prompt = Path("prompts/audit-use-cases/access-review-agent.md").read_text()
findings_raw = call_claude(system_prompt, build_prompt(orphaned))
Path("outputs/examples/access-review-findings.json").write_text(findings_raw)
```

**Tech stack used:** Python 3.11, Claude API (claude-sonnet-4-6), CSV (or Strapi synthetic data API)

**Intended file location:** `tools/scripts/access_review_agent.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISO/IEC 27001:2022 | A.5.18 — Access rights; A.8.2 — Privileged access rights |
| SOC 2 Type II | CC6.2 — Logical access controls; CC6.3 — Access provisioning |
| ISAE 3402 | Control objective: user access is reviewed and revoked on termination |

### Claude / AI tool usage notes

- Only synthetic or anonymized data will be sent to the Claude API during testing.
- The script replaces usernames with `USER-NNN` placeholders before sending to the API.
- Model: `claude-sonnet-4-6` — sufficient for structured extraction tasks at this scope.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output

```json
[
  {
    "id": "F-001",
    "title": "Orphaned AD account — no active HR record",
    "risk_rating": "High",
    "observation": "Account USER-003 exists in Active Directory (department: Finance, last login: 2024-03-10) but has no corresponding record in the HR active-employee list. This suggests the account belongs to a departed employee and has not been disabled.",
    "recommendation": "Disable or delete USER-003 in Active Directory immediately and investigate whether the account was used after the employee's departure date."
  },
  {
    "id": "F-002",
    "title": "Stale account — no login in over 90 days",
    "risk_rating": "Low",
    "observation": "Account USER-005 has not been logged into since 2025-09-01 (>180 days). Stale accounts increase the attack surface if credentials are compromised.",
    "recommendation": "Review whether USER-005 requires continued access. If not, disable the account in line with the access review policy."
  }
]
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [x] Strapi (synthetic data API — optional)
- [ ] Other: ___

**Stretch goals:**

- [ ] Automated scheduling via cron + email report
- [ ] Integration with Jira to open tickets for each High finding

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- The system prompt (in `prompts/audit-use-cases/`)
- The Python script with synthetic test data
- Example output JSON

**What help I'm looking for:**

- Feedback on the risk rating logic — is High/Medium/Low calibrated correctly for access findings?
- Anyone with SOC 2 CC6 expertise to validate the control mapping

**Cross-org interest:**

At least three organizations at Session 1 mentioned quarterly access reviews as a pain point. Happy to co-develop with anyone working on the same domain.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | This document |
| **Do** | Complete | Script and prompt drafted at Session 2 |
| **Check** | In progress | Testing internally with synthetic AD/HR exports |
| **Act** | Not started | Target: Hackathon 3 — share validation results |

---

## 12. Open Questions

1. Should the agent handle service accounts separately, or is a single prompt sufficient?
2. What is the right threshold for "stale" accounts — 90 days or organization-defined?
3. Is there a shared synthetic AD/HR dataset in the repo we should all use for consistency?
