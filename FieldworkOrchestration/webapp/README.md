# `webapp/`

A demo web UI over `agents/orchestrator.py` — **a concept prototype, not
production infrastructure.** It exists to validate the workflow (auditee
delivers evidence → auditor reviews the AI output and approves/rejects →
eindverantwoordelijke auditor finalizes) cheaply, before investing in real
infrastructure. See the root `CLAUDE.md` / `agents/README.md` for the
underlying agents and pipelines this only renders and calls.

## Running it

From `FieldworkOrchestration/`, after `pip install -r requirements.txt`:

```bash
uvicorn webapp.server:app --reload
```

Then open <http://127.0.0.1:8000/>.

## What it is

- `server.py` — FastAPI app. Every endpoint is a thin wrapper over an
  already-tested `agents`/`orchestrator` function; no business logic lives
  here beyond the HTTP plumbing and the PBC-item/audit-trail join described
  in `_pbc_item_rows`.
- `state.py` — the one piece of *new* persistence this layer needed: a
  `runs/<run_id>/webapp_state.json` file holding the run's `pbc_list`,
  `received_documents`, and `validation_status` between HTTP requests (the
  agents themselves return data from function calls; nothing about a run's
  higher-level state is persisted anywhere else on its own). Not part of
  the agents' contract — no agent module reads or depends on this file. For
  an engagement created from a UC8 work program, the *exact* file that was
  uploaded is additionally kept as-is at `runs/<run_id>/uploaded_work_program.json`
  — a parsed copy also lives inside `webapp_state.json["work_program"]` (what
  `pbc_scope_from_work_program`/`control_coverage` actually consume), but
  the original upload is never only reachable through that derived form.
- `static/` — plain HTML/CSS/JS, no build step, no framework. One shared
  header (`common.js`'s `renderHeader()`) so the "DEMO — Track 2 Fieldwork"
  label, the SAAF logo (top-left), and the role picker (with a name next to
  it) stay in sync across every page from one place. Switching role in the
  header reloads the current page so its role-dependent logic
  re-initializes.

**Usernames are part of the engagement, not the browser.** Auditor and
final-auditor names are set at engagement creation (or corrected later on
`engagement.html`), alongside the auditee contact, and stored in that
engagement's own `webapp_state.json["assigned"]` (`{"auditor": ...,
"senior_auditor": ...}`) — `POST /api/runs/{run_id}/approve` and
`POST /api/runs/{run_id}/items/{pbc_id}/process` both resolve the
attributed name from that record server-side, never from anything the
client sends. There is no browser-local name storage any more (an earlier
version had one, as a per-role convenience — removed once engagement.html
made editing the engagement's own record the natural place to fix a name,
making the local copy a second, driftable source of truth for the same
thing). The header's name next to the role picker is read live from the
selected engagement; with no engagement selected, or no name set yet for
the current role, it says so plainly (and links to `engagement.html` to set
one) instead of falling back to anything browser-local.

Pages: `index.html` (list existing engagements, each with a "Details" link
to `engagement.html`; create a new one — either by typing a
required-documents list, or from a UC8 `work_program.json` via the
Track 1 → Track 2 bridge — including the auditor/final-auditor name
fields), `dashboard.html`
(visual progress overview: a funnel of not-yet-delivered / awaiting-auditor
/ approved / rejected counts, a stacked progress bar, and the overall status
banner), `auditee.html` (upload evidence per PBC item, with the upload
sanity-check/override flow below), `auditor.html` (propose/approve a
validation prompt, run the check, quality verdict + approve/reject per
item), `senior.html` (approved/rejected items + finalize), `coverage.html`
(risk → control → planned work → status, when a work program is linked),
`item.html` (one PBC item's full audit trail — linked from both
`auditor.html` and `senior.html`; not in the header nav since it's always
reached in context of one item, never browsed to cold), `engagement.html`
(one engagement's master data — scope, period, auditee contact, assigned
auditor/final-auditor names — view and edit; reached via a "Details" button
next to each engagement on `index.html`, not in the header nav for the same
reason as `item.html`).

Every page that has an engagement loaded shows a consistent
"organization · audit scope · audit period" line (`common.js`'s
`engagementContextText(run)`) so which engagement you're looking at is
never ambiguous, whichever page you're on.

## Editing engagement master data

`POST /api/runs/{run_id}/update` (body: any subset of `audit_scope`,
`audit_period`, `auditee_name`, `auditee_email`, `auditee_org`,
`auditor_name`, `senior_auditor_name` — the same field names the two
creation forms already use) corrects the engagement's own record after
creation — a typo in the scope, a changed contact email, reassigning who's
the auditor. It deliberately does not touch `pbc_list`,
`received_documents`, `validation_status`, or `work_program` — there is no
"regenerate the PBC list" action here, only metadata correction.
`engagement.html` is the page for this: a read-only reference block (run
ID, item count, whether this engagement came from a UC8 work program or a
typed list) plus an editable form pre-filled from the current record.

## Deleting an engagement

`DELETE /api/runs/{run_id}` permanently removes `runs/<run_id>/` (state,
audit trail, quality/approval logs, prompt and note history,
`finalized.json` if present) and `intake/<run_id>/` (every document the
auditee uploaded) from disk — irreversible, no soft-delete, no trash to
recover from. The server enforces no safeguard beyond the run existing
(404 otherwise); the only protection is `index.html`'s "Delete" button on
each engagement row, which requires confirming a native browser dialog that
explicitly warns this cannot be undone before the request is even sent.

## Jumping from traceability straight to where an item currently sits

Each PBC item on `coverage.html` is a link, not just a pill — clicking it
goes to whichever page actually owns the next action for that item right
now, the same step-by-step logic an internal auditor would apply by eye:
nothing delivered yet (`pending`/`overdue`) → `auditee.html`; delivered but
no auditor decision recorded yet → `auditor.html` (true whether the AI
approved it, flagged it `insufficient`, or was itself uncertain — all of
those still wait on the auditor, not just a clean AI pass); rejected → back
to `auditor.html` for a correction; approved → `senior.html`, awaiting
final sign-off. `coverage.html` has to fetch `/board` alongside `/coverage`
to do this — `control_coverage` (`agents/orchestrator.py`) only carries
each item's AI/delivery status, not the human approval decision, so the
board (which has both) is the source of truth for "where does clicking
this item take me"; see `targetPageFor` in `coverage.html`. The pill label
and colour also now come from the same board-derived `display_status` /
`display_status_class` every other page uses, instead of the raw
`validation_status` coverage rows carry on their own — one consistent
status vocabulary across the whole app, not a second one just for this
page.

## Risk & control context on the review pages

Judging an AI verdict means knowing what it's actually being judged
against — the risk this PBC item mitigates, the control it evidences, and
the audit work planned around it, not just "did the AI say validated".
`_work_program_context` (`server.py`, already used server-side to give
`pbc_validation_prompt_proposal` the same context when drafting a prompt —
see "Tailored, human-approved validation prompts" above) is now also
exposed per item as `work_program_context` on both `/board` and
`/items/{pbc_id}/history`, and rendered as a distinct "Risk & control
context" block (risk, control + objective, planned audit work as a bulleted
list) on `auditor.html` — right under each item's description, before its
AI status — and on `item.html`. Empty (renders nothing) for an engagement
not linked to a UC8 work program, or an item traceability couldn't connect
to a specific control, the same as `coverage.html`'s own availability
check.

Each stage's page only shows what's actually ready for it — `auditor.html`
hides a PBC item until the auditee has delivered something for it, and
`senior.html` hides an item until the auditor has recorded a decision on it
(both note how many items are hidden for that reason, and `dashboard.html`
is the place to see everything, including what's not ready yet, all at
once).

## Per-item audit trail (`item.html`)

`GET /api/runs/{run_id}/items/{pbc_id}/history` assembles everything that
happened to one PBC item — every file the auditee delivered, every Claude
call tagged with that item (input, output, model — see "Exact per-item
linkage" below), each call's quality verdict and — when the call had
`thinking` enabled and actually produced a reasoning trace — its extended
thinking, nested under it, the proposed/approved validation-prompt history,
and every approve/reject decision (timestamp, reviewer, role, comment).
`item.html` renders that as one page (the thinking trace under its own
"Reasoning (extended thinking)" expandable section per call, only shown
when one exists), linked from a "View full audit trail →" line on each item
in `auditor.html` and an "Audit trail →" column in `senior.html`'s table —
an internal auditor should never need to reconstruct one item's story by
cross-referencing `audit_trail.jsonl` by hand.

## Item status is always live — nothing to manually re-validate

An item's `pending`/`overdue`/`received` status (has anything been
delivered yet, and is it late) is recomputed from today's date and
`received_documents` on every read of the board/coverage/item-history
endpoints — `pbc_validation` makes no Claude call any more (see its
docstring), so there's no cost or latency reason to cache it, and no button
or endpoint to trigger a refresh. There used to be a "Re-validate
everything" button on `auditee.html` and a `POST /api/runs/{run_id}/validate`
endpoint behind it; both are gone — the button's own click handler wrote
`pbc_validation`'s basic result over *all* of `validation_status`, silently
overwriting a real `pbc_document_check` verdict from the flow below with a
shallow "received" the moment someone clicked it after a detailed check had
already run. That was a genuine bug, not just stale UI, so the fix was to
remove the caching (and the button) rather than patch the overwrite.

A `pbc_document_check` result recorded via `/items/{pbc_id}/process` (see
below) always overrides the live basic status for that item — never the
reverse — via `_merged_validation_results` in `server.py`, the one place
that does this merge; `_pbc_item_rows` and the `/coverage` endpoint both
read through it rather than `state["validation_status"]` directly.

## Tailored, human-approved validation prompts — with an automatic first pass

A single generic "does this filename look right" prompt does not scale to
what different PBC items actually need checked (see
`agents/pbc_document_check.py`'s docstring for the full reasoning). The
propose → approve → run shape still exists, but it now runs automatically
the moment a document is accepted as delivered, so an auditor opening the
board finds an AI verdict already waiting rather than having to trigger the
first check by hand:

1. **Propose** — `pbc_validation_prompt_proposal` drafts a prompt tailored
   to the item's risk/control/planned-work context (when the engagement is
   linked to a UC8 work program) plus the PBC description and the delivered
   document.
2. **Run** — `pbc_document_check` runs with exactly that prompt, and the
   resulting status (`validated`/`received`/`insufficient`) is folded into
   `validation_status`.

`_auto_evaluate_upload` in `server.py` does both steps right inside
`POST /api/runs/{run_id}/upload`, once a document is accepted (not before —
see the sanity check below), using the AI's own proposal with no prompt
edits. Both the proposed and the "approved" prompt still land in
`runs/<run_id>/prompts/<pbc_id>.jsonl` — the approved entry is tagged
`"auto": true`, `"approved_by": "AI (automatic first pass)"`, so `item.html`
and the audit trail always show plainly that this run had no human editing
the prompt first, unlike a manual approval. If the automatic pass itself
fails (a flaky call, a bad extraction), it fails silently and just leaves
the item without an AI verdict — never the upload, which has already
succeeded by that point; see that function's docstring.

The propose/edit/run controls on `auditor.html` still exist, now serving
the **correction loop**: an auditor who disagrees with the automatic
verdict re-proposes (or edits the textarea) and re-runs via
`POST /api/runs/{run_id}/items/{pbc_id}/process`, which records a real,
named human approval — not an automatic one — and only that fresh call is
quality-reviewed (`orchestrator.review_last_entry`), not the whole trail;
see `agents/README.md`'s warning about `review_run` re-reviewing everything
on every call. Nothing is ever overwritten in the prompt history — every
proposed and every approved prompt (automatic or human) is appended, so a
correction loop's full "what was tried, by whom" stays visible even after a
later run supersedes an earlier `validation_status` entry.

The AI's verdict is never itself the decision that gates finalization
(`orchestrator.require_approved`) — the board's combined status label makes
this explicit: an item that passed the automatic check reads **"AI
approved — awaiting auditor confirmation"**, never "approved" on its own;
only a recorded human decision produces **"Auditor approved"**. See
`_display_status` in `server.py` for the full label set, including the one
non-obvious case: `pbc_document_check`'s own `"received"` verdict (it ran,
and genuinely couldn't decide) reads differently from the pre-check
`"received"` `pbc_validation` gives a delivered-but-not-yet-evaluated item —
same status string, disambiguated by whether a `pbc_document_check`
audit-trail entry actually exists for the item, not by the string alone.

`pbc_document_check`'s `system_prompt` is deliberately a caller-supplied
argument, not a fixed `prompts/pbc_document_check.py` constant — that's the
entire point of this feature, and is documented as an explicit exception to
the usual agent contract in that module's docstring.

## Upload-time sanity check, with auditee override

`POST /api/runs/{run_id}/upload` runs `pbc_upload_check` (a fast, cheap
model) against the file before anything else. If that looks wrong for the
requested PBC item, the file is still saved to disk but *not* counted as
delivered yet (`received_documents` untouched, and the automatic evaluation
above does not run yet either); the response is `{"ok": false,
"looks_correct": false, "concern": "..."}` and `auditee.html` shows the
concern with two choices: pick a different file, or "This is correct — send
anyway" (re-POSTs the same file with `force=true`). Forcing it through
still counts it as delivered — and still triggers the automatic evaluation
— but records `state["flags"][pbc_id]` (`{"type": "auditee_override",
"concern": ..., "filename": ..., "at": ...}`) — surfaced on the board, in
`senior.html`'s table, and at the top of `item.html`, so the auditor sees a
document that was pushed through over a concern, not one that quietly
looked fine.

A successful upload can now make up to three sequential Claude calls (the
sanity check, the prompt proposal, the document check) before responding —
`auditee.html` disables the Upload button and shows "Uploading &
checking…" for the duration rather than leaving it looking stuck.

## Opening the original document

An AI verdict is not itself evidence — confirming it means opening the same
file the AI evaluated, not taking the summary on faith. `GET
/api/runs/{run_id}/items/{pbc_id}/document` serves whatever
`pbc_document_check` most recently ran against (`auditor.html`'s "Open
original document →" link, next to "View full audit trail →"); `GET
/api/runs/{run_id}/items/{pbc_id}/document/{filename}` serves one specific
historical upload by name (`item.html`'s "Delivered by the auditee" list
links each past upload to itself, useful once an item has more than one —
an auditee correction, or a re-upload after `insufficient`). The uploaded
filename is sanitized to its basename on the way in (`Path(...).name`,
inside `api_upload`) and the filename-scoped download endpoint only serves
a name that's actually recorded in this item's `received_documents` — both
exist so a crafted filename (`../../etc/passwd`-shaped) can neither write
nor read outside that item's own intake folder; `_serve_item_document`
re-resolves and re-checks the final path against the intake folder as a
second, independent guard even after that lookup passes.

## Auditor notes — supplementary audit evidence

Confirming the AI's document check is only one of the auditor's two jobs on
an item (open the source document, above, and judge the AI's own read of
it); the other is doing whatever further audit work the item still needs —
work an AI verdict can support but not replace. `POST
/api/runs/{run_id}/items/{pbc_id}/notes` (body: `text`, optional `author` —
same assigned-auditor fallback as `/process`'s `approved_by`) records one
free-text note to `runs/<run_id>/notes/<pbc_id>.jsonl`, append-only, shown
on both `auditor.html` (inline, with a comment box to add another) and
`item.html` (the full history, in the "Auditor notes" section). Deliberately
separate from the `comment` an approve/reject decision can carry
(`AuditTrail.record_approval`) — that comment explains *one decision* and
only exists once one is made; a note is independent of deciding anything at
all, for evidence gathered outside the AI (a call to the bank, a
reconciliation run by hand) or a caveat the auditor wants on record before
anyone — themselves later, a colleague, the final auditor — decides.

## Exact per-item linkage via `item_ref`

Every per-item Claude call (`pbc_creation`, `pbc_upload_check`,
`pbc_validation_prompt_proposal`, `pbc_document_check`, and the
`quality_check` call reviewing any of them) is tagged with an explicit
`item_ref` — the PBC id — threaded through `ClaudeClient.message()` down to
`AuditTrail.record()`. `AuditTrail.entries_for_item(pbc_id)` is then an
exact lookup, not a guess. This replaced an earlier, explicitly-documented
"zip audit-trail entries back onto PBC items by call order" heuristic in
`_pbc_item_rows` — that positional assumption no longer exists anywhere in
this layer. `pbc_validation` itself makes no Claude call at all any more
(see its docstring) — the judgement it used to make with one generic prompt
per item is now the propose/approve/process flow above.

## Two deliberate gaps — fine for a demo, not for anything real

**No real authentication.** The role picker in the header is still a
dropdown, not a login — anyone using the browser can select "Final auditor"
and approve as whoever this engagement has on record for that role (see
"Usernames are part of the engagement" above). That's a real improvement
over a freely-typed name (the attributed identity is now fixed per
engagement, not whatever a browser happened to have cached), but it is
*not* the same as verifying who's actually at the keyboard — the dropdown
itself is still unauthenticated. This is the right simplification *for
validating the workflow*; it is the wrong foundation for anything that
needs the full accountability property the approval-gate system
(`agents/orchestrator.py`) was built to provide. Don't let a demo running in
this mode be mistaken for having that property.

**No concurrency safety under real multi-user load.** `approvals.jsonl` /
`quality.jsonl` are appended to from a single process today; nothing
guards against two people recording a decision on the same item at nearly
the same instant. Fine at demo scale (a handful of people clicking through
a walkthrough); a real risk once this serves genuine concurrent traffic.

Both are acceptable to defer *as long as they stay visibly labelled* as not
solved yet — see the conversation that led here for the fuller reasoning:
the JSON/folder data model this sits on is portable to a real deployment
(e.g. Docker, a volume for `runs/`/`intake/`) later; swapping local files
for a real database is the standard next step once the concept is
validated, not something to solve now.

## ElevenLabs voice assistant

A per-engagement voice assistant, on by default for no engagement — a "🎤
Voice" button appears in the header only when the loaded engagement has
both `elevenlabs_enabled` (bool) and a non-empty `elevenlabs_agent_id`, set
on `engagement.html`'s "Voice assistant (ElevenLabs)" card (an on/off
switch and a text field, both saved immediately on change via the same
`POST /api/runs/{run_id}/update` endpoint as the rest of the engagement's
master data — see `renderHeaderRoleName` in `common.js`, which fetches the
engagement anyway and toggles the button's visibility from the same call).

**The agent itself is not something this app creates.** It's a separate
ElevenLabs Conversational AI agent, created via a claude.ai chat with the
ElevenLabs MCP connected (this webapp session has no MCP access to
ElevenLabs — see the conversation this was built from for the exact prompt
used), configured with four **client tools** that this app answers, not
ElevenLabs' own servers:

| Tool | Parameters | Answered by (in `voice.js`) |
| --- | --- | --- |
| `get_engagement_status` | none | counts from `/board`: not yet delivered, awaiting auditor, approved, rejected |
| `get_item_status` | `pbc_id` | one item's description, `display_status`, AI notes, and risk/control context from `/board` |
| `list_outstanding_items` | none | items still pending/overdue, with deadlines, from `/board` |
| `switch_role` | `role` (auditee/auditor/senior_auditor) | calls `setRole()` and navigates to that role's page |

The agent has no server-side access to this app or its data at all — every
tool call is dispatched back to the browser tab the conversation is
running in (`Conversation.startSession({ clientTools: {...} })` from
`@elevenlabs/client`, loaded on demand via
`https://cdn.jsdelivr.net/npm/@elevenlabs/client/+esm` — not bundled,
matching this project's "no build step" static frontend) and answered from
whatever that tab can already see through the same `/board` endpoint every
page uses. The agent literally cannot know more about an engagement than
its own browser tab does.

**Auth**: this ElevenLabs agent requires a signed conversation URL (not a
bare public `agent_id`), which means the ElevenLabs API key has to sign it
— and that key must never reach the browser. `GET
/api/runs/{run_id}/elevenlabs/signed-url` is the server-side proxy: it
reads `ELEVENLABS_API_KEY` from the environment (`.env.example`), calls
ElevenLabs' own `get_signed_url` endpoint, and returns only the resulting
`signed_url` to the browser. 400s if the engagement doesn't have the
assistant enabled or has no agent id (shouldn't normally be reachable,
since the header button is hidden in both cases); 500 if the server has no
key configured; 502 if ElevenLabs' own call fails. Uses `httpx` — the one
new runtime dependency this feature added (`requirements.txt`), since
nothing else in this project talks to an external HTTP API directly.

Ending a voice session with "switch me to auditor" navigates the whole
page (same as the header's role dropdown always has) — the in-progress
conversation drops when that happens, a known, accepted limitation rather
than something this handles gracefully yet.

## Not built yet

- Two-tier approval enforcement (`record_approval`'s `role` field is
  recorded today but `require_approved`/`finalize_run` don't yet require
  *both* an `"auditor"` and a `"senior_auditor"` decision before finalizing
  — right now any role can approve and that alone satisfies the gate).
- The propose/edit/run loop on `auditor.html` keeps the current proposal
  only in the page's own memory (a browser refresh loses an unrun edit,
  though nothing is lost once "Run check" is clicked — that call is what
  gets appended to `prompts/<pbc_id>.jsonl`). Fine for a demo walkthrough;
  a real UI would persist an in-progress draft server-side too.
- `pbc_upload_check` and `pbc_document_check` are independent calls today —
  an auditee who overrides a flagged upload and an auditor who then runs
  the detailed check are not told about each other's finding beyond what's
  visible on the board/`item.html`; there's no automatic "the detailed
  check also came back insufficient, and this was already flagged at
  upload" callout.
- Voice-dictated auditor notes (speak a note instead of typing it into
  `auditor.html`'s note box) — a separate, simpler ElevenLabs
  Speech-to-Text feature that doesn't need a Conversational AI agent at
  all, not built alongside the four-tool assistant above.
- The voice panel (`voice.js`) shows a one-line status ("Listening…",
  "Speaking…") only — no visible transcript of what was said or heard, and
  no history of a past conversation once it ends.
