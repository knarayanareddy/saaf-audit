# ADR-002 — Claude Agent SDK boven directe Anthropic API

## Status

Accepted (2026-06-16) · superseded the earlier "API-key in browser" baseline.

## Context

In de eerste iteratie riep de webapp Anthropic direct aan met `anthropic-dangerous-direct-browser-access: true` en de API-sleutel in `localStorage`. Dat werkte maar:

1. De sleutel verliet de browser per request en zat letterlijk in de `localStorage`-dump.
2. Op een gedeelde audit-machine konden alle DevTools-gebruikers hem zien.
3. Billing was los van de Claude Code-subscription die de auditor toch al had.
4. Geen koppeling met de provenance van Claude Code (welke versie, welk model-defaults).

Tegelijk hadden we al een lokale Python-server staan voor andere doelen. De Claude Agent SDK is precies ontworpen voor dit pad: een programmatische `query()` die onder water dezelfde authenticatie en sessie als de Claude Code-CLI gebruikt.

## Decision

We routeren alle AI-aanroepen via de server. De server gebruikt `claude_agent_sdk.query()` met `permission_mode="bypassPermissions"`, `allowed_tools=[]` en `max_turns=1` voor een pure single-shot text-completion.

De server stelt geen Anthropic API-sleutel-eis. Wie de tool draait moet `claude login` hebben gedaan; de SDK pakt die sessie automatisch.

## Consequences

**Positief**

- Geen sleutel in de browser. De drawer toont geen API-key-veld meer.
- Billing/quota loopt op de Claude Code-subscription van de auditor.
- Claude-versie-pinning gebeurt op het systeem, niet in onze code (we vragen het model bij naam aan; de SDK doet de rest).
- We profiteren automatisch van Claude Code-features (geüpdate models, prompt-caching infrastructure waar van toepassing).

**Negatief**

- Vereist Claude Code geïnstalleerd en gelogd-in op de machine — extra installatie-stap voor wie alleen een Python-omgeving had.
- De SDK is jong; we pinnen alleen `>= 0.1.0` en accepteren dat we tegen breaking changes aan kunnen lopen.
- We kunnen geen Anthropic-prompt-caching meer expliciet sturen vanuit de browser (cache_control headers); de SDK behandelt dat.
- Een netwerk-storing tussen Python en Claude Code is een nieuwe failure-mode die we niet zelf kunnen monitoren.

**Mitigaties**

- `/ping` rapporteert `tool: "claude-agent-sdk"` en de geladen routes; afwijking valt op.
- Fouten van de SDK worden in HTTP-503 → UI-error vertaald met expliciete vermelding "Claude Agent SDK fout" zodat de auditor weet dat het niet aan de API ligt.
