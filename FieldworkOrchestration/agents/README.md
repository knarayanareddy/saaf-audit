# `agents/`

Home of the fieldwork agents and the **single orchestrator** that calls
them, chains the ones that depend on each other, and gives an internal
auditor a way to monitor progress and check quality across a run.

Everything an agent needs is split across three sibling packages so the same
concern lives in the same place for every agent:

| Folder | Holds | See |
| --- | --- | --- |
| `prompts/` | System/user prompt text per agent | [prompts/README.md](prompts/README.md) |
| `data/` | Input files the agent reads (fixtures, samples, reference data) | [data/README.md](data/README.md) |
| `settings/` | Model, tokens, thinking, tool config per agent | [settings/README.md](settings/README.md) |

## Layout

```
agents/
  claude_init.py         # shared Claude client wrapper — do not fork per agent
  audit_trail.py         # append-only trail of every Claude call — see runs/<run_id>/
  orchestrator.py         # runs agents, chains pipelines, owns quality + approval + finalization
  dashboard.py            # renders one run's status as a local HTML file
  cli_runner.py           # allowlist-enforcing CLI command runner (not an agent — no Claude call)
  cli_allowlist.json      # the allowlist cli_runner.py enforces
  <agent_name>.py         # one module per fieldwork agent — see REGISTERED_AGENTS in orchestrator.py
  prompts/  data/  settings/
```

Use the same short, lowercase `snake_case` **agent slug** in all four
places, so `pbc_creation` means `agents/pbc_creation.py`,
`prompts/pbc_creation.py`, `settings/pbc_creation.py` and
`data/pbc_creation/`. Never invent a second spelling for the same agent.

## Agents at a glance

Every agent below follows the same contract (see [Agent contract](#agent-contract)):
`run(inputs: dict, client: ClaudeClient | None = None) -> dict`. Grouped by
which pipeline (if any) chains them — see
[The two chained pipelines](#the-two-chained-pipelines) for how each group's
steps feed into each other.

**PBC (Prepared-By-Client) pipeline** — ported from PBC-Assistant-Isabelle
(Track 2 — Evidence Collection, `plans/hackathon-2/diyve-garg-pbc-assistant-isabelle.md`):

| Slug | Model | What it does |
| --- | --- | --- |
| `pbc_creation` | Opus | Drafts a structured PBC request list (IDs, deadlines, actionable descriptions) from an audit scope and required documents |
| `pbc_distribution` | Opus | Drafts the email distributing the PBC list to the auditee (delivery itself is mocked) |
| `pbc_validation` | — (no Claude call) | Purely deterministic pending/overdue/received split per item from deadlines and what's been delivered — the judgement role it used to play with one generic prompt has moved to the propose/approve/process flow below |
| `pbc_upload_check` | Sonnet | Fast, cheap sanity check at upload time: does this delivered file even look like the right document for this PBC item? Auditee-facing — flags a mismatch before it ever reaches the auditor, but a confirmed override still goes through, flagged |
| `pbc_validation_prompt_proposal` | Opus | Drafts a validation prompt tailored to one PBC item's risk/control/planned-work context and delivered document, for a human to review/edit before it's used |
| `pbc_document_check` | Opus | Runs the actual content-based validation of one document, using a caller-supplied (human-approved) `system_prompt` — the only agent that takes its system prompt as a run-time argument instead of a fixed `prompts/<slug>.py` constant; see its docstring |
| `pbc_dashboard` | Opus | Turns validation results into completion counts, percentage, and a narrative summary |
| `pbc_reminder` | Opus | Drafts reminder/escalation emails for outstanding items (>7 days overdue = escalated) |
| `pbc_document_analysis` | Opus | Analyses one uploaded document (PDF/Excel/Word/CSV) against a specific PBC request; independent of the chain below |
| `pbc_intake` | Sonnet | Scans the `intake/` watched folder (see [Document intake](#document-intake)) and suggests PBC-ID matches for unfiled files; independent of the chain |

**Evidence-audit pipeline** — built from the Mollie Group X evidence-audit
plan (Track 2, `plans/alignment/mollie-group-x-evidence-audit.md`):

| Slug | Model | What it does |
| --- | --- | --- |
| `evidence_collection` | Sonnet | Classifies already-gathered evidence items by type/source/reliability against a control objective |
| `evidence_analysis` | Opus | Assesses evidence sufficiency/appropriateness; concludes Effective / Not Effective / Inconclusive |
| `findings_conclusion` | Opus | Drafts a structured finding (id, title, risk_rating, observation, recommendation) or confirms an effective conclusion |

**Standalone agents** — each independently useful, not part of a chained pipeline:

| Slug | Model | What it does |
| --- | --- | --- |
| `quality_check` | Opus | Independent, skeptical review of *any* agent's Claude call — pass / requires_revision / fail. Reused by both pipelines above rather than duplicated; see [Monitoring](#monitoring-progress-and-quality) |
| `document_evidence_extraction` | Sonnet (vision) | Extracts policy metadata, control statements, and evidence-implied gaps from a PDF, page by page — digital text via `pdfplumber`, scanned pages rendered to an image and read via Claude vision |
| `cli_evidence_analysis` | Opus | Interprets the raw output of an already-executed, allowlisted CLI command (see `cli_runner.py`) into structured, cited audit evidence |
| `grc_copilot_cheatsheet` | Sonnet | Generates a practitioner-ready M365 Copilot "cheat sheet" (copy-paste prompts) for a given audit domain — Markdown output, not a structured finding |

**Not an agent**: `cli_runner.py` (`run_command`) is a deterministic,
allowlist-enforcing CLI command runner — the only code in this package that
touches `subprocess`. It makes no Claude call, so it is not in
`REGISTERED_AGENTS`; treat it like `agents/data/loaders.py`. Claude never
decides which command to run — the allowlist is the actual security
control. See its module docstring for why it's kept separate from
`cli_evidence_analysis`.

## The two chained pipelines

Most agents above need another agent's output — the orchestrator is the
only module that knows the full chain (agents never import each other, per
the [Agent contract](#agent-contract)).

**`orchestrator.run_pbc_workflow(...)`** — five stages, PBC list and
validation status threaded through:

```
pbc_creation ──▶ pbc_list ──┬──▶ pbc_distribution ──▶ delivery_status
                             ├──▶ pbc_validation ──▶ validation_status ──┬──▶ pbc_dashboard ──▶ dashboard_report
                             │                                            └──▶ pbc_reminder ──▶ reminder_log
                             └────────────────────────────────────────────────────┘  (both need pbc_list too)
```

`pbc_document_analysis` and `pbc_intake` are *not* part of this chain —
call them directly, or via `run_orchestrator` (below), per received
document / to source `received_documents` from the intake folder first.

**`orchestrator.run_evidence_audit_pipeline(...)`** — four stages, with a
bounded revision loop:

```
evidence_collection ──▶ evidence_collected
                              │
                              ▼
                    evidence_analysis ──▶ analysis ──▶ quality_check ──▶ verdict
                              ▲                                │
                              └──── "requires_revision" ────────┘   (re-run analysis with feedback,
                                                                      up to max_revisions times)
                                                                │
                                                                ▼
                                                    findings_conclusion ──▶ finding
```

Stage 3 is the *same* `quality_check` agent used for monitoring every other
run (see next section) — the source plan's own "Quality Check Agent" is
what `quality_check` had already been generalized from, so this pipeline
reuses it instead of duplicating it.

**`orchestrator.run_orchestrator(agent_inputs, ...)`** — the generic,
non-chaining option: pass pre-built `inputs` per agent slug and each runs
independently (nothing passed between them). Use this for agents with no
required dependency on another's output — currently `pbc_document_analysis`,
`pbc_intake`, `pbc_upload_check`, `pbc_validation_prompt_proposal`,
`pbc_document_check`, `document_evidence_extraction`, `cli_evidence_analysis`,
`grc_copilot_cheatsheet`, and ad hoc `quality_check` calls. The webapp calls
the last three of those directly rather than through `run_orchestrator`,
since each needs to react to the previous step's result before deciding
whether to run the next (propose → human approval → process) — see
`webapp/README.md`'s "Tailored, human-approved validation prompts".

All three entry points accept `client`/`audit_trail`; if you don't supply
either, one `ClaudeClient` wired to one new `AuditTrail` is created and
shared across every stage in the call, so a whole pipeline run lands in a
single `runs/<run_id>/`.

## Per-item processing and cost

Several agents handle a *list* of independent things — `pbc_creation` drafts
one PBC item per required document, `pbc_validation` judges one item per
received file, `pbc_scope_from_work_program` atomizes one control at a
time. Each of those is one small Claude call per item, not one call for the
whole list — a single call trying to do everything at once has repeatedly
proven both less reliable (a large enough list truncates the JSON response
before it's complete — this is what originally broke `pbc_creation` /
`pbc_validation` against a ~100-item, work-program-derived PBC list) and,
for judgement-only tasks like grouping short phrases, actually *more*
expensive: `thinking="adaptive"` has been observed to consume its entire
token budget on thinking alone for tasks like these, even at very generous
budgets, leaving nothing for the output — see the settings modules for the
agents above for the specific measurements. Per-item calls sidestep both
problems and, as a bonus, make ID assignment and date arithmetic a
Python-side guarantee instead of something asked of the model.

Each such call can also be tagged with an explicit `item_ref` (e.g. a PBC
ID) via `ClaudeClient.message(..., item_ref=...)`, recorded straight onto
the audit-trail entry. `AuditTrail.entries_for_item(item_ref)` then finds
every call *about* one specific item as an exact lookup, not a positional
guess — used by the webapp's per-item audit-trail page (see
`webapp/README.md`) and by `quality_check`/`review_run` to tag their own
review of an item's call with the same `item_ref`. An agent with no natural
single-item scope simply leaves it unset.

Independent per-item calls run through **`ClaudeClient.message_many(requests,
batch_threshold=150)`**, which picks the fast path or the cheap path based
on how many there are:

- **Below the threshold** — plain individual `.message()` calls. This is
  the right choice whenever a person or a UI is waiting on the result.
- **At or above it** — `.message_batch()`, the Anthropic Batches API
  (~half the per-token cost). **This is not latency-optimized** — a batch
  goes through the same asynchronous queue regardless of size, and queue
  wait is not obviously proportional to batch size either: measured against
  a real ~104-item batch, it sat `in_progress` for longer than
  `message_batch`'s own 30-minute default timeout. `batch_threshold`
  therefore defaults high — favoring the fast, predictable path at any
  scale this project currently produces (a single engagement — tens to
  ~100 items) — rather than silently risking a demo hanging for cost
  savings nobody asked to wait that long for. `message_batch()` also
  retries a transient connection error during polling a few times before
  giving up — a multi-minute poll losing one connection along the way is
  normal on a real network, not a reason to throw away an otherwise
  still-running (or already finished) batch.

Pass a lower `batch_threshold` explicitly only for a call you know is a
genuinely large, non-interactive, background-style job where that wait is
acceptable — don't reach for `.message_batch()` directly for a per-item
loop otherwise.

## Monitoring progress and quality

This is what lets an internal auditor answer, for any run: *what happened,
was it any good, who signed off on it, and is it safe to treat as final?*
Four layers, each building on the one before:

**1. Audit trail (`audit_trail.py`) — what happened.** Every
`ClaudeClient.message()`/`.stream()` call made with an `agent="<slug>"` tag
is recorded automatically in `runs/<run_id>/audit_trail.jsonl` when the
client has an `AuditTrail` (every orchestrator entry point wires this up by
default) — system prompt, user prompt, full response text, model, timing,
token usage, one entry per call, each with a stable `entry_id`. When a call
had `thinking` enabled, its extended-thinking trace is captured too
(`reasoning_text`, via `claude_init.reasoning_from_message`) — `None` when
`thinking` wasn't on, or when adaptive thinking judged the call trivial
enough to skip visible reasoning (observed for simple tasks; the model
decides per-call, not something a caller controls), never an empty string,
so those two cases stay distinguishable. Vision input (image content
blocks) is sent to the API in full but redacted to a short placeholder
before logging, so a page scan doesn't bloat the trail with megabytes of
base64. This is the raw material everything below reads.

**2. Quality (`quality_check` + `orchestrator.review_run` /
`review_last_entry`) — was it any good.** `quality_check` is an
independent, skeptical reviewer — not the original agent's advocate — that
takes one audit trail entry and returns `{"verdict": "pass" |
"requires_revision" | "fail", "confidence", "issues", "rationale"}`.
`orchestrator.review_run(run_id)` runs it over *every* entry in a run — safe
to call more than once (append-only, so a repeat adds a second opinion
rather than overwriting), but each call re-reviews the *whole* trail, so
call it once when a run is complete, not repeatedly or per-request.
`orchestrator.review_last_entry(client,
audit_trail)` is the single-entry version for exactly that per-request
case — the pipelines use it internally right after each stage that needs a
revision decision, and it's also the one the webapp calls after
`pbc_document_check` so only the one fresh call just made gets reviewed
(see `webapp/README.md`). Verdicts are recorded separately in
`runs/<run_id>/quality.jsonl`, linked by `entry_id` — the original entry is
never touched, the same way a review note never overwrites the work paper
item it comments on. This is automated QA only: it flags what a human
should look at first, it does not replace a sign-off.

**3. Approval (`orchestrator.record_approval` / `require_approved`) — who
signed off.** Nothing an agent produces counts as final until an internal
auditor records an explicit `"approved"` or `"rejected"` decision — there
is no workflow engine here to pause a running pipeline, so this is the
honest equivalent for a synchronous script. Decisions go to
`runs/<run_id>/approvals.jsonl`, append-only (a later approval doesn't erase
an earlier rejection from the history — `approval_status` reflects only the
*most recent* decision). `orchestrator.require_approved(run_id)` raises
`ApprovalRequiredError` unless every entry is approved; any code that would
treat a run's output as final — sending an email for real instead of
mocking it, exporting a signed-off report, closing an engagement — must
call it first. `orchestrator.finalize_run(run_id)` is the concrete example:
it calls `require_approved`, then writes `runs/<run_id>/finalized.json`.

**4. Visibility (`orchestrator.approval_summary` + `dashboard.py`) — seeing
it all at once.** `approval_summary(run_id)` joins the three layers above
into one row per fieldwork step: agent, timestamp, quality verdict,
approval status. `dashboard.write_dashboard(run_id)` renders that as a
single, self-contained local HTML file
(`runs/<run_id>/dashboard.html` — open directly in a browser, no server) —
a status banner (awaiting review / ready to finalize / rejected /
finalized), counts, and one card per step with its quality rationale, any
flagged issues, and who approved or rejected it and why. It's a pure
renderer with no state of its own — re-run it after new decisions to
refresh. Scoped to one run; no cross-run/engagement overview yet.

```
ClaudeClient.message()/.stream()
        │  (tagged agent="<slug>")
        ▼
audit_trail.jsonl  ───────▶  quality_check  ───────▶  quality.jsonl
   (what happened)          (was it good?)          (verdict, linked
                                                       by entry_id)
        │                                                   │
        └───────────────────────┬───────────────────────────┘
                                 ▼
                        approval_summary(run_id)
                                 │
                    ┌────────────┴────────────┐
                    ▼                          ▼
          record_approval/require_approved   dashboard.write_dashboard
             (approvals.jsonl, who signed        (one HTML file —
              off, append-only history)           what it all looks like)
```

## Document intake

Documents an auditee/auditor delivers arrive through a watched folder, not
a web upload — drop them under `intake/<engagement_id>/<PBC-ID>/`
(confirmed, no guessing: the folder name *is* the PBC ID) or
`intake/<engagement_id>/_unassigned/` (`pbc_intake` can suggest a likely
PBC-ID match for these, which an auditor must still confirm — never
auto-assigned). See `pbc_intake.py` for the full convention. `intake/` is
gitignored, the same as `runs/` — both can hold real engagement content and
must never be committed.

## Adding a new agent — checklist

1. Pick the slug.
2. `prompts/<slug>.py` — the prompt constants.
3. `settings/<slug>.py` — the run configuration.
4. `data/<slug>/` — input files, only if the agent reads any.
5. `<slug>.py` — the agent itself, exposing the shared contract below.
6. Register it in `REGISTERED_AGENTS` in `orchestrator.py`. If it depends on
   another agent's output, add it to (or write a new) chained pipeline
   function there too — see [The two chained pipelines](#the-two-chained-pipelines)
   for the pattern.

## Agent contract

Keep every agent callable the same way, otherwise the orchestrator has to
special-case it:

```python
from agents.claude_init import ClaudeClient
from agents.prompts.<slug> import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from agents.settings.<slug> import SETTINGS


def run(inputs: dict, client: ClaudeClient | None = None) -> dict:
    """Run the <slug> agent and return its structured result."""
```

- Take inputs as arguments; do not read global state.
- Return structured data (a dict), not printed text — the orchestrator has to
  aggregate it.
- Get your Claude client from `claude_init.ClaudeClient`; do not construct
  `anthropic.Anthropic` directly and do not hardcode a model — that belongs in
  `settings/`.
- Pass `agent="<slug>"` to `client.message()`/`.stream()` so calls are
  attributed correctly in the audit trail.
- No API keys in code. They come from `.env` (see `.env.example`).

## Orchestrator

`orchestrator.py` is the only module that knows about more than one agent
at a time. It owns run order and fan-out/fan-in for the two chained
pipelines, runs independent agents on demand, and — per
[Monitoring progress and quality](#monitoring-progress-and-quality) — owns
quality review, approval gating, and finalization for every run. Agents
must not import each other; if agent B needs agent A's output, the
orchestrator passes it along.
