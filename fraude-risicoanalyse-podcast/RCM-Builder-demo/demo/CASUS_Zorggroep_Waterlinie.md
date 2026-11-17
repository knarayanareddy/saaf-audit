# Casus: Stichting Zorggroep Waterlinie

Fictieve organisatie, bedacht voor de demo van de RCM Builder. Alle namen, systemen, getallen en incidenten zijn verzonnen. Overeenkomsten met bestaande organisaties berusten op toeval.

## De organisatie

Zorggroep Waterlinie is een VVT-aanbieder (verpleging, verzorging en thuiszorg) in het rivierengebied. Veertien verpleeghuislocaties en zes thuiszorgteams, circa 2.800 fte, omzet ongeveer EUR 210 miljoen. De zorg wordt bekostigd via het zorgkantoor (Wlz), vier zorgverzekeraars (Zvw wijkverpleging) en zeven gemeenten (Wmo). De Raad van Bestuur bestaat uit twee leden. Interne audit is een team van drie personen dat rapporteert aan de auditcommissie. Boekjaar 2026 is de beoordelingsperiode.

De organisatie zit in een NEN 7510-certificeringstraject (informatiebeveiliging in de zorg) met de externe audit in het vierde kwartaal van 2026. Twee interim-managers werken via bureaus, wat de WNT-toets (Wet normering topinkomens) relevant maakt.

## Risicobereidheid

| Domein | Uitspraak in de casus | Effect in de pipeline |
|---|---|---|
| Financial | Cautious: een materiele fout in jaarrekening of declaraties is niet acceptabel | geen opslag |
| Operational | Moderate: tijdelijke verstoring van ondersteunende processen is acceptabel als de zorgcontinuiteit geborgd blijft | geen opslag |
| Compliance | Low tolerance voor privacy-incidenten met clientgegevens | +1 impact |
| Fraud | Zero tolerance | +1 impact, +1 likelihood |
| IT | Moderate: ECD en ERP moeten betrouwbaar en herleidbaar zijn; korte geplande downtime is acceptabel | geen opslag |

## Systeemlandschap

| Systeem | Rol | Eigenaar |
|---|---|---|
| ZorgDossier (ECD) | Elektronisch clientendossier: zorgplan, zorgregistratie, declaratie aan verzekeraars via Vecozo | Zorg / Informatiemanagement |
| FinCore (ERP) | Grootboek, crediteuren, factuurworkflow, koppelingen naar declaratie en bank | Financien |
| IdentiteitsHub (IAM) | Toegangsaanvragen en autorisaties voor ECD en ERP | IT |
| PlanWijs | Roosterapplicatie, levert uren aan de salarisverwerking | HR |
| LoonLink (SaaS) | Externe salarisverwerking | HR / Financien |
| Bankportaal | Betaalbatches en salarisbetalingen | Treasury |
| ChangeFlow | Servicedesk en changetickets, grotendeels handmatig bijgehouden | IT |
| DataGuard (DLP) | Logging van exports en verwisselbare media | IT-beveiliging |
| PrivacyPortaal | Verwerkingsregister en toestemmingen, handmatig bijgehouden | Functionaris gegevensbescherming |
| LogWacht (SIEM) | Monitoring van de toegangslogging van het ECD | IT-beveiliging |

## Processen, subprocessen en doelstellingen

| Proces | Subproces | Doelstellingen (OBJ) |
|---|---|---|
| PRC-01 Revenue and Billing | SP-01-01 Care Registration and Declaration | 0001 volledig en juist declareren in de juiste periode; 0002 declaratie gedekt door indicatie en zorgplan; 0003 alleen daadwerkelijk geleverde zorg declareren |
| | SP-01-02 Journal Entries and Financial Close | 0004 journaalposten geautoriseerd en onderbouwd; 0005 management override voorkomen en ontdekken; 0006 tijdige afsluiting met aangesloten saldi |
| PRC-02 Purchase to Pay | SP-02-01 Vendor Master Data and Procurement | 0007 legitieme leveranciers, stamdatawijzigingen onafhankelijk goedgekeurd |
| | SP-02-02 Invoice Processing and Payment | 0008 facturen goedgekeurd door bevoegd mandaathouder; 0009 alleen betalen voor ontvangen prestaties |
| PRC-03 Payroll | SP-03-01 Payroll Processing and Payment | 0010 salaris op aangesloten uren; 0011 alleen aan huidige medewerkers; 0012 bezoldiging binnen de WNT |
| | SP-03-02 Leave and Absence Registration | 0013 verlof en verzuim volledig en tijdig (bewust zonder risico's) |
| PRC-04 Client Data and Privacy | SP-04-01 Access to Client Records | 0014 alleen bevoegde zorgmedewerkers, beperkt tot eigen clienten; 0015 gebruik van dossiers gelogd en gemonitord |
| | SP-04-02 Privacy and Data Protection | 0016 beschermd tegen verlies en ongeoorloofde inzage; 0017 rechtmatig verwerken en delen |
| PRC-05 IT Change Management | SP-05-01 Changes to ECD and ERP | 0018 wijzigingen getest en goedgekeurd voor productie; 0019 productieconfiguratie alleen via het changeproces |

Namen van processen, subprocessen en doelstellingen zijn Engels omdat de pipeline daar trefwoorden uit haalt voor de keuze van controlsjablonen.

## De vier bronnen (24 items)

### UC2 Bevindingen interne audit (historical_risks, 7)

| Ref | Subproces | Wat is er aan de hand |
|---|---|---|
| F-2024-03 | Journaalposten | Handmatige journaalposten boven EUR 50.000 zonder vastgelegde goedkeuring (9 van 25 in steekproef) |
| F-2024-07 | Toegang ECD | Geen periodieke review van gebruikersaccounts; 112 actieve accounts van vertrokken medewerkers |
| F-2025-02 | Leveranciersstamdata | AP-medewerker kan bankrekening van leverancier zelf wijzigen en goedkeuren |
| F-2025-05 | Salaris | Uren uit PlanWijs gaan zonder aansluiting naar LoonLink |
| F-2025-09 | Wijzigingen | Noodwijzigingen in FinCore zonder test of achteraf-goedkeuring (7 van 11) |
| F-2025-11 | Afsluiting | Geen afsluitchecklist; aansluitingen worden overgeslagen. Staat als lopende zin om de tekstparser te tonen |
| F-2023-12 | Zorgregistratie | Registraties niet getoetst aan zorgplan en indicatie; EUR 1,4 miljoen correcties, herhaald in 2024 |

### UC3 Incidenten (incidents, 7)

| Ref | Datum | Wat er gebeurde |
|---|---|---|
| INC-2025-114 | jun 2025 | Vertrokken thuiszorgmedewerker opent 14 clientdossiers met nog actief account. Samengevoegd met F-2024-07 |
| INC-2025-131 | jul 2025 | EUR 86.000 aan facilitaire facturen goedgekeurd door teamleider zonder mandaat na reorganisatie |
| INC-2025-158 | sep 2025 | ECD-release 8.4 op vrijdag zonder regressietest; mobiele app twee dagen plat, 1.900 medewerkers registreren op papier |
| INC-2026-007 | jan 2026 | USB-stick met 230 clientrapportages achtergelaten in taxi; gemeld bij de AP. Samengevoegd met GDPR art. 32 |
| INC-2026-019 | jan 2026 | 41 medewerkers onderbetaald doordat roostercorrecties niet zijn overgezet. Samengevoegd met F-2025-05 |
| INC-2026-023 | feb 2026 | 3,2% van de januari-declaraties afgewezen als te laat; omzet in februari geboekt |
| INC-2025-140 | aug 2025 | Veldmapping van de declaratiekoppeling direct in productie gewijzigd; twee weken afgekeurde bestanden bij Vecozo. Lopende zin |

### UC4 Fraudescenario's (fraud_scenarios, 5)

Uit de fraude-risicoworkshop 2026. Dit zijn de zaadjes voor simulaties met agents.

| Ref | Persona | Schema | Doelstelling |
|---|---|---|---|
| FS-01 | AP-medewerker | Bankrekening van leverancier omzetten naar eigen rekening (fictieve leverancier). Samengevoegd met F-2025-02 | OBJ-0007 |
| FS-02 | Controller of bestuurder | Goedkeuringsworkflow omzeilen en omzet opblazen met top-side journaalposten aan het eind van de periode | OBJ-0005 |
| FS-03 | HR of salarisadministratie | Vertrokken medewerkers niet afvoeren, spookmedewerkers laten doorbetalen | OBJ-0011 |
| FS-04 | Zorgmedewerker | Zelf registreren en goedkeuren; nooit geleverde uren declareren | OBJ-0003 |
| FS-05 | Inkoper met leverancier | Fictieve facturen gesplitst onder de goedkeuringsdrempel, geen match met order of ontvangst | OBJ-0009 |

### UC5 Regelgeving (regulatory_risks, 5)

| Ref | Subproces | Eis |
|---|---|---|
| GDPR art. 32 / NEN 7510-2 10.1 | Privacy | Versleuteling van gegevens op verwisselbare media. Samengevoegd met INC-2026-007 |
| Wmg / NZa beleidsregel declaraties | Zorgregistratie | Declaratiecodes moeten aansluiten op de indicatie; NZa handhaaft |
| WNT | Salaris | Bezoldiging van bestuurders en interim-managers binnen het maximum (klasse 4) |
| GDPR art. 6 en 30 | Privacy | Verwerkingsregister en grondslag voor gegevensdeling met drie regionale partners |
| NEN 7510-2 12.4 | Toegang ECD | Logging staat aan, maar niemand beoordeelt de logs; certificeringsaudit Q4 2026 |

## Bewuste ontwerpkeuzes in de data

- Vier paren zijn zo geschreven dat de ontdubbeling ze samenvoegt: bevinding plus incident (2x), bevinding plus fraudescenario, incident plus regelgeving. Zo laat de RCM zien dat één risico uit meerdere bronnen komt.
- Twee items staan als lopende zin (`risk_description`) in plaats van cause/event/impact, om de tekstparser te tonen.
- Subproces SP-03-02 heeft geen risico's en levert daardoor de waarschuwing "Structural Integrity" op.
- F-2025-09 en INC-2025-158 delen doelstelling OBJ-0018 en krijgen hetzelfde sjabloon; het tweede risico krijgt daardoor de design gap "Redundant".
- Categorie-aliassen ("Financial Reporting", "Cyber", "Technology", "Regulatory", "Operations") staan bewust door elkaar om de normalisatie te tonen.
- Trefwoorden in de teksten zijn gekozen zodat elk risico bij een passend controlsjabloon uitkomt: journaalposten bij Journal, toegang bij Access, wijzigingen bij Change, betalingen en salaris bij Payment, privacy en WNT bij Privacy/Compliance, fictieve zorg bij Fraud Prevention, zorgregistratie versus zorgplan bij General IT.

## IT-matrix (basis)

Per control een systeem, ITGC-type en IPE-beoordeling. Het profiel is zo opgezet dat alle vier de betrouwbaarheidsuitkomsten voorkomen.

| Systeem | Bewijs dat sterk is | Bewijs dat zwak of afwezig is |
|---|---|---|
| FinCore ERP | Approval-log journaalposten, wijzigingslog leveranciers, afsluitchecklist, configuratie-auditlog, cut-off rapport (Strong) | Exceptierapporten als bewerkbare Excel zonder aansluiting (Weak); geen regel voor de 3-way-match control van FS-05 en de mandaatcontrol van INC-2025-131 |
| ZorgDossier ECD | Goedkeuringsworkflow registratie, codevalidatie, declaratievalidatie (Strong) | Declaratiebatch-log als Excel (Weak); gebruikerslijst bewerkbaar maar aangesloten (Moderate) |
| IdentiteitsHub IAM | Toegangsworkflow systeemgegenereerd, niet bewerkbaar (Moderate) | |
| LoonLink | Stamdatarapport (Moderate), WNT-rapport (Moderate) | Geen regel voor de preventieve urencontrole van F-2025-05 |
| Bankportaal | Betaalbatch en salarisbestand aangesloten (Strong) | |
| ChangeFlow | | Alle changebewijs is handmatig bijgehouden: IPE None, drie risico's Unreliable |
| DataGuard DLP | Exportlog (Strong) | Exceptieoverzicht als Excel (Weak) |
| PrivacyPortaal | | Register en toestemmingen handmatig: IPE None |
| LogWacht SIEM | Alerts en maandelijkse logreview (Strong) | |

Uitkomst basis: 12 controls Reliable, 11 Partially Reliable, 11 Unreliable, 5 Not Assessed. Final residual: 6 Low, 12 Medium, 2 High (RISK-0009 ECD-release en RISK-0016 gesplitste facturen).

## What-if

Verhaal voor de demo: "De koppeling met IdentiteitsHub is uitgevallen. Toegangsaanvragen lopen sinds vorige maand via Excel-lijsten zonder aansluiting. En FinCore levert de goedkeuringslog van journaalposten niet meer op sinds de laatste release."

Effect: RISK-0002 (toegang ECD) van 10,0 Medium naar 16,25 High; RISK-0001 (journaalposten) van 8,0 Low naar 17,0 High. Twee regels in de matrix, twee risico's die van kleur verschieten, verder niets. Dat is de boodschap: zonder ITGC- en IPE-bewijs kun je niet steunen op een control, hoe goed die op papier ook is.

## Gebruik voor fraude-simulaties

De vijf fraudescenario's zijn geschreven als persona plus gelegenheid plus schema. Een agent die een persona speelt kan de RCM lezen als kaart van de gelegenheden: controls die Not Assessed of Unreliable zijn, zijn de zwakke plekken. In het basisscenario zijn dat:

- FS-05 gesplitste facturen: de preventieve control heeft geen matrixregel en het 3-way-match rapport is Weak. Final 21,25 High. Dit scenario "slaagt".
- FS-02 management override: de preventieve workflow is Reliable, maar het top-side rapport is een bewerkbare Excel. Detectie is zwak.
- FS-01, FS-03, FS-04: preventieve controls Reliable. Een agent moet hier een omweg bedenken, bijvoorbeeld via ChangeFlow (alle changebewijs handmatig) of via het IAM-portaal in het what-if-scenario.

Nieuwe scenario's gaan in dezelfde JSON-vorm in `fraud_scenarios`, met een eigen `reference` (FS-06 en verder) en een regel in het IT-profiel. Zie `README.md` voor de agent-loop en de trefwoorden die het sjabloon "Fraud Prevention" activeren.
