# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**HighTable** — a Chrome browser extension + Python backend that helps internal auditors find similar past audit issues and generate AI-powered recommendations, integrated with [TeamMate+](https://www.wolterskluwer.com/en/solutions/teammate) via its REST API.

TeamMate+ instance: `https://br1ght8.teammatehosting.com/TeamMate`
TeamMate+ API base: `https://br1ght8.teammatehosting.com/TeamMate/api/v1`
API spec (requires login): `https://br1ght8.teammatehosting.com/TeamMate/swagger/ui/index`

## Architecture

```
extension/          Chrome MV3 browser extension (vanilla JS)
  manifest.json     Scoped to br1ght8.teammatehosting.com, storage permission
  content.js        Injected into TeamMate+ pages — sidebar UI, analyze logic, SPA nav detection
  panel.css         Sidebar styles (scoped under #hightable-sidebar)
  options.html/js   Settings page for backend URL + API key
  background.js     Service worker — sets storage defaults on install

backend/            Python FastAPI backend
  main.py           FastAPI app — /api/analyze, /api/issue/{id}, /api/refresh-cache, /api/health
  teammate_client.py TeamMate+ REST API client — pagination, field normalisation, TTL cache
  embeddings.py     sentence-transformers semantic similarity (all-MiniLM-L6-v2)
  claude_client.py  Claude API — scoring, explanation, draft recommendation generation
  models.py         Pydantic v2 models (AnalyzeRequest, SimilarIssue, AnalysisResponse)
```

## How it works

1. Extension injects a 🏛️ floating button into every TeamMate+ page
2. Auditor opens the sidebar, enters/pastes the current issue title + description
3. Extension POSTs to the Python backend `/api/analyze`
4. Backend fetches all **Closed-Verified** issues + recommendations from TeamMate+ (cached in memory, 6h TTL), runs sentence-transformer embeddings, computes cosine similarity, takes top 5 matches
5. Claude scores each match, explains relevance, and writes a draft recommendation
6. Results render in the sidebar with score bars, collapsible recommendations, and a copy button for the draft

**"Effective" issues** = released issues whose workflow state name contains both "Closed" and "Verified" (e.g. `Closed-Verified`).

## Running the backend

```bash
cd backend
cp .env.example .env        # fill in TEAMMATE_API_KEY, ANTHROPIC_API_KEY, BACKEND_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend starts on `http://localhost:8000`. On startup it warms the issue cache in the background (first request may be slower).

## Loading the extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder
4. Click the extension icon → **Options** → set Backend URL (`http://localhost:8000`) and Backend API Key

## Key TeamMate+ API endpoints used

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/Issues` | Paginated list of released issues |
| `GET /api/v1/Issues/{id}` | Single issue by ID |
| `GET /api/v1/Recommendations` | All recommendations (matched to issues by parent ID) |
| `GET /api/v1/Setup` | Workflow state metadata |

Auth header: `Authorization: ApiKey {key}` (configurable via `TEAMMATE_AUTH_SCHEME` env var).

## Environment variables (`backend/.env`)

| Variable | Description |
|---|---|
| `TEAMMATE_BASE_URL` | TeamMate+ base URL |
| `TEAMMATE_API_KEY` | TeamMate+ API key |
| `TEAMMATE_AUTH_SCHEME` | Auth header scheme, default `ApiKey` |
| `ANTHROPIC_API_KEY` | Claude API key |
| `BACKEND_API_KEY` | Shared secret for extension→backend auth (optional in dev) |
| `CACHE_TTL_HOURS` | How long to cache issues before re-fetching, default `6` |
| `EMBEDDING_MODEL` | sentence-transformers model, default `all-MiniLM-L6-v2` |
