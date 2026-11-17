"""Privacy Guard fieldwork agent — deterministic, no AI.

Scans the fieldwork dataset, detects and classifies PII against the audit
purpose, masks/pseudonymises per role, and records a tamper-evident audit
trail. Runs in the standard AgentRun lifecycle (pending -> running -> complete |
failed). Writes nothing into the RACM spine.
"""

import json

from database import AsyncSessionLocal
from models.agent_run import AgentRun
from services.demo_dataset import demo_dataset

from .config import MIN_PSEUDONYM_KEY_LENGTH, get_pseudonym_key, load_legal_bases
from .models import AuditContext, Role
from .pipeline import PrivacyGuardPipeline

AGENT_TYPE = "privacy_guard"


def _legal_basis_for(purpose: str) -> str:
    purpose_map = load_legal_bases().get("purpose_to_legal_basis", {})
    return purpose_map.get(purpose, "art_5_1_c")


def _config_error() -> dict | None:
    """Return a UI-friendly result when the pseudonymisation key is unusable,
    rather than crashing the run. Mirrors the standalone app's fail-closed UX."""
    key = get_pseudonym_key()
    if not key:
        return {
            "config_ok": False,
            "message": (
                "No pseudonymisation key configured. Set GDPR_PSEUDONYM_KEY in "
                "backend/.env (at least 32 characters, unique to this deployment) "
                "and restart the backend."
            ),
        }
    if len(key) < MIN_PSEUDONYM_KEY_LENGTH:
        return {
            "config_ok": False,
            "message": (
                f"GDPR_PSEUDONYM_KEY must be at least {MIN_PSEUDONYM_KEY_LENGTH} "
                f"characters; it is currently {len(key)}."
            ),
        }
    return None


async def run_privacy_guard(
    run_id: str,
    engagement_id: str,
    role: str = "auditor",
    purpose: str = "customer_due_diligence",
    justification: str | None = None,
) -> None:
    """Background task: deterministic PII scan -> masked view + audit trail."""
    async with AsyncSessionLocal() as db:
        run = await db.get(AgentRun, run_id)
        if not run:
            return
        run.status = "running"
        await db.commit()

    try:
        config_err = _config_error()
        if config_err is not None:
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.raw_output = json.dumps(config_err)
                    run.input_summary = "Pseudonymisation key not configured"
                    run.status = "complete"
                    await db.commit()
            return

        ctx = AuditContext(
            role=Role(role),
            purpose=purpose,
            legal_basis=_legal_basis_for(purpose),
            justification=justification,
        )

        rows = demo_dataset()
        pipeline = PrivacyGuardPipeline(audit_context=ctx)
        result = pipeline.process_records(rows)
        result["config_ok"] = True

        summary = result["summary"]
        input_summary = (
            f"{summary['records_processed']} records · {summary['total_pii_fields']} PII fields · "
            f"{summary['total_masked']} masked · {summary['role']}"
        )

        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.raw_output = json.dumps(result)
                run.input_summary = input_summary
                run.status = "complete"
                await db.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.raw_output = json.dumps({"error": str(exc)[:500]})
                await db.commit()
