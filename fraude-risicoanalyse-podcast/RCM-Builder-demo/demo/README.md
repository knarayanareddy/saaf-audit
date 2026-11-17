# RCM Builder demo: casus Zorggroep Waterlinie

Fictieve casus plus dataset om de RCM Builder-pipeline te demonstreren, uit te breiden en te hergebruiken. Alles wat bij de demo hoort staat in deze map `demo/`. De rest van de repo is RCM-Builder-main, ongewijzigd.

De casus: Stichting Zorggroep Waterlinie, een fictieve VVT-zorgaanbieder (verpleeghuizen en thuiszorg). Vijf processen, negen subprocessen, tien systemen, 24 risico-items uit vier bronnen. De pipeline maakt daar 20 risico's van met 39 controls, toetst die aan een IT-matrix en voegt 20 afgeleide IT-risico's toe. Een what-if-variant laat zien wat er gebeurt als twee IT-bewijzen wegvallen. De volledige casusbeschrijving staat in `CASUS_Zorggroep_Waterlinie.md`.

## Snel starten

Vereist: Python 3.11 of hoger.

```
pip install -r requirements.txt
```

Windows:

```
demo\run_demo.cmd
```

macOS, Linux of Git Bash:

```
bash demo/run_demo.sh
```

Het script draait vanuit de repo-root en is in enkele seconden klaar. Resultaat:

| Bestand | Inhoud |
|---|---|
| `demo/outputs/basis/rcm_output.html` | De RCM als gekleurde tabel, basisscenario. Dit is het demoscherm. |
| `demo/outputs/basis/rcm_output.json` | Volledige uitvoer, drie stages per risico, schema-gevalideerd |
| `demo/outputs/basis/rcm_output.md` | Pipe-tabel |
| `demo/outputs/whatif/...` | Dezelfde drie bestanden voor het what-if-scenario |
| `demo/outputs/vergelijking_basis_whatif.md` | Per risico wat er verschilt tussen basis en what-if |

## Wat het script doet, stap voor stap

1. Pipeline draaien met een lege IT-matrix. Dit levert de control-ID's op (CTRL-0001 en verder). Die ID's deelt de pipeline pas tijdens de run uit, op volgorde van de invoer.
2. `make_it_matrix.py` bouwt `it_matrix_basis.json` uit `it_profile_basis.json`. Het profiel beschrijft de matrix per bronreferentie (F-2024-03, FS-02, WNT) en per positie van de control, niet per control-ID. Zo blijft de matrix kloppen als de nummering verschuift.
3. Hetzelfde voor het what-if: basisprofiel plus `it_profile_whatif.json` als override.
4. Pipeline basis: `rcm_builder.py` met de basis-matrix.
5. Pipeline what-if.
6. `export_html.py` voor beide.
7. `compare_runs.py` vergelijkt beide runs per risico.

Wil je één run met de hand doen:

```
python tools/scripts/rcm_builder.py --input demo/data/use_cases.json --it-matrix demo/data/it_matrix_basis.json --out-json demo/outputs/basis/rcm_output.json --out-md demo/outputs/basis/rcm_output.md --schema outputs/schemas/rcm-schema.json
python tools/scripts/export_html.py --input-json demo/outputs/basis/rcm_output.json --output-html demo/outputs/basis/rcm_output.html --title "RCM Zorggroep Waterlinie"
```

## Bestanden in demo/

| Bestand | Rol |
|---|---|
| `data/use_cases.json` | De casus: context, processen met doelstellingen, en vier bronverzamelingen (`historical_risks`, `incidents`, `fraud_scenarios`, `regulatory_risks`) |
| `data/it_profile_basis.json` | IT-matrix per bronreferentie, basisscenario |
| `data/it_profile_whatif.json` | Twee afwijkende regels voor het what-if-scenario |
| `data/it_matrix_basis.json`, `data/it_matrix_whatif.json` | Gegenereerd door `make_it_matrix.py`. Niet met de hand bewerken. |
| `data/_empty_matrix.json` | Lege matrix voor de eerste pass |
| `make_it_matrix.py` | Vertaalt een profiel naar een matrix met de control-ID's van een run |
| `compare_runs.py` | Vergelijkt twee `rcm_output.json`-bestanden per risico, gekoppeld op bronreferentie |
| `run_demo.cmd`, `run_demo.sh` | De hele keten in één keer |
| `CASUS_Zorggroep_Waterlinie.md` | Casusbeschrijving: organisatie, systemen, processen, bronnen, IT-matrix, what-if |
| `outputs/` | Uitvoer van de laatste run |

## Verwachte uitkomst van het basisscenario

24 items in, 20 risico's uit. Vier paren zijn bewust zo geschreven dat de ontdubbeling ze samenvoegt (tekstgelijkenis 90 of hoger, drempel is 65). Eén subproces heeft bewust geen risico's, dat geeft de waarschuwing "Structural Integrity". Eén risico krijgt de design gap "Redundant" omdat het dezelfde sjablooncontrol deelt met een ander risico op dezelfde doelstelling.

| Risico | Bron | Subproces | Cat. | Inherent | Prelim. | Final | Controls | What-if |
|---|---|---|---|---:|---:|---:|---|---:|
| RISK-0001 | F-2024-03 | Journaalposten en afsluiting | Financial | 20 | 8,0 | 8,0 Low | R / U | 17,0 High |
| RISK-0002 | F-2024-07 + INC-2025-114 | Toegang clientdossiers | IT | 25 | 10,0 | 10,0 Medium | R / P | 16,25 High |
| RISK-0003 | F-2025-02 + FS-01 | Leveranciersstamdata | Fraud | 25 | 10,0 | 10,0 Medium | R / P | 10,0 |
| RISK-0004 | F-2025-05 + INC-2026-019 | Salarisverwerking | Financial | 20 | 8,0 | 13,0 Medium | NA / P | 13,0 |
| RISK-0005 | F-2025-09 | Wijzigingen ECD/ERP | IT | 12 | 4,8 | 10,2 Medium | U / U | 10,2 |
| RISK-0006 | F-2025-11 | Journaalposten en afsluiting | Financial | 16 | 6,4 | 6,4 Low | R / P | 6,4 |
| RISK-0007 | F-2023-12 | Zorgregistratie en declaratie | Financial | 20 | 13,0 | 13,0 Medium | P | 13,0 |
| RISK-0008 | INC-2025-131 | Factuurverwerking | Operational | 12 | 4,8 | 4,8 Low | R / NA | 4,8 |
| RISK-0009 | INC-2025-158 | Wijzigingen ECD/ERP | IT | 20 | 8,0 | 17,0 High | U / NA | 17,0 |
| RISK-0010 | INC-2026-007 + GDPR art. 32 | Privacy | Compliance | 25 | 10,0 | 10,0 Medium | R / U | 10,0 |
| RISK-0011 | INC-2026-023 | Zorgregistratie en declaratie | Financial | 20 | 8,0 | 13,0 Medium | U / P | 13,0 |
| RISK-0012 | INC-2025-140 | Wijzigingen ECD/ERP | IT | 16 | 6,4 | 10,4 Medium | U / P | 10,4 |
| RISK-0013 | FS-02 | Journaalposten en afsluiting | Fraud | 25 | 10,0 | 10,0 Medium | R / U | 10,0 |
| RISK-0014 | FS-03 | Salarisverwerking | Fraud | 25 | 10,0 | 10,0 Medium | R / P | 10,0 |
| RISK-0015 | FS-04 | Zorgregistratie en declaratie | Fraud | 25 | 10,0 | 10,0 Medium | R / P | 10,0 |
| RISK-0016 | FS-05 | Factuurverwerking | Fraud | 25 | 10,0 | 21,25 High | NA / U | 21,25 |
| RISK-0017 | Wmg / NZa | Zorgregistratie en declaratie | Compliance | 15 | 6,0 | 6,0 Low | R / P | 6,0 |
| RISK-0018 | WNT | Salarisverwerking | Compliance | 15 | 6,0 | 6,0 Low | R / NA | 6,0 |
| RISK-0019 | GDPR art. 6 en 30 | Privacy | Compliance | 15 | 6,0 | 12,75 Medium | U / U | 12,75 |
| RISK-0020 | NEN 7510-2 12.4 | Toegang clientdossiers | Compliance | 15 | 6,0 | 6,0 Low | R / P | 6,0 |

R = Reliable, P = Partially Reliable, U = Unreliable, NA = Not Assessed (geen matrixregel). Daarna volgen RISK-0021 tot en met RISK-0040: de UC6-afgeleide IT-risico's, één per bovenstaand risico.

What-if-verhaal: de koppeling met het IAM-portaal is uitgevallen en toegangsaanvragen lopen via bewerkbare Excel-lijsten (IPE wordt Weak), en de ERP-leverancier levert de goedkeuringslog van journaalposten niet meer (geen matrixregel). RISK-0001 gaat van 8,0 naar 17,0 en RISK-0002 van 10,0 naar 16,25. Alle andere risico's blijven gelijk. Precies dit staat in `outputs/vergelijking_basis_whatif.md`.

## Zelf uitbreiden

Een risico toevoegen:

1. Kies de verzameling: `historical_risks` (bron UC2), `incidents` (UC3), `fraud_scenarios` (UC4) of `regulatory_risks` (UC5).
2. Vul `process_id`, `process_name`, `sub_process_id`, `sub_process_name` en `objective`. Het `objective` moet letterlijk gelijk zijn aan een `objective_description` onder `processes`, anders krijgt het risico geen OBJ-id en een taxonomiewaarschuwing.
3. Vul `cause`, `event` en `impact` (Engels, zie hieronder), of één `risk_description` in de vorm "X may result in Y leading to Z" of "X could lead to Y resulting in Z".
4. Geef een referentie: `finding_id`, `incident_id`, `reference` of `regulation_reference`. Die komt in de RCM en is de sleutel in het IT-profiel. Velden als `scenario_id` of `observation` worden genegeerd.
5. `risk_category`: Financial, Operational, IT, Compliance, Fraud of Strategic. Aliassen als "Financial Reporting", "Cyber", "Regulatory" worden vertaald.
6. Voeg in `it_profile_basis.json` een regel toe onder dezelfde referentie: een lijst met per control een matrixregel of `null`. Positie 1 is de preventieve control, positie 2 de detectieve. Het sjabloon "General IT and Operations" heeft één control.
7. Draai `run_demo` opnieuw en bekijk het verschil met `compare_runs.py`.

Wil je alleen een what-if maken, zet dan de afwijkende regels in een nieuw override-bestand en roep `make_it_matrix.py` aan met `--override`.

## Fraude-simulaties met agents

Het injectiepunt is de lijst `fraud_scenarios` in `use_cases.json`. Een agent kan scenario's in dezelfde vorm bijschrijven en de keten opnieuw draaien. De meetlat is stage 3: welke controls zijn Not Assessed of Unreliable, en welk final residual risk blijft over. In de casus zit dat al ingebouwd:

| Scenario | Persona | Gelegenheid in de IT-matrix | Uitkomst basis |
|---|---|---|---|
| FS-01 bankrekening leverancier | AP-medewerker | Wijzigingslog FinCore is Strong, bankbatch wordt aangesloten | Reliable / Partial, blijft 10,0 |
| FS-02 management override | Controller / RvB | Approval-log Strong, maar top-side rapport is bewerkbare Excel | Reliable / Unreliable |
| FS-03 spookmedewerkers | HR / salarisadministratie | Stamdatarapport LoonLink Moderate | Reliable / Partial |
| FS-04 fictieve zorg | Zorgmedewerker | Goedkeuringsworkflow ZorgDossier Strong | Reliable / Partial |
| FS-05 gesplitste facturen | Inkoper met leverancier | Preventieve control zonder matrixregel, 3-way-match rapport Weak | Not Assessed / Unreliable, 21,25 High |

Een agent-loop die werkt zonder code te wijzigen:

1. Geef de agent `CASUS_Zorggroep_Waterlinie.md`, de vijf bestaande scenario's en de tabel hierboven.
2. Laat hem één nieuw scenario schrijven als JSON-object (zelfde velden als FS-01 tot FS-05, referentie FS-06 en verder) plus een profielregel voor `it_profile_basis.json`.
3. Voeg beide toe, draai `run_demo`, en vergelijk met `compare_runs.py <vorige run> <nieuwe run>`. Nieuwe risico's staan onder "Alleen in run B".
4. Beoordeel: welke reliability krijgen de controls, en blijft het final residual risk onder de tolerantie.

Wat de agent moet weten om bruikbare invoer te maken:

- Teksten in het Engels. De sjabloonkeuze en de scoring werken op Engelse trefwoorden.
- Sjabloon "Fraud Prevention" wordt alleen gekozen als de tekst minstens twee van deze woorden bevat: `fraud`, `override`, `collusion`, `misappropriation`. Het woord `unauthorized` telt niet mee (zie hieronder). De categorie Fraud telt als één keer `fraud`.
- Fraude-risico's scoren altijd 25 inherent: startwaarde 5 × 4 plus 1 op beide assen voor de categorie.
- Zet een `reference` en gebruik die ook als sleutel in het profiel.

## Gedrag van de pipeline dat je moet kennen

- **Control-ID's verschuiven.** Ze worden per run oplopend uitgedeeld. Gebruik in verhalen en profielen bronreferenties, geen CTRL- of RISK-nummers.
- **Ontdubbeling is tekstueel.** rapidfuzz `token_sort_ratio` op de hele risicozin, drempel 65, alleen binnen hetzelfde proces en subproces. Het eerst geziene item bepaalt categorie en doelstelling van het samengevoegde risico; bronnen en referenties worden samengevoegd. Volgorde: `use_cases`, dan de overige verzamelingen in de volgorde van het bestand.
- **Sjabloonkeuze telt trefwoorden.** Uit procesnaam, subprocesnaam, doelstelling, oorzaak, gebeurtenis, gevolg én categorie. Het sjabloon met de meeste treffers wint; bij gelijkspel wint het eerste in de lijst (Journal, Access, Change, Payment, Privacy, Fraud, General IT). De categorie "Financial" telt daardoor als trefwoord voor Journal.
- **Woorden worden gestemd voordat ze vergeleken worden** (uitgangen -ies, -ing, -ed, -es, -s gaan eraf), maar de trefwoorden zelf niet. Daardoor matchen `access`, `privileged`, `testing` en `unauthorized` nooit. Wél bruikbaar per sjabloon:
  - Journal: journal, ledger, revenue, close, reconciliation, financial
  - Access: user, account, identity, credential, provision
  - Change: change, deploy, production, release, code, implementation
  - Payment: payment, invoice, vendor, bank, cash, beneficiary, treasury
  - Privacy/Compliance: privacy, compliance, regulatory, gdpr, consent, encryption, subject
  - Fraud: fraud, override, collusion, misappropriation
  - General IT: application, configuration, interface, report, backup, availability, restore
- **Risk appetite wordt op woorden gelezen.** "zero" geeft +1 impact en +1 likelihood, "low" of "minimal" +1 impact, "high" −1 impact, anders niets. Daarom staat de financiële appetite in de casus als "Cautious", anders klapt bijna alles naar 25.
- **Extra opslagen**: meer dan één bron-UC +1 likelihood, bron met "incident" +1 likelihood, tekst met material/critical/breach/outage/misstatement/penalt/fine +1 impact, tekst met repeated/recurring/history/trend +1 likelihood. Assen worden afgekapt op 1 tot 5.
- **De beste control bepaalt het getal.** Preliminary en final residual nemen de hoogste reductie onder de controls van een risico. Een Reliable control naast een Unreliable control laat de score op 60% reductie (zie RISK-0001 basis).
- **Ontbrekende matrixregel is Not Assessed met 0% reductie**: final residual wordt gelijk aan inherent voor die control.
- **Stage 3 maakt voor vrijwel elk risico een UC6-risico.** De trigger is "een control is niet Reliable". Met de ingebouwde sjablonen is de tweede control altijd Detective/Moderate en dus hoogstens Partially Reliable, dus elk risico krijgt er een. Wil je dat voor de demo beperken tot echte problemen, verander dan in `tools/scripts/rcm_it_validator.py` in `apply_it_validation` de voorwaarde `or assessment["additional_itgc_control_required"]` naar alleen `control_reliability in ("Unreliable", "Not Assessed")`. Dat is één regel en de tests blijven grotendeels werken, maar het is een afwijking van de originele repo.
- **Redundant** wordt gemeld als twee risico's op dezelfde doelstelling in hetzelfde subproces dezelfde sjablooncontrol krijgen. Geef risico's een eigen doelstelling als je dat niet wilt.
- **Encoding**: de scripts lezen JSON met de standaard Windows-codering. Houd de JSON-bestanden ASCII, dus geen accenten of typografische aanhalingstekens.
