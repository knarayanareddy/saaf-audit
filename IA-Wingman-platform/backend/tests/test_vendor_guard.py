"""Dependency-free tests for the Vendor Guard fieldwork agent.

Run from the backend dir:
    venv/Scripts/python.exe -m tests.test_vendor_guard

Covers the DETERMINISTIC surface only (no AI calls):
  - Finding status/severity normalisation (alias maps)
  - specialist applicability by AI / government flags
  - all 8 curated framework files load
  - compute_rag_scorecard Red/Amber/Green + gap_register ordering
  - _write_risk_proposals: only Critical/High gaps become proposals, idempotent
The specialist assessments and memo are opt-in AI and are not exercised here.
"""
import asyncio
import sys
from uuid import uuid4

from services.vendor_guard.models import Finding, normalize_status, normalize_severity
from services.vendor_guard.assessors import applicable_specialists, SPECIALISTS, _load_framework
from services.vendor_guard.scorecard import compute_rag_scorecard, gap_register, overall_rag

failures: list[str] = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def _F(fw, cid, status, sev):
    return Finding(framework=fw, control_id=cid, control_name="x",
                   status=status, severity=sev, evidence="e", recommendation="r")


def test_normalisation():
    print("normalisation:")
    check(normalize_status("not met") == "Gap", "'not met' -> Gap")
    check(normalize_status("partially compliant") == "Partial", "'partially compliant' -> Partial")
    check(normalize_status("n/a") == "Not Applicable", "'n/a' -> Not Applicable")
    check(normalize_status("weird") == "Partial", "unknown status -> Partial")
    check(normalize_severity("severe") == "Critical", "'severe' -> Critical")
    check(normalize_severity("minor") == "Low", "'minor' -> Low")
    check(normalize_severity("weird") == "Medium", "unknown severity -> Medium")


def test_frameworks_and_applicability():
    print("frameworks + applicability:")
    ok = all(_load_framework(f).strip() for s in SPECIALISTS.values() for f in s["frameworks"])
    check(ok, "all 8 curated framework files load")
    check(applicable_specialists(False, False) == ["security", "resilience"], "base: security + resilience")
    check("ai_trust" in applicable_specialists(True, False), "AI flag adds ai_trust")
    check("gov_baseline" in applicable_specialists(False, True), "gov flag adds gov_baseline")
    check("ai_trust" not in applicable_specialists(False, False), "no AI flag -> no ai_trust")
    check("gov_baseline" not in applicable_specialists(False, False), "no gov flag -> no gov_baseline")


def test_scorecard():
    print("scorecard:")
    findings = [
        _F("ISO 27001", "A.9", "Gap", "High"),
        _F("ISO 27001", "A.5", "Compliant", "Info"),
        _F("DORA", "Art.17", "Partial", "Medium"),
        _F("BIO2", "B.1", "Compliant", "Info"),
    ]
    sc = compute_rag_scorecard(findings)
    check(sc["ISO 27001"]["rag"] == "Red", "High gap -> Red")
    check(sc["DORA"]["rag"] == "Amber", "Partial only -> Amber")
    check(sc["BIO2"]["rag"] == "Green", "all compliant -> Green")
    check(overall_rag(sc) == "Red", "overall = worst = Red")
    reg = gap_register(findings)
    check(reg[0]["status"] == "Gap", "gap register puts gaps first")


def test_proposals():
    print("risk proposals (deterministic):")
    # `_replace_previous_proposals` moved to services/risk_proposals, where the
    # governance assessor shares it. The discipline it carries — a re-run clears
    # only its OWN unaccepted proposals — is tested there, for both agents at once.
    from services.vendor_guard.agent import _write_risk_proposals, PROVENANCE_SOURCE
    from services.risk_proposals import replace_previous as _replace_previous_proposals
    from database import create_tables, run_migrations, AsyncSessionLocal
    import models  # noqa: F401
    from sqlalchemy import select, delete
    from models.racm import RacmRisk

    eid = f"test-vg-{uuid4()}"
    findings = [
        _F("ISO 27001", "A.9.1", "Gap", "Critical"),   # -> proposed
        _F("DORA", "Art.17", "Gap", "High"),           # -> proposed
        _F("NIS2", "Art.21", "Gap", "Medium"),         # NOT proposed (medium)
        _F("BIO2", "B.1", "Partial", "High"),          # NOT proposed (not a gap)
        _F("ISO 27001", "A.5", "Compliant", "Info"),   # NOT proposed
    ]

    async def go():
        await create_tables(); await run_migrations()
        n1 = await _write_risk_proposals(eid, "run-1", findings)
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(RacmRisk).where(RacmRisk.engagement_id == eid))).scalars().all()
        n2 = await _write_risk_proposals(eid, "run-2", findings)  # idempotent re-run
        async with AsyncSessionLocal() as db:
            rows2 = (await db.execute(select(RacmRisk).where(RacmRisk.engagement_id == eid))).scalars().all()
            # cleanup
            await db.execute(delete(RacmRisk).where(RacmRisk.engagement_id == eid))
            await db.commit()
        return n1, len(rows), n2, len(rows2), rows

    n1, count1, n2, count2, rows = asyncio.run(go())
    check(n1 == 2, "only the 2 Critical/High gaps become proposals")
    check(count1 == 2, "exactly 2 rows written")
    check(n2 == 2 and count2 == 2, "re-run is idempotent (still 2, no pile-up)")
    check(all(r.origin == "ai" and r.accepted is False for r in rows), "proposals are ai/unaccepted")
    check(all(r.inherent_rating == "high" for r in rows), "Critical/High map to inherent_rating 'high'")


def main():
    test_normalisation()
    test_frameworks_and_applicability()
    test_scorecard()
    test_proposals()
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
