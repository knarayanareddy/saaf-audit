from sqlalchemy import text, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from paths import DB_PATH

# Absolute, because a host decides the working directory a process starts in and
# a relative path would quietly create a second, empty database there.
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    """WAL + a busy timeout so concurrent agent writes don't hit 'database is locked'.

    WAL lets readers and a writer coexist; busy_timeout makes a blocked writer
    wait instead of failing immediately. Applied on every new connection.
    """
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()


class Base(DeclarativeBase):
    pass


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Nullable-column additions that are safe to run on every startup.
# SQLite raises OperationalError if the column already exists — we catch and continue.
_MIGRATIONS = [
    "ALTER TABLE racm_tests ADD COLUMN priority VARCHAR(10)",
    "ALTER TABLE racm_tests ADD COLUMN assigned_to VARCHAR(120)",
    "ALTER TABLE racm_tests ADD COLUMN progress VARCHAR(20)",
    "ALTER TABLE applicable_frameworks ADD COLUMN specific_provision TEXT",
    "ALTER TABLE applicable_frameworks ADD COLUMN source_url VARCHAR(500)",
    "ALTER TABLE applicable_frameworks ADD COLUMN confidence VARCHAR(20) DEFAULT 'medium'",
    "ALTER TABLE applicable_frameworks ADD COLUMN jurisdiction VARCHAR(20)",
    "ALTER TABLE process_notes ADD COLUMN status VARCHAR(30) DEFAULT 'not_started'",
    "ALTER TABLE process_notes ADD COLUMN reasoning TEXT",
    "ALTER TABLE process_notes ADD COLUMN process_items TEXT",
    "ALTER TABLE process_notes ADD COLUMN preliminary_observations TEXT",
    "ALTER TABLE process_notes ADD COLUMN analyser_run_id VARCHAR(36)",
    "ALTER TABLE topic_intelligence ADD COLUMN search_results TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN search_queries TEXT",
    "ALTER TABLE agent_runs ADD COLUMN search_progress TEXT",
    "ALTER TABLE agent_runs ADD COLUMN search_queries TEXT",
    "ALTER TABLE engagements ADD COLUMN planning_date VARCHAR(20)",
    "ALTER TABLE engagements ADD COLUMN draft_report_date VARCHAR(20)",
    "ALTER TABLE engagements ADD COLUMN final_report_date VARCHAR(20)",
    "ALTER TABLE topic_intelligence ADD COLUMN lens1_summary TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens1_sources TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens1_run_id VARCHAR(36)",
    "ALTER TABLE topic_intelligence ADD COLUMN lens2_summary TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens2_sources TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens2_run_id VARCHAR(36)",
    "ALTER TABLE topic_intelligence ADD COLUMN lens3_summary TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens3_sources TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens3_run_id VARCHAR(36)",
    "ALTER TABLE topic_intelligence ADD COLUMN lens4_notes TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN lens4_state VARCHAR(20)",
    "ALTER TABLE uploaded_documents ADD COLUMN injection_flags TEXT",
    "ALTER TABLE engagements ADD COLUMN jurisdictions TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN topic_primer TEXT",
    "ALTER TABLE kickoff_agendas ADD COLUMN audit_purpose TEXT",
    "ALTER TABLE kickoff_agendas ADD COLUMN questions_for_auditor TEXT",
    "ALTER TABLE applicable_frameworks ADD COLUMN category VARCHAR(20) DEFAULT 'law'",
    "ALTER TABLE findings ADD COLUMN racm_test_id VARCHAR(36)",
    "ALTER TABLE scope_decisions ADD COLUMN provenance TEXT",
    "ALTER TABLE findings ADD COLUMN explainability TEXT",
    "ALTER TABLE findings ADD COLUMN validation TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN extra_context TEXT",
    "ALTER TABLE agent_calls ADD COLUMN cache_write_tokens INTEGER",
    "ALTER TABLE agent_calls ADD COLUMN prompt_version VARCHAR(16)",
    "ALTER TABLE agent_calls ADD COLUMN reasoned BOOLEAN",
    "ALTER TABLE board_reports ADD COLUMN based_on_sig TEXT",
    "ALTER TABLE engagements ADD COLUMN copilot_autonomy_paused BOOLEAN DEFAULT 0",
    "ALTER TABLE copilot_tasks ADD COLUMN item_id VARCHAR(36)",
    "ALTER TABLE scope_items ADD COLUMN source_ref VARCHAR(64)",
    "ALTER TABLE key_audit_questions ADD COLUMN source_ref VARCHAR(64)",
    "ALTER TABLE racm_evidence ADD COLUMN requested_from VARCHAR(120)",
    "ALTER TABLE racm_evidence ADD COLUMN period VARCHAR(120)",
    "ALTER TABLE racm_evidence ADD COLUMN drl_item_id VARCHAR(36)",
    "ALTER TABLE copilot_messages ADD COLUMN is_proactive BOOLEAN DEFAULT 0",
    "ALTER TABLE topic_intelligence ADD COLUMN proposed_frameworks TEXT",
    "ALTER TABLE topic_intelligence ADD COLUMN synthesis_failed BOOLEAN DEFAULT 0",
    "ALTER TABLE topic_intelligence ADD COLUMN verification TEXT",
    "ALTER TABLE copilot_tasks ADD COLUMN rationale TEXT",
    "ALTER TABLE drl_documents ADD COLUMN distribution_email TEXT",
    "ALTER TABLE drl_documents ADD COLUMN reminder_log TEXT",
    "ALTER TABLE agent_calls ADD COLUMN repair VARCHAR(30)",
    "ALTER TABLE agent_calls ADD COLUMN caller VARCHAR(80)",
    "ALTER TABLE rcsa_templates ADD COLUMN primary_band VARCHAR(200)",
]


async def run_migrations() -> None:
    async with engine.begin() as conn:
        for sql in _MIGRATIONS:
            try:
                await conn.execute(text(sql))
            except OperationalError:
                pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
