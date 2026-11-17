# Vendor Guard in Copilot Studio

Runs the Vendor Guard audit as a Copilot Studio agent. No Python, API key or Azure resources are needed at the customer. The Python pipeline in the repo root is unchanged and remains the reference implementation.

## 1. Build the package

```bash
python copilot_studio/build.py
```

This creates `copilot_studio/dist/` with:
- `agent_instructions.md` (paste into the agent's Instructions field)
- `knowledge/` (upload as knowledge sources): 8 framework files copied from `prompts/` plus `document_validity_rules.md`

## 2. Create the agent

1. In Copilot Studio create a new agent named **Vendor Guard**.
2. Paste `dist/agent_instructions.md` into **Instructions**.
3. Under **Knowledge**, upload every file in `dist/knowledge/`.
4. Enable file upload so users can attach vendor documents in the chat.
5. Turn off web search / general knowledge so answers only rely on the knowledge files and the uploaded documents.
6. Publish and share with the audit team.

Menu names and settings in Copilot Studio change over time. These steps describe the intent; check them against the current Copilot Studio documentation, including file size and knowledge-source limits.

## 3. Test before real use

Use the sample files in the repo root (CloudSafe Solutions B.V.): `sample_vendor_q.txt`, `sample_soc2_report.txt`, `sample_iso_certificate.txt`, `sample_dora_questionnaire.txt`. Compare the result with the Python pipeline:

```bash
python main.py --questionnaire sample_vendor_q.txt --docs sample_soc2_report.txt sample_iso_certificate.txt sample_dora_questionnaire.txt
```

Check at minimum: the same frameworks were selected, RAG colours match, the Document Validity dates and day counts are correct, and every finding quotes evidence from a real document, and every control in the knowledge files was assessed (not only a subset). If controls are skipped, tell the agent in the instructions to walk through the knowledge file control by control.

## Differences from the Python pipeline

| Topic | Python pipeline | Copilot Studio agent |
|---|---|---|
| Execution | Parallel specialist agents | One agent, frameworks assessed one by one |
| RAG score and date checks | Computed by code | Computed by the model from instructions (verify counts) |
| Output | xlsx, docx, csv, html files | Chat tables and memo text |
| Framework coverage | Full framework text is placed in each agent prompt | Knowledge sources are searched, not read in full; the agent may skip controls |
| Model | Claude | Whatever the Copilot Studio tenant uses |

## Optional: file output

For Excel and Word files, add a Power Automate flow that takes the findings table from the agent and writes it to a template. Not included here.

## Keeping it in sync

The framework files are copied from `prompts/` by `build.py`. After editing a framework in `prompts/`, rebuild and re-upload `dist/knowledge/`. Never edit files in `dist/`.
