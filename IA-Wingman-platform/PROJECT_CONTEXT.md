# IA Wingman — Project Context

> **Gebruik deze file** om nieuwe chatsessies snel up to speed te brengen.  
> Update dit document elke keer als er significante wijzigingen zijn gedaan.

---

## Wat is dit project?

Een AI-ondersteund intern audit platform voor the organisation's IA-teams (Internal Audit) verspreid over meerdere entiteiten: **Group, International, Retail, Business, AM**. Het platform begeleidt auditors door de volledige audit-lifecycle (planning → fieldwork → reporting) en integreert Claude (Anthropic) als AI-backbone.

**Status:** Actief in ontwikkeling — nog geen productie-deployment.

---

## Tech Stack

| Laag | Technologie |
|------|-------------|
| Frontend | React 18 + Vite + Tailwind CSS + Zustand + TanStack Query |
| Backend | FastAPI (Python) + SQLAlchemy async + Pydantic v2 |
| Database | SQLite (lokaal bestand `backend/ia_wingman.db`) |
| AI | Anthropic Claude API (`claude-sonnet-4-6`) |
| Web Search | Tavily API (optioneel, voor Regulatory Intelligence) |
| Document parsing | pypdf + python-docx |
| Word export | python-docx |

---

## Projectstructuur

```
IA Wingman platform/
├── backend/
│   ├── main.py              # FastAPI app, routers, lifespan
│   ├── config.py            # .env laden (ANTHROPIC_API_KEY, TAVILY_API_KEY)
│   ├── database.py          # SQLAlchemy async engine + migraties
│   ├── schemas.py           # Pydantic request/response modellen
│   ├── models/              # ORM modellen (engagement, agent_run, planning)
│   ├── routers/             # API-routes per module
│   ├── services/            # Business logic + AI agents
│   ├── uploads/             # Geüploade documenten (PDF/DOCX)
│   └── ia_wingman.db        # SQLite database
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Route-definities
│   │   ├── api/             # Axios API-clients per module
│   │   ├── store/useStore.js # Zustand global state
│   │   ├── pages/           # Pagina-componenten
│   │   └── components/      # Herbruikbare UI-componenten
│   ├── vite.config.js       # Dev server (port 5173), proxy naar :8000
│   └── tailwind.config.js   # IA Wingman branding (#1E6B4F grounded green)
├── README.md
└── PROJECT_CONTEXT.md       # Dit bestand
```

---

## Hoe opstarten

```bash
# Terminal 1 — Backend
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev   # → http://localhost:5173
```

**Vereiste .env in `/backend/`:**
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=           # optioneel
```

---

## Database modellen (kern)

| Model | Doel |
|-------|------|
| `Engagement` | Audit-zaak (code, naam, entiteit, type, status, auditor) |
| `AgentRun` | Tracking van AI-agent uitvoeringen |
| `UploadedDocument` | Geüploade interne documenten + extracted text |
| `TopicIntelligence` | Fase 1A: AI-memo (regulatory + policy + interview) |
| `ScopeObjectives` + `ScopeItem` | Fase 1B: scope & doelstellingen |
| `KeyAuditQuestion` | Kernvragen per scope |
| `ApplicableFramework` | Toepasselijke regelgeving + confidence |
| `ProcessNotes` | Fase 2: procesanalyse |
| `BackgroundRiskAssessment` | BRA-document |
| `KickoffAgenda` | Kickoff-vergadering voorbereiding |
| `AuditNotificationLetter` | ANL-document |
| `WorkProgram` | Testprocedures |
| `FieldworkObservation` | Fase 3: bevindingen fieldwork |

**Entiteiten:** `GRP`, `INT`, `AM`, `RET`, `BUS`  
**Audit types:** `compliance`, `operational`, `it`, `financial`, `esg`, `fraud`, `conduct`, `advisory`, `validation`  
**Engagement statussen:** `to_be_scheduled` → `in_planning` → `in_fieldwork` → `in_reporting` → `closed`

---

## AI-architectuur: Drie-agenten pipeline

Wordt getriggerd vanuit **Topic Intelligence (Fase 1A)**:

```
[Gebruiker triggert agent run]
        ↓
┌─────────────────────┐   parallel   ┌────────────────────┐
│ Regulatory          │              │ Policy Scout       │
│ Intelligence Agent  │              │ Agent              │
│ (web search +       │              │ (ALLEEN geüploade  │
│  Claude synthese)   │              │  interne docs)     │
└─────────────────────┘              └────────────────────┘
        ↓ (beide klaar)
┌─────────────────────┐
│ Interview Guide     │
│ Agent               │
│ (vragensets per     │
│  stakeholder)       │
└─────────────────────┘
        ↓
[Orchestrator assembleert TopicIntelligence memo]
[Auditor reviewt → accepteert → cascade naar rest van planning]
```

**Regulatory Intelligence:** genereert zoekqueries per entiteit/audit-type, voert Tavily web search uit, Claude synthetiseert met chain-of-thought (4 stappen).  
**Policy Scout:** zoekt uitsluitend in geüploade documenten, verzint nooit iets.  
**Interview Guide:** genereert vragen per stakeholdertype (sponsor, SME, IA pre-work).

---

## API-routes overzicht

| Prefix | Module |
|--------|--------|
| `GET/POST/PATCH/DELETE /api/engagements` | Engagement CRUD |
| `GET /api/engagements/stats` | Dashboard statistieken |
| `POST /api/engagements/{id}/agents/run` | Start 3-agenten pipeline |
| `GET /api/engagements/{id}/agents/status` | Poll agent-status |
| `GET/PATCH /api/planning/{id}/topic-intelligence` | Topic Intelligence memo |
| `POST /api/planning/{id}/topic-intelligence/accept` | Memo accepteren |
| `/api/planning/{id}/scope-objectives` | Scope & doelstellingen |
| `/api/planning/{id}/frameworks` | Toepasselijke frameworks |
| `/api/planning/{id}/anl` | Audit Notification Letter |
| `/api/planning/{id}/bra` | Background Risk Assessment |
| `/api/planning/{id}/kickoff` | Kickoff agenda |
| `/api/planning/{id}/work-program` | Werkprogramma/testprocedures |
| `/api/fieldwork/{id}/observations` | Fieldwork bevindingen |
| `POST /api/chat` | Algemene AI-chat |

---

## Beveiliging & privacy

- **API keys** uitsluitend in `.env` (git-ignored), nooit naar frontend
- **Documenten:** UUID-bestandsnamen, alleen PDF/DOCX, max 20 MB, uitsluitend via API geserveerd
- **CORS:** alleen `http://localhost:5173`
- **SSRF-bescherming:** private IP-ranges geblokkeerd bij URL-fetching
- **Geen persoonsdata:** gebruiker typt eigen initialen in browser (localStorage), geen team-roster
- **ORM-only:** geen raw SQL, SQLAlchemy beschermt tegen SQL-injectie

---

## Seed data

`backend/seed_service.py` zaait bij opstarten **44 audit-engagements** (idempotent) verspreid over alle entiteiten, statussen en audit-types — voor ontwikkeling en demo.

---

## Branding

- **Hoofdkleur:** IA Wingman brand green `#1E6B4F`
- **Entiteitskleuren:** NL=indigo, UK=red, AM=teal
- **Fonts:** RB Freigeist Neue (headers) + Inter (body)
- **Logo & assets** in `frontend/public/`

---

## Wijzigingslog

| Datum | Wat gedaan |
|-------|------------|
| 2026-06-29 | Initiële `PROJECT_CONTEXT.md` aangemaakt op basis van volledige codebase-verkenning |

---

*Voeg nieuwe rijen toe aan de wijzigingslog bij elke significante sessie.*
