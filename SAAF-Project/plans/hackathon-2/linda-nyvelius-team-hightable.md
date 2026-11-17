# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Linda Nyvelius, Francois Marais, Julian) |
| **Organisation** | BR1GHT / Booking.com / JTI |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

Internal auditors using TeamMate+ spend time manually searching past audit issues to check whether a current finding has been raised before, how it was resolved, and what recommendation was given. This cross-engagement lookup is tedious, inconsistently done, and relies on institutional memory. HighTable automates this: a Chrome extension injects a sidebar into every TeamMate+ page, where auditors can describe a current issue and instantly see the top 5 most semantically similar past issues — with an AI-drafted recommendation ready to adapt.

---

## 3. Use-Case Type and Scope

**Audit domain:** Internal Audit — Knowledge Reuse / Issue Management

**Applicable standards:**

- IIA International Standards for the Professional Practice of Internal Auditing (IPPF)
- ISO 19011 — Guidelines for auditing management systems

**In scope:**

- Chrome MV3 browser extension injecting a sidebar into TeamMate+ pages
- Python FastAPI backend: fetching Closed-Verified issues from TeamMate+ API (6h TTL cache)
- Semantic similarity search (sentence-transformers `all-MiniLM-L6-v2`) to find top 5 past issues
- Claude API for scoring, explanation, and draft recommendation generation
- Settings page for backend URL + API key

**Out of scope:**

- Integration with audit management systems other than TeamMate+
- Automated creation or update of issues in TeamMate+ (read-only by design)
- On-premise or air-gapped deployment (requires Anthropic API connectivity)

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Claude prompts for issue scoring, explanation, and recommendation drafting (in `backend/claude_client.py` of the [Team-HighTable repo](https://github.com/SAAF-Project/Team-HighTable)) |
| **Tools** | Chrome MV3 extension (`extension/`); Python FastAPI backend (`backend/`) with TeamMate+ client, embeddings, Claude client |
| **Regulatory** | IIA Standards — reuse `regulatory/` for audit standard references |
| **Outputs** | Top-5 similar past issues with similarity scores + AI-drafted recommendation; surfaced in sidebar UI |

---

## 5. Prompts

### System prompt (draft — Claude recommendation drafting)

```
You are an internal audit assistant specialised in drafting audit findings and recommendations.
Given a current audit issue and a set of similar past issues with their resolutions,
score the similarity of each past issue, explain the connection, and draft a recommendation
for the current issue that builds on past resolutions.
Base your output only on the provided past issues — do not invent findings or recommendations.
Never include real names, account numbers, or personal data in your output.
```

### Example user prompts

**Prompt 1:**
```
Current issue: "User accounts of terminated employees were not deactivated within
the agreed 24-hour SLA in 15 out of 50 sampled cases."

Similar past issues: [top-5 results from semantic search]

Score each past issue's similarity (0–1), explain the connection, and draft a
recommendation for the current issue.
```

**Prompt 2:**
```
Current issue: "Change requests were approved by the same person who implemented
the change in 8 out of 30 tested cases."

Similar past issues: [top-5 results from semantic search]

Score similarity, explain connections, and suggest a recommendation drawing on
how similar issues were resolved in past engagements.
```

**Intended file location:** `prompts/audit-use-cases/hightable-recommendation.md`

---

## 6. Tools and Techniques

### Approach

1. **Extension** — Chrome MV3 extension injects a floating 🏛️ button into every TeamMate+ page (`br1ght8.teammatehosting.com`). Auditor opens sidebar, enters current issue description.
2. **Backend — cache** — FastAPI backend fetches all Closed-Verified issues + recommendations from TeamMate+ REST API on startup; refreshes every 6 hours.
3. **Semantic search** — sentence-transformers (`all-MiniLM-L6-v2`) embeds all cached issues + the current issue; cosine similarity selects top 5 matches.
4. **Claude analysis** — Claude API scores similarity, explains each match, and drafts a recommendation for the current issue.
5. **Sidebar display** — extension renders the top 5 past issues + recommendation in the sidebar; auditor adapts and copies to TeamMate+.

### Example script or pseudocode

```python
# backend/main.py (simplified)
@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    issues = await teammate_client.get_effective_issues()   # cached, 6h TTL
    embeddings = embedding_service.embed([r.query for r in issues])
    top5 = embedding_service.top_k(request.query, embeddings, k=5)
    analysis = await claude_analyzer.analyze(request.query, top5)
    return AnalysisResponse(similar_issues=top5, recommendation=analysis)
```

**Tech stack used:** Python 3.11+, FastAPI, sentence-transformers (`all-MiniLM-L6-v2`), Claude API (claude-sonnet-4-6), Chrome MV3 (vanilla JS), TeamMate+ REST API

**Intended file location:** `tools/scripts/hightable-backend/` (reference [Team-HighTable repo](https://github.com/SAAF-Project/Team-HighTable))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF | Standard 2300 — Performing the Engagement; Standard 2400 — Communicating Results |
| ISO 19011 | Clause 6.4 — Collecting and verifying information |

### Claude / AI tool usage notes

Current issue descriptions entered by auditors should not contain real personal data or confidential evidence. The TeamMate+ API connection uses an API key stored in environment variables. The extension settings page allows auditors to configure their own backend URL and key — no credentials are hardcoded.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (API response), rendered in Chrome extension sidebar

**Schema reference:** Similar issues map to `outputs/schemas/finding-schema.json` — each past issue has an observation and recommendation field.

### Synthetic example output

```json
{
  "similar_issues": [
    {
      "id": "ISS-2024-0142",
      "title": "Terminated employee accounts not deactivated within SLA",
      "similarity": 0.94,
      "explanation": "Near-identical control failure: access rights not revoked on time. Resolved by implementing automated deprovisioning trigger from HR system.",
      "past_recommendation": "Implement automated deprovisioning workflow triggered by HR system termination event, with 4-hour SLA and escalation alert."
    }
  ],
  "draft_recommendation": "Implement an automated deprovisioning workflow triggered by the HR termination event, targeting a 4-hour SLA. Configure an escalation alert to the IT service desk if deactivation is not confirmed within the SLA window. Follow up with a 90-day post-implementation review."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-sonnet-4-6)
- [x] Python 3.11+ (FastAPI backend)
- [x] Chrome MV3 extension (vanilla JS)
- [x] sentence-transformers (`all-MiniLM-L6-v2`)
- [x] TeamMate+ REST API

**Stretch goals:**

- [ ] Support for audit management systems beyond TeamMate+ (e.g. AuditBoard, ServiceNow GRC)
- [ ] On-premise embedding model for organizations with data residency requirements
- [ ] Write-back: draft recommendation directly into TeamMate+ issue via API

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Chrome extension (MV3, vanilla JS) — adaptable to any TeamMate+ instance
- Python FastAPI backend with TeamMate+ client, embeddings, and Claude client
- Configuration guide for connecting to a custom TeamMate+ instance

**What help I'm looking for:**

- Auditors at other organizations using TeamMate+ to test and validate the similarity matching quality
- Input on prompt improvements for the recommendation drafting step
- Interest from organizations using other audit management platforms

**Cross-org interest:**

Any organization using TeamMate+ can deploy this agent against their own instance. The semantic similarity + AI recommendation pattern is generalizable to other audit management tools. Strong candidate for cross-org collaboration given the number of TeamMate+ users in the SAAF community.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Working prototype (extension + backend) built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned: deploy against BR1GHT TeamMate+ instance for real engagement use |
| **Act** | Not started | Target: Hackathon 3 — share results and extend to other audit platforms |

---

## 12. Open Questions

1. How should the agent handle issues where the current engagement's context differs significantly from past engagements (different sector, different regulatory scope)?
2. What is the minimum cache size (number of past issues) needed for the semantic search to produce useful results?
3. Is there interest from other SAAF organizations in a shared, maintained version of the backend that any TeamMate+ user can self-host?
