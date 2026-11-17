from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from .config import Settings
from .models import AnalysisResult, Dataset, Finding


SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def write_reports(
    output_dir: Path,
    dataset: Dataset,
    analysis: AnalysisResult,
    settings: Settings,
    profile: dict[str, Any],
    run_id: str,
    feedback: str = "",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tactical_path = output_dir / "tactical_report.html"
    executive_path = output_dir / "executive_report.html"
    analysis_path = output_dir / "analysis_result.json"

    tactical_path.write_text(
        _render_tactical_dashboard(dataset, analysis, settings, profile, run_id, feedback),
        encoding="utf-8",
    )
    executive_path.write_text(
        _render_executive_dashboard(analysis, settings, profile, run_id, feedback),
        encoding="utf-8",
    )
    analysis_path.write_text(json.dumps(analysis.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    return {
        "tactical_report": tactical_path,
        "executive_report": executive_path,
        "analysis_result": analysis_path,
    }


def _render_tactical_dashboard(
    dataset: Dataset,
    analysis: AnalysisResult,
    settings: Settings,
    profile: dict[str, Any],
    run_id: str,
    feedback: str,
) -> str:
    metrics = analysis.metrics
    source_files = _source_file_list(metrics.get("source_files", []))
    feedback_panel = (
        f'<section class="panel"><h2>Manager Context</h2><p>{escape(feedback)}</p></section>' if feedback else ""
    )

    return _html_document(
        title=f"Tactical GRC Dashboard - {run_id}",
        body=f"""
<header class="page-header">
  <div>
    <p class="eyebrow">Tactical risk and control analysis</p>
    <h1>Tactical GRC Dashboard</h1>
    <p class="subtitle">Run {escape(run_id)} - {escape(profile.get("name", "Default"))} - {_approval_status(settings)}</p>
  </div>
  <nav class="links">
    <a href="dashboard.html">Overview</a>
    <a href="executive_report.html">Executive</a>
    <a href="audit_summary.md">Audit</a>
  </nav>
</header>
<main>
  <section class="kpi-grid" aria-label="Tactical indicators">
    {_kpi("Posture", analysis.posture, "Overall residual risk posture")}
    {_kpi("Weak controls", metrics.get("weak_controls", 0), "Controls requiring remediation")}
    {_kpi("High risks", metrics.get("high_risks", 0), "Residual score above threshold")}
    {_kpi("Direct correlations", metrics.get("direct_correlations", 0), "High risks mapped to weak controls")}
    {_kpi("Increasing risks", metrics.get("increasing_risks", 0), "Risks with upward trend")}
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <div class="section-heading">
        <h2>Risk Matrix</h2>
        <p>Risk count by residual impact and likelihood.</p>
      </div>
      {_risk_matrix(metrics.get("risk_matrix", []))}
    </div>
    <div class="panel">
      <div class="section-heading">
        <h2>Process Control Effectiveness</h2>
        <p>Effective versus weak measures per process.</p>
      </div>
      {_process_effectiveness(metrics.get("process_effectiveness", []))}
    </div>
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <div class="section-heading">
        <h2>Trend Analysis</h2>
        <p>Direction of residual risk movement in the uploaded dataset.</p>
      </div>
      {_trend_chart(metrics.get("trend_counts", {}))}
    </div>
    <div class="panel">
      <div class="section-heading">
        <h2>Trend by Process</h2>
        <p>Where increasing risks and high exposure overlap.</p>
      </div>
      {_trend_by_process(metrics.get("trend_by_process", []))}
    </div>
  </section>

  <section class="panel">
    <div class="section-heading">
      <h2>Correlation Deep Dive</h2>
      <p>Detailed findings, supporting evidence and concrete improvement measures.</p>
    </div>
    {_finding_cards(analysis.findings)}
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <h2>Data Quality Notes</h2>
      {_bullet_list(analysis.data_quality)}
    </div>
    <div class="panel">
      <h2>Source and Audit Context</h2>
      {source_files}
      <p class="callout">Trace every conclusion through <code>analysis_result.json</code>, <code>audit_trail.ndjson</code> and <code>manifest.json</code>.</p>
    </div>
  </section>

  {feedback_panel}
</main>
""",
    )


def _render_executive_dashboard(
    analysis: AnalysisResult,
    settings: Settings,
    profile: dict[str, Any],
    run_id: str,
    feedback: str,
) -> str:
    metrics = analysis.metrics
    insights = _executive_insights(analysis)
    frameworks = ", ".join(profile.get("frameworks", [])) or "Not specified"
    feedback_note = f'<p class="callout">Management context: {escape(feedback)}</p>' if feedback else ""

    return _html_document(
        title=f"Executive Risk Dashboard - {run_id}",
        body=f"""
<header class="page-header">
  <div>
    <p class="eyebrow">Board-level risk decision support</p>
    <h1>Executive Risk Dashboard</h1>
    <p class="subtitle">Run {escape(run_id)} - {_approval_status(settings)}</p>
  </div>
  <nav class="links">
    <a href="dashboard.html">Overview</a>
    <a href="tactical_report.html">Tactical</a>
    <a href="audit_summary.md">Audit</a>
  </nav>
</header>
<main>
  <section class="kpi-grid" aria-label="Executive indicators">
    {_kpi("Posture", analysis.posture, "Management attention level")}
    {_kpi("Critical risks", metrics.get("critical_risks", 0), "Direct decision pressure")}
    {_kpi("High risks", metrics.get("high_risks", 0), "Above risk threshold")}
    {_kpi("Weak controls", metrics.get("weak_controls", 0), "Control reliability pressure")}
    {_kpi("Increasing risks", metrics.get("increasing_risks", 0), "Trend pressure")}
  </section>

  <section class="dashboard-grid two">
    <div class="panel impact-panel">
      <div class="section-heading">
        <h2>Strategic Risk Impact</h2>
        <p>Exposure index combines residual score and weak-control pressure.</p>
      </div>
      {_impact_by_process(metrics.get("risk_impact_by_process", []))}
    </div>
    <div class="panel">
      <div class="section-heading">
        <h2>Executive Risk Matrix</h2>
        <p>Where risks cluster by impact and likelihood.</p>
      </div>
      {_risk_matrix(metrics.get("risk_matrix", []))}
    </div>
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <div class="section-heading">
        <h2>Strategic Insights</h2>
        <p>What the board should take away from this run.</p>
      </div>
      {_insight_cards(insights)}
    </div>
    <div class="panel">
      <div class="section-heading">
        <h2>Trend Pressure</h2>
        <p>Directional signal for escalation and monitoring cadence.</p>
      </div>
      {_trend_chart(metrics.get("trend_counts", {}))}
      {_trend_by_process(metrics.get("trend_by_process", []))}
    </div>
  </section>

  <section class="panel">
    <div class="section-heading">
      <h2>Decision Agenda</h2>
      <p>Prioritized decisions, evidence and recommended management action.</p>
    </div>
    {_decision_table(analysis.findings)}
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <h2>Assurance and Limitations</h2>
      <ul class="clean-list">
        <li>Framework context: {escape(frameworks)}.</li>
        <li>The analysis uses uploaded data only and does not modify source records.</li>
        <li>Outputs remain draft until reviewed by a human approver.</li>
        <li>Material conclusions are traceable through the audit trail and artifact manifest.</li>
      </ul>
      {feedback_note}
    </div>
    <div class="panel">
      <h2>Recommended Governance Response</h2>
      {_governance_response(analysis)}
    </div>
  </section>
</main>
""",
    )


def _html_document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f4f6f8;
      --surface: #ffffff;
      --surface-soft: #f9fafb;
      --text: #17202a;
      --muted: #607080;
      --border: #d8e0e8;
      --accent: #2367a2;
      --accent-2: #6f4bb8;
      --green: #23834f;
      --amber: #b76e00;
      --red: #c83737;
      --blue-soft: #e8f1fa;
      --green-soft: #e8f5ed;
      --amber-soft: #fff3dd;
      --red-soft: #fdebea;
      --purple-soft: #f0ecf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    .page-header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      padding: 28px 34px 22px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
    }}
    main {{ padding: 24px 34px 42px; }}
    h1 {{ margin: 0; font-size: 30px; font-weight: 760; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 18px; font-weight: 730; letter-spacing: 0; }}
    h3 {{ margin: 0; font-size: 15px; font-weight: 720; }}
    p {{ margin: 6px 0 0; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.93em; }}
    .eyebrow {{
      margin: 0 0 4px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 760;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .subtitle {{ color: var(--muted); max-width: 900px; }}
    .links {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
    .links a {{
      color: var(--accent);
      text-decoration: none;
      border: 1px solid var(--border);
      background: var(--surface-soft);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 13px;
      font-weight: 650;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .dashboard-grid {{
      display: grid;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .dashboard-grid.two {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }}
    .panel, .kpi-card, .finding-card, .insight-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      min-width: 0;
    }}
    .panel {{ padding: 18px; }}
    .kpi-card {{ padding: 16px; }}
    .kpi-label {{ color: var(--muted); font-size: 12px; font-weight: 680; text-transform: uppercase; letter-spacing: .05em; }}
    .kpi-value {{ margin-top: 5px; font-size: 28px; font-weight: 780; }}
    .kpi-note {{ color: var(--muted); font-size: 13px; }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      margin-bottom: 14px;
    }}
    .section-heading p {{ color: var(--muted); font-size: 13px; max-width: 480px; }}
    .matrix-wrap {{
      display: grid;
      grid-template-columns: 34px repeat(5, minmax(54px, 1fr));
      gap: 6px;
      align-items: stretch;
    }}
    .matrix-axis {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .matrix-cell {{
      min-height: 62px;
      border: 1px solid var(--border);
      border-radius: 7px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 6px;
      text-align: center;
    }}
    .matrix-cell strong {{ font-size: 22px; line-height: 1; }}
    .matrix-cell span {{ margin-top: 5px; color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }}
    .matrix-low {{ background: var(--green-soft); }}
    .matrix-medium {{ background: var(--amber-soft); }}
    .matrix-high {{ background: #ffe7c2; }}
    .matrix-critical {{ background: var(--red-soft); border-color: #f0b5b5; }}
    .matrix-footer {{
      display: grid;
      grid-template-columns: 34px repeat(5, minmax(54px, 1fr));
      gap: 6px;
      margin-top: 6px;
    }}
    .bar-list {{ display: grid; gap: 12px; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(120px, 1.2fr) minmax(160px, 2.4fr) minmax(48px, .4fr);
      gap: 12px;
      align-items: center;
      font-size: 13px;
    }}
    .track {{
      height: 14px;
      border-radius: 5px;
      overflow: hidden;
      background: #e9eef3;
      border: 1px solid var(--border);
      display: flex;
    }}
    .bar {{ height: 100%; min-width: 2px; }}
    .bar.effective {{ background: var(--green); }}
    .bar.weak {{ background: var(--red); }}
    .bar.high {{ background: var(--amber); }}
    .bar.accent {{ background: var(--accent); }}
    .bar.purple {{ background: var(--accent-2); }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 720; background: var(--surface-soft); }}
    .finding-grid, .insight-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .finding-card, .insight-card {{ padding: 15px; }}
    .meta-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 12px;
      font-weight: 700;
      background: var(--blue-soft);
      color: #174c79;
    }}
    .badge.critical, .badge.high {{ background: var(--red-soft); color: #9a2525; }}
    .badge.medium {{ background: var(--amber-soft); color: #8a5200; }}
    .badge.low {{ background: var(--green-soft); color: #17613a; }}
    .clean-list {{ margin: 10px 0 0; padding-left: 18px; }}
    .clean-list li {{ margin: 6px 0; }}
    .callout {{
      margin-top: 12px;
      padding: 11px 12px;
      border-radius: 7px;
      border: 1px solid var(--border);
      background: var(--surface-soft);
      color: var(--text);
    }}
    .source-list {{ display: grid; gap: 8px; margin-top: 10px; }}
    .source-item {{ padding: 9px 10px; border: 1px solid var(--border); border-radius: 7px; background: var(--surface-soft); font-size: 13px; }}
    @media (max-width: 980px) {{
      .page-header {{ align-items: flex-start; flex-direction: column; }}
      .links {{ justify-content: flex-start; }}
      .dashboard-grid.two {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 680px) {{
      .page-header, main {{ padding-left: 16px; padding-right: 16px; }}
      h1 {{ font-size: 24px; }}
      .bar-row {{ grid-template-columns: 1fr; gap: 5px; }}
      .matrix-wrap, .matrix-footer {{ grid-template-columns: 28px repeat(5, minmax(42px, 1fr)); gap: 4px; }}
      .matrix-cell {{ min-height: 54px; padding: 4px; }}
      .matrix-cell strong {{ font-size: 18px; }}
      .section-heading {{ flex-direction: column; align-items: flex-start; }}
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def _kpi(label: str, value: Any, note: str) -> str:
    return (
        '<div class="kpi-card">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value">{escape(str(value))}</div>'
        f'<div class="kpi-note">{escape(note)}</div>'
        "</div>"
    )


def _risk_matrix(matrix: list[dict[str, Any]]) -> str:
    by_cell = {(int(cell["impact"]), int(cell["likelihood"])): cell for cell in matrix}
    cells: list[str] = ['<div class="matrix-axis">Impact</div>']
    for impact in range(1, 6):
        cells.append(f'<div class="matrix-axis">{impact}</div>')

    for likelihood in range(5, 0, -1):
        cells.append(f'<div class="matrix-axis">{likelihood}</div>')
        for impact in range(1, 6):
            cell = by_cell.get((impact, likelihood), {"count": 0, "risk_ids": [], "max_score": 0})
            count = int(cell.get("count", 0))
            risk_ids = ", ".join(cell.get("risk_ids", []))
            severity = _matrix_severity(impact, likelihood)
            label = risk_ids if risk_ids else "No risks"
            cells.append(
                f'<div class="matrix-cell matrix-{severity}" title="{escape(label)}">'
                f"<strong>{count}</strong><span>{escape(risk_ids or ' ')}</span></div>"
            )

    footer = ['<div class="matrix-axis"></div>'] + [f'<div class="matrix-axis">{value}</div>' for value in range(1, 6)]
    return (
        '<div class="matrix-wrap" aria-label="Risk matrix">'
        + "".join(cells)
        + "</div>"
        + '<div class="matrix-footer" aria-hidden="true">'
        + "".join(footer)
        + "</div>"
        + '<p class="subtitle">Y-axis: likelihood. X-axis: impact. Cells show number of risks and IDs.</p>'
    )


def _process_effectiveness(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No process effectiveness data available.</p>"
    output = ['<div class="bar-list">']
    for row in rows:
        controls = max(int(row.get("controls", 0)), 1)
        effective_pct = round((float(row.get("effective_controls", 0)) / controls) * 100)
        weak_pct = max(0, 100 - effective_pct)
        output.append(
            '<div class="bar-row">'
            f'<div><strong>{escape(str(row.get("process", "Unmapped")))}</strong>'
            f'<div class="kpi-note">{row.get("high_risks", 0)} high risks - avg score {row.get("average_residual_score", 0):g}</div></div>'
            '<div class="track">'
            f'<div class="bar effective" style="width:{effective_pct}%"></div>'
            f'<div class="bar weak" style="width:{weak_pct}%"></div>'
            "</div>"
            f"<div>{effective_pct}%</div>"
            "</div>"
        )
    output.append("</div>")
    return "".join(output)


def _trend_chart(counts: dict[str, int]) -> str:
    if not counts:
        return "<p>No trend data available.</p>"
    max_value = max(counts.values()) or 1
    order = [("Increasing", "weak"), ("Stable", "accent"), ("Decreasing", "effective"), ("Unknown", "purple")]
    rows = ['<div class="bar-list">']
    for label, color_class in order:
        value = int(counts.get(label, 0))
        width = max(3, round((value / max_value) * 100)) if value else 0
        rows.append(
            '<div class="bar-row">'
            f"<div>{escape(label)}</div>"
            f'<div class="track"><div class="bar {color_class}" style="width:{width}%"></div></div>'
            f"<div>{value}</div>"
            "</div>"
        )
    rows.append("</div>")
    return "".join(rows)


def _trend_by_process(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No process trend data available.</p>"
    table_rows = []
    for row in rows[:8]:
        table_rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('process', 'Unmapped')))}</td>"
            f"<td>{row.get('increasing', 0)}</td>"
            f"<td>{row.get('stable', 0)}</td>"
            f"<td>{row.get('decreasing', 0)}</td>"
            f"<td>{row.get('high_risks', 0)}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>Process</th><th>Increasing</th><th>Stable</th><th>Decreasing</th><th>High risks</th></tr></thead>"
        f"<tbody>{''.join(table_rows)}</tbody></table></div>"
    )


def _impact_by_process(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No impact data available.</p>"
    max_value = max(float(row.get("exposure_index", 0)) for row in rows) or 1.0
    output = ['<div class="bar-list">']
    for row in rows[:8]:
        value = float(row.get("exposure_index", 0))
        width = max(3, round((value / max_value) * 100)) if value else 0
        output.append(
            '<div class="bar-row">'
            f'<div><strong>{escape(str(row.get("process", "Unmapped")))}</strong>'
            f'<div class="kpi-note">Max score {row.get("max_residual_score", 0):g} - weak controls {row.get("weak_controls", 0)}</div></div>'
            f'<div class="track"><div class="bar high" style="width:{width}%"></div></div>'
            f"<div>{value:g}</div>"
            "</div>"
        )
    output.append("</div>")
    return "".join(output)


def _finding_cards(findings: list[Finding]) -> str:
    if not findings:
        return "<p>No findings generated.</p>"
    cards = ['<div class="finding-grid">']
    for finding in sorted(findings, key=lambda item: SEVERITY_ORDER.get(item.severity, 0), reverse=True):
        evidence = _bullet_list(finding.evidence)
        measures = _bullet_list(_improvement_measures(finding))
        cards.append(
            '<article class="finding-card">'
            f"<h3>{escape(finding.finding_id)} - {escape(finding.title)}</h3>"
            '<div class="meta-row">'
            f'<span class="badge {escape(finding.severity.lower())}">{escape(finding.severity)}</span>'
            f'<span class="badge">{escape(finding.confidence)} confidence</span>'
            f'<span class="badge">{escape(finding.theme)}</span>'
            "</div>"
            f"<p><strong>Risk:</strong> {escape(finding.risk_id or 'Unmapped')}</p>"
            f"<p><strong>Controls:</strong> {escape(', '.join(finding.control_ids) or 'No weak control mapped')}</p>"
            "<h3>Evidence</h3>"
            f"{evidence}"
            "<h3>Concrete improvement measures</h3>"
            f"{measures}"
            f'<p class="kpi-note">Sources: {escape(", ".join(finding.source_refs))}</p>'
            "</article>"
        )
    cards.append("</div>")
    return "".join(cards)


def _insight_cards(insights: list[dict[str, str]]) -> str:
    cards = ['<div class="insight-grid">']
    for insight in insights:
        cards.append(
            '<article class="insight-card">'
            f"<h3>{escape(insight['title'])}</h3>"
            f"<p>{escape(insight['body'])}</p>"
            f'<p class="callout">{escape(insight["decision"])}</p>'
            "</article>"
        )
    cards.append("</div>")
    return "".join(cards)


def _decision_table(findings: list[Finding]) -> str:
    if not findings:
        return "<p>No decision points generated.</p>"
    rows = []
    for finding in sorted(findings, key=lambda item: SEVERITY_ORDER.get(item.severity, 0), reverse=True)[:8]:
        rows.append(
            "<tr>"
            f"<td>{escape(finding.severity)}</td>"
            f"<td>{escape(finding.theme)}</td>"
            f"<td>{escape(_decision_for_finding(finding))}</td>"
            f"<td>{escape(finding.recommendation)}</td>"
            f"<td>{escape(', '.join(finding.source_refs))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>Priority</th><th>Theme</th><th>Decision</th><th>Recommended action</th><th>Evidence</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _executive_insights(analysis: AnalysisResult) -> list[dict[str, str]]:
    metrics = analysis.metrics
    impact_rows = metrics.get("risk_impact_by_process", [])
    top_process = impact_rows[0] if impact_rows else {"process": "Unmapped", "exposure_index": 0, "weak_controls": 0}
    high_risks = int(metrics.get("high_risks", 0))
    direct = int(metrics.get("direct_correlations", 0))
    direct_ratio = round((direct / max(high_risks, 1)) * 100)
    insights = [
        {
            "title": "Primary exposure concentration",
            "body": (
                f"{top_process.get('process')} has the highest exposure index "
                f"({top_process.get('exposure_index'):g}) and {top_process.get('weak_controls')} weak controls."
            ),
            "decision": "Confirm whether this process requires immediate remediation funding or formal risk acceptance.",
        },
        {
            "title": "Control reliability drives risk posture",
            "body": f"{direct_ratio}% of high risks are directly correlated with weak controls in this dataset.",
            "decision": "Prioritize control remediation before accepting residual risk as structurally unavoidable.",
        },
        {
            "title": "Trend pressure",
            "body": f"{metrics.get('increasing_risks', 0)} risks are trending upward, including high-risk themes where escalation may be needed.",
            "decision": "Set a monitoring cadence and require refreshed evidence for upward-trending risks.",
        },
    ]
    if analysis.posture in {"Critical", "Elevated"}:
        insights.append(
            {
                "title": "Board attention required",
                "body": f"The current posture is {analysis.posture}, based on thresholds and uploaded evidence.",
                "decision": "Table the remediation plan, accountable owners and acceptance boundaries in the next governance forum.",
            }
        )
    return insights


def _governance_response(analysis: AnalysisResult) -> str:
    if analysis.posture == "Critical":
        items = [
            "Escalate critical findings to the risk committee.",
            "Require remediation plans with accountable owners and dated milestones.",
            "Request independent validation for remediated controls before board publication.",
        ]
    elif analysis.posture == "Elevated":
        items = [
            "Approve targeted remediation for high-exposure processes.",
            "Increase management reporting cadence until trend pressure stabilizes.",
            "Review whether risk appetite statements still match residual exposure.",
        ]
    else:
        items = [
            "Maintain standard monitoring cadence.",
            "Close data quality gaps before the next reporting cycle.",
            "Validate that risk-control mappings remain complete.",
        ]
    return _bullet_list(items)


def _improvement_measures(finding: Finding) -> list[str]:
    measures = [finding.recommendation]
    theme = f"{finding.theme} {finding.title}".lower()
    if "access" in theme or "credential" in theme or "identity" in theme:
        measures.extend(
            [
                "Enforce MFA coverage for all privileged and remote access paths.",
                "Complete privileged access recertification and attach evidence to the control record.",
                "Retest failed access controls and update residual risk scoring after remediation.",
            ]
        )
    elif "third" in theme or "vendor" in theme or "supplier" in theme:
        measures.extend(
            [
                "Refresh supplier assurance evidence for critical vendors.",
                "Document exit plans, concentration risk and contractual resilience obligations.",
                "Add quarterly follow-up for overdue vendor remediation actions.",
            ]
        )
    elif "policy" in theme or "exception" in theme:
        measures.extend(
            [
                "Escalate overdue policy exceptions to the control owner.",
                "Define expiry dates and acceptance criteria for each exception.",
                "Report aging exceptions as a recurring management metric.",
            ]
        )
    else:
        measures.extend(
            [
                "Assign an accountable owner and remediation due date.",
                "Define retest evidence before marking the action complete.",
                "Update the risk-control mapping after management validation.",
            ]
        )
    return _unique(measures)


def _decision_for_finding(finding: Finding) -> str:
    if finding.severity == "Critical":
        return "Approve immediate remediation or document explicit risk acceptance."
    if finding.severity == "High":
        return "Prioritize remediation and require management follow-up."
    if finding.confidence == "Low":
        return "Request additional evidence before deciding on treatment."
    return "Track remediation through standard management reporting."


def _source_file_list(source_files: list[dict[str, Any]]) -> str:
    if not source_files:
        return "<p>No source file metadata available.</p>"
    rows = ['<div class="source-list">']
    for source in source_files:
        rows.append(
            '<div class="source-item">'
            f'<strong>{escape(str(source.get("path", "")))}</strong><br>'
            f'{source.get("records_loaded", 0)} records - sha256 <code>{escape(str(source.get("sha256", "")))}</code>'
            "</div>"
        )
    rows.append("</div>")
    return "".join(rows)


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "<p>No items available.</p>"
    return '<ul class="clean-list">' + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _matrix_severity(impact: int, likelihood: int) -> str:
    score = impact * likelihood
    if score >= 20:
        return "critical"
    if score >= 15:
        return "high"
    if score >= 8:
        return "medium"
    return "low"


def _approval_status(settings: Settings) -> str:
    return "Draft - human approval required" if settings.require_human_approval else "Draft - automated approval flag disabled"


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output
