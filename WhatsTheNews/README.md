# SAAF RSS Nieuwsapp

Kleine Node-app zonder externe dependencies die nieuws van de afgelopen week ophaalt uit RSS-feeds, per onderwerp groepeert en als HTML teruggeeft.

## Bronnen

- DNB: officiële RSS-feed
- AFM: officiële RSS-feed
- FD: configureerbare feed via `FD_FEED_URL`
  - standaard staat deze op een nieuws-RSS fallback voor `fd.nl`

## Starten

```bash
npm start
```

Open daarna `http://localhost:3000/`.

De homepage op `http://localhost:3000/` bevat een formulier waarmee je:

- kunt kiezen welke RSS-feeds worden meegenomen
- categorieen kunt filteren via een tekstveld met suggesties
- eigen categorieen kunt toevoegen als extra trefwoorden voor de indeling

## Configuratie

- `PORT`: poort van de HTTP-server
- `REPORT_WINDOW_DAYS`: aantal dagen terugkijken, standaard `7`
- `DNB_FEED_URL`: overschrijft de DNB-feed
- `AFM_FEED_URL`: overschrijft de AFM-feed
- `FD_FEED_URL`: overschrijft de FD-feed
- `REQUEST_TIMEOUT_MS`: timeout per feedrequest, standaard `12000`

## Testen

```bash
npm test
```
