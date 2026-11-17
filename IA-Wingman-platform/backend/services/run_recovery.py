"""Clearing out work that stopped existing when the process did.

An agent run lives inside the process that started it. When that process goes
away — a deploy, a crash, a laptop closing, a free-tier dyno going to sleep —
the database keeps the last thing it was told: `pending`. Nothing ever corrects
it, because the only thing that could have is gone.

The screen then says "Agents running…" forever over a scan that no one is
performing. That is the failure this module exists to prevent, and it is the
same rule the ledger and the coverage check follow: **a claim and a fact must
not look the same**. "Running" has to mean a process is running.

Startup is the one moment when that can be settled without guessing. Anything
still marked pending or running was started by a process that no longer exists,
by definition — this one just started. So it is not alive, and the row is
corrected to say so, with a reason an auditor can read.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.planning import TopicIntelligence

logger = logging.getLogger("ia.wingman")

#: What a recovered run reports. Phrased as what happened, not as a failure of
#: the agent: nothing went wrong with the work, the work never happened.
INTERRUPTED = "The server restarted while this agent was running, so the run never finished."

_UNFINISHED = ("pending", "running")


async def recover_interrupted_runs() -> dict:
    """Mark everything left mid-flight by a previous process, and unstick the page.

    Returns a small report so startup can log what it corrected — silence here
    would hide the very thing this is for.
    """
    async with AsyncSessionLocal() as db:
        runs = (await db.execute(
            select(AgentRun).where(AgentRun.status.in_(_UNFINISHED))
        )).scalars().all()

        for run in runs:
            run.status = "failed"
            run.raw_output = json.dumps({"error": INTERRUPTED})
            run.search_progress = json.dumps({"stage": "failed", "error": INTERRUPTED})

        stuck = (await db.execute(
            select(TopicIntelligence).where(TopicIntelligence.status == "agents_pending")
        )).scalars().all()

        for ti in stuck:
            # Whatever the lenses did manage to produce is real and stays. The
            # question is only which screen the auditor should land on: the
            # results they already have, or the start screen to run it again.
            has_output = any((ti.lens1_summary, ti.lens2_summary, ti.lens3_summary,
                              ti.regulatory_summary, ti.internal_framework_summary))
            ti.status = "review" if has_output else "not_started"
            if not has_output:
                ti.progress_pct = 0

        await db.commit()

    report = {"runs": len(runs), "scans": len(stuck)}
    if runs or stuck:
        logger.warning(
            "Recovered after restart: %d agent run(s) marked failed, %d scan(s) unstuck.",
            report["runs"], report["scans"],
        )
    return report
