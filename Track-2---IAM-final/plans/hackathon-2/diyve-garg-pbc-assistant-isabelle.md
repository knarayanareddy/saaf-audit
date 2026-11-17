# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Diyve Garg, Juriën Huisman, Karim Zemouri, Mourad Fakirou) |
| **Organisation** | Deloitte Netherlands / Auditdienst Rijk / KPN / Wolters Kluwer |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Workflow |
| **Status** | Draft |

---

## 2. Problem Statement

Managing Prepared-by-Client (PBC) requests is one of the most administrative-heavy parts of an audit engagement. Auditors must track which documents have been requested, which have been received, which are overdue, validate received documents for completeness, send reminders, and maintain a status overview — all while managing the relationship with the auditee. "Isabelle" (PBC Assistant) automates this entire workflow: five sequential AI agents take an audit scope and contact details as input and produce a complete PBC list, distribute it, validate received documents, generate a status dashboard, and send targeted reminders — all traceable and consistent across engagements.

---

## 3. Use-Case Type and Scope

**Audit domain:** Audit Engagement Management — PBC (Prepared by Client) Process

**Applicable standards:**

- IIA International Standards for the Professional Practice of Internal Auditing (IPPF) — Standard 2300 (Performing the Engagement)
- ISO 19011 — Guidelines for auditing management systems

**In scope:**

- AI-generated PBC list from audit scope + required document types
- Simulated PBC distribution with delivery status tracking
- Document validation against expected items (completeness check)
- Status dashboard report (received/pending/overdue per item)
- Reminder generation for overdue or incomplete items
- FastAPI web UI for manual PBC management (CRUD, status, file upload, AI analysis)

**Out of scope:**

- Actual email sending (distribution is modelled, not executed)
- Integration with external document management systems (SharePoint, OneDrive)
- Legal review or substantive testing of received documents

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Five agent system prompts (PBC creation, distribution, validation, dashboard, reminders) — in `pbc_workflow/agents.py` of the [PBC-Assistant repo](https://github.com/SAAF-Project/PBC-Assistant-Isabelle---IA-AI-Hackathon) |
| **Tools** | Python workflow orchestrator (`pbc_workflow/orchestrator.py`), document analysis agent (`pbc_workflow/document_agent.py`), FastAPI web UI (`app.py`) |
| **Regulatory** | IIA standards referenced in PBC creation agent; reuse `regulatory/` for engagement-specific control mappings |
| **Outputs** | PBC list, delivery status, validation report, status dashboard, reminder log — all as structured JSON; AI document commentary via Claude |

---

## 5. Prompts

### System prompt (draft — PBC creation agent)

```
You are an internal audit assistant specialised in creating Prepared-by-Client (PBC) lists.
Given an audit scope, audit period, and a list of required document types, produce a
complete, structured PBC list with: item ID, description, responsible contact, deadline,
and priority.
Base the list on standard audit practice — be specific and actionable.
Never request documents that are not relevant to the stated audit scope.
```

### Example user prompts

**Prompt 1 — PBC creation:**
```
Audit scope: Access management controls for FY 2025.
Audit period: 1 January 2025 – 31 December 2025.
Required document types: user access lists, joiner-mover-leaver logs, access review evidence, privilege account inventory.
Auditee contact: Sarah Johnson, IT Manager, sarah.johnson@auditee.com.

Generate a complete PBC list with item IDs, descriptions, deadlines, and priorities.
```

**Prompt 2 — reminder generation:**
```
PBC status as of today:
- PBC-001 (signed trial balance): received ✓
- PBC-002 (general ledger): overdue by 5 days
- PBC-003 (access review evidence): not yet submitted, deadline in 2 days

Generate targeted reminder messages for overdue and at-risk items.
Tone: professional, non-accusatory.
```

**Intended file location:** `prompts/audit-use-cases/pbc-assistant.md`

---

## 6. Tools and Techniques

### Approach

Five AI agents run sequentially, each passing its output as input to the next:

1. **PBC_Creation_Agent** — takes audit scope + required documents → produces structured PBC list
2. **PBC_Distribution_Agent** — models distribution to auditee contacts → tracks delivery status
3. **Document_Validation_Agent** — compares received documents against PBC list → flags gaps
4. **Status_Dashboard_Agent** — aggregates status per item → produces dashboard report
5. **Reminder_Agent** — generates targeted reminders for overdue/incomplete items

A FastAPI web UI sits alongside the workflow for manual interaction: auditors can manage PBC items (CRUD), upload received documents (PDF/XLSX/DOCX/CSV), and trigger AI document analysis via the Document Analysis Agent (Claude claude-opus-4-6).

### Example script or pseudocode

```python
from pbc_workflow.orchestrator import run_pbc_workflow
from pbc_workflow.models import AuditeeContact

result = run_pbc_workflow(
    audit_scope="Access management controls FY 2025",
    audit_period="1 Jan – 31 Dec 2025",
    required_documents=["user access list", "JML log", "access review evidence"],
    auditee_contact=AuditeeContact(
        name="Sarah Johnson",
        email="sarah.johnson@auditee.com",
        role="IT Manager",
    ),
)

print(result.pbc_list)          # structured PBC items
print(result.dashboard_report)  # status overview
print(result.reminder_log)      # generated reminders
```

**Tech stack used:** Python 3.9+, Claude API (claude-opus-4-6), FastAPI, `pypdf`, `openpyxl`, `python-docx`

**Intended file location:** `tools/scripts/pbc-assistant/` (reference [PBC-Assistant repo](https://github.com/SAAF-Project/PBC-Assistant-Isabelle---IA-AI-Hackathon))

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF Standard 2300 | Performing the Engagement — evidence collection and documentation |
| IIA IPPF Standard 2400 | Communicating Results |
| ISO 19011 Clause 6.4 | Collecting and verifying information |

### Claude / AI tool usage notes

Document content sent to the API for analysis should be synthetic or anonymized. The document analysis agent caps input at 40,000 characters per file. No real personal data, financial records, or confidential client information should be processed through the API in production use. The API key is loaded from environment variables only.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** JSON (all agent outputs), HTML (web UI)

**Schema reference:** PBC list items and validation findings can be mapped to `outputs/schemas/finding-schema.json` — gaps between expected and received documents become findings.

### Synthetic example output

```json
{
  "id": "F-PBC-002",
  "title": "General ledger not received — 5 days overdue",
  "risk_rating": "Medium",
  "observation": "PBC item PBC-002 (full-year general ledger) was due 2026-03-01 and has not been received as of 2026-03-06. No response received from David Wilson (contact person).",
  "recommendation": "Send escalation reminder to David Wilson and copy the engagement manager. If not received within 2 business days, flag as a scope limitation in the audit report."
}
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6)
- [x] Python 3.9+
- [x] FastAPI (web UI + REST API)
- [x] GitHub (fork + PR)

**Stretch goals:**

- [ ] Real email integration (SMTP / Microsoft Graph) for actual PBC distribution and reminders
- [ ] SharePoint / OneDrive integration for document upload
- [ ] Integration with TeamMate+ or other audit management systems

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Five agent system prompts (PBC creation, distribution, validation, dashboard, reminders)
- Python workflow orchestrator and all agent modules
- FastAPI web UI with document upload and AI analysis
- Data models (`pbc_workflow/models.py`)

**What help I'm looking for:**

- Auditors at other organizations to test PBC list quality against their standard engagement templates
- Input on reminder tone and escalation thresholds
- Interest from organizations using specific audit management platforms for integration

**Video Transcription Insights (Hackathon #3 analysis):**

**Local voice dictation for fieldwork with Parakeet 3:**

A pattern from video analysis that directly extends this plan: **local voice dictation for PBC note-taking in the field**. NVIDIA's Parakeet 3 (a fast, local speech-to-text model) enables auditors to dictate PBC observations, evidence gaps, and interview notes from their phone or laptop without sending audio to a cloud API.

Integration with this plan:
- Auditor dictates: "Vendor X cannot produce the signed contract for service agreement Z" — Parakeet 3 transcribes locally in <2 seconds
- The transcription is passed to the PBC validation agent, which maps it to the relevant PBC line item and flags the open item
- Local processing ensures compliance with GDPR Art. 32 — interview audio and client conversations never leave the device
- Parakeet 3 runs on CPU (no GPU required) via Hugging Face Transformers; install: `pip install transformers torch` + 600MB model download

This converts PBC management from a back-office activity (auditor returns to office, types up notes) into a real-time field workflow. See [`plans/hackathon-3/always-on-audit-agent.md`](../hackathon-3/always-on-audit-agent.md) for the companion always-on agent pattern.

**Cross-org interest:**

PBC management is a universal pain point across internal and external audit functions. The five-agent workflow is directly reusable across all 45+ SAAF organizations. The document analysis module (AI commentary on uploaded audit evidence) is independently reusable as a standalone skill.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan |
| **Do** | Complete | Working prototype (5-agent workflow + FastAPI UI) built at Hackathon 1 (March 10, 2026) |
| **Check** | Not started | Planned: test with real PBC processes at Deloitte, Auditdienst Rijk, KPN, Wolters Kluwer |
| **Act** | Not started | Target: Hackathon 3 — share cross-org learnings and add real email integration |

---

## 12. Open Questions

1. How should the agent handle PBC items where the auditee provides a document that partially satisfies the request — should it flag as Partial or prompt the auditor to specify what is still missing?
2. What is the right escalation path when a PBC item is significantly overdue — does the agent draft an email to the engagement manager, or only to the auditee contact?
3. Is there interest in a shared, maintained PBC template library (standard document request lists per audit domain) that all SAAF organizations can contribute to?
