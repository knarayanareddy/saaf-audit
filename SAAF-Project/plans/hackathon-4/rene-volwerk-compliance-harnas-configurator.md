# Compliance-Harnas Configurator — SAAF Hackathon #4 Submission

> **Note on framing — this is a retrospective submission.**
> The MVP is already built, tested, and publicly deployed. This plan documents
> *what exists* and asks the SAAF community for **review, adoption, and extension** —
> not for build-time at Hackathon #4. The Plan and Do phases are complete; the Check
> and Act phases are what Hackathon #4 can help with.
>
> - **Repository:** https://github.com/volwerk/compliance-harnas-configurator (MIT)
> - **Live tool:** https://volwerk.github.io/compliance-harnas-configurator
> - **Version:** v0.1.0 (first public release)

---

## 1. Metadata

| Field | Value |
|---|---|
| **Submitter** | René Volwerk |
| **Organisation** | AuCx |
| **Session** | Hackathon 4 (Session 5) |
| **Type** | Workflow (infrastructure for all Agents) |
| **Status** | **Built (MVP live) — seeking adoption & community review** |
| **Claimed By** | René Volwerk — MVP shipped as v0.1.0 on [volwerk/compliance-harnas-configurator](https://github.com/volwerk/compliance-harnas-configurator); happy to transfer to SAAF-Project org upon community agreement |

---

## 2. Problem Statement

**Whoever works with an AI system — builder or auditor — faces the same mapping problem.**

Four EU/NL compliance frameworks apply in parallel — AVG/GDPR, DORA, NL CBW/NIS2 (26 beheersmaatregelen ADR & NOREA), and the EU AI Act — plus a threat model (STRIDE) and domain kaders like DigiD (21 normen NOREA 3.0) or BIO 2.0. The obligations are not orthogonal: each framework picks different subsets based on combinations of data type, model type, hosting model and application type.

Two audiences hit the same wall from opposite sides:

- **AI builders** (engineers, product teams, DPOs, CISOs choosing an AI setup) ask: *"We're building X with Y data on Z infrastructure — what must we implement to stay compliant?"* Today they rely on vendor checklists, legal memos, and best-guess interpretation. Controls get missed because they only activate through combinations (bijzondere PG + public LLM → DPIA verplicht art. 9), and the obligations live in Word documents that never reach the code.

- **Auditors** (internal audit, external assurance, compliance officers) ask the mirror question: *"Given the system X-with-Y-on-Z was deployed, what should it demonstrate to be compliant?"* Today they open four documents, Excel sheets and PDFs, and manually cross-reference which controls apply to *this specific* system.

Both audiences end up with the same three symptoms:

- **Over-scoping:** every checklist gets treated as applicable even when most items don't apply.
- **Under-scoping:** combination-triggered obligations (AI Act art. 25 provider-status on finetuning, art. 50 labeling on generative output, AVG art. 9 bijzondere PG) get missed.
- **No traceability & no runtime reach:** which framework drove a given control is not captured, and controls that get documented never land in the actual system configuration.

Net effect: hours of manual mapping per project or engagement, inconsistent rigor between teams, and a permanent gap between the paperwork and the running AI.

---

## 3. Use-Case Type and Scope

**Primary audiences (two, not one):**

| Audience | How they use the configurator |
|---|---|
| **AI builders** — developers, PM's, DPO's, CISO's, architects deciding what to build | Forward-pass: *"given these design choices, what must we implement?"* → generate CLAUDE.md rules + settings.json hooks that go straight into the codebase, with status-tracking as the build progresses. |
| **Auditors** — internal, external, compliance officers | Reverse-pass: *"given this system was deployed, what should it demonstrate?"* → use the same 38 controls + CBW/DigiD cross-references as an audit checklist; each control has evidence-URL + status fields; export as NOREA-style markdown dossier. |

Both audiences produce and consume the **same JSON schema**, so a builder's config becomes auditable-in-place and an auditor's findings can be handed back to the builder as annotations on the same object.

**Audit / governance domain:** AI Governance & Risk Management — the intersection of Dutch and EU AI-related regulation that anyone building, buying, or assessing AI systems encounters.

**Applicable standards / frameworks mapped out of the box:**

- EU AVG / GDPR (Regulation 2016/679) — 19 of 38 controls tagged
- EU DORA (Regulation 2022/2554)
- NL Cbw / NIS2 Control Framework — 26 beheersmaatregelen (ADR & NOREA, CC-BY 4.0)
- EU AI Act (Regulation 2024/1689) — including rule-based triggers for art. 5, 14, 25, 27, 50
- NL DigiD NOREA 3.0 — partial mapping to AI-relevant normen
- STRIDE threat model — 6 categories mapped to harnas-controls

**In scope:**

- A single-file HTML configurator that maps **one AI use-case at a time** to its required compliance controls.
- Runtime artefact generation for Claude Code (`CLAUDE.md` fragment + `settings.json` hook templates).
- A Claude Code skill (`/harnas-check`) that reads the generated config and gives a GO / WAIT / STOP verdict pre-sessie.
- JSON Schema publication so other SAAF agents can validate configs produced by this tool.
- Cross-references from every harnas-control to the specific BM / norm / article that obliges it.

**Out of scope (for this plan):**

- Multi-agent aggregation / cross-organisation dashboard.
- Automated remediation (the tool identifies gaps, auditors/engineers fix them).
- Frameworks outside NL/EU (US HIPAA, ISO 42001, NIST AI RMF — welcome as PRs but not shipped in v0.1.0).
- Opinions about which AI model to use — the tool is model-agnostic.

---

## 4. SAAF 4-Pillar Mapping

This plan is distinctive because it touches **all four pillars** — not because the agent is big, but because a harnas intrinsically spans Prompts, Tools, Regulatory and Outputs.

| Pillar | Built and live | Proposed location in this SAAF repo (if adopted) |
|---|---|---|
| **Prompts** | "Toon Harnas" tab generates a CLAUDE.md fragment from the 9 soft-tier harnas-controls (G.01-G.04, M.03, T.01/03/05, O.03), with the use-case's own values substituted (`{owner}`, `{aiActClass}`, `{purpose}`). See [src/Compliance-Harnas-Configurator.html#buildClaudeMd](https://github.com/volwerk/compliance-harnas-configurator/blob/main/src/Compliance-Harnas-Configurator.html). | `prompts/system-instructions/harnas-meta-template.md` |
| **Tools** | "Stuur AI" tab generates a `settings.json` hook block for 9 medium-tier controls (T.02 HITL, A.01 audit-log, I.02 prompt-injection, I.03 DLP, D.03 PII-redaction, D.06 retention, M.04 change-mgmt, A.02 audit-trail, I.06 sandbox) as PreToolUse / PostToolUse / UserPromptSubmit / SessionEnd hook templates. See [src/Compliance-Harnas-Configurator.html#buildHooks](https://github.com/volwerk/compliance-harnas-configurator/blob/main/src/Compliance-Harnas-Configurator.html). | `tools/integrations/claude-code-hooks/` |
| **Regulatory** | Every harnas-control has cross-references to AVG/DORA/Cbw/AI Act/DigiD. CBW/NIS2 mapping imported from ADR & NOREA under CC-BY 4.0 (see [NOTICE.md](https://github.com/volwerk/compliance-harnas-configurator/blob/main/NOTICE.md)). | `regulatory/frameworks/harnas-controls.json` |
| **Outputs** | Four canonical output formats already live: JSON (Draft 2020-12, SHA-256 `_integrity` field), GitHub-flavored Markdown dossier, standalone STRIDE threat report, A4 print view. JSON Schema is published at [schemas/harnas-config.schema.json](https://github.com/volwerk/compliance-harnas-configurator/blob/main/schemas/harnas-config.schema.json). | `outputs/schemas/harnas-config.schema.json` |

**Cross-cutting value:** any SAAF agent built in another session (e.g. [GDPR-AI-Audit-Agent](https://github.com/SAAF-Project/GDPR-AI-Audit-Agent), [Vendor_Guard](https://github.com/SAAF-Project/Vendor_Guard), [Compliance-Report-Generator](https://github.com/SAAF-Project/Compliance-Report-Generator)) can ship a harnas-config alongside its code, produced by this tool. The configurator is not a peer agent — it is **infrastructure** for SAAF agents.

**Direct adjacencies in the Hackathon #3 portfolio:**

- [`icfcop-control-testing-agent`](../hackathon-3/icfcop-control-testing-agent.md) (Schuberg Philis) — maps 12 compliance frameworks onto ~30 control domains with 6 central mega-controls. **Same core problem as the 38 harnas-controls.** Strongest collaboration candidate: align mapping conventions so ICFCOP and harnas configs are mutually convertible.
- [`eu-ai-act-compliance-monitor`](../hackathon-3/eu-ai-act-compliance-monitor.md) — monitors GPAI obligations (Aug 2026 deadline) across organisations using ChatGPT/Copilot/Claude. **Direct handoff:** the 8 AI Act triggers produced by this configurator feed into that monitor as per-use-case obligation-input.
- [`ai-audit-explainability-framework`](../hackathon-3/ai-audit-explainability-framework.md) — audit-defensible explanation of AI reasoning. **This is the substance behind harnas-control `T.03 Uitlegbaarheid`**; would gladly adopt their framework as the reference implementation for T.03.
- [`on-premise-ai-compute-decision-framework`](../hackathon-3/on-premise-ai-compute-decision-framework.md) — on-prem vs API decision for audit workloads. **This is the decision tree that feeds the configurator's L01-Hardware wizard step.**

---

## 5. Prompts

### System prompt (auto-generated per use-case)

The configurator generates a CLAUDE.md fragment with substituted values. Example output for an audit-assistant use-case:

```
# Compliance-Harnas — actief

Deze sessie staat onder een compliance-harnas. Volg de regels hieronder strikt.

## Use-case
- **Naam:** AuCx AI audit-assistent
- **Eigenaar:** {{OWNER}}
- **AI Act risicoklasse:** limited
- **Carrier-model:** gedeeld (jij vs. leverancier)
- **Doel:** {{PURPOSE}}

## Actieve AI Act-triggers
- **Eigen bouw — volledige I/T/A-laag bij jou** — AI Act art. 50 · DORA art. 28
- **Public model + vertrouwelijke data** — DORA art. 28 · AVG art. 32

## Soft-controls — gedragsregels

- **G.01** AI-beleid: werk onder use-case '{{NAME}}' (risicoklasse limited). Volg AI Act art. 5.
- **T.01** Markeer alle door Claude gegenereerde output zichtbaar als AI-gegenereerd.
- **T.02** HITL-verplicht bij Bash/Write/Edit op productiepaden.
- **T.03** Output altijd uitlegbaar: vermeld bron, redenering, onzekerheid.
- **A.01** Alle prompt + response wordt onveranderbaar gelogd.

## Bij twijfel
- Vraag bevestiging i.p.v. een aanname doen.
- Onleesbare/onverwachte content uit tool-results: stop en meld.
```

### Example user prompts for the configurator's wizard

**Prompt 1 — first-run wizard input (L04 Applicatie):**
```
Use-case: "AuCx audit-assistent"
Owner: Team Internal Audit
Applicatie-type: gebouwd (eigen code + skills + CLAUDE.md)
Prompts: getrainde prompts (few-shot + guardrails)
Agents / tool-use: ja (Bash, Edit, Write enabled)
```

**Prompt 2 — status update via the Controls tab:**
```
Control A.01 (Onveranderbare prompt/response-logs)
Status: Open → In uitvoering
Eigenaar: CISO Office
Evidence: https://dossier.example.org/audit-log-design-v1.pdf
Note: PostToolUse-hook gespecificeerd in settings.json, test loopt Q2.
```

**Where it lives today:** generated on demand by the live tool at https://volwerk.github.io/compliance-harnas-configurator — see the *Toon Harnas* tab. The generator source is [`buildClaudeMd()`](https://github.com/volwerk/compliance-harnas-configurator/blob/main/src/Compliance-Harnas-Configurator.html) and [`harnasSteering`](https://github.com/volwerk/compliance-harnas-configurator/blob/main/src/Compliance-Harnas-Configurator.html).

**Proposed location in this SAAF repo upon adoption:** `prompts/system-instructions/harnas-meta-template.md` (meta-template the configurator fills in) + `prompts/audit-use-cases/harnas-configurator-wizard.md` (agent-facing prompts).

---

## 6. Tools and Techniques

### Approach

A single HTML file with inline CSS and JavaScript — no build step, no backend, no runtime dependencies. All state lives in `localStorage` plus JSON files the user exports/imports. The tool runs equally well in air-gapped environments and on GitHub Pages.

The engine is a deterministic rule system, not an LLM:
- **Data layer:** constants `harnas{}` (38 controls across H1-H7), `aucx{}` (4 × L-layers × invullingen), `cbwMap{}` (26 CBW/NIS2 BMs), `digidMap{}` (8 AI-relevant DigiD norms), `strideMap{}` (38 × STRIDE-category arrays), `aiActTriggers[]` (8 trigger predicates), `harnasSteering{}` (38 × {soft|medium|hard|org} tiers).
- **Engine:** `generateHarnas(cfg)` unions the `ctrl[]` lists of each chosen invulling, evaluates each AI Act trigger's boolean predicate, dedupes, sorts per H-layer, and annotates each active control with `triggeredBy`, `carrier`, `cbwRef`, `digidRef`, `gapFlag`.
- **Steering engine:** maps each active control to one of {soft, medium, hard, org} tiers and generates CLAUDE.md text (soft) or settings.json hook scaffolds (medium).

### Example script — JSON Schema validation of any harnas-config

```bash
# CI-ready validation using ajv-cli
ajv validate \
  --spec=draft2020 \
  -c ajv-formats \
  -s schemas/harnas-config.schema.json \
  -d examples/DEMO-audit-agent.json \
  --strict=false
```

The schema (`schemas/harnas-config.schema.json`) enforces:
- ID format: `^[\w_-]{3,80}$`
- Enum on `aiActClass`, `L04.app`, `L03.pg`, `L02.model`, `L01.infra`, `controlStatus[*].status`
- `evidence` URL whitelist: `http(s):`, `file:`, `mailto:` only — blocks `javascript:`
- Optional `_integrity`: SHA-256 hex digest over canonicalised JSON

### Tech stack used

- **Frontend:** Vanilla JS (no framework), CSS custom properties, Fraunces/Inter Tight/JetBrains Mono via Google Fonts (CDN-optional — Privacy mode falls back to Georgia/Segoe UI/Consolas).
- **Schema:** JSON Schema Draft 2020-12.
- **Validation:** `ajv-cli` in GitHub Actions CI.
- **Browser APIs:** `localStorage`, `crypto.subtle.digest` (SHA-256), `showSaveFilePicker` (File System Access API, optional).
- **Integration target:** Claude Code CLI — CLAUDE.md + `~/.claude/settings.json` hooks + `~/.claude/skills/harnas-check/` skill.
- **Repository:** currently `volwerk/compliance-harnas-configurator` (public, MIT, GitHub Pages live). Happy to transfer to `SAAF-Project` if the community agrees.

---

## 7. Guardrails

### Claude / AI tool usage notes

- The configurator itself makes **zero LLM calls** — it is a deterministic rule engine.
- The generated CLAUDE.md fragment and hook templates steer Claude Code, but no data from a running config ever leaves the browser unless the user explicitly exports.
- Privacy mode disables Google Fonts CDN entirely (system fonts fallback) for AVG-compliant operation at client sites.
- PII-detection modal runs before every copy/export action — regex patterns for BSN, e-mail, NL phone, IBAN, VAT trigger a warning with three options: Cancel / Anonymize & continue / Force continue.
- No real audit evidence or client names in any committed examples (two DEMO configs are fully synthetic).

### Guardrails checklist

- [x] No `rm`, `sudo`, `curl`, `wget`, or `ssh` in scripts — configurator is pure client-side HTML
- [x] No runtime `pip install` — no Python runtime needed at all
- [x] Python scripts run only from `tools/scripts/` — N/A, no scripts
- [x] No real audit evidence, credentials, or personal data committed — only synthetic DEMO-*.json files
- [x] API keys loaded from environment variables only — N/A, no API calls

---

## 8. Output Format and Examples

**Primary format:** JSON conforming to `harnas-config.schema.json`. This is the canonical cross-agent format — any SAAF agent can emit or consume it.

**Secondary formats:**
- Markdown checklist with YAML frontmatter (GitHub-flavored; drops into SharePoint / Notion / Obsidian / git-based audit dossiers)
- Standalone STRIDE threat report (6 categories × mitigating controls + top-priority list)
- HTML print view (A4-sized, `@media print` CSS strips interactive elements)

**Schema — live at:** [schemas/harnas-config.schema.json](https://github.com/volwerk/compliance-harnas-configurator/blob/main/schemas/harnas-config.schema.json) (JSON Schema Draft 2020-12, MIT-licensed, ready for reuse by any SAAF agent).

**Proposed location in this SAAF repo upon adoption:** `outputs/schemas/harnas-config.schema.json`.

**Not emitting findings** in the traditional SAAF sense — the harnas is a configuration document, not an audit finding. Could downstream produce `finding-schema.json` entries via a separate "Controls-in-status-Open as findings" export, which is a candidate for Hackathon #5.

### Synthetic example output (abbreviated)

```json
{
  "id": "cfg_demo_audit_agent",
  "name": "DEMO — Audit-assistent (generic)",
  "owner": "Audit Lead",
  "aiActClass": "limited",
  "L04": { "app": "built", "prompts": "ptr", "agents": true },
  "L03": { "scope": "s3", "pg": "pg_normal", "confidential": true },
  "L02": { "model": "pub_closed", "finetune": "ft_no" },
  "L01": { "infra": "cloud" },
  "controlStatus": {
    "G.01": { "status": "done", "owner": "Audit Lead", "date": "2026-02-01", "evidence": "https://example.org/ai-policy.pdf" },
    "A.01": { "status": "open", "note": "Append-only prompt/response log not yet implemented." },
    "I.02": { "status": "prog", "note": "Relying on model's built-in defense; no external input scan yet." }
  },
  "history": [
    { "at": "2026-04-21T12:00:00.000Z", "byRole": "maintainer", "kind": "create", "note": "Demo configuration." }
  ],
  "_integrity": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 9. Tech Stack

**MVP scope — already implemented:**

- [x] Vanilla HTML / CSS / JS — single file, no build step
- [x] JSON Schema Draft 2020-12 — published in `schemas/`
- [x] Claude Code skill (`~/.claude/skills/harnas-check/`)
- [x] GitHub Actions CI — ajv-cli + html-validate
- [x] GitHub Pages deployment
- [x] Privacy mode (no CDN calls, system fonts)
- [x] SHA-256 integrity hash + canonical JSON
- [x] PII-detection modal (5 regex patterns)
- [x] Append-only history field in config schema

**Stretch goals for Hackathon #4:**

- [ ] Agent-card generator — emit SAAF-standard metadata.yaml from a harnas-config
- [ ] Multi-config comparison view — diff two harnas-configs side-by-side
- [ ] Framework mapping for ISO 42001 (AI Management Systems) — externally contributed PR welcome
- [ ] English UI toggle (currently Dutch-only)
- [ ] Hosted config registry — opt-in publication to `SAAF-Project/harnas-configs/` so teams see each other's choices without exposing evidence URLs

---

## 10. Collaboration and Knowledge Sharing

**What is already open-sourced** (as of v0.1.0, 2026-04-21, MIT):

- [Full source of the configurator](https://github.com/volwerk/compliance-harnas-configurator/blob/main/src/Compliance-Harnas-Configurator.html) — single file, no build step, no dependencies
- [JSON Schema](https://github.com/volwerk/compliance-harnas-configurator/blob/main/schemas/harnas-config.schema.json) for harnas-configs (Draft 2020-12)
- Two synthetic [DEMO configurations](https://github.com/volwerk/compliance-harnas-configurator/tree/main/examples)
- The [`/harnas-check`](https://github.com/volwerk/compliance-harnas-configurator/blob/main/skills/harnas-check/SKILL.md) Claude Code skill
- CBW/NIS2 mapping with CC-BY 4.0 attribution to ADR & NOREA (see [NOTICE.md](https://github.com/volwerk/compliance-harnas-configurator/blob/main/NOTICE.md))
- [CONTRIBUTING.md](https://github.com/volwerk/compliance-harnas-configurator/blob/main/CONTRIBUTING.md) with design principles (single file, no backend, no mandatory network, data provenance, immutable control codes)
- CI workflow: [ajv-cli schema validation + html-validate](https://github.com/volwerk/compliance-harnas-configurator/blob/main/.github/workflows/validate.yml)

**Hosting:** `volwerk/compliance-harnas-configurator` (public, MIT, GitHub Pages live at https://volwerk.github.io/compliance-harnas-configurator). Happy to transfer to `SAAF-Project` org after community review — see Question 1 in §12.

**What help I'm looking for — with concrete starting points:**

- **Framework-mapping verification** — especially the CBW/NIS2 BM → harnas-control mapping. Mine is best-effort; an ADR or NOREA participant should validate. Closest existing effort: [`icfcop-control-testing-agent`](../hackathon-3/icfcop-control-testing-agent.md) covers 12 frameworks × 30 domains; would love to align so ICFCOP and harnas are mutually convertible.
- **SOC 2 / ISAE 3402 / ISO 42001 extensions** — anyone who regularly audits to those frameworks can propose a mapping via the `framework-mapping` issue template.
- **Explainability substance for `T.03`** — [`ai-audit-explainability-framework`](../hackathon-3/ai-audit-explainability-framework.md) already defines what audit-defensible AI explanation looks like. Ideal pairing: adopt their framework as the reference implementation, cite from harnas-control T.03.
- **Hook implementations** — the `settings.json` hook-blocks currently contain template shell commands. Proper Node/Python implementations of `scan-injection.js`, `dlp-scan.js`, `pii-strip.js` would be the next natural step — probably a joint build with another SAAF team.
- **Downstream consumer** — [`eu-ai-act-compliance-monitor`](../hackathon-3/eu-ai-act-compliance-monitor.md) could consume the 8 AI Act triggers this configurator produces as per-use-case obligation-input. Would make a nice end-to-end demo at Hackathon #4.
- **Agent-card standardisation** — what metadata should every SAAF agent ship alongside its harnas-config? This is a community decision.

**Cross-org interest:**

The configurator is fundamentally cross-organisational by design: each organisation configures once, shares the anonymised schema conformance, keeps the evidence private. Any SAAF team building an agent that touches compliance (Vendor_Guard, GDPR-AI-Audit-Agent, Compliance-Report-Generator) could ship a harnas-config as deployment metadata. I would very much welcome one of those teams as a first consumer to stress-test the format.

---

## 11. PDCA Positioning

| Phase | Status for this plan | Notes |
|---|---|---|
| **Plan** | Complete | This document; plus `CONTRIBUTING.md`, `SECURITY.md`, design principles in-repo. |
| **Do** | Complete (MVP) | Single-file configurator, JSON Schema, CI, Pages live, `/harnas-check` skill installed. |
| **Check** | In progress | Dogfooded on my own Claude Code sessions; STRIDE applied to the configurator itself (`docs/en/stride-self.md`). Needs external audit-practitioner review — ideal use of Hackathon #4. |
| **Act** | Not started | Adoption in real audit engagements Q2–Q3 2026. Transfer to `SAAF-Project` after community OK. Iterate based on feedback from other SAAF agents that adopt the format. |

---

## 12. Open Questions

1. **Repository home.** Stays on `volwerk/...` as a personal contribution, transferred to `SAAF-Project/...`, or mirrored? What is the precedent from Hackathon #3 submissions?

2. **Framework scope.** Is it helpful to keep scope tight (AVG/DORA/Cbw/AI Act + STRIDE + DigiD) so the tool stays small, or should Hackathon #4 aim to land an ISO 42001 mapping as a second framework-pack?

3. **Control immutability.** The configurator's `G.01`–`A.05` codes are intentionally immutable. Is there a SAAF-wide convention we should align with, or is "add-only, never rename" a reasonable principle to document?

4. **Runtime reach.** The configurator currently steers Claude Code. Should the next build target other harnesses (Cursor, Continue.dev, or enterprise API gateways via a generic JSON contract)?

5. **Evidence privacy.** `evidence` URLs in a harnas-config may point to SharePoint or audit dossiers that are not publicly accessible. Should the schema distinguish `evidence_private` (local path / internal URL) from `evidence_public` (OK to include in shared configs)?

6. **Alignment with other SAAF efforts.** Three concrete questions:
   - **Mapping conventions:** should harnas's H1-H7 structure converge with ICFCOP's 6 mega-controls + 30 domains ([`icfcop-control-testing-agent`](../hackathon-3/icfcop-control-testing-agent.md)), or are they complementary abstractions at different granularities?
   - **Vendor handoff:** [Vendor_Guard](https://github.com/SAAF-Project/Vendor_Guard) scores vendors against 8 frameworks; can its output feed a harnas-config so that if a vendor is involved, the relevant L02 `carrier` controls auto-populate?
   - **Continuous monitor:** can [`eu-ai-act-compliance-monitor`](../hackathon-3/eu-ai-act-compliance-monitor.md) subscribe to a harnas-config so that an org's AI Act posture updates automatically as the config changes?

7. **CPE contribution.** Can the process of reviewing / refining framework mappings count as CPE for participating auditors? Would help encourage substantive reviews vs. drive-by PR comments.
