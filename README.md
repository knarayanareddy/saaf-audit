# SAAF Audit Repository

A consolidated monorepo containing source code and assets from all **64 SAAF-Project repositories**, organized into individual browseable directories for security audits, red-teaming, cross-repository compliance analysis, and reporting.

---

## Repository Index (64 Repositories)

| # | Repository Folder | Original Source | Description |
|---|-------------------|-----------------|-------------|
| 1 | [`saaf-org-dot-github/`](saaf-org-dot-github/) | [.github](https://github.com/SAAF-Project/.github) | Organisation-wide defaults for SAAF-Project: the security policy of Stichting SAAF |
| 2 | [`Agent-Auditor/`](Agent-Auditor/) | [Agent-Auditor](https://github.com/SAAF-Project/Agent-Auditor) | Hulpmiddel voor ontwikkelaars of QA/IT-auditors om SAAF AI-agents tegen het A2-raamwerk te beoordelen. |
| 3 | [`agent-drift-rater/`](agent-drift-rater/) | [agent-drift-rater](https://github.com/SAAF-Project/agent-drift-rater) | *(No description provided)* |
| 4 | [`agent-finder-agent-rule-inferrer/`](agent-finder-agent-rule-inferrer/) | [agent-finder-agent-rule-inferrer](https://github.com/SAAF-Project/agent-finder-agent-rule-inferrer) | make rules durable |
| 5 | [`agent-rogue-risk-assessor/`](agent-rogue-risk-assessor/) | [agent-rogue-risk-assessor](https://github.com/SAAF-Project/agent-rogue-risk-assessor) | IT-audit skill that scores how likely an AI agent is to go rogue (1-10). A heuristic scanner finds evidence for six red flags (self-edit, targets in context, prompt-only rules, falling escalations, softening, no log) and five controls, then fixes gaps on a new branch only with explicit consent. |
| 6 | [`agent-template/`](agent-template/) | [agent-template](https://github.com/SAAF-Project/agent-template) | Starter template for a SAAF agent: the nine quality standards already in place |
| 7 | [`AI-Digital-Resilience-Hero/`](AI-Digital-Resilience-Hero/) | [AI-Digital-Resilience-Hero](https://github.com/SAAF-Project/AI-Digital-Resilience-Hero) | This agent scans all repositories for AI Enabled Cyber Threats such as Prompt Injection |
| 8 | [`airlock/`](airlock/) | [airlock](https://github.com/SAAF-Project/airlock) | *(No description provided)* |
| 9 | [`APM-Writer/`](APM-Writer/) | [APM-Writer](https://github.com/SAAF-Project/APM-Writer) | Conversational agent that drafts sections of an Audit Planning Memorandum through a structured intake: scoping, document validation, clarification, writing (workflow skeleton) |
| 10 | [`Audit-criteria/`](Audit-criteria/) | [Audit-criteria](https://github.com/SAAF-Project/Audit-criteria) | AI agent that drafts and hardens AUDIT-CRITERIA.md for SAAF audit-agent repos: every acceptance criterion is executed, failures must be disclosed, and a human decides at a code-bounded soft block. Includes the Audit Planning Orchestrator (UC7→UC8→UC9) as its first verified target. |
| 11 | [`Audit-Work-Program-Agent-UC-8-/`](Audit-Work-Program-Agent-UC-8-/) | [Audit-Work-Program-Agent-UC-8-](https://github.com/SAAF-Project/Audit-Work-Program-Agent-UC-8-) | Create audit work program based on the delivered risk-control matrix from UC 7 |
| 12 | [`AuditRepAnalysis/`](AuditRepAnalysis/) | [AuditRepAnalysis](https://github.com/SAAF-Project/AuditRepAnalysis) | Analysis of previous audit reports to score relevance of findings to the current audit objective, include where necessary, and draft followup findings including risk score |
| 13 | [`Compliance-Audit-Agent/`](Compliance-Audit-Agent/) | [Compliance-Audit-Agent](https://github.com/SAAF-Project/Compliance-Audit-Agent) | Compliance audit agent: triages relevant internal policies for a regulatory clause, assesses compliance with Claude, and renders a Word report. Part of the SAAF Project (Hackathon 4). |
| 14 | [`Compliance-Report-Generator/`](Compliance-Report-Generator/) | [Compliance-Report-Generator](https://github.com/SAAF-Project/Compliance-Report-Generator) | It finds the relevant regulatory frameworks for a given financial entity |
| 15 | [`CUEC_Crosscheck/`](CUEC_Crosscheck/) | [CUEC_Crosscheck](https://github.com/SAAF-Project/CUEC_Crosscheck) | CUEC Crosscheck Agent — match vendor ISAE 3402 / SOC 2 CUECs to organizational controls. Part of the SAAF Project. |
| 16 | [`customs/`](customs/) | [customs](https://github.com/SAAF-Project/customs) | Offline CI check that inspects contributions to shared prompts, skills and agent settings |
| 17 | [`data-not-instructions/`](data-not-instructions/) | [data-not-instructions](https://github.com/SAAF-Project/data-not-instructions) | Reusable prompt-injection guard for SAAF agents: marks auditee documents as data, not instructions. Security Challenge #10, team rm -rf trust. |
| 18 | [`demo-repository/`](demo-repository/) | [demo-repository](https://github.com/SAAF-Project/demo-repository) | A code repository designed to show the best GitHub has to offer. |
| 19 | [`EU-AI-Act-DNB-Auditor/`](EU-AI-Act-DNB-Auditor/) | [EU-AI-Act-DNB-Auditor](https://github.com/SAAF-Project/EU-AI-Act-DNB-Auditor) | Audits AI systems in Dutch financial institutions against the EU AI Act and DNB SAFEST principles (plus GDPR Art. 22, DORA). SAAF Track 3a. |
| 20 | [`ExecGRC/`](ExecGRC/) | [ExecGRC](https://github.com/SAAF-Project/ExecGRC) | *(No description provided)* |
| 21 | [`Executive-Summary-Writer/`](Executive-Summary-Writer/) | [Executive-Summary-Writer](https://github.com/SAAF-Project/Executive-Summary-Writer) | Conversational agent that guides an audit manager through root cause, finding relationships, storyline and tone before writing the Executive Board summary (Claude API + LangGraph) |
| 22 | [`FieldworkOrchestration/`](FieldworkOrchestration/) | [FieldworkOrchestration](https://github.com/SAAF-Project/FieldworkOrchestration) | *(No description provided)* |
| 23 | [`Finding-analysis/`](Finding-analysis/) | [Finding-analysis](https://github.com/SAAF-Project/Finding-analysis) | The AuditRepAnalysis agent automates previous audit report reviews by analyzing historical findings and scoring their relevance to current audit objectives. It filters key issues for follow-up and drafts new findings with risk scores, saving time and removing subjectivity for auditors preparing for engagements. |
| 24 | [`four-eyes/`](four-eyes/) | [four-eyes](https://github.com/SAAF-Project/four-eyes) | Signed human sign-off for SAAF agents: nothing final is released without an approval of exactly that content. Includes a bypass test kit and the Red Pencil scanner. SAAF Security Challenge, team RAG TAG. |
| 25 | [`fraude-risicoanalyse-podcast/`](fraude-risicoanalyse-podcast/) | [fraude-risicoanalyse-podcast](https://github.com/SAAF-Project/fraude-risicoanalyse-podcast) | Fraude-risicoanalyse Zorggroep Waterlinie (fictieve casus): Risk Control Matrix, groepschat-artifact en tweetalige podcast-pijplijn op ElevenLabs |
| 26 | [`GDPR-AI-Audit-Agent/`](GDPR-AI-Audit-Agent/) | [GDPR-AI-Audit-Agent](https://github.com/SAAF-Project/GDPR-AI-Audit-Agent) | An automated compliance agent that audits AI systems for GDPR alignment, featuring PII data masking, automated DPIA generation, and real-time risk scoring. |
| 27 | [`hallucination-detection-agent/`](hallucination-detection-agent/) | [hallucination-detection-agent](https://github.com/SAAF-Project/hallucination-detection-agent) | Hallucination detection for AI-generated audit findings (SAAF Track 5) |
| 28 | [`IA-Fieldwork-Preparation/`](IA-Fieldwork-Preparation/) | [IA-Fieldwork-Preparation](https://github.com/SAAF-Project/IA-Fieldwork-Preparation) | AI-Powered Internal Audit Fieldwork Preparation tool |
| 29 | [`IA-Wingman-platform/`](IA-Wingman-platform/) | [IA-Wingman-platform](https://github.com/SAAF-Project/IA-Wingman-platform) | *(No description provided)* |
| 30 | [`joiners-movers-leavers-agent/`](joiners-movers-leavers-agent/) | [joiners-movers-leavers-agent](https://github.com/SAAF-Project/joiners-movers-leavers-agent) | Joiners-Movers-Leavers access audit agent: reconciles HR events, access rights and Jira access-request tickets, drafts findings with Claude Code behind a human review gate. Spin-off of Track-2---IAM-final. |
| 31 | [`judging-found-controls/`](judging-found-controls/) | [judging-found-controls](https://github.com/SAAF-Project/judging-found-controls) | Judges the found controls from a policy document to avoid hallucination. |
| 32 | [`llm_owasp/`](llm_owasp/) | [llm_owasp](https://github.com/SAAF-Project/llm_owasp) | *(No description provided)* |
| 33 | [`NoSilentPassGuard/`](NoSilentPassGuard/) | [NoSilentPassGuard](https://github.com/SAAF-Project/NoSilentPassGuard) | *None shall pass without proof.*  A small, deterministic guard for audit tooling that stops a bad actor (or plain bad input) from getting a green tick by staying silent. No LLM, no network, no runtime dependencies. The rule it enforces is called **No |
| 34 | [`OWASP-AI-Testing-Agent/`](OWASP-AI-Testing-Agent/) | [OWASP-AI-Testing-Agent](https://github.com/SAAF-Project/OWASP-AI-Testing-Agent) | Agent that operationalises the OWASP AI Testing Guide v1.0 for internal audit (plan stage) |
| 35 | [`OWASP-top-10-LLM-assessment/`](OWASP-top-10-LLM-assessment/) | [OWASP-top-10-LLM-assessment](https://github.com/SAAF-Project/OWASP-top-10-LLM-assessment) | Agent that assesses other agents if they comply with the OWASP top 10 risk on LLM applications |
| 36 | [`PBC-Assistant-Isabelle---IA-AI-Hackathon/`](PBC-Assistant-Isabelle---IA-AI-Hackathon/) | [PBC-Assistant-Isabelle---IA-AI-Hackathon](https://github.com/SAAF-Project/PBC-Assistant-Isabelle---IA-AI-Hackathon) | *(No description provided)* |
| 37 | [`Policy-to-Controls-Extractor/`](Policy-to-Controls-Extractor/) | [Policy-to-Controls-Extractor](https://github.com/SAAF-Project/Policy-to-Controls-Extractor) | *(No description provided)* |
| 38 | [`python-mcp-framework/`](python-mcp-framework/) | [python-mcp-framework](https://github.com/SAAF-Project/python-mcp-framework) | *(No description provided)* |
| 39 | [`RCM-Builder/`](RCM-Builder/) | [RCM-Builder](https://github.com/SAAF-Project/RCM-Builder) | RCM Builder |
| 40 | [`saaf-agent-scanner/`](saaf-agent-scanner/) | [saaf-agent-scanner](https://github.com/SAAF-Project/saaf-agent-scanner) | Read-only static scanner + Claude Code skill to find the security weaknesses seen across SAAF audit agents (SAAF Security Challenge, team ragtag) |
| 41 | [`SAAF-circuit-breaker/`](SAAF-circuit-breaker/) | [SAAF-circuit-breaker](https://github.com/SAAF-Project/SAAF-circuit-breaker) | SAAF Circuit Breaker: deterministic policy guards, drift detection, rollback and offline workpaper verification. |
| 42 | [`SAAF-community-playbook/`](SAAF-community-playbook/) | [SAAF-community-playbook](https://github.com/SAAF-Project/SAAF-community-playbook) | A field guide for starting SAAF-style hackathon programmes — inside your organisation, or as a regional chapter — and bringing the learnings back to the main SAAF Project. |
| 43 | [`saaf-customs/`](saaf-customs/) | [saaf-customs](https://github.com/SAAF-Project/saaf-customs) | Inspect skills, plugins, MCP servers and packages before you install them. |
| 44 | [`saaf-gatekeeper/`](saaf-gatekeeper/) | [saaf-gatekeeper](https://github.com/SAAF-Project/saaf-gatekeeper) | Blocks API keys in git history and committed .env files: pre-commit hook, CI check, repo sweep |
| 45 | [`saaf-guard/`](saaf-guard/) | [saaf-guard](https://github.com/SAAF-Project/saaf-guard) | *(No description provided)* |
| 46 | [`saaf-living-map/`](saaf-living-map/) | [saaf-living-map](https://github.com/SAAF-Project/saaf-living-map) | Living map of SAAF audit agents: a small agent.yaml manifest per repo, rendered automatically into one view. |
| 47 | [`saaf-portal/`](saaf-portal/) | [saaf-portal](https://github.com/SAAF-Project/saaf-portal) | SAAF Participant Portal — Next.js app for SAAF Project members |
| 48 | [`SAAF-Project/`](SAAF-Project/) | [SAAF-Project](https://github.com/SAAF-Project/SAAF-Project) | Repository for the SAAF Project |
| 49 | [`saaf-quarantine/`](saaf-quarantine/) | [saaf-quarantine](https://github.com/SAAF-Project/saaf-quarantine) | CI check and drop-in helper that keep auditee documents out of LLM prompts as instructions |
| 50 | [`saaf-tripwire/`](saaf-tripwire/) | [saaf-tripwire](https://github.com/SAAF-Project/saaf-tripwire) | *(No description provided)* |
| 51 | [`Stress-test---standalone-criteria/`](Stress-test---standalone-criteria/) | [Stress-test---standalone-criteria](https://github.com/SAAF-Project/Stress-test---standalone-criteria) | An agent to check if it can operate locally |
| 52 | [`Team-HighTable/`](Team-HighTable/) | [Team-HighTable](https://github.com/SAAF-Project/Team-HighTable) | *(No description provided)* |
| 53 | [`The-Control-Freaks/`](The-Control-Freaks/) | [The-Control-Freaks](https://github.com/SAAF-Project/The-Control-Freaks) | *(No description provided)* |
| 54 | [`three-way-match-audit/`](three-way-match-audit/) | [three-way-match-audit](https://github.com/SAAF-Project/three-way-match-audit) | P2P 3-way match audit report generator with data and reporting tools |
| 55 | [`threewaysecurity/`](threewaysecurity/) | [threewaysecurity](https://github.com/SAAF-Project/threewaysecurity) | Security project group |
| 56 | [`TipsAndTricks/`](TipsAndTricks/) | [TipsAndTricks](https://github.com/SAAF-Project/TipsAndTricks) | Tips and tricks |
| 57 | [`Track-1---Planning-en-Orientatie/`](Track-1---Planning-en-Orientatie/) | [Track-1---Planning-en-Orientatie](https://github.com/SAAF-Project/Track-1---Planning-en-Orientatie) | Track 1 - Planning en Orientatie |
| 58 | [`Track-2---IAM-final/`](Track-2---IAM-final/) | [Track-2---IAM-final](https://github.com/SAAF-Project/Track-2---IAM-final) | *(No description provided)* |
| 59 | [`Track-2-Evidence-Collection-Extraction/`](Track-2-Evidence-Collection-Extraction/) | [Track-2-Evidence-Collection-Extraction](https://github.com/SAAF-Project/Track-2-Evidence-Collection-Extraction) | SAAF AI Control Assessment — Track 2 Hackathon 4 MVP. Upload policy PDFs, ask one compliance question, receive a verdict with evidence, confidence reasoning and a GIAS v2024 8-step reasoning trail. |
| 60 | [`Track-4-Audit-Report-Generator/`](Track-4-Audit-Report-Generator/) | [Track-4-Audit-Report-Generator](https://github.com/SAAF-Project/Track-4-Audit-Report-Generator) | Group 8, Track 4: Audit Report Generator |
| 61 | [`UC3-incident-issue-intelligence/`](UC3-incident-issue-intelligence/) | [UC3-incident-issue-intelligence](https://github.com/SAAF-Project/UC3-incident-issue-intelligence) | *(No description provided)* |
| 62 | [`Vendor_Guard/`](Vendor_Guard/) | [Vendor_Guard](https://github.com/SAAF-Project/Vendor_Guard) | Thrird Party Risk Management Agent |
| 63 | [`website/`](website/) | [website](https://github.com/SAAF-Project/website) | Website repo for SAAF Project communications |
| 64 | [`WhatsTheNews/`](WhatsTheNews/) | [WhatsTheNews](https://github.com/SAAF-Project/WhatsTheNews) | Scours the internet to find news from trusted sources and gives you your personal summarized report with only the information that is relevant for you. |

---

## Structure
Each top-level directory corresponds to an individual SAAF-Project repository, stripped of nested `.git` trees so that all files and directories are directly navigable and inspectable in the GitHub UI.
