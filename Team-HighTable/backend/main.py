from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from claude_client import ClaudeAnalyzer
from embeddings import EmbeddingService
from models import AnalysisResponse, AnalyzeRequest
from teammate_client import TeamMateClient, _field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Globals — populated during startup
# ---------------------------------------------------------------------------

teammate_client: Optional[TeamMateClient] = None
embedding_service: Optional[EmbeddingService] = None
claude_analyzer: Optional[ClaudeAnalyzer] = None
cache_loaded: bool = False


async def _warm_cache() -> None:
    global cache_loaded
    try:
        logger.info("Warming issue cache in background…")
        assert teammate_client is not None
        await teammate_client.get_effective_issues()
        cache_loaded = True
        logger.info("Cache warm-up complete")
    except Exception as exc:
        logger.warning("Cache warm-up failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global teammate_client, embedding_service, claude_analyzer

    teammate_base_url = os.environ.get(
        "TEAMMATE_BASE_URL", "https://br1ght8.teammatehosting.com/TeamMate"
    )
    teammate_api_key = os.environ.get("TEAMMATE_API_KEY", "")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    teammate_client = TeamMateClient(
        base_url=teammate_base_url,
        api_key=teammate_api_key,
    )
    embedding_service = EmbeddingService()
    claude_analyzer = ClaudeAnalyzer(
        api_key=anthropic_api_key,
        teammate_base_url=teammate_base_url,
    )

    # Kick off cache warm-up without blocking startup
    asyncio.create_task(_warm_cache())

    yield

    # Cleanup (nothing to close for now)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HighTable Backend",
    description="AI-powered audit issue similarity search and recommendation generation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

BACKEND_API_KEY = os.environ.get("BACKEND_API_KEY", "")


async def verify_api_key(x_backend_key: Optional[str] = Header(default=None)) -> None:
    """Verify the X-Backend-Key header if BACKEND_API_KEY is configured."""
    if not BACKEND_API_KEY:
        # No key configured — allow all requests (local dev mode)
        return
    if x_backend_key != BACKEND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Backend-Key header",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"status": "ok", "cache_loaded": cache_loaded}


@app.get("/api/issue/{issue_id}", dependencies=[Depends(verify_api_key)])
async def get_issue(issue_id: str) -> Dict[str, Any]:
    """Fetch a single issue from TeamMate+ by ID."""
    assert teammate_client is not None, "TeamMate client not initialised"
    try:
        issue = await teammate_client.get_issue(issue_id)
        return {
            "id": str(_field(issue, "id", "Id", "issueId", "IssueId") or issue_id),
            "title": _field(issue, "title", "Title") or "",
            "description": _field(issue, "description", "Description") or "",
        }
    except Exception as exc:
        logger.error("Error fetching issue %s: %s", issue_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch issue from TeamMate+: {exc}",
        )


@app.post("/api/analyze", dependencies=[Depends(verify_api_key)])
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    """Find similar past issues and generate an AI-powered recommendation."""
    assert teammate_client is not None
    assert embedding_service is not None
    assert claude_analyzer is not None

    # If an issue_id was supplied, fetch the issue content from TeamMate+ first
    if request.issue_id:
        try:
            raw_issue = await teammate_client.get_issue(request.issue_id)
            fetched_title = _field(raw_issue, "title", "Title") or ""
            fetched_description = _field(raw_issue, "description", "Description") or ""
            # Prefer fetched values if the request fields are empty
            if not request.title and fetched_title:
                request = AnalyzeRequest(
                    title=fetched_title,
                    description=fetched_description or request.description,
                    issue_id=request.issue_id,
                )
        except Exception as exc:
            logger.warning(
                "Could not fetch issue %s from TeamMate+ (using provided text): %s",
                request.issue_id,
                exc,
            )

    # Retrieve all effective (Closed-Verified) issues
    effective_issues = await teammate_client.get_effective_issues()

    if not effective_issues:
        logger.warning("No effective issues found in cache — returning empty analysis")
        return AnalysisResponse(
            similar_issues=[],
            draft_recommendation="No historical issues are available to base a recommendation on.",
            key_themes=[],
        )

    # Semantic similarity search
    current_text = f"{request.title} {request.description}"
    similar = embedding_service.find_similar(current_text, effective_issues, top_k=5)

    # Claude analysis
    response = await claude_analyzer.analyze(request, similar)
    return response


@app.get("/api/diagnostic", dependencies=[Depends(verify_api_key)])
async def diagnostic() -> Dict[str, Any]:
    """Return raw first-page response from TeamMate+ for debugging."""
    assert teammate_client is not None
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try issues with both old and new pagination params
        issues_resp = await client.get(
            f"{teammate_client.base_url}/api/v1/Issues",
            headers=teammate_client._headers(),
            params={"pageNumber": 1, "pageSize": 5},
        )
        issues_resp_legacy = await client.get(
            f"{teammate_client.base_url}/api/v1/Issues",
            headers=teammate_client._headers(),
            params={"pageIndex": 0, "pageSize": 5},
        )
        # Try fetching a known issue by ID (from recommendation parent)
        issue1_resp = await client.get(
            f"{teammate_client.base_url}/api/v1/Issues/1",
            headers=teammate_client._headers(),
        )
        recs_resp = await client.get(
            f"{teammate_client.base_url}/api/v1/Recommendations",
            headers=teammate_client._headers(),
            params={"pageNumber": 1, "pageSize": 2},
        )
    return {
        "issues_pageNumber_status": issues_resp.status_code,
        "issues_pageNumber_raw": issues_resp.json(),
        "issues_pageIndex_status": issues_resp_legacy.status_code,
        "issues_pageIndex_raw": issues_resp_legacy.json(),
        "issue_1_status": issue1_resp.status_code,
        "issue_1_raw": issue1_resp.json(),
        "recommendations_status": recs_resp.status_code,
        "recommendations_raw": recs_resp.json(),
    }


@app.post("/api/refresh-cache", dependencies=[Depends(verify_api_key)])
async def refresh_cache() -> Dict[str, Any]:
    """Invalidate the TeamMate+ issue cache and reload it in the background."""
    global cache_loaded
    assert teammate_client is not None

    teammate_client.invalidate_cache()
    cache_loaded = False
    asyncio.create_task(_warm_cache())
    return {"status": "cache refresh started"}
