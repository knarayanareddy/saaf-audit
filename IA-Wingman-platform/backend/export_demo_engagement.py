"""Export one audit from the local database as a demo snapshot.

    venv/Scripts/python.exe export_demo_engagement.py 26-047

Writes seed_data/demo_engagements/<audit code>.json, which every fresh start
loads when that audit is missing (services/seed_demo_snapshots.py). Run it
again after changing the audit locally to carry the change into the demo;
commit the file, and a deploy brings it online.

Read-only on the database. The file goes into the repository, so look at what
the audit holds before exporting it: no personal data, no client documents.
"""
import asyncio
import json
import sys

from sqlalchemy import select

import main  # noqa: F401 — registers every model
from models.engagement import Engagement
from database import AsyncSessionLocal
from services.seed_demo_snapshots import (
    SNAPSHOT_DIR, SNAPSHOT_TABLES, VIA_SCOPE, model_for, snapshot_value,
)


async def export(audit_code: str) -> None:
    async with AsyncSessionLocal() as db:
        eng = (await db.execute(select(Engagement).where(Engagement.audit_code == audit_code))).scalars().first()
        if not eng:
            sys.exit(f"No audit with code {audit_code}")
        scope_model = model_for("scope_objectives")
        scope_ids = list((await db.execute(
            select(scope_model.id).where(scope_model.engagement_id == eng.id))).scalars().all())

        tables = {}
        for table in SNAPSHOT_TABLES:
            model = model_for(table)
            if table == "engagements":
                q = select(model).where(model.id == eng.id)
            elif table in VIA_SCOPE:
                q = select(model).where(model.scope_id.in_(scope_ids or [""]))
            else:
                q = select(model).where(model.engagement_id == eng.id)
            keys = [a.key for a in model.__mapper__.column_attrs]
            tables[table] = [{k: snapshot_value(getattr(obj, k)) for k in keys}
                             for obj in (await db.execute(q)).scalars().all()]

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / f"{audit_code}.json"
    out.write_text(json.dumps({"engagement_id": eng.id, "audit_code": audit_code, "name": eng.name,
                               "tables": tables}, ensure_ascii=False, indent=1, default=str) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"{out.relative_to(SNAPSHOT_DIR.parent.parent)}: "
          + ", ".join(f"{t} {len(r)}" for t, r in tables.items() if r))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asyncio.run(export(sys.argv[1]))
