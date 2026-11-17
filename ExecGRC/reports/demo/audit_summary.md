# Audit Summary

- Run id: `demo`
- Events: 7
- Hash chain enabled: True
- Final event hash: `26d269fd5d30c22e3ee7ef819b70eb8e3e7d2998b7eb2a111b8de3ce45478200`

## Steps

1. `configuration_loaded` - Loaded environment, thresholds and reporting profile. (`30d2a5c42e97dd589adc78adb1199e03a83e4cf979ae3374331b7cfec527870d`)
2. `source_data_loaded` - Loaded structured GRC records from input path. (`3fec5693ed6ed471b6d8cf9a0624da1073f71cdad215145eb57266aaa6780d90`)
3. `data_normalized` - Normalized source records into controls and risks. (`e2d277fee3d2c061bb0750336a28ee23af15099644e69cb299f680aba571053c`)
4. `analysis_completed` - Applied deterministic risk-control correlation rules. (`bbba38f6f4512476010a2759d70f2e61a984ae88cc793b035d4692393ca899a1`)
5. `reports_generated` - Generated tactical and executive reports with traceability. (`a9c676d1fc8148fe9328109324801fcb98052602f1f2fe6b46e749ba9534bef8`)
6. `dashboard_generated` - Generated static dashboard with offline visualizations. (`8c338bc664299af35a6ccb346c4631a3fc8785f6b836d2dc1edbd525c73dafe1`)
7. `manifest_prepared` - Prepared final manifest after report generation. (`26d269fd5d30c22e3ee7ef819b70eb8e3e7d2998b7eb2a111b8de3ce45478200`)

## Verification Note

The NDJSON trail is append-only for this run. Recompute each event hash from the canonical event payload and compare `previous_hash` with the prior `event_hash` to detect later edits.
