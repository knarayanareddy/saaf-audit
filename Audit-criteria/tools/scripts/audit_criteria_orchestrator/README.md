# Audit Criteria Orchestrator

Drafts and hardens an `AUDIT-CRITERIA.md` for any SAAF repo PR:

```
read PR -> Q&A -> draft -> ( review || stress test ) -> revise -> gate -> place in PR
                              ^                                     |
                              +--------- retry (<= MAX_RETRIES) ----+  No-Go = soft block:
                                                                       human picks retry / override / abort
```

The stage order, the gate and the retry budget are **code**; the LLM
sub-agents only shape content. Design:
[`plans/hackathon-4/p-audit-criteria-orchestrator.md`](../../../plans/hackathon-4/p-audit-criteria-orchestrator.md).

## What makes the output trustworthy

- **Executed, not asserted.** Every acceptance criterion carries a verification
  command. The stress tester runs it for real (exit 0 pass / 1 fail / 2 not
  testable), and the gate re-runs it on the final text.
- **Honest by construction.** An AC that fails when executed blocks the gate
  until it is disclosed under *Known deviations*. A command that cannot run
  blocks it until it is fixed.
- **Bounded in code.** `_retry_options()` removes `retry` from the offered
  choices once `MAX_RETRIES = 2` is spent. A third retry request is refused and
  logged as `decision_rejected`.
- **Fail-closed gate.** `schemas.validate()` rejects any tool name without a
  registered validator.
- **Complete trail.** `runs/<run_id>/log.jsonl` records input/output digests,
  model and prompt hash per call, every gate verdict and every human decision.
  The trail is closed in a `finally`, even on an API outage. Run IDs cannot
  collide.

## Run it (from the repo root)

```bash
# Offline, no API key. Mock LLM stages; real execution against sample_data/toy_repo:
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate                       # retry -> Go
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate --decisions override  # published with banner
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate --decisions abort     # nothing placed
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --simulate --stubborn --decisions retry,retry,retry
                                                                      # 3rd retry refused in code -> abort

# Live, against your PR checkout (needs ANTHROPIC_API_KEY). Interactive Q&A and decisions:
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --repo-dir . --allow-exec --place

# Fallbacks / alternatives
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --zip repo.zip --allow-exec
python -m tools.scripts.audit_criteria_orchestrator.orchestrator --github SAAF-Project/<repo> --pr 12   # read-only
```

`--answers answers.json` (`{"question": "answer"}`) replaces interactive Q&A.

## Security: read before `--allow-exec`

Verification commands come from the document, which means code from the PR
under review runs on your machine. Safeguards:

- only `python -m tools.scripts.*` or `python <file>.py` inside the repo root are allowed;
- no shell is used;
- a 60-second timeout applies;
- `ANTHROPIC_API_KEY` and `GITHUB_TOKEN` are stripped from the child environment.

These reduce the risk; they do not make it a sandbox. Run live in CI or a
disposable container. Without `--allow-exec`, every AC is `not-run` and the
gate stays No-Go.

"Place in PR" writes the file into your local PR checkout. Committing and
pushing stays with the human; the tool makes no remote writes.

## Files

| File | Role |
|---|---|
| `orchestrator.py` | Code-controlled flow, parallel review/stress, gate, soft block, CLI |
| `sub_agents.py` | PR reader (dir / zip / GitHub), Q&A, drafter, reviewer, stress tester, reviser, offline fixtures |
| `schemas.py` | Fail-closed hand-off validators and the deterministic DoD parser |
| `prompts.py` | LLM sub-agent prompts and the shared format spec |
| `run_logger.py` | Per-run artifacts and `log.jsonl` (IIA GIAS 12.3 / 14.6 trail) |
| `sample_data/toy_repo/` | Synthetic target with a deliberate retry-bound flaw |
