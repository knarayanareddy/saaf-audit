# Deploying IA Wingman

One service, one URL. The container serves the built frontend and the API from
the same origin, keeps the database and the uploaded documents on a mounted
volume, and reads every secret from the host's own secret store.

Nothing here depends on a laptop staying awake.

---

## What the deployment is made of

| Piece | Where it lives | Why |
| --- | --- | --- |
| Frontend | built inside the image, served by FastAPI from `/app/static` | one origin, so no CORS and no second service that can be down on its own |
| API | the same process | same |
| Database + uploads | `/data` | a volume when the host offers one; on a free plan this is writable but **not** persistent |
| Secrets | the host's environment, `sync: false` in `render.yaml` | never in the image, never in the repository |

The frontend is **built in the image**, not committed. A stale `dist/` that
someone forgot to rebuild is the standard way for a demo to show yesterday's app.

---

## Environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | yes | the app refuses to start without it |
| `APP_PASSWORD` | yes | **empty means the API rejects everything with 503** — fail-closed on purpose |
| `APP_USERNAME` | no | defaults to `iawingman` |
| `GDPR_PSEUDONYM_KEY` | for Privacy Guard | ≥ 32 characters, unique per deployment; empty makes that agent refuse to run |
| `IA_WINGMAN_DATA_DIR` | yes, in a container | the volume mount, e.g. `/data` |
| `IA_WINGMAN_STATIC_DIR` | set by the image | the built frontend |
| `EXPOSE_API_DOCS` | set to `false` | FastAPI mounts `/docs` itself, **outside** the password gate |
| `IA_WINGMAN_ALLOWED_ORIGINS` | no | only if something off-origin must call the API |

Unset `IA_WINGMAN_DATA_DIR` and `IA_WINGMAN_STATIC_DIR` locally and nothing
about development changes: the database stays next to the code and Vite keeps
serving the frontend.

---

## Render (the path this repo is configured for)

`render.yaml` is a blueprint: the whole service in one file, so it can be rebuilt
without anyone remembering which boxes were ticked.

1. **New → Blueprint** in the Render dashboard, point it at this repository.
2. Render reads `render.yaml` and asks for the four secret values. Paste them.
3. Deploy. First build takes a few minutes — it installs npm and pip from scratch.
4. The URL appears as `https://ia-wingman-<something>.onrender.com`.
5. Sign in with `APP_USERNAME` and `APP_PASSWORD`.

Region is **Frankfurt**. This holds audit documents about European entities, and
where they are stored is a question an auditor is entitled to ask.

`autoDeploy` is **off**. A push should not redeploy the thing you are presenting.

### What the free plan costs you instead of money

Two things, both manageable if you know about them:

**It sleeps after 15 minutes without traffic** and takes about a minute to wake.
Open the URL a few minutes before you present and it is warm when your audience
arrives. 750 instance hours a month, and sleeping hours don't count.

**The filesystem is not persistent** — persistent disks are the paid feature.
Every restart wipes the database and the uploads. For a demo that is close to
harmless, because startup seeds the whole thing again; see below. For real audit
work it is disqualifying, and that is the moment to pay for a disk.

To upgrade later: set `plan: starter` and add a `disk:` block with `mountPath:
/data`. Nothing else changes — the app already keeps everything there.

### Every start seeds itself

The filesystem starts empty, and startup fills it: the 15-audit annual plan, the
golden-path engagement, the RACM, the board demo and the audit memory. So the
deployed app is demonstrable the moment it is up, without copying any database
from a laptop.

An audit built by hand in the app can come along too, as a **snapshot**: 26-047
(Artificial Intelligence) does. `backend/export_demo_engagement.py <audit code>`
writes it from the local database to `backend/seed_data/demo_engagements/`, and
every start loads it when it is missing. To carry later local changes online,
export again, commit the file and deploy. Look at what the audit holds before
exporting: the file goes into the repository.

Seeding is not recorded in the edit register, so a fresh start does not look
like a day of edits.

What it will *not* have is the RCSA import and anything else built locally and
not exported — those are in the laptop's database.

---

## Anywhere else

The `Dockerfile` has no Render in it. Any host that runs a container works —
Fly.io, Railway, Azure Container Apps, a VM with Docker:

```
docker build -t ia-wingman .
docker run -p 8000:8000 -v ia-wingman-data:/data \
  -e ANTHROPIC_API_KEY=... -e APP_PASSWORD=... -e GDPR_PSEUDONYM_KEY=... \
  -e EXPOSE_API_DOCS=false ia-wingman
```

Two things any host needs: a **persistent volume** at `/data`, and the secrets as
environment variables.

---

## Before sharing the URL with anyone

- **One password guards everything.** Anyone with the link and the password sees
  every engagement, every uploaded document, and spends the Anthropic credit on
  that key. Pick a password you would be willing to see in a chat message,
  because that is where it will end up.
- **`EXPOSE_API_DOCS=false`.** Otherwise `/docs` publishes every route and schema
  to anyone with the URL, password or not.
- **Real audit material is a different decision.** A demo instance with seeded,
  white-label data is not the same thing as a system holding actual engagement
  documents. That one needs a conversation about data classification first.
