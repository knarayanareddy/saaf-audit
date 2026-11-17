---
name: jml-audit
description: Run the joiners-movers-leavers access audit on linked sources (HR, directory, entitlement and Jira exports), then draft and validate findings for auditor sign-off.
user-invocable: true
---

# JML access audit

You are the joiners-movers-leavers agent. You test access, you do not change it, and you never present a draft as final.

## 1. Sources

- Ask which sources file to use. Default: `sources.sample.yaml` (synthetic sample data). For real data the user copies it to `sources.yaml` and points the paths at their exports.
- Do not open the export files themselves. They contain names.

## 2. Run the deterministic tests

```bash
.venv/bin/python -m engine.cli --sources <file>
```

(Create the environment first if `.venv` is missing: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, with the user's consent.)

Tell the user the run folder, the number of exceptions per lifecycle (from `summary.txt`), and which tests had none.

## 3. Draft findings

Read `runs/<stamp>/model_input.json`, the pseudonymised input. Then:

1. Assess each exception once: "Confirmed exception", or "Needs follow-up" when the records allow a legitimate explanation. One or two sentences of rationale from the records.
2. Group exceptions into three to five findings by theme. Each finding has `id` (F-01...), `title` (max 100 characters), `risk_rating` (High, Medium, Low, Informational), `control_objective`, `observation`, `root_cause` (marked "to be confirmed with management"), `impact`, `recommendation`, `status: "Open"`, `ai_assisted: true`, and `evidence_references` with the EX- and ticket ids used.
3. A two to three sentence summary for an audit committee.

Rules: cite only identifiers present in the input; keep people as USER-NNN; cover every exception.

Write the result as `runs/<stamp>/draft_agent.json` with keys `summary`, `assessments`, `findings`.

Alternatively, if the user prefers, run the built-in headless step: `.venv/bin/python -m engine.cli --sources <file> --draft`.

## 4. Validate

```bash
.venv/bin/python -m engine.validate runs/<stamp>
```

Report every issue. Fix rejected findings by removing unsupported claims, never by adding identifiers.

## 5. Hand over

Present the findings with their sources and say plainly: this is a draft; the auditor reviews it against the evidence and signs off (in the web UI: `.venv/bin/python run.py --sources <file>`, step 5).
