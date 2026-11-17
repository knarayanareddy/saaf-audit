---
name: saaf-guard
description: Bouwregels voor SAAF audit-agents / build rules for SAAF audit agents (NL + EN). Gebruik bij het maken of wijzigen van een agent, prompt, web-endpoint, export of audit-trail in een SAAF-repo — vóór je code schrijft die documenten van de auditee leest, een LLM aanroept, een oordeel (Green/Match/Go/Pass) bepaalt, een server start of een CSV/Excel/HTML-rapport maakt.
---

# SAAF Guard — bouwregels voor audit-agents

Deze regels komen uit de 61 bevindingen van de SAAF Security Challenge (10 november 2026).
Volg ze tijdens het bouwen. Gebruik de bouwstenen uit `saaf_guard` (pip-installeerbaar of kopieer `saaf_guard/safe.py`, alleen standaardbibliotheek).
Draai na elke wijziging `python -m saaf_guard.check . --history` en los meldingen op vóór je commit.

## De negen regels

1. **Documenten zijn data, geen instructies.** Alles van de auditee, uploads, web, RSS, repo-inhoud of output van een andere agent gaat de prompt in via `fence(text, source=...)`. Zet `FENCE_RULE` in de systeemprompt. Laat nooit agent-output de systeemprompt van een volgende agent worden.
2. **Bij twijfel nooit groen.** Een eindoordeel komt uit `rollup()`: leeg, onleesbaar of onbekend label => `Inconclusive`. Een mislukte LLM-call of parse levert een fout op, nooit een standaard "Green/Match/Go/Pass/Low risk". Geen mock- of dry-run-uitvoer die eruitziet als een echt rapport: label het zichtbaar.
3. **Controleer wat het model terugzegt.** Citaten en paginanummers via `is_grounded(quote, page, pages)`. Velden die al in de bron staan (control_id, owner, bedragen, IBAN) overschrijf je uit de bron; wijkt het model af, dan is dat een fout. Enum-waarden strikt valideren.
4. **Getallen eerst valideren.** `within_tolerance(a, b, tol)` of `require_finite()` vóór elke vergelijking. NaN of inf is een fout, geen match.
5. **Mensen beslissen, de server weet wie.** Een LLM-oordeel zet nooit zelf een status op validated/approved/Go. De naam van de goedkeurder komt uit de sessie op de server, niet uit de request-body. Een goedkeuring hoort bij één versie van het artefact (hash); nieuwe versie = opnieuw goedkeuren.
6. **Servers lokaal en dicht.** Bind op `127.0.0.1`, geen `debug=True`, geen CORS `*`. Elk endpoint dat een agent draait, bestanden leest/schrijft, een token gebruikt of API-tegoed verbruikt vereist een token. Geen GET-routes die data wijzigen of wissen. Uploads: bestandsnaam zelf genereren, grootte beperken, tijdelijk bestand opruimen.
7. **Geen geheimen in git.** Sleutels alleen via omgevingsvariabelen of een secret store; `.env` in `.gitignore` vóór de eerste commit; `.env.example` alleen met `xxxx`. Nooit sleutels loggen, in rapporten zetten of naar de browser sturen. Een server-token gaat alleen mee naar URLs die je uit gevalideerde, allowlisted delen bouwt (geen `..`, `?`, `#`).
8. **Audit-trail met sleutel.** Gebruik `AuditTrail` (HMAC, sleutel uit env en niet naast de data, alleen toevoegen, `verify()`). Nooit een trail opnieuw opbouwen uit bestanden die zelf aanpasbaar zijn. Een security-check die faalt moet de verwerking stoppen, niet alleen loggen.
9. **Veilige uitvoer.** Elke CSV/Excel-cel door `safe_cell()`. HTML via `textContent` of escape per waarde; links alleen met `http(s):`-schema. Geen `shell=True`, `eval`, `pickle` of `yaml.load` op invoer. Externe scripts met versiepin en `integrity`. PII maskeren vóór het de prompt in gaat als de repo dat belooft — inclusief namen in vrije tekst.

## Werkwijze voor de coding-agent

- Lees vóór het bouwen welke van de negen regels geraakt worden en noem ze in je plan.
- Schrijf bij regel 2, 3 en 4 een test met een kwaadaardig of kapot invoervoorbeeld (leeg model-antwoord, verzonnen citaat, `NaN`, geïnjecteerde instructie in een document).
- Draai `python -m saaf_guard.check . --history`. Een uitzondering mag alleen met reden in `.saaf-guard-ignore`.
- Vermeld in de README onder "Beperkingen" welke regels (nog) niet gehaald worden.

---

## English — the nine build rules

1. **Documents are data, not instructions.** Anything from the auditee, uploads, web, RSS, repo content or another agent's output enters the prompt via `fence(text, source=...)`, with `FENCE_RULE` in the system prompt. Never let agent output become the next agent's system prompt.
2. **When in doubt, never green.** A final verdict comes from `rollup()`: empty, unreadable or unknown => `Inconclusive`. A failed LLM call or parse is an error, never a default "Green/Match/Go/Pass/Low risk". Label mock or dry-run output visibly.
3. **Check what the model says.** Quotes and page numbers via `is_grounded(quote, page, pages)`. Fields that exist in the source (control_id, owner, amounts, IBAN) are overwritten from the source; a mismatch is an error. Validate enums strictly.
4. **Validate numbers first.** `within_tolerance(a, b, tol)` or `require_finite()` before any comparison. NaN or inf is an error, not a match.
5. **Humans decide, the server knows who.** An LLM verdict never sets validated/approved/Go by itself. The approver's name comes from the server session, not the request body. An approval belongs to one artefact version (hash).
6. **Servers local and closed.** Bind to `127.0.0.1`, no `debug=True`, no CORS `*`. Every endpoint that runs an agent, reads/writes files, uses a token or spends API credit requires a token. No GET routes that change or delete data. Uploads: generate the filename, limit size, clean up temp files.
7. **No secrets in git.** Keys only via environment variables or a secret store; `.env` in `.gitignore` before the first commit; `.env.example` with `xxxx` only. Never log keys, put them in reports or send them to the browser. A server token only goes to URLs built from validated, allowlisted parts.
8. **Audit trail with a key.** Use `AuditTrail` (HMAC, key from env and not next to the data, append-only, `verify()`). Never rebuild a trail from editable files. A failing security check stops processing, it does not just log.
9. **Safe output.** Every CSV/Excel cell through `safe_cell()`. HTML via `textContent` or per-value escaping; links only with `http(s):`. No `shell=True`, `eval`, `pickle` or `yaml.load` on input. External scripts pinned with `integrity`. Mask PII before it enters the prompt when the repo promises it — including names in free text.

Run `python -m saaf_guard.check . --history --lang en` before committing. Exceptions only with a reason in `.saaf-guard-ignore`.
