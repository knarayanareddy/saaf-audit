# SAAF Strapi Synthetic Data Sandbox

Local Strapi 4 sandbox for hackathon demos that need realistic but fictional audit data. The sandbox ships with deterministic seed files so every participant can test against the same dataset.

## 5-minute guide

If you just want to get started quickly:

1. Open a terminal in the root of this repo.
2. Start the sandbox:

```bash
./tools/strapi/start-sandbox.sh
```

3. Wait until you see:

```text
Seeded Strapi sandbox is ready.
API:   http://localhost:1340/api
Admin: http://localhost:1340/admin
```

4. Open the admin interface in your browser:

- `http://localhost:1340/admin`

5. Open the API in your browser:

- all incidents: `http://localhost:1340/api/jira-incidents`
- one incident by `ticket_id`: `http://localhost:1340/api/jira-incidents?filters[ticket_id][$eq]=INC-2026-0001`

6. When you are done, stop the sandbox:

```bash
./tools/strapi/stop-sandbox.sh
```

If startup fails, inspect the logs:

```bash
docker compose -f tools/strapi/docker-compose.yml logs strapi
```

## Quick start

Run one command from the repo root:

```bash
./tools/strapi/start-sandbox.sh
```

The launcher will:

1. create `tools/strapi/.env` from `.env.example` if needed
2. build and start Strapi
3. wait until Strapi is healthy
4. reset and reseed all five datasets
5. verify live API counts before printing the ready URLs

The local API will be available at `http://localhost:1340/api`.

## Requirements

- Docker with `docker compose`
- Python 3.9+ on the host
- Internet access the first time Docker builds the images

## Sign in to Strapi Admin

Open in your browser:

- `http://localhost:1340/admin`

The admin username and password are stored in:

- `tools/strapi/.env`

The relevant variables are:

- `SAAF_STRAPI_ADMIN_EMAIL`
- `SAAF_STRAPI_ADMIN_PASSWORD`

The default values are:

- `admin@example.com`
- `ChangeMe123!`

## Use the API in your browser

You do not need to sign in to browse the test data through the public REST API. Simply open a URL in your browser.

Base URL:

- `http://localhost:1340/api`

Examples:

- all incidents: `http://localhost:1340/api/jira-incidents`
- one incident by `ticket_id`: `http://localhost:1340/api/jira-incidents?filters[ticket_id][$eq]=INC-2026-0001`
- only P1 incidents: `http://localhost:1340/api/jira-incidents?filters[priority][$eq]=P1`
- only exception access reviews: `http://localhost:1340/api/access-reviews?filters[is_exception][$eq]=true`
- high-risk findings: `http://localhost:1340/api/audit-findings?filters[risk_rating][$eq]=High`

Important:

- Strapi has its own internal record `id`
- the business identifier for an incident is `ticket_id`
- if you want to look up an incident such as `INC-2026-0001`, use the `filters[...]` URL and not `/api/jira-incidents/:id`

## Operations

Stop the sandbox:

```bash
./tools/strapi/stop-sandbox.sh
```

Remove containers and volumes for a full local reset:

```bash
docker compose -f tools/strapi/docker-compose.yml down --volumes
```

Manual troubleshooting path if you need it:

```bash
docker compose -f tools/strapi/docker-compose.yml up -d --build strapi
docker compose -f tools/strapi/docker-compose.yml run --rm seed
python3 tools/scripts/verify_strapi_seed.py --check-api --base-url http://localhost:1340
```

## Public contract

Supported read-only collections:

- `/api/jira-incidents`
- `/api/access-reviews`
- `/api/change-tickets`
- `/api/vendor-contracts`
- `/api/audit-findings`

Example filters:

```text
/api/jira-incidents?filters[priority][$eq]=P1
/api/jira-incidents?filters[ticket_id][$eq]=INC-2026-0001
/api/access-reviews?filters[is_exception][$eq]=true
/api/change-tickets?sort=implemented_at:desc
/api/vendor-contracts?filters[tprm_status][$eq]=Expired
/api/audit-findings?filters[risk_rating][$eq]=High
```

## Dataset contract

- `jira-incidents`: 500 records, including 75 major incidents (`P1`/`P2`) and recurring incident-management exceptions.
- `access-reviews`: 200 records with synthetic reviewer decisions and 30+ access-governance exceptions.
- `change-tickets`: 150 records covering standard, normal, and emergency changes.
- `vendor-contracts`: 50 records with criticality, SLA, and TPRM lifecycle fields.
- `audit-findings`: 100 records aligned to [`outputs/schemas/finding-schema.json`](/Users/erik/coding/projects/SAAF/SAAF-Project/outputs/schemas/finding-schema.json:1).

Because Strapi reserves the top-level `id` field, the committed seed file for audit findings uses the finding schema field `id`, while the Strapi content type stores the same value as `id_code`.

## Tooling

- `tools/scripts/generate_synthetic_data.py`: regenerates the canonical JSON fixtures in `tools/strapi/seed/`.
- `tools/scripts/seed_strapi.py`: deletes existing entries and reloads all five datasets through the Strapi admin API.
- `tools/scripts/verify_strapi_seed.py`: validates fixture counts, basic schema rules, and optional live API counts.

## Scope defaults

- Local Docker is the MVP path.
- Committed JSON fixtures are the source of truth for demos.
- REST is the only supported interface in v1.
- Jira-compatible route emulation is deferred; Jira/Confluence consumers should integrate to the Strapi endpoints above.
