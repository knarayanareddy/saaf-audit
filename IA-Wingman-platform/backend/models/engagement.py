from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    audit_code = Column(String(20), nullable=True)
    name = Column(String(255), nullable=False)
    entity = Column(String(20), nullable=False)   # GRP | INT | AM | RET | BUS
    audit_type = Column(String(50), nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="to_be_scheduled")
    lead_auditor = Column(String(100), nullable=True)
    team_members = Column(Text, nullable=False, default="[]")  # JSON string
    planning_date = Column(String(20), nullable=True)
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    draft_report_date = Column(String(20), nullable=True)
    final_report_date = Column(String(20), nullable=True)
    scope_period = Column(String(100), nullable=True)
    jurisdictions = Column(Text, nullable=True)   # JSON list, e.g. ["NL","EU"] — audit-wide countries
    copilot_autonomy_paused = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# Audit-wide jurisdictions feed Topic Intelligence and both Frameworks apps. Agents read this
# off the engagement (not through the pipeline signature) so protected flows stay unchanged.
VALID_JURISDICTIONS = ["NL", "BE", "UK", "ES", "EU"]
_DEFAULT_JURISDICTIONS = ["NL", "EU"]


def jurisdictions_or_default(engagement) -> list[str]:
    """Return the engagement's selected jurisdictions, falling back to a sensible default
    when none are set, so downstream agents always have a scope to reason about."""
    import json
    raw = getattr(engagement, "jurisdictions", None)
    if not raw:
        return list(_DEFAULT_JURISDICTIONS)
    try:
        vals = json.loads(raw)
    except (ValueError, TypeError):
        return list(_DEFAULT_JURISDICTIONS)
    vals = [v for v in vals if v in VALID_JURISDICTIONS]
    return vals or list(_DEFAULT_JURISDICTIONS)
