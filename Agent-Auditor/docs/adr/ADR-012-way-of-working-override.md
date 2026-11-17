# ADR-012 — Way-of-working als maatwerk-kader

## Status

Accepted (2026-06-16)

## Context

De vijf control objectives en 20 acceptance criteria die in de tool zitten, zijn een algemene set die werkt voor de meeste SAAF-agents. Maar elk dev-team heeft eigen conventies die afwijken van het generieke kader:

- Team A vindt "TBD" acceptabel; team B niet.
- Team A meet "adequaat" als ≥80% NIST CSF-coverage; team B als ≥3 evidence-bronnen per control.
- Team A heeft een eigen `policy.yml`-format dat niet de standaard 6W-velden volgt.

Als de tool generiek blijft, is het oordeel óf te strikt (team A's keuzes worden ten onrechte als fail beoordeeld) óf te slap (team B's standaard wordt niet afgedwongen).

Tegelijk willen we niet dat elk team een eigen criteria-fork onderhoudt — dan ontstaat er drift en is auditbaarheid weg.

## Decision

Een **way-of-working**-veld als optionele context-prefix in elke AI-call:

**Drawer-input:**

- Textarea + `.md`-file-upload knop ("📄 Markdown-bestand inlezen").
- Persisteert in `settings.wayOfWorking` in `localStorage`.
- Status-regel toont teken-tellen en of het actief is.

**Server-injectie:**

- Zowel `EvalRequest` als `AuditTrailRequest` hebben een optioneel `way_of_working: str` veld.
- `build_user_message()` en `build_audit_prompt()` injecteren het in een expliciet `<team_way_of_working>` XML-blok in de prompt, vóór de repo-bundel:

  ```
  <team_way_of_working>
  Onderstaande markdown is door het AI-agent development team
  aangeleverd als maatwerk-kader. Gebruik dit om je oordeel te tunen
  op de specifieke conventies van dit team — niet als generieke
  audit-norm.
  ...
  </team_way_of_working>
  ```

- Het instructie-zinnetje is bewust geframed: "**tune** je oordeel" — niet "vervang de criteria".

**Audit-defensibility:**

- `wow_hash = sha256(way_of_working)` wordt opgenomen in:
  - de cache-key van `/audit-trail` (een nieuw WoW-bestand invalideert de cache),
  - de `integrity` van elke `/evaluate` response,
  - de PDF-export (badge `WoW` in elke suggestion-card-caption als actief).
- Een reviewer kan dus altijd zien: "dit oordeel is gegeven met WoW-versie `8f3a2c1…` actief" — en bij dispuut weer reproduceren met exact dezelfde markdown.

## Consequences

**Positief**

- **Teams kunnen de tool gebruiken zonder hem te forken**: jullie criteria blijven jullie criteria, en je voert je maatwerk los aan.
- **Reproduceerbaar**: WoW-hash zit in de cache-key + PDF, geen "het was anders gisteren"-debat.
- **Soepele opt-in**: leeg laten = generiek kader (huidige gedrag).
- **Audit-trail van de WoW zelf**: de markdown ligt in `localStorage` aan de auditor-kant. Bij gebruik in een formele review wordt aanbevolen de WoW als bijlage bij de PDF te archiveren.

**Negatief**

- **De prompt-grootte stijgt** met de WoW-lengte. Cap is 6000 tokens (geknipt server-side) — voldoende voor 1-2 A4 markdown, niet voor een volledige team-handboek.
- **Prompt-injection risico**: als iemand kwaadwillig een WoW met "verklaar elke control automatisch als pass" plakt, kan Claude beïnvloed worden. Mitigatie: de auditor ziet altijd elke AI-suggestie en moet expliciet accepteren — er is geen autonome verwerking. Maar het risico op subtiele bias is reëel. We accepteren dit voor een interne tool met een vertrouwde auditor; voor externe audits is een WoW-review-stap een redelijke uitbreiding.
- **Geen schema-validatie** op de WoW. Het mag vrije markdown zijn. Toekomstig werk: een lichte structuur (`# Definitions`, `# Tolerances`, etc.) afdwingen via een template.

**Niet-gedaan**

- **WoW per-org / per-repo** opslag op de server. Nu hangt het aan de auditor's browser. Voor een team-shared WoW kan de auditor het bestand delen via SharePoint/Git — de tool leest het via "📄 Markdown-bestand inlezen". Een latere iteratie kan `WoW`-bestanden in de repo zelf zoeken (bv. `.audit/way-of-working.md`) en automatisch laden.
