# ADR-006 — GitHub-API als bron van waarheid voor de doel-repo

## Status

Accepted (2026-06-16) · superseded the local-clone approach used in v0.1.0.

## Context

In de eerste iteratie verwachtte de tool dat de auditor zelf de doel-repo cloned naar `repo/`. De server las bestanden direct van schijf, gebruikte `git log` voor commit-walking, `git show` voor diffs, en `git rev-parse HEAD` voor provenance.

Dat werkte voor één tester, maar gaf drie operationele problemen:

1. **Versie-drift.** Een auditor kon vergeten `git pull` te doen; de bundle was niet meer de "echte" agent-versie.
2. **Cross-platform.** Windows / WSL / Linux paden, line-endings, en CRLF-LF-handling gaven inconsistente hashes voor effectief identieke bestanden.
3. **Onboarding.** Nieuwe auditors moesten Git lokaal werkend hebben + de URL kennen + clonen. Een te lange ramp.

Tegelijk wilde de tool een **commit-selector**: niet alleen "HEAD van wat ik gecloned heb", maar "deze specifieke SHA, ongeacht waar HEAD nu staat".

## Decision

We refactoren naar een **GitHub-API gedreven** model:

- De drawer accepteert `owner/repo` of een GitHub-URL.
- De drawer accepteert een branch / tag / SHA (leeg = default branch).
- `POST /configure-target` vertaalt de ref naar een concrete SHA en haalt de bestanden op via de GitHub Contents-API.
- `POST /list-commits` voedt de commit-picker met de laatste 30 commits.
- `repo.lock.json` wordt geschreven met de opgelost-aan-SHA informatie.

De `repo/` directory en lokale Git zijn niet meer nodig. De server-laag voor commit-walking + diff-extractie gebruikt `gh_list_commits` en `gh_get_commit_detail` (GitHub-API) i.p.v. `git log` en `git show`.

Authenticatie: de server probeert `GITHUB_TOKEN`, dan `GH_TOKEN`, dan `gh auth token`. Dat dekt zowel CI-omgevingen als de typische ontwikkel-werkstation-flow met de `gh`-CLI ingelogd.

## Consequences

**Positief**

- Eén bron van waarheid (GitHub), geen synchronisatie nodig.
- De commit-picker is letterlijk een SAAF-agent-archief: elke commit ooit is selecteerbaar.
- Provenance per definitie clean (`dirty: false`) — er kunnen geen uncommitted changes zijn in een API-fetch.
- Bestand-discovery via `gh_get_tree` met whitelist-patronen (`README*.md`, root `*.py`, `services/*.py`, etc.) — geen aannames over hoe een agent gestructureerd is.

**Negatief**

- Latency: elke `/configure-target` doet meerdere HTTP-calls (tree → contents per bestand).
- Rate-limiting: anoniem 60 req/uur, met token 5000/uur. Voor kleine bundles (≤25 bestanden) ruim voldoende, maar audit-trail van grote repos kan tegen de limiet aanlopen.
- Vereist `GITHUB_TOKEN` of `gh auth login` voor privé-repos.
- Files-cap (250KB totaal) is een harde grens — grote agents moeten via expliciete `files: [...]` selectie binnen scope worden gebracht.

**Mitigaties**

- De server cached opgehaalde files in-memory na elke `/configure-target`. Een tweede `/evaluate`-call doet geen nieuwe GitHub-fetch.
- `POST /reload` herhaalt de fetch zonder server-restart.
- De fallback `gh auth token` betekent dat de typische auditor (met `gh` al geconfigureerd) geen extra setup hoeft.
