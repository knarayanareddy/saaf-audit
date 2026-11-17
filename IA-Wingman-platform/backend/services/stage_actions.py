"""Stage -> run-action registry.

Maps a STAGE_GRAPH key (services/orchestrator.py) to the exact router handler
that starts drafting/analysis for it. Both the copilot's manual "run this
stage" chat tool (propose_run_stage) and the future autonomous orchestrator
call through this registry, so a stage's setup logic (row creation, status
transitions, AgentRun bookkeeping) is never duplicated — they invoke the same
coroutine FastAPI itself would call for the equivalent HTTP request.

Only stages with a genuine, single-shot "run this now" trigger are listed.
Stages that are manual-entry, always-computed, or need extra per-item context
(e.g. scope, drl, fieldwork, findings) are intentionally absent — there is no
one action to propose for them. So are the stages the auditor starts
themselves, after adding what they know (AUDITOR_STARTED_STAGE_KEYS below). quality_coverage is the same story: it's a
live-computed view (services/coverage_service.py), never a stored draft, so
there is nothing to "run" — it's absent for that reason alone, not because it
was overlooked.
"""
from routers.planning import analyse_framework_requirements, analyse_process_notes
from routers.bra import draft_bra
from routers.anl import draft_anl
from routers.kickoff import draft_kickoff
from routers.phase3 import generate_work_program_endpoint, generate_drl_endpoint
from routers.interview import build_guide
from routers.racm import scoping_run, run_governance_assessment_endpoint, run_data_analysis_endpoint
from routers.reporting import draft_report_ai
from routers.review import run_review

#: Stages the system never starts by itself, and that no chat proposal starts
#: either: the auditor presses Run on the stage's own page.
#:
#: Topic Intelligence is the one. It searches the web and the supervisors' sites
#: with whatever it is given, and what it is given is the auditor's to decide:
#: the documents, the keyword, the sources, and what the auditor already knows.
#: It used to start itself — any page that polled /agents/pack queued it the
#: moment its gate opened — and ran empty-handed, spending the money on an
#: answer nobody had briefed. Listed here so that every route that could start
#: a stage can say why this one refuses, and so a test can hold them all to it.
AUDITOR_STARTED_STAGE_KEYS = frozenset({"topic_intelligence"})


async def _run_drl(engagement_id, background_tasks, db):
    return await generate_drl_endpoint(engagement_id, db)


async def _run_racm_scoping(engagement_id, background_tasks, db):
    return await scoping_run(engagement_id, db)


async def _run_racm_data_analysis(engagement_id, background_tasks, db):
    # run_data_analysis_endpoint's signature has `narrate` between
    # background_tasks and db — pass db by keyword so it can't silently bind
    # to the wrong (narrate) parameter.
    return await run_data_analysis_endpoint(engagement_id, background_tasks, db=db)


async def _run_quality_review(engagement_id, background_tasks, db):
    # One stage_key, three artifacts — run_review's own _load_artifact already
    # no-ops (status="no_data", no LLM call) for whichever of the three has
    # nothing to review yet, so firing all three unconditionally is safe.
    for artifact in ("topic_intelligence", "scope", "frameworks"):
        await run_review(engagement_id, artifact, background_tasks, db=db)


async def _run_quality_peer_review(engagement_id, background_tasks, db):
    # artifact is a required positional param between engagement_id and
    # background_tasks in run_review's real signature — db by keyword again.
    return await run_review(engagement_id, "peer_review", background_tasks, db=db)


# Every entry has the uniform signature (engagement_id, background_tasks, db).
# Keep the key set in sync with ai_service.py:CHAT_TOOLS' propose_run_stage enum.
STAGE_RUN_ACTIONS = {
    "frameworks": analyse_framework_requirements,
    "process_understanding": analyse_process_notes,
    "bra": draft_bra,
    "anl": draft_anl,
    "kickoff": draft_kickoff,
    "work_program": generate_work_program_endpoint,
    "drl": _run_drl,
    "interview_guide": build_guide,
    "racm_scoping": _run_racm_scoping,
    "racm_governance": run_governance_assessment_endpoint,
    "racm_data_analysis": _run_racm_data_analysis,
    "report_draft": draft_report_ai,
    "quality_review": _run_quality_review,
    "quality_peer_review": _run_quality_peer_review,
}
