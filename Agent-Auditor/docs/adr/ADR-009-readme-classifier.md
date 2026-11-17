# ADR-009 — README-based agent classifier met manual override

## Status

Accepted (2026-06-16)

## Context

Een org zoals `SAAF-Project` bevat ~30 repos waarvan misschien 20 echte AI-agents zijn. De rest is overige werk: een portal-website, libraries, leeg-startpoint-repos, een wiki, courseware. De auditor wil binnen één scherm zien "welke 20 zijn agents — en welke ben ik?".

Mogelijke classificatie-methoden:

| Optie | Voordeel | Nadeel |
|---|---|---|
| Topic-tag op GitHub | Native | Bijna geen repo heeft 'em |
| Filename-pattern (heuristiek) | Snel | Mist context — een file met `agent.py` kan ook een library zijn |
| Statische rule-engine | Auditbaar | Te bros — agent-vorm varieert |
| LLM-classificatie op README | Genuanceerd | Kost een Claude-call per repo |

We hebben sowieso al een Claude-uitvoeringspad voor de andere AI-stappen — een kortere call per README is geen significante overhead bij 30 repos.

Tegelijk: de classifier moet **nooit overrulen** wat de auditor weet. Een vakman kan in 2 seconden zien dat repo X géén agent is, ook al heeft de README misleidende terminologie.

## Decision

Een dedicated classifier-pad met manual override:

**Server:**

- `SYSTEM_PROMPT_CLASSIFY` definieert de "agent"-categorie expliciet en geeft tegenvoorbeelden (libraries, portals).
- `classify_agent(owner, repo, model)` fetcht de README via Contents-API en stuurt hem (tot 8KB) naar Claude met max_turns=1.
- Output is een gestructureerd JSON-object: `verdict ∈ {agent, not_agent, unclear}` + `reasoning` (1-2 zinnen NL) + `agent_signals` (lijst korte triggers).
- Persisteert in `orgs.json` per repo onder `agent_classification` + `is_agent` + `tag_source: "auto"`.

**Override-pad:**

- `POST /repos/{o}/{r}/tag` zet `is_agent` handmatig op `true`, `false` of `null` (onduidelijk).
- `tag_source` springt naar `"manual"`.
- Bij volgende `rescan` van de org wordt deze repo **overgeslagen** — manual wint.
- Reasoning gaat in `manual_notes[]` met timestamp.

**UI:**

- Repo-card toont chip met type (🤖 Agent / Niet / ?) plus klein label van de bron (`auto` / `manual`).
- "Edit"-knop opent een modal met drie keuzes en een toelichtings-veld.

## Consequences

**Positief**

- One-shot setup: voeg de org toe, ga koffie halen, kom terug met een geclassificeerde lijst.
- De `agent_signals`-lijst geeft de auditor een snelle reden om in te grijpen ("ik zie 'gebruikt anthropic' maar weet dat dit een test-fixture is").
- Manual override is sticky — auditor hoeft de classifier niet te wantrouwen, omdat zijn correctie nooit verdwijnt.
- De classifier-prompt is geversionneerd (hash in `/ping`), dus reviewers weten welke definitie van "agent" gebruikt is.

**Negatief**

- Eén Claude-call per repo bij `POST /orgs?classify=true` — kosten schalen met org-grootte. Voor 30 repos meestal binnen 1 minuut; voor 300+ wordt het significant.
- Geen rate-limit-bescherming binnen de classifier — bij grote orgs kunnen we GitHub's anonieme limiet raken. Mitigatie: `gh auth login` met token = 5000/uur.
- Een lege of zeer korte README maakt de classifier kwetsbaar voor false-positives op naam alleen. Mitigatie: vallback verdict `unclear` wanneer geen README + reasoning expliciet zegt "geen README gevonden".

**Niet-gekozen alternatief**

- **Repo-tree analyse** (kijk naar `agent.py`, `prompts.py`, `requirements.txt`): leek robuuster maar geeft veel ruis (een library `import anthropic` is óók agent-like). De README-aanpak is sneller om uit te leggen en past beter bij hoe een mens de keuze maakt.
