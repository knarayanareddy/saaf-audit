# ADR-004 — PDF via `window.print()` + sha256-stamp

## Status

Accepted (2026-06-16)

## Context

De eind-output van de tool is een PDF die buiten de webapp gaat circuleren (mail, document-management, archief). Opties:

| Aanpak | Voordeel | Nadeel |
|---|---|---|
| `window.print()` + print-CSS | Geen dependencies | Browser-afhankelijke pagina-breaks |
| jsPDF / html2pdf in de browser | Volledige controle | Zware lib, layout-mismatch |
| Server-side PDF (wkhtmltopdf, puppeteer) | Consistente layout | Extra dependency + server-rondreis |
| Markdown → Pandoc | Eenvoudig | Verliest de scoring-UI |

We willen zo min mogelijk dependencies en de PDF moet visueel matchen met wat de auditor op het scherm ziet.

## Decision

We gebruiken `window.print()` met een toegewijde `@media print { ... }` block in `<style>` voor pagina-breaks, A4-page-size, hiding van knoppen/drawer, en kleurkalibratie. De auditor klikt **Exporteer naar PDF** en kiest in de print-dialog "Save as PDF".

Audit-defensibility wordt apart geleverd door een **integrity stamp** — een sha256 over `JSON.stringify(snapshot())` die zichtbaar wordt in een print-only `<div>` aan het einde van het document. Naast de hash worden tool-versie, prompt-hashes, bundle-hash en timestamp gestempeld.

Vóór `window.print()` draait `exportToPDF()`:

1. `refreshIntegrityStamp()` rebuilds de hash met de laatste state.
2. Dirty-check (`currentProvenance.dirty`) vraagt confirm + log (P-9).
3. `beforeprint`-event logt naar `/log` (P-1).

## Consequences

**Positief**

- Geen extra dependencies, geen build, geen aparte service.
- Layout matcht 1-op-1 met scherm — auditor ziet wat hij print.
- Integrity-stamp dekt G-3 (muteerbare localStorage) partial — een gewijzigde state krijgt een andere hash.

**Negatief**

- Pagina-breaks zijn browser-afhankelijke ASCII-art. We mitigeren met `page-break-inside: avoid` op `.card`, `.objective` en `.at-issue`. Chrome geeft een ander resultaat dan Firefox/Safari.
- Geen PDF/A (archive-quality) garantie zonder server-side tooling.
- De integrity-stamp is informationeel, geen cryptografische handtekening — een sluwe gebruiker kan dezelfde hash herstellen door de gemanipuleerde JSON-data te bewaren. Mitigatie: pair met server-side `actions.log.jsonl` (ADR-007).

**Open**

- Latere iteratie kan een server-side print-route toevoegen (`POST /export-pdf` met headless Chromium) wanneer pagination-determinisme harder vereist wordt.
