# Plan Template — SAAF Hackathon Submission

## 1. Metadata

| Field | Value |
|---|---|
| Submitter | SAAF Participant (synthetic — for illustration only) |
| Organisation | Synthetic Corp B.V. |
| Session | Session 2 |
| Type | Agent |
| Status | Finalised |

---

## 2. Problem Statement

User access reviews are conducted quarterly. The current process requires an IT auditor to manually export an Active Directory extract, cross-reference it against the HR system, and flag accounts belonging to departed employees or role changes. This takes 2–3 days per entity and is error-prone when exports are misaligned in timing.

The goal is an agent that ingests both exports, identifies mismatches automatically, and produces a structured finding list ready for auditor review.

---

## 3. Use-Case Type and Scope

**Audit domain:** Access Management

**Applicable standards:**
- ISO/IEC 27001:2022 — A.5.18 Access rights, A.8.2 Privileged access rights
- SOC 2 Type II — CC6.2, CC6.3
- ISAE 3402 — relevant for outsourced processing environments

**In scope:**
- Matching user accounts from an AD export to an HR active-employee list
- Flagging orphaned accounts (no HR record) and role mismatches (department field differs)
- Flagging stale accounts (no login within a configurable threshold, default 90 days)
- Producing findings conforming to `outputs/schemas/finding-schema.json`

**Out of scope:**
- Privileged access workstations (PAW) review
- Service accounts and non-human identities
- Real-time Active Directory querying (batch export only)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| Prompts | New agent system prompt: `prompts/audit-use-cases/access-review-agent.md` |
| Tools | New Python script: `tools/scripts/access_review_agent.py`; synthetic test data: `tools/scripts/test_data/ad_export.csv`, `tools/scripts/test_data/hr_export.csv` |
| Regulatory | New ISO 27001 access mapping: `regulatory/control-mappings/iso27001-access.md`; new SOC 2 CC6 mapping: `regulatory/control-mappings/soc2-access.md` |
| Outputs | JSON findings example conforming to `outputs/schemas/finding-schema.json`: `outputs/examples/access-review-findings.json` |

---

## 5. Prompts

**System prompt location:** `prompts/audit-use-cases/access-review-agent.md`

The agent system prompt instructs Claude to:
- Receive pre-processed exception lists (orphaned, stale, mismatches) already anonymised to USER-NNN placeholders
- Apply fixed risk ratings: orphaned = High, role mismatch = Medium, stale = Low
- Return a single JSON array of findings in the SAAF schema — no prose, no hallucinated details
- Never reconstruct real usernames or personal data

**Example user prompts** (see full templates in the prompt file):

*Prompt 1 — Orphaned and stale accounts:*
```
I am performing a user access review.
All usernames have been anonymised to USER-NNN placeholders.

Orphaned AD accounts (no matching HR record):
  USER-003, department: Finance, role: Analyst, last_login: 2024-03-10
  USER-007, department: Operations, role: Analyst, last_login: 2026-04-15

Stale accounts (no login in >90 days):
  USER-003, department: Finance, last_login: 2024-03-10

Please produce SAAF findings for all exceptions.
```

*Prompt 2 — Role mismatches:*
```
Role mismatches:
  USER-004: AD department = Operations, HR department = Finance

Please produce SAAF findings for each mismatch.
```

---

## 6. Tools and Techniques

**Approach:**
1. Load AD export and HR export from CSV.
2. Anonymise all usernames to USER-NNN placeholders before any API call.
3. Left-join AD on HR by username: unmatched AD rows = orphaned accounts.
4. Compare `department` field on matched rows: differences = role mismatches.
5. Flag accounts with `last_login` older than the configured threshold = stale accounts.
6. Call Claude API with the system prompt and a structured exception summary.
7. Parse and validate the JSON findings response against the SAAF schema.
8. Write `findings.json` to `outputs/access-review/`.

**Script location:** `tools/scripts/access_review_agent.py`

**CLI usage:**
```bash
python3 tools/scripts/access_review_agent.py \
    --ad tools/scripts/test_data/ad_export.csv \
    --hr tools/scripts/test_data/hr_export.csv \
    --threshold-days 90
```

**Tech stack:** Python 3.9+, Claude API (`claude-sonnet-4-6`), CSV (standard library)

---

## 7. Regulatory and Policies

**Applicable standards:**

| Standard | Relevant controls |
|---|---|
| ISO/IEC 27001:2022 | A.5.18 — Access rights; A.8.2 — Privileged access rights; A.8.5 — Secure authentication |
| SOC 2 Type II | CC6.2 — Logical access controls; CC6.3 — Access provisioning and deprovisioning |
| ISAE 3402 | Control objective: user access is reviewed and revoked on termination |

Full control mappings: `regulatory/control-mappings/iso27001-access.md`, `regulatory/control-mappings/soc2-access.md`

**Claude / AI tool usage notes:**
- Only synthetic or anonymised data is sent to the Claude API. Usernames are replaced with USER-NNN before the API call.
- Model: `claude-sonnet-4-6` — sufficient for structured extraction at this scope.

**Guardrails checklist:**
- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only (`ANTHROPIC_API_KEY`)

---

## 8. Output Format and Examples

**Format:** JSON
**Schema reference:** `outputs/schemas/finding-schema.json`
**Static example:** `outputs/examples/access-review-findings.json`

The example contains three synthetic findings:
- F-001: Orphaned AD account — High risk
- F-002: Role mismatch (department differs) — Medium risk
- F-003: Stale account (>180 days inactivity) — Low risk

All include optional fields: `control_objective`, `root_cause`, `impact`, `ai_assisted: true`, `status: "Open"`.

---

## 9. Tech Stack

**MVP scope:**
- [x] Claude API / claude-sonnet-4-6
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional stretch)

**Stretch goals:**
- Automated scheduling via cron + email report for each High finding
- Integration with Jira to open tickets automatically

---

## 10. Collaboration and Knowledge Sharing

**Open-sourced in this submission:**
- System prompt (`prompts/audit-use-cases/access-review-agent.md`)
- Python script with synthetic test data (`tools/scripts/access_review_agent.py`, `tools/scripts/test_data/`)
- Example output JSON (`outputs/examples/access-review-findings.json`)
- ISO 27001 and SOC 2 control mappings for Access Management

**Help wanted:**
- Feedback on risk rating calibration — is High/Medium/Low correctly set for access findings?
- SOC 2 CC6 expertise to validate the control mapping rows
- Anyone building a shared synthetic AD/HR dataset for cross-org testing

**Cross-org interest:**
At least three organisations at Session 1 mentioned quarterly access reviews as a pain point. Open to co-developing a shared synthetic dataset and a combined prompt for multi-system access reviews.

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| Plan | Complete | This document |
| Do | Complete | Script and prompt drafted at Session 2 |
| Check | In progress | Testing with synthetic AD/HR exports in `tools/scripts/test_data/` |
| Act | Not started | Target: Hackathon 3 — share validation results and publish refined prompt |

---

## 12. Open Questions

1. Should the agent handle service accounts separately, or is a single prompt sufficient for both human and non-human identities?
2. What is the right threshold for "stale" accounts — 90 days as a universal baseline, or should organisations configure their own policy threshold?
3. Is there a shared synthetic AD/HR dataset in the repo we should all use for consistency in testing and benchmarking?
4. Should role mismatches trigger a Medium or High finding when the affected account also has privileged access?
