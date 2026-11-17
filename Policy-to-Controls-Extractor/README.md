# Policy-to-Controls Extractor

Een AI-agent die beleidsdocumenten (PDF of DOCX) verwerkt en daaruit concrete, toetsbare controls afleidt op basis van het **6W-framework** (Who, What, Why, When, Where, How).

De output is bedoeld als invoer voor een downstream **PBC/Request Agent** die per control evidenceverzoeken en verduidelijkingsvragen genereert.

---

## Werking

```
testdata/to-do/beleid.pdf
        │
        ▼
  [Tekstextractie]          pdfplumber / python-docx
        │
        ▼
  [Claude analyseert]       Normatieve statements → 6W-controls + Critic-check
        │
        ▼
testdata/output/beleid.json     machine-leesbaar (voor downstream agent)
testdata/output/beleid.xlsx     leesbare tabel (voor mensen)
testdata/output/beleid.pdf      origineel verplaatst
```

Per beleidszin met een verplichting, verbod of voorwaarde leidt Claude één of meer controls af. Ontbrekende velden worden gemarkeerd als `TBD` en resulteren in een open question. Een ingebouwde Critic-check dwingt traceerbaarheid en toetsbaarheid af.

---

## Installatie

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Vereist Python 3.9 of hoger.

---

## Gebruik

```bash
# Alle bestanden in testdata/to-do/ verwerken
.venv/bin/python agent.py

# Met domein en scope
.venv/bin/python agent.py --domain IAM --scope "Organisatie X"

# Één specifiek bestand
.venv/bin/python agent.py --file testdata/to-do/beleid.pdf --domain Change
```

Beschikbare domeinen: `IAM`, `Change`, `Logging`, `Vendor Risk` (of eigen waarde).

---

## Configuratiebestand — `P2C.conf`

Kopieer `P2C.conf.example` naar `P2C.conf` en vul je eigen waarden in. Het bestand is gitignored en wordt nooit meegecommit.

```ini
[paths]
todo_dir = testdata/to-do       # map met te verwerken beleidsdocumenten
output_dir = testdata/output    # map voor output en verplaatste originelen

[defaults]
domain = IAM                    # standaard domein (overschrijfbaar via --domain)
scope = unknown                 # toepassingsscope (overschrijfbaar via --scope)

[anthropic]
api_key = sk-ant-...            # Anthropic API-sleutel (console.anthropic.com)

[claude]
model = claude-sonnet-4-6       # claude-opus-4-6 | claude-sonnet-4-6 | claude-haiku-4-5
```

Argumenten op de commandoregel (`--domain`, `--scope`) overschrijven de waarden in `P2C.conf`.

---

## Invoerbestanden

| Eigenschap | Waarde |
|---|---|
| Formaat | PDF of DOCX |
| Locatie | `testdata/to-do/` (configureerbaar via `todo_dir`) |
| Naamgeving | Vrij; de basisnaam wordt overgenomen in de output |

Na verwerking wordt het originele bestand verplaatst naar de `output_dir`.

---

## Uitvoerbestanden

Voor elk verwerkt bestand `<naam>.<ext>` schrijft de agent:

### `<naam>.json`
Machine-leesbare control-lijst voor de downstream PBC/Request Agent.

```json
{
  "controls": [
    {
      "control_id": "POL-IAM-001",
      "domain": "IAM",
      "who": "IAM beheerder",
      "what": "Productietoegang wordt uitsluitend verleend na aantoonbare goedkeuring door de teamlead.",
      "why": "Voorkomt ongeautoriseerde toegang / reduceert privilege misuse.",
      "when": "Bij elke aanvraag voor productietoegang.",
      "where": "TBD",
      "how": "Aanvraag + approval workflow; provisioning pas na approval.",
      "source_anchors": [
        { "section": "§2.3", "quote": "Toegang tot productie wordt alleen verleend na goedkeuring door de teamlead." }
      ],
      "evidence_hints": ["approval records", "access request tickets", "user access list"],
      "confidence": "High",
      "open_questions": ["Welke systemen vallen onder 'productie'?"]
    }
  ],
  "document_summary": "...",
  "domain_detected": "IAM"
}
```

### `<naam>.xlsx`
Leesbare tabel met dezelfde velden, ingekleurd op confidence-niveau:
- **Groen** — High
- **Geel** — Medium
- **Rood** — Low

---

## Projectstructuur

```
agent.py          hoofdscript (orkestratie, CLI)
models.py         Pydantic-schema's voor controls en extractieresultaat
prompts.py        systeemprompt met extractie-logica voor Claude
requirements.txt  Python-dependencies
P2C.conf          lokale configuratie (gitignored)
P2C.conf.example  voorbeeldconfiguratie
testdata/
  to-do/          invoermap voor beleidsdocumenten
  output/         uitvoermap voor JSON, XLSX en verplaatste originelen
```
