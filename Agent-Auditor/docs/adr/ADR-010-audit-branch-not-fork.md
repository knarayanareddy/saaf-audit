# ADR-010 — Audit-branch `auditedby_<reviewer>_<datum>` i.p.v. fork

## Status

Accepted (2026-06-16) · superseded de eerdere "fork-the-repo"-aanname.

## Context

De auditor wil voor elke bevinding een **concreet vervolg** kunnen plaatsen: niet alleen rapporteren dat iets fout zit, maar ook een voorstel klaarleggen waarmee het dev-team aan de slag kan. De vraag is: waar leg je dat voorstel?

Drie opties:

1. **Een PR op `main`** — direct duidelijk, maar onbeleefd (auditor wijzigt de hoofdtak van het dev-team) en breekt branch-protection.
2. **Een GitHub-fork** — schoon gescheiden, maar verplaatst het werk naar een ander namespace (`auditor/repo` i.p.v. `team/repo`), wat de discoverability voor het dev-team verlaagt en review-tooling fragmenteert.
3. **Een aparte branch op dezelfde repo** — leeft náást `main` in hetzelfde namespace; standaard review-workflow (PR vanuit branch) is van toepassing; geen content-migratie nodig.

Optie 3 matcht het beste hoe auditors offline-style werken: "ik heb een voorstel, leg het naast jullie main zodat jullie het kunnen openen of negeren".

## Decision

Audit-voorstellen landen op een branch met naam:

```
auditedby_<reviewer-slug>_<YYYY-MM-DD>
```

waarin `reviewer-slug` is gegenereerd via `slugify_reviewer()` (`[^A-Za-z0-9_-]+` → `-`). Voorbeeld: `auditedby_johannusNL_2026-06-16`.

**Server-flow** (`POST /repos/{o}/{r}/audit-branch`):

1. Resolve `from_ref` (default = repo's default branch) naar SHA.
2. `POST /repos/{o}/{r}/git/refs` met `ref: refs/heads/<name>` en `sha: <base>`. Bij 422 (bestaat al) hergebruiken.
3. Optioneel: per finding `propose_fix()` aanroepen met `SYSTEM_PROMPT_AUTOFIX` voor een gestructureerd voorstel.
4. Aggregeren tot `AUDIT_FIXES.md` met repo+branch+reviewer+timestamp-header.
5. Committen naar de branch via Contents-API.

**`main` blijft van het dev-team** — de auditor raakt hem nooit. De branch is van de auditor; de owner van de repo beslist over merge / cherry-pick / negeren.

**UI-flow** (criteria-sheet, sectie 1):

- "🌿 Maak audit-branch + autofix-voorstellen" knop verzamelt bevindingen automatisch:
  - geaccepteerde of door AI gesuggereerde fail-AC's
  - audit-trail-items met verdict `inadequate` / `open` / `unrelated`
  - high-severity secrets (geen voorbeelden)
- Reviewer-naam komt uit het metadata-veld (anders `prompt()`).
- Resultaat-blok toont deep-link naar de branch + uitvouwbare lijst per voorstel.
- "↻ Re-audit op deze branch" switcht target en runt audit-trail opnieuw — voor het "gerapporteerd" deel van de loop.

## Consequences

**Positief**

- **Geen namespace-versplintering**: de branch blijft op `org/repo`, GitHub-search en notifications werken voor het dev-team.
- **Review-workflow blijft normaal**: dev-team opent een PR vanuit de branch, of haalt hem direct in.
- **Auditbaar**: `actions.log.jsonl` houdt het `audit_branch_created`-event vast met reviewer + branch + base-commit + #voorstellen.
- **Schoon overgangsmoment**: de naam `auditedby_<jij>_<datum>` is zelf-documenterend — geen verwarring over "is dit een feature-branch of een audit-spoor?".
- **Re-audit loop**: na fixes kun je dezelfde tool opnieuw inzetten op de branch en vergelijken met de oorspronkelijke audit.

**Negatief**

- **Schrijfrechten nodig**: token moet `repo`-scope hebben en de auditor moet collaborator zijn op de target. Voor public-archive audits (waar je geen rechten hebt) faalt deze flow — daar zou een echte fork wel nodig zijn. We accepteren dit voor de SAAF-context waar alle agents binnen één org liggen.
- **Lange `AUDIT_FIXES.md`-bestanden** kunnen vervuilen als de auditor de branch niet opruimt. Mitigatie: het bestand staat in zijn eigen branch — niet `main`.
- **Geen automatische PR-creatie naar `main`**. Bewust niet — dat is een keuze van het dev-team, niet van de auditor. Kan later toegevoegd worden als optionele "Open PR"-knop.

**Niet-gedaan**

- Geen echte autofix van code. `AUDIT_FIXES.md` is een **voorstel-document**, geen code-diff. De `complexity`-tag (`trivial / moderate / research`) maakt expliciet dat Claude niet altijd weet hoe te fixen — alleen wat te overwegen. Dat is eerlijker dan een fake-autofix die niet compileert.
