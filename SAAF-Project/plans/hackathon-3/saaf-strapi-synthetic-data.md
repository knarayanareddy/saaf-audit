# SAAF Strapi Synthetic Data Sandbox

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten |
| **Organisation** | SAAF Project |
| **Session** | Hackathon 3 (Session 4) |
| **Type** | Skill |
| **Status** | Draft |

---

## 2. Problem Statement

Every SAAF participant who builds an audit agent needs realistic test data to demonstrate their agent. The problem is:

- **Real data is off-limits** — no participant can use actual audit evidence, access logs, or incident tickets due to privacy and confidentiality obligations
- **DIY synthetic data is inconsistent** — each participant generates their own test data in different formats; agent outputs are not comparable across the community
- **No shared data model** — there is no agreed schema for common audit objects (incident ticket, access review record, vendor contract, audit finding)
- **Testing without data is impossible** — agents that need to reason over a dataset (e.g. 1,000 access review records) cannot be realistically tested with 3 hand-crafted examples

This plan sets up a **Strapi 4 instance** populated with synthetic datasets that all SAAF agents can use as a shared testing sandbox.

---

## 3. Use-Case Type and Scope

**Audit domain:** SAAF Infrastructure — Shared Synthetic Data

**Applicable standards:**

- GDPR (by design: no real personal data; datasets are synthetic)
- ISO 27001 A.8.10 (Information deletion — data lifecycle for synthetic data)

**In scope:**

- Strapi 4 instance with REST API and optional GraphQL
- 5 content types with seed data:
  1. **Jira Incidents** — 500 synthetic IT incident tickets (priority, category, MTTR, resolution)
  2. **Access Reviews** — 200 synthetic user-access-review records (user, role, entitlement, review outcome, reviewer)
  3. **Change Tickets** — 150 synthetic change management records (requested, approved, implemented, tested, emergency flag)
  4. **Vendor Contracts** — 50 synthetic vendor records (name, SLA, last audit date, risk rating, TPRM status)
  5. **Audit Findings** — 100 synthetic audit findings conforming to `outputs/schemas/finding-schema.json`

**Out of scope:**

- Real customer data from any SAAF member organisation
- Strapi authentication / multi-tenant setup (public API for hackathon day, read-only)
- Production-grade hosting (local Docker for v1, Railway/Render for cloud stretch)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | No new prompts — this is data infrastructure. Claude can be used to *generate* the synthetic seed data (see Tools). |
| **Tools** | Strapi 4 Docker setup (`tools/strapi/`); seed data JSON files (`tools/strapi/seed/`); Python seed script (`tools/scripts/seed_strapi.py`); Claude-powered data generator script (`tools/scripts/generate_synthetic_data.py`) |
| **Regulatory** | GDPR compliance by design — all data is synthetic; seed data generator prompt includes instruction to avoid any real personal names or identifying information |
| **Outputs** | REST API endpoints accessible at `http://localhost:1337/api/` (local) or cloud URL; seed data JSON files committed to repo |

---

## 5. Prompts

### System prompt (draft — for synthetic data generation)

```
You are a synthetic data generator for internal audit test scenarios.
You generate realistic-looking but entirely fictional audit data.

Rules:
- Never use real company names, real personal names, or real IP addresses
- Use fictional names that sound plausible (e.g. "Nexara B.V.", "Jan Bergveld")
- Dates should be in the past 12 months, relative to today
- Follow the provided JSON schema exactly
- Include a mix of normal records and exception records (approximately 15% exceptions)
- Exceptions should be realistic: leavers with active accounts, missing reviews, overdue changes, expired vendor assessments

Generate [N] records of type [type] following this schema: [schema JSON]
```

### Example user prompts

**Prompt 1 — Generate access review seed data:**
```
Generate 200 synthetic user access review records following this schema:
{
  "user_id": "string (USR-XXXX)",
  "user_name": "string (fictional)",
  "role": "string (e.g. Developer, Admin, Read-Only)",
  "system": "string (e.g. Active Directory, SAP, AWS)",
  "entitlement": "string",
  "last_review_date": "date (YYYY-MM-DD)",
  "review_outcome": "Approved | Revoked | Escalated | Not reviewed",
  "reviewer": "string (fictional name)",
  "is_exception": "boolean",
  "exception_type": "string (e.g. Leaver with active account, SoD conflict, Overdue review)"
}

Include 30 exception records. Make exceptions realistic for a financial services company.
```

**Prompt 2 — Generate incident seed data:**
```
Generate 500 synthetic Jira-style IT incident tickets for a payment processing company.
Schema: [schema injected here]
Include 75 major incidents (P1/P2) and 425 minor (P3/P4).
Mix categories: network outage, access issue, application error, security alert, data quality.
```

**Intended file location:** `prompts/audit-use-cases/synthetic-data-generator.md`

---

## 6. Tools and Techniques

### Approach

**Phase 1 — Strapi setup:**

```bash
# Docker Compose setup
cd tools/strapi
docker compose up -d
# Access at http://localhost:1337
```

**Phase 2 — Content type definitions:**

Each content type is defined via Strapi's schema builder and exported as JSON in `tools/strapi/src/api/`. Content types match the schemas above.

**Phase 3 — Seed data generation:**

```python
# generate_synthetic_data.py
import anthropic, json
from pathlib import Path

client = anthropic.Anthropic()

def generate_dataset(content_type: str, count: int, schema: dict) -> list[dict]:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": (
                f"Generate {count} synthetic {content_type} records following this schema: "
                f"{json.dumps(schema)}. Return only valid JSON array."
            )
        }]
    )
    return json.loads(response.content[0].text)
```

**Phase 4 — Seed loading:**

```python
# seed_strapi.py — POSTs generated data to Strapi API
import requests

def seed(content_type: str, records: list[dict], strapi_url: str) -> None:
    for record in records:
        requests.post(f"{strapi_url}/api/{content_type}s", json={"data": record})
```

**Tech stack used:** Strapi 4 (Node.js 18), Docker Compose, Python 3.9+, Claude API (claude-sonnet-4-6 — seed data generation), optionally Railway/Render for cloud hosting

**Intended file location:** `tools/strapi/`, `tools/scripts/seed_strapi.py`, `tools/scripts/generate_synthetic_data.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GDPR Art. 4 | Personal data definition — synthetic data does not qualify as personal data |
| GDPR Art. 25 | Privacy by design — synthetic data approach eliminates GDPR risk by design |
| ISO 27001 A.8.10 | Information deletion — seed data can be wiped/reset between hackathons |

### Claude / AI tool usage notes

- Data generation prompt explicitly prohibits real personal names, company names, or identifying information.
- Generated data is reviewed before committing to the repo (spot-check for accidental PII).
- Strapi instance is local-only by default; cloud deployment uses Railway/Render with environment-variable-based credentials.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** REST API (JSON responses) + seed data JSON files

**Schema reference:** Audit findings content type follows `outputs/schemas/finding-schema.json`

### Synthetic example — access review record

```json
{
  "user_id": "USR-0042",
  "user_name": "Anke Bergveld",
  "role": "System Administrator",
  "system": "Active Directory",
  "entitlement": "Domain Admin",
  "last_review_date": "2025-08-15",
  "review_outcome": "Not reviewed",
  "reviewer": null,
  "is_exception": true,
  "exception_type": "Leaver with active privileged account",
  "employment_end_date": "2025-10-01",
  "days_since_termination": 197
}
```

### Synthetic example — incident ticket

```json
{
  "ticket_id": "INC-2025-0441",
  "title": "Payment gateway timeout — checkout failure",
  "priority": "P1",
  "category": "Application Error",
  "reported_at": "2025-11-12T14:32:00Z",
  "resolved_at": "2025-11-12T17:15:00Z",
  "mttr_hours": 2.72,
  "assigned_team": "Platform Engineering",
  "root_cause": "Database connection pool exhausted due to unoptimised query",
  "post_incident_review_completed": false,
  "is_exception": true,
  "exception_type": "No post-incident review within SLA (5 business days)"
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Strapi 4 (Docker Compose, local)
- [x] Claude API (claude-sonnet-4-6 — seed data generation)
- [x] Python 3.9+ (seed loader)
- [x] 5 content types with 500/200/150/50/100 seed records

**Stretch goals:**

- [ ] Cloud hosting on Railway or Render (shared URL accessible to all participants on hackathon day)
- [ ] Read-only API token for hackathon day (no write access for participants)
- [ ] GraphQL endpoint (Strapi built-in, enable plugin)
- [ ] Reset endpoint: POST /api/reset-seed to restore to clean state between demos
- [ ] Faker.js-based seed generation (faster than Claude API for large datasets)

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Docker Compose setup for Strapi 4
- All 5 content type schemas (JSON)
- Seed data generation prompts
- Python seed loader script
- 1,000 synthetic records (pre-generated, committed to repo)

**What help I'm looking for:**

- Engineers: help with Docker setup and Railway/Render deployment
- Auditors: validate that exception rates and types in seed data are realistic
- Analysts: suggest additional content types or fields that would make demos more realistic

**Cross-org interest:**

Shared test data is a prerequisite for meaningful cross-org comparisons during hackathons. Any agent that claims to process 1,000 access reviews or 500 incidents needs a dataset to demonstrate against. This is foundational infrastructure for "build more, send less."

**Related SAAF plans:**

- [`plans/hackathon-3/saaf-jira-confluence-mcp.md`](saaf-jira-confluence-mcp.md) — Strapi can simulate the Jira API for agents that don't have real Jira access
- [`plans/hackathon-3/saaf-rag-knowledge-base.md`](saaf-rag-knowledge-base.md) — synthetic policy documents can be included in the RAG corpus
- [`plans/hackathon-2/example-synthetic-access-review.md`](../hackathon-2/example-synthetic-access-review.md) — predecessor access review example

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | 5 content types defined; Docker setup designed; seed generation approach clear |
| **Do** | In progress | Strapi setup + 1,000 seed records generated at Hackathon #3 |
| **Check** | Not started | Validate: can participants successfully query and use the sandbox data? |
| **Act** | Not started | Target: cloud-hosted Strapi instance live before Hackathon #4 |

---

## 12. Open Questions

1. Should the Strapi instance be local-only (each participant runs Docker) or cloud-hosted (one shared instance)? Cloud is more convenient but requires a hosting decision.
2. How many seed records per content type is "enough" for a realistic demo? 500 incidents, 200 access reviews — is this the right scale?
3. Should seed data be committed to the repo (large JSON files) or generated on-the-fly from the seed script?
4. Can the Strapi API be made to behave like the real Jira REST API (same endpoint structure) for agents built against the Jira schema?
