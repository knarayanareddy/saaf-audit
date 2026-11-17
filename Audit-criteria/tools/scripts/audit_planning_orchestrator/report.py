"""Render an orchestrator run (summary.json + log.jsonl) as a standalone HTML report.

    # Render the most recent run:
    python -m tools.scripts.audit_planning_orchestrator.report

    # Render a specific run:
    python -m tools.scripts.audit_planning_orchestrator.report --run accounts-payable-20260908-134436

Writes ``report.html`` into the run directory. The file is self-contained
(inline CSS, no external requests) so it opens straight from disk in any browser.
"""

import argparse
import html
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("report")

RUNS_DIR = Path(__file__).parent / "runs"

_RATING_CLASS = {"High": "r-high", "Medium": "r-med", "Low": "r-low"}


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _pill(rating: Optional[str]) -> str:
    cls = _RATING_CLASS.get(rating or "", "r-none")
    return f'<span class="pill {cls}">{_esc(rating or "-")}</span>'


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_run(run_dir: Path) -> Dict[str, Any]:
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    log: List[Dict[str, Any]] = []
    log_path = run_dir / "log.jsonl"
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                log.append(json.loads(line))
    return {"summary": summary, "log": log}


def latest_run() -> Optional[Path]:
    if not RUNS_DIR.exists():
        return None
    runs = [p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "summary.json").exists()]
    return max(runs, key=lambda p: p.stat().st_mtime) if runs else None


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_TOOL_LABELS = {
    "run_rcm_builder": "UC7 · RCM Builder",
    "run_work_program": "UC8 · Work Program",
    "run_quality_guard": "UC9 · Quality &amp; Resource Guard",
}


def _render_timeline(log: List[Dict[str, Any]]) -> str:
    items: List[str] = []
    for rec in log:
        event = rec.get("event")
        if event == "run_start":
            items.append(_timeline_item("start", "Run started", _esc(rec.get("engagement", "")), rec.get("at")))
        elif event == "orchestrator":
            items.append(_timeline_item("think", "Orchestrator", _esc(rec.get("reasoning", "")), rec.get("at")))
        elif event == "tool_call":
            tool = rec.get("tool", "")
            label = _TOOL_LABELS.get(tool, _esc(tool))
            status = rec.get("status", "")
            body = []
            if tool == "run_quality_guard" and rec.get("verdict"):
                body.append(_verdict_badge(rec["verdict"]))
                for gap in rec.get("gaps", []) or []:
                    body.append(f'<div class="gap">{_esc(gap)}</div>')
            if rec.get("errors"):
                for err in rec["errors"]:
                    body.append(f'<div class="gap err">{_esc(err)}</div>')
            if rec.get("artifact"):
                body.append(f'<div class="artifact">→ {_esc(rec["artifact"])}</div>')
            kind = "error" if status == "error" else "tool"
            items.append(_timeline_item(kind, label, "".join(body), rec.get("at"), status=status))
        elif event == "run_end":
            items.append(_timeline_item("end", "Run ended", _verdict_badge(rec.get("final_verdict")), rec.get("at")))
    return "\n".join(items)


def _timeline_item(kind: str, title: str, body: str, at: Optional[str], status: str = "") -> str:
    when = _esc((at or "")[11:19]) if at else ""
    status_html = f'<span class="status s-{_esc(status)}">{_esc(status)}</span>' if status else ""
    return (
        f'<li class="tl {kind}">'
        f'<div class="tl-dot"></div>'
        f'<div class="tl-body"><div class="tl-head"><span class="tl-title">{title}</span>'
        f'{status_html}<span class="tl-time">{when}</span></div>'
        f'<div class="tl-text">{body}</div></div></li>'
    )


def _verdict_badge(verdict: Optional[str]) -> str:
    cls = "go" if verdict == "Go" else "nogo"
    return f'<span class="verdict {cls}">{_esc(verdict or "-")}</span>'


def _render_rcm(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "<p class='muted'>No RCM rows.</p>"
    body = []
    for r in rows:
        inh = r.get("inherent_risk", {})
        res = r.get("residual_risk", {})
        control = r.get("control_description") or '<span class="muted">— no control (gap)</span>'
        body.append(
            "<tr>"
            f"<td class='mono'>{_esc(r.get('risk_id'))}</td>"
            f"<td>{_esc(r.get('sub_process'))}</td>"
            f"<td>{_esc(r.get('risk_description'))}</td>"
            f"<td>{_pill(inh.get('rating'))}</td>"
            f"<td>{control}<div class='sub'>{_esc(r.get('control_type') or '')}</div></td>"
            f"<td>{_pill(res.get('rating'))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Risk</th><th>Sub-process</th><th>Description</th>"
        "<th>Inherent</th><th>Control</th><th>Residual</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _render_work_program(tasks: List[Dict[str, Any]]) -> str:
    if not tasks:
        return "<p class='muted'>No work program tasks.</p>"
    body = []
    for t in tasks:
        body.append(
            "<tr>"
            f"<td class='mono'>{_esc(t.get('task_id'))}</td>"
            f"<td class='mono'>{_esc(t.get('control_id'))}</td>"
            f"<td>{_esc(t.get('test_type'))}</td>"
            f"<td>{_esc(t.get('objective'))}<div class='sub'>{_esc(t.get('methodology') or '')}</div></td>"
            f"<td>{_esc(t.get('assigned_to'))}</td>"
            f"<td class='num'>{_esc(t.get('estimated_hours'))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Task</th><th>Control</th><th>Type</th>"
        "<th>Objective</th><th>Assigned</th><th>Hrs</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _render_resources(report: Dict[str, Any]) -> str:
    if not report:
        return ""
    required = report.get("total_hours_required") or 0
    available = report.get("available_hours") or 0
    pct = min(100, round(100 * required / available)) if available else 0
    over = required > available
    alert = report.get("resource_alert")
    alert_html = f"<div class='gap'>{_esc(alert)}</div>" if alert else ""
    return (
        "<section><h2>Resources</h2>"
        f"<div class='res'><div class='res-bar'><div class='res-fill {'over' if over else ''}' "
        f"style='width:{pct}%'></div></div>"
        f"<div class='res-num'>{_esc(required)} h required / {_esc(available)} h available</div></div>"
        f"{alert_html}</section>"
    )


def render_html(data: Dict[str, Any]) -> str:
    s = data["summary"]
    verdict = s.get("final_verdict")
    gaps = s.get("outstanding_gaps") or []
    gaps_html = ""
    if gaps:
        items = "".join(f"<li>{_esc(g)}</li>" for g in gaps)
        gaps_html = f"<section class='gaps-box'><h2>Outstanding gaps</h2><ul>{items}</ul></section>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audit Planning Run — {_esc(s.get('engagement'))}</title>
<style>
:root {{ --bg:#f6f7f9; --card:#fff; --ink:#1b1f24; --muted:#6b7280; --line:#e5e7eb;
  --go:#0f9d58; --nogo:#d93025; --accent:#2b5cff; --high:#d93025; --med:#e8890c; --low:#0f9d58; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
.wrap {{ max-width:960px; margin:0 auto; padding:32px 20px 64px; }}
header.top {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:22px 24px; margin-bottom:24px; }}
.crumb {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }}
h1 {{ margin:6px 0 14px; font-size:24px; }}
h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:0 0 12px; }}
.meta {{ display:flex; flex-wrap:wrap; gap:20px; align-items:center; }}
.verdict {{ font-weight:700; padding:5px 12px; border-radius:999px; color:#fff; font-size:13px; }}
.verdict.go {{ background:var(--go); }} .verdict.nogo {{ background:var(--nogo); }}
.kv {{ font-size:13px; color:var(--muted); }} .kv b {{ color:var(--ink); font-weight:600; }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:20px 24px; margin-bottom:20px; }}
.gaps-box {{ border-color:#f3c2bd; background:#fdf3f2; }}
.gaps-box ul {{ margin:0; padding-left:18px; }} .gaps-box li {{ margin:4px 0; }}
ul.timeline {{ list-style:none; margin:0; padding:0; }}
li.tl {{ position:relative; padding:0 0 18px 26px; }}
li.tl:last-child {{ padding-bottom:0; }}
li.tl::before {{ content:""; position:absolute; left:6px; top:14px; bottom:0; width:2px; background:var(--line); }}
li.tl:last-child::before {{ display:none; }}
.tl-dot {{ position:absolute; left:0; top:5px; width:14px; height:14px; border-radius:50%; background:var(--accent); border:2px solid var(--card); }}
li.tl.think .tl-dot {{ background:#9aa5b1; }} li.tl.error .tl-dot {{ background:var(--nogo); }}
li.tl.start .tl-dot {{ background:#111; }} li.tl.end .tl-dot {{ background:var(--go); }}
.tl-head {{ display:flex; align-items:center; gap:10px; }}
.tl-title {{ font-weight:600; }}
.tl-time {{ margin-left:auto; color:var(--muted); font-size:12px; font-variant-numeric:tabular-nums; }}
.tl-text {{ color:#374151; margin-top:2px; }}
.status {{ font-size:11px; padding:1px 7px; border-radius:999px; text-transform:uppercase; letter-spacing:.04em; }}
.status.s-ok {{ background:#e6f4ea; color:var(--go); }} .status.s-error {{ background:#fce8e6; color:var(--nogo); }}
.gap {{ background:#fdf3f2; border:1px solid #f3c2bd; color:#8a2c22; border-radius:8px; padding:6px 10px; margin-top:6px; font-size:13px; }}
.gap.err {{ background:#fff7ed; border-color:#fed7aa; color:#9a3412; }}
.artifact {{ color:var(--muted); font-size:12px; margin-top:6px; font-family:ui-monospace,Menlo,Consolas,monospace; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ text-align:left; color:var(--muted); font-weight:600; border-bottom:2px solid var(--line); padding:8px 10px; }}
td {{ border-bottom:1px solid var(--line); padding:9px 10px; vertical-align:top; }}
.mono {{ font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12px; white-space:nowrap; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.sub {{ color:var(--muted); font-size:12px; margin-top:2px; }}
.pill {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:12px; font-weight:600; color:#fff; }}
.pill.r-high {{ background:var(--high); }} .pill.r-med {{ background:var(--med); }}
.pill.r-low {{ background:var(--low); }} .pill.r-none {{ background:#9aa5b1; }}
.muted {{ color:var(--muted); }}
.res-bar {{ height:14px; background:#eef1f4; border-radius:8px; overflow:hidden; }}
.res-fill {{ height:100%; background:var(--go); }} .res-fill.over {{ background:var(--nogo); }}
.res-num {{ margin-top:6px; color:var(--muted); font-size:13px; }}
.foot {{ color:var(--muted); font-size:12px; text-align:center; margin-top:8px; }}
</style></head>
<body><div class="wrap">
<header class="top">
  <div class="crumb">Audit Planning Orchestrator · UC7 → UC8 → UC9</div>
  <h1>{_esc(s.get('engagement'))}</h1>
  <div class="meta">
    {_verdict_badge(verdict)}
    <span class="kv">Run <b>{_esc(s.get('run_id'))}</b></span>
    <span class="kv">Correction cycles <b>{_esc(s.get('cycles'))}</b></span>
    <span class="kv">Risks <b>{len(s.get('rcm') or [])}</b></span>
    <span class="kv">Tasks <b>{len(s.get('work_program') or [])}</b></span>
  </div>
</header>
{gaps_html}
<section><h2>Pipeline run</h2><ul class="timeline">{_render_timeline(data['log'])}</ul></section>
<section><h2>Risk &amp; Control Matrix</h2>{_render_rcm(s.get('rcm') or [])}</section>
<section><h2>Work Program</h2>{_render_work_program(s.get('work_program') or [])}</section>
{_render_resources(s.get('resource_report') or {})}
<div class="foot">Generated from summary.json + log.jsonl · synthetic planning data</div>
</div></body></html>"""


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render an orchestrator run as an HTML report.")
    parser.add_argument("--run", help="Run id or path (default: most recent run).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if args.run:
        run_dir = Path(args.run)
        if not run_dir.exists():
            run_dir = RUNS_DIR / args.run
    else:
        run_dir = latest_run()

    if not run_dir or not (run_dir / "summary.json").exists():
        logger.error("No run found. Run the orchestrator first (e.g. --simulate).")
        return 2

    data = load_run(run_dir)
    out = run_dir / "report.html"
    out.write_text(render_html(data), encoding="utf-8")
    logger.info("Report written: %s", out)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
