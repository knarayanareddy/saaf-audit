"""Word and Excel export service — fills the organisation templates with audit data."""
import io
import copy
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Template files (read-only, never modified)
TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "IA team doc's"
ANL_TEMPLATE = TEMPLATE_DIR / "Preparation - Audit Notification Letter (2026) v1.0.docx"
KICKOFF_TEMPLATE = TEMPLATE_DIR / "Preparation - Kick off Meeting Agenda (2026) v1.0.docx"
BRA_TEMPLATE = TEMPLATE_DIR / "Preparation - Background risk assessment and work program (2026) v1.0.xlsx"

# Brand colour comes from the org profile so every export stays white-label.
def _brand_hex6() -> str:
    from organization import ORG
    return ((ORG.brand_hex or "#1E6B4F").lstrip("#") or "1E6B4F")[:6]


def _brand_rgb() -> RGBColor:
    h = _brand_hex6()
    try:
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except (ValueError, IndexError):
        return RGBColor(0x1E, 0x6B, 0x4F)


BRAND_GREEN = _brand_rgb()


def _replace_in_para(para, old: str, new: str):
    """Replace text in a paragraph, handling text split across multiple runs."""
    full = para.text
    if old not in full:
        return
    new_full = full.replace(old, new)
    # Clear all runs, set text in first run preserving its format
    for i, run in enumerate(para.runs):
        run.text = new_full if i == 0 else ""


def _replace_in_doc(doc: Document, replacements: dict):
    """Apply all replacements across paragraphs and table cells."""
    for old, new in replacements.items():
        # Main paragraphs
        for para in doc.paragraphs:
            _replace_in_para(para, old, str(new))
        # Table cells
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        _replace_in_para(para, old, str(new))


def _add_section(doc: Document, heading: str, content: str):
    """Append a styled section (heading + body) to a document."""
    h = doc.add_paragraph(heading)
    h.style = "Heading 2" if "Heading 2" in [s.name for s in doc.styles] else h.style
    run = h.runs[0] if h.runs else h.add_run(heading)
    run.bold = True
    run.font.color.rgb = BRAND_GREEN
    run.font.size = Pt(10)

    body = doc.add_paragraph(content or "")
    body.runs[0].font.size = Pt(9) if body.runs else None


# ── Audit report export ─────────────────────────────────────────────────────────

def generate_report_docx(report: dict, findings: list, eng: dict, annexes: list | None = None) -> bytes:
    """Assemble the audit report (exec summary, opinion, 5C findings) into Word.
    Brand-neutral; colours come from the org profile. AI-assisted; auditor signs.
    `annexes` (optional) adds an Explainability appendix, one block per finding."""
    brand = _brand_rgb()
    doc = Document()

    title = doc.add_paragraph("Internal Audit Report (draft)")
    if title.runs:
        title.runs[0].bold = True
        title.runs[0].font.size = Pt(18)
        title.runs[0].font.color.rgb = brand

    meta = doc.add_paragraph(
        f"Audit: {eng.get('name', '')} | Code: {eng.get('audit_code') or 'TBD'} | Entity: {eng.get('entity', '')}"
    )
    if meta.runs:
        meta.runs[0].font.size = Pt(9)

    opinion = (report.get("overall_opinion") or "").replace("_", " ").title()
    if opinion:
        op = doc.add_paragraph(f"Overall opinion: {opinion}")
        if op.runs:
            op.runs[0].bold = True
            op.runs[0].font.color.rgb = brand
            op.runs[0].font.size = Pt(11)

    if report.get("exec_summary"):
        _add_section(doc, "Executive summary", report["exec_summary"])

    rated = sorted(findings, key=lambda f: {"high": 0, "medium": 1, "low": 2}.get((f.get("rating") or "low"), 3))
    if rated:
        h = doc.add_paragraph("Findings")
        if h.runs:
            h.runs[0].bold = True
            h.runs[0].font.color.rgb = brand
            h.runs[0].font.size = Pt(13)
        for i, f in enumerate(rated, 1):
            fh = doc.add_paragraph(f"{i}. {f.get('title', '')}  [{(f.get('rating') or 'n/a').upper()}]")
            if fh.runs:
                fh.runs[0].bold = True
                fh.runs[0].font.size = Pt(11)
            for label, key in [("Condition", "condition"), ("Criteria", "criteria"), ("Cause", "cause"),
                               ("Effect", "effect"), ("Recommendation", "recommendation")]:
                val = f.get(key)
                if val:
                    p = doc.add_paragraph()
                    r1 = p.add_run(f"{label}: ")
                    r1.bold = True
                    r1.font.size = Pt(9)
                    r2 = p.add_run(str(val))
                    r2.font.size = Pt(9)

    if report.get("conclusion"):
        _add_section(doc, "Conclusion", report["conclusion"])

    # ── Appendix A — Explainability annexes ─────────────────────────────────────
    if annexes:
        doc.add_page_break()
        ah = doc.add_paragraph("Appendix A — Explainability annexes")
        if ah.runs:
            ah.runs[0].bold = True
            ah.runs[0].font.color.rgb = brand
            ah.runs[0].font.size = Pt(13)
        intro = doc.add_paragraph(
            "For each finding, a traceable account of how it was reached — aligned with the EU AI Act "
            "Art. 13/14 transparency and human-oversight principles. Grounding strength measures how much "
            "traceable support exists, not whether the finding is correct."
        )
        if intro.runs:
            intro.runs[0].font.size = Pt(8)
            intro.runs[0].italic = True
        for a in annexes:
            strength = a.get("strength") or {}
            trail = " -> ".join(a.get("grounding_trail") or [])
            fh = doc.add_paragraph(f"{a.get('title', 'Finding')}")
            if fh.runs:
                fh.runs[0].bold = True
                fh.runs[0].font.size = Pt(11)
            meta = doc.add_paragraph(
                f"Grounding strength: {strength.get('score', 0)}/100 ({strength.get('label', '')})"
                + (f"  |  Trail: {trail}" if trail else "")
            )
            if meta.runs:
                meta.runs[0].font.size = Pt(8)
                meta.runs[0].font.color.rgb = brand
            for q in a.get("questions", []):
                p = doc.add_paragraph()
                r1 = p.add_run(f"{q.get('n')}. {q.get('q')} ")
                r1.bold = True
                r1.font.size = Pt(9)
                r2 = p.add_run(str(q.get("answer", "")))
                r2.font.size = Pt(9)

    note = doc.add_paragraph("AI-assisted; reviewed and signed off by the responsible auditor.")
    if note.runs:
        note.runs[0].font.size = Pt(8)
        note.runs[0].italic = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Board / portfolio report export ─────────────────────────────────────────────

def generate_board_docx(board: dict, narrative: dict, org: dict) -> bytes:
    """Assemble the portfolio Board Report into Word: executive summary (AI or
    deterministic), portfolio table, findings severity, candidate hotspots and
    coverage gaps. Brand-neutral; AI-assisted, auditor signs."""
    brand = _brand_rgb()
    doc = Document()

    title = doc.add_paragraph(f"{org.get('name', 'Internal Audit')} — Board Report (draft)")
    if title.runs:
        title.runs[0].bold = True
        title.runs[0].font.size = Pt(18)
        title.runs[0].font.color.rgb = brand

    p = board.get("portfolio", {})
    meta = doc.add_paragraph(
        f"Portfolio: {p.get('total', 0)} engagements | {p.get('active', 0)} active | {p.get('closed', 0)} closed"
    )
    if meta.runs:
        meta.runs[0].font.size = Pt(9)

    opinion = (narrative.get("overall_opinion") or "").replace("_", " ").title()
    if opinion:
        op = doc.add_paragraph(f"Overall portfolio opinion: {opinion}")
        if op.runs:
            op.runs[0].bold = True
            op.runs[0].font.color.rgb = brand
            op.runs[0].font.size = Pt(11)

    if narrative.get("exec_summary"):
        _add_section(doc, "Executive summary", narrative["exec_summary"])

    msgs = narrative.get("key_messages") or []
    if msgs:
        kh = doc.add_paragraph("Key messages")
        if kh.runs:
            kh.runs[0].bold = True
            kh.runs[0].font.color.rgb = brand
            kh.runs[0].font.size = Pt(10)
        for m in msgs:
            b = doc.add_paragraph(str(m), style="List Bullet")
            if b.runs:
                b.runs[0].font.size = Pt(9)

    f = board.get("findings", {})
    rat = f.get("by_rating", {})
    _add_section(doc, "Findings across the portfolio",
                 f"{f.get('total', 0)} finding(s) across {f.get('engagements_with_findings', 0)} engagement(s): "
                 f"{rat.get('high', 0)} high, {rat.get('medium', 0)} medium, {rat.get('low', 0)} low.")

    hotspots = board.get("hotspots") or []
    hh = doc.add_paragraph("Candidate risk-and-control hotspots (verify)")
    if hh.runs:
        hh.runs[0].bold = True
        hh.runs[0].font.color.rgb = brand
        hh.runs[0].font.size = Pt(10)
    if hotspots:
        for h in hotspots:
            line = f"[{(h.get('severity') or '').upper()}] {h.get('engagement_name', '')} — {h.get('reason', '')}"
            refs = " / ".join(x for x in (h.get("risk_ref"), h.get("control_ref")) if x)
            if refs:
                line += f" ({refs})"
            bp = doc.add_paragraph(line, style="List Bullet")
            if bp.runs:
                bp.runs[0].font.size = Pt(9)
    else:
        doc.add_paragraph("None identified in the current data.").runs[0].font.size = Pt(9)

    ws = (board.get("coverage") or {}).get("entity_whitespace") or []
    if ws:
        _add_section(doc, "Assurance coverage gaps",
                     "No audit is recorded for: " + ", ".join(ws) + ".")

    note = doc.add_paragraph(
        f"{'AI-assisted' if narrative.get('generated_by') == 'ai' else 'Deterministically generated'}; "
        "reviewed and signed off by the responsible auditor."
    )
    if note.runs:
        note.runs[0].font.size = Pt(8)
        note.runs[0].italic = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── Interview minutes export ───────────────────────────────────────────────────

def generate_minutes_docx(session: dict, eng: dict) -> bytes:
    """Build interview minutes from a companion session. AI-assisted; reviewed by
    the auditor. No template needed — clean, brand-neutral document."""
    analysis = session.get("analysis") or {}
    brand = _brand_rgb()
    doc = Document()

    title = doc.add_paragraph("Interview minutes (draft)")
    if title.runs:
        title.runs[0].bold = True
        title.runs[0].font.size = Pt(16)
        title.runs[0].font.color.rgb = brand

    meta = doc.add_paragraph(
        f"Audit: {eng.get('name', '')} | Code: {eng.get('audit_code') or 'TBD'} | Entity: {eng.get('entity', '')}"
    )
    if meta.runs:
        meta.runs[0].font.size = Pt(9)
    role = session.get("label") or session.get("persona") or "Interviewee"
    sub = doc.add_paragraph(f"Persona/role: {role}    ·    AI-assisted; reviewed by auditor")
    if sub.runs:
        sub.runs[0].font.size = Pt(9)
        sub.runs[0].italic = True

    if analysis.get("summary"):
        _add_section(doc, "Summary", analysis["summary"])

    def _bullets(heading, items, render):
        if not items:
            return
        h = doc.add_paragraph(heading)
        if h.runs:
            h.runs[0].bold = True
            h.runs[0].font.color.rgb = brand
            h.runs[0].font.size = Pt(11)
        for it in items:
            p = doc.add_paragraph(render(it), style="List Bullet")
            if p.runs:
                p.runs[0].font.size = Pt(9)

    _bullets("Minutes", analysis.get("minutes", []), lambda x: str(x))
    _bullets("Observations", analysis.get("observations", []),
             lambda x: f"{x.get('text', '')}  [confidence: {x.get('confidence', 'n/a')}]" if isinstance(x, dict) else str(x))
    _bullets("Candidate control gaps (to verify)", analysis.get("control_gaps", []),
             lambda x: f"{x.get('text', '')} — verify: {x.get('verify', '')}" if isinstance(x, dict) else str(x))
    _bullets("Suggested follow-ups", analysis.get("follow_ups", []), lambda x: str(x))

    note = doc.add_paragraph(
        "These minutes were drafted with AI assistance from the auditor's own notes. "
        "Candidate control gaps are hypotheses to verify, not audit conclusions."
    )
    if note.runs:
        note.runs[0].font.size = Pt(8)
        note.runs[0].italic = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── ANL export ─────────────────────────────────────────────────────────────────

def generate_anl_docx(anl, eng) -> bytes:
    """Build a clean, white-label Audit Notification Letter. Returns bytes.

    Mirrors the standard ANL structure (metadata header + Background · Objectives ·
    Scope · Approach · Timing · Your responsibility) with the org brand colour and
    Inter body, ragged-right. Built from scratch so no third-party template branding
    (fonts, colours, sample names) can leak into the output."""
    doc = _build_anl_from_scratch(anl, eng)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _replace_guidance_with_content(doc: Document, anl: dict):
    """Replace the guidance/placeholder text paragraphs with real ANL content."""
    section_map = {
        "The text you write here should explain": ("background", anl.get("background")),
        "The objective of our work": ("objectives", anl.get("objectives")),
        "As a result of our preparatory work": ("scope", anl.get("scope_description")),
        "Not in scope": ("out_of_scope", None),  # handled separately
        "This Internal Audit engagement will be completed": ("approach", anl.get("approach")),
        "The fieldwork will be undertaken between": ("timing", _format_timing(anl)),
        "Please inform, as necessary": ("responsibility", anl.get("responsibility")),
    }
    for para in doc.paragraphs:
        for trigger, (_, content) in section_map.items():
            if trigger.lower() in para.text.lower() and content:
                for i, run in enumerate(para.runs):
                    run.text = content if i == 0 else ""
                break


def _format_timing(anl: dict) -> str:
    parts = []
    if anl.get("timing_fieldwork_start") and anl.get("timing_fieldwork_end"):
        parts.append(f"The fieldwork will be undertaken between {anl['timing_fieldwork_start']} and {anl['timing_fieldwork_end']}.")
    if anl.get("timing_draft_report"):
        parts.append(f"We expect to issue the draft report by {anl['timing_draft_report']}.")
    if anl.get("timing_mgmt_response"):
        parts.append(f"Management is expected to provide their response by {anl['timing_mgmt_response']}.")
    if anl.get("timing_final_report"):
        parts.append(f"The final report will be issued by {anl['timing_final_report']}.")
    return " ".join(parts) or "Timing to be confirmed."


_MUTED = RGBColor(0x8A, 0x96, 0x8F)


def _anl_heading(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.bold = True
    r.font.name = "Inter"
    r.font.size = Pt(11)
    r.font.color.rgb = _brand_rgb()


def _anl_body(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT  # ragged right, per the standard template
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text or "To be confirmed.")
    r.font.name = "Inter"
    r.font.size = Pt(9)


def _build_anl_from_scratch(anl: dict, eng: dict) -> Document:
    """A clean, white-label ANL: brand-coloured title + section headers, a metadata
    header block, and ragged-right Inter body — mirroring the standard ANL layout."""
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Inter"
    normal.font.size = Pt(9)

    # ── Title ──────────────────────────────────────────────────────────────
    tp = doc.add_paragraph()
    tp.paragraph_format.space_after = Pt(0)
    tr = tp.add_run("Internal Audit Notification Letter")
    tr.bold = True
    tr.font.name = "Inter"
    tr.font.size = Pt(18)
    tr.font.color.rgb = _brand_rgb()
    sp = doc.add_paragraph()
    sr = sp.add_run("Draft")
    sr.italic = True
    sr.font.name = "Inter"
    sr.font.size = Pt(9)
    sr.font.color.rgb = _MUTED

    # ── Metadata header block ──────────────────────────────────────────────
    team = eng.get("lead_auditor") or "To be confirmed"
    members = eng.get("team_members") or []
    if members:
        team += " (lead), " + ", ".join(str(m) for m in members)
    meta = [
        ("Engagement", f"{eng.get('audit_code') or 'TBD'} — {eng.get('name') or ''}"),
        ("Entity", eng.get("entity") or "—"),
        ("Internal Audit team", team),
        ("Scope period", eng.get("scope_period") or "To be confirmed"),
    ]
    table = doc.add_table(rows=len(meta), cols=2)
    for i, (k, v) in enumerate(meta):
        lc, vc = table.rows[i].cells
        lc.width = Inches(1.9)
        vc.width = Inches(4.6)
        lr = lc.paragraphs[0].add_run(k)
        lr.bold = True
        lr.font.name = "Inter"
        lr.font.size = Pt(9)
        vr = vc.paragraphs[0].add_run(v)
        vr.font.name = "Inter"
        vr.font.size = Pt(9)
    doc.add_paragraph()

    # ── Sections ───────────────────────────────────────────────────────────
    _anl_heading(doc, "Background")
    _anl_body(doc, anl.get("background"))
    _anl_heading(doc, "Objectives")
    _anl_body(doc, anl.get("objectives"))
    _anl_heading(doc, "Scope")
    _anl_body(doc, anl.get("scope_description"))
    if (anl.get("out_of_scope") or "").strip():
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        r1 = p.add_run("Not in scope:  ")
        r1.bold = True
        r1.font.name = "Inter"
        r1.font.size = Pt(9)
        r2 = p.add_run(anl["out_of_scope"])
        r2.font.name = "Inter"
        r2.font.size = Pt(9)
    _anl_heading(doc, "Approach")
    _anl_body(doc, anl.get("approach"))
    _anl_heading(doc, "Timing")
    _anl_body(doc, _format_timing(anl))
    _anl_heading(doc, "Your responsibility")
    _anl_body(doc, anl.get("responsibility"))
    return doc


# ── Kick-off Agenda export ─────────────────────────────────────────────────────

def generate_kickoff_docx(agenda_data: dict, eng: dict) -> bytes:
    """Fill the the organisation kick-off agenda template. Returns bytes."""
    if KICKOFF_TEMPLATE.exists():
        doc = Document(str(KICKOFF_TEMPLATE))
        replacements = {
            "26-xxx": eng.get("audit_code") or "26-xxx",
            "Engagement title": eng.get("name") or "",
            "DD/MM/YYYY": agenda_data.get("meeting_date") or "TBD",
        }
        _replace_in_doc(doc, replacements)
        # Inject agenda notes into relevant sections
        _inject_kickoff_notes(doc, agenda_data)
    else:
        doc = _build_kickoff_from_scratch(agenda_data, eng)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _inject_kickoff_notes(doc: Document, agenda_data: dict):
    """Insert prepared notes after each agenda section heading."""
    section_triggers = {
        "Welcome and objectives": "notes_welcome",
        "What are the aims and context": "notes_context",
        "What documentation and information do we have": "notes_documentation",
        "What documentation and information do we miss": "notes_missing",
        "Selection of subjects": "notes_scope",
        "Team composition": "notes_team",
        "Any other business": "notes_aob",
        "Next steps": "notes_next_steps",
    }
    for para in doc.paragraphs:
        for trigger, field in section_triggers.items():
            if trigger.lower() in para.text.lower():
                note = agenda_data.get(field)
                if note and "<Include" not in para.text:
                    # Insert note as a new run at end of paragraph
                    para.add_run(f"\n{note}")
                break


def _build_kickoff_from_scratch(agenda_data: dict, eng: dict) -> Document:
    doc = Document()
    doc.add_heading("Kick-off Meeting Agenda", 0)
    doc.add_paragraph(f"Audit: {eng.get('name')} | Code: {eng.get('audit_code') or 'TBD'}")
    doc.add_paragraph(f"Date: {agenda_data.get('meeting_date') or 'TBD'} | Attendees: {agenda_data.get('attendees') or 'TBD'}")
    sections = [
        ("1. Welcome and objectives", "notes_welcome"),
        ("2. Audit information in annual plan", "notes_context"),
        ("3. Available documentation and information", "notes_documentation"),
        ("4. Missing documentation", "notes_missing"),
        ("5. Scope — subjects, nature, depth", "notes_scope"),
        ("6. Team composition and planning", "notes_team"),
        ("7. Any other business", "notes_aob"),
        ("8. Next steps", "notes_next_steps"),
    ]
    for heading, field in sections:
        h = doc.add_paragraph(heading)
        if h.runs: h.runs[0].bold = True
        note = agenda_data.get(field)
        if note:
            doc.add_paragraph(note)
    return doc


# ── Background Risk Assessment export ─────────────────────────────────────────

def generate_bra_xlsx(bra_data: dict, eng: dict) -> bytes:
    """Fill the the organisation BRA Excel template with risk assessment data. Returns bytes."""
    import json as _json
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    risk_items = []
    if bra_data.get("risk_items"):
        try:
            risk_items = _json.loads(bra_data["risk_items"]) if isinstance(bra_data["risk_items"], str) else bra_data["risk_items"]
        except (TypeError, ValueError):
            risk_items = []

    if BRA_TEMPLATE.exists():
        wb = openpyxl.load_workbook(str(BRA_TEMPLATE))
        # Fill Background sheet
        _fill_bra_background(wb, bra_data, eng)
        # Fill Risk Assessment sheet
        _fill_bra_risk_sheet(wb, risk_items, eng)
    else:
        wb = _build_bra_from_scratch(bra_data, risk_items, eng)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fill_bra_background(wb, bra_data: dict, eng: dict):
    try:
        ws = wb["1. Background"]
    except KeyError:
        return
    # Replace audit name placeholder
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and "<include text here>" in str(cell.value).lower():
                cell.value = str(cell.value).replace(
                    "<include text here>", eng.get("name", "")
                ).replace("<Include text here>", eng.get("name", ""))

    # Fill section content (rows 5, 7, 9, 11 based on template structure — approximate)
    section_map = {
        "Organisational strategies": "section_strategy",
        "Risk tolerance": "section_risk_tolerance",
        "Governance, risk management": "section_governance",
        "Applicable frameworks": "section_frameworks",
    }
    for row in ws.iter_rows():
        for cell in row:
            val = str(cell.value or "")
            for trigger, field in section_map.items():
                if trigger.lower() in val.lower() and "<Include" in val:
                    content = bra_data.get(field, "")
                    if content:
                        cell.value = content


def _fill_bra_risk_sheet(wb, risk_items: list, eng: dict):
    try:
        ws = wb["2 RiskAssessment & WorkProgram"]
    except KeyError:
        return

    # Replace audit name
    for row in ws.iter_rows(max_row=5):
        for cell in row:
            if cell.value and "<include text here>" in str(cell.value).lower():
                cell.value = eng.get("name", "")

    # Find the first data row (after the header rows — typically row 9)
    start_row = 9
    for i, item in enumerate(risk_items):
        r = start_row + i * 2  # 2 rows per risk (template has merged rows)
        try:
            ws.cell(row=r, column=1).value = item.get("link_to_anl", "")
            ws.cell(row=r, column=2).value = item.get("ref", f"R{i+1}")
            ws.cell(row=r, column=3).value = item.get("description", "")
            ws.cell(row=r, column=4).value = item.get("process", "")
            ws.cell(row=r, column=5).value = item.get("risk_statement", "")
            ws.cell(row=r, column=6).value = item.get("inherent_risk", "High")
            ws.cell(row=r, column=7).value = item.get("controls", "")
            ws.cell(row=r, column=8).value = item.get("residual_risk", "Medium")
        except Exception:  # noqa: BLE001
            pass


def _build_bra_from_scratch(bra_data: dict, risk_items: list, eng: dict):
    """Fallback: simple Excel workbook without template."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    # Background sheet
    ws_bg = wb.active
    ws_bg.title = "1. Background"
    ws_bg["A1"] = f"Background — {eng.get('name')}"
    ws_bg["A1"].font = Font(bold=True, size=12)
    sections = [
        ("1. Strategies, objectives and risks", "section_strategy"),
        ("2. Risk tolerance", "section_risk_tolerance"),
        ("3. Governance and controls", "section_governance"),
        ("4. Applicable frameworks", "section_frameworks"),
    ]
    row = 3
    for label, field in sections:
        ws_bg.cell(row=row, column=1).value = label
        ws_bg.cell(row=row, column=1).font = Font(bold=True)
        row += 1
        ws_bg.cell(row=row, column=1).value = bra_data.get(field, "")
        ws_bg.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
        ws_bg.row_dimensions[row].height = 60
        row += 2
    ws_bg.column_dimensions["A"].width = 100

    # Risk sheet
    ws_ra = wb.create_sheet("2. Risk Assessment")
    headers = ["Link to ANL", "Ref", "Description", "Process", "Risk statement", "Inherent risk", "Controls", "Residual risk"]
    for c, h in enumerate(headers, 1):
        cell = ws_ra.cell(row=1, column=c, value=h)
        cell.font = Font(bold=True)
        fill = PatternFill("solid", fgColor=_brand_hex6())
        cell.fill = fill
        cell.font = Font(bold=True, color="FFFFFF")
    for r, item in enumerate(risk_items, 2):
        ws_ra.cell(row=r, column=1).value = item.get("link_to_anl", "")
        ws_ra.cell(row=r, column=2).value = item.get("ref", "")
        ws_ra.cell(row=r, column=3).value = item.get("description", "")
        ws_ra.cell(row=r, column=4).value = item.get("process", "")
        ws_ra.cell(row=r, column=5).value = item.get("risk_statement", "")
        ws_ra.cell(row=r, column=6).value = item.get("inherent_risk", "High")
        ws_ra.cell(row=r, column=7).value = item.get("controls", "")
        ws_ra.cell(row=r, column=8).value = item.get("residual_risk", "Medium")
    for c in range(1, 9):
        ws_ra.column_dimensions[get_column_letter(c)].width = 25
    return wb
