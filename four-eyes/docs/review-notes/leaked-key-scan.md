# Secret scan of SAAF repo git history (RAG TAG, 10 Nov 2026)

Findings file: `findings/new-secrets.csv` (3 rows). All values below are masked (first 4 chars + length). No key was tested or used.

## Fetch
- 47 repos in `repos/`.
- 38 were shallow: all unshallowed OK with `fetch --unshallow` plus `+refs/heads/*:refs/remotes/origin/*` (gh credential helper passed per command, no global git config changed). 0 failures.
- 9 were already full clones with all branches (APM-Writer, Compliance-Audit-Agent, Executive-Summary-Writer, Finding-analysis, OWASP-AI-Testing-Agent, OWASP-top-10-LLM-assessment, SAAF-circuit-breaker, saaf-living-map, three-way-match-audit): not refetched.
- AuditRepAnalysis: remote is empty (0 commits), nothing to scan.
- No checkout, reset, commit or push. Working trees untouched (Executive-Summary-Writer and FieldworkOrchestration local changes left as they were).

## Scan
- 46 repos with history scanned (`git log -p --all`), every added line in every commit on every branch. 0 scan errors.
- Patterns: Anthropic, OpenAI, GitHub (classic and fine-grained), AWS, Slack, Google, ElevenLabs-style, private key blocks, quoted key/secret/password/token assignments. Extra sweeps: unquoted `.env` style `*_KEY/SECRET/TOKEN/PASSWORD=` lines, JWTs, Hugging Face, Groq, Stripe live, DB URLs with passwords, hardcoded Bearer tokens.

## Confirmed hits (in CSV)
| Repo | Type | Commit / date | File | In HEAD | Masked |
|---|---|---|---|---|---|
| Team-HighTable | Anthropic API key | 1294181 / 2026-03-10 | backend/.env | No (untracked in ea1d1ec) | sk-a...(108) |
| Team-HighTable | TeamMate API key | 1294181 / 2026-03-10 | backend/.env | No (untracked in ea1d1ec) | P6ja...(44) |
| ExecGRC | Anthropic API key | 22177ad / 2026-05-19 | .env.example | No (deleted in 5a80ff3) | sk-a...(108) |

Both Anthropic keys are real format (sk-ant-api03 prefix, 108 chars, high entropy) and are two different keys. All three are still reachable from main and origin/main, so anyone who can read the repo can recover them.

By type: Anthropic 2, TeamMate (generic API key) 1. GitHub, AWS, Slack, Google, ElevenLabs, OpenAI (real), private keys: 0.

## Rejected as false positives (checked by masked shape/context)
- OWASP-AI-Testing-Agent tests: `sk-a...` 25/29 chars, all lowercase letters, fake fixtures for redaction tests.
- Stress-test---standalone-criteria: `sk-a...(35)` in `tests/fixtures/proj_hardcoded/agent.py`, deliberate fixture for a hardcoded-key detector.
- SAAF-Project and Track-2---IAM-final: "risk-heat..." output file name, not a key.
- SAAF-Project: private key header only mentioned in a skill doc (no key material).
- OWASP-top-10-LLM-assessment and threewaysecurity: `API_KEY = "secr...(19)"`, word-based demo value with comment "LLM01 risk: secrets in code".
- Vendor_Guard: `__VG...__` template token, and `secrets.token_urlsafe(...)` code.
- saaf-portal, Team-HighTable `.env.example`, Finding-analysis: "generate..." / Dutch "change this" style placeholders.
- SAAF-circuit-breaker and Compliance-Report-Generator: USER:PASSWORD placeholder URL and a "hunter2" test URL.

## Notes
- Several repos contain "ignore previous instructions" strings (Compliance-Report-Generator, Executive-Summary-Writer, OWASP-AI-Testing-Agent, OWASP-top-10-LLM-assessment, Policy-to-Controls-Extractor, SAAF-Project, Track-2---IAM-final, Vendor_Guard, agent-drift-rater). All are prompt-injection test cases or methodology docs. Treated as data, nothing acted on.
- Merge-commit-only changes were not diffed separately (normal `git log -p` behaviour).
- Not checked: whether the keys are still active (testing them was out of scope).
