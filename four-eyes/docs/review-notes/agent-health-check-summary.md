# 08. How good are the SAAF agents? (review of 29 agents, 10 Nov)

Two helper agents ran and reviewed 29 SAAF agents offline (no API key, no real AI
calls), each in its own isolated install. Full tables: `agent-review-A.md` (13
agents) and `agent-review-B.md` (16 agents). I checked the biggest claims in the
code myself. Executive-Summary-Writer, Compliance-Audit-Agent and
FieldworkOrchestration were reviewed earlier (notes 05 and four-eyes).

## The short answer

Many SAAF agents run, and some are well built. But three weaknesses repeat across
almost all of them:

1. **"A person reviews this" is usually a sentence, not a lock.**
   Only **3 of 29** agents enforce a human sign-off in code
   (OWASP-AI-Testing-Agent, joiners-movers-leavers-agent, agent-drift-rater), and
   1 does it partly (Audit-criteria: a No-Go needs a person, a Go does not).
   This is exactly the gap our guard, Four Eyes, closes.
2. **When something goes wrong, many agents say "all fine".** Examples confirmed in
   the code: CUEC_Crosscheck reports Green when it has no results; the hallucination
   checker never blocks anything; Audit-Work-Program throws away the AI's own
   warnings. Found by a helper (not checked by me): three-way-match gives MATCH on a
   blank price, Vendor_Guard drops cut-off findings with only a log line.
3. **SAAF's own standards are thinly followed.** Across the 29: agent.yaml in 2,
   a licence in 3, AUDIT-CRITERIA.md in about half, working tests in about a third,
   and dependencies mostly not pinned.

## What works well (worth copying)

| Agent | Why it is good |
|-------|----------------|
| OWASP-AI-Testing-Agent | 79 of 79 tests pass. Live tests need a signed token and a SHA-256 approval of the reviewed payload. The best human gate in SAAF. |
| joiners-movers-leavers-agent | Report is final only after sign-off, enforced in code. (4 tests fail on Windows only, line endings.) |
| agent-drift-rater | Only fixes a person approved become issues. Self-test passes. |
| RCM-Builder | 29 of 29 tests pass, has agent.yaml. Missing: an approval field the next agent must check. |
| Vendor_Guard | 230 of 231 tests pass; cleans documents before wrapping them (a pattern our scanner now recognises). |
| GDPR-AI-Audit-Agent | 73 of 73 tests pass. But names in free-text fields are not masked. |

## What does not work, or is not finished

- **Not runnable as published:** Compliance-Audit-Agent (core code kept private),
  APM-Writer (skeleton), UC3-incident-issue-intelligence (docstrings only).
- **Install fails on this laptop:** Finding-analysis (Windows long path),
  Track-4-Audit-Report-Generator (old pandas pin, no build for Python 3.14).
- **Tests failing or broken:** ExecGRC (2 of 4 fail, data out of sync),
  judging-found-controls (fails under plain pytest), Compliance-Report-Generator
  (9 errors, not portable to Windows).
- **Needs an API key, no offline mode or tests:** CUEC_Crosscheck,
  Policy-to-Controls-Extractor, PBC-Assistant, Audit-Work-Program.

## What could be done differently (for SAAF as a whole)

1. **Make sign-off a lock, not a sentence.** Every agent that produces a final
   deliverable should release it only after a recorded, signed approval of that
   exact content. Four Eyes is a ready-made way to do this.
2. **Fail closed.** Missing data, an empty or unparsed AI answer, or an unknown
   status must give "Incomplete" or Red, never Green or MATCH.
3. **Never discard the AI's own warnings.** Merge them with rule-based checks.
4. **Ship the SAAF basics in every repo:** agent.yaml with a mandate, AUDIT-CRITERIA.md,
   a licence, an offline mode or fake model for tests, pinned dependencies.
5. **Test on Windows too.** Several failures were Windows-only; many auditors use Windows.
6. **Keep keys out of config files and browsers**, and lock web servers to the
   local machine (no `0.0.0.0`, no `CORS *`, no `debug=True`).

## Caveats

- No real AI calls were made, so the quality of the AI's answers was not judged.
- About 2 to 3 minutes per agent: this is a quick health check, not an audit.
- Helpers ran tests on copies of the repos (under `venvs\`), so the cloned repos
  stayed unchanged.
