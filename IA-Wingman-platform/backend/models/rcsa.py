"""The RCSA an audit reads, and what the auditor decided about relying on it.

An RCSA is the **auditee's own risk and control self-assessment**. Everything
here is evidence about the control environment, never Internal Audit's
conclusion, and every view that shows it says so. That is the invariant of this
whole area, and `rcsa_mapping.AUDITEE_LABEL` is the one string it travels in.

Four tables, and the split between them is the design:

* `RcsaTemplate` — a column mapping, confirmed once by a person. A bank's export
  has no standard shape: the column names differ per template, per department
  and per year, so a hardcoded parser works exactly once. The mapping is named,
  reusable and **not tied to an engagement** — the second import from the same
  template is one click.
* `RcsaImport` — one upload, for one engagement, read with one template.
* `RcsaRow` — one risk-and-control line, keeping **the whole source row verbatim**
  beside the fields projected out of it. That is what makes a mapping correction
  a re-projection instead of a re-upload: the residual rating in a real export
  turned out to exist twice — once during change implementation, once at go-live
  — and which of the two an auditor means is a judgement they may revise.
* `RelianceDecision` — the moment IA leans on second-line work is *reliance*, and
  the standards require assessing the quality of what you rely on before you rely
  on it. Without this row, "the second line said it was fine" would read in the
  file as "we established it was fine".
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class RcsaTemplate(Base):
    __tablename__ = "rcsa_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(200), nullable=False)
    #: Free text: the department or export this shape belongs to.
    source_label = Column(String(200), nullable=True)

    #: Which rows of the sheet form the header. A real export carries a title
    #: block above it and a banded, multi-row header below that, so this is a
    #: list of row numbers rather than "row 1".
    header_rows = Column(Text, nullable=False, default="[1]")   # JSON: [int]
    sheet_name = Column(String(200), nullable=True)

    #: The mapping itself: one entry per source column, in column order.
    #: [{"column": "Exposure (residual)", "band": "Residual … go-live",
    #:   "target": "residual_exposure" | null, "why": "..."}]
    #: A column with target null is **unmapped and kept** — reported, never
    #: guessed, because a wrong match is worse than a visible gap.
    columns = Column(Text, nullable=False, default="[]")        # JSON

    #: Which band's values are read as "the" residual rating. A real export
    #: carries two — during change implementation, and at go-live — and both are
    #: true statements about different moments. Which one an audit leans on is
    #: the auditor's judgement, so it is stored beside their confirmation rather
    #: than decided by whichever column the parser saw last.
    primary_band = Column(String(200), nullable=True)

    confirmed_by = Column(String(120), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class RcsaImport(Base):
    __tablename__ = "rcsa_imports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    engagement_id = Column(String(36), nullable=False, index=True)
    template_id = Column(String(36), nullable=True, index=True)

    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    sheet_name = Column(String(200), nullable=True)
    #: What the business calls the process this export covers, and over which
    #: period it was assessed. Both are the auditee's own words.
    process = Column(String(300), nullable=True)
    period = Column(String(120), nullable=True)

    status = Column(String(30), nullable=False, default="uploaded")
    # uploaded | mapping_proposed | imported | failed
    row_count = Column(Integer, nullable=False, default=0)
    error = Column(String(500), nullable=True)

    imported_by = Column(String(120), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())


class RcsaRow(Base):
    __tablename__ = "rcsa_rows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    import_id = Column(String(36), nullable=False, index=True)
    #: Where it sat in the sheet, so a row can be pointed at in the source.
    sheet_row = Column(Integer, nullable=False, default=0)

    #: The source row as it was recorded, column name → cell text. Kept whole:
    #: re-projecting under a corrected mapping must never need the file again.
    raw = Column(Text, nullable=False, default="{}")            # JSON
    #: The fields projected out of `raw` by the template, ratings parsed.
    projected = Column(Text, nullable=False, default="{}")      # JSON

    #: Copied out of `projected` for querying and display; both are the
    #: auditee's own assessment, never IA's.
    risk_title = Column(String(500), nullable=True)
    process = Column(String(300), nullable=True)
    key_risk = Column(Boolean, nullable=True)


class RelianceDecision(Base):
    __tablename__ = "rcsa_reliance_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    rcsa_import_id = Column(String(36), nullable=False, index=True)

    #: Did the auditor assess the quality of this second-line work? `extent`
    #: says how far they will lean on it, and `rationale` is why. All three are
    #: required together: an extent without a rationale is a preference.
    quality_assessed = Column(Boolean, nullable=False, default=False)
    extent = Column(String(10), nullable=False, default="none")  # full | partial | none
    rationale = Column(Text, nullable=False, default="")

    decided_by = Column(String(120), nullable=True)
    #: Set in Python, not by the database. Decisions are append-only and the
    #: latest one governs, so reading them back depends on their order — and
    #: SQLite's `now()` has second precision, which is coarse enough that two
    #: decisions recorded in the same second cannot be told apart. A second-line
    #: reliance that was withdrawn and then re-granted would resolve to
    #: whichever row the query happened to return first.
    decided_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(timezone.utc))
