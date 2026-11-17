# Architecture Decision Records

Elke ADR beschrijft één significante ontwerpkeuze: de context die hem heeft afgedwongen, de daadwerkelijke beslissing, en de gevolgen op lange termijn (positief én negatief).

| ID | Titel | Status |
|---|---|---|
| [ADR-001](ADR-001-single-page-html-light-server.md) | Single-page HTML + lichte Python-server | Accepted |
| [ADR-002](ADR-002-claude-agent-sdk.md) | Claude Agent SDK boven directe Anthropic API | Accepted |
| [ADR-003](ADR-003-localstorage-state-store.md) | `localStorage` als werkstation-cache met integrity-stamp | Accepted |
| [ADR-004](ADR-004-pdf-via-browser-print.md) | PDF via `window.print()` + sha256-stamp | Accepted |
| [ADR-005](ADR-005-cache-key-strategy.md) | Cache-key strategie (commit + model + hashes + exclusions) | Accepted |
| [ADR-006](ADR-006-github-api-target.md) | GitHub-API als bron van waarheid voor de doel-repo | Accepted |
| [ADR-007](ADR-007-append-only-action-log.md) | Append-only `actions.log.jsonl` | Accepted |
| [ADR-008](ADR-008-two-page-dashboard-drilldown.md) | Twee-pagina-architectuur (dashboard + criteria-sheet) | Accepted |
| [ADR-009](ADR-009-readme-classifier.md) | README-based agent classifier met manual override | Accepted |
| [ADR-010](ADR-010-audit-branch-not-fork.md) | Audit-branch `auditedby_<reviewer>_<datum>` i.p.v. fork | Accepted |
| [ADR-011](ADR-011-secrets-scan-auto-finding.md) | Secrets-scan als auto-finding met FP-heuristiek | Accepted |
| [ADR-012](ADR-012-way-of-working-override.md) | Way-of-working als maatwerk-kader | Accepted |

Formaat van een ADR:

- **Status** — Proposed / Accepted / Deprecated / Superseded by ADR-NNN
- **Context** — wat dwong de keuze af, welke beperkingen golden
- **Decision** — wat is besloten (één regel, helder)
- **Consequences** — wat dit makkelijker en wat dit moeilijker maakt
