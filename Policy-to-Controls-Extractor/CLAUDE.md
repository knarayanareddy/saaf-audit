# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Doel van het project

Een AI-agent die beleidsdocumenten (tekst/PDF/Word) verwerkt en daaruit concrete, toetsbare controls afleidt. Onderdeel van een twee-agent pipeline:

1. **Policy-to-Controls Extractor** (deze repo) — segmenteert beleidstekst, herkent normatieve statements en produceert gestructureerde controls via het 6W-framework.
2. **PBC/Request Agent** (downstream) — ontvangt de control-JSON en genereert evidenceverzoeken, verduidelijkingsvragen en steekproefgroottes.

## Architectuur

### Mapstructuur & bestandsworkflow

```
to-do/          ← plaats hier PDF of DOCX beleidsdocumenten
output/         ← verwerkte bestanden + outputbestanden komen hier terecht
```

De agent verwerkt elk bestand in `to-do/`, verplaatst het daarna naar `output/` en schrijft daar twee outputbestanden met dezelfde basisnaam als het origineel:
- `<beleidsnaam>.json` — machine-leesbare control-lijst (voor de downstream agent)
- `<beleidsnaam>.xlsx` (of `.csv`) — leesbare tabel voor mensen

Voorbeeld: `to-do/IAM-beleid-v2.pdf` → verwerkt → `output/IAM-beleid-v2.pdf` + `output/IAM-beleid-v2.json` + `output/IAM-beleid-v2.xlsx`

### Input
- Beleidsdocument: PDF of DOCX (geplaatst in `to-do/`)
- Optioneel: domein (IAM, Change, Logging, Vendor Risk)
- Optioneel: toepassingsscope (organisatie/BU/systemen), of `"unknown"`

### Extractie-pipeline
1. **Segmenteren** — splits in paragrafen; detecteer modaliteitswoorden (`must`, `shall`, `only`, `required`, `verboden`, `tenzij`)
2. **Normatieve statements herkennen** — filter zinnen met verplichting, verbod of voorwaarde
3. **Control candidate genereren** — herschrijf naar toetsbare "shall"-vorm: `actor + actie + object + constraint`
4. **6W's invullen** — haal velden expliciet uit tekst; ontbrekende velden → `TBD` + open question (geen aannames)
5. **Ontdubbeling & clustering** — voeg duplicaten samen; maak sub-controls als één zin meerdere eisen bevat
6. **Quality gate / Critic-check** — flagt niet-toetsbare controls (`adequaat`, `tijdig`); dwingt ≥1 source anchor per control af; flagt aanname-taal (`waarschijnlijk`, `typisch`, `meestal`)

### Output — Control-schema (per control)
```json
{
  "control_id": "POL-IAM-001",
  "domain": "IAM",
  "who": "...",
  "what": "...",
  "why": "...",
  "when": "...",
  "where": "...",
  "how": "...",
  "source_anchors": [{"section": "§2.3", "quote": "..."}],
  "evidence_hints": ["approval records", "access request tickets"],
  "confidence": "High | Medium | Low",
  "open_questions": ["Welke tool wordt gebruikt voor aanvragen?"]
}
```

Output wordt weggeschreven naar `output/` (zie Mapstructuur): JSON voor de downstream agent, XLSX/CSV als leesbare tabel.

### Handover contract
De downstream PBC/request-agent hoeft alleen:
- Per control de evidence te concretiseren (formats, owners, periode, steekproefgrootte)
- `open_questions` om te zetten naar clarification requests

## Toolchain & commando's

```bash
# Eenmalig: virtuele omgeving aanmaken en dependencies installeren
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Agent uitvoeren
.venv/bin/python agent.py                        # alle bestanden in testdata/to-do/
.venv/bin/python agent.py --domain IAM           # met domein
.venv/bin/python agent.py --file pad/naar/beleid.pdf --domain IAM --scope "Org X"
```

- Virtuele omgeving: `.venv`
- Linter/formatter: `ruff` (nog niet geconfigureerd)
- Configuratie: `P2C.conf` (gitignored) — paden, domein, scope, model

## Hackathon-scope (dag 1)

- Focus op 1 domein (IAM of Change) voor scherpe heuristiek
- Doel: 10–20 controls uit één beleidsdocument
- Critic-check is verplicht: alle 6W's zijn gevuld of expliciet `TBD`
