# Traceability review (SAAF "Trace" principle)

Team RAG TAG, SAAF Security Challenge, 10 Nov 2026. Read-only code review: no code was run and no files in the repos were changed. Our own Four Eyes additions were not counted. For Executive-Summary-Writer and FieldworkOrchestration we judged the committed (original) code.

Question per agent: if something goes wrong, can an auditor tell what the agent did?

Criteria: 1 Inputs, 2 Prompts, 3 Model, 4 Outputs, 5 Path, 6 Human decisions, 7 Run identity, 8 Tamper-evident, 9 Re-performable, 10 Safe logging.
Y = Yes, P = Partly, N = No, - = not applicable (no model call). Strong = 8 or more Yes.

Five agents were not reviewed because we ran out of time: Audit-criteria, OWASP-AI-Testing-Agent, agent-drift-rater, threewaysecurity, SAAF-circuit-breaker. Quick searches show that all five contain logging code (run_logger.py, chain_log.py, audit_log.py, run_log.py, audit_logger.py, ledger/merkle.py), so they may score well. They should be reviewed next.

## Matrix

| Agent | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Executive-Summary-Writer | P | P | P | Y | P | P | P | N | Y | P | Partial |
| Compliance-Audit-Agent | P | P | N | P | P | N | P | N | P | P | Partial |
| Finding-analysis | P | N | N | N | N | N | P | N | N | P | Weak |
| FieldworkOrchestration | P | Y | Y | Y | P | P | Y | N | P | Y | Partial |
| three-way-match-audit | P | - | - | - | P | N | N | N | P | Y | Weak |
| Vendor_Guard | P | N | N | N | P | N | P | N | N | Y | Partial |
| GDPR-AI-Audit-Agent | P | - | - | P | P | P | P | Y | P | Y | Partial |
| CUEC_Crosscheck | P | P | Y | Y | Y | N | P | N | P | P | Partial |
| Compliance-Report-Generator | Y | P | Y | Y | P | N | Y | N | P | Y | Partial |
| Policy-to-Controls-Extractor | P | N | N | P | P | N | N | N | N | P | Weak |
| Track-2-Evidence-Collection-Extraction | P | N | Y | P | P | P | P | N | P | Y | Partial |
| Track-2---IAM-final | P | N | P | N | P | N | P | N | N | P | Weak |
| PBC-Assistant-Isabelle---IA-AI-Hackathon | P | N | P | P | N | P | N | N | N | P | Weak |
| ExecGRC | P | - | P | Y | Y | P | Y | Y | Y | Y | Partial |
| Track-4-Audit-Report-Generator | N | N | N | N | N | N | N | N | N | Y | Weak |
| RCM-Builder | P | - | - | Y | P | N | P | N | Y | Y | Partial |
| Audit-Work-Program-Agent-UC-8- | P | Y | Y | Y | P | N | P | N | P | Y | Partial |
| Audit-criteria | not reviewed | | | | | | | | | | |
| hallucination-detection-agent | P | N | P | P | P | N | P | N | N | Y | Weak |
| judging-found-controls | P | N | N | P | P | N | N | N | N | Y | Weak |
| OWASP-AI-Testing-Agent | not reviewed | | | | | | | | | | |
| OWASP-top-10-LLM-assessment | Y | P | P | Y | P | N | P | P | P | Y | Partial |
| llm_owasp | P | N | N | N | N | N | P | N | N | Y | Weak |
| agent-rogue-risk-assessor | Y | P | P | P | P | P | P | N | Y | Y | Partial |
| agent-drift-rater | not reviewed | | | | | | | | | | |
| Agent-Auditor | Y | P | Y | P | P | P | P | P | P | P | Partial |
| joiners-movers-leavers-agent | Y | P | Y | Y | Y | P | Y | P | Y | Y | Partial (close to Strong) |
| threewaysecurity | not reviewed | | | | | | | | | | |
| Team-HighTable | P | N | P | N | P | N | N | N | N | Y | Weak |
| SAAF-circuit-breaker | not reviewed | | | | | | | | | | |

Totals for the 25 agents reviewed: Strong 0, Partial 15, Weak 10.

A "Y" on safe logging for an agent that logs almost nothing (for example Track-4) only means nothing unsafe is written. It is not praise.

## Verdict and one-line summary per agent

- **Executive-Summary-Writer (Partial).** The command-line run saves a replayable record of every model call and every manager reply, but the web version saves nothing, and the record leaves out the system prompt, the input file hashes and the error that stopped a run. Evidence: scripts/run_record.py:55-134; scripts/run.py:177-185 and 204-235 (committed version); frontend/agent-service/app.py:128.
- **Compliance-Audit-Agent (Partial).** The README promises a per-step record and an offline replay, but the code that writes the record is not in the repo, so an auditor cannot check it. Evidence: README.md:75-77; .gitignore excludes scripts/*.py; orchestration.py:59.
- **Finding-analysis (Weak).** Only the uploaded files and the final report are kept; nothing shows what the model was asked or what it answered. Evidence: agent/audit_agent.py:39-45, 73, 100-103.
- **FieldworkOrchestration (Partial).** This is the best per-call record we saw: prompt, model, settings, raw reply, reasoning and tokens under a run id, with approvals in a separate log. But the log can be edited without detection, and failed calls and image inputs are not recorded. Evidence: agents/audit_trail.py:42-45, 102-119, 185-194, 211-216; agents/claude_init.py:119-140, 229.
- **three-way-match-audit (Weak).** The result is shown on screen and then gone; nobody can later see which files or tolerances produced a MATCH. Evidence: webapp/app/main.py:73-145; webapp/app/services/matcher.py:108-121.
- **Vendor_Guard (Partial).** Each run has an id and keeps its input files and reports, but the step log lives only in memory, and prompts and model replies are not kept. Evidence: webui/server.py:83-110, 132-143; agents/llm.py:43-60.
- **GDPR-AI-Audit-Agent (Partial).** This agent makes no model call. It keeps a hash-chained log of what was masked and why, but the web app writes that log into a temporary folder that is deleted after each run. Evidence: src/gdpr_agent/audit_logger.py:55-95; app.py:128-132, 205-211.
- **CUEC_Crosscheck (Partial).** Each model call and its raw reply are logged well, but there is no run id and no input hashes, and the log can be edited unnoticed. Evidence: cuec_crosscheck.py:153-154, 173-205, 512-531.
- **Compliance-Report-Generator (Partial).** A run can be fully reconstructed from its record, but the record is off by default and is only written for runs that succeed. Evidence: saaf/core/audit_trail.py:102-119; saaf/core/agent.py:60-61, 107-136; cli.py:154-155.
- **Policy-to-Controls-Extractor (Weak).** The controls are saved, but not which model, prompt or segmentation fallback produced them, and a rerun overwrites the earlier output. Evidence: agent.py:105, 111-112; services/segments.py:63-70, 125.
- **Track-2-Evidence-Collection-Extraction (Partial).** A JSONL log keeps each verdict and the auditor's accept or override, but not who decided or when, and not the exact document and prompt. Evidence: compliance_qa.py:63-68, 90, 310-311, 391-397; compliance_qa_app.py:541-545, 562-565.
- **Track-2---IAM-final (Weak).** The team's own observability notes list what should be logged, but the code logs little beyond the console and keeps no prompts or replies. Evidence: tools/scripts/access_review_agent.py:34, 208-237, 268-270; observability_notes.md:25-27.
- **PBC-Assistant-Isabelle (Weak).** It stores the latest AI analysis per file, but status changes, edits and deletions leave no history, and earlier analyses are overwritten. Evidence: app.py:266-286, 372-382, 485-496.
- **ExecGRC (Partial, close to Strong).** By default it runs without a model. It keeps a hash-chained step log with the thresholds and rules applied, records failed runs, redacts environment variables, and writes a manifest with the SHA-256 of every output. The manager's context in the report has no author or time. Evidence: src/execsummary_grc/audit.py:23-61; cli.py:22-133, 167-186.
- **Track-4-Audit-Report-Generator (Weak).** It writes a full audit report and keeps nothing, so nobody can tell what the model was given or what it said. Evidence: app/main.py:40-118; app/services/claude_service.py:35-69.
- **RCM-Builder (Partial).** This agent makes no model call. Each risk shows its source, but the output does not say which input files were used or who approved the matrix. Evidence: tools/scripts/rcm_builder.py:1257-1263, 1384-1386.
- **Audit-Work-Program-Agent-UC-8- (Partial).** It keeps a good record of prompts and raw replies, but every run overwrites the previous log, and the input files are not identified. Evidence: work_program_generator.py:171-238, 805-808.
- **hallucination-detection-agent (Weak).** The log shows that a check ran and the risk it gave, but not the evidence or prompts behind the verdict. It can also name the wrong retrieval backend after a silent fallback. Evidence: hallucination/annotator.py:51-75.
- **judging-found-controls (Weak).** The verdicts file gives no model, prompt, policy file or time. Evidence: agent.py:24, 145, 164-175.
- **OWASP-top-10-LLM-assessment (Partial).** The reviewed code and the prompt are hashed well, but the web log does not keep the review itself and ignores write failures. Evidence: review_agent.py:132, 198-214; app.py:1105-1121.
- **llm_owasp (Weak).** The report cannot show which model ran or which code it actually read. Evidence: owasp_llm_audit/auditor.py:216-234; report.py:24-37.
- **agent-rogue-risk-assessor (Partial).** The deterministic score can be re-run from the commit, but the human overrides and the assistant's reasoning depend on a report the assistant fills in by hand. Evidence: skills/agent-rogue-risk-assessor/scripts/scan_repo.py:284-338.
- **Agent-Auditor (Partial).** Inputs are hashed and events are logged, but decisions carry no identity, the log can be edited without detection, and matching secret lines are copied into a cache file. Evidence: server/server.py:378-391, 465-477, 1235-1240, 1486-1493.
- **joiners-movers-leavers-agent (Partial, close to Strong).** An auditor can rebuild almost the whole run (input hashes, model input and raw output, which path was taken); only the sign-off is weakly tied to the content. Evidence: engine/sources.py:85-94; ai/claude_runner.py:173-247; web/app.py:112-116, 167-184.
- **Team-HighTable (Weak).** Nothing about a recommendation is kept once the browser closes. Evidence: backend/claude_client.py:126-128, 155-160.

## Patterns

- **Most agents keep the answer but not how it was reached.** Only FieldworkOrchestration, Audit-Work-Program, joiners-movers-leavers, CUEC_Crosscheck and Compliance-Report-Generator keep the raw model reply next to the prompt (or a prompt hash). Most others keep only the final report or parsed JSON.
- **Logs can almost always be edited without anyone noticing.** Only ExecGRC and GDPR-AI-Audit-Agent chain their entries, and neither chain is keyed or anchored outside the file, so someone who rewrites the whole file can recompute it. Several records are also overwritten by the next run (Audit-Work-Program, Policy-to-Controls, judging-found-controls) or thrown away (the GDPR temporary folder, Vendor_Guard's in-memory events).
- **Errors, retries and fallbacks are the least recorded part of the path.** They go to the console or memory, or are skipped entirely: FieldworkOrchestration records successful calls only, Compliance-Report-Generator records successful runs only, hallucination-detection records the configured backend rather than the one used, and Team-HighTable silently fills in missing scores.
- **Human decisions are recorded without a verified identity and are not bound to what was approved.** Examples are a typed name, a role picked from a dropdown, or a value taken from the request body (joiners-movers-leavers, Agent-Auditor, Track-2-Evidence, GDPR).
- **Input hashing is rare.** Only OWASP-top-10, Agent-Auditor, joiners-movers-leavers, agent-rogue-risk-assessor and ExecGRC hash what they read. Most others keep a file name at best.

## What good looks like (taken from the best agents reviewed)

- **One record per model call**, as in FieldworkOrchestration: run id, entry id, agent, system and user prompt, model, max_tokens and thinking settings, raw reply, reasoning, tokens, stop reason, start time and latency.
- **Inputs identified by SHA-256**, plus one fingerprint of all inputs, written into every output and sign-off, as in joiners-movers-leavers.
- **Every step recorded with the rule or threshold that drove it**, including a "run_failed" event, as in ExecGRC.
- **A hash chain on the log**, and at the end a manifest with the SHA-256 of every output and the final chain hash, as in ExecGRC. Store or sign the final hash somewhere the operator cannot change.
- **Human decisions in a separate append-only log**, linked to the entry they approve, as in FieldworkOrchestration. Each decision should carry the logged-in user, a time and a hash of the approved content.
- **An offline replay from the saved record**, as in Executive-Summary-Writer's --replay. Alternatively, record the model input and output so a deterministic engine can be re-run, as in joiners-movers-leavers.
- **Safe by default**: record company names redacted and endpoints without credentials (Compliance-Report-Generator), take an environment snapshot with secrets redacted (ExecGRC), send the model pseudonymised data only (joiners-movers-leavers), and put run folders in .gitignore with a warning that they hold engagement data (FieldworkOrchestration).

## Text aimed at AI assistants

Nothing hostile was found in the agents reviewed:
- Several repos contain CLAUDE.md files (for example Vendor_Guard, Policy-to-Controls-Extractor, Track-2---IAM-final, Audit-Work-Program, joiners-movers-leavers and Team-HighTable). These are normal developer guidance with no instructions to a reviewer.
- Policy-to-Controls-Extractor/AUDIT-CRITERIA.md:111 quotes a prompt-injection string as a test example.
- The SKILL.md in agent-rogue-risk-assessor is written for an AI assistant by design. Its run-time install step is already in our findings.
