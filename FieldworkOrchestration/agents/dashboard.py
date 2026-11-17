"""Local HTML monitoring dashboard for one fieldwork run.

Renders ``orchestrator.approval_summary(run_id)`` — per-stage quality
verdict + approval status — plus the finalization state, into a single,
self-contained HTML file: no server, no external assets, works fully
offline from a double-click. This is the visibility layer the rest of
agents/README.md's monitoring section refers to; the data itself lives in
``audit_trail.py`` / ``orchestrator.py`` — this module only renders it.

    from agents.dashboard import write_dashboard
    path = write_dashboard(run_id)   # -> runs/<run_id>/dashboard.html

Scoped to one run at a time, the same unit everything else (audit trail,
quality, approvals) already uses. A cross-run/engagement overview would be a
natural next step if you need to monitor many runs at once, not built here.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from agents.audit_trail import AuditTrail
from agents.orchestrator import approval_summary

_QUALITY_LABELS = {
    "pass": "Pass",
    "requires_revision": "Requires revision",
    "fail": "Fail",
    None: "Not yet reviewed",
}

_APPROVAL_LABELS = {
    "approved": "Approved",
    "rejected": "Rejected",
    "pending": "Pending",
}

_STYLE = """
:root {
  --bg: #f7f7f5; --surface: #ffffff; --border: #e5e3de; --text: #1f1e1c; --text-muted: #6b6862;
  --green-bg: #e7f5ea; --green-text: #1f6d3a; --amber-bg: #fdf1dd; --amber-text: #92590c;
  --red-bg: #fbe9e7; --red-text: #a3311a; --gray-bg: #eeece8; --gray-text: #57544e;
  --accent: #2f6f4f;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161513; --surface: #201f1c; --border: #322f2a; --text: #ece9e2; --text-muted: #9a968d;
    --green-bg: #163524; --green-text: #6fd396; --amber-bg: #3a2b0c; --amber-text: #e8b053;
    --red-bg: #3a1a15; --red-text: #f0897a; --gray-bg: #2a2823; --gray-text: #b3aea3;
    --accent: #6fd396;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
main { max-width: 880px; margin: 0 auto; padding: 40px 24px 80px; }
h1 { font-size: 20px; margin: 0 0 4px; }
.run-id { font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--text-muted); margin: 0 0 24px; }
.banner {
  border-radius: 10px; padding: 14px 18px; font-weight: 600; margin-bottom: 20px;
  display: flex; align-items: center; gap: 8px;
}
.banner-final { background: var(--green-bg); color: var(--green-text); }
.banner-ready { background: var(--green-bg); color: var(--green-text); }
.banner-rejected { background: var(--red-bg); color: var(--red-text); }
.banner-pending { background: var(--amber-bg); color: var(--amber-text); }
.counts { display: flex; gap: 10px; margin-bottom: 28px; flex-wrap: wrap; }
.count {
  background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 14px; font-size: 13px; color: var(--text-muted);
}
.count b { color: var(--text); font-size: 15px; display: block; }
.card {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 18px 20px; margin-bottom: 14px;
}
.card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.agent { font-weight: 600; font-size: 15px; }
.timestamp { font-size: 12px; color: var(--text-muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.badges { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.pill {
  display: inline-flex; align-items: center; gap: 6px; border-radius: 999px;
  padding: 3px 10px; font-size: 12px; font-weight: 600;
}
.pill-pass, .pill-approved { background: var(--green-bg); color: var(--green-text); }
.pill-requires_revision, .pill-pending { background: var(--amber-bg); color: var(--amber-text); }
.pill-fail, .pill-rejected { background: var(--red-bg); color: var(--red-text); }
.pill-none { background: var(--gray-bg); color: var(--gray-text); }
.confidence { font-size: 12px; color: var(--text-muted); }
.rationale { margin: 10px 0 0; font-size: 13px; color: var(--text-muted); }
.issues { margin: 8px 0 0; padding-left: 18px; font-size: 13px; }
.issues li { margin-bottom: 3px; }
.approval-note {
  margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);
  font-size: 13px; color: var(--text-muted);
}
.empty { color: var(--text-muted); text-align: center; padding: 40px 0; }
footer { margin-top: 32px; font-size: 12px; color: var(--text-muted); text-align: center; }
"""


def render_dashboard(run_id: str) -> str:
    """Render one run's status as a self-contained HTML page."""
    trail = AuditTrail(run_id=run_id)
    summary = approval_summary(run_id)
    approvals_by_entry: dict[str, list[dict]] = {}
    for a in trail.approvals():
        approvals_by_entry.setdefault(a["entry_id"], []).append(a)

    finalized_path = trail.path.parent / "finalized.json"
    finalized = (
        json.loads(finalized_path.read_text(encoding="utf-8"))
        if finalized_path.exists()
        else None
    )

    counts = {"approved": 0, "rejected": 0, "pending": 0}
    for row in summary:
        counts[row["approval_status"]] += 1

    cards = "\n".join(
        _render_card(row, approvals_by_entry.get(row["entry_id"], [])) for row in summary
    )
    if not cards:
        cards = '<p class="empty">No entries recorded for this run yet.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fieldwork run {html.escape(run_id)}</title>
<style>{_STYLE}</style>
</head>
<body>
<main>
  <h1>Fieldwork run status</h1>
  <p class="run-id">{html.escape(run_id)}</p>
  {_render_banner(finalized, counts, len(summary))}
  <div class="counts">
    <div class="count"><b>{len(summary)}</b>total steps</div>
    <div class="count"><b>{counts['approved']}</b>approved</div>
    <div class="count"><b>{counts['pending']}</b>pending</div>
    <div class="count"><b>{counts['rejected']}</b>rejected</div>
  </div>
  {cards}
  <footer>Generated from runs/{html.escape(run_id)}/ — re-run write_dashboard() after new decisions to refresh.</footer>
</main>
</body>
</html>"""


def write_dashboard(run_id: str, out_path: Path | None = None) -> Path:
    """Render and write the dashboard, by default to ``runs/<run_id>/dashboard.html``."""
    trail = AuditTrail(run_id=run_id)
    out_path = out_path or (trail.path.parent / "dashboard.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_dashboard(run_id), encoding="utf-8")
    return out_path


def _render_banner(finalized: dict | None, counts: dict, total: int) -> str:
    if finalized:
        return (
            f'<div class="banner banner-final">✓ Finalized '
            f'{html.escape(finalized["finalized_at"])}</div>'
        )
    if counts["rejected"]:
        return '<div class="banner banner-rejected">⚠ One or more steps rejected — needs auditor attention</div>'
    if total > 0 and counts["approved"] == total:
        return '<div class="banner banner-ready">Every step approved — ready to finalize</div>'
    return '<div class="banner banner-pending">Awaiting auditor review</div>'


def _render_card(row: dict, approval_history: list[dict]) -> str:
    quality = row["quality"] or {}
    verdict = quality.get("verdict")
    confidence = quality.get("confidence")
    issues = quality.get("issues") or []
    rationale = quality.get("rationale")

    quality_pill = (
        f'<span class="pill pill-{html.escape(str(verdict))}">{html.escape(_QUALITY_LABELS.get(verdict, verdict or "?"))}</span>'
        + (f'<span class="confidence">confidence: {html.escape(confidence)}</span>' if confidence else "")
    )
    approval_pill = (
        f'<span class="pill pill-{html.escape(row["approval_status"])}">'
        f'{html.escape(_APPROVAL_LABELS.get(row["approval_status"], row["approval_status"]))}</span>'
    )

    issues_html = ""
    if issues:
        items = "".join(f"<li>{html.escape(i)}</li>" for i in issues)
        issues_html = f'<ul class="issues">{items}</ul>'

    rationale_html = f'<p class="rationale">{html.escape(rationale)}</p>' if rationale else ""

    approval_note = ""
    if approval_history:
        latest = approval_history[-1]
        note = f'{html.escape(_APPROVAL_LABELS.get(latest["decision"], latest["decision"]))} by {html.escape(latest["reviewer"])}'
        if latest.get("comment"):
            note += f' — "{html.escape(latest["comment"])}"'
        if len(approval_history) > 1:
            note += f" ({len(approval_history)} decisions recorded, most recent shown)"
        approval_note = f'<div class="approval-note">{note}</div>'

    return f"""<div class="card">
  <div class="card-head">
    <span class="agent">{html.escape(row['agent'])}</span>
    <span class="timestamp">{html.escape(row['timestamp'])}</span>
  </div>
  <div class="badges">{quality_pill}{approval_pill}</div>
  {rationale_html}
  {issues_html}
  {approval_note}
</div>"""
