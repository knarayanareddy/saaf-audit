# ADR-008 — Twee-pagina-architectuur (dashboard + criteria-sheet)

## Status

Accepted (2026-06-16)

## Context

In de v0.3.x-iteratie was `audit-criteria-sheet.html` de enige entry-point. Eén HTML = één target — de auditor moest voor elke agent opnieuw owner/repo invoeren en de drawer doorlopen. Dat schaalt slecht zodra je 30+ agents onder één org wilt beoordelen.

Bovendien hebben "kies een agent om te beoordelen" en "beoordeel deze ene agent in detail" fundamenteel verschillende UX-eisen:

- **Overzicht** wil je: alle agents, sorteer-/filter-bare lijst, snelle counts, één klik om in te zoomen.
- **Detail** wil je: één agent diep door, met 20 acceptance criteria, AI per AC, audit-trail, PDF-export.

Mengen die twee in één view, dan wordt het overzicht te detail-zwaar en het detail te chaotisch.

## Decision

Twee aparte HTML-pagina's, gekoppeld via URL-parameters:

```
dashboard.html
  └─→ klik "Open audit →"
        ↓
        audit-criteria-sheet.html?owner=X&repo=Y[&ref=Z]
              └─→ klik "← Dashboard" linksboven
                    ↓
                    dashboard.html
```

**Dashboard verantwoordelijkheid:**

- Organisaties toevoegen / verwijderen
- README-classifier per repo (D-1)
- Per-repo: tag, compliance-score, bevinding-chips, last-audit-timestamp
- Tag-overrides via modal
- "Run audit"-knop voor light-scan
- Drill-down naar criteria-sheet

**Criteria-sheet verantwoordelijkheid:**

- Single-target audit met de 8 secties
- AI-suggesties per AC
- Audit-trail per issue + secrets + orphans
- Audit-branch + autofix-flow
- PDF-export met integrity stamp

State-deling: beide praten met dezelfde lokale server (`http://127.0.0.1:8765`) en delen `localStorage`-settings (server-URL, model). De criteria-sheet leest `?owner=X&repo=Y&ref=Z`, populeert de drawer en roept `applyTarget()` automatisch zodat de auditor direct kan beginnen.

## Consequences

**Positief**

- Mentale scheiding "kies → detail" matcht de natuurlijke flow van vaktechniek: eerst overzicht ("welke 5 agents hebben de meeste issues?"), dan ingaan op één.
- Elke pagina blijft self-contained en debugbaar; geen reactivity-framework nodig.
- URL-parameters = bookmarkbaar en deelbaar. Een vaktechniek-coach kan een directe link naar één criteria-sheet sturen.
- Drill-down werkt natural over browser-tabs: rechtermuisknop → "open in nieuw tabblad" = parallelle audits.

**Negatief**

- Geen client-side router; refresh in criteria-sheet betekent volledig page-load (acceptabel — kost <1s).
- Twee `localStorage`-namespaces: één per pagina. Bewust gekozen — settings overlappen, maar audit-state hoort bij de target, niet bij de dashboardsessie.
- Bij wijziging van een settings-veld (bv. server-URL) wordt het in beide pagina's onthouden, maar pas zichtbaar na refresh van de andere.

**Niet-gekozen alternatief**

- **SPA met routes** (React/Vue): biedt soepelere transities maar voegt een bundler-toolchain, build-step en bundle-grootte toe. Voor een hackathon-tool met twee schermen niet de moeite waard. Migratie kan later via Astro/Eleventy als tussenstap zonder volledige rewrite.
