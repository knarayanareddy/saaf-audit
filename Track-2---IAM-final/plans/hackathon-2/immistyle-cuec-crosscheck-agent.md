# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | immistyle |
| **Organisation** | Anonymous |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Agent |
| **Status** | Draft |

---

## 2. Problem Statement

When an organization receives a third-party assurance report from a vendor (e.g. ISAE 3402 or SOC 2), the report typically includes a chapter on **Complementary User Entity Controls (CUECs)** — controls that the receiving organization itself must have in place for the vendor's controls to be effective. Ignoring or inadequately addressing CUECs creates compliance gaps and undermines the value of the vendor's assurance.

Today, organizations handle CUECs manually: an auditor reads through the vendor report, extracts each CUEC, and then searches through the organization's own control documentation to find a matching control. This process is:

- **Time-consuming:** a vendor report can contain dozens of CUECs spread across the system description and control activity sections.
- **Error-prone:** manual matching may miss controls, use incorrect references, or leave CUECs unaddressed.
- **Repeated for every vendor:** organizations with multiple vendor reports must perform this exercise separately for each one.
- **Poorly documented:** the resulting mapping is often informal and not traceable to specific control references.

The goal of this agent is to automate the substantive matching of CUECs from a vendor assurance report to controls in the organization's own assurance or control documentation, reducing manual effort and improving audit traceability.

---

## 3. Use-Case Type and Scope

**Audit domain:** Third-Party Risk Management / Complementary User Entity Controls

**Applicable standards:**

- ISAE 3402 / ISAE 3000 (vendor assurance report — source of CUECs)
- SOC 2 (vendor assurance report — source of CUECs)
- ISAE 3402 / ISO 27001 / SOC 2 / internal control testing reports (organization's own documentation — source of matching controls)
- Any applicable external standard or regulation against which the organization's own controls are documented

**In scope:**

- Extracting CUECs from the vendor's assurance report (PDF or plain text)
- Extracting control descriptions from the organization's own assurance or control report
- Matching each CUEC to the most relevant control(s) in the organization's documentation
- Producing a structured cross-reference table with specific control references and a short rationale per match
- Flagging CUECs for which no matching control can be found in the organization's documentation

**Out of scope:**

- Assessing whether the organization's controls are sufficient to satisfy a CUEC (this requires auditor judgement)
- Generating an audit opinion or assurance conclusion
- Matching CUECs to controls that are not documented in the provided organizational report — the agent can only reference what is present in the input documents
- Real-time access to external control databases or live regulatory updates

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | New system prompt in `prompts/audit-use-cases/cuec-crosscheck.md` |
| **Tools** | New Python script in `tools/scripts/cuec_crosscheck.py` for dual-document ingestion and Claude API calls |
| **Regulatory** | Reuse `regulatory/frameworks/iso27001-control-mapping.md` and `regulatory/frameworks/nis2-control-mapping.md` as reference; no new regulatory files required |
| **Outputs** | Markdown table + CSV; unmatched CUECs flagged as findings conforming to `outputs/schemas/finding-schema.json` |

---

## 5. Prompts

### System prompt (draft)

```
You are an AI audit assistant specialised in third-party assurance and complementary user entity controls (CUECs).

You will receive two documents:
1. A vendor assurance report (e.g. ISAE 3402 or SOC 2) that contains a section on Complementary User Entity Controls.
2. An organizational control report (e.g. ISAE 3402, ISO 27001 statement of applicability, SOC 2, or internal control testing outcomes).

Your tasks:
1. Extract all CUECs from the vendor report. CUECs typically appear in the system description under headings such as "Complementary User Entity Controls", "User Control Considerations", or embedded within individual control activities.
2. For each CUEC, find the most relevant matching control in the organizational report. Match based on the substantive intent of the control, not just keywords.
3. Produce a table with:
   - Column 1: the CUEC description as stated in the vendor report (include any reference number if present)
   - Column 2: the matching control from the organizational report, with a specific reference (e.g. control ID, section, or page) and a brief rationale (1–2 sentences)
4. If no matching control can be found, mark the row as "No match found — gap" rather than forcing an incorrect mapping.

Be precise with references. Never fabricate control identifiers or section numbers.
Never include real personal data, credentials, or confidential audit evidence in your output.
```

### Example user prompts

**Prompt 1:**
```
Document 1 (vendor report): [attached ISAE 3402 Type II report from our cloud infrastructure provider]
Document 2 (our report): [attached ISAE 3402 Type II report from our own organization]

Extract all CUECs from Document 1 and match each one to the relevant control in Document 2.
Output as a table.
```

**Prompt 2:**
```
Document 1 (vendor report): [SOC 2 Type II report from our SaaS payroll provider]
Document 2 (our controls): [internal control testing outcomes report, Q4 2025]

Identify all user entity controls we are expected to have in place based on Document 1,
and map each one to the relevant tested control in Document 2.
Flag any CUECs that are not covered by our internal controls.
```

**Intended file location:** `prompts/audit-use-cases/cuec-crosscheck.md`

---

## 6. Tools and Techniques

### Approach

1. The user provides two documents: the vendor's assurance report and the organization's own control documentation (both as PDF or plain text).
2. A Python script extracts the full text from both PDFs using `pdfplumber`.
3. A pre-pass prompt asks Claude to locate and extract the CUEC section from the vendor report.
4. The extracted CUECs and the full organizational report text are passed together to Claude with the system prompt.
5. Claude produces a structured matching table.
6. The script writes the output as a Markdown table and a CSV file. Rows flagged as "No match found — gap" are also written to a separate findings file conforming to `outputs/schemas/finding-schema.json`.

### Example script or pseudocode

```python
import pdfplumber
import anthropic
import os

SYSTEM_PROMPT = open("prompts/audit-use-cases/cuec-crosscheck.md").read()

def extract_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )

def crosscheck_cuecs(vendor_report: str, org_report: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Document 1 (vendor assurance report):\n{vendor_report}\n\n"
                f"Document 2 (organizational control report):\n{org_report}"
            )
        }]
    )
    return response.content[0].text

if __name__ == "__main__":
    vendor_text = extract_text("inputs/vendor-assurance-report.pdf")
    org_text = extract_text("inputs/org-control-report.pdf")
    result = crosscheck_cuecs(vendor_text, org_text)
    print(result)
```

**Tech stack used:** Python 3.11, Claude API (claude-sonnet-4-6), pdfplumber, anthropic SDK

**Intended file location:** `tools/scripts/cuec_crosscheck.py`

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| ISAE 3402 / ISAE 3000 | Section on Complementary User Entity Controls |
| SOC 2 | User Control Considerations (CC section) |
| ISO 27001:2022 | Annex A — controls that commonly satisfy CUECs (e.g. A.8.2 access management, A.8.32 change management) |

### Claude / AI tool usage notes

No real audit evidence or personal data will be sent to the API during development. Testing uses synthetic or anonymised report extracts only. In production, users should be advised to anonymise or redact sensitive content (client names, personal data, financial figures) before uploading.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] Python scripts run only from `tools/scripts/`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown table + CSV; gap findings as JSON

**Schema reference:** `outputs/schemas/finding-schema.json` (for unmatched CUECs flagged as gaps)

### Synthetic example output

| CUEC (vendor report) | Matching control (organizational report) |
|---|---|
| UEC-01 — The user organization shall ensure that access to the service is restricted to authorized personnel and that access rights are reviewed periodically. | Control IT-AC-04 (section 4.2, p. 18): "Access rights to third-party systems are reviewed quarterly by the IT owner. Last review: Q3 2025." — Direct match: periodic access review satisfies this CUEC. |
| UEC-02 — The user organization is responsible for notifying the service provider promptly when an employee is terminated or changes role. | Control HR-OFF-02 (section 6.1, p. 31): "Upon offboarding, IT receives notification within 24 hours to revoke all system access including third-party tools." — Direct match: offboarding procedure covers timely notification obligation. |
| UEC-03 — The user organization shall maintain and test a business continuity plan that covers reliance on services provided under this agreement. | No match found — gap. No BCP control referencing third-party service dependencies was identified in the organizational report. |

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API / Claude Desktop
- [x] Python 3.9+
- [x] GitHub (fork + PR)
- [ ] Strapi (synthetic data API — optional)
- [x] Other: pdfplumber (PDF text extraction)

**Stretch goals:**

- [ ] Support for multiple vendor reports in a single run (one organizational report matched against N vendor CUECs)
- [ ] Streamlit web UI for non-technical auditors to upload both reports and view the results
- [ ] Confidence scoring per match (high / medium / low) with flagging for manual review
- [ ] Auto-generation of a gap remediation action list from unmatched CUECs

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- System prompt (`prompts/audit-use-cases/cuec-crosscheck.md`)
- Python dual-document ingestion and matching script (`tools/scripts/cuec_crosscheck.py`)
- Synthetic test extracts (vendor CUEC section + organizational control list) for community validation

**What help I'm looking for:**

- Example or publicly available ISAE 3402 or SOC 2 reports containing a CUEC section for testing
- Reviewers familiar with third-party risk management practices to validate matching logic
- Input on how to handle partial matches and confidence scoring

**Cross-org interest:**

Any organization that receives ISAE 3402 or SOC 2 reports from vendors faces the same CUEC challenge. This agent is source-format agnostic on the organizational side — it works whether the organization's own controls are documented in an ISAE 3402, an ISO 27001 SoA, a SOC 2, or an internal testing report. Shared adoption across SAAF organizations would benefit from a common library of CUEC patterns.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Template filled in at Hackathon 2 |
| **Do** | In progress | Prototype script and prompt drafted at hackathon |
| **Check** | Not started | Planned for internal validation with anonymised vendor and organizational reports |
| **Act** | Not started | Target: Hackathon 3 |

---

## 12. Open Questions

1. CUECs can appear in two places in a SOC 2 report: a dedicated subsection and embedded within individual control activities. What is the best strategy to reliably extract both locations?
2. How should the agent handle a CUEC that is only partially satisfied by an organizational control — should it flag as a partial match or a gap?
3. Is there interest from other SAAF organizations in building a shared library of common CUECs and their typical organizational control responses?
