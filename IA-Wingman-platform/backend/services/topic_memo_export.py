"""The Topic Intelligence memo as a Word document.

The memo lives on one page of the platform, and an auditor who wants to put it in a file,
send it to a sponsor or read it on paper had nothing to hand over. This is that, built from
the same answer the page reads so the two cannot differ.

Three things it does on purpose:
- it says what the memo is: AI-assisted research, whether the auditor has accepted it, and
  how many searches stand behind each lens;
- it shows what the auditor selected, and says how many items were left out, so a reader
  does not take a shortlist for the whole proposal;
- a point the research could not settle is printed as open, never rounded up.
"""
from __future__ import annotations

import io
import re
from datetime import date

from docx import Document
from docx.shared import Pt, RGBColor

from services.word_export import _brand_rgb

_BOLD = re.compile(r"(\*\*[^*]+\*\*)")

_VERDICT = {"confirmed": "Confirmed", "corrected": "Corrected", "not_found": "Not settled"}
_TIER = {"core": "Core", "supporting": "Supporting", "optional": "Optional"}


def _runs(paragraph, text: str, size: float = 10) -> None:
    """Text with **bold** segments, as the primer is written."""
    for part in _BOLD.split(text or ""):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        run = paragraph.add_run(part[2:-2] if bold else part)
        run.bold = bold
        run.font.size = Pt(size)


def _heading(doc, text: str, level: int = 1) -> None:
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = _brand_rgb()


def _lines(doc, text: str | None, size: float = 10) -> None:
    """A lead sentence and '- ' bullets, which is how the lenses and the primer write."""
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            _runs(doc.add_paragraph(style="List Bullet"), line[2:], size)
        else:
            _runs(doc.add_paragraph(), line, size)


def _bullets(doc, items: list[str], empty: str = "None.") -> None:
    if not items:
        doc.add_paragraph(empty).runs[0].italic = True
        return
    for item in items:
        _runs(doc.add_paragraph(style="List Bullet"), item)


def _selected(items: list[dict]) -> tuple[list[dict], int]:
    chosen = [i for i in items if i.get("included", True)]
    return chosen, len(items) - len(chosen)


def _left_out(doc, n: int) -> None:
    if n:
        note = doc.add_paragraph(f"{n} further proposed item{'s' if n != 1 else ''} not selected by the auditor.")
        note.runs[0].italic = True
        note.runs[0].font.size = Pt(9)
        note.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def _search_line(search: dict | None) -> str:
    if not search:
        return "Search record not available."
    if not search.get("web_search"):
        return "Live search was off: built-in knowledge only."
    text = f"{search.get('used', 0)} of {search.get('allowed', 0)} searches used."
    if search.get("used", 0) == 0:
        text = "No searches ran: treat this summary as written from memory and verify it."
    if search.get("errors"):
        text += f" Search errors: {', '.join(sorted(set(search['errors'])))}."
    return text


def _sources(doc, sources: list[dict]) -> None:
    for src in sources or []:
        title = src.get("title") or src.get("url") or "Source"
        extra = " · ".join(p for p in (src.get("date"), src.get("url")) if p)
        _runs(doc.add_paragraph(style="List Bullet"), f"{title}" + (f" ({extra})" if extra else ""), 9)


def generate_topic_memo_docx(ti: dict, eng: dict) -> bytes:
    """`ti` is the answer of GET /planning/{id}/topic-intelligence; `eng` is {name, audit_code, entity}."""
    doc = Document()
    title = doc.add_heading(f"Topic Intelligence memo: {eng.get('name', '')}", level=0)
    for run in title.runs:
        run.font.color.rgb = _brand_rgb()

    status = "Accepted by the auditor" if ti.get("memo_accepted") else "Draft: not yet accepted by the auditor"
    meta = doc.add_paragraph()
    _runs(meta, f"**Audit:** {eng.get('audit_code') or 'TBD'} · **Entity:** {eng.get('entity', '')} · "
                f"**Date:** {date.today().isoformat()} · **Status:** {status}", 9)
    note = doc.add_paragraph(
        "AI-assisted research. The summaries below were written by Topic Intelligence from web research and "
        "must be verified by the auditor before they are relied on. Each lens states how many searches stand "
        "behind it.")
    note.runs[0].italic = True
    note.runs[0].font.size = Pt(9)

    if ti.get("topic_primer"):
        _heading(doc, "The topic in plain words")
        _lines(doc, ti["topic_primer"])

    if ti.get("conclusion"):
        _heading(doc, "Recommended scope")
        _lines(doc, ti["conclusion"])

    verification = ti.get("verification")
    if verification:
        _heading(doc, "Verification of open points")
        checks = verification.get("checks", [])
        if not checks:
            doc.add_paragraph("Nothing in the research needed checking.")
        for c in checks:
            para = doc.add_paragraph(style="List Bullet")
            _runs(para, f"**{_VERDICT.get(c.get('verdict'), 'Not settled')}:** {c.get('claim', '')} "
                        f"{c.get('finding', '')}" + (f" ({c['source_url']})" if c.get("source_url") else ""))
        searched = f"{verification.get('searches_used', 0)} of {verification.get('searches_allowed', 0)} searches used."
        doc.add_paragraph(searched).runs[0].font.size = Pt(9)

    risks, left = _selected(ti.get("key_risk_areas", []))
    if risks or left:
        _heading(doc, "Key risk areas")
        for r in risks:
            line = f"**{r.get('title', '')}**"
            if r.get("rationale"):
                line += f": {r['rationale']}"
            if r.get("basis"):
                line += f" (Basis: {r['basis']})"
            _runs(doc.add_paragraph(style="List Bullet"), line)
        _left_out(doc, left)

    excluded, left = _selected(ti.get("excluded_areas", []))
    if excluded or left:
        _heading(doc, "Out of scope")
        for a in excluded:
            _runs(doc.add_paragraph(style="List Bullet"),
                  f"**{a.get('title', '')}**" + (f": {a['rationale']}" if a.get("rationale") else ""))
        _left_out(doc, left)

    agenda = ti.get("interview_agenda") or {}
    key_qs, left = _selected(agenda.get("key_audit_questions", []))
    if key_qs or left:
        _heading(doc, "Key audit questions")
        _bullets(doc, [q.get("question_text", "") for q in key_qs])
        _left_out(doc, left)
    sponsor, left = _selected(agenda.get("sponsor", []))
    if sponsor or left:
        _heading(doc, "Questions for the sponsor (kick-off meeting)")
        _bullets(doc, [q.get("question_text", "") for q in sponsor])
        _left_out(doc, left)
    sme, left = _selected(agenda.get("sme", []))
    if sme or left:
        _heading(doc, "Questions for experts (interviews)")
        _bullets(doc, [q.get("question_text", "") for q in sme])
        _left_out(doc, left)
    if agenda.get("ia_prework"):
        _heading(doc, "Preparation for the audit team (still to do)")
        _bullets(doc, [p if isinstance(p, str) else p.get("question_text", "") for p in agenda["ia_prework"]])

    frameworks = ti.get("proposed_frameworks", [])
    if frameworks:
        _heading(doc, "Frameworks")
        chosen = [f for f in frameworks if f.get("included", True)]
        doc.add_paragraph(f"{len(chosen)} of {len(frameworks)} proposed frameworks selected by the auditor.").runs[0].font.size = Pt(9)
        for f in frameworks:
            mark = "Selected" if f.get("included", True) else "Not selected"
            line = (f"**{f.get('framework_name', f.get('framework_code', ''))}** "
                    f"({_TIER.get(f.get('tier'), 'Supporting')}, {f.get('jurisdiction') or 'n/a'}, {mark})")
            if f.get("applicability_rationale"):
                line += f": {f['applicability_rationale']}"
            _runs(doc.add_paragraph(style="List Bullet"), line)

    _heading(doc, "Research behind the memo")
    for key, name in (("lens1", "Normative & regulatory"), ("lens2", "Supervisory & enforcement"),
                      ("lens3", "Society, trends & incidents")):
        if not ti.get(f"{key}_summary"):
            continue
        _heading(doc, name, level=2)
        p = doc.add_paragraph()
        _runs(p, _search_line(ti.get(f"{key}_search")), 9)
        _lines(doc, ti[f"{key}_summary"])
        queries = (ti.get(f"{key}_search") or {}).get("queries") or []
        if queries:
            doc.add_paragraph("Searched for: " + "; ".join(queries)).runs[0].font.size = Pt(9)
        if ti.get(f"{key}_sources"):
            doc.add_paragraph("Sources").runs[0].bold = True
            _sources(doc, [s for s in ti[f"{key}_sources"] if s.get("title") or s.get("url")])

    if ti.get("lens4_notes"):
        _heading(doc, "Internal context added by the auditor", level=2)
        _lines(doc, ti["lens4_notes"])

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
