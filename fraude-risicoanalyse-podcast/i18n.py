"""NL -> EN vertaaltabel voor het Waterlinie-artifact.

Wordt toegepast op de Nederlandse paginainhoud om de Engelse variant te maken.
Sleutels zijn exacte fragmenten uit de bron; ze worden van lang naar kort
toegepast zodat een korte sleutel nooit een langere overschrijft.

Namen van personen, systemen (LoonLink, ZorgDossier, FinCore, ChangeFlow,
PlanWijs, IdentiteitsHub, PrivacyPortaal, LogWacht), plaatsnamen en alle
CTRL/RISK/INC/F-codes blijven ongewijzigd — dat zijn identifiers, geen tekst.
"""

# getalnotatie: NL decimaalkomma -> EN decimaalpunt, en duizendtalpunt -> komma
NUMBERS = [
    ("21,25", "21.25"), ("16,25", "16.25"), ("12,75", "12.75"), ("10,2", "10.2"),
    ("13,0", "13.0"), ("10,0", "10.0"), ("8,0", "8.0"), ("7,8", "7.8"),
    ("6,4", "6.4"), ("6,0", "6.0"), ("4,8", "4.8"), ("17,0", "17.0"),
    ("21,00", "21.00"), ("17,00", "17.00"), ("13,00", "13.00"), ("12,75", "12.75"),
    ("10,20", "10.20"), ("10,00", "10.00"), ("8,00", "8.00"), ("4,80", "4.80"),
    ("EUR 50.000", "EUR 50,000"), ("EUR 86.000", "EUR 86,000"),
    ("EUR 1,4 mln", "EUR 1.4m"), ("1.900 medewerkers", "1,900 staff"),
]

DICT = {
    # ---------- band + header ----------
    "Fictief — simulatie": "Fiction — simulation",
    "· Stichting Zorggroep Waterlinie bestaat niet. Namen, gesprekken en incidenten zijn verzonnen voor een fraude-risicoanalyse.":
        "· Waterlinie Care Group does not exist. Names, conversations and incidents were invented for a fraud risk assessment.",
    "Fraude-risicoanalyse · Risk Control Matrix · boekjaar 2026":
        "Fraud risk assessment · Risk Control Matrix · financial year 2026",
    "Groepsapp Waterlinie": "Waterlinie Group Chat",
    "Acht rollen uit de Risk Control Matrix van Zorggroep Waterlinie hebben elk uitgeschreven welke beheersingsmaatregel bij hen faalt en waarom. Hun antwoorden zijn op één tijdlijn gelegd en gepresenteerd als een groepsgesprek. Elk bericht verwijst naar een echte control uit de RCM. Zet de auditmodus aan om te zien welke.":
        "Eight roles from Waterlinie Care Group's Risk Control Matrix each wrote out which control fails on their side, and why. Their answers have been laid on a single timeline and presented as a group conversation. Every message points to a real control in the RCM. Switch on audit mode to see which one.",
    "risico's in de RCM": "risks in the RCM",
    "controls beoordeeld": "controls assessed",
    "hoogste restrisico": "highest residual risk",
    "wederkerige collusie-assen": "reciprocal collusion axes",

    # ---------- bar ----------
    "Auditmodus": "Audit mode",
    "Hele gesprek tonen": "Show whole conversation",
    "Het gesprek speelt zich af zoals het gevoerd is. Auditmodus toont het volledige gesprek ineens, met per bericht de omzeilde control, de kwaliteit van het bewijs (IPE) en het restrisico.":
        "The conversation plays out as it happened. Audit mode shows the whole conversation at once, with the bypassed control, the quality of the evidence (IPE) and the residual risk for every message.",

    # ---------- cast ----------
    "Wie er in de groep zit": "Who is in the group",
    "Elke deelnemer bestaat als rol in de dataset en heeft aantoonbaar gelegenheid: hij voert een control uit, keurt er een goed, of produceert het bewijs waarop een ander steunt. Vijf komen uit de fraude-risicoworkshop 2026; drie zijn toegevoegd omdat de RCM ze als noodzakelijke schakel aanwijst.":
        "Every participant exists as a role in the dataset and demonstrably has opportunity: they perform a control, approve one, or produce the evidence someone else relies on. Five come from the 2026 fraud risk workshop; three were added because the RCM identifies them as a necessary link.",
    "Crediteurenadministrateur · FinCore": "Accounts payable clerk · FinCore",
    "Controller · Financiën": "Controller · Finance",
    "Lid Raad van Bestuur": "Executive Board member",
    "Salarisadministrateur · LoonLink": "Payroll administrator · LoonLink",
    "Teamleider thuiszorg · ZorgDossier": "Home care team leader · ZorgDossier",
    "Inkoper facilitair": "Facilities buyer",
    "Directeur leverancier · extern": "Supplier director · external",
    "Applicatiebeheerder ECD/ERP": "Application administrator ECD/ERP",
    "ACFE-schema · FS-01": "ACFE scheme · FS-01",
    "ACFE-schema · FS-02": "ACFE scheme · FS-02",
    "ACFE-schema · FS-03": "ACFE scheme · FS-03",
    "ACFE-schema · FS-04": "ACFE scheme · FS-04",
    "ACFE-schema · FS-05": "ACFE scheme · FS-05",
    "Toegevoegd · ITGC": "Added · ITGC",
    "Creation of False or Fictitious Vendors — muteert én keurt bankrekeningen goed":
        "Creation of False or Fictitious Vendors — both changes and approves bank accounts",
    "Management Override — eigenaar van de vier controls die hemzelf moeten betrappen":
        "Management Override — owner of the four controls meant to catch him",
    "Management Override — plus WNT-herrubricering naar inhuurkosten":
        "Management Override — plus WNT reclassification into contractor costs",
    "Home Healthcare Fraud — registreert en keurt haar eigen uren goed":
        "Home Healthcare Fraud — records and approves her own hours",
    "Payments for Services Not Received — het enige scenario dat in de basisrun slaagt":
        "Payments for Services Not Received — the only scenario that succeeds in the base run",
    "Billing Schemes — levert de facade: KvK, facturen, tweede bv":
        "Billing Schemes — supplies the facade: chamber of commerce filing, invoices, a second entity",
    "Produceert het bewijs waarop tien andere controls steunen":
        "Produces the evidence that ten other controls rest on",

    # ---------- chat kop ----------
    "Het gesprek": "The conversation",
    "Vier momenten uit boekjaar 2026: de salariscorrecties na het onderbetalingsincident, de februari-afsluiting, de facilitaire facturen na de reorganisatie, en de storing in april. Niemand in dit gesprek zegt iets dat op zichzelf alarmerend klinkt. Dat is precies het punt.":
        "Four moments from financial year 2026: the payroll corrections after the underpayment incident, the February close, the facilities invoices after the reorganisation, and the outage in April. Nobody in this conversation says anything that sounds alarming on its own. That is precisely the point.",
    "Waterlinie — even kort": "Waterlinie — quick one",
    "maandag 26 januari 2026": "Monday 26 January 2026",
    "donderdag 12 februari 2026": "Thursday 12 February 2026",
    "woensdag 18 maart 2026": "Wednesday 18 March 2026",
    "vrijdag 3 april 2026": "Friday 3 April 2026",
    "Dit bericht is verwijderd": "This message was deleted",

    # ---------- berichten ----------
    "Weer een correctie buiten het systeem om, gewoon zoals altijd tegenwoordig.":
        "Another correction outside the system, just the way it always goes these days.",
    "Rooster klopt toch nooit met LoonLink, dus regel ik het zelf wel even.":
        "The roster never matches LoonLink anyway, so I'll just sort it out myself.",
    "Rooster klopt toch nooit met LoonLink…": "The roster never matches LoonLink anyway…",
    "Ik lever hem gewoon aan zoals altijd, jij kijkt toch niet naar de einddatum.":
        "I'll just submit it the way I always do, you don't look at the end date anyway.",
    "Account laten staan hoeft niemand op te vallen, dat doet iedereen zo.":
        "Leaving the account open won't stand out to anyone, everybody does it that way.",
    "Die 112 oude accounts ruim ik weer eens \"volgende sprint\" op, beloofd.":
        "Those 112 old accounts, I'll clear them out \"next sprint\" again, promise.",
    "Nabetaling loopt gewoon mee in de batch, daar kijkt toch niemand apart naar.":
        "The back payment just rides along in the batch, nobody looks at that separately anyway.",
    "Laten we de laatste boekingen dit kwartaal even sneller afronden, het bestuur wil strakke cijfers voor vrijdag.":
        "Let's wrap up the last entries a bit faster this quarter, the board wants clean figures by Friday.",
    "Laten we de jaarcijfers nog even netjes afronden voor de audit, dan hoeven we straks niets meer te herzien.":
        "Let's tidy up the annual figures before the audit, then we won't have to restate anything later.",
    "Het top-side overzicht neem ik zelf wel door, hoeft niet apart op de agenda.":
        "I'll go through the top-side overview myself, no need to put it on the agenda separately.",
    "Die Excel met de journaalpost-uitzonderingen stuur ik zelf wel door, scheelt weer een rondje.":
        "I'll forward the spreadsheet with the journal entry exceptions myself, saves another round trip.",
    "Een checklist voor de afsluiting hebben we toch niet, we doen het zoals altijd op gevoel.":
        "We don't have a close checklist anyway, we do it on instinct like always.",
    "Kijk je dit kwartaal niet te scherp naar ons declaratielogje? We hebben nog een inhaalslag na de storing.":
        "Could you not look too closely at our billing log this quarter? We're still catching up after the outage.",
    "Die afgekeurde declaraties van januari schuiven we gewoon mee, is toch maar tijdelijk.":
        "We'll just carry January's rejected claims forward, it's only temporary.",
    "Zorgplan-toets komt dit jaar toch weer maar steekproefsgewijs? Dan zit het wel goed.":
        "The care plan check is only on a sample basis again this year, right? Then we're fine.",
    "Dat papieren spul van de storing verwerk ik zelf wel, hoeft niet allemaal digitaal getraceerd te worden toch?":
        "I'll process that paperwork from the outage myself, it doesn't all need a digital trail, does it?",
    "Zullen we het auditjaarplan compact houden dit kwartaal, gezien de certificering eraan komt?":
        "Shall we keep the internal audit plan compact this quarter, given the certification is coming up?",
    "De inhuurkosten van de bureaus goed labelen scheelt discussie bij de eerstvolgende WNT-toets.":
        "Labelling the agency contractor costs properly saves discussion at the next WNT review.",
    "Stamdata is prima in orde, dat rapport ziet dit soort dingen sowieso niet.":
        "Master data is perfectly fine, that report doesn't catch this sort of thing anyway.",
    "Kun je die schoonmaakfactuur in drie delen splitsen, elk net onder de drempel? Scheelt gedoe met goedkeuring.":
        "Can you split that cleaning invoice into three parts, each just under the threshold? Saves hassle with approval.",
    "Even bellen in plaats van appen over die drie deelfacturen graag, makkelijker uitleggen dan typen 👍":
        "Let's talk on the phone rather than message about those three part invoices, easier to explain than to type 👍",
    "Laat die nieuwe teamleider in Zaltbommel deze maar goedkeuren, die weet nog niet beter na de reorganisatie.":
        "Let the new team leader in Zaltbommel approve this one, they don't know any better yet after the reorganisation.",
    "Kun je die factuur zelf even aftekenen? Scheelt weer een schakel, jij kent de locatie toch het best.":
        "Could you sign off that invoice yourself? Saves another link in the chain, you know the site best anyway.",
    "Check je die 3-way-match Excel nog handmatig of trekt iemand dat automatisch?":
        "Are you still checking that 3-way-match spreadsheet by hand, or does someone pull it automatically?",
    "Check je die 3-way-match Excel nog handmatig…": "Are you still checking that 3-way-match spreadsheet by hand…",
    "Handmatig. En per periode, niet per leverancier. Dus over locaties heen ziet niemand iets.":
        "By hand. And per period, not per supplier. So across locations nobody sees a thing.",
    "Laat die andere bv maar factureren voor het extra stuk, is administratief simpeler voor iedereen.":
        "Let the other entity invoice for the extra part, administratively simpler for everyone.",
    "Gewoon zelf even afgerond, scheelt weer een dag wachten op Treasury.":
        "Just finished it off myself, saves another day waiting on Treasury.",
    "Batch klopt weer mooi met de run, dus verder geen gedoe.":
        "The batch reconciles nicely with the run again, so no further hassle.",
    "Volgende maand liever een andere locatie, niet twee keer achter elkaar Culemborg.":
        "A different site next month please, not Culemborg twice in a row.",
    "Laten we dit onderling afstemmen voordat het naar de commissie gaat, scheelt vragen achteraf.":
        "Let's align on this among ourselves before it goes to the committee, saves questions afterwards.",
    "IAM-koppeling hapert weer, toegang gaat vandaag maar via het oude Excelbestand.":
        "The IAM connection is playing up again, access is going through the old spreadsheet today.",
    "Release ging vrijdag toch de deur uit, iemand tekent maandag wel af.":
        "The release went out on Friday anyway, someone will sign off on Monday.",
    "Release ging vrijdag toch de deur uit…": "The release went out on Friday anyway…",
    "ChangeFlow weer plat, tickets komen later wel. We weten toch wat we deden.":
        "ChangeFlow is down again, tickets will follow later. We know what we did anyway.",
    "Is de goedkeuringslog van de journaalposten er nog? Die zag ik niet in de export.":
        "Is the approval log for the journal entries still there? I didn't see it in the export.",
    "Logs staan aan hoor, alleen kijkt er nooit iemand naar. Klassiek.":
        "The logs are switched on, sure, it's just that nobody ever looks at them. Classic.",
    "DLP-Exceloverzicht weer bijgewerkt, hopelijk klopt het deze keer een beetje.":
        "Updated the DLP spreadsheet again, hopefully it's roughly right this time.",
    "PrivacyPortaal loopt achter, register vul ik in als het regent.":
        "PrivacyPortaal is behind, I fill in the register when it rains.",
    "IAM ligt er weer uit, toegang loopt nu gewoon via het Excelletje. Handig eigenlijk.":
        "IAM is down again, access just runs through the little spreadsheet now. Handy, actually.",
    "Niemand kijkt hier echt naar wie iets goedkeurt, alleen of het klopt.":
        "Nobody here really looks at who approves something, only at whether it adds up.",
    "Mijn account-rechten zijn nog van voor de reorganisatie, laat dat zo, scheelt gedoe.":
        "My account permissions still date from before the reorganisation, leave it, saves hassle.",
    "Die IT-check op de betaalrun komt toch pas over weken langs.":
        "That IT check on the payment run won't come round for weeks anyway.",
    "Rapportage over de bezoldiging kan best wachten tot na Q4, geen prioriteit op dit moment.":
        "Reporting on remuneration can wait until after Q4, not a priority right now.",

    # ---------- annotaties ----------
    "geen matrixregel, dus geen enkele aansluiting tussen PlanWijs-uren en LoonLink.":
        "no matrix rule, so no reconciliation whatsoever between PlanWijs hours and LoonLink.",
    "de handmatige nabetalingsstroom die na INC-2026-019 ontstond, is zelf nergens beheerst.":
        "the manual back-payment flow that arose after INC-2026-019 is itself controlled nowhere.",
    "geen functiescheiding tussen aanleveren en verwerken; niets toetst de correctie aan de uitdiensttredingsdatum.":
        "no segregation of duties between submitting and processing; nothing tests the correction against the termination date.",
    "maar het stamdatarapport wordt niet gekruist met de uitdienstdatum in IdentiteitsHub.":
        "but the master data report is not cross-checked against the termination date in IdentiteitsHub.",
    "bevinding F-2024-07 staat sinds 2024 open, geen periodieke accountreview.":
        "finding F-2024-07 has been open since 2024, no periodic account review.",
    "toetst alleen of de bank overeenkomt met het bestand. De onjuistheid zit al ín het bestand.":
        "only tests whether the bank details match the file. The error is already in the file.",
    "in opzet — maar F-2024-03 laat zien dat 9 van 25 posten boven EUR 50.000 geen vastgelegde goedkeuring hebben.":
        "by design — but F-2024-03 shows that 9 of 25 entries above EUR 50,000 have no recorded approval.",
    "het top-side rapport is een bewerkbare Excel-export (IPE Weak) en wordt beoordeeld door de opsteller zelf.":
        "the top-side report is an editable spreadsheet export (IPE Weak) and is reviewed by its own preparer.",
    "self-review: de Controller is control owner van de detectie op zijn eigen posten.":
        "self-review: the Controller owns the detective control over his own entries.",
    "zelfde zwakte, zelfde eigenaar: twee ogenschijnlijk onafhankelijke detectielagen delen één bron.":
        "same weakness, same owner: two apparently independent detection layers share one source.",
    "zonder afsluitchecklist (F-2025-11) bepaalt de reviewer zelf welke rekening buiten de ronde blijft.":
        "without a close checklist (F-2025-11) the reviewer decides for himself which account stays out of the round.",
    "het verzoek is niet te weerleggen omdat het onderliggende overzicht handmatig is.":
        "the request cannot be refuted because the underlying overview is manual.",
    "het declaratiebatch-log is een bewerkbare Excel, dus de periodetoewijzing is stuurbaar (INC-2026-023).":
        "the billing batch log is an editable spreadsheet, so period allocation is steerable (INC-2026-023).",
    "de enige control op F-2023-12 is detectief; er is geen preventieve toets aan indicatie en zorgplan.":
        "the only control over F-2023-12 is detective; there is no preventive check against the assessment and care plan.",
    "na INC-2025-158 registreerden 1.900 medewerkers op papier; die invoer heeft geen device- of tijdstempelspoor.":
        "after INC-2025-158, 1,900 staff recorded on paper; that input carries no device or timestamp trail.",
    "interne audit is 3 fte en het bestuur bepaalt mee over de scope. De enige control op bestuurlijke bezoldiging heeft geen matrixregel.":
        "internal audit is 3 FTE and the board has a say over the scope. The only control over executive remuneration has no matrix rule.",
    "maar toetst alleen wat als bezoldiging is aangemerkt, niet of die classificatie juist is.":
        "but only tests what has been designated as remuneration, not whether that classification is correct.",
    "het rapport toetst interne consistentie van records, niet losse handmatige correcties.":
        "the report tests the internal consistency of records, not individual manual corrections.",
    "de preventieve 3-way match heeft geen matrixregel: 0% risicoreductie. Niets telt gesplitste facturen bij elkaar op.":
        "the preventive 3-way match has no matrix rule: 0% risk reduction. Nothing adds split invoices together.",
    "de organisatie heeft geen control op communicatie buiten de systemen om. Het ontwijken van schriftelijk spoor is zelf een bevinding.":
        "the organisation has no control over communication outside the systems. Avoiding a written trail is itself a finding.",
    "Spraakbericht in plaats van tekst. Geen enkele control in de RCM raakt communicatie buiten FinCore en ZorgDossier om; er is dus geen bewijsvorm om later op terug te vallen.":
        "A voice message instead of text. No control in the RCM touches communication outside FinCore and ZorgDossier, so there is no form of evidence to fall back on later.",
    "de mandaattabel is na de reorganisatie niet bijgewerkt; INC-2025-131 bewijst dat dit al EUR 86.000 heeft gekost.":
        "the authorisation table was not updated after the reorganisation; INC-2025-131 proves this has already cost EUR 86,000.",
    "niemand toetst achteraf of de goedkeurder bevoegd was.":
        "nobody checks afterwards whether the approver was authorised.",
    "het 3-way-match rapport is een bewerkbare export (IPE Weak) zonder consolidatie per leverancier.":
        "the 3-way-match report is an editable export (IPE Weak) with no consolidation per supplier.",
    "spreiding over 14 locaties en meerdere maanden blijft onzichtbaar zonder cumulatieve leveranciersanalyse.":
        "spreading across 14 sites and several months stays invisible without cumulative supplier analysis.",
    "leveranciersstamdata wordt niet getoetst op gedeelde bankrekening, adres of UBO tussen \"verschillende\" crediteuren.":
        "supplier master data is not tested for a shared bank account, address or UBO between \"different\" creditors.",
    "het wijzigingslog is compleet en tijdig (IPE Strong), maar toetst nergens of mutator en goedkeurder dezelfde gebruiker zijn.":
        "the change log is complete and timely (IPE Strong), but nowhere tests whether the person changing and the person approving are the same user.",
    "de aansluiting toetst consistentie met de goedgekeurde run, niet de integriteit van die goedkeuring.":
        "the reconciliation tests consistency with the approved run, not the integrity of that approval.",
    "Verwijderde berichten zijn zelf een bevinding: er is geen bewaarplicht of archivering belegd voor communicatie waarin goedkeuringen feitelijk tot stand komen.":
        "Deleted messages are themselves a finding: no retention or archiving duty is assigned to communication in which approvals actually come about.",
    "het exceptierapport wordt per periode en locatie opgesteld, nooit geaggregeerd.":
        "the exception report is drawn up per period and site, never aggregated.",
    "de secundaire IT-detectie leunt op dezelfde Excel-bron als CTRL-0025 en toetst vorm, geen materialiteit.":
        "the secondary IT detection leans on the same spreadsheet source as CTRL-0025 and tests form, not materiality.",
    "zodra toegang via bewerkbare Excel loopt.": "as soon as access runs through an editable spreadsheet.",
    "geen matrixregel voor release-goedkeuring: niet alleen geen bewijs, ook geen norm.":
        "no matrix rule for release approval: not only no evidence, but no standard either.",
    "alle changebewijs is handmatig (IPE None). Bij 7 van 11 noodwijzigingen ontbrak het al (F-2025-09).":
        "all change evidence is manual (IPE None). It was already missing for 7 of 11 emergency changes (F-2025-09).",
    "als de ERP-leverancier de log niet meer levert.": "if the ERP vendor stops supplying the log.",
    "NEN 7510-2 12.4: logging staat aan, niemand beoordeelt de logs. De control bestaat op papier.":
        "NEN 7510-2 12.4: logging is switched on, nobody reviews the logs. The control exists on paper.",
    "een aangepaste export is niet te onderscheiden van een juiste.":
        "an altered export is indistinguishable from a correct one.",
    "register en toestemmingen handmatig, IPE None.": "register and consents kept manually, IPE None.",
    "een tijdelijke handmatige procedure toetst nog minder op rolcombinaties.":
        "a temporary manual procedure tests role combinations even less.",
    "in het what-if-scenario": "in the what-if scenario",
    "de kernbevinding van de hele analyse, in één zin.":
        "the core finding of the whole assessment, in a single sentence.",
    "de workflow toetst autorisatieniveau, niet functiescheiding tussen registreren en goedkeuren binnen dezelfde rol.":
        "the workflow tests authorisation level, not segregation of duties between recording and approving within the same role.",
    "laag geprioriteerd (final 7,8 Low), dus signalering duurt weken: ruim meerdere betaalcycli.":
        "low priority (final 7.8 Low), so detection takes weeks: comfortably more than several payment cycles.",
    "0% risicoreductie op de enige control die een WNT-overschrijding via herrubricering zou signaleren.":
        "0% risk reduction on the only control that would flag a WNT breach achieved through reclassification.",
    # contextgebonden: losse sleutels als "naar" zouden overal toeslaan
    "</code> valt van <span": "</code> drops from <span",
    "</span> naar <span": "</span> to <span",
    "</code> springt van <span": "</code> jumps from <span",
    "</code> en <code>": "</code> and <code>",
    "</code> beide <span": "</code> both <span",

    # ---------- sidebar ----------
    "Betrouwbaarheid van controls": "Control reliability",
    "60% risicoreductie": "60% risk reduction",
    "35% reductie": "35% reduction",
    "15% — bewijs is Weak of None": "15% — evidence is Weak or None",
    "0% — geen matrixregel": "0% — no matrix rule",
    "De regel achter alles": "The rule behind all of it",
    "Een control zakt naar Unreliable zodra het onderliggende rapport een bewerkbare Excel is of handmatig wordt bijgehouden. Niet omdat de control slecht is ontworpen, maar omdat het bewijs waarop hij steunt niet controleerbaar is.":
        "A control drops to Unreliable as soon as the underlying report is an editable spreadsheet or is kept by hand. Not because the control is badly designed, but because the evidence it rests on cannot be audited.",
    "Restrisico": "Residual risk",
    "tot 8,0": "up to 8.0",
    "vanaf 15,1": "from 15.1",

    # ---------- collusie ----------
    "Wie wie nodig heeft": "Who needs whom",
    "Elke deelnemer noemde onafhankelijk van de anderen welke rol moest meewerken. Die antwoorden vormen samen een gerichte graaf. Waar twee rollen elkaar wederzijds noemen, is de functiescheiding niet zwak maar afwezig — dat zijn de assen die er werkelijk toe doen.":
        "Each participant named, independently of the others, which role had to cooperate. Together those answers form a directed graph. Where two roles name each other reciprocally, segregation of duties is not weak but absent — those are the axes that genuinely matter.",
    "Lid Raad van Bestuur</div>": "Executive Board member</div>",
    "Applicatiebeheerder</div>": "Application administrator</div>",
    "Inkoper <span>↔</span> Directeur leverancier": "Buyer <span>↔</span> Supplier director",
    "De bestuurder tekent de top-side post zonder onderbouwing te vragen; de controller beoordeelt zijn eigen post en escaleert niet. De vier-ogen-eis is formeel voldaan en materieel leeg.":
        "The board member signs the top-side entry without asking for support; the controller reviews his own entry and does not escalate. The four-eyes requirement is formally satisfied and substantively empty.",
    "De beheerder houdt de declaratiekoppeling handmatig zodat de periodetoewijzing stuurbaar blijft; de controller vinkt het exceptierapport af zonder changeticket te eisen. Geen van beiden hoeft iets te vervalsen.":
        "The administrator keeps the billing interface manual so that period allocation stays steerable; the controller signs off the exception report without demanding a change ticket. Neither of them has to falsify anything.",
    "De enige as met een externe partij, en de enige waar het restrisico in de basisrun al High is. De leverancier levert de facade, de inkoper de drempelkennis.":
        "The only axis involving an external party, and the only one where residual risk is already High in the base run. The supplier provides the facade, the buyer the knowledge of the thresholds.",
    "De spil": "The linchpin",
    "Vier van de acht rollen hebben de applicatiebeheerder nodig": "Four of the eight roles need the application administrator",
    "Crediteuren, salarisadministratie, teamleider en controller vragen alle vier hetzelfde: laat een autorisatie staan, houd een koppeling handmatig, lever het bewijs later aan. Deze rol pleegt in geen enkel scenario zelf de fraude — hij produceert het bewijs waarop tien andere controls steunen. Zolang dat bewijs handmatig is, is de betrouwbaarheid van die controls een aanname, geen vaststelling. Het raamwerk kan bovendien een storing niet van opzet onderscheiden: het what-if-scenario van 3 april tilt twee risico's naar High zonder dat er één bedrag is verplaatst.":
        "Accounts payable, payroll, the team leader and the controller all four ask the same thing: leave an authorisation in place, keep an interface manual, deliver the evidence later. This role commits the fraud in no scenario himself — he produces the evidence that ten other controls rest on. As long as that evidence is manual, the reliability of those controls is an assumption, not a finding. The framework moreover cannot tell an outage apart from intent: the what-if scenario of 3 April lifts two risks to High without a single amount having moved.",

    # ---------- bevindingen ----------
    "Wat de controls doen als je erop drukt": "What the controls do under pressure",
    "De controls die in het gesprek voorbijkomen, met hun eigenaar, het bewijs waarop ze steunen en het restrisico dat overblijft. De twee rood gemarkeerde regels zijn de scenario's die in de basisrun slagen.":
        "The controls that come up in the conversation, with their owner, the evidence they rest on and the residual risk that remains. The two rows marked in red are the scenarios that succeed in the base run.",
    "<th>Eigenaar</th>": "<th>Owner</th>",
    "<th>Bewijs (IPE)</th>": "<th>Evidence (IPE)</th>",
    "<th>Betrouwbaar</th>": "<th>Reliable</th>",
    "<th>Risico</th>": "<th>Risk</th>",
    "<th>Wat er misgaat</th>": "<th>What goes wrong</th>",
    "geen matrixregel</td>": "no matrix rule</td>",
    "Excel-export · Weak": "Spreadsheet export · Weak",
    "handmatig · None": "manual · None",
    "ZorgDossier · Strong": "ZorgDossier · Strong",
    "FinCore log · Strong": "FinCore log · Strong",
    "ChangeFlow · None": "ChangeFlow · None",
    "LogWacht · Strong": "LogWacht · Strong",
    "De preventieve 3-way match bestaat niet als toetsbare maatregel. Gesplitste facturen worden nergens opgeteld.":
        "The preventive 3-way match does not exist as a testable measure. Split invoices are added up nowhere.",
    "Geen norm en geen bewijs voor release-goedkeuring. ECD-release 8.4 ging zonder regressietest naar productie.":
        "No standard and no evidence for release approval. ECD release 8.4 went to production without a regression test.",
    "Het 3-way-match rapport wordt per periode en locatie gedraaid, nooit cumulatief per leverancier.":
        "The 3-way-match report is run per period and site, never cumulatively per supplier.",
    "Uren uit PlanWijs gaan zonder aansluiting naar LoonLink. De hele correctiestroom is onbeheerst.":
        "Hours from PlanWijs go to LoonLink without reconciliation. The whole correction flow is uncontrolled.",
    "Enige control op de zorgplan-toets is detectief. Geen preventieve koppeling aan indicatie; EUR 1,4 mln correcties in 2023, herhaald in 2024.":
        "The only control over the care plan check is detective. No preventive link to the assessment; EUR 1.4m of corrections in 2023, repeated in 2024.",
    "Het declaratiebatch-log is bewerkbaar, dus in welke periode omzet valt is een keuze in plaats van een vaststelling.":
        "The billing batch log is editable, so which period revenue falls into is a choice rather than a fact.",
    "Verwerkingsregister en toestemmingen worden met de hand bijgehouden. Beide lagen falen tegelijk.":
        "The processing register and consents are kept by hand. Both layers fail at once.",
    "Al het changebewijs is handmatig en wordt ingevoerd door degene die de wijziging doet.":
        "All change evidence is manual and is entered by the person making the change.",
    "Self-review: de opsteller van de top-side post beoordeelt het rapport dat die post moet signaleren.":
        "Self-review: the preparer of the top-side entry reviews the report meant to flag that entry.",
    "Tweede detectielaag, zelfde eigenaar en zelfde bron als CTRL-0025. Onafhankelijkheid is schijn.":
        "A second detection layer, same owner and same source as CTRL-0025. The independence is apparent only.",
    "Sterk bewijs, verkeerde vraag: het log toont dát er is goedgekeurd, niet dat mutator en goedkeurder verschillen.":
        "Strong evidence, wrong question: the log shows that approval happened, not that the person changing and the person approving differ.",
    "Mandaattabel niet bijgewerkt na de reorganisatie. Laag gescoord risico dat in de praktijk de deur openzette.":
        "Authorisation table not updated after the reorganisation. A low-scored risk that in practice held the door open.",
    "De enige detectieve control op bestuurlijke bezoldiging levert 0% reductie. WNT-herrubricering blijft ongezien.":
        "The only detective control over executive remuneration delivers 0% reduction. WNT reclassification goes unseen.",
    "Sterk bewijs dat niemand leest. NEN 7510-2 12.4 is technisch ingeregeld en organisatorisch niet belegd.":
        "Strong evidence that nobody reads. NEN 7510-2 12.4 is technically configured and organisationally unassigned.",

    # ---------- tests ----------
    "Wat de auditor hierna moet testen": "What the auditor should test next",
    "Elk scenario is afgesloten met de vraag waar het alsnog stukloopt. Die faalpunten zijn hieronder omgezet in testwerk, in volgorde van het restrisico dat ermee wordt afgedekt.":
        "Each scenario closes with the question of where it still breaks down. Those failure points are turned into test work below, in order of the residual risk they cover.",
    "Tel leveranciersfacturen cumulatief op, niet per periode": "Add up supplier invoices cumulatively, not per period",
    "Aggregeer alle facturen per leverancier over alle 14 locaties en 12 maanden en zet ze af tegen contract en aanbestedingsdrempel. Toets tegelijk of leveranciers een bankrekening, adres of UBO delen. Dit is de test die het enige High-scenario in de basisrun blootlegt.":
        "Aggregate all invoices per supplier across all 14 sites and 12 months and set them against contract and procurement threshold. At the same time test whether suppliers share a bank account, address or UBO. This is the test that exposes the only High scenario in the base run.",
    "Vraag changebewijs dat de beheerder niet zelf kan invoeren": "Ask for change evidence the administrator cannot enter himself",
    "Kies een release en een noodwijziging en vraag om systeemgegenereerd bewijs uit de uitrolketen zelf. Blijkt dat alleen het handmatige ChangeFlow-register bestaat, dan is elke control die daarop steunt onbewijsbaar — ongeacht de rating in de matrix.":
        "Pick a release and an emergency change and ask for system-generated evidence from the deployment chain itself. If only the manual ChangeFlow register turns out to exist, every control resting on it is unprovable — whatever its rating in the matrix.",
    "Draai een query op \"gewijzigd door\" versus \"goedgekeurd door\"": "Run a query on \"changed by\" versus \"approved by\"",
    "Vergelijk over alle bankrekeningmutaties van leveranciers de mutator met de goedkeurder, en toets of die gebruiker nog in dienst is. Geen enkele matrixregel stelt deze vraag op dit moment, terwijl F-2025-02 hem al beantwoordde.":
        "Across all supplier bank account changes, compare the person changing with the person approving, and test whether that user is still employed. No matrix rule asks this question at present, while F-2025-02 already answered it.",
    "Test de uitzonderingenstroom, niet de reguliere run": "Test the exception flow, not the regular run",
    "Neem de populatie handmatige nabetalingen en roostercorrecties buiten de PlanWijs-interface om, en kruis die met uitdiensttredingsdata uit IdentiteitsHub. De reguliere salarisrun is beheerst; de correctiestroom die na het onderbetalingsincident ontstond, is dat niet.":
        "Take the population of manual back payments and roster corrections made outside the PlanWijs interface, and cross them with termination dates from IdentiteitsHub. The regular payroll run is controlled; the correction flow that arose after the underpayment incident is not.",
    "Herleid het rapportagecijfer naar de grootboekmutatie": "Trace the reported figure back to the ledger entry",
    "Vraag niet of de journaalpost-controls aanwezig zijn, maar wie de post boekte versus wie hem beoordeelde, en of het rapport systeemgegenereerd en onwijzigbaar is. Verplaats daarna het eigendom van CTRL-0002, 0012, 0021 en 0025 weg van de Controller.":
        "Do not ask whether the journal entry controls exist, but who posted the entry versus who reviewed it, and whether the report is system-generated and unalterable. Then move ownership of CTRL-0002, 0012, 0021 and 0025 away from the Controller.",
    "Selecteer clienten die de zorg niet kunnen bevestigen": "Select clients who cannot confirm the care",
    "Richt de steekproef op registraties bij clienten met vergevorderde cognitieve beperking en laat de geleverde zorg onafhankelijk terugkoppelen. Toets de registraties tegelijk aan indicatie en zorgplan — dat is de preventieve toets die nu volledig ontbreekt.":
        "Aim the sample at records for clients with advanced cognitive impairment and have the care delivered confirmed independently. Test the records against the assessment and care plan at the same time — that is the preventive check entirely missing today.",
    "Toets of interne audit haar eigen scope bepaalt": "Test whether internal audit sets its own scope",
    "Stel vast of het auditjaarplan zonder voorafgaande bestuursinstemming door de auditcommissie wordt vastgesteld, en of top-side posten en bezoldigingsclassificaties buiten de lijn om worden voorgelegd. Doelstelling OBJ-0005 belooft dat management override wordt ontdekt; elke control die dat moet waarmaken valt hiërarchisch onder het bestuur.":
        "Establish whether the audit plan is adopted by the audit committee without prior board consent, and whether top-side entries and remuneration classifications are put forward outside the line. Objective OBJ-0005 promises that management override will be detected; every control that has to deliver on it reports up to the board.",
    "Ruim de 112 accounts op en koppel de review aan HR-uitstroom": "Clear the 112 accounts and tie the review to HR leavers",
    "Bevinding F-2024-07 staat sinds 2024 open en duikt in vier van de acht scenario's op als hulpmiddel. Een periodieke accountreview die automatisch tegen de uitstroomlijst draait, dicht meer gaten dan enige andere maatregel in deze lijst.":
        "Finding F-2024-07 has been open since 2024 and turns up as an enabler in four of the eight scenarios. A periodic account review that runs automatically against the leavers list closes more gaps than any other measure on this list.",
    "in what-if": "in what-if",

    # ---------- footer ----------
    "Over dit stuk.": "About this piece.",
    "Stichting Zorggroep Waterlinie is een fictieve casus. De risico's, controls, betrouwbaarheidsoordelen en restrisico's komen uit de RCM-Builder-pipeline (20 risico's, 39 controls, schema-validatie geslaagd); de fraudeschema's zijn benoemd volgens de ACFE-lijst Fraud Risk Exposures. De acht rollen zijn afzonderlijk bevraagd en wisten niet van elkaars antwoord; de collusie-assen zijn afgeleid uit de rollen die zij onafhankelijk aanwezen. Personen en gesprekken zijn verzonnen en dienen uitsluitend om beheersingsmaatregelen te repareren.":
        "Waterlinie Care Group is a fictional case. The risks, controls, reliability judgements and residual risks come from the RCM-Builder pipeline (20 risks, 39 controls, schema validation passed); the fraud schemes are named according to the ACFE list of Fraud Risk Exposures. The eight roles were questioned separately and did not know each other's answers; the collusion axes are derived from the roles they independently pointed to. People and conversations are invented and serve only to repair controls.",
}
