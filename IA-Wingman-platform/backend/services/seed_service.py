from uuid import uuid4
from sqlalchemy import select, func
from database import AsyncSessionLocal
from models.engagement import Engagement

# No TEAM_ROSTER — names are never pre-loaded by the application.
# lead_auditor and team_members are filled in by auditors themselves.
# A compact, generic 15-audit annual plan spread across all business units,
# statuses and audit types — white-label, not tied to any real organisation.
SEED_ENGAGEMENTS = [
    # In planning
    {"name": "Customer Due Diligence Onboarding Review", "entity": "GRP", "type": "compliance", "status": "in_planning"},
    {"name": "ESG Risk Framework Assessment", "entity": "GRP", "type": "esg", "status": "in_planning"},
    {"name": "Conduct Risk & Complaints Handling", "entity": "RET", "type": "conduct", "status": "in_planning"},
    {"name": "Sustainable Finance Disclosure Review", "entity": "AM", "type": "esg", "status": "in_planning"},
    # In fieldwork
    {"name": "IT Security Management Review", "entity": "GRP", "type": "it", "status": "in_fieldwork"},
    {"name": "Cybersecurity Controls Review", "entity": "RET", "type": "it", "status": "in_fieldwork"},
    {"name": "Client Asset Segregation", "entity": "AM", "type": "compliance", "status": "in_fieldwork"},
    # In reporting
    {"name": "Fraud Risk Management", "entity": "GRP", "type": "operational", "status": "in_reporting"},
    {"name": "Capital and Liquidity Adequacy Assessment", "entity": "GRP", "type": "financial", "status": "in_reporting"},
    {"name": "Sanctions Screening Process", "entity": "INT", "type": "compliance", "status": "in_reporting"},
    # To be scheduled
    {"name": "Third-Party & Outsourcing Risk", "entity": "BUS", "type": "operational", "status": "to_be_scheduled"},
    {"name": "Data Governance Framework", "entity": "GRP", "type": "it", "status": "to_be_scheduled"},
    {"name": "Anti-Money Laundering Controls Review", "entity": "BUS", "type": "compliance", "status": "to_be_scheduled"},
    # Closed
    {"name": "Business Continuity & Disaster Recovery", "entity": "INT", "type": "it", "status": "closed"},
    {"name": "Model Risk & AI Governance", "entity": "GRP", "type": "validation", "status": "closed"},
]


async def seed_if_empty():
    """Only seeds on first run. Safe to call on every server start."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(Engagement))
        count = result.scalar()
        if count and count > 0:
            return
        for e in SEED_ENGAGEMENTS:
            db.add(Engagement(
                id=str(uuid4()),
                name=e["name"],
                entity=e["entity"],
                audit_type=e["type"],
                status=e["status"],
                lead_auditor=None,
                team_members="[]",
            ))
        await db.commit()
