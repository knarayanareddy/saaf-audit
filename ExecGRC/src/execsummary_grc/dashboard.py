from __future__ import annotations

from html import escape
from pathlib import Path

from .models import AnalysisResult
from .reports import (
    _html_document,
    _impact_by_process,
    _kpi,
    _process_effectiveness,
    _risk_matrix,
    _trend_chart,
    _trend_by_process,
)


def write_dashboard(output_dir: Path, analysis: AnalysisResult, run_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    html = _render_dashboard(analysis, run_id)
    path = output_dir / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path


def _render_dashboard(analysis: AnalysisResult, run_id: str) -> str:
    metrics = analysis.metrics
    return _html_document(
        title=f"GRC Reporting Dashboard - {run_id}",
        body=f"""
<header class="page-header">
  <div>
    <p class="eyebrow">Auditable GRC reporting run</p>
    <h1>GRC Reporting Dashboard</h1>
    <p class="subtitle">Run {escape(run_id)} - posture: {escape(analysis.posture)}</p>
  </div>
  <nav class="links">
    <a href="tactical_report.html">Tactical</a>
    <a href="executive_report.html">Executive</a>
    <a href="audit_summary.md">Audit</a>
    <a href="manifest.json">Manifest</a>
  </nav>
</header>
<main>
  <section class="kpi-grid" aria-label="Key metrics">
    {_kpi("Controls", metrics.get("total_controls", 0), "Loaded controls")}
    {_kpi("Weak controls", metrics.get("weak_controls", 0), "Ineffective or partially effective")}
    {_kpi("Risks", metrics.get("total_risks", 0), "Loaded risks")}
    {_kpi("High risks", metrics.get("high_risks", 0), "At or above configured threshold")}
    {_kpi("Critical risks", metrics.get("critical_risks", 0), "At or above critical threshold")}
    {_kpi("Findings", len(analysis.findings), "Generated report findings")}
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <div class="section-heading">
        <h2>Risk Matrix</h2>
        <p>Risk count by impact and likelihood.</p>
      </div>
      {_risk_matrix(metrics.get("risk_matrix", []))}
    </div>
    <div class="panel">
      <div class="section-heading">
        <h2>Strategic Impact by Process</h2>
        <p>Exposure index highlights where residual risk and weak controls combine.</p>
      </div>
      {_impact_by_process(metrics.get("risk_impact_by_process", []))}
    </div>
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <div class="section-heading">
        <h2>Measure Effectiveness</h2>
        <p>Effective versus weak controls by process.</p>
      </div>
      {_process_effectiveness(metrics.get("process_effectiveness", []))}
    </div>
    <div class="panel">
      <div class="section-heading">
        <h2>Trend Analysis</h2>
        <p>Residual risk movement and process-level trend pressure.</p>
      </div>
      {_trend_chart(metrics.get("trend_counts", {}))}
      {_trend_by_process(metrics.get("trend_by_process", []))}
    </div>
  </section>

  <section class="dashboard-grid two">
    <div class="panel">
      <h2>Theme Overview</h2>
      {_theme_table(analysis)}
    </div>
    <div class="panel">
      <h2>Findings Snapshot</h2>
      {_finding_table(analysis)}
    </div>
  </section>
</main>
""",
    )


def _theme_table(analysis: AnalysisResult) -> str:
    rows = []
    for theme in analysis.themes:
        rows.append(
            "<tr>"
            f"<td>{escape(str(theme['theme']))}</td>"
            f"<td>{theme['high_risks']}</td>"
            f"<td>{theme['weak_controls']}</td>"
            f"<td>{theme['max_score']:g}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>Theme</th><th>High risks</th><th>Weak controls</th><th>Max score</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _finding_table(analysis: AnalysisResult) -> str:
    rows = []
    for finding in analysis.findings[:8]:
        rows.append(
            "<tr>"
            f"<td>{escape(finding.finding_id)}</td>"
            f"<td>{escape(finding.severity)}</td>"
            f"<td>{escape(finding.confidence)}</td>"
            f"<td>{escape(finding.theme)}</td>"
            f"<td>{escape(finding.title)}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>ID</th><th>Severity</th><th>Confidence</th><th>Theme</th><th>Finding</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )
