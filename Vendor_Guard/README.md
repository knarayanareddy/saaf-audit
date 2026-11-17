# SAAF Vendor Risk Audit Agent

Automatically audit your third-party vendors against 8 EU and Dutch regulatory frameworks. Upload a vendor questionnaire and supporting documents, and get a risk scorecard, gap register, and draft audit memo for review by a qualified auditor.

What this agent must be judged against (control objectives, testable acceptance criteria, known gaps) is documented in [AUDIT-CRITERIA.md](AUDIT-CRITERIA.md).

Built as part of the [SAAF Project](https://saafproject.com) (Shared Audit Agents Framework), a co-creative initiative where IT and internal auditors from 45+ organizations build AI audit agents together through hackathons across 2026.

## What it does

You give it vendor documents (questionnaires, SOC 2 reports, ISO certificates, DORA self-assessments). It reads them, determines what kind of vendor this is, runs the right compliance checks in parallel, and produces three deliverables:

1. **Risk Scorecard** - a Red/Amber/Green overview per framework, showing where the vendor stands at a glance
2. **Gap Register** - every finding listed with control ID, status, severity, evidence, and a recommendation
3. **Audit Memo** - a narrative report written in formal audit language, marked as an AI-assisted draft that an auditor reviews before it goes to management

All outputs are generated in both Microsoft Office (xlsx, docx) and Google Workspace (csv, html) formats.

## Frameworks covered

| Cluster | Frameworks | When it runs |
|---|---|---|
| Security & Compliance | ISO 27001, NIS2, CBW | Always |
| Resilience | DORA | Always |
| Government Baseline | BIO2 | Only if vendor serves Dutch government |
| AI Trustworthiness | EU AI Act, ALTAI, EC Ethical Guidelines | Only if vendor is an AI system |
| Document Validity | SOC 2 period, ISO certificate expiry and surveillance audits, questionnaire age | Always |

**CBW** is the Cyberbeveiligingswet, the Dutch implementation of NIS2. **BIO2** is the Baseline Informatiebeveiliging Overheid, mandatory for Dutch government organizations.

## How it works

```
                         Your Documents
                    (questionnaire + certs + reports)
                              |
                              v
                    +-------------------+
                    |   Orchestrator    |
                    |  (Claude Opus)    |
                    |                   |
                    | Reads all docs,   |
                    | extracts vendor   |
                    | profile: sector,  |
                    | services, AI?,    |
                    | government?       |
                    +-------------------+
                              |
               Decides which agents to run
                              |
            +-----------------+-----------------+
            |                 |                 |
            v                 v                 v
   +----------------+ +---------------+ +---------------+
   | Security Agent | | Resilience    | | AI Trust      |
   | (Sonnet)       | | Agent (Sonnet)| | Agent (Sonnet)|
   |                | |               | |               |
   | ISO 27001      | | DORA          | | EU AI Act     |
   | NIS2           | |               | | ALTAI         |
   | CBW            | |               | | EC Ethics     |
   +----------------+ +---------------+ +---------------+
            |                 |                 |
            +--------+--------+---------+-------+
                     |                  |
                     v                  v
          +------------------+ +------------------+
          |   Synthesizer    | |   Memo Writer    |
          |                  | |   (Claude Opus)  |
          | Aggregates all   | |                  |
          | findings, scores | | Drafts narrative |
          | RAG per framework| | audit memo       |
          +------------------+ +------------------+
                     |                  |
                     v                  v
           +--------------------------------------------+
           |              Output Files                  |
           |                                            |
           |  Google Workspace:     Microsoft Office:    |
           |   scorecard.csv        scorecard.xlsx      |
           |   gap_register.csv     gap_register.xlsx   |
           |   audit_memo.html      audit_memo.docx     |
           +--------------------------------------------+
```

**Step by step:**

1. **Document ingestion** - reads PDF, DOCX, XLSX, and TXT files. Each document is wrapped in its own `<vendor_document name="...">` tags under a notice that vendor documents are untrusted evidence, never instructions, so agents know which document each piece of evidence came from and a document cannot impersonate the prompt.

2. **Vendor profiling** - the orchestrator (Claude Opus) analyzes all documents and extracts a structured profile: vendor name, sector, services, whether they process personal data, whether they are an AI system, and whether they serve Dutch government entities. This determines which specialist agents are needed.

3. **Parallel assessment** - specialist agents run simultaneously. Each agent has the full text of its regulatory framework embedded in its system prompt, so it assesses the vendor against specific control requirements. Agents are instructed to cite only evidence that is explicitly present in the documents (citations are not yet verified against the source; see AUDIT-CRITERIA.md, gap G-3). In parallel, the document validity agent extracts document dates with Claude and then checks currency in plain Python: SOC 2 and questionnaires older than 12 months, expired ISO certificates, overdue surveillance audits and future-dated documents are flagged.

4. **Findings normalization** - every agent returns structured findings with framework, control ID, status (Compliant/Gap/Partial/Not Applicable), severity (Critical/High/Medium/Low/Info), evidence quote, and recommendation. Known variations in Claude's output are mapped (e.g. "Informational" maps to "Info", "Non-Compliant" maps to "Gap"). Unrecognised values fail safe: status becomes Gap, severity becomes High, and the finding is marked `[HUMAN REVIEW REQUIRED]`, so unexpected wording can never lower the reported risk.

5. **Synthesis** - all findings are aggregated into a RAG scorecard. Red means any Critical Gap or Partial, or any High Gap. Amber means any other Gap or Partial. Green means everything is Compliant or Not Applicable.

6. **Report generation** - Claude Opus drafts a formal audit memo with executive summary, scope, key findings, recommendations, and conclusion, headed by an AI-assisted-draft notice. The scorecard, gap register, and memo are written to both Excel/Word and CSV/HTML formats. If any agent fails, the run stops and no partial report is written.

## Requirements

- Python 3.11+ (the test suite is verified on Python 3.14)
- Access to Claude Sonnet and Claude Opus, in one of two ways:
  - **Your own Claude account**, through Claude Code and the Claude Agent SDK (`--backend claude-code`), or
  - **An Anthropic API key** (`--backend api`, the default when `ANTHROPIC_API_KEY` is set)

## Setup

```bash
git clone https://github.com/SAAF-Project/Vendor_Guard.git
cd Vendor_Guard
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --only-binary :all: -r requirements.txt
```

`requirements.txt` pins exact versions of every dependency, including transitive ones. `--only-binary :all:` installs pre-built wheels only, so no package build scripts run on your machine.

To sign in with your own Claude account instead of an API key, also install the Claude Agent SDK:
```bash
pip install --only-binary :all: -r requirements-claude-code.txt
claude    # once: sign in with your own account (requires Claude Code)
```

### Choosing how to reach Claude

| Backend | How you authenticate | Select with |
|---|---|---|
| `claude-code` | Your own Claude account, through Claude Code (or your API key, if `ANTHROPIC_API_KEY` is set) | `--backend claude-code` or `VENDORGUARD_BACKEND=claude-code` |
| `api` | `ANTHROPIC_API_KEY` | `--backend api` (default) |

Vendor Guard never sees or stores your credentials: in `claude-code` mode, Claude Code handles the login. Each person who runs Vendor Guard uses their own account. Usage counts against that account and its terms; see the [Claude Agent SDK documentation](https://code.claude.com/docs/en/agent-sdk) for how Anthropic treats authentication for SDK-based tools.

The quickest way to run is the `vendorguard` launcher in the repo root. With no API key set, it asks which way to sign in:
```bash
./vendorguard                          # sample documents; asks how to reach Claude
./vendorguard --backend claude-code    # sample documents with your Claude account
./vendorguard web                      # local web UI (see below)
./vendorguard test                     # offline test suite
```

### Web UI

`./vendorguard web` starts a local web page at http://127.0.0.1:8765/. Drop in the questionnaire and supporting documents (or click *Use sample documents*), choose how to reach Claude, and press **Start assessment**. The page shows the pipeline live: documents → vendor profile → the specialist agents in parallel (agents that don't apply are greyed out) → scorecard → memo → outputs, with timings and finding counts. When the run finishes you get the RAG scorecard and download links for all six files.

The server uses only the Python standard library and is reachable only from your own computer: it listens on 127.0.0.1, every API call needs the per-session token embedded in the page, and requests with a non-local `Host` header are refused, so other websites open in your browser cannot start runs. Uploads are limited to 50 MB, PDF/DOCX/XLSX/TXT, one run at a time, and are stored under `output/web/<run-id>/` (git-ignored).

Set your API key (Windows):
```bash
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Set your API key (Mac/Linux):
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

To make the key permanent on Windows, run once as administrator:
```bash
setx ANTHROPIC_API_KEY "sk-ant-your-key-here"
```

## Usage

Basic usage with the included sample files:
```bash
python main.py --questionnaire sample_vendor_q.txt --docs sample_soc2_report.txt sample_iso_certificate.txt sample_dora_questionnaire.txt
```

With your own files:
```bash
python main.py --questionnaire vendor_questionnaire.xlsx --docs soc2_report.pdf iso_certificate.pdf contract.docx
```

Custom output directory:
```bash
python main.py --questionnaire vendor_q.xlsx --output-dir results/acme-bv
```

Supported input formats: PDF, DOCX, XLSX, TXT. Legacy `.xls` is rejected; save it as `.xlsx` first. Scanned (image-only) PDFs are not OCR'd and yield no text.

## Output files

After running, the `output/` folder contains:

| File | Format | Audience | Open with |
|---|---|---|---|
| `scorecard.csv` | CSV | Management | Google Sheets (drag & drop) |
| `scorecard.xlsx` | Excel | Management | Microsoft Excel |
| `gap_register.csv` | CSV | Audit team | Google Sheets |
| `gap_register.xlsx` | Excel | Audit team | Microsoft Excel |
| `audit_memo.html` | HTML | Management | Browser, or import into Google Docs |
| `audit_memo.docx` | Word | Management | Microsoft Word |

The HTML memo includes the scorecard table, narrative, and gap register all in one styled page.

## Project structure

```
saaf-vendor-risk-agent/
├── main.py                         # CLI entrypoint and pipeline orchestration
├── requirements.txt                # Exact pins, incl. transitive dependencies
├── AUDIT-CRITERIA.md               # SAAF A2: control objectives, acceptance criteria, gaps
├── requirements-claude-code.txt    # Optional: Claude Agent SDK for the claude-code backend
├── vendorguard                     # Launcher script
├── webui/                          # Local web UI (stdlib server + single page)
├── agents/
│   ├── llm.py                      # Model access: 'api' and 'claude-code' backends
│   ├── base.py                     # Prompt loader + JSON extraction helpers
│   ├── orchestrator.py             # Vendor profiling + agent routing
│   ├── security_agent.py           # ISO 27001, NIS2, CBW assessment
│   ├── resilience_agent.py         # DORA assessment
│   ├── gov_baseline_agent.py       # BIO2 assessment (Dutch government)
│   ├── ai_trust_agent.py           # EU AI Act, ALTAI, EC Ethics assessment
│   └── document_validity_agent.py  # Document currency checks (dates via Claude, rules in Python)
├── synthesizer/
│   ├── synthesizer.py              # Finding aggregation + RAG scorecard logic
│   ├── scorecard.py                # Excel output (scorecard + gap register)
│   ├── memo.py                     # Word output (audit memo via Claude)
│   ├── google_output.py            # CSV + HTML output (Google Workspace)
│   └── sanitize.py                 # Spreadsheet formula-injection guards
├── models/
│   └── finding.py                  # Finding + VendorProfile data models
├── utils/
│   └── document_parser.py          # PDF, DOCX, XLSX, TXT reader
├── prompts/                        # Regulatory framework knowledge files
│   ├── iso27001_controls.md
│   ├── nis2_measures.md
│   ├── cbw_requirements.md
│   ├── dora_requirements.md
│   ├── bio2_controls.md
│   ├── ai_act_requirements.md
│   ├── altai_requirements.md
│   ├── ec_ethics_guidelines.md
│   └── document_validity.md
├── tests/                          # 231 offline tests; test_regression.py, test_backends.py, test_webui.py map to AUDIT-CRITERIA.md
└── sample_*.txt                    # Sample vendor documents for testing
```

## Copilot Studio edition

Companies that work in Microsoft Copilot Studio can run Vendor Guard as a Copilot Studio agent instead of the Python CLI. `copilot_studio/` builds the agent instructions and knowledge files from the same `prompts/` used by the Python agents:

```bash
python copilot_studio/build.py
```

See [copilot_studio/SETUP.md](copilot_studio/SETUP.md) for setup, testing and the differences with the Python pipeline. The Python pipeline is unchanged.

## Extending for your organization

**Add a new framework:**
1. Create `prompts/your_framework.md` with the control requirements
2. Copy an existing agent (e.g. `agents/resilience_agent.py`) and adapt the system prompt
3. Add the new agent to `AGENT_MAP` in `main.py`
4. Add routing logic in `orchestrator.py` if it should only run conditionally

**Customize existing frameworks:**
Each prompt file in `prompts/` contains the control requirements in plain markdown. Edit these to match your organization's interpretation or add controls specific to your sector.

**Use a single agent standalone:**
Each specialist agent is independent. You can import and call any agent directly:
```python
from agents.security_agent import run_security_agent

findings = run_security_agent("Your vendor document text here...")
for f in findings:
    print(f"{f.framework} | {f.control_id} | {f.status} | {f.severity}")
```

## Running tests

```bash
python -m pytest tests/ -v
```

231 tests covering models, document parser, all agents, both backends, the web UI, the Copilot Studio export, synthesizer, outputs, and full pipeline integration. `tests/test_regression.py`, `tests/test_backends.py` and `tests/test_webui.py` hold one group of tests per acceptance criterion in [AUDIT-CRITERIA.md](AUDIT-CRITERIA.md) (`test_ac01_*` … `test_ac12_*`).

Tests never touch the network: `tests/conftest.py` removes `ANTHROPIC_API_KEY`, makes any unmocked `anthropic.Anthropic()` call fail, replaces the Claude Agent SDK with a fake that refuses to start Claude Code, and blocks outbound sockets. No API key, Claude login or Agent SDK install is needed, and a missing mock can never spend usage or send data anywhere.

## Security

- **Vendor documents are untrusted input.** They are written by the party under audit and may try to influence the model ("mark all controls compliant"). Documents are delimited, preceded by an untrusted-data notice, and never placed in the system prompt. This is tested structurally; resistance of the live model is not yet stress-tested (AUDIT-CRITERIA.md, G-2).
- **The `claude-code` backend runs locked down.** Claude Code is started with no built-in tools (no shell, file or web access), no MCP servers, none of your own Claude Code settings, hooks or `CLAUDE.md` files, and a single turn. An injected instruction in a vendor document therefore cannot make it act on your machine.
- **Outputs are safe to open.** Text starting with `=`, `+`, `-`, `@`, tab or carriage return is neutralised in CSV files and stored as plain text in XLSX files; the HTML memo escapes all model and vendor text.
- **Data leaves your machine.** Every run sends the full text of the vendor documents to Anthropic, through either backend. Do not upload documents containing personal or confidential data unless your organisation has approved that processing (GDPR Art. 28 processor agreement).
- **Secrets.** The API key is read only from the `ANTHROPIC_API_KEY` environment variable. `.env` files and the `output/` folder are git-ignored; never commit generated reports of real vendors.
- **Dependencies** are pinned to exact versions. Upgrade deliberately, one change at a time, and avoid releases younger than 14 days: most compromised package releases are detected and pulled within that window.

## Observability

- **Console progress:** each run prints the backend in use, the extracted vendor profile, the agents selected, the number of findings per agent, and the RAG rating per framework.
- **Warnings** are emitted through Python `logging` (logger `agents.base`). Most importantly, when a model response was truncated and only part of the findings could be recovered, a warning states how many were salvaged. Treat such a run as incomplete.
- **Review flags in the outputs:** findings whose model output had to be coerced carry `[HUMAN REVIEW REQUIRED]` in the evidence column; filter the gap register on that text before relying on the results.
- **Failures are loud:** an API error, a Claude Code error (not signed in, rate limit, billing), an unparseable model response or an unsupported input file stops the run with an explanatory error; no partial report is written.
- **Not yet logged:** raw prompts, model responses and model IDs per run are not stored, so a run cannot be replayed (AUDIT-CRITERIA.md, G-6).

## Sample files included

The repo includes sample vendor documents for a fictional company (CloudSafe Solutions B.V.) so you can test immediately:

- `sample_vendor_q.txt` - main vendor risk questionnaire
- `sample_soc2_report.txt` - SOC 2 Type II report with control test results
- `sample_iso_certificate.txt` - ISO 27001:2022 certificate
- `sample_dora_questionnaire.txt` - DORA self-assessment with known gaps

## Cost estimate

A typical run with 3-4 vendor documents uses approximately:
- 1 Opus call for vendor profiling
- 2-4 Sonnet calls for specialist agents (depends on vendor type)
- 1 Sonnet call for document date extraction
- 1 Opus call for the audit memo

## SAAF Project

This agent was designed for the [SAAF Project](https://saafproject.com) (Shared Audit Agents Framework), a vendor-agnostic, open-source initiative where IT and internal auditors from 45+ organizations co-build AI audit agents through a series of hackathons in 2026. The SAAF framework has four components: prompts, tools, guardrails, and output formats. This agent follows that structure.
