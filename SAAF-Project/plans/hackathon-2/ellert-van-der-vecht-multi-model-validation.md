# Plan Template — SAAF Hackathon Submission

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | Mathijs Schouten (on behalf of Ellert van der Vecht) |
| **Organisation** | Schuberg Philis |
| **Session** | Hackathon 2 (Session 3) |
| **Type** | Skill |
| **Status** | Draft |

---

## 2. Problem Statement

AI agents and skills built by audit teams rely on a single model's output — which may contain errors, blind spots, or overconfident conclusions. In an audit context, where findings have real consequences, unchecked AI output is a risk. Multi-model validation is a lightweight quality gate: have a second Claude model review the output of the first. This cross-model peer review consistently surfaces issues the original model missed. The technique is model-agnostic, requires no additional tooling, and takes minutes to apply to any prompt or code output. This plan formalises multi-model validation as a shared SAAF skill and best practice, to be documented in the SAAF-Project repository.

---

## 3. Use-Case Type and Scope

**Audit domain:** AI Quality Assurance / Prompt Engineering — applicable across all audit domains

**Applicable standards:**

- IIA IPPF — Standard 1220 (Due Professional Care — quality of AI-assisted work)
- ISO 42001 — AI management system (quality assurance for AI outputs)

**In scope:**

- Documenting the multi-model validation technique as a reusable skill
- Providing prompt templates for cross-model code review and output review
- Adding the technique to `docs/` or `prompts/conventions/` in the SAAF-Project repo
- Guidance on when to apply it (code generation, finding drafts, control extractions)

**Out of scope:**

- Automated CI integration (documenting the manual technique is the MVP)
- Quantitative benchmarking of Opus vs. Sonnet review quality

---

## 4. SAAF 4-Pillar Mapping

| Pillar | What you will produce or reuse |
|---|---|
| **Prompts** | Peer-review prompt template: "Review the following output from [Model A] for correctness, completeness, and audit appropriateness." — add to `prompts/conventions/` |
| **Tools** | No new code — technique applies to any Claude-powered tool in the repo |
| **Regulatory** | IIA Standard 1220 (Due Professional Care) — AI outputs require quality review before use |
| **Outputs** | Best-practice guide in `docs/tips/multi-model-validation.md` (from [TipsAndTricks repo](https://github.com/SAAF-Project/TipsAndTricks)); peer-review prompt template |

---

## 5. Prompts

### System prompt (draft — peer reviewer)

```
You are a critical reviewer. You will receive output produced by another AI model
(Claude Opus or Claude Sonnet) performing an audit-related task.
Your role is to identify: errors, omissions, unsupported conclusions, vague language,
and any place where the output could mislead an auditor.
Be specific — cite the exact part of the output you are questioning.
Do not simply approve the output. If you find nothing to challenge, explain why
each part of the output is correct and complete.
```

### Example user prompts

**Prompt 1 — code review (Sonnet reviews Opus output):**
```
The following Python function was written by Claude Opus to extract PII from audit records.
Review it for correctness, edge cases, and security issues.

[paste function code]
```

**Prompt 2 — finding review (Opus reviews Sonnet output):**
```
The following audit finding was drafted by Claude Sonnet.
Review it for: factual accuracy, logical consistency, appropriate risk rating,
and whether the recommendation is actionable.

[paste finding]
```

**Intended file location:** `prompts/conventions/multi-model-validation.md`

---

## 6. Tools and Techniques

### Approach

The multi-model validation technique is applied manually in two steps:

1. **Generate** — use Model A (e.g. Claude Opus) to produce the output (code, finding, control extraction, prompt)
2. **Review** — submit the output to Model B (e.g. Claude Sonnet) with a reviewer system prompt. Model B identifies errors, omissions, and weak reasoning.
3. **Decide** — the auditor reviews Model B's critique and accepts, rejects, or revises the original output

The technique works in both directions: Opus reviewing Sonnet output is effective for catching reasoning errors; Sonnet reviewing Opus output is effective for catching implementation bugs. The reviewer is not required to accept the original output — the discipline of asking "what would the other model say?" improves output quality even when the reviewer finds nothing significant.

### Example script or pseudocode

```python
# Manual workflow — no code required
# Step 1: Generate with Model A
response_a = client.messages.create(
    model="claude-opus-4-6",
    system=TASK_PROMPT,
    messages=[{"role": "user", "content": task_input}]
)

# Step 2: Review with Model B
response_b = client.messages.create(
    model="claude-sonnet-4-6",
    system=REVIEWER_PROMPT,
    messages=[{"role": "user", "content": response_a.content[0].text}]
)

# Step 3: Human decision — accept, revise, or reject
```

**Tech stack used:** Claude API (claude-opus-4-6 + claude-sonnet-4-6), any Claude interface (API, Claude Desktop, Claude Code)

**Intended file location:** `docs/tips/multi-model-validation.md` in the SAAF-Project repo

---

## 7. Regulatory and Policies

### Applicable standards

| Standard | Relevant controls |
|---|---|
| IIA IPPF Standard 1220 | Due Professional Care — AI-generated outputs require human and quality review |
| ISO 42001 | AI management — quality assurance for AI system outputs |

### Claude / AI tool usage notes

The peer-review prompt should not include real audit evidence or personal data unless the original task output already handles that appropriately. The reviewer sees the same content as the original model — apply the same data handling rules.

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts
- [x] No runtime `pip install`
- [x] No real audit evidence, credentials, or personal data committed
- [x] API keys loaded from environment variables only

---

## 8. Output Format and Examples

**Format:** Markdown (best-practice guide + prompt template)

**Schema reference:** Not a findings schema. The technique is a quality gate for any output format.

### Synthetic example output

```
Peer review of Claude Opus finding draft F-001:

Issue 1 — Observation lacks specificity: "15 out of 50 sampled accounts" — which
population was sampled? The finding does not state whether this is a statistical
or judgement sample, which affects the conclusion's supportability.

Issue 2 — Risk rating: "High" is appropriate given the finding, but the rationale
should reference a specific risk (e.g. unauthorized access by former employees)
rather than just the control failure.

Issue 3 — Recommendation: "implement automated deprovisioning" is valid but vague.
Specify the trigger (HR system termination event) and the SLA (e.g. 4 hours).

Verdict: Revise before use. Address issues 1 and 3; issue 2 is minor.
```

---

## 9. Tech Stack

**MVP scope:**

- [x] Claude API (claude-opus-4-6 + claude-sonnet-4-6)
- [x] GitHub (fork + PR — add to SAAF-Project repo)

**Stretch goals:**

- [ ] Automated peer-review step integrated into SAAF agent pipelines as a post-processing skill
- [ ] Quantitative scoring: have the reviewer assign a confidence score (0–10) to the original output

---

## 10. Collaboration and Knowledge Sharing

**What I plan to open-source:**

- Best-practice guide: `docs/tips/multi-model-validation.md`
- Peer-review prompt template: `prompts/conventions/multi-model-validation.md`
- Examples of effective Opus ↔ Sonnet review pairs for audit tasks

**What help I'm looking for:**

- Examples from other SAAF organizations where cross-model review caught a meaningful error
- Input on whether a formal confidence score from the reviewer adds value in practice

**Cross-org interest:**

Multi-model validation applies to every AI audit agent built by the 45+ SAAF organizations — it is a meta-skill that improves the reliability of all other skills. Strong candidate for adoption as a SAAF-wide quality standard and for inclusion in the SAAF-Project repo's conventions documentation.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | Documented in this plan; technique documented in TipsAndTricks repo (March 10, 2026) |
| **Do** | Complete | Technique used during Hackathon 1; guidance written up |
| **Check** | Not started | Planned: contribute guide to SAAF-Project repo `docs/` |
| **Act** | Not started | Target: formalise as SAAF quality convention at Hackathon 3 |

---

## 12. Open Questions

1. Should multi-model validation become a mandatory step in the SAAF quality checklist before an agent output is used in a real audit?
2. Is there a meaningful quality difference between Opus reviewing Sonnet vs. Sonnet reviewing Opus — or is the benefit purely from having any second-opinion review?
3. Should the peer-review prompt be specialized per output type (code, finding, control extraction) or kept generic?
