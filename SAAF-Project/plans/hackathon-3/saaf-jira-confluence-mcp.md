# SAAF Jira & Confluence MCP Integration

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

Internal audit fieldwork involves heavy evidence collection from IT systems, particularly:

- **Jira**: incident tickets, change requests, access request workflows
- **Confluence**: IT policies, procedures, SOPs, control documentation

Currently, auditors manually export data from these systems (CSV exports, copy-paste from browser), then analyse it in Excel or Word. This process is:

- **Slow** — a Jira evidence export for a change management audit takes 1-2 hours per auditor
- **Error-prone** — manual filtering and formatting introduces mistakes
- **Non-repeatable** — each auditor does it differently; no shared query templates

The emergence of the **Model Context Protocol (MCP)** offers a better approach: Claude Code can query Jira and Confluence directly via MCP servers, enabling audit agents to pull evidence programmatically without manual export steps.

This plan builds and documents two MCP servers:
1. **`saaf-jira-mcp`** — queries Jira issues by JQL; fetches issue detail, comments, attachments metadata
2. **`saaf-confluence-mcp`** — searches Confluence spaces; fetches page content (policies, SOPs)

Tested against the Strapi synthetic data sandbox (simulated Jira) during Hackathon #3.

---

## 3. Use-Case Type and Scope

**Audit domain:** IT Infrastructure — MCP Integration (Jira + Confluence)

**Applicable standards:**

- ITIL (Change Management — Jira change tickets as primary evidence)
- COBIT BAI06 (Manage IT Changes)
- ISO 27001 A.8.32 (Change management)
- GDPR Art. 5 (Data minimisation — only query fields needed for audit)

**In scope:**

- MCP server: Jira — JQL query execution, issue fetch, comment fetch
- MCP server: Confluence — page search by space/label, page content fetch
- Claude Code integration: both MCP servers usable from Claude Code CLI (`claude --mcp-config saaf-mcps.json`)
- Strapi fallback: MCP server can target Strapi sandbox API (for hackathon testing without real Jira)
- Configuration guide: how to configure the MCP servers for real Jira/Confluence Cloud

**Out of scope:**

- Write operations (creating/updating Jira issues or Confluence pages)
- Jira Service Management (separate API surface)
- On-premise Jira/Confluence (cloud REST API only for v1)
- Attachments download (metadata only in v1)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Claude Code system prompt extension: how to use the Jira/Confluence MCP tools within an audit agent context; example tool-use patterns for evidence collection |
| **Tools** | Two MCP servers (`tools/mcp/saaf-jira-mcp/`, `tools/mcp/saaf-confluence-mcp/`); MCP config file (`saaf-mcps.json`); test script (`tools/scripts/test_mcp_connections.py`) |
| **Regulatory** | Data minimisation guidance: which Jira/Confluence fields to query for each audit domain; GDPR Art. 5 compliance checklist for MCP queries |
| **Outputs** | Structured evidence objects (JSON) passed to audit agent for analysis; evidence package Markdown (for workpaper documentation) |

---

## 5. Prompts

### System prompt (draft)

```
You are an IT audit evidence collector with access to Jira and Confluence via MCP tools.

Available tools:
- jira_search(jql, fields, max_results): Search Jira issues using JQL
- jira_get_issue(issue_key): Get full details of a specific Jira issue
- confluence_search(query, space_key, label): Search Confluence pages
- confluence_get_page(page_id): Get the full content of a Confluence page

Audit principles to follow:
- Query only the fields you need (data minimisation)
- Document every query you execute (audit trail)
- Never use write operations
- Flag when evidence appears incomplete or inconsistent
- Cross-reference Jira tickets with Confluence policies where relevant

When gathering evidence, always:
1. State the audit objective
2. Execute queries with explanatory comments
3. Summarise what was found and what was NOT found
4. Flag exceptions or anomalies immediately
```

### Example user prompts

**Prompt 1 — Change management evidence:**
```
Audit objective: Test the change management control for the Q1 2026 change freeze period
(Jan 15 – Feb 15, 2026).

Using the Jira MCP, find all change tickets implemented during the freeze period.
Then check the Confluence change management policy to understand what was permitted
during the freeze.

Flag any changes that appear to violate the freeze policy.
```

**Prompt 2 — Access request workflow audit:**
```
Audit objective: Verify that all privileged access requests in the past 90 days were
properly approved before access was granted.

Search Jira for access request tickets (project = IAM, type = "Access Request")
created in the past 90 days. For each ticket:
- Was it approved before the access grant date?
- Who approved it (is the approver in the authorisation matrix)?
- Was there a business justification?

Produce an exception list for any ticket that failed these checks.
```

**Intended file location:** `prompts/audit-use-cases/jira-confluence-mcp.md`

---

## 6. Tools and Techniques

### Approach

**MCP Server architecture (TypeScript):**

```typescript
// tools/mcp/saaf-jira-mcp/src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({ name: "saaf-jira-mcp", version: "1.0.0" }, {
  capabilities: { tools: {} }
});

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "jira_search",
      description: "Search Jira issues using JQL",
      inputSchema: {
        type: "object",
        properties: {
          jql: { type: "string", description: "JQL query string" },
          fields: { type: "array", items: { type: "string" } },
          max_results: { type: "number", default: 50 }
        },
        required: ["jql"]
      }
    },
    {
      name: "jira_get_issue",
      description: "Get full details of a Jira issue",
      inputSchema: {
        type: "object",
        properties: { issue_key: { type: "string" } },
        required: ["issue_key"]
      }
    }
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "jira_search") {
    const { jql, fields = ["summary", "status", "assignee", "created", "resolved"], max_results = 50 } = request.params.arguments;
    const response = await fetch(
      `${process.env.JIRA_BASE_URL}/rest/api/3/search?jql=${encodeURIComponent(jql)}&fields=${fields.join(",")}&maxResults=${max_results}`,
      { headers: { Authorization: `Basic ${btoa(`${process.env.JIRA_EMAIL}:${process.env.JIRA_API_TOKEN}`)}` } }
    );
    return { content: [{ type: "text", text: JSON.stringify(await response.json()) }] };
  }
});
```

**Strapi fallback (for Hackathon #3 testing):**

When `JIRA_BASE_URL` is not set, the MCP server falls back to querying the Strapi sandbox API, translating JQL to Strapi filter syntax.

**Tech stack used:** TypeScript (Node.js 18), `@modelcontextprotocol/sdk`, Jira REST API v3, Confluence REST API v2, optionally Strapi 4 (testing fallback)

**Intended file location:** `tools/mcp/saaf-jira-mcp/`, `tools/mcp/saaf-confluence-mcp/`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| GDPR Art. 5(1)(c) | Data minimisation — query only audit-relevant fields |
| ISO 27001 A.5.28 | Collection of evidence — maintain audit trail of evidence queries |
| COBIT BAI06 | Change Management — use Jira as authoritative change record |

### Claude / AI tool usage notes

- MCP servers only perform READ operations against Jira/Confluence.
- API tokens stored in environment variables only; never committed.
- During hackathon: all queries target Strapi sandbox with synthetic data — no real Jira/Confluence.
- Data returned by MCP servers contains only synthetic records (Strapi) or publicly non-sensitive change data (real Jira, with permission).

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts (MCP uses `fetch` in TypeScript)
- [x] No runtime `pip install` (TypeScript/npm build only)
- [x] MCP servers live in `tools/mcp/` (not `tools/scripts/`, TypeScript exception)
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only (`JIRA_API_TOKEN`, `CONFLUENCE_API_TOKEN`)

---

## 8. Output Format and Examples

**Format:** JSON (raw API response, structured by MCP server) → passed to Claude for analysis → Markdown evidence summary

**Schema reference:** N/A (evidence collection, not findings — findings conform to `outputs/schemas/finding-schema.json`)

### Synthetic example — jira_search result

```json
{
  "total": 3,
  "issues": [
    {
      "key": "CHG-2025-0441",
      "summary": "Emergency deployment — payment gateway patch",
      "status": "Done",
      "priority": "Critical",
      "created": "2026-01-22T09:15:00Z",
      "resolved": "2026-01-22T11:30:00Z",
      "is_emergency": true,
      "approval_status": "Emergency approved (post-hoc)",
      "change_freeze_active": true,
      "exception_flag": "Change implemented during freeze period without pre-approval"
    }
  ]
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] TypeScript (Node.js 18)
- [x] `@modelcontextprotocol/sdk`
- [x] Jira REST API v3 (or Strapi fallback)
- [x] Confluence REST API v2 (or Strapi fallback)
- [x] Claude Code (MCP client)

**Stretch goals:**

- [ ] Strapi fallback with full JQL → Strapi filter translation
- [ ] Confluence: full page HTML → Markdown conversion for clean agent context
- [ ] Jira: attachment metadata (list filenames, sizes — not download)
- [ ] Python wrapper (`tools/scripts/mcp_evidence_collector.py`) for non-Claude-Code usage
- [ ] Pre-built Claude Code slash command: `/collect-evidence --domain change-management`

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Both MCP server implementations (TypeScript)
- MCP config file template (`saaf-mcps.json`)
- Setup guide for real Jira/Confluence Cloud connection
- Example audit prompts using the MCP tools

**What help I'm looking for:**

- Engineers familiar with the MCP SDK (TypeScript) for code review
- Auditors to design realistic JQL queries per audit domain
- Jira/Confluence administrators to test against real instances (with permission)

**Cross-org interest:**

Jira is used as an ITSM tool by Schuberg Philis, Mollie, Wolters Kluwer, and likely many other SAAF member organisations. The MCP approach means any Claude Code agent can use these tools without organisation-specific code changes — just a different `JIRA_BASE_URL`.

**Video Transcription Insights (Hackathon #3 analysis):**

Two alternatives to the MCP pattern were identified in video analysis, relevant when MCP development is too complex or when the target system has no REST API:

1. **n8n MCP toolkit**: n8n's recent AI agent nodes include a native MCP tool connector. For teams already running n8n workflows, this is a lower-friction path to Jira/Confluence integration than building a TypeScript MCP server from scratch. Tradeoff: less control over tool schema; n8n workflow dependency. See [`plans/hackathon-3/n8n-audit-workflow-migration.md`](n8n-audit-workflow-migration.md) for migration considerations.

2. **CLI wrapper alternative**: For Jira and Confluence instances that expose a strong CLI (e.g., Jira CLI, Confluence CLI tools), the `cli-audit-system-wrapper.md` pattern may be simpler than an MCP server — no TypeScript required, no server process to maintain. Suitable for single-user or small-team scenarios. See [`plans/hackathon-3/cli-audit-system-wrapper.md`](cli-audit-system-wrapper.md).

**Recommended approach**: MCP server for production/team use; CLI wrapper for quick prototyping; n8n for teams already in the n8n ecosystem.

**Related SAAF plans:**

- [`plans/hackathon-2/frank-van-dissel-uc3-incident-issue-intelligence.md`](../hackathon-2/frank-van-dissel-uc3-incident-issue-intelligence.md) — primary consumer of the Jira MCP
- [`plans/hackathon-3/saaf-strapi-synthetic-data.md`](saaf-strapi-synthetic-data.md) — provides the test data for MCP development
- [`plans/hackathon-2/koekenpan-ia-fieldwork-preparation.md`](../hackathon-2/koekenpan-ia-fieldwork-preparation.md) — fieldwork preparation benefits from Confluence policy retrieval
- [`docs/reference/skills-and-agents.md`](../../docs/reference/skills-and-agents.md) — Change Management Analyzer agent is a key consumer
- [`plans/hackathon-3/cli-audit-system-wrapper.md`](cli-audit-system-wrapper.md) — CLI alternative for legacy Jira/Confluence CLI setups
- [`plans/hackathon-3/n8n-audit-workflow-migration.md`](n8n-audit-workflow-migration.md) — n8n MCP toolkit as alternative integration path

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | MCP architecture defined; tool schema designed; Strapi fallback approach clear |
| **Do** | In progress | Both MCP servers + Strapi fallback at Hackathon #3 |
| **Check** | Not started | Validate: can audit agents successfully execute evidence collection via MCP? |
| **Act** | Not started | Target: test against real Jira instance (with permission) at Hackathon #4 |

---

## 12. Open Questions

1. Should the Strapi fallback translate JQL exactly, or should it use a simpler filter syntax and document the limitations?
2. Does the Jira REST API v3 (cloud) vs. v2 (server) difference affect this plan? Most SAAF members will be on Jira Cloud.
3. Are there rate limiting considerations for the Jira REST API that affect bulk evidence collection (e.g. 1,000 change tickets)?
4. Should the Confluence MCP return raw storage format HTML or Markdown? Markdown is cleaner for Claude but requires conversion.
