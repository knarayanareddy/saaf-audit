# ADR-003 — `localStorage` als werkstation-cache met integrity-stamp als mitigatie

## Status

Accepted (2026-06-16)

## Context

De auditor moet:

- Een sessie kunnen onderbreken en hervatten (browser sluiten, terugkomen).
- AI-suggesties bewaren tussen `evaluateAC()` calls (kosten besparen, history houden).
- Geen database opzetten.

Mogelijke state-stores:

| Optie | Voordeel | Probleem |
|---|---|---|
| `localStorage` | Native browser, geen server | Muteerbaar via DevTools, niet tamper-evident |
| Server-side SQLite | Server gecontroleerd | Vereist accounts/sessions |
| Bestand op schijf | Eenvoudig | Browser kan niet schrijven |
| IndexedDB | Capaciteit | Overkill voor enkele KB |

`localStorage` is verreweg het eenvoudigste — maar volledig vertrouwd op de gebruiker, en in audit-context juist een rode vlag.

## Decision

Werkstation-state (formulier-invoer, AI-suggestie-cache, drawer-instellingen, audit-trail-cache) gaat in `localStorage`. Tamper-resistance wordt verkregen door **niet** te vertrouwen op de localStorage zelf, maar door een **integrity stamp** (SHA-256 over de complete state-snapshot) zichtbaar in de PDF-footer en in een afzonderlijke print-only div.

Een tweede reviewer kan de PDF naast een `snapshot.json` houden en zelf `sha256sum` draaien — komt de hash niet overeen, dan is de tussenliggende state gemanipuleerd.

## Consequences

**Positief**

- Geen accounts, sessions, persistente server nodig — auditor kan offline (op `/evaluate` na) doorwerken.
- Per-browser, per-machine — er is geen "lekken" tussen auditors.
- Reset is letterlijk `localStorage.removeItem(KEY)` met confirm-dialog.
- Integrity-stamp dekt elke wijziging in de gebundelde state-JSON.

**Negatief**

- `localStorage` is muteerbaar — een kwaadwillende auditor kan zijn eigen scores wijzigen vóór hij de PDF maakt. Mitigatie: de hash wijzigt mee, dus een reviewer kan ontdekken dat er ná de officiële export is geknoeid (mits hij de oorspronkelijke `snapshot.json` heeft).
- Cross-device hervatten kan alleen via expliciete JSON-export/import.
- Domain-quota van browsers (typisch 5–10 MB) is een harde limiet — voor één criteriasheet ruim voldoende.

**Compensatie van de gap**

- P-5 (signed PDF) en P-1 (server-side append-only audit log) samen leveren een dubbele controle: de log toont wat de auditor heeft gedaan (server-zijde, onmutable per definitie), de hash dat de PDF die data accuraat weergeeft.
