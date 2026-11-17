# ADR-011 — Secrets-scan als auto-finding met FP-heuristiek

## Status

Accepted (2026-06-16)

## Context

Een terugkerende bevinding bij agent-reviews: er stond een API-key hardcoded in een bestand, of een private key in `services/`. Dat is een direct beletsel voor productiewaardigheid — geen reden om de A2-criteria zelfs maar te checken.

We wilden dit als auto-bevinding in de tool, **zónder** dat het een aparte security-tool wordt. Doelen:

1. Detecteer veel-voorkomende secret-patterns met goede recall.
2. Lage false-positive-rate — een auditor mag niet door 50 placeholders heen klikken.
3. Severity-rating zodat reviewer onderscheid maakt tussen "vergeten in productie" en "voorbeeld in een README".
4. Findings landen automatisch in de audit-trail-sectie zodat de auditor ze ook in de PDF terugziet.

## Decision

**Server-side regex-scan** met:

- **Specifieke patterns** voor bekende formats: Anthropic (`sk-ant-…`), OpenAI, GitHub-tokens (`gh[opasu]_…`), AWS (`AKIA…`/`ASIA…`), Slack, Google, PEM private keys, Mongo/Postgres connection-strings met password.
- **Generiek pattern** voor "ziet eruit als hardcoded credential" (`(?i)(api_key|password|secret_key|…)\s*[:=]\s*['"][...]['"]`).
- **False-positive-onderdrukking** in twee lagen:
  - **Pad-patterns**: `*example*`, `*.sample`, `*.template`, `/tests?/`, `/fixtures?/`, `*.lock.json`.
  - **Per-regel placeholders**: `your-`, `<your`, `xxxx`, `REPLACE_ME`, `EXAMPLE`, `FAKE`, `DUMMY`, `example.com`, `1234567890`.
- Findings die door één van deze heuristieken matchen worden naar `severity: low` gedegradeerd én gemarkeerd met `is_example: true`.

**Findings worden in twee responses meegestuurd**:

- `POST /configure-target` — direct na het laden van de bundle, zodat de drawer al kan waarschuwen.
- `POST /audit-trail` — zodat ze in sectie 1 van de criteria-sheet als auto-bevinding boven de GitHub-issues verschijnen.

**Browser-rendering**:

- Rood blok bovenaan sectie 1 met severity-badge, bestand:regel, kind, snippet en optionele "voorbeeld/placeholder"-markering.
- Wanneer high-severity secrets in de bundel zitten, neemt de "Maak audit-branch"-knop ze automatisch op als bevinding (`collectFindingsForAutofix`).

## Consequences

**Positief**

- Onmiddellijk feedback bij target-load — auditor ziet "🔑 3 secrets" voordat hij überhaupt sectie 1 opent.
- Pad-heuristiek voorkomt dat een agent met goede `*.example`-bestanden vol false-positives komt te staan.
- Findings zitten in het audit-trail-resultaat dat als JSON wordt gecached — reproduceerbaar tussen reviewers.
- Audit-branch krijgt automatisch een fix-voorstel per secret ("verwijderen + roteren").

**Negatief**

- **Regex-based** = nooit volledig dekkend. Slim verstopte secrets (in een base64-blob, in een binary, in een ongebruikelijk format) ontsnappen.
- Sommige private repos hebben legitiem voorbeelden met **echte** test-keys — die zouden ten onrechte naar `low` worden gedegradeerd. Mitigatie: de auditor ziet de path en de severity-degradatie expliciet en kan zelf upgraden.
- Geen ondersteuning voor `git history scan` — alleen de huidige bundle. Een gerouleerd-uit-history secret blijft onzichtbaar; voor harde gevallen verwijst de tool naar `gitleaks` of `trufflehog`.
- 100KB-cap per file in de bundle betekent dat heel grote logs / data-dumps niet gescand worden. Niet erg — een agent-repo hoort die ook niet te bevatten.

**Niet-gekozen alternatief**

- **Tool-integration met `gitleaks`/`trufflehog`** zou volledigere detectie geven maar voegt een externe binary toe aan de installatie. Voor de hackathon-scope een te grote uitbreiding. Voor productiezekerheid: zet `gitleaks` los in CI naast deze tool.
