# ADR-001 — Single-page HTML + lichte Python-server

## Status

Accepted (2026-06-16)

## Context

De Agent Auditor moest in één 3-uurs hackathon-sessie bruikbaar zijn voor IT-auditors die noch een dev-omgeving optuigen, noch met een SPA-toolchain (Node, bundler, framework) willen werken. De doelgroep is "Vaktechniek" — mensen die HTML/Markdown lezen en een Python-CLI kunnen starten, niet noodzakelijk frontend-engineers.

Tegelijk vroegen we om:

- AI-aanroepen via de Claude Agent SDK (vereist Python-host of Node-host op de machine)
- GitHub-API-aanroepen (vereist token-houderschap; veiliger niet in de browser)
- PDF-export (browser native)
- Lokale persistentie (browser native)

Een full-stack SPA met React + Vite + Express-server zou werken, maar overdrive zijn voor twintig criteria + één toolfunctie, en de barrière om hem zelfstandig te runnen te hoog leggen.

## Decision

We bouwen een single-file HTML-pagina (`audit-criteria-sheet.html`) met embedded CSS + vanilla JS, gekoppeld aan een single-file FastAPI-server (`server/server.py`). Geen build-stap. Geen bundler. Geen Node. Een auditor `python server.py` + dubbelklik HTML = werkende stack.

## Consequences

**Positief**

- Onmiddellijke startbaarheid (≤ 30 seconden van clone naar eerste suggestie).
- Volledige tool past in `cat audit-criteria-sheet.html server/server.py | less` voor reviewer-inspectie.
- Geen `node_modules`, geen pinning-problemen, geen build-cache.
- Eén HTML = portable; de webapp draait ook van `file://` zolang de server lokaal draait.
- De browser-Devtools-console is de enige debugger die nodig is.

**Negatief**

- Geen module-systeem in de JS: alles in één `<script>`-blok, ~1500 regels. We mitigeren met sectie-comments en duidelijke functie-namen.
- Geen reactiviteit (geen React/Vue) — we re-renderen handmatig na state-wijzigingen via dedicated `renderX()`-functies.
- Geen test-framework. Acceptatie gebeurt door handmatig doorlopen tegen een referentie-repo.
- Geen CSS-preprocessor — design tokens als CSS custom properties (`--accent` etc.) in `:root`.

**Niet-overwogen tegen-alternatieven**

- Streamlit/Gradio: te restricted in custom UI (criteria-sheet vereist eigen DOM, integrity stamp, print-styling).
- Server-side rendered Jinja: vereist tweede ronde tussen wijziging en zien, breekt de directe browser-`file://` opening.

Deze keuze laat ruimte voor latere migratie naar een SPA als de tool buiten hackathon-scope groeit; alle businesslogica zit in `server.py` en de UI is HTML-vrije logica + DOM-rendering.
