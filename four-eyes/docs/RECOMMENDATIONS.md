# What to fix, and in what order

Team RAG TAG, SAAF Security Challenge, 10 November 2026. Every finding has its own fix in
`findings/RAG-TAG-findings.csv` and `findings/FINDINGS-REPORT.md`. This page puts them in order and
turns them into one standard every SAAF agent can follow.

## 1. Today

1. **Revoke the three leaked keys.** Team-HighTable (an Anthropic key and a TeamMate key in
   `backend/.env`, commit 1294181) and ExecGRC (an Anthropic key in `.env.example`, commit 22177ad).
   Deleting the file did not remove them: they are still in git history. Treat them as burned.
2. **Turn on secret scanning with push protection** for the SAAF-Project organisation, so a key
   cannot be committed again.
3. **SAAF-circuit-breaker:** stop `GET /api/seed` from deleting all workpapers (make it a POST that
   needs a login, or remove it).
4. **OWASP-top-10-LLM-assessment** (and its copy in SAAF-Project): stop `/owasp-update` from
   replacing the review rules from any URL, and stop listening on `0.0.0.0`.

## 2. This week

1. **Review and merge the two fixes:** [Executive-Summary-Writer#4](https://github.com/SAAF-Project/Executive-Summary-Writer/pull/4)
   and [FieldworkOrchestration#5](https://github.com/SAAF-Project/FieldworkOrchestration/pull/5).
2. **Fix the High findings** listed in the findings file (21), starting with the agents that produce
   final deliverables: reports, summaries, work programs, verdicts.
3. **Add a CI check to every agent repo:** its own tests, Red Pencil (`examples/red-pencil.yml`) and a
   secret scan of the history.

## 3. A minimum standard for every SAAF agent

Six controls. Each one closes a group of today's findings. Write them into each agent's `agent.yaml`
mandate and `AUDIT-CRITERIA.md`, and check them in CI.

| # | Control | What it means in practice | Closes |
|---|---------|---------------------------|--------|
| 1 | **Sign-off is a lock, not a sentence** | Final deliverables are released only through a signed approval of exactly that content, by a logged-in person. Add the Four Eyes bypass test kit to the agent's tests. | "Approvals nobody really gave" (7) |
| 2 | **A record of every run** | Keep, per run: inputs with a hash, prompts sent, model and settings, raw answers, path taken (retries, fallbacks, errors), human decisions, a run id. Append-only and signed, kept with the workpaper. | "Can the agent prove what it did?" (25) |
| 3 | **When in doubt, stop** | Missing data, an empty or unparsed AI answer, a cut-off output or an unknown status gives "Incomplete" or Red, never Green or MATCH. Never throw away the AI's own warnings. | "All fine when it broke" (11) |
| 4 | **Documents are evidence, not instructions** | Wrap each document in a random boundary per run, escape it, and tell the model that document text is never an instruction. Check quotes against the source. Never label model output "authoritative". | "Documents that can give the AI orders" (6) |
| 5 | **Secrets and personal data stay put** | Keys only from environment variables or a secret store: never in pages, logs, config files or examples. Redact outputs and traces. Mask personal data by content, not by field name. | "Secrets exposed" (2), "Keys in history" (3) |
| 6 | **Web tools are closed by default** | Listen on 127.0.0.1, no debug mode, no `CORS *`, a login on anything that changes data, no data changes on GET, check URLs and file paths from requests, escape output, guard spreadsheet cells. | "Web apps open too wide" (15), "Other risky code" (5) |

## How the pieces fit

- **SAAF Guard** (built by another team today) checks the code for risky patterns.
- **Data, Not Instructions** (another team), going by its name, guards what goes into the AI.
- **Four Eyes** (this repo) protects what comes out: nothing leaves without a named person approving
  that exact content, and every approval is on a record an auditor can check.

They are layers: use them together.
