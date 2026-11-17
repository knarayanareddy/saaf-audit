"""Tests for the shared framework store (services/framework_rows.py).

    venv/Scripts/python.exe -m tests.test_framework_rows

The bug this locks down was real and latent. Laws and guidance both write to
`ApplicableFramework` and both clear their own rows before re-inserting, but
only the guidance side filtered on category:

    # laws, before
    delete(...).where(engagement_id == ..., source == "auto_analysed")

Any other writer reusing that source string would have lost its rows to a re-run
of the laws agent. Nothing did yet, which is exactly why it survived.
"""
import asyncio
import sys

from sqlalchemy import select

from database import AsyncSessionLocal
from models.planning import ApplicableFramework
from services.framework_rows import GUIDANCE, LAW, replace_rows

failures: list[str] = []
ENGAGEMENT = "test-framework-rows"


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


LAWS = [
    {"framework_code": "AMLD5", "framework_name": "Fifth Anti-Money Laundering Directive",
     "what_it_requires": "Beneficial ownership must be verified.",
     "specific_provision": "Art. 13", "jurisdiction": "EU", "is_primary": "yes"},
    {"framework_code": "Wwft", "framework_name": "Wet ter voorkoming van witwassen",
     "what_it_requires": "Client due diligence before onboarding.", "jurisdiction": "NL"},
]

GUIDES = [
    {"guidance_code": "DNB-2024", "guidance_name": "DNB Good Practices CDD",
     "what_it_says": "Risk-based CDD expectations.", "guidance_type": "good practice",
     "issuer": "DNB", "jurisdiction": "NL"},
]


async def _rows(db, category=None):
    stmt = select(ApplicableFramework).where(ApplicableFramework.engagement_id == ENGAGEMENT)
    if category:
        stmt = stmt.where(ApplicableFramework.category == category)
    return (await db.execute(stmt)).scalars().all()


async def run() -> None:
    async with AsyncSessionLocal() as db:
        # Start from a known state — this engagement id belongs to the test.
        for row in await _rows(db):
            await db.delete(row)
        await db.commit()

        print("\nwriting both kinds:")
        await replace_rows(db, ENGAGEMENT, LAW, LAWS)
        await replace_rows(db, ENGAGEMENT, GUIDANCE, GUIDES)
        await db.commit()
        check(len(await _rows(db, "law")) == 2, "two laws stored")
        check(len(await _rows(db, "guidance")) == 1, "one guidance row stored")

        print("\na kind clears only its own rows:")
        # The bug: before this module, re-running laws deleted by source alone.
        await replace_rows(db, ENGAGEMENT, LAW, [LAWS[0]])
        await db.commit()
        check(len(await _rows(db, "law")) == 1, "the laws re-run replaced its own rows")
        check(len(await _rows(db, "guidance")) == 1, "and left the guidance row alone")

        print("\nfield mapping follows the agent's own vocabulary:")
        law = (await _rows(db, "law"))[0]
        check(law.framework_name == "Fifth Anti-Money Laundering Directive", "law name mapped")
        check(law.applicability_rationale.startswith("Beneficial"),
              "'what_it_requires' became the rationale")
        check(law.specific_provision == "Art. 13", "'specific_provision' carried over")
        check(law.is_primary is True, "'yes' read as a boolean")

        await replace_rows(db, ENGAGEMENT, GUIDANCE, GUIDES)
        await db.commit()
        gd = (await _rows(db, "guidance"))[0]
        check(gd.applicability_rationale.startswith("Risk-based"),
              "'what_it_says' became the rationale for guidance")
        check(gd.specific_provision == "good practice", "'guidance_type' carried over")

        print("\nan unnamed row is skipped, not stored blank:")
        # A framework with no name is something the model failed to find, not a
        # framework that exists without a name.
        written = await replace_rows(db, ENGAGEMENT, LAW, [{"framework_code": "X"}])
        await db.commit()
        check(written == 0, "nothing written")
        check(len(await _rows(db, "law")) == 0, "and the table reflects it")

        print("\na guidance row with no code falls back to its issuer:")
        await replace_rows(db, ENGAGEMENT, GUIDANCE,
                           [{"guidance_name": "Dear CEO letter", "issuer": "AFM"}])
        await db.commit()
        check((await _rows(db, "guidance"))[0].framework_code == "AFM", "issuer used as the code")

        for row in await _rows(db):
            await db.delete(row)
        await db.commit()


def main():
    asyncio.run(run())
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILURE(S): ' + str(failures)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
