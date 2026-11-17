# Four Eyes

**A lock that stops SAAF audit agents from releasing work that nobody approved, plus the
tests and checks that keep it from coming back.**

Built by team RAG TAG at the SAAF Security Challenge, Mollie Amsterdam, 10 November 2026,
against the queued attack "bypassing the human checkpoint". Standard library Python only.

## Start here (for the SAAF team)

| Read | What you get |
|------|--------------|
| [docs/RECOMMENDATIONS.md](docs/RECOMMENDATIONS.md) | What to fix today, this week, and a six-control minimum standard for every SAAF agent. |
| [findings/FINDINGS-REPORT.md](findings/FINDINGS-REPORT.md) | All 74 findings in plain English: where, how found, evidence, why it matters, fix, status. |
| [findings/RAG-TAG-findings.csv](findings/RAG-TAG-findings.csv) | The same 74 findings in the challenge's CSV format (as handed in). |
| [docs/METHODS.md](docs/METHODS.md) | How we found them: scope, rules, the eight methods, what "verified" means, what we did not cover. |
| [docs/review-notes/](docs/review-notes/) | Working notes: agent health check (29 agents run), record-keeping scorecard (25 agents), risky-pattern scan, leaked-key scan (masked). |
| This page, below | The guard we built (Four Eyes), how to adopt it, and how to keep these problems from coming back. |

The findings describe weaknesses that are not fixed yet. This repo is private to SAAF-Project;
please keep it that way until the owners have fixed or accepted them.

## What is in this repo

| Folder | What it is |
|--------|------------|
| `four_eyes/` | The guard: signed, content-bound human approval (`Gate`), a re-checkable logbook (`verify_log`) and the reusable bypass test kit (`four_eyes/testkit.py`). |
| `red_pencil/` | A scanner that fails the build on 8 risky patterns we found in SAAF agents today (documents that can give the AI orders, secrets sent to pages, model output rendered as live HTML, debug servers, unsafe path checks). See [docs/RED-PENCIL.md](docs/RED-PENCIL.md). |
| `action.yml`, `examples/red-pencil.yml` | Run Red Pencil automatically on every push in any SAAF repo. |
| `tests/` | 22 Four Eyes tests and 28 Red Pencil tests. No network, no API key. |
| `demo/` | Evidence: the replayed attacks before and after the fix, and the patches. |
| `findings/`, `docs/` | All findings, methods, recommendations and review notes (see Start here). |
| `agent.yaml` | The guard's own mandate in the SAAF living-map schema. |

## The problem it fixes (found today, proven by replaying the attack)

- **Executive-Summary-Writer:** the Board summary, findings, JSON and slide deck were released
  with nobody approving them. Skipping every step, or a steered model reading "no" as "confirmed",
  still released it. Before: [demo/esw-before-fix.txt](demo/esw-before-fix.txt). After: 104 tests pass.
  Fix proposed in [SAAF-Project/Executive-Summary-Writer#4](https://github.com/SAAF-Project/Executive-Summary-Writer/pull/4).
- **FieldworkOrchestration:** anyone could approve in the senior auditor's name, reassign roles,
  or close an engagement with a hand-written "approved" line. Before:
  [demo/fieldwork-before-fix.txt](demo/fieldwork-before-fix.txt). After: 18 tests pass (it had none).
  Fix proposed in [SAAF-Project/FieldworkOrchestration#5](https://github.com/SAAF-Project/FieldworkOrchestration/pull/5).

Across 29 SAAF agents we ran today, only 3 enforce a human sign-off in code. In the rest,
"a person reviews this" is a sentence in the README, not a lock.

## How Four Eyes works (plain English)

1. **Sign this exact report.** The person types `APPROVE` plus a short code computed from the
   exact content. "yes", "approve all" or a code for other content are refused.
2. **Real name.** The approver comes from the app's login (`Gate(identity=...)`), never from a
   form field, a document or the model.
3. **A stamp the AI can't fake.** The approval is signed (HMAC-SHA256) with `FOUR_EYES_KEY`,
   which stays on the server and never reaches a prompt.
4. **Change a word, the seal breaks.** `gate.require()` refuses a missing, forged, changed,
   expired or reused approval, right before anything is saved or sent.
5. **A logbook.** Every approval, refusal and release is a signed, chained line;
   `python -m four_eyes verify-log <file>` re-checks it and reports edited lines.
6. **No approval, no release.** No key, no login, any doubt: nothing is released.

## Add it to a SAAF agent (three steps)

1. Copy the `four_eyes/` folder into the agent.
2. Wire two calls:

   ```python
   import four_eyes

   gate = four_eyes.Gate(lambda: session_user, log_path="output/four-eyes-log.jsonl")
   # show the content; the person types gate.confirmation_phrase(content)
   approval = gate.approve("final_report", content, typed_reply)   # raises ApprovalRejected
   gate.require("final_report", content, approval)                 # the only way to release
   save(content)
   ```

3. Add the bypass test kit to the agent's tests:

   ```python
   import unittest
   from four_eyes.testkit import FourEyesBypassTests

   class TestSignOff(FourEyesBypassTests, unittest.TestCase):
       STEP = "final_report"
       def prepare(self, gate): ...                  # run the agent up to the draft
       def artefact(self, state): ...                # the exact content approved
       def tamper(self, state): ...                  # same state, content changed
       def release(self, gate, state, approval): ... # the agent's real release path
   ```

   The kit tries 9 bypasses (no approval, ten non-approval replies, an approval written by a
   model, a foreign key, content changed after approval, replay, wrong identity, nobody logged
   in) plus a positive control. If anyone ever weakens the sign-off, the agent's tests fail.

## Keep these problems from coming back (any SAAF repo)

Add to the repo's CI, on every push and pull request:

1. **The agent's own tests, including the Four Eyes bypass kit** (step 3 above).
2. **Red Pencil:** copy [examples/red-pencil.yml](examples/red-pencil.yml) to `.github/workflows/`.
   It fails the build on high-risk patterns (pin to a commit SHA once adopted).
3. **A secret scan of the full git history** (for example gitleaks). Today we found three real
   API keys still recoverable from old commits in two SAAF repos.
4. Declare the agent's mandate in `agent.yaml`, including
   `human_approval_required_for`, and enforce that line with Four Eyes.

## Run the tests

```bash
python -m unittest discover -s tests -v      # 50 tests, no network, no API key
python -m red_pencil path/to/some-saaf-agent # scan an agent
```

## Limitations

- A person can still approve a bad report. Four Eyes proves who approved exactly what, and that
  nothing else went out.
- Identity is only as good as the app's login. A web app must pass its authenticated session
  user (for example from a sign-on proxy that sets and strips a header), never a form field.
- Anyone holding `FOUR_EYES_KEY` can sign approvals. Keep it in a secret store, out of prompts,
  repos and browsers.
- The logbook is tamper-evident, not tamper-proof: lines cut off at the very end leave a valid
  shorter chain. `verify-log` prints the last line's signature; keep that value elsewhere.
- Red Pencil finds known patterns in Python and Jinja/HTML only; a clean scan is not a clean bill
  of health. Details in [docs/RED-PENCIL.md](docs/RED-PENCIL.md).

## Status, owners, licence

- Status: building (v0.1.0), hackathon prototype, independently security-reviewed on 10 Nov.
- Owners: team RAG TAG, SAAF Security Challenge.
- Licence: to be decided with Stichting SAAF; most SAAF repos use MIT.
