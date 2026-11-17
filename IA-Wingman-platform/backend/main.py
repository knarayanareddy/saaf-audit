import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import models  # noqa: F401
import paths
from database import create_tables, run_migrations
from services.run_recovery import recover_interrupted_runs
from services.seed_service import seed_if_empty
from services.backfill_service import backfill_engagement_dates
from services.golden_path_service import seed_golden_path, backfill_golden_demo_content
from services.seed_racm import seed_racm
from services.seed_board_demo import seed_board_demo
from services.seed_audit_memory_demo import seed_audit_memory_demo
from services.seed_demo_snapshots import seed_demo_snapshots
from organization import ORG
from auth import require_auth
from services import edit_register
from config import settings
from routers import (
    engagements, planning, agents, ai_chat,
    anl as anl_router, kickoff as kickoff_router,
    bra as bra_router, phase3 as phase3_router,
    fieldwork as fieldwork_router, review as review_router,
    interview as interview_router, reporting as reporting_router,
    documents as documents_router, assurance as assurance_router,
    racm as racm_router, board as board_router, memory as memory_router,
    copilot as copilot_router, workflow as workflow_router,
    rcsa as rcsa_router, edit_register as edit_register_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    paths.ensure()
    await create_tables()
    await run_migrations()
    # Before anything reads the database: no agent run from a previous process
    # is still alive, so none may still claim to be.
    await recover_interrupted_runs()
    # Seeding the demo is not an edit by anyone, so the register does not
    # record it (services/edit_register.paused).
    with edit_register.paused():
        await seed_if_empty()
        await backfill_engagement_dates()
        await seed_golden_path()
        await backfill_golden_demo_content()
        await seed_racm()
        await seed_board_demo()
        await seed_audit_memory_demo()
        await seed_demo_snapshots()
    yield


# /docs + /openapi.json are not covered by the global auth dependency (FastAPI
# mounts them itself), so allow locking them down for a hardened deployment.
_docs_kwargs = {} if settings.EXPOSE_API_DOCS else {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(
    title="IA Wingman Platform",
    lifespan=lifespan,
    # The second dependency records who a request says it is, for the edit
    # register; it decides nothing about access.
    dependencies=[Depends(require_auth), Depends(edit_register.actor_from_request)],
    **_docs_kwargs,
)

# Dev runs the frontend on its own port, so it needs CORS. A deployment serves
# the frontend from this same process and therefore needs none — anything extra
# is set explicitly through IA_WINGMAN_ALLOWED_ORIGINS, never guessed from a
# request header.
_EXTRA_ORIGINS = [o.strip() for o in (os.environ.get("IA_WINGMAN_ALLOWED_ORIGINS") or "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", *_EXTRA_ORIGINS],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(engagements.router, prefix="/api", tags=["engagements"])
app.include_router(planning.router, prefix="/api", tags=["planning"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(ai_chat.router, prefix="/api", tags=["ai"])
app.include_router(anl_router.router, prefix="/api", tags=["anl"])
app.include_router(kickoff_router.router, prefix="/api", tags=["kickoff"])
app.include_router(bra_router.router, prefix="/api", tags=["bra"])
app.include_router(phase3_router.router, prefix="/api", tags=["phase3"])
app.include_router(fieldwork_router.router, prefix="/api", tags=["fieldwork"])
app.include_router(review_router.router, prefix="/api", tags=["review"])
app.include_router(interview_router.router, prefix="/api", tags=["interview"])
app.include_router(reporting_router.router, prefix="/api", tags=["reporting"])
app.include_router(documents_router.router, prefix="/api", tags=["documents"])
app.include_router(assurance_router.router, prefix="/api", tags=["assurance"])
app.include_router(racm_router.router, prefix="/api", tags=["racm"])
app.include_router(board_router.router, prefix="/api", tags=["board"])
app.include_router(memory_router.router, prefix="/api", tags=["memory"])
app.include_router(copilot_router.router, prefix="/api", tags=["copilot"])
app.include_router(workflow_router.router, prefix="/api", tags=["workflow"])
app.include_router(rcsa_router.router, prefix="/api", tags=["rcsa"])
app.include_router(edit_register_router.router, prefix="/api", tags=["edit-register"])

# Every flush now records who proposed and who decided (services/edit_register.py).
edit_register.install()


@app.get("/api/org")
async def get_org():
    """White-label organization profile — the single source of org identity."""
    return ORG.to_dict()


@app.get("/api/health")
async def health():
    from config import api_key_problem, settings
    key = settings.ANTHROPIC_API_KEY or ""
    problem = api_key_problem(key)
    ai_enabled = problem is None
    return {
        "status": "ok",
        "service": "ia-wingman",
        "ai_enabled": ai_enabled,
        "web_search_enabled": ai_enabled,
        # Enough to say what is wrong with a key, never enough to rebuild it:
        # the length and, for a wrong start, its first three characters.
        "ai_key_problem": problem,
        "ai_key_length": len(key),
        "ai_key_starts_with": key[:3] if problem == "unexpected_prefix" else None,
    }


# ── The frontend, served by this same process ───────────────────────────────
# A deployment gets one origin for the app and its API: no CORS, no second URL
# that can be up while the other is down, and nothing to keep alive separately.
# Mounted last, so every /api route above wins over the catch-all.
#
# Deliberately NOT behind require_auth: Starlette serves a mount itself, outside
# the global dependency. That is what makes the sign-in screen reachable at all —
# a password screen you need a password to load cannot be used — and the bundle
# carries no secrets, by the rule that keeps keys in backend/.env.
if paths.STATIC_DIR and (paths.STATIC_DIR / "index.html").is_file():
    _INDEX = paths.STATIC_DIR / "index.html"

    @app.exception_handler(404)
    async def _spa_fallback(request, exc):
        """A client-side route is not a missing file.

        The router lives in the browser, so /engagements/<id> exists only there
        and must be answered with the app itself. Under /api a 404 is a real
        404 and stays one — handing an API caller a page of HTML would turn a
        clear error into a parse failure somewhere else.
        """
        if request.url.path.startswith("/api"):
            return JSONResponse({"detail": getattr(exc, "detail", "Not Found")}, status_code=404)
        # A path with a file extension asks for a file, and a missing file is a
        # 404. Answering /assets/Page-<old hash>.js with index.html made a tab
        # opened before a deploy fail with a MIME error instead of "not found".
        if "." in request.url.path.rsplit("/", 1)[-1]:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(_INDEX, headers={"Cache-Control": "no-cache"})

    class _Frontend(StaticFiles):
        """The built app, with caching that survives a deploy: index.html is
        revalidated every time, so a reload always names the current chunks;
        files under /assets carry a content hash and never change."""

        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable"
                if path.replace("\\", "/").startswith("assets/") else "no-cache")
            return response

    app.mount("/", _Frontend(directory=paths.STATIC_DIR, html=True), name="frontend")
