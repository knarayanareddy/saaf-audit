# SAAF Guard

**Een guardrail die de fouten uit de SAAF Security Challenge al tijdens het bouwen tegenhoudt.**

Op 10 november 2026 vonden we 61 zwakke plekken in 29 SAAF-repos. Ze komen steeds neer op dezelfde negen patronen:
- documenten van de auditee die het oordeel van de agent sturen;
- oordelen die "Green" of "MATCH" geven als er iets misgaat;
- servers die voor iedereen openstaan;
- sleutels in de git-geschiedenis;
- audit-trails die te herschrijven zijn.

SAAF Guard pakt die patronen in drie lagen aan:

| Laag | Wat | Wanneer |
|---|---|---|
| **1. Skill** | `skills/saaf-guard/SKILL.md`: negen bouwregels voor Claude Code of een andere coding-agent | tijdens het ontwerpen en coderen |
| **2. Bouwstenen** | `saaf_guard/safe.py`: veilige functies (alleen standaardbibliotheek) | in de code van de agent |
| **3. CI-check** | `saaf_guard/check.py` + `.github/workflows/saaf-guard.yml` | bij elke push/PR; de build faalt op `high` |
| **4. Scan-agent** | `saaf_guard/scan.py` + skill `saaf-repo-scan` + agent `saaf-security-reviewer` | periodiek of per challenge: alle repos scannen en rapporteren |

Alles werkt in het **Nederlands en Engels** (`--lang nl|en`, of `SAAF_GUARD_LANG=en`); het HTML-rapport heeft een NL/EN-schakelaar.

## Snel starten

```bash
pip install -e .            # geen afhankelijkheden; of gebruik PYTHONPATH

# Check één repo (incl. sleutelscan van de hele git-geschiedenis)
python -m saaf_guard.check pad/naar/repo --history [--lang en]

# Opties: --json  --fail-on high|medium|low|never  --include-tests
```

## Scan-agent: alle repos scannen en rapporteren

De scan-agent maakt van een map met repo-clones een gegroepeerd rapport:

1. **Automatische scan.** SAAF Guard draait per repo. Dit is deterministisch en werkt zonder netwerk.
2. **Review.** Eén of meer `saaf-security-reviewer`-agents in Claude Code beoordelen de repos en schrijven JSON.
3. **Samenvoegen.** Per oorzaak per bestand blijft één bevinding over; bij een dubbeling wint de review.
4. **Rapport.** De agent maakt de bestanden hieronder.

```bash
python -m saaf_guard.scan <werkmap> --reviews scan-out/reviews --out scan-out --lang nl --team "<team>" --history
```

| Uitvoer | Inhoud |
|---|---|
| `findings.json` | alle bevindingen met oorzaak, bron (review/automatisch) en vindplaats |
| `findings.csv` | challenge-formaat: `title,repo,risk_rating,observation,recommendation,verified,team` |
| `report.html` | gegroepeerd naar negen oorzaken, met eerst Critical en High, gekoppeld aan de bouwregels; NL/EN-schakelaar; werkt offline |

In Claude Code zeg je gewoon "scan de SAAF-repos op security" of "run a security scan of the SAAF repos". De skill `skills/saaf-repo-scan/SKILL.md` stuurt dan de stappen aan:
- scope afspreken;
- de automatische scan draaien;
- reviewers parallel laten werken;
- de Critical- en High-bevindingen zelf controleren;
- het rapport maken.

Installeren: kopieer `skills/*` naar `.claude/skills/` en `agents/saaf-security-reviewer.md` naar `.claude/agents/`.
De skill verstuurt, publiceert of pusht niets zonder jouw expliciete toestemming.

### Bevindingen melden in de online repos

```bash
python -m saaf_guard.issues --findings scan-out/findings.json --org SAAF-Project            # proefrun
python -m saaf_guard.issues --findings scan-out/findings.json --org SAAF-Project --apply    # echt melden
```
Eén issue per repo met een afvinklijst. Een volgende scan **werkt hetzelfde issue bij**, dankzij een onzichtbare marker.
Publieke repos krijgen **nooit** een publiek issue: daar gaat de melding via GitHub Private Vulnerability Reporting,
of de repo wordt overgeslagen als dat uit staat. Standaard is het een proefrun, die de teksten naar `issues-preview/` schrijft.

### English summary

SAAF Guard prevents the nine root causes found in the SAAF Security Challenge. It works in four layers:
- a build-rules skill;
- safe building blocks;
- a CI check;
- a repo-scan agent that scans many repos and produces a grouped CSV + bilingual HTML report (`python -m saaf_guard.scan <workspace> --lang en`).

Ask Claude Code to "run a security scan of the SAAF repos" and the `saaf-repo-scan` skill takes it from there. Nothing is sent or published without your explicit approval.

In CI: kopieer `.github/workflows/saaf-guard.yml` naar je repo. Als skill: kopieer `skills/saaf-guard/` naar `.claude/skills/` in je repo.

## Bouwstenen

```python
from saaf_guard import fence, FENCE_RULE, rollup, within_tolerance, is_grounded, safe_cell, AuditTrail

prompt = "Beoordeel dit beleid:\n" + fence(pdf_text, source="beleid.pdf")   # document = data
client.messages.create(system=FENCE_RULE, messages=[{"role": "user", "content": prompt}], ...)

rag = rollup(statuses, order=("No match", "Partial", "Matched"))   # leeg/onbekend => "Inconclusive"
ok = within_tolerance(invoice_total, po_total, tol=0.01)            # NaN => ValueError, geen MATCH
is_grounded(quote, page, pages)                                     # citaat moet op díe pagina staan
writer.writerow([safe_cell(v) for v in row])                        # geen formule-injectie
trail = AuditTrail("trail.jsonl")                                   # HMAC, sleutel uit SAAF_AUDIT_KEY
trail.append("goedkeuring", wie=session_user, artefact_sha256=h); trail.verify()
```

## Regels van de CI-check

| Regel | Ernst | Patroon | Wat een kwaadwillende ermee doet |
|---|---|---|---|
| SG01 | high | echte API-sleutel in werkboom of git-geschiedenis | haalt een oude sleutel uit de geschiedenis en gebruikt hem |
| SG02 | high | LLM-aanroep op documenten/uploads/web zonder `fence()` | zet instructies in een beleids-PDF die het oordeel sturen |
| SG03 | high | functie valt terug op `return "Green"/"MATCH"/"Go"` | levert kapotte invoer aan; het rapport wordt toch groen |
| SG04 | medium | `abs(a-b) > tol` zonder NaN-check | zet `NaN` in een factuurbedrag; elke vergelijking "klopt" |
| SG05 | high | `0.0.0.0`, CORS `*`, `debug=True` | roept vanaf het netwerk of een website de agent aan |
| SG06 | high | `shell=True`, `eval`, `pickle`, `yaml.load` | voert eigen commando's uit via een parameter |
| SG07 | medium | hashketen zonder HMAC-sleutel | past de audit-trail aan en rekent de hashes opnieuw uit |
| SG08 | low | CSV/Excel-export zonder `safe_cell()` | zet een formule in een veld die bij openen data lekt |
| SG09 | high | server-token naar URL uit request-parameters | laat de server met zijn token andere API-paden opvragen |
| SG10 | low | CDN-script zonder versiepin/integrity | levert via een gekaapt CDN-pakket eigen code aan |
| SG11 | medium | `innerHTML` met onge-escapete waarde | plaatst script in een veld dat in de UI wordt getoond |
| SG12 | medium | GET-route die data wist of wijzigt | laat een bezoeker via één link alle werkpapieren wissen |
| SG13 | medium | upload volledig ingelezen zonder groottelimiet | stuurt een enorm bestand en legt de server plat |
| SG14 | low | XML van buiten zonder `defusedxml` | entity-expansie (billion laughs) of XXE |
| SG15 | medium | `extractall()` zonder pad/groottecontrole | zip-bom of bestand buiten de doelmap (padtraversal) |
| SG16 | high | template samengesteld uit tekst (SSTI) | voert code uit via een veld dat in de template belandt |
| SG17 | medium | tekst stil afgekapt vóór de prompt | verstopt het bezwarende bewijs voorbij de limiet |

Uitzondering nodig? Zet de regel in `.saaf-guard-ignore` in de repo-root, mét reden; zonder reden wordt de uitzondering genegeerd:
```
SG08 tools/generate_sample_data.py   # synthetische testdata, geen gebruikersinvoer
```

## Red-team: prompt-injectie lokaal testen

```bash
python -m saaf_guard.redteam <werkmap> --out redteam-out --model sonnet --base borderline
```

Test de echte systeemprompts van oordeel-gevende agents (nu: Track-2 Evidence, judging-found-controls, PBC-Assistant)
met 16–17 aanvalsvarianten, vóór en na `fence()`. Het model draait via de lokale Claude Code-CLI, headless,
**zonder tools, instellingen of MCP, in een lege map**: een geïnjecteerde instructie kan niets uitvoeren.
Uitkomst 10 nov 2026 (Sonnet en Haiku, duidelijke en twijfeldocumenten): **0 geslaagde aanvallen, voor en na**;
`fence(max_chars)` blokkeert de afkap-aanval. Niet getest: lokale open-source modellen, adaptieve aanvallers, agent-ketens.

## Hoe goed werkt het?

Gemeten tegen de 61 bevindingen van 10 november (per bevinding vastgesteld welke regel hem in het juiste bestand moet vangen):

| Ernst | Gevangen door de CI-check |
|---|---|
| Critical | **2 / 2** |
| High | **12 / 20** |
| Medium | 10 / 26 |
| Low | 4 / 13 |
| **Totaal** | **28 / 61** |

De overige 33 zijn ontwerpfouten die je niet aan de code kunt zien. Voorbeelden: een Go/No-go die op ongecontroleerde input vertrouwt, een goedkeurder die uit de request-body komt, of PII-masking die namen mist. Die dekt de **skill** (regels 2, 3, 5 en 8) met de bouwstenen `rollup`, `is_grounded` en `AuditTrail`. Dat gebeurt tijdens het bouwen, niet in CI.

De demo staat in `demo/`: `bad_agent` geeft 6 meldingen (exit 1), `good_agent` geeft er 0 (exit 0).

Tests: `python tests/test_guard.py` (9 tests, geen netwerk nodig).

## Beperkingen

- **Statische heuristieken.** De check leest code en voert niets uit. Hij kan meldingen missen (bijvoorbeeld een prompt die in een ander bestand wordt opgebouwd) en kan vals alarm geven. Vooral bij SG02, SG08 en SG11 is het verstandig de melding te beoordelen.
- **SG02 controleert alleen of `fence()` in het bestand voorkomt**, niet of élke onvertrouwde tekst erdoorheen gaat.
- **`fence()` verkleint de kans op prompt-injectie, maar sluit die niet uit.** Laat een model-oordeel daarom nooit zelf een status vastzetten (regel 5).
- **De sleutelscan herkent alleen bekende formaten**: Anthropic, OpenAI, GitHub, AWS en Slack. Sleutels test hij nooit live.
- **Alleen Python, JS/TS en HTML.** Voor andere talen werkt alleen de sleutelscan.
- **Deze check vervangt geen review of pentest.**

## Privacy en veiligheid

- De check draait volledig lokaal en maakt geen netwerkverbindingen; alleen de CI-workflow haalt de guard zelf op.
- Gevonden sleutels worden nooit getoond, alleen het type en de vindplaats.
