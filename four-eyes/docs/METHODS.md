# How we found the 74 findings (methods, scope, limits)

Team RAG TAG, SAAF Security Challenge, 10 November 2026.

## Scope

- **All repositories in the SAAF-Project organisation that were live before 13:30 on 10 Nov 2026:
  47 repos.** Three repos created that day were excluded, as the challenge rules require.
- State of the code as cloned on the afternoon of 10 Nov (latest version, then full history for the key search).

## Rules we kept

- Local copies only. No attacks on live systems; live SAAF sites were not tested.
- No real AI calls: we used no API key. Agents ran in their offline or test modes.
- No secret values copied anywhere. Key previews are masked (first 4 characters and the length).
- Each agent ran in its own isolated Python environment; nothing was installed system-wide.

## The eight methods

| # | Method | What we did | Result |
|---|--------|-------------|--------|
| 1 | **Reading the code** | A person read the code paths that build prompts, handle approvals and write outputs in the main agents. | Most of the high-risk findings. |
| 2 | **Red Pencil scan** | Our scanner (in this repo) checked 709 Python and template files across all 47 repos for 8 risky patterns. A person read every hit. | 21 hits, all real after removing one false alarm (fixed in the scanner). |
| 3 | **Risky-pattern search** | Searched Python, TypeScript, JavaScript and HTML for command execution, unsafe loading, TLS checks off, open servers and CORS, debug mode, GET routes that change data, paths or URLs taken from requests, spreadsheet formula injection, SQL building, raw HTML insertion and unpinned CDN scripts. | About 25 candidates read in detail, 12 confirmed. |
| 4 | **Running the agents** | 29 agents installed and run offline with their own tests, samples and dry-run modes, with small probes on edge cases (empty or missing data). | Which agents run, which fail, and "all fine when broken" behaviour. Details: `review-notes/agent-health-check-*.md`. |
| 5 | **Replaying attacks** | Automated tests on local copies that act as the bad actor: skip every review step, a model steered to read "no" as "yes", an anonymous approval in the senior auditor's name, a hand-written "approved" line, an answer edited after approval. | All succeeded on the original code (output saved in `demo/`), all blocked after the Four Eyes fix. |
| 6 | **Leaked-key search** | The full git history (every commit on every branch) of 46 repos (1 repo was empty) searched for API keys, tokens, passwords and private keys. Placeholders rejected by hand. | 3 real keys in 2 repos. Details (masked): `review-notes/leaked-key-scan.md`. |
| 7 | **Record-keeping review** | 25 agents checked against a 10-point audit-trail checklist: inputs, prompts, model, raw outputs, path taken, human decisions, run id, tamper evidence, replay, safe logging. | None complete; 15 partial, 10 weak. Scorecard: `review-notes/record-keeping-scorecard.md`. |
| 8 | **Reviewing our own guard** | An independent review of the Four Eyes code and both integrations before the demo. | Core logic sound; the must-fix items were fixed the same afternoon; the rest is listed under Limitations in the README. |

## What "verified" means in the findings file

- **verified: yes** (62 findings): a person read the code line, or a replayed attack proved it.
- **verified: no** (12 findings): found while running or probing an agent offline, but not re-checked
  line by line. Treat these as strong leads.

## What we did not cover

- **Real AI behaviour.** With no API key, we did not send poisoned documents to a real model. Prompt
  injection findings are about how documents reach the model, not about a model actually obeying them.
- **Dependency vulnerabilities.** No audit of package versions against known advisories.
- **Five agents' record-keeping** (Audit-criteria, OWASP-AI-Testing-Agent, agent-drift-rater,
  threewaysecurity, SAAF-circuit-breaker): not reviewed for lack of time; all five have logging code.
- **Web apps were read, not started.** No live testing of the servers.
- **Depth.** About 2 to 3 minutes per agent in the health check: a quick check, not a full audit.

## How we worked

Team RAG TAG used Claude Code with helper agents for scanning, running and first reads, and checked
the important claims by hand. The scanners and the guard were written during the afternoon and are
in this repo, so every step can be re-run.
