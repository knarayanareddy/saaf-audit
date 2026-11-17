"""Item-level run-action registry — the M7 counterpart to stage_actions.py.

Stage-level actions (stage_actions.py) are keyed by a STAGE_GRAPH stage_key,
one per engagement. Item-level actions here are keyed by an item TYPE
("finding", "interview_session") and act on ONE row of that type at a time —
copilot_orchestrator's item scanner calls the matching action once per
eligible row, passing that row's id.

Same principle as stage_actions.py: call the real FastAPI coroutine, don't
duplicate its setup logic (status transition, background-task queuing).
"""
from routers.reporting import draft_finding_ai
from routers.interview import analyse_session


async def _run_finding_draft(engagement_id, item_id, background_tasks, db):
    return await draft_finding_ai(engagement_id, item_id, background_tasks, db)


async def _run_interview_session_analysis(engagement_id, item_id, background_tasks, db):
    return await analyse_session(engagement_id, item_id, background_tasks, db)


# Every entry has the uniform signature (engagement_id, item_id, background_tasks, db).
ITEM_RUN_ACTIONS = {
    "finding": _run_finding_draft,
    "interview_session": _run_interview_session_analysis,
}
