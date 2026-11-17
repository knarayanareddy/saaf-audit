# ADR-007 — Append-only `actions.log.jsonl`

## Status

Accepted (2026-06-16)

## Context

De Agent Auditor produceert audit-oordelen. Een externe reviewer, een kwaliteitsfunctie, of een toekomstige toezichthouder moet kunnen reconstrueren:

- Welke verdicts kwamen van de AI, welke van de mens.
- Wanneer welke handeling plaatsvond.
- Tegen welke commit en bundle het oordeel viel.
- Of een verdict gedegradeerd is wegens hallucinatie (P-4).

De gap die dit afsluit (G-1) was ironisch: de tool eiste dit van de gecontroleerde agent (issue → commit → diff trail), maar niet van zichzelf.

Mogelijke implementaties:

| Optie | Voordeel | Nadeel |
|---|---|---|
| Append-only JSONL bestand | Eenvoudig, robuust, leesbaar | Geen indexen / queries |
| SQLite met INSERT | Zoekbaar | Schema-migratie nodig |
| External log-service (Loki, ELK) | Centralisatie | Operational overhead |
| Browser localStorage | Geen server-vereiste | Geen integriteit |

## Decision

Server-side append-only JSON-lines log: `actions.log.jsonl`. Eén regel = één event. Geen rotatie (in een audit-context wil je geen oude entries verliezen — disk-druk wordt in een latere iteratie via archivering opgelost).

Schema per regel:

```json
{
  "ts":           "2026-06-16T14:42:00+00:00",
  "type":         "accept_suggestion | reject_suggestion | dismiss_suggestion | manual_score | manual_unset | audit_session_open | audit_session_reset | export_pdf | configure_target | eval_request | eval_response | audit_trail_run",
  "tool_version": "0.2.0",
  "commit":       "<target SHA>",
  "bundle_hash":  "<sha256>",
  "payload":      { ... event-specifiek ... }
}
```

Schrijfpad: server-events worden direct door `log_event()` toegevoegd. Browser-events gaan via `POST /log` met een gevalideerd `type` (whitelist).

Lezen: `GET /log?limit=N` retourneert de laatste N entries, primair voor debug en (later) voor opname in de PDF-export.

## Consequences

**Positief**

- Append-only is **structureel** tamper-resistant in de meest gangbare zin: een wijziging in een eerdere regel kan worden ontdekt door log-hashing of door file-system attestation.
- Eenvoudig te grepen, parsen, en in te lezen vanuit elke gangbare tool.
- Geen schema-migratie nodig — losse velden in `payload` kunnen evolueren.
- Server is single-writer (FastAPI proces), geen lock-contention.

**Negatief**

- Zonder rotatie of compactie groeit het bestand monotoon. Voor een typische audit-sessie (~100 events) is dit ruim binnen perken.
- Geen authentication op `/log` POST — een lokale partij met toegang tot `127.0.0.1:8765` kan willekeurige events toevoegen. Mitigatie: server is bewust gebonden aan localhost (geen externe vector).
- Het log is niet cryptografisch gechained (hash-pointer per regel) — een geavanceerde aanvaller die toegang heeft tot de schijf kan regels herschrijven. Mitigatie: future-werk — een PDCA-item kan een Merkle-tree of HMAC-keten introduceren.

**Open vraag**

- Hoe vaak archiveert een audit-team z'n logs? Voor nu is dat handmatig (kopieer `actions.log.jsonl` naar archief en herstart de server om een leeg log te beginnen).
