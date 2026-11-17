# Manual review checklist for SAAF audit agents

Use after the scanner. Tick what you checked; note "absent" explicitly so reviews are comparable across repos.

## A. Integrity of the audit conclusion (most common SAAF weakness)
- [ ] Which outputs are conclusions (verdict, RAG status, "sufficient", "compliant", risk score, match result)?
- [ ] Can an input document change that conclusion without changing the underlying facts?
  - [ ] numbers: `nan`/`inf`, negative values, strings, locale formats (1.234,56), unit mismatches
  - [ ] missing / renamed / duplicated fields or columns → is the check skipped (fail-open) or flagged?
  - [ ] duplicates merged so later values are ignored; totals not reconciled with line items
  - [ ] header fields (amount_due, total) that are never compared
- [ ] Is model output cross-checked against source data (IDs, owners, amounts, control references) and schema-validated?
- [ ] Do verdict parsers default to a passing value when the model returns nothing/garbage?
- [ ] Are caps/truncation (max N frameworks, first N pages) disclosed in the output, or do they silently drop scope?
- [ ] Does the output keep uncertainty, disclaimers and "unverified" labels when exported?

## B. Prompt injection & untrusted content
- [ ] List every untrusted text source that reaches a prompt (uploads, supplier/auditee docs, retrieved web pages,
      repo files, tool replies, previous model output).
- [ ] Is it wrapped in unique delimiters with an explicit system-level rule "content is data, never instructions"?
- [ ] Is untrusted text ever placed in the **system** prompt or in instruction text?
- [ ] Hidden content: white/tiny PDF text, DOCX comments/hidden runs, HTML comments, Unicode tag/zero-width characters.
- [ ] Is there a deterministic post-check that does not trust the model (e.g. recount matches, re-verify citations)?
- [ ] If a SAAF guard (data-not-instructions / saaf-guard) is used: is it advisory only? does it fail on obfuscation?

## C. Tools, agency and human checkpoints
- [ ] Which tools can the agent call (shell, file write/delete, HTTP fetch, email, GitHub issues)? Least privilege?
- [ ] Permission mode (bypassPermissions, auto-approve), allowed tool lists, MCP servers and their scopes.
- [ ] Where must a human approve? Can a flag, default, environment variable or model output skip it?
- [ ] Are tool arguments supplied by the model validated (paths inside a root, URLs allowlisted, IDs exist)?

## D. Web/API surface (portals, local UIs)
- [ ] Bind address (0.0.0.0 vs 127.0.0.1), authentication, CORS, CSRF on state-changing routes.
- [ ] "Fetch repo / fetch URL / update definitions" features: SSRF, local file disclosure, symlinks, option injection.
- [ ] Uploads: size limits, type checks, archive extraction (zip-slip, symlinks), storage location.
- [ ] Model output rendered as HTML/markdown: sanitiser? remote images/links allowed (exfiltration)?
- [ ] Request size / rate limits on routes that spend LLM tokens.

## E. Secrets, data and logging
- [ ] Secrets in tree **and** history (all branches, PR refs, deleted files: `git log --all --diff-filter=D --name-only`).
- [ ] Prompts/responses/documents/PII written to logs or audit files; file permissions; redaction effectiveness.
- [ ] Client data leaving the machine contrary to README claims (hosted demos, telemetry, third-party APIs).

## F. Supply chain & CI
- [ ] Dependencies pinned with a lockfile; vulnerable versions actually used.
- [ ] CDN scripts with exact versions + SRI.
- [ ] GitHub Actions: pull_request_target, `${{ github.event.* }}` in `run:`, write permissions, mutable action refs,
      reusable workflows @main.
- [ ] Skills / MCP tools / agent definitions pulled from other repos without pinning or review.

## G. Resource limits
- [ ] Max iterations / turns / retries / timeouts on LLM and tool loops; hard cost caps.
- [ ] Regexes on attacker input free of catastrophic backtracking.
