# Plan — Fraudescenario-analyse via actor-simulatie

Status: opgesteld 2026-09-08, vóór ontvangst dataset. Alle ID-verwijzingen zijn placeholders.

## 0. Doel en kader

Doel: de fraudekwetsbaarheid van het procesframework blootleggen door per actor een
aanvalsplan te laten uitschrijven, en het resultaat presenteren als een gesimuleerd
WhatsApp-groepsgesprek waarin de collusie zichtbaar wordt.

Kader: dit is een fraud risk assessment / red-teaming-oefening op een beheersingsraamwerk.
Alle personen, bedrijven en gebeurtenissen in het eindproduct zijn fictief. Het eindproduct
draagt zichtbaar het label FICTIEF — SIMULATIE en bevat geen namen van echte medewerkers,
klanten of leveranciers uit de dataset. Waar de dataset echte namen bevat, worden die
vervangen door rolgebonden personages (zie 5.2).

Waarde zit in de mapping, niet in het verhaal: elk bericht in de chat moet herleidbaar zijn
naar een concrete control-tekortkoming of een risico zonder dekkende control.

## 1. Intake-checklist dataset

Bij ontvangst eerst vaststellen wat er is. Minimaal nodig per bestand:

- Processen: proces-ID, naam, eigenaar/rol, processtappen, systemen, in-/outputs.
- Controls: control-ID, gekoppeld proces + risico, omschrijving, type (preventief/detectief),
  uitvoering (handmatig/geautomatiseerd/IT-dependent), frequentie, uitvoerder-rol,
  reviewer-rol, key/non-key, drempelbedragen, laatste testdatum en testuitkomst.
- Risico's: risico-ID, omschrijving, inherent risico, restrisico, gekoppelde controls, eigenaar.
- CRM: entiteiten en velden (account, contact, opportunity, quote, order, contract),
  stages en statusovergangen, rollen/profielen en rechten, goedkeuringsworkflows,
  validatieregels, veldhistorie/auditlog-instellingen, integraties naar ERP/facturatie.

Ontbreekt iets, dan wordt dat expliciet als aanname genoteerd in het eindproduct — niet
stilzwijgend ingevuld.

## 2. Fase 0 — Normalisatie

1. Alles inlezen naar één werkbestand met vaste kolomnamen.
2. Koppeltabellen bouwen: risico -> control, control -> proces, proces -> rol, rol -> CRM-recht.
3. Wezen opsporen: risico's zonder control, controls zonder risico, processtappen zonder control,
   controls zonder benoemde uitvoerder of reviewer.

Deliverable: `01-genormaliseerd.md` met de koppeltabellen en de wezenlijsten.

## 3. Fase 1 — Control-gap analyse (de munitie voor de agents)

Zes analyses, elk levert een lijst met control-ID's en een korte motivering:

1. **SoD-matrix.** Per rol de combinatie van bevoegdheden. Rood bij: aanmaken + goedkeuren,
   invoeren + betalen, muteren masterdata + transacties, en bij reviewer == uitvoerder.
2. **Drempelanalyse.** Alle bedragsgrenzen in controls en goedkeuringsworkflows. Elke drempel
   is een uitnodiging tot opsplitsen; noteer de exacte grens en of er een detectieve control
   op cumulatie zit.
3. **Preventief/detectief-balans.** Processen die alleen detectief zijn beheerst, en met welke
   vertraging (maand-, kwartaalcontrole = venster waarin geld al weg is).
4. **Testdekking.** Controls die nooit getest zijn, faalpunten uit eerdere tests, en controls
   die alleen op opzet en niet op werking zijn getoetst.
5. **Systeemafhankelijkheid.** Welke controls leunen op een CRM-veld, validatieregel of workflow
   die door een admin te wijzigen is. Dat maakt de CRM-admin een sleutelactor voor iedereen.
6. **Restrisico-inconsistentie.** Waar het restrisico laag is gescoord terwijl de onderliggende
   controls zwak, ongetest of vertrouwd-op-één-persoon zijn. Dit is de blinde vlek van de
   organisatie en daarmee het meest aantrekkelijke aanvalsterrein.

Deliverable: `02-control-gaps.md`, gaps gerangschikt op exploiteerbaarheid.

## 4. Fase 2 — Actorderivatie en fan-out

### 4.1 Actorlijst
De hypothese-actorlijst (sales rep, sales manager, customer success, inkoper, crediteuren-
administratie, masterdatabeheer, IT-/CRM-admin, controller, CFO, HR/payroll, externe
leverancier/klant) wordt getoetst aan de daadwerkelijke rollen in de dataset. Regel: een actor
komt in de simulatie als er in de data een rol bestaat die (a) een control uitvoert of
goedkeurt, of (b) een CRM-/systeemrecht heeft dat een control kan omzeilen. Rollen zonder
gelegenheid vallen af, hoe verdacht ze ook klinken. Doel: 6-10 actoren, meer maakt de chat
onleesbaar.

### 4.2 Eén agent per actor
Elke agent krijgt: de volledige control-gap analyse, de processen en controls die zijn rol
raken, zijn CRM-rechten, en de instructie in rol te blijven. Alle agents worden in één bericht
gespawned zodat ze parallel draaien.

Verplicht outputschema per agent (JSON), zodat de synthese mechanisch kan:

```
{
  "actor": "rol",
  "persona": {"naam": "fictief", "drijfveer": "...", "rationalisatie": "..."},
  "masterplan": "narratief, max 400 woorden",
  "stappen": [{"stap": 1, "handeling": "...", "systeem": "...",
               "omzeilde_control": "CTRL-xxx", "waarom_dat_werkt": "..."}],
  "benodigde_medeplichtigen": [{"actor": "rol", "wat_die_moet_doen": "...",
                                "wat_die_ervoor_krijgt": "..."}],
  "geraakte_risicos": ["RISK-xxx"],
  "detectiekans": {"door_welke_control": "CTRL-xxx", "vertraging": "...",
                   "hoe_ontweken": "..."},
  "faalpunt": "waar dit plan alsnog stukloopt"
}
```

Het veld `faalpunt` is bewust verplicht: dat is voor de auditor het aangrijpingspunt.

## 5. Fase 3 — Synthese

### 5.1 Collusiegraaf
De `benodigde_medeplichtigen` uit alle agents samenvoegen tot een gerichte graaf. Wederkerige
paren (A vraagt B én B vraagt A) zijn de harde collusie-assen; die krijgen de hoofdrol in de
chat. Verwachte assen: sales x masterdata, inkoop x crediteuren, controller x directie, en
iedereen x IT-admin.

### 5.2 Casting en tijdlijn
Per actor één fictief personage met eigen toon (sales schrijft anders dan de controller).
De plannen worden op één tijdlijn gelegd, meestal rond een kwartaalafsluiting, zodat losse
plannen één samenhangende operatie worden.

### 5.3 Bericht-naar-control mapping
Elk chatbericht krijgt in de bronbestanden een verwijzing naar control-ID en risico-ID.
Berichten zonder verwijzing worden geschrapt of tot sfeerbericht gedegradeerd. Dit is de
kwaliteitsborg: geen anekdote zonder onderliggende bevinding.

## 6. Fase 4 — Het artifact

Eén HTML-pagina, WhatsApp-groepsgesprek "Q4 — even afstemmen".

- Groepsheader met deelnemerslijst (rol onder de fictieve naam), datumscheiders,
  tijdstempels, afzenderkleuren, reply-quotes, "dit bericht is verwijderd", reacties.
- Bijlagen als kaartjes: `Prijslijst_v7_DEF.xlsx`, `factuur_2411.pdf` — elk gekoppeld aan
  de control die het passeert.
- Voicememo-balkjes op de plekken waar iemand bewust niets op schrift wil zetten. Dat is
  zelf een bevinding: bewijsvernietiging en het ontbreken van een communicatiecontrol.
- **Auditmodus** (schakelaar rechtsboven): markeert per bericht het omzeilde control-ID, het
  geraakte risico en de detectiekans. Uit = leesbaar verhaal, aan = auditbevinding.
- Sluitpaneel: overzichtstabel van alle geraakte controls en risico's, plus de faalpunten uit
  de agents — de lijst met aanbevelingen.
- Zichtbare FICTIEF — SIMULATIE-markering, thema-aware (licht/donker), scrollbare tabellen.

## 7. Acceptatiecriteria

1. Elke actor in de chat bestaat als rol in de dataset en heeft aantoonbaar gelegenheid.
2. Elk inhoudelijk bericht verwijst naar een bestaand control- of risico-ID.
3. Minstens twee wederkerige collusie-assen zijn uitgewerkt, niet alleen genoemd.
4. Per scenario is de detectiekans benoemd, inclusief de vertraging.
5. Het sluitpaneel bevat per scenario minimaal één concrete beheersingsmaatregel.
6. Geen echte namen uit de brondata in het eindproduct.

## 8. Risico's in deze aanpak

- Zonder data schrijven de agents leerboekfraude. Daarom fan-out pas na fase 1.
- Te veel actoren maakt de chat onleesbaar; harde grens op tien.
- Het verhaal kan de analyse overvleugelen. De auditmodus en het sluitpaneel zijn de rem:
  wat daar niet in past, hoort niet in de chat.
