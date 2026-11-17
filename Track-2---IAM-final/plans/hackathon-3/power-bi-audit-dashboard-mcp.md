# Power BI Audit Dashboard MCP

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

Audit findings and control statuses live in disconnected documents and spreadsheets. Management and audit committees want live dashboards — but building Power BI reports manually from audit findings is time-consuming and requires BI skills most auditors don't have.

The gap: Claude agents produce structured findings (JSON, Markdown), but there is no automated path from agent output to a management-ready Power BI dashboard. Every reporting cycle requires a manual export-import loop.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Reporting / Audit Committee Communication

**Applicable standards:**

- IIA IPPF — Standard 2400 (Communicating Results), 2420 (Quality of Communications)
- EU AI Act — Art. 13 (Transparency)

**In scope:**

- MCP server that exposes Power BI Dataset API as Claude-callable tools
- Tools: push findings to Power BI dataset, refresh a report, query dataset status
- Dashboard templates: risk heat map, control status overview, evidence summary
- Integration with `finding-schema.json` output from any SAAF agent

**Out of scope:**

- Building the Power BI report visuals (those are pre-built templates)
- Power BI Embedded (this targets Power BI Service for organizational use)
- Real-time streaming datasets (batch push per audit run is sufficient)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What is produced or reused |
|---|---|
| **Prompts** | Reporting prompt: "summarize all High findings for the audit committee slide" |
| **Tools** | TypeScript MCP server (`tools/mcp/power-bi-mcp/`) wrapping Power BI REST API |
| **Regulatory** | IIA 2420 (quality of communications) — dashboard templates meet audit committee standards |
| **Outputs** | Power BI dataset rows conforming to `finding-schema.json`; dashboard template (`.pbix`) |

---

## 5. Prompts

### System prompt (draft)

```
You are an audit reporting assistant with access to a Power BI dataset via MCP tools.
When asked to report findings:
1. Retrieve open findings from the audit results in context
2. Push each finding to the Power BI dataset using push_finding tool
3. Trigger a dataset refresh using refresh_dataset tool
4. Confirm the number of findings pushed and the refresh status
Never modify or delete existing Power BI data — only append new findings.
Always use finding IDs from finding-schema.json format (F-XXXX).
```

### Example user prompts

**Prompt 1 — Push findings:**
```
Push all High and Medium findings from today's vendor assessment run to the Power BI audit dashboard.
Use the finding-schema format. Confirm how many were pushed and the dataset refresh status.
```

**Prompt 2 — Query for committee:**
```
Retrieve all open findings rated High from the Power BI dataset.
Summarize them in a 5-bullet executive summary suitable for the audit committee.
Include: total count, top 3 risks by domain, oldest open finding date.
```

**Intended file location:** `prompts/audit-use-cases/power-bi-reporting.md`

---

## 6. Tools and Techniques

### Approach

The MCP server wraps the Power BI REST API (Push Datasets endpoint). It exposes three tools to Claude:

1. `push_finding` — appends a finding row to the Power BI streaming dataset
2. `refresh_dataset` — triggers a dataset refresh to update report visuals
3. `query_findings` — retrieves findings from the dataset with optional filters

Authentication uses Power BI Service Principal (Azure AD app registration + client credentials). For hackathon testing, a mock REST endpoint (Strapi) replaces the Power BI API.

### Example script or pseudocode

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";

const PBI_API = process.env.POWER_BI_API_URL ?? "http://localhost:1337/api";
const PBI_TOKEN = process.env.POWER_BI_TOKEN ?? "";
const DATASET_ID = process.env.POWER_BI_DATASET_ID ?? "";

const server = new Server(
  { name: "power-bi-audit-mcp", version: "0.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "push_finding") {
    const finding = args as {
      id: string; title: string; risk_rating: string;
      observation: string; recommendation: string; domain: string;
    };
    const response = await fetch(
      `${PBI_API}/datasets/${DATASET_ID}/rows`,
      {
        method: "POST",
        headers: { "Authorization": `Bearer ${PBI_TOKEN}`, "Content-Type": "application/json" },
        body: JSON.stringify({ rows: [finding] }),
      }
    );
    const status = response.ok ? "pushed" : `error: ${response.status}`;
    return { content: [{ type: "text", text: JSON.stringify({ finding_id: finding.id, status }) }] };
  }

  if (name === "refresh_dataset") {
    await fetch(`${PBI_API}/datasets/${DATASET_ID}/refreshes`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${PBI_TOKEN}` },
    });
    return { content: [{ type: "text", text: JSON.stringify({ status: "refresh triggered" }) }] };
  }

  throw new Error(`Unknown tool: ${name}`);
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

**Tech stack used:** TypeScript, MCP Server SDK, Power BI REST API, Azure AD (service principal)

**Intended file location:** `tools/mcp/power-bi-mcp/index.ts`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF 2400 | Communicating results — automated push from agent to dashboard reduces reporting lag |
| IIA IPPF 2420 | Quality of communications — dashboard templates enforce consistent finding structure |
| EU AI Act Art. 13 | Transparency — dashboard must show which findings were AI-generated and human-reviewed |

### Claude / AI tool usage notes

Power BI receives structured finding data from Claude agents. The data pushed to Power BI should be synthetic during testing. For production: findings pushed to Power BI should be human-reviewed (auditor approved) before push, as Power BI reports are visible to audit committee.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Power BI dataset rows (JSON) + dashboard refresh confirmation

**Schema reference:** `outputs/schemas/finding-schema.json`

### Synthetic example output (push confirmation)

```json
{
  "pushed": 14,
  "skipped": 0,
  "dataset_refresh": "triggered",
  "findings_summary": {
    "High": 3,
    "Medium": 7,
    "Low": 4
  },
  "dashboard_url": "https://app.powerbi.com/groups/.../reports/..."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] TypeScript
- [x] MCP Server SDK
- [x] Power BI REST API (or Strapi mock for testing)
- [x] Azure AD service principal (for authentication)

**Stretch goals:**

- [ ] Pre-built `.pbix` dashboard template (risk heat map + control status + evidence summary)
- [ ] Scheduled push: GitHub Actions runs weekly audit and pushes findings automatically
- [ ] Bi-directional: read audit committee feedback from Power BI comments back into Claude

---

## 10. Collaboration and Knowledge Sharing

**What will be open-sourced:**

- MCP server TypeScript source
- Power BI dashboard template (`.pbix`)
- System prompt for reporting agent

**Help requested:**

- Organizations with Power BI Premium or Pro licenses to test the push API
- BI specialists to design dashboard templates that meet audit committee standards
- Azure AD administrators to validate service principal setup instructions

**Cross-org interest:**

Most large Dutch organizations use Microsoft 365 and Power BI. A shared MCP server + dashboard template reduces per-org setup effort significantly.

**Related SAAF plans:**

- [`saaf-jira-confluence-mcp.md`](saaf-jira-confluence-mcp.md) — same MCP pattern for Jira/Confluence
- [`grc-copilot-mindshift-agent.md`](grc-copilot-mindshift-agent.md) — M365 ecosystem integration
- [`rohan-sobha-compliance-report-generator.md`](../hackathon-2/rohan-sobha-compliance-report-generator.md) — findings source

---

## 11. PDCA Positioning

| Phase | Status | Notes |
|---|---|---|
| **Plan** | Complete | MCP architecture defined; tool schema designed |
| **Do** | In progress | Hackathon #3: implement MCP server with Strapi mock; test push_finding |
| **Check** | Not started | Test with real Power BI tenant post-H3 |
| **Act** | Not started | Target: shared dashboard template available to all SAAF orgs |

---

## 12. Open Questions

1. Does Power BI's push dataset API require Premium capacity, or is it available on Pro licenses?
2. Should findings be pushed immediately after generation, or batched at end of audit run?
3. How do we handle finding updates (re-runs that modify an existing finding) — upsert or append?
4. Should the dashboard distinguish AI-generated findings from manually entered findings?
