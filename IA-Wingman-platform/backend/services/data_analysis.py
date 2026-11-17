"""Data-Analysis / Anomaly agent — deterministic full-population testing.

The analytics are computed in plain Python (stdlib only) over the whole dataset,
so every count is real and reproducible — the AI never invents a number. Each
check that finds exceptions becomes a proposed test in the RACM's TEST lane
(origin='ai', accepted=False, method='full_population'); the auditor accepts or
dismisses it. An optional AI narration step only adds a plain-language sentence
per check — explicitly forbidden from changing any figure.

Deterministic run is free (no AI). Narration is opt-in and best-effort.
"""
import json
from uuid import uuid4

from sqlalchemy import select

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from models.racm import RacmTest
from services.demo_dataset import demo_dataset

AGENT_TYPE = "data_analysis"
PROVENANCE_SOURCE = "data_analysis"
_THRESHOLD = 10000  # the approval threshold the gaming check looks just below


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _check(title, description, n, exceptions, examples):
    return {
        "title": title, "description": description, "sample_size": n,
        "exceptions_count": exceptions, "result": "exceptions" if exceptions > 0 else "pass",
        "examples": examples,
        "conclusion": (f"{exceptions} of {n} records flagged." if exceptions > 0
                       else f"No exceptions in {n} records."),
    }


def analyze(rows: list[dict]) -> dict:
    """Run the deterministic full-population checks. Pure function, no I/O."""
    n = len(rows)

    seen = {}
    for r in rows:
        seen.setdefault(r.get("customer_id"), []).append(r)
    dup_ids = [cid for cid, rs in seen.items() if cid and len(rs) > 1]
    dup_count = sum(len(seen[c]) for c in dup_ids)

    missing = [r for r in rows if (r.get("ubo_verified") or "").strip().lower() in ("", "no")]

    amts = sorted(a for a in (_num(r.get("amount")) for r in rows) if a is not None)
    outliers = []
    if len(amts) >= 4:
        q1 = amts[len(amts) // 4]
        q3 = amts[(3 * len(amts)) // 4]
        hi = q3 + 1.5 * (q3 - q1)
        outliers = [r for r in rows if (_num(r.get("amount")) or 0) > hi]

    band = [r for r in rows
            if _THRESHOLD * 0.9 <= (_num(r.get("amount")) or 0) < _THRESHOLD]

    sod = [r for r in rows if r.get("maker") and r.get("maker") == r.get("checker")]

    checks = [
        _check("Duplicate customers", "customer_id appears on more than one case",
               n, dup_count, dup_ids[:5]),
        _check("Missing beneficial-ownership evidence", "ubo_verified is empty or 'no'",
               n, len(missing), [r.get("case_id") for r in missing][:5]),
        _check("Amount outliers", "amount beyond Q3 + 1.5·IQR",
               n, len(outliers), [r.get("case_id") for r in outliers][:5]),
        _check(f"Possible threshold gaming (< {_THRESHOLD:,})",
               f"amount within 10% below the {_THRESHOLD:,} approval threshold",
               n, len(band), [r.get("case_id") for r in band][:5]),
        _check("Segregation-of-duties conflict", "maker equals checker on the same case",
               n, len(sod), [r.get("case_id") for r in sod][:5]),
    ]
    total_exceptions = sum(c["exceptions_count"] for c in checks)
    return {"row_count": n, "checks": checks, "total_exceptions": total_exceptions}


async def _replace_previous_proposals(db, engagement_id: str) -> None:
    """Drop this agent's earlier UNACCEPTED test proposals so re-runs don't pile
    up. Accepted tests (owned by the auditor) are never touched."""
    rows = (await db.execute(
        select(RacmTest).where(
            RacmTest.engagement_id == engagement_id,
            RacmTest.origin == "ai",
            RacmTest.accepted == False,  # noqa: E712
        )
    )).scalars().all()
    for t in rows:
        try:
            prov = json.loads(t.provenance) if t.provenance else {}
        except (json.JSONDecodeError, TypeError):
            prov = {}
        if prov.get("source_type") == PROVENANCE_SOURCE:
            await db.delete(t)


async def _write_test_proposals(engagement_id: str, run_id: str, checks: list) -> int:
    """Deterministically turn checks-with-exceptions into AI-proposed RACM tests."""
    created = 0
    async with AsyncSessionLocal() as db:
        await _replace_previous_proposals(db, engagement_id)
        last = (await db.execute(
            select(RacmTest).where(RacmTest.engagement_id == engagement_id)
            .order_by(RacmTest.sort_order.desc())
        )).scalars().first()
        order = (last.sort_order + 1) if last else 0
        for c in checks:
            if c["exceptions_count"] <= 0:
                continue
            provenance = json.dumps({
                "source_type": PROVENANCE_SOURCE,
                "source_ref": "full-population analytics",
                "rationale": c["description"],
                "run_id": run_id,
                "examples": c.get("examples"),
            })
            db.add(RacmTest(
                id=str(uuid4()), engagement_id=engagement_id, control_id=None,
                title=c["title"][:500], description=c["description"],
                method="full_population", sample_size=c["sample_size"],
                exceptions_count=c["exceptions_count"], result="exceptions",
                conclusion=c["conclusion"], origin="ai", accepted=False,
                confidence="high", provenance=provenance, sort_order=order + created,
            ))
            created += 1
        await db.commit()
    return created


async def _narrate(analysis: dict) -> None:
    """Optional AI narration: one plain-language sentence per check. The prompt
    forbids changing any figure; on any error we simply skip narration."""
    from services.ai_service import run_agent_to_json
    lines = "\n".join(
        f"- {c['title']}: {c['exceptions_count']} of {c['sample_size']} flagged ({c['description']})"
        for c in analysis["checks"]
    )
    prompt = f"""These are deterministic full-population data-analysis results for an audit. The counts are
final and correct — DO NOT change, recompute or invent any number.

RESULTS:
{lines}

Return ONLY a JSON object mapping each check title to a one-sentence, plain-language explanation of what
the result means for the audit and why it matters:
{{ "explanations": [ {{ "title": "<exact check title>", "explanation": "<one sentence>" }} ] }}
"""
    result = await run_agent_to_json(
        system_prompt=("You are an internal-audit data analyst. You explain deterministic analytics results "
                       "in plain language for a medior auditor. You never change the figures given to you."),
        user_prompt=prompt, max_tokens=1500,
    )
    if isinstance(result, dict):
        by_title = {e.get("title"): e.get("explanation") for e in result.get("explanations", [])}
        for c in analysis["checks"]:
            if c["title"] in by_title:
                c["explanation"] = by_title[c["title"]]


async def run_data_analysis(run_id: str, engagement_id: str, narrate: bool = False) -> None:
    """Background task: deterministic analysis → RACM test proposals → optional narration."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if not run:
            return
        run.status = "running"
        await db.commit()

    try:
        rows = demo_dataset()
        analysis = analyze(rows)
        proposed = await _write_test_proposals(engagement_id, run_id, analysis["checks"])
        analysis["proposed_test_count"] = proposed

        if narrate:
            try:
                await _narrate(analysis)
            except Exception:  # noqa: BLE001 — narration is best-effort, never fails the run
                pass

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.raw_output = json.dumps(analysis)
                run.input_summary = f"{analysis['row_count']} records · {analysis['total_exceptions']} exceptions · {proposed} tests proposed"
                run.status = "complete"
                await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.raw_output = json.dumps({"error": str(exc)[:500]})
                await db.commit()
