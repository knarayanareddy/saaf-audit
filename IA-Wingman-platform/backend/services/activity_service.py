"""Append-only AI activity log — the provenance / defensibility trail.

Every meaningful AI event (an agent run, a human acceptance, edit, or dismissal)
is written here. It is never mutated or deleted, so it survives agent re-runs and
gives auditors a record of *how* AI-assisted conclusions were reached.
"""
import json
import logging
from uuid import uuid4

from database import AsyncSessionLocal
from models.agent_activity import AgentActivity

logger = logging.getLogger("ia_wingman.activity")


async def log_activity(
    engagement_id: str,
    agent: str,
    action: str,
    summary: str | None = None,
    sources: list | None = None,
    confidence: str | None = None,
    actor: str = "AI",
) -> None:
    """Write one activity record. Best-effort: never breaks the caller."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(AgentActivity(
                id=str(uuid4()),
                engagement_id=engagement_id,
                agent=agent,
                action=action,
                summary=summary,
                sources=json.dumps(sources or []),
                confidence=confidence,
                actor=actor,
            ))
            await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to log activity (%s/%s): %s", agent, action, exc)
