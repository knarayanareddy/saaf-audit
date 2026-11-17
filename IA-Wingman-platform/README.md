# IA Wingman

An AI-powered internal audit platform for the organisation's IA team (Group · International · AM).
Phase 1: dashboard, engagements, and the planning phase with three focused AI agents.

## Privacy & scope

- **No personal data is pre-loaded.** Seeded engagements have no lead or team. You type your own
  identifier (initials) on first use — it is stored only in your browser's localStorage.
- **TB DE is excluded** (wind-down).
- **Single user per installation** in Phase 1. Data lives in a local SQLite file on this machine and
  is not shared between machines. Team sharing is a later phase.

## One-time setup

All commands start from the folder you cloned or unzipped (the one that contains `backend` and `frontend`).

### 1. Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
Then edit `backend\.env`. Three values are needed, and each participant uses their own:

| Setting | What to put there |
|---|---|
| `ANTHROPIC_API_KEY` | **Your own** Anthropic API key (https://console.anthropic.com/settings/api-keys). The AI features run on it and are billed to it. Never share it and never commit `.env`; it is git-ignored. |
| `GDPR_PSEUDONYM_KEY` | A random secret of at least 32 characters, unique to your installation. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. Without it the privacy guard refuses to run. |
| `APP_PASSWORD` | The password you will type on the sign-in screen (user name `iawingman`). For a purely local try-out you can instead set `IA_WINGMAN_DEV_OPEN=true` and leave the password empty. |

### 2. Frontend
```powershell
cd frontend
npm install
```

## Running (two terminals, both must stay open)

**Terminal 1 — backend (port 8000):**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```
The database is auto-created and seeded with the 2026 audit plan on first start
(seeding is idempotent — restarting never duplicates data).

**Terminal 2 — frontend (port 5173):**
```powershell
cd frontend
npm run dev
```
Open http://localhost:5173

## Running the tests

Start the backend once first: it creates the database and seeds the demo data that the tests use.
For local tests the backend needs `IA_WINGMAN_DEV_OPEN=true` (or an `APP_PASSWORD`) in `backend\.env`.
Then, from `backend`, with the virtual environment active:
```powershell
pip install -r requirements-dev.txt
python -m tests.smoke
python -m tests.test_security
```
Each file in `backend\tests` is a standalone suite run the same way (`python -m tests.<name>`);
none of them calls the Anthropic API. Frontend tests: `node --test tests/*.test.mjs` in `frontend`.

## The three agents (planning → Topic Intelligence)

1. **Regulatory Intelligence** — applicable laws, supervisory focus, recent developments (built-in
   knowledge + any URLs you paste). Runs in parallel with Policy Scout.
2. **Policy Scout** — searches only your uploaded internal documents; never invents content.
3. **Interview Guide** — runs after the first two, producing sponsor / SME / IA-prework questions.

Every AI output is shown for review — edit, accept, or dismiss before anything is saved. Accepting the
Topic Intelligence memo queues scope items, key questions, and frameworks for confirmation.

## Branding

IA Wingman brand green `#1E6B4F`, Inter body font, and the the organisation logo + official audit-process
diagram are extracted from the IA team's own Word templates and bundled in `frontend/public/`.

## Security notes

- API key only in `.env` (git-ignored); never logged or sent to the frontend.
- Uploads: PDF/.docx only, 20 MB cap, UUID filenames, served only via API (not as static files).
- URL fetching blocks private IP ranges (SSRF protection), 10s timeout.
- CORS restricted to localhost:5173. All inputs validated via Pydantic; ORM only (no raw SQL).

## Licence

For SAAF project participants only; see [LICENSE](LICENSE). Do not publish or share this repository outside the SAAF project.
