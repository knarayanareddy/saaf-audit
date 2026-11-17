"""Idempotent demo-data backfill: fills only-null planning dates and audit codes.

Runs on every startup after seeding. It never overwrites a value that already
exists (so anything an auditor edits by hand survives restarts), and it is
deterministic — a fixed anchor date plus an id-derived jitter means the same
row always computes the same values. Purely for demo/timeline data; safe to run
repeatedly. lead_auditor is set to a privacy-safe ROLE label (never a real name)
for most active audits, with a deterministic few left empty so the dashboard
"attention" list surfaces genuine gaps rather than flagging every active audit.
team_members are still left empty.
"""
import hashlib
import logging
from datetime import date, timedelta

from sqlalchemy import select
from database import AsyncSessionLocal
from models.engagement import Engagement

logger = logging.getLogger("ia_wingman.backfill")

# Kept in step with shift_demo_dates.py: newly seeded rows must land in the same
# window as the existing portfolio, not two months behind it.
ANCHOR = date(2026, 9, 1)

# Day offsets from ANCHOR per status: (planning, start, end, draft_report, final_report)
_STATUS_OFFSETS = {
    "in_planning":     (-14,  21,  84,  98, 126),
    "in_fieldwork":    (-56, -28,  21,  35,  63),
    "in_reporting":    (-98, -70, -14,   3,  28),
    "closed":          (-168, -140, -84, -56, -35),
    "to_be_scheduled": (30,  60, 120, 134, 160),
}

_ENTITY_SHORT = {"GRP": "GR", "RET": "RE", "BUS": "BU", "AM": "AM", "INT": "IN"}

# Privacy-safe, role-based lead labels — never real people. They populate the
# lead field for a demo without pre-loading personal data.
_LEAD_ROLES = ["Lead Auditor", "Senior IA Manager", "Principal Auditor", "IA Manager", "Audit Team Lead"]
_ACTIVE = {"in_planning", "in_fieldwork", "in_reporting"}


def _jitter(engagement_id: str, spread: int = 21) -> int:
    """Deterministic 0..spread-1 derived from the engagement id."""
    h = int(hashlib.md5(engagement_id.encode()).hexdigest(), 16)
    return h % spread


def _iso(offset_days: int) -> str:
    return (ANCHOR + timedelta(days=offset_days)).isoformat()


async def backfill_engagement_dates() -> int:
    """Fill null dates + audit codes. Returns the number of rows written."""
    written = 0
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Engagement).order_by(Engagement.created_at, Engagement.id))
        engagements = result.scalars().all()

        # Audit-code sequencing: remember codes already in use so re-runs and
        # any hand-assigned codes are never duplicated.
        used_codes = {e.audit_code for e in engagements if e.audit_code}
        seq_per_entity: dict[str, int] = {}

        for e in engagements:
            changed = False
            offsets = _STATUS_OFFSETS.get(e.status)
            if offsets:
                j = _jitter(e.id)
                planning, start, end, draft, final = offsets
                # spread start/planning a little so timeline bars don't stack
                fields = {
                    "planning_date": planning + (j % 7),
                    "start_date": start + (j % 14),
                    "end_date": end + (j % 14),
                    "draft_report_date": draft + (j % 10),
                    "final_report_date": final + (j % 10),
                }
                for attr, off in fields.items():
                    if not getattr(e, attr):
                        setattr(e, attr, _iso(off))
                        changed = True

            # Assign a role-based lead to most active audits; leave a deterministic
            # ~quarter empty so "needs attention" shows real gaps, not every audit.
            if e.status in _ACTIVE and not e.lead_auditor and _jitter(e.id, 100) >= 25:
                e.lead_auditor = _LEAD_ROLES[_jitter(e.id, len(_LEAD_ROLES))]
                changed = True

            if not e.audit_code:
                short = _ENTITY_SHORT.get(e.entity, (e.entity or "XX")[:2].upper())
                n = seq_per_entity.get(short, 0) + 1
                code = f"IA-26-{short}{n:02d}"
                while code in used_codes:
                    n += 1
                    code = f"IA-26-{short}{n:02d}"
                seq_per_entity[short] = n
                used_codes.add(code)
                e.audit_code = code
                changed = True

            if changed:
                written += 1

        if written:
            await db.commit()
    logger.info("Backfill wrote %d engagement row(s).", written)
    return written
