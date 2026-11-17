# ADR-005 — Cache-key strategie

## Status

Accepted (2026-06-16)

## Context

Audit-trail-analyse is duur: per issue één LLM-call met de complete repo-bundel in de prompt. Voor 10 issues × 5 minuten cumulatief × meerdere reviewers = veel kosten, latency en variantie.

We wilden cachen, maar in een audit-tool is "ik geef je gisteren's antwoord" zonder controle gevaarlijk: de auditor moet kunnen vertrouwen dat het resultaat **een functie is van een bekende, controleerbare input**.

De eerste implementatie had cache-key = `(commit, model)`. Dat is fout: prompt-tuning of het uitsluiten van een bestand uit de bundle invalideerde de cache **niet**, waardoor de auditor het oude oordeel zou zien voor een effectief andere input.

## Decision

De cache-key bevat **alle deterministische inputs** waar Claude over redeneert:

```
cache_key = (
  commit_SHA,
  model,
  prompt_hash      (sha256 van SYSTEM_PROMPT_AUDIT),
  bundle_hash      (sha256 van [sha256 per included file]),
  exclude_files    (sorted set)
)
```

Wijzigt één van deze velden, dan invalideert de cache automatisch.

Server-side cache leeft in `audit-trail.cache.json` (geserialiseerd). Client-side cache leeft in `localStorage` met dezelfde key-check.

Verder wordt de **integriteit van elk verdict** in de response meegegeven (`integrity.bundle_hash`, `integrity.prompt_hash`, `integrity.tool_version`), zodat de PDF-export later kan tonen onder welke exacte voorwaarden de AI tot dat oordeel kwam.

## Consequences

**Positief**

- Een prompt-bewerking dwingt herevaluatie af — auditors kunnen niet per ongeluk vergelijken tegen een oud prompt-resultaat.
- Per-file uitsluiting werkt voorspelbaar: zelfde inputs ⇒ zelfde cache-hit; andere uitsluitings-set ⇒ andere cache-key.
- De integrity-velden in de PDF maken externe verificatie mogelijk: een reviewer kan exacter dan ooit reproduceren wat Claude in de prompt zag.

**Negatief**

- Iedere prompt-wijziging breekt de cache breed; tweemaal per dag tunen = tweemaal volledig herevalueren. Mitigatie: prompt-wijzigingen gaan altijd via een commit, dus er is sowieso een nieuwe `commit_SHA` (mocht de tool ooit zichzelf auditen).
- De cache-key heeft geen versie-veld; nieuwe Claude-modellen die in toevallig dezelfde model-string komen worden niet gedetecteerd. We accepteren dit risico: modelnamen zijn versie-gepind in Anthropic's API.

**Niet-meegekocht**

- We hashen niet over de exacte user-prompt-string per AC. Dat zou cleaner zijn maar verviervoudigt het aantal cache-entries en biedt geen extra zekerheid (de AC-tekst is statisch in `OBJECTIVES`).
