# RAG TAG findings report: SAAF Security Challenge, 10 November 2026

Team RAG TAG. Every finding below is also a row in `RAG-TAG-final.csv`, the file handed in.

## Summary

- **74 findings in 31 SAAF repos.** 2 Critical, 21 High, 39 Medium, 12 Low.
- **62 confirmed by us in the code or by a replayed attack** (verified: yes). The rest come from a helper's offline run and are marked verified: no.
- **5 fixed or mitigated today** with our guard Four Eyes, with tests that fail before the fix and pass after.
- **Scope:** all 47 SAAF-Project repos live before 13:30 today (3 repos created today excluded). Local copies only, no attacks on live systems, no real AI calls, no secret values copied.

## How we looked (methods)

| Method | What it means |
|--------|---------------|
| read | We read the code and confirmed the line ourselves. |
| scan | Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm. |
| replay | We replayed the attack in an automated test on a local copy. It succeeded on the original code (test output saved), then failed after our fix. |
| run | We ran the agent offline (no real AI calls) and saw it happen. |
| helper | A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no. |
| secrets | We downloaded the full git history of every in-scope repo and searched every past change for key patterns. Values were masked and never tested. |
| patterns | We searched all repos for risky code patterns, then read each hit to confirm it is reachable. |
| trace | We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging). |

## Findings by dimension

### 1. Approvals nobody really gave (7)

An audit agent must not release a final result unless a real, identified person approved that exact result. Here the approval could be skipped, faked, given in someone else's name, or decided by the AI itself. This is today's queued attack 'bypassing the human checkpoint'.

#### No final human sign-off before the board summary is written

- **Where:** Executive-Summary-Writer
- **Risk:** High. **Verified:** yes. **Status:** Fixed today by team RAG TAG with our guard Four Eyes; pull request open (link in the fix line).
- **What is wrong:** In scripts/graph.py the confirm node (line 352) is a normal node, not an interrupt. The only gate before write_summary (lines 355-363) checks that each step key is in 'done' and that grade and tone are set; a step the model classifies as skipped is also added to 'done' (lines 154-160). Replay: skipping every step, the summary, JSON, trace and deck are produced without any person approving the content.
- **How we found it:** We replayed the attack in an automated test on a local copy. It succeeded on the original code (test output saved), then failed after our fix.
- **Evidence:** scripts/graph.py:352 'confirm' is not a pause; the gate at :355-363 only checks steps are 'done', and 'skipped' counts as done (:154-160). Test output on the original code: 'AssertionError: summary released without a person approving it'.
- **Why it matters:** The Executive Board could receive a summary that no manager ever approved.
- **Fix:** Add a final approval step that requires an exact confirmation decided in code and bound to the content, record who approved and when, and refuse to save without it. FIXED TODAY by team RAG TAG with our guard Four Eyes: signed, content-bound final approval in graph.py and run.py; 13 replay tests added; all 104 agent tests pass. Pull request: https://github.com/SAAF-Project/Executive-Summary-Writer/pull/4

#### Human approval of preparation steps is decided by a model call

- **Where:** Executive-Summary-Writer
- **Risk:** High. **Verified:** yes. **Status:** Mitigated today by team RAG TAG: the final release now needs a Four Eyes approval checked in code.
- **What is wrong:** For steps 1 to 4 the user's free-text reply is classified as confirmed or skipped by a model call (llm.interpret, scripts/graph.py line 137). Replay with a model steered to read every reply as confirmed: the manager answers 'No, that is wrong' four times and the summary is still released.
- **How we found it:** We replayed the attack in an automated test on a local copy. It succeeded on the original code (test output saved), then failed after our fix.
- **Evidence:** scripts/graph.py:137 uses a model call (llm.interpret) to decide whether a reply was 'confirmed'. Every reply shows up in the run trace as an 'interpret' call. Test with a steered model: 'AssertionError: summary released although the manager said no'.
- **Why it matters:** A manipulated AI can turn a manager's 'no' into a 'yes'.
- **Fix:** Match accept and skip replies in code before any model call; never let a model decide that a human approved. MITIGATED TODAY by team RAG TAG: the final release now needs a Four Eyes approval checked in code, so a steered model can no longer release the summary (replay test included). Pull request: https://github.com/SAAF-Project/Executive-Summary-Writer/pull/4

#### Approver name on a prompt approval is taken from the request body

- **Where:** FieldworkOrchestration
- **Risk:** High. **Verified:** yes. **Status:** Fixed today by team RAG TAG with our guard Four Eyes; pull request open (link in the fix line).
- **What is wrong:** webapp/server.py line 575: approved_by = body.get("approved_by") or the assigned auditor or "unknown". The person named on the approval record in the prompt history is whatever the client sends; the server has no authentication (its own header, line 5, says real authentication is not solved yet). Anyone who can reach the app can record an approval in another person's name.
- **How we found it:** We replayed the attack in an automated test on a local copy. It succeeded on the original code (test output saved), then failed after our fix.
- **Evidence:** webapp/server.py:575 approved_by = body.get('approved_by'); the app has no login (its own header, :5). Test after fix: a body 'approved_by' without login is refused (401).
- **Why it matters:** The audit file can show an approval in the name of someone who never gave it.
- **Fix:** Take the approver only from an authenticated session, never from the request; sign approvals and bind them to the exact prompt and document approved. FIXED TODAY by team RAG TAG with Four Eyes: approved_by now comes from the logged-in user only; replay test included. Pull request: https://github.com/SAAF-Project/FieldworkOrchestration/pull/5

#### Anyone can approve review entries in the assigned reviewer's name

- **Where:** FieldworkOrchestration
- **Risk:** High. **Verified:** yes. **Status:** Fixed today by team RAG TAG with our guard Four Eyes; pull request open (link in the fix line).
- **What is wrong:** webapp/server.py api_approve (lines 671-695) accepts entry_id, decision and role from the request body and records the decision under whoever is assigned to that role, with no authentication. The caller chooses the role, so any caller can approve as the manager; /finalize (line 697) then accepts these approvals as the human sign-off. For older engagements the reviewer name itself is taken from the body (line 684).
- **How we found it:** We replayed the attack in an automated test on a local copy. It succeeded on the original code (test output saved), then failed after our fix.
- **Evidence:** webapp/server.py api_approve (:671-695): no login; caller picks the role. Test output on the original code: an anonymous approval as senior auditor returned '200 OK'; a hand-written 'approved' line let the run finalize.
- **Why it matters:** Anyone who can reach the app can close an engagement as the senior auditor.
- **Fix:** Require login on approval endpoints and check that the logged-in person holds the role; record a signed approval bound to the reviewed content before /finalize accepts it. FIXED TODAY by team RAG TAG with Four Eyes: anonymous approvals refused (401), approving in another role refused (403), hand-written or out-of-date approvals no longer finalize; 18 tests added (the repo had none). Pull request: https://github.com/SAAF-Project/FieldworkOrchestration/pull/5

#### Anyone can reassign roles and redirect auditee requests

- **Where:** FieldworkOrchestration
- **Risk:** High. **Verified:** yes. **Status:** Fixed today by team RAG TAG with our guard Four Eyes; pull request open (link in the fix line).
- **What is wrong:** webapp/server.py api_update_run (line 271) changes auditor_name, senior_auditor_name and auditee_email with no login. Anyone who can reach the app can make themselves the senior auditor and then approve their own work, or redirect PBC requests to their own email address.
- **How we found it:** We replayed the attack in an automated test on a local copy. It succeeded on the original code (test output saved), then failed after our fix.
- **Evidence:** webapp/server.py api_update_run (:271) changes auditor_name, senior_auditor_name and auditee_email with no login. Test: anonymous change now 401, self-assignment 403.
- **Why it matters:** Someone could make themselves the senior auditor, or send document requests to their own email address.
- **Fix:** Require a logged-in user for role and contact changes and forbid self-assignment. FIXED TODAY by team RAG TAG: anonymous changes refused (401), self-assignment refused (403); replay test included. Pull request: https://github.com/SAAF-Project/FieldworkOrchestration/pull/5

#### Payment released by the pipeline without a human approval

- **Where:** threewaysecurity
- **Risk:** High. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** demo_pipeline.py sets pay_status 'RELEASED' after the automated checks and IBAN verification (lines 289-294), and the decision agent writes 'Payment released' (src/agent/decision_agent.py line 95). No person approves the release.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** demo_pipeline.py:289-294 sets pay_status 'RELEASED'; src/agent/decision_agent.py:95 'Payment released.'
- **Why it matters:** Money can leave the company on the AI pipeline's decision alone.
- **Fix:** Make release a separate step that needs a recorded, signed approval by an authorised person (for example with Four Eyes).

#### A Go decision needs no human sign-off

- **Where:** Audit-criteria
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** The planning orchestrator asks a person to decide only on a No-Go; a Go outcome proceeds without any human sign-off.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** The planning orchestrator asks a person only on No-Go.
- **Why it matters:** A 'Go' to start fieldwork can happen without anyone signing it off.
- **Fix:** Require a recorded human sign-off for Go as well as No-Go.

### 2. Documents that can give the AI orders (6)

Audit agents read documents written by the auditee. If the document text is pasted into the AI's instructions without a clear, unbreakable boundary, a sentence planted in a policy or slide can change the AI's verdict. This is today's queued attack 'prompt injection hidden in evidence documents'.

#### Audited repo files wrapped in fixed tags the files can close

- **Where:** Agent-Auditor
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** server/server.py line 486 wraps each file of the audited repo as <file path="name"> content </file>, and lines 890 and 943 wrap the whole repo as <repo> ... </repo>, without escaping. A file in the audited repo that contains </file> or </repo> can end the wrapper and give the auditing model instructions that change its verdict.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** server/server.py:486 wraps each audited file as <file path=...>content</file>; :890 and :943 wrap the repo as <repo>...</repo>, nothing escaped.
- **Why it matters:** The agent that audits other agents can be told by the audited code to pass it.
- **Fix:** Escape or reject the delimiter inside file content (or use a random per-run boundary) and tell the model that repo content is evidence, never instructions.

#### Policies joined into the prompt without any data boundary

- **Where:** Compliance-Audit-Agent
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** scripts/build_prompt.py policies_as_knowledge_chunks (lines 595-601) and summary_as_knowledge_chunks (lines 385-391) join full policy texts with newlines and place them in the prompt with no delimiters and no instruction that policy text is data. A line planted in a policy can change the verdicts of both independent assessors at once.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** scripts/build_prompt.py:597 joins all policy texts with newlines into the prompt; :389 does the same for the policy summary. No delimiter, no 'this is data' rule.
- **Why it matters:** One planted sentence in a policy can flip both independent compliance checks at once.
- **Fix:** Wrap each policy in labelled delimiters with a random boundary, and tell every agent prompt that policy content is evidence only, never an instruction.

#### Document wrapper can be closed by the document itself

- **Where:** Executive-Summary-Writer
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** scripts/material.py line 211 wraps each file as <audit_material file="name"> text </audit_material> without escaping the closing tag or the file name. A document, slide note or hidden sheet containing </audit_material> ends the wrapper early and the rest is read as instructions. The same code is copied in frontend/agent-service/upstream/material.py line 211.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** scripts/material.py:211 builds f'<audit_material file="{name}">{text}</audit_material>' with nothing escaped; the same line is copied in frontend/agent-service/upstream/material.py:211.
- **Why it matters:** A slide note containing '</audit_material>' can give the AI instructions about the Board summary.
- **Fix:** Use a random per-run delimiter, escape or reject it inside the material, and tell the model in the system prompt that material is data, never instructions. Fix both copies.

#### Document text placed in a fixed <document> tag without cleaning

- **Where:** Track-2-Evidence-Collection-Extraction
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** compliance_qa.py line 271 builds the prompt as <document> document_text </document>, and line 266 wraps additional_context the same way. document_text comes straight from the uploaded PDF (line 425) and is not cleaned, so a PDF containing </document> can end the wrapper and inject instructions into the compliance verdict.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** compliance_qa.py:271 '<document>{document_text}</document>' and :266 for additional_context; document_text comes straight from the PDF (:425).
- **Why it matters:** A policy PDF containing '</document>' can steer the compliance verdict.
- **Fix:** Neutralise the delimiter inside document text before wrapping (as Vendor_Guard does with _neutralize_tags) and state in the system prompt that the document is data.

#### Model output treated as Authoritative Source by the reporter

- **Where:** Compliance-Audit-Agent
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** scripts/build_prompt.py lines 424 and 433-434 pass the merged checker and gap results to the reporter under the heading 'Authoritative Source' and tell it to work strictly and only from it. A poisoned verdict from an earlier stage is carried into the final report as authoritative.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** scripts/build_prompt.py:433 heading 'Consolidated Compliance & Gap Results (Authoritative Source)' and :424 'work strictly and only' from it.
- **Why it matters:** A poisoned verdict from an earlier step reaches the final report as 'authoritative'.
- **Fix:** Label merged output as model output to be checked, not as an authoritative source; keep the evidence check against the original policy text.

#### Policy lines joined into the heading prompt with no boundary

- **Where:** Policy-to-Controls-Extractor
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** services/segments.py lines 100-102 join every numbered line of the policy document with newlines straight into the model prompt, with no delimiter around the document text. The same code exists in a stray copy, services/docx_extractor copy.py line 176. A line in the policy can act as an instruction to the model.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** services/segments.py:100-102 joins every policy line into the prompt; the same code sits in a stray copy, 'services/docx_extractor copy.py':176.
- **Why it matters:** A line in the policy can instruct the AI how to split and read the policy.
- **Fix:** Wrap the document lines in a random-boundary block labelled as data, and remove the stray copy file.

### 3. 'All fine' when something went wrong (11)

When data is missing, the AI's answer is empty or cut off, or a check finds a problem, the agent should say 'incomplete' or 'red'. These agents say 'green', 'match' or nothing at all.

#### Report shows Green when there are no results or unknown statuses

- **Where:** CUEC_Crosscheck
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** cuec_crosscheck.py _compute_rag (lines 282-289) returns Red only for 'No match', Amber only for 'Partial', and Green for everything else. An empty match list, an unparsed model reply or an unexpected status value all produce a Green report.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** cuec_crosscheck.py:282-289 returns Red only for 'No match', Amber only for 'Partial', and Green for everything else, including an empty list.
- **Why it matters:** If the AI fails or returns nothing, the client sees a Green controls report.
- **Fix:** Fail closed: return Red or 'Incomplete' unless every CUEC has a recognised status, and show the count of unassessed items.

#### Model's own sufficiency warnings are silently discarded

- **Where:** Audit-Work-Program-Agent-UC-8-
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** work_program_generator.py sufficiency_check() starts from an empty list (line 279) and overwrites entry['sufficiency_flags'] (line 338), although the prompt asks the model to fill sufficiency_flags (line 134). Warnings the model raised never reach the auditor.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** work_program_generator.py:279 starts from an empty list and :338 overwrites the model's sufficiency_flags requested at :134.
- **Why it matters:** Warnings the AI raised about weak test steps never reach the auditor.
- **Fix:** Merge the model's flags with the rule-based flags instead of replacing them, and record where each flag came from.

#### Model JSON output is not validated against a schema

- **Where:** Finding-analysis
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** agent/audit_agent.py parses the model's JSON (around line 97) and uses it without schema validation. Injected document text can drop findings, invent a source file or set an unexpected priority value.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** agent/audit_agent.py around :97 uses the parsed JSON without checks.
- **Why it matters:** An injected document can make findings disappear or invent sources without any error.
- **Fix:** Validate the JSON: source must be one of the uploaded files, priority must be Hoog, Middel or Laag, unknown keys dropped; otherwise reject and flag.

#### Documents marked validated by file name only

- **Where:** PBC-Assistant-Isabelle---IA-AI-Hackathon
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** Delivered PBC documents are accepted as validated based on their file name, without checking their content.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** Delivered documents are accepted based on their file name.
- **Why it matters:** A wrong document with the right name is accepted as audit evidence.
- **Fix:** Validate the content of each document against the request, and require approval before any email is sent to the auditee.

#### Invented quotes only soft-flagged, verdict still returned

- **Where:** Track-2-Evidence-Collection-Extraction
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** When a quote in the model's answer is not found in the source document, the evidence check flags it but the compliance verdict is still returned unchanged.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** The evidence check flags quotes not found in the document but returns the verdict unchanged.
- **Why it matters:** A compliance verdict can rest on a quote the AI made up.
- **Fix:** Downgrade the verdict to 'Insufficient evidence' or block it when any supporting quote is not found verbatim.

#### Cut-off model output silently drops later findings

- **Where:** Vendor_Guard
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** When the model's output is truncated, findings after the cut are dropped and only a log warning is written; the report does not say it is incomplete.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** When the AI output is truncated, later findings are dropped with only a log warning.
- **Why it matters:** A vendor risk report can look complete while findings are missing.
- **Fix:** Mark the run as incomplete in the report and outputs, or retry, when the output was cut off.

#### Hallucination check never blocks and under-rates flagged claims

- **Where:** hallucination-detection-agent
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** hallucination/aggregator.py aggregate() always returns blocked: False (line 57). A claim judged LIKELY_HALLUCINATED with Medium confidence does not raise the risk; risk is HIGH only for High-confidence verdicts and MEDIUM only with two or more unverified claims, so one likely-hallucinated plus one unverified claim scores LOW.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** hallucination/aggregator.py:57 'blocked': False always; :42-52 only High-confidence hallucinations raise the risk.
- **Why it matters:** A finding with a likely invented claim can still be rated LOW risk and pass.
- **Fix:** Count any likely-hallucinated claim as at least MEDIUM, and set blocked: True on HIGH so the finding cannot be released without a person.

#### Blank quantity or price is treated as a MATCH

- **Where:** three-way-match-audit
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** In an offline probe of the matcher with its own sample format, an invoice line with an empty quantity or price produced MATCH instead of a failure.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** A helper's probe with the app's own sample format: an empty quantity or price produced MATCH.
- **Why it matters:** An invoice with missing amounts passes the three-way match control.
- **Fix:** Treat missing or unparseable values as FAIL, never as a match.

#### Refusal fallback to another model is on by default

- **Where:** Executive-Summary-Writer
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** scripts/llm.py line 28 sets USE_FALLBACKS from USE_REFUSAL_FALLBACKS with default '1'. A request refused by a safety classifier is re-run on a fallback model, so audit content can be processed by a model other than the one the auditor configured, without opt-in.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** scripts/llm.py:28 USE_FALLBACKS defaults to '1'.
- **Why it matters:** Audit material can be processed by a different AI model than the one the auditor configured, without anyone choosing that.
- **Fix:** Default the fallback to off, and record the model that actually answered in the trace and output.

#### Free-text domain accepted into the report header

- **Where:** Executive-Summary-Writer
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** At the report header domain question any reply that is not one of the listed options is accepted as the domain name. In an offline run the reply 'yes' was accepted and recorded as the domain.
- **How we found it:** We ran the agent offline (no real AI calls) and saw it happen.
- **Evidence:** In our offline run the reply 'yes' was accepted and recorded as the audit domain.
- **Why it matters:** Wrong or injected text ends up in the official report header.
- **Fix:** Accept only the listed options, or ask the user to confirm a typed domain before it is used.

#### Dry run prints a canned audit report with no label

- **Where:** llm_owasp
- **Risk:** Low. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** The dry-run mode prints a pre-written audit report that is not labelled as sample output, so it can be mistaken for a real assessment.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** The dry-run mode prints a pre-written report that is not marked as sample output.
- **Why it matters:** A sample can be mistaken for a real security assessment.
- **Fix:** Label dry-run output clearly as sample data and never write it where real reports go.

### 4. Secrets and confidential data exposed (2)

API keys and personal data must stay on the server and out of pages, files and logs. This is today's queued attack 'leaking secrets through outputs'.

#### PII masking misses names in free-text fields

- **Where:** GDPR-AI-Audit-Agent
- **Risk:** High. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** In an offline test, personal names placed in the approver, submitted_by and description fields were not masked: masking is driven by field names, not by scanning content.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** A helper's offline test put names in approver, submitted_by and description fields; they were not masked.
- **Why it matters:** Personal data leaks into outputs of a tool meant to protect it.
- **Fix:** Scan free text for names and other identifiers, and fail closed when masking cannot be confirmed.

#### Anthropic API key stored in a plaintext config file

- **Where:** Policy-to-Controls-Extractor
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** services/config.py (line 14) writes an anthropic api_key field into the P2C.conf config file, and agent.py reads the key from that file and passes it to the client (lines 64, 180). The key sits in plain text next to the project and is easy to commit or share by mistake.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** services/config.py:14 writes an anthropic api_key field into P2C.conf; agent.py:64 and :180 read it from there.
- **Why it matters:** The key sits in a file next to the project, easy to commit or share by mistake.
- **Fix:** Read the key only from an environment variable or secret store; keep it out of config files.

### 5. Keys left in the project history (3)

A key that was ever committed stays in the git history even after it is deleted from the files. Anyone with access to the repo can still read it, so it must be treated as leaked.

#### Anthropic API key committed to git history

- **Where:** ExecGRC
- **Risk:** Critical. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** Anthropic API key (sk-ant-api03 format, 108 chars, high entropy) assigned to ANTHROPIC_API_KEY in .env.example, added in the initial commit 22177ad (2026-05-19). The file was deleted in commit 5a80ff3 the same day, so it is NOT in current HEAD (b162683), but the commit is still reachable from main and origin/main. Masked preview: sk-a...(108 chars). Different key from the Team-HighTable one.
- **How we found it:** We downloaded the full git history of every in-scope repo and searched every past change for key patterns. Values were masked and never tested.
- **Evidence:** Commit 22177ad (2026-05-19), .env.example line 23: a real-format key (sk-ant-api..., 108 characters), deleted later in 5a80ff3. Re-checked by us, masked.
- **Why it matters:** A real key in an 'example' file is copied by everyone who sets up the project, and it stays recoverable.
- **Fix:** Revoke and rotate this Anthropic key now in the Anthropic console. Deleting the file did not remove it: rewrite history with git filter-repo and force-push, or treat the key as burned. Keep only placeholder values in .env.example and add a secret scan (for example gitleaks) on every push.

#### Anthropic API key committed to git history

- **Where:** Team-HighTable
- **Risk:** Critical. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** Anthropic API key (sk-ant-api03 format, 108 chars, high entropy) assigned to ANTHROPIC_API_KEY in backend/.env, added in commit 1294181 (2026-03-10). The file was untracked by commit ea1d1ec the same day, so it is NOT in current HEAD (417cc8a), but the commit is still reachable from main and origin/main. Masked preview: sk-a...(108 chars).
- **How we found it:** We downloaded the full git history of every in-scope repo and searched every past change for key patterns. Values were masked and never tested.
- **Evidence:** Commit 1294181 (2026-03-10) added backend/.env with a real-format key (sk-a..., 108 characters). The file was untracked later (ea1d1ec) but stays in history.
- **Why it matters:** Anyone with read access to the repo can recover the key and run up AI costs or read data in that account.
- **Fix:** Revoke and rotate this Anthropic key now in the Anthropic console. Remove backend/.env from history with git filter-repo and force-push, or treat the key as burned. Add a secret scan (for example gitleaks) on every push and keep .env in .gitignore.

#### TeamMate API key committed to git history

- **Where:** Team-HighTable
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** TeamMate API key (44 chars, high-entropy random value) assigned to TEAMMATE_API_KEY in backend/.env, added in the same commit 1294181 (2026-03-10). Untracked in ea1d1ec, so NOT in current HEAD (417cc8a), but still reachable from main and origin/main. Masked preview: P6ja...(44 chars).
- **How we found it:** We downloaded the full git history of every in-scope repo and searched every past change for key patterns. Values were masked and never tested.
- **Evidence:** Same commit 1294181, backend/.env: a TeamMate+ API key (P6ja..., 44 characters).
- **Why it matters:** TeamMate+ holds audit working papers; a leaked key can expose real audit files.
- **Fix:** Revoke and rotate this TeamMate API key now with the TeamMate administrator. Remove backend/.env from history with git filter-repo and force-push, or treat the key as burned. Add a secret scan (for example gitleaks) on every push.

### 6. Web apps open wider than needed (15)

Several agents run a small web server. Debug mode, listening on every network, allowing any website to call it, or taking file paths and web addresses from the request make them easy to misuse. This is today's queued attack 'misuse of tool permissions'.

#### Server holding a GitHub token accepts requests from any website

- **Where:** Agent-Auditor
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** server/server.py line 1015 enables CORSMiddleware with allow_origins ['*'], all methods and all headers, on a local server that reads the user's GITHUB_TOKEN or GH_TOKEN (line 110). Any web page open in the same browser can call its endpoints and act with the user's GitHub access.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** server/server.py:1015 CORSMiddleware(allow_origins=['*'], all methods, all headers); :110 reads GITHUB_TOKEN or GH_TOKEN.
- **Why it matters:** Any web page open in the same browser can use the auditor's GitHub access through this server.
- **Fix:** Allow only the app's own origin, require a per-session token on state-changing endpoints, and bind to 127.0.0.1.

#### HTML report rendered with autoescaping off

- **Where:** Finding-analysis
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** report/report_generator.py line 16 renders the HTML report with a bare jinja2 Template, which has autoescaping off. Model output, which uploaded documents can influence, is placed into report.html, so any HTML or script in it becomes active when the auditor opens the report.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** report/report_generator.py:16 renders with a bare jinja2 Template (autoescape off).
- **Why it matters:** Text from the AI, which uploaded documents can steer, runs as code in the auditor's browser when the report is opened.
- **Fix:** Render with a jinja2 Environment using autoescape=True (select_autoescape), and escape model text before it goes to the PDF generator.

#### Anyone on the network can replace the OWASP review criteria from any URL

- **Where:** OWASP-top-10-LLM-assessment
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** app.py lines 1202-1210: POST /owasp-update reads url from the JSON body and passes it to update_owasp_definitions (review_agent.py line 153). That function calls urllib.request.urlopen(url) (line 161) with no scheme or host allowlist and overwrites the OWASP definitions file that drives the review (line 180) after only a key-presence check. The Flask app has no authentication and listens on 0.0.0.0 (app.py line 1220). Anyone who can reach the port can point the tool at their own JSON and silently change the criteria every later review uses; urlopen also accepts file:// and internal http hosts (SSRF). The copy in agent-reviewer/app.py line 1203 has the same flaw.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** app.py:1202-1210 /owasp-update takes 'url' from the request body; review_agent.py fetches it (urlopen) and overwrites the OWASP definitions file; the app listens on 0.0.0.0 with no login (app.py:1220). Re-checked by us.
- **Why it matters:** Someone on the same network can quietly rewrite the rules this reviewer uses to judge other agents, so unsafe agents pass.
- **Fix:** Ignore any url in the request and only fetch the fixed OWASP_UPDATE_URL over https, verifying a pinned hash or signature before saving. Bind to 127.0.0.1 and require authentication for any route that changes state.

#### Stored cross-site scripting through the deadline and reminder date fields

- **Where:** PBC-Assistant-Isabelle---IA-AI-Hackathon
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** static/index.html line 729 inserts item.deadline into the table HTML without escaping (getDeadlineHTML returns <div class="deadline-date">${deadline}</div>), and line 640 does the same for item.last_reminder_date; the result is assigned to tbody.innerHTML (line 628). Both values are free strings accepted from the API: deadline in PBCItemCreate (app.py line 226, POST /api/pbc) and last_reminder_date in PBCItemUpdate (app.py line 237, PUT /api/pbc/{id} at line 268). The API has no authentication, so anyone who can reach it can store a value such as an <img onerror> payload that runs script in the coordinator's browser.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** static/index.html:729 puts '${deadline}' into the page unescaped (re-checked by us); :640 the same for reminders; values come from app.py:226 and :237 with no login.
- **Why it matters:** Text saved once runs as code in every auditor's browser that opens the PBC list.
- **Fix:** Escape every value with the existing esc() helper before inserting it (lines 640 and 729), and validate deadline and last_reminder_date as ISO dates on the server.

#### Copied OWASP reviewer lets any caller overwrite its criteria from any URL

- **Where:** SAAF-Project
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** tools/scripts/owasp-agent-reviewer/app.py lines 994-1001: POST /owasp-update takes url from the request body and calls update_owasp_definitions(url) (review_agent.py line 130), which fetches it with urllib.request.urlopen (line 138) and overwrites owasp_llm_top10.json (line 157) that the reviewer loads as its criteria. The Flask app has no authentication and runs on host 0.0.0.0 (app.py line 1012), so anyone on the network can swap the review criteria or use the server to fetch internal or file:// URLs.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** tools/scripts/owasp-agent-reviewer/app.py:994-1001 and review_agent.py:138, :157; listens on 0.0.0.0 (app.py:1012).
- **Why it matters:** The same flaw lives on in a copy inside the central SAAF repo; fixing one copy is not enough.
- **Fix:** Remove the url parameter and only fetch the fixed https source with a pinned hash or signature check; bind to 127.0.0.1 and require authentication for the update route.

#### GET request to /api/seed wipes all workpapers and tickets without any check

- **Where:** SAAF-circuit-breaker
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** src/app/api/seed/route.ts lines 11-14 export a GET handler that calls seedAll() with no session or token check. seedAll (src/lib/persist.ts lines 34-44) deletes every row in ticketEvents, checkpoints, workpapers, rehearsalRuns, forgeScans, tickets, personas and policies before re-inserting demo data. Any visitor, crawler, link preview or an <img src="/api/seed"> on another site can erase the audit trail and workpapers.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** src/app/api/seed/route.ts exports GET calling seedAll(); src/lib/persist.ts:34-44 deletes tickets, checkpoints, workpapers, runs, scans, personas and policies. Re-checked by us.
- **Why it matters:** Opening one link, or a browser prefetching it, erases the verified workpapers this tool exists to protect.
- **Fix:** Remove the GET handler, keep seeding as a POST that requires an admin secret or is disabled outside development, and never delete audit records from a web route.

#### Plan viewer forwards the server GitHub token to any GitHub API path

- **Where:** saaf-portal
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** src/app/api/plan-content/route.ts lines 9-30: session and slug come from the query string and are placed unencoded into `https://api.github.com/repos/SAAF-Project/SAAF-Project/contents/plans/${session}/${slug}.md`, which is fetched with Authorization: Bearer GITHUB_PAT and the raw response is returned to the caller. Because "../" segments are normalised by the URL parser and "?" moves the ".md" suffix into the query, any signed-in org member can make the server call any GitHub API GET endpoint with the server's token (for example other private repositories the PAT can read) and see the result.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** src/app/api/plan-content/route.ts:9-30 puts query values unencoded into a GitHub API URL fetched with the server's GITHUB_PAT; '../' and '?' reach other endpoints.
- **Why it matters:** Any signed-in member can use the portal's own GitHub token to read things it can see, beyond the plans it was meant for.
- **Fix:** Validate session and slug against a strict pattern (letters, digits, dash) or a list of known plans, and encode each path segment with encodeURIComponent before building the URL.

#### SharePoint site URL taken from the form without an allowlist

- **Where:** Finding-analysis
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** The SharePoint site URL, folder and credentials go from the form (app.py lines 49-53) straight into the connector (parsers/sharepoint_connector.py lines 35-36). There is no scheme or host allowlist, so the server can be pointed at an arbitrary address and send the supplied credentials there.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** app.py:49-53 passes the form's site URL and credentials into parsers/sharepoint_connector.py:35-36.
- **Why it matters:** The server can be pointed at any address and send the user's SharePoint credentials there.
- **Fix:** Accept https only and *.sharepoint.com hosts only; add size and count limits on downloaded files.

#### Flask review portals run with debug=True

- **Where:** OWASP-top-10-LLM-assessment
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** prototype/app.py line 30 and project_2026-03-24/app.py line 30 start the Flask app with app.run(debug=True), which shows stack traces and an interactive debugger console to the browser.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** prototype/app.py:30 and project_2026-03-24/app.py:30 app.run(debug=True).
- **Why it matters:** Errors show internal details and a debugger console in the browser.
- **Fix:** Read debug from an environment variable that defaults to off.

#### Repo fetch clones any URL or local path given in the request

- **Where:** OWASP-top-10-LLM-assessment
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** app.py lines 1136-1186: POST /fetch-repo takes url from the JSON body and runs subprocess.run(["git","clone","--depth","1", url, tmp_dir]) (line 1146) with no scheme or host check and no "--" before the url, then returns the text of every matching file in the clone. With the server on 0.0.0.0 and no authentication (line 1220), a network caller can make the server clone from internal git hosts (SSRF) or from a local repository path on the server and read its contents back; a url starting with "-" is parsed as a git option. Same code in agent-reviewer/app.py line 1148.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** app.py:1136-1186 runs 'git clone' (:1146) on a URL from the request body with no check and returns file contents.
- **Why it matters:** The server can be made to fetch from internal addresses or read local folders and hand back their files.
- **Fix:** Accept only https://github.com/<owner>/<repo> URLs that match a strict pattern, put "--" before the url in the git command, and bind the app to 127.0.0.1 with authentication.

#### Web server bound to all interfaces with auto-reload

- **Where:** PBC-Assistant-Isabelle---IA-AI-Hackathon
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** run.py line 4: uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True). The app listens on every network interface and runs in development auto-reload mode.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** run.py:4 uvicorn.run(..., host='0.0.0.0', reload=True).
- **Why it matters:** Anyone on the same network can reach the app.
- **Fix:** Bind to 127.0.0.1 by default and enable reload only through an explicit development flag.

#### API with no login allows any website to read and delete PBC data

- **Where:** PBC-Assistant-Isabelle---IA-AI-Hackathon
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** app.py lines 30-36 add CORSMiddleware with allow_origins ["*"], allow_credentials True and all methods and headers. No route checks who is calling: DELETE /api/pbc/{item_id} (line 280), DELETE /api/documents/{file_id} (line 415), PUT /api/pbc/{item_id} (line 268) and GET /api/documents/{file_id}/download (line 433). Any web page the auditor opens can call the local API from the browser, read the PBC list and evidence files, and change or delete them. This is separate from the already reported 0.0.0.0 binding: it works even when the server only listens on localhost.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** app.py:30-36 CORS '*' with credentials; delete routes :280 and :415, update :268, download :433, none with a login.
- **Why it matters:** Any web page open in the same browser can read, change or delete the audit's document requests.
- **Fix:** Restrict allow_origins to the app's own origin, drop allow_credentials, and add authentication to every data-changing and download route.

#### Backend open to everyone when no key is set, with CORS *

- **Where:** Team-HighTable
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** When no backend key is configured the backend accepts all callers, and it allows cross-origin requests from any site.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** With no backend key configured the backend accepts every caller and allows any website.
- **Why it matters:** A missing setting silently opens the backend to anyone.
- **Fix:** Fail closed when no key is configured and restrict CORS to the extension's origin.

#### Web server bound to all interfaces with auto-reload

- **Where:** Track-4-Audit-Report-Generator
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** run.py line 4: uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True). The app listens on every network interface (reachable by anyone on the same network) and runs in development auto-reload mode.
- **How we found it:** Our scanner Red Pencil flagged it across all 47 in-scope repos; we then read the code to confirm.
- **Evidence:** run.py:4 uvicorn.run(..., host='0.0.0.0', reload=True).
- **Why it matters:** Anyone on the same network (a hackathon, a hotel, an office) can reach the app.
- **Fix:** Bind to 127.0.0.1 by default and enable reload only through an explicit development flag.

#### Flask app runs with debug=True and returns tracebacks to the browser

- **Where:** Finding-analysis
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** app.py line 218 starts the app with app.run(debug=True, port=5000, threaded=True), enabling the Werkzeug debugger and reloader, and the analysis stream sends the last 500 characters of the Python traceback to the client on any error (around line 183). The form handles a Claude API key and SharePoint username and password (lines 41-52). The server binds to localhost and the debugger is PIN protected, which limits exposure.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** app.py:218 app.run(debug=True); app.py:183 returns traceback text to the browser.
- **Why it matters:** Internal details leak to the browser when something fails.
- **Fix:** Read debug from an environment variable that defaults to off, and return a generic error message to the client while logging the traceback on the server.

### 7. Other risky code (5)

Patterns that let input run commands, load unsafe files, switch off security checks or inject formulas into spreadsheets.

#### Work program Excel writes model and RCM text without formula guarding

- **Where:** Audit-Work-Program-Agent-UC-8-
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** work_program_generator.py to_excel (line 568) appends rows with ws.append at lines 606 and 620 containing model-generated test steps, methodology, evidence and pass criteria, plus control text from the input RCM. openpyxl turns any string starting with "=" into a formula, and nothing in the file strips or escapes such values. A manipulated RCM or model output can place a working formula in the work program the auditor opens.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** work_program_generator.py:606 and :620 write model and RCM text into Excel cells unguarded.
- **Why it matters:** Text from the AI or the risk matrix can become a live formula in the work program.
- **Fix:** Escape strings that begin with =, +, - or @ (prefix an apostrophe) or force string cells to data_type "s" before saving the workbook.

#### Model text written to Excel can become live formulas

- **Where:** Policy-to-Controls-Extractor
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** services/write_output.py lines 66-68 write every field of each extracted control (control_to_row, lines 30-40: who, what, why, how, source quotes, open questions) with ws.cell(value=value). openpyxl stores any string that starts with "=" as a formula, and these fields come from the model's reading of the policy document (agent.py line 112 calls write_xlsx). A crafted policy can make a cell start with "=" so the reviewer's Excel runs a formula such as HYPERLINK or WEBSERVICE when the file is opened.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** services/write_output.py:66-68 writes model text into cells; openpyxl stores strings starting with '=' as formulas.
- **Why it matters:** A policy containing '=HYPERLINK(...)' can become a live formula in the auditor's spreadsheet.
- **Fix:** Before writing, prefix any string starting with =, +, - or @ with an apostrophe, or set cell.data_type to "s" for string values (as Vendor_Guard does in synthesizer/sanitize.py).

#### Skill fetches extra skills from the internet at run time

- **Where:** agent-rogue-risk-assessor
- **Risk:** Medium. **Verified:** no. **Status:** Open. Fix suggested.
- **What is wrong:** The skill instructions tell the coding assistant to install further skills from skills.sh while running, so what runs depends on a third-party site at that moment.
- **How we found it:** A helper agent found it while running or probing the agent offline. We did not re-check it line by line, so it is marked verified: no.
- **Evidence:** The skill instructions tell the coding assistant to install more skills from skills.sh while running.
- **Why it matters:** What runs depends on a third-party website at that moment.
- **Fix:** Pin or vendor the needed skills, or drop the runtime install.

#### CSV export of SOC report and model text has no formula guard

- **Where:** CUEC_Crosscheck
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** cuec_crosscheck.py write_csv (lines 262-270) writes cuec_description (taken from the vendor SOC report), org_control_description and the model's rationale with csv.DictWriter and no escaping. A value starting with =, +, - or @ is treated as a formula when the CSV is opened in Excel.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** cuec_crosscheck.py:262-270 writes SOC report and model text to CSV unguarded.
- **Why it matters:** Opening the CSV in Excel can run a formula that came from a vendor's report.
- **Fix:** Prefix any cell value that starts with =, +, - or @ with an apostrophe before writing the CSV.

#### Tailwind loaded from CDN with no pinned version or integrity check

- **Where:** website
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** index.html line 53 loads <script src="https://cdn.tailwindcss.com"> with no version and no integrity attribute. Whatever that third-party host serves at load time runs with full access to the page.
- **How we found it:** We searched all repos for risky code patterns, then read each hit to confirm it is reachable.
- **Evidence:** index.html:53 loads Tailwind from a CDN with no version pin or integrity hash.
- **Why it matters:** If the CDN serves something else, the SAAF website runs it.
- **Fix:** Build Tailwind into a static CSS file at build time, or pin an exact version and add an integrity hash with crossorigin.

### 8. Can the agent prove what it did? (25)

An auditor must be able to re-perform an agent's work: which documents it read, what it asked the AI, what the AI answered, which path it took and who approved what. Gaps here mean a result cannot be evidenced or challenged. We checked 25 agents against a 10-point checklist: none keeps a complete, tamper-evident record; 15 keep a partial record and 10 keep almost nothing. Closest to good: ExecGRC (hash-chained step log and output hashes) and joiners-movers-leavers-agent. Full matrix: notes/traceability.md (5 agents with their own logging were not reviewed for lack of time).

#### Audit report generated with no record at all

- **Where:** Track-4-Audit-Report-Generator
- **Risk:** High. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** /api/generate-report (app/main.py lines 40-118) sends the auditor's inputs to the model (app/services/claude_service.py lines 54-59), fills the Word template with the parsed reply and returns it as a download. No inputs, prompt, model, raw reply, timestamp or user are saved anywhere; there is no logging in the app. The report contains findings, an executive summary and a conclusion.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** /api/generate-report (app/main.py lines 40-118) sends the auditor's inputs to the model (app/services/claude_service.py lines 54-59), fills the Word template with the parsed reply and returns it as a download. No inputs, prompt, model, raw reply, timestamp or user are saved anywhere; there is no logging in the app. The report contains findings, an executive summary and a conclusion.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Save a run record for every report (input and template hashes, prompt, model and settings, raw reply, auditor, UTC timestamp, run id) and stamp the run id and model in the generated document.

#### Reviewer decisions logged without who made them, in an editable log

- **Where:** Agent-Auditor
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** POST /log (server/server.py lines 1486-1493) accepts accept, reject and manual score events with whatever the browser sends; log_event (lines 378-391) appends them to actions.log.jsonl with no user, chain or signature and only warns if the write fails. The secret scan also copies the full matching line of each secret into audit-trail.cache.json (lines 465-477, 1437).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** POST /log (server/server.py lines 1486-1493) accepts accept, reject and manual score events with whatever the browser sends; log_event (lines 378-391) appends them to actions.log.jsonl with no user, chain or signature and only warns if the write fails. The secret scan also copies the full matching line of each secret into audit-trail.cache.json (lines 465-477, 1437).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Record the logged-in reviewer on each decision, hash-chain the action log, and mask secret values before writing them.

#### Run log overwritten on every run and input files not identified

- **Where:** Audit-Work-Program-Agent-UC-8-
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** work_program_generator.py keeps prompts and raw replies per control (lines 171-238), but the log is written to <output>_log.json opened with 'w' (lines 805-808) and the default output name is fixed, so each run replaces the earlier evidence. The run log (lines 171-181) has no input file path or hash, and no hash or signature.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** work_program_generator.py keeps prompts and raw replies per control (lines 171-238), but the log is written to <output>_log.json opened with 'w' (lines 805-808) and the default output name is fixed, so each run replaces the earlier evidence. The run log (lines 171-181) has no input file path or hash, and no hash or signature.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Give each run its own folder with a run id, record input paths with SHA-256, and hash the log.

#### Code that writes the audit trail is not published

- **Where:** Compliance-Audit-Agent
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** README.md lines 75-77 say each stage saves its prompt and raw model output, but .gitignore excludes scripts/*.py apart from three entry files, and orchestration.py line 59 imports a utils module that is missing from the repo, so the record cannot be checked. The model id comes only from an environment variable (claude_config.py lines 13-14) with no evidence it is written to output, SDK retries (claude_config.py lines 17, 27-29) are not recorded, and raw results are off by default (orchestration.py lines 43-47).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** README.md lines 75-77 say each stage saves its prompt and raw model output, but .gitignore excludes scripts/*.py apart from three entry files, and orchestration.py line 59 imports a utils module that is missing from the repo, so the record cannot be checked. The model id comes only from an environment variable (claude_config.py lines 13-14) with no evidence it is written to output, SDK retries (claude_config.py lines 17, 27-29) are not recorded, and raw results are off by default (orchestration.py lines 43-47).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Publish the logging code (or a manifest spec with a sample run), and write the model id, settings, retries and a hash of each input into the combined JSON by default.

#### Audit trail is off by default and skips failed or rejected runs

- **Where:** Compliance-Report-Generator
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** saaf/core/audit_trail.py writes a good per-run record (inputs, model, endpoint, settings, attempts, prompt SHA-256, UTC times, raw response; lines 102-119). But it is opt-in: agent.audit_trail is None by default (saaf/core/agent.py lines 60-61) and only set when --audit-trail-dir is passed (cli.py lines 154-155, 259-262). The record is written only after parsing and the grounding check pass (agent.py lines 107-136), so a run whose output was rejected or whose API calls failed leaves no record, and a failed write is only logged (audit_trail.py lines 142-144). The record itself carries no hash or signature.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** saaf/core/audit_trail.py writes a good per-run record (inputs, model, endpoint, settings, attempts, prompt SHA-256, UTC times, raw response; lines 102-119). But it is opt-in: agent.audit_trail is None by default (saaf/core/agent.py lines 60-61) and only set when --audit-trail-dir is passed (cli.py lines 154-155, 259-262). The record is written only after parsing and the grounding check pass (agent.py lines 107-136), so a run whose output was rejected or whose API calls failed leaves no record, and a failed write is only logged (audit_trail.py lines 142-144). The record itself carries no hash or signature.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Turn the audit trail on by default, also write a record (with the error and raw reply) for failed and rejected runs, and add a hash over the whole record or a signed manifest.

#### Web version keeps no run record; CLI trace omits prompts, input hashes and errors

- **Where:** Executive-Summary-Writer
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** The CLI saves a replayable trace (scripts/run_record.py lines 55-134; scripts/run.py lines 177-185 in the committed version) with file names, the configured model name, each call's task arguments and parsed output, and the manager's replies. Not recorded: the system prompt and the request actually sent, a hash of the audit material (excluded from each call at run_record.py line 81 and named only by file name at run.py line 182), the effort and thinking settings (scripts/llm.py lines 247-253), and the error that stopped a run (run.py lines 204-231 only print it; the trace just says incomplete). The web agent service builds the same graph per session (frontend/agent-service/app.py line 128) without TracingLLM and saves no trace at all.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** The CLI saves a replayable trace (scripts/run_record.py lines 55-134; scripts/run.py lines 177-185 in the committed version) with file names, the configured model name, each call's task arguments and parsed output, and the manager's replies. Not recorded: the system prompt and the request actually sent, a hash of the audit material (excluded from each call at run_record.py line 81 and named only by file name at run.py line 182), the effort and thinking settings (scripts/llm.py lines 247-253), and the error that stopped a run (run.py lines 204-231 only print it; the trace just says incomplete). The web agent service builds the same graph per session (frontend/agent-service/app.py line 128) without TracingLLM and saves no trace at all.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Use TracingLLM in the web service and save one trace per session; add SHA-256 of each material file, the system prompt version or hash, effort and thinking settings, the error that ended a run, and a run id shared by the trace and the output files.

#### Audit trail can be edited undetected and skips failed calls and image inputs

- **Where:** FieldworkOrchestration
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** agents/audit_trail.py records each Claude call with prompts, model, settings, raw reply, reasoning, tokens and run id (lines 102-119). But entries are plain JSON lines (_append, lines 211-216) with no hash or chain, so an edited or deleted line is not detectable. A call is recorded only when it succeeds (agents/claude_init.py line 229), so failed calls and the connection retries in _retry_on_connection_error (lines 146-161) leave no trace. Image inputs are replaced by a placeholder with only their length (claude_init.py lines 119-140) and no hash, so the pages the model saw cannot be identified.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** agents/audit_trail.py records each Claude call with prompts, model, settings, raw reply, reasoning, tokens and run id (lines 102-119). But entries are plain JSON lines (_append, lines 211-216) with no hash or chain, so an edited or deleted line is not detectable. A call is recorded only when it succeeds (agents/claude_init.py line 229), so failed calls and the connection retries in _retry_on_connection_error (lines 146-161) leave no trace. Image inputs are replaced by a placeholder with only their length (claude_init.py lines 119-140) and no hash, so the pages the model saw cannot be identified.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Chain each entry to the previous entry's hash (or sign it), record failed calls and retries as their own entries, and store a SHA-256 of every image and document sent to the model.

#### No record of prompts, model or raw output for the findings analysis

- **Where:** Finding-analysis
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** agent/audit_agent.py lines 39-45 send the system prompt and document content to the model with adaptive thinking. The streamed text (line 73) is parsed and discarded, and the report metadata (lines 100-103) holds only the file count, lookback and date. Prompts, model, settings and raw reply are not saved; on a parse error only the first 800 characters go to the browser (line 91).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** agent/audit_agent.py lines 39-45 send the system prompt and document content to the model with adaptive thinking. The streamed text (line 73) is parsed and discarded, and the report metadata (lines 100-103) holds only the file count, lookback and date. Prompts, model, settings and raw reply are not saved; on a parse error only the first 800 characters go to the browser (line 91).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Per upload_id, save a run.json with input file hashes, prompts sent, model and settings, the raw reply and a UTC timestamp, and print the model name in the report footer.

#### Hash-chained audit log is deleted after each web run

- **Where:** GDPR-AI-Audit-Agent
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** The chained log is well built (src/gdpr_agent/audit_logger.py lines 55-75, verify_chain lines 84-95), but the Streamlit app writes it into a tempfile.TemporaryDirectory that is removed as soon as processing ends (app.py lines 128-132). The only remaining copy is an optional browser download (app.py lines 205-211), which the user can edit before keeping. Entries record role, purpose and justification but no user identity (the role is a dropdown, app.py line 60), and there is no hash of the source dataset.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** The chained log is well built (src/gdpr_agent/audit_logger.py lines 55-75, verify_chain lines 84-95), but the Streamlit app writes it into a tempfile.TemporaryDirectory that is removed as soon as processing ends (app.py lines 128-132). The only remaining copy is an optional browser download (app.py lines 205-211), which the user can edit before keeping. Entries record role, purpose and justification but no user identity (the role is a dropdown, app.py line 60), and there is no hash of the source dataset.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Write the log to a persistent, access-controlled location, store or sign the final chain hash separately, and record the logged-in user and a hash of the input data.

#### PBC status changes, edits and deletions leave no history

- **Where:** PBC-Assistant-Isabelle---IA-AI-Hackathon
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** analyze_document overwrites record['analysis'] (app.py line 488) and moves a PBC item to validated on the AI conclusion (app.py lines 493-496) without recording the previous status. update_item and delete_item (app.py lines 266-286) change or remove items with no record of who, when or what changed. The model name is a hard-coded string (app.py line 486), not read from the response.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** analyze_document overwrites record['analysis'] (app.py line 488) and moves a PBC item to validated on the AI conclusion (app.py lines 493-496) without recording the previous status. update_item and delete_item (app.py lines 266-286) change or remove items with no record of who, when or what changed. The model name is a hard-coded string (app.py line 486), not read from the response.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Keep an append-only event log per PBC item (old and new status, actor, timestamp, analysis version) and never overwrite earlier analyses.

#### No record of model, prompts or run; reruns overwrite the output

- **Where:** Policy-to-Controls-Extractor
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** agent.py line 105 and services/segments.py line 111 only print the model. Prompts (agent.py lines 61-89, segments.py lines 95-125) are not saved, and the AI heading fallback failure is only printed (segments.py line 125). Outputs are written as <stem>.json and .xlsx (agent.py lines 111-112) with no timestamp, model or input hash, so a rerun overwrites the earlier result.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** agent.py line 105 and services/segments.py line 111 only print the model. Prompts (agent.py lines 61-89, segments.py lines 95-125) are not saved, and the AI heading fallback failure is only printed (segments.py line 125). Outputs are written as <stem>.json and .xlsx (agent.py lines 111-112) with no timestamp, model or input hash, so a rerun overwrites the earlier result.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Write a run manifest next to each output (source hash, model and header model, prompts, segmentation route, UTC timestamp, run id) and use run-specific file names.

#### No record of prompts, retrieved issues or model output for recommendations

- **Where:** Team-HighTable
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** backend/claude_client.py lines 126-128 log only the model name and the prompt and reply lengths to the console, and nothing is saved. When the model leaves out an issue, its relevance is silently set to 5 with a generic explanation (lines 155-160), and fallbacks are only printed (main.py lines 166, 176).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** backend/claude_client.py lines 126-128 log only the model name and the prompt and reply lengths to the console, and nothing is saved. When the model leaves out an issue, its relevance is silently set to 5 with a generic explanation (lines 155-160), and fallbacks are only printed (main.py lines 166, 176).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Write a record per request (id, time, model, prompt, retrieved issue ids and scores, raw reply) and mark any filled-in scores in the output.

#### Observability plan not implemented: no request ID, token use or raw reply kept

- **Where:** Track-2---IAM-final
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** observability_notes.md lines 25 and 27 promise a hash of the token map plus request ID, token usage, latency and model version per call. tools/scripts/access_review_agent.py logs only to the console (basicConfig, line 34), logs the model (line 208) and reply length (line 216), keeps the raw reply only at DEBUG (line 237) while the level is INFO, and overwrites findings.json (lines 268-270). The bart run summary (tools/scripts/bart/access_review_agent.py lines 432-439) omits the stale_days, match_key and exclusion settings used, and user_mapping.csv with real identifiers is written next to the findings (lines 497-503).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** observability_notes.md lines 25 and 27 promise a hash of the token map plus request ID, token usage, latency and model version per call. tools/scripts/access_review_agent.py logs only to the console (basicConfig, line 34), logs the model (line 208) and reply length (line 216), keeps the raw reply only at DEBUG (line 237) while the level is INFO, and overwrites findings.json (lines 268-270). The bart run summary (tools/scripts/bart/access_review_agent.py lines 432-439) omits the stale_days, match_key and exclusion settings used, and user_mapping.csv with real identifiers is written next to the findings (lines 497-503).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Implement the fields from the notes in a per-run JSONL file (request id, model, tokens, raw reply, input hashes, parameters) and store user_mapping.csv separately with restricted access.

#### Auditor accept or override logged without who or when

- **Where:** Track-2-Evidence-Collection-Extraction
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** compliance_qa_app.py lines 541-545 and 562-565 append the auditor's accept or override to audit-log.jsonl by reusing the AI verdict object. The record has no reviewer identity, and its timestamp is the AI call time set at compliance_qa.py line 311, not the decision time. session_id (compliance_qa.py line 90) is never set, the user prompt is not logged (lines 282-293), and the chmod 444 protection (line 397) is lifted by the tool itself (line 391) with no hashes.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** compliance_qa_app.py lines 541-545 and 562-565 append the auditor's accept or override to audit-log.jsonl by reusing the AI verdict object. The record has no reviewer identity, and its timestamp is the AI call time set at compliance_qa.py line 311, not the decision time. session_id (compliance_qa.py line 90) is never set, the user prompt is not logged (lines 282-293), and the chmod 444 protection (line 397) is lifted by the tool itself (line 391) with no hashes.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Record the reviewer identity and a decision timestamp, set a session or run id, hash the document text and prompt, and chain each log line to the previous line's hash.

#### Run step log kept in memory only; prompts and model replies not saved

- **Where:** Vendor_Guard
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** Run.emit (webui/server.py lines 86-91) appends routing decisions, per-agent errors and truncation warnings (forwarded by _RunLogHandler, lines 102-110) to an in-memory list that is never written to output/web/<run_id>, so it is lost when the server stops. complete() in agents/llm.py (lines 43-60) saves no prompts or replies, and the per-agent model constant (agents/orchestrator.py line 5) is not recorded. Input files are copied but not hashed (server.py lines 132-143).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** Run.emit (webui/server.py lines 86-91) appends routing decisions, per-agent errors and truncation warnings (forwarded by _RunLogHandler, lines 102-110) to an in-memory list that is never written to output/web/<run_id>, so it is lost when the server stops. complete() in agents/llm.py (lines 43-60) saves no prompts or replies, and the per-agent model constant (agents/orchestrator.py line 5) is not recorded. Input files are copied but not hashed (server.py lines 132-143).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Write events.jsonl, prompts, raw replies and the model id per agent into the run folder, with SHA-256 of each input file.

#### Retrieval fallback recorded wrongly; prompts, context and raw verdicts not kept

- **Where:** hallucination-detection-agent
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** hallucination/annotator.py line 55 records the retrieval backend from the RAG_BACKEND environment setting, while hallucination/rag.py lines 51-56 and 66-68 silently fall back to markdown files when ChromaDB fails, so the record can say chromadb when markdown was used. The JSONL log (annotator.py lines 63-75) keeps only finding id, counts, risk, blocked and warning; prompts, retrieved passages, the extractor model and the raw verifier reply are not kept.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** hallucination/annotator.py line 55 records the retrieval backend from the RAG_BACKEND environment setting, while hallucination/rag.py lines 51-56 and 66-68 silently fall back to markdown files when ChromaDB fails, so the record can say chromadb when markdown was used. The JSONL log (annotator.py lines 63-75) keeps only finding id, counts, risk, blocked and warning; prompts, retrieved passages, the extractor model and the raw verifier reply are not kept.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Record the backend actually used and why it fell back, the retrieved passages with source and hash, both model names, and the raw verifier reply.

#### Control verdicts saved without model, prompt, policy file or time

- **Where:** judging-found-controls
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** agent.py lines 174-175 write only control_id, found, page_no and paragraph. The model (line 24), policy path (line 145), prompt and time are missing, the raw reply is discarded on a parse error (lines 164-171), and the default output file judge_verdicts.json is overwritten on every run.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** agent.py lines 174-175 write only control_id, found, page_no and paragraph. The model (line 24), policy path (line 145), prompt and time are missing, the raw reply is discarded on a parse error (lines 164-171), and the default output file judge_verdicts.json is overwritten on every run.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Add a run header (run id, UTC time, model, max_tokens, SHA-256 of the PDF and controls file, prompt hash) and keep the raw reply for each control.

#### Report does not name the model or the files that were read

- **Where:** llm_owasp
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** owasp_llm_audit/auditor.py lines 216-234 keep neither the prompt nor the raw reply. report.py lines 24-37 record only the target and the date. The model (configurable, auditor.py line 173 and cli.py line 23) and any files skipped or cut off (collector.py lines 55-64) are not recorded.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** owasp_llm_audit/auditor.py lines 216-234 keep neither the prompt nor the raw reply. report.py lines 24-37 record only the target and the date. The model (configurable, auditor.py line 173 and cli.py line 23) and any files skipped or cut off (collector.py lines 55-64) are not recorded.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Write a run record next to the report with the model, a prompt hash, the files read with their hashes, any truncation, and the raw reply.

#### Match result and tolerances used are not saved

- **Where:** three-way-match-audit
- **Risk:** Medium. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** /match and /api/match (webapp/app/main.py lines 73-145) take price, quantity and total tolerances from the form, build the report and return it without saving it. MatchReport.to_dict (webapp/app/services/matcher.py lines 108-121) includes neither the tolerances nor file hashes, so a MATCH cannot be re-performed or linked to its inputs.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** /match and /api/match (webapp/app/main.py lines 73-145) take price, quantity and total tolerances from the form, build the report and return it without saving it. MatchReport.to_dict (webapp/app/services/matcher.py lines 108-121) includes neither the tolerances nor file hashes, so a MATCH cannot be re-performed or linked to its inputs.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Save each run (input file hashes, tolerances, verdict per line, timestamp, user) to an append-only log and show the tolerances on the result page.

#### Run log has no run ID, input hashes or tamper protection

- **Where:** CUEC_Crosscheck
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** cuec_crosscheck.py logs model, tokens, raw replies and completeness checks well (lines 173-205), but main() logs only input paths and sizes (lines 521-531), every run is appended to the same output/cuec_crosscheck.log with no run id (lines 512-519), only a 12-character prefix of the system prompt hash is kept (line 153) and the user prompt is not kept. The log is plain text, so edits are not detectable.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** cuec_crosscheck.py logs model, tokens, raw replies and completeness checks well (lines 173-205), but main() logs only input paths and sizes (lines 521-531), every run is appended to the same output/cuec_crosscheck.log with no run id (lines 512-519), only a 12-character prefix of the system prompt hash is kept (line 153) and the user prompt is not kept. The log is plain text, so edits are not detectable.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Add a run id to every line or use a per-run log file, log full SHA-256 of both input documents and of the full prompt, and add a hash chain or a final manifest hash.

#### Web audit log keeps only the rating and silently skips failed writes

- **Where:** OWASP-top-10-LLM-assessment
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** app.py lines 1105-1121 log time, file names, input hashes, model and rating, but not the review text, and a failed write is ignored (except OSError: pass), so the review exists only in the browser unless the user downloads it. Only a hash of the system prompt is kept (review_agent.py line 132).
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** app.py lines 1105-1121 log time, file names, input hashes, model and rating, but not the review text, and a failed write is ignored (except OSError: pass), so the review exists only in the browser unless the user downloads it. Only a hash of the system prompt is kept (review_agent.py line 132).
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Store the review (or its hash plus a copy) on the server for each run and stop with an error when the log cannot be written.

#### Original policy evidence file is moved, not copied

- **Where:** Policy-to-Controls-Extractor
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** agent.py line 113 calls shutil.move on the source policy file after processing, so the original evidence is removed from where the auditor placed it.
- **How we found it:** We read the code and confirmed the line ourselves.
- **Evidence:** agent.py:113 shutil.move on the source policy file.
- **Why it matters:** The original evidence disappears from where the auditor put it.
- **Fix:** Copy the file and leave the original untouched; record its hash so the evidence can be traced.

#### RCM approval and input files not recorded

- **Where:** RCM-Builder
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** The output of tools/scripts/rcm_builder.py (lines 1257-1263) has version, time, context, warnings and per-risk source references, but no input file paths or hashes (inputs are read at lines 1384-1386) and no approval block, although agent.yaml requires auditor approval before hand-off to UC8.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** The output of tools/scripts/rcm_builder.py (lines 1257-1263) has version, time, context, warnings and per-risk source references, but no input file paths or hashes (inputs are read at lines 1384-1386) and no approval block, although agent.yaml requires auditor approval before hand-off to UC8.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Add the SHA-256 of each input file, a run id and an approval block (approver, time, hash of the RCM).

#### Auditor score overrides stored without reason or name

- **Where:** agent-rogue-risk-assessor
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** skills/agent-rogue-risk-assessor/scripts/scan_repo.py lines 333-338 apply override values and store only the numbers. The reason and the person exist only in the report the assistant fills in by hand (SKILL.md line 33; assets/report_template.md lines 51-62), and the model used is recorded only if the assistant follows the template.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** skills/agent-rogue-risk-assessor/scripts/scan_repo.py lines 333-338 apply override values and store only the numbers. The reason and the person exist only in the report the assistant fills in by hand (SKILL.md line 33; assets/report_template.md lines 51-62), and the model used is recorded only if the assistant follows the template.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Require a reason and a reviewer for each override in the scanner input, refuse overrides without them, and put the hash of the scan JSON in the report.

#### Sign-off name is free text and not bound to the draft content

- **Where:** joiners-movers-leavers-agent
- **Risk:** Low. **Verified:** yes. **Status:** Open. Fix suggested.
- **What is wrong:** web/app.py lines 167-184 store a typed name, statement, time, input fingerprint and finding ids for the sign-off. There is no login and no hash of the draft that was approved, and events.jsonl (web/app.py lines 56-62) is a plain append file that can be edited without detection.
- **How we found it:** We reviewed each agent's logging against a 10-point audit-trail checklist (inputs, prompts, model, outputs, path, human decisions, run id, tamper evidence, replay, safe logging).
- **Evidence:** web/app.py lines 167-184 store a typed name, statement, time, input fingerprint and finding ids for the sign-off. There is no login and no hash of the draft that was approved, and events.jsonl (web/app.py lines 56-62) is a plain append file that can be edited without detection.
- **Why it matters:** Without this record an auditor cannot show what the agent read, asked, answered or decided, so its result cannot be evidenced, re-performed or challenged.
- **Fix:** Put a hash of draft.json in the sign-off, take the reviewer from a login, and chain the event log.

