# Self-audit · Agent Auditor v0.1.0

| | |
|---|---|
| Subject | Agent Auditor — webapp + lokale server |
| Versie | 0.5.0 (na D-6 AC-summary sync + D-7 sort opties + sync-indicator) |
| Beoordelaars | Vaktechniek (initiator) + Claude Code |
| Datum | 2026-06-16 |
| Framework | SAAF Hackathon A2 — Audit Criteria & Controls |
| Status | Baseline · gepubliceerd als kennisgeving van bekende gaps |

## 1. Wat de tool doet

**Doel.** Een lokaal-first hulpmiddel voor IT-auditors om voor één SAAF AI-agent een A2-criteriasheet te produceren, scoren en exporteren — inclusief AI-suggesties per acceptance criterium en een audit-trail-analyse van het issue-proces in de doel-repo.

**Input.** (a) een gecloneerde of via GitHub-API benaderbare agent-repo; (b) een optionele GitHub-issue-set; (c) auditor-invoer in een browser-formulier; (d) Claude Agent SDK-authenticatie via de gebruiker's Claude Code-sessie.

**Output.** (a) Een PDF (browser-print) met de complete criteriasheet, geaccepteerde AI-suggesties, audit-trail en provenance; (b) `repo.lock.json` met commit-snapshot; (c) `audit-trail.cache.json` met analyse-resultaat; (d) JSON-export voor archivering.

**Ondersteunde audit-taak.** Een eerste-lijns onderbouwing van een AI-agent-review die later door vaktechniek wordt aftekend.

## 2. Control objectives × frameworks

| ID | Control objective | Framework + clausule | Waarom relevant |
|---|---|---|---|
| **T-1** | Reproduceerbaarheid — een tweede beoordelaar krijgt dezelfde tool-output uit dezelfde input | ISO/IEC 27001 A.5.36 · IIA Standard 2330 · ISO/IEC 42001 §8.3 | Zonder reproduceerbaarheid is de tool zelf niet audit-defensible |
| **T-2** | Integriteit en herleidbaarheid van auditor-acties — wie heeft wanneer welke suggestie geaccepteerd of overruled | IIA Standard 2330 · PCAOB AS 1215 · COBIT 2019 MEA02 | Een AI-suggestie wordt pas een score na menselijke acceptatie; die actie moet vastliggen |
| **T-3** | Hallucinatieweerstand van de tool-uitvoer — AI-suggesties verwijzen alleen naar bestaande bestanden, regels en quotes | OWASP LLM Top 10 — LLM09 · EU AI Act Art. 13 · IIA Standard 2410 | De tool moet niet zelf de gap creëren die hij in agents detecteert |
| **T-4** | Provenance-binding — elk oordeel staat tegen exact één commit en wordt ongeldig bij wijziging | IIA Standard 2330 · ISO/IEC 27001 A.7.5 · NIST SP 800-53 SA-12 | Audit-defensibility vereist dat reviewers met `git checkout <sha>` kunnen reproduceren |
| **T-5** | Vertrouwelijkheid van de gedeelde context — repo-inhoud, prompts en oordelen lekken niet buiten de geautoriseerde flow | OWASP LLM Top 10 — LLM06 · ISO/IEC 27001 A.8.10 · GDPR Art. 32 | Repo-bundles kunnen IP / persoonsgegevens bevatten die naar Anthropic gaan |
| **T-6** | Effectieve menselijke supervisie — de auditor kan AI-oordeel begrijpen, weerleggen en overrulen | EU AI Act Art. 14 · ISO/IEC 42001 §6.1.3 · IIA Standard 2410 | Wettelijke verplichting bij AI-systemen die menselijke beslissingen onderbouwen |

## 3. Acceptance criteria

### T-1 Reproduceerbaarheid

- **T-1.1** Bij dezelfde repo-commit + model + system-prompt produceert `/evaluate` een deterministisch resultaat — getest met N=10 identieke calls per AC, verschil ≤ 1 verdict-mismatch.
- **T-1.2** De cache-key van `/audit-trail` en suggesties bevat álle deterministische inputs: `commit + model + prompt-hash + repo-file-hashes`.
- **T-1.3** `repo.lock.json` wordt geschreven bij elke server-boot en update bij `/reload`.

### T-2 Audit-log van auditor-acties

- **T-2.1** Voor elke handeling (accept / reject / dismiss / overrule / handmatige score) wordt een immutable log-entry vastgelegd met `(timestamp, ac_code, oude waarde, nieuwe waarde, bron)`.
- **T-2.2** Het log overleeft een browser-refresh, een Reset (verplaatst naar archief, niet gewist), en kan in de PDF worden opgenomen.
- **T-2.3** Bij export is in de PDF zichtbaar hoeveel verdicts zijn AI-gesuggereerd vs. handmatig overruled.

### T-3 Hallucinatieweerstand van de tool

- **T-3.1** Op een testset van 20 prompts met sluw geformuleerde criteria verwijst de AI nooit naar een file/regel die niet in de repo voorkomt — recall=100% op een evidence-existence-check.
- **T-3.2** Bij ontbrekende basis levert de AI verdict `"unknown"` met expliciete reden (niet `"pass"`, niet `"fail"`).
- **T-3.3** De server valideert dat het JSON-antwoord van Claude een whitelist aan verdict-waarden gebruikt en weigert anders.

### T-4 Provenance-binding

- **T-4.1** Elke AI-suggestie wordt opgeslagen mét de commit-hash waarop ze is gegenereerd.
- **T-4.2** Bij detectie van een commit-mismatch tussen browser-cache en `repo.lock.json` wordt de auditor zichtbaar gewaarschuwd vóór hij verder werkt.
- **T-4.3** De pill in de header wordt rood / oranje bij `dirty: true` en blokkeert PDF-export tot bevestigd.

### T-5 Vertrouwelijkheid

- **T-5.1** De server bindt op `127.0.0.1` (niet `0.0.0.0`); externe verzoeken worden geweigerd.
- **T-5.2** API-sleutel of OAuth-token komt nooit in browser-`localStorage` of de PDF terecht.
- **T-5.3** De auditor kan vóór elke run zien welke bestanden naar Claude gaan en specifieke bestanden uitsluiten.

### T-6 Menselijke supervisie

- **T-6.1** Een verdict telt pas mee in het dashboard nadat de auditor het expliciet heeft geaccepteerd.
- **T-6.2** Elke AI-suggestie toont redenering + evidence + commit-context vóór acceptatie.
- **T-6.3** De auditor kan elk AC overrulen ná acceptatie, met behoud van zowel het AI-voorstel als de override in het log.

## 4. Good output / never do

**Een correcte PDF-export bevat altijd**

- Repo-pill met commit-hash + dirty-flag
- Voor elke geaccepteerde AC: de AI-redenering + evidence + commit waarop het oordeel is gegeven
- Auditor-naam, datum, model-naam
- Een teller van hoeveel AC's AI-gesuggereerd vs. handmatig zijn ingevuld
- Auditor-acties-log (zie T-2)
- State-JSON sha256 als footer voor verificatie

**De tool mag nooit**

- Een verdict in het dashboard meetellen zonder expliciete auditor-actie
- Een commit-hash claimen die niet uit `git rev-parse HEAD` (of GitHub-API) komt
- Een suggestie cachen onder een dirty-commit zonder de dirty-staat in de cache-sleutel mee te nemen
- Een AI-suggestie produceren zonder repo-context (lege bundle = abort)
- De Reset-knop alles vernietigen zonder eerst een lokale export aan te bieden
- Externe netwerkverbindingen openen buiten Anthropic en `api.github.com`

## 5. Coverage gaps

| ID | Gap | Severity | Toelichting |
|---|---|---|---|
| **G-1** | Geen audit-log van auditor-acties | **Hoog** | Wij eisen traceerbare opvolging van issues bij de agent, maar leggen onze eigen click-acties niet vast. T-2 faalt nu volledig. |
| **G-2** | Cache-sleutel mist prompt-versie en file-hash | **Hoog** | Aanpassing van `SYSTEM_PROMPT_EVAL` of een file in `repo/` zonder `git commit` levert oude cached suggesties op. Server-cache key is alleen (commit, model). |
| **G-3** | LocalStorage is muteerbaar zonder integriteits-check | **Hoog** | Een reviewer kan in DevTools de scores wijzigen, daarna PDF exporteren — de PDF is niet tamper-evident. |
| **G-4** | Geen evidence-existence-validatie aan de server-kant | **Middel** | T-3 wordt niet handhavingbaar gemaakt: de server vertrouwt op de claim van Claude over `file/lines/quote`. |
| **G-5** | Repo-bundle van ~34 KB gaat ongesnipperd naar Anthropic | **Middel** | Mogelijke vertrouwelijkheids-issue (T-5). Geen PII-filter, geen opt-out per bestand. |
| **G-6** | Diff-truncatie op 8 KB in `/audit-trail` | **Middel** | Grote refactors worden gedeeltelijk beoordeeld — verdict op gemankeerde evidence. |
| **G-7** | Orphan-commits worden gelijst maar niet door AI beoordeeld | **Middel** | Inconsistent: closing-commits krijgen wel een verdict, niet-issue-gerefereerde changes niet. |
| **G-8** | Geen 4-ogen-principe of approval-workflow | **Middel** | Eén auditor produceert én PDF zonder tweede-reviewer-handtekening. |
| **G-9** | Geen bescherming tegen prompt-injectie in issue-bodies | **Laag** | Een gemanipuleerd issue kan de AI-analyse pogen te beïnvloeden; risico beperkt omdat de auditor alles ziet, maar niet nul. |
| **G-10** | Browser-`window.print()` produceert browser-afhankelijke pagination | **Laag** | Verschillende browsers produceren verschillende PDF's uit dezelfde scoringsdata. |

### Nieuwe features (post-baseline)

| ID | Feature | Status | Beschrijving |
|---|---|---|---|
| **F-1** | Secrets-scan in bundled files | **resolved** | Server scant alle bundle-bestanden op API-keys, tokens, private keys, hardcoded credentials en database-URLs met password. Server flags severity high/medium en degradeert naar low bij placeholder-bestanden (`*example*`, `*.template`) of placeholder-markers (`your-`, `xxxx`). Findings landen in `/configure-target` en `/audit-trail` response; UI rendert ze als rood blok bovenaan sectie 1. |
| **F-2** | Way-of-working markdown als maatwerk-kader | **resolved** | EvalRequest+AuditTrailRequest hebben `way_of_working: str`. Server injecteert in een `<team_way_of_working>` XML-blok in zowel `build_user_message` als `build_audit_prompt`. Cache-keys nemen `wow_hash` mee zodat wijziging in het kader een nieuwe AI-call uitlokt. Integrity-veld toont `wow_applied: true` per suggestie en in PDF. Drawer accepteert plak-tekst of `.md` upload; persisteert via `settings.wayOfWorking`. |
| **F-3** | Leesbaardere uitleg per acceptance criterium | **resolved** | OBJECTIVES uitgebreid met `purpose` (per objective, "Waar let je op?") en `plainLanguage` (per AC, "Wat betekent dit concreet?"). Beide uitvouwbare `<details>`-blokken; in browser dichtgeklapt voor snelle scan, in print altijd uitgeklapt zodat de PDF-versie de minder ervaren auditor direct meeneemt. Geen jargon, voorbeelden en testaanwijzingen per criterium. |
| **D-1** | Multi-org storage + agent classifier | **resolved** | `orgs.json` als persistente state; `gh_list_org_repos`, `classify_agent` met dedicated `SYSTEM_PROMPT_CLASSIFY`. Endpoints `GET/POST/DELETE /orgs`, `/orgs/{o}/rescan`, `/repos/{o}/{r}/tag`, `/repos/{o}/{r}/classify`. Manual tags worden gerespecteerd bij rescan. |
| **D-2** | Dashboard.html multi-org overview | **resolved** | Aparte standalone HTML met add-org form, filter-pills, per-org en per-repo cards (score 0-100, bevinding-chips, tag-chip met source-marker). Klikbare drill-down link naar audit-sheet. Tag-edit modal voor handmatige overrides. |
| **D-3** | Drill-down via URL-params | **resolved** | `consumeUrlParams()` leest `?owner=&repo=&ref=` bij init, populeert drawer, toont back-link naar dashboard, auto-roept `applyTarget()` zodat de bundle direct binnenkomt. |
| **D-4** | Compliance metrics aggregation | **resolved** | `compute_repo_metrics()` doet light-scan zonder Claude (counts + secrets + orphans). Full `/audit-trail` updatet ook automatisch de dashboard-state met AI-verdicts. `POST /repos/{o}/{r}/audit` voor dashboard "Run audit"-knop. |
| **D-5** | Audit-branch + autofix-voorstellen + re-audit | **resolved** | `POST /repos/{o}/{r}/audit-branch` maakt branch `auditedby_<reviewer>_<datum>` op dezelfde repo (geen fork — main blijft van dev-team). Optioneel `generate_fixes=true`: voor elke bevinding vraagt server Claude een fix-voorstel (`SYSTEM_PROMPT_AUTOFIX`), aggregeert tot `AUDIT_FIXES.md` en commit dat naar de branch. UI: `createAuditBranch()` verzamelt fails uit AC's + open issues + secrets, toont resultaat met deep-link naar GitHub + `reauditOnBranch()`-knop die direct opnieuw audit op de branch draait. |

## 6. PDCA — actiepunten

| ID | Actie | Status | Vervolg-commit |
|---|---|---|---|
| **P-1** | Implementeer `actions.log.jsonl` server-side: append-only log van elke `/evaluate` en elke browser-geaccepteerde verdict, met `(ts, ac, oude, nieuwe, model, prompt_hash, commit)` | **resolved** | `log_event()` schrijft JSONL naar `actions.log.jsonl`. Server logt `eval_request/eval_response/audit_trail_run`. Browser logt via nieuw `/log`-endpoint: `accept/reject/dismiss_suggestion`, `manual_score`, `audit_session_open/reset`, `export_pdf` (beforeprint). `GET /log?limit=N` voor reviewers. Whitelist op event-type. |
| **P-2** | Voeg `prompt_hash` (sha256 van system-prompt + relevant Python-source) toe aan cache-key van `/evaluate` en `/audit-trail` | **resolved** | server.py: `PROMPT_HASH_EVAL`/`PROMPT_HASH_AUDIT`; `/audit-trail` cache vergelijkt nu ook prompt_hash en bundle_hash; `EvalResponse.integrity` zit per suggestie in de PDF |
| **P-3** | Hash alle bestanden van `repo-bundle` bij `/ping` en voeg de hash toe aan elke suggestie; de PDF toont dezelfde hash voor verificatie | **resolved** | `hash_bundle()` levert `BUNDLE_HASH` + `FILE_HASHES`; `/ping` en `/reload` exposen ze; suggestion-card toont prompt+bundle short-hash; metadata-blok rendert volledige hashes |
| **P-4** | Server-zijde evidence-validatie: parse `quote` en verifieer dat ze als substring voorkomen in het genoemde bestand; markeer hallucinaties met `evidence_validated=false` en degradeer verdict | **resolved** | `validate_evidence()` doet whitespace-genormaliseerde substring-match per bestand; markeert items met `validated:true/false`; bij `all_hallucinated` wordt pass/fail gedegradeerd naar unknown (in `/evaluate`) of inadequate (in `/audit-trail`). UI toont ✓/✗ marker per evidence-item en rode "verdict gedegradeerd"-banner. |
| **P-5** | Signed PDF-export: embed in de PDF een sha256 van het volledige state-JSON als footer; reviewers kunnen verifiëren | **resolved** | `refreshIntegrityStamp()` berekent sha256 over `JSON.stringify(snapshot())` via Web Crypto. Print-only `<div class="integrity-stamp">` toont state-hash + repo + prompt-hashes + bundle-hash + tool-versie + timestamp. Wordt bij elke save() (gedebounced) en bij `exportToPDF()` vernieuwd. Hindert G-3 (muteerbare localStorage): een gewijzigde state geeft een andere hash. |
| **P-6** | Per-bestand opt-out in de drawer: lijst de bundle-bestanden met checkboxes om uit te sluiten van Claude-context | **resolved** | `EvalRequest`/`AuditTrailRequest` accepteren `exclude_files: list[str]`; `build_repo_xml(exclude=...)`, `build_audit_prompt(exclude=...)` en `effective_bundle_hash()` zijn opgenomen. Cache-key in `/audit-trail` bevat ook de exclusieset. Drawer toont checkbox per file met UITGESLOTEN-markeer; persisteert via `settings.excludedFiles`. |
| **P-7** | Orphan-commit AI-pass: per orphan een korte adequaatheid-check ("rechtvaardigt deze code-wijziging een eigen issue?") | **resolved** | `SYSTEM_PROMPT_ORPHAN` + `analyze_orphan()` doen per orphan-commit een lichte verdict-call: needs_issue / acceptable / unclear. Capped op 15 commits voor kosten/latentie. UI toont gekleurde badge per orphan + redenering + telstrip in de header van het orphan-blok. |
| **P-8** | Approval-stap voor PDF-export: tweede-reviewer-naam vereist vóór de PDF wordt vrijgegeven met "approved"-watermerk | **resolved** | Twee nieuwe metadata-velden: `secondReviewer` + `approvalDate`. Approval-banner toont DRAFT (geel) of APPROVED (groen) op basis daarvan. In de PDF krijgt body een `DRAFT`-diagonale watermerk-tekst tot een tweede reviewer is ingevuld. Banner status zit in `snapshot()` dus integrity-hash dekt 'm. |
| **P-9** | Dirty-block: blokkeer PDF-export met een expliciete "ik weet dat de repo dirty is"-confirmatie | **resolved** | `exportToPDF()` checkt `currentProvenance.dirty` en vraagt expliciete bevestiging vóór `window.print()`. Beide uitkomsten (akkoord/afgebroken) gaan naar het audit-log met reden. |
| **P-10** | Documenteer een formele tool-versie (semver) en koppel die aan elke export | **resolved** | server.py: `TOOL_VERSION = "0.1.0"`; `/ping` retourneert nu `version`+`build`; HTML-footer toont beide en wordt bij Test verbinding bijgewerkt |

## Samenvattend oordeel

De tool levert inhoudelijk een degelijke A2-criteriasheet en heeft sterke pluspunten op T-4 (provenance) en T-6 (human-in-the-loop UX). De zwakte zit in de eigen audit-defensibility: er is geen log van auditor-acties (G-1), geen prompt-versie in de cache-key (G-2) en geen integriteits-anchor op de export (G-3). Dat is ironisch en het is de eerste prioriteit om op te lossen voordat de tool zelf voor formele oordelen wordt gebruikt.

Deze baseline-audit wordt bewust mee-gepubliceerd in de initiële commit zodat de toolkit publiek transparant is over zijn bekende beperkingen op v0.1.0. Elke gap die in een vervolg-commit wordt geadresseerd krijgt een terugverwijzing in het commit-message én een update in dit bestand onder kolom "Status / Vervolg-commit".

### Update v0.4.0 — overzicht doorgevoerde features

Naast de tien initiële P-acties zijn drie features (F-1..F-3) en vijf dashboard-features (D-1..D-5) gestapeld. Alle commit-messages volgen Conventional-Commits met `Resolves: <id>` zodat `git log --grep="P-1"` of `git log --grep="D-5"` direct de implementatie-trail oplevert. Zie [`README.md`](../README.md) en [`docs/adr/`](../docs/adr/) voor de uitleg per architectuurkeuze.
