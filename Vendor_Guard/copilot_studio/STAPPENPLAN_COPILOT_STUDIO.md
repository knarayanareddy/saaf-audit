# Vendor Guard in Copilot Studio: stappenplan

Dit stappenplan zet de Vendor Guard audit-agent op in Microsoft Copilot Studio. Je hebt er geen Python, API-sleutel of Azure-omgeving voor nodig.

Menunamen in Copilot Studio kunnen afwijken van wat hieronder staat. De stappen beschrijven wat je moet bereiken.

## Wat je nodig hebt

- Toegang tot Copilot Studio met rechten om een agent te maken.
- De map `dist` uit dit pakket (`vendor_guard_copilot_pakket.zip`), met:
  - `agent_instructions.md`
  - `knowledge/` met 10 bestanden
- De vier voorbeeldbestanden om te testen: `sample_vendor_q.txt`, `sample_soc2_report.txt`, `sample_iso_certificate.txt`, `sample_dora_questionnaire.txt`.

## Stap 1: Agent aanmaken

1. Kies **Create** (Maken) en dan **New agent**.
2. Sla de chat-wizard over met **Skip to configure** (of **Configure**).
3. Naam: `Vendor Guard`.
4. Description: `Third-party risk audit agent: assesses vendor documents against EU/NL frameworks.`
5. Laat Instructions leeg en klik **Create**.

## Stap 2: Instructions plakken

1. Open `agent_instructions.md`, selecteer alles en kopieer.
2. Plak het in het veld **Instructions** op het tabblad **Overview**.
3. Klik **Save**. De tekst is ongeveer 4.500 tekens. Bij een lengtefout: meld dat.

## Stap 3: Knowledge uploaden

1. Ga naar het tabblad **Knowledge** en kies **Add knowledge**.
2. Kies **Files** en selecteer alle 10 bestanden uit `knowledge/`:
   - `ai_act_requirements.md`
   - `altai_requirements.md`
   - `bio2_controls.md`
   - `cbw_requirements.md`
   - `document_validity_rules.md`
   - `dora_requirements.md`
   - `ec_ethics_guidelines.md`
   - `iso27001_controls.md`
   - `nis2_measures.md`
   - `subcontracting_chain.md`
3. Wordt `.md` niet geaccepteerd, hernoem dan de bestanden naar `.txt` en upload opnieuw. Houd de bestandsnamen verder gelijk, want de instructies verwijzen ernaar.
4. Wacht tot alle bestanden de status **Ready** hebben. Dat kan enkele minuten duren.

## Stap 4: Instellingen

1. Zet **Web search** en **Use general knowledge** (namen kunnen verschillen) uit, zodat de agent alleen antwoordt op basis van de knowledge en de geüploade documenten.
2. Controleer dat het uploaden van bestanden in de chat aan staat. Staat dat niet in de instellingen, test het dan in stap 5.

## Stap 5: Testen

1. Open het paneel **Test your agent**.
2. Upload de vier voorbeeldbestanden en stuur: `Assess this vendor.`
3. Controleer het resultaat:
   - Draaien ISO 27001, NIS2, CBW, DORA en Document Validity? BIO2 en AI Trust draaien alleen als de documenten dat rechtvaardigen.
   - Staan er scorecard, gap register en memo, in die volgorde?
   - Quoot elke finding een echt document?
   - Zijn alle controls uit de kaders beoordeeld, of zijn er veel overgeslagen? Worden er controls overgeslagen, vraag de agent dan om elk kader control voor control door te lopen, en voeg dat toe aan de instructies.
   - Kloppen de dagtellingen bij Document Validity en de aantallen in de scorecard? Rekenen doet in Copilot het model, dus controleer dit steekproefsgewijs.

## Gebruik tijdens klantopdrachten

- Eén gesprek per entiteit: de klant zelf, elke leverancier en elke onderaannemer krijgen een eigen gesprek. Gooi geen documenten van meerdere partijen door elkaar.
- De agent vraagt eerst naar de rol van de entiteit (klant, leverancier van de klant of onderaannemer), de dienst, de keten, de beoordelingsdatum en de uitvoertaal. Beantwoord dat per gesprek.
- Zet geen klantdocumenten in de Knowledge van de agent. Alleen de kaderbestanden horen daar. Klantdocumenten gaan alleen in het chatgesprek.
- Deel de agent alleen met het opdrachtteam en controleer met de afdeling Security/IT hoe lang chatgesprekken en geüploade bestanden in jullie omgeving bewaard worden en wie erbij kan, voordat je klantdocumenten uploadt. Controleer ook of de klantovereenkomst het gebruik van AI-tools toestaat.
- De uitvoer is een concept ("DRAFT for auditor review"). De auditor beoordeelt statussen, severity en de RAG-score voordat iets naar de klant gaat.
- De agent beoordeelt alleen wat in de documenten staat. Het is geen vervanging van testwerk of een auditoordeel.
- Voorbeeld voor de keten: `sample_soc2_report.txt` noemt AWS als infrastructuur. Test een gesprek waarin CloudSafe als leverancier is en AWS als onderaannemer, en kijk of de agent SUB-02, SUB-04 en SUB-09 oppakt.

## Stap 6: Publiceren

1. Klik rechtsboven op **Publish**.
2. Deel de agent met het team via **Share** of **Channels** (bijvoorbeeld Teams).

## Beperkingen ten opzichte van de Python-versie

- Eén agent beoordeelt de kaders na elkaar, niet parallel.
- RAG-score en datumberekeningen worden door het model gedaan, niet door code.
- De agent beoordeelt één entiteit per gesprek. Een overzicht van de hele keten stel je zelf samen uit de losse gesprekken.
- Het kader `subcontracting_chain` is door mij uit algemene kennis opgesteld. Laat een DORA/NIS2-specialist artikelnummers en drempels controleren voor gebruik bij een klant.
- Kaders worden doorzocht, niet volledig in de prompt gezet. Controls kunnen worden overgeslagen.
- De uitvoer komt in de chat. Excel- en Word-bestanden vragen een aparte Power Automate-flow.

## Bijwerken

De kader-bestanden komen uit `prompts/` in de repo. Na een wijziging: `python copilot_studio/build.py` draaien en `dist/knowledge/` opnieuw uploaden.
