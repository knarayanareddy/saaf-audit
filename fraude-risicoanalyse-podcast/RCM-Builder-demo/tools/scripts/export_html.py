import argparse
import html
import json
from pathlib import Path


def get_risk_color(score: float) -> str:
    if score <= 9:
        return '#27ae60'
    if score <= 15:
        return '#f39c12'
    return '#e74c3c'


def get_control_color(reliability: str) -> str:
    mapping = {
        'Reliable': '#27ae60',
        'Partially Reliable': '#f39c12',
        'Unreliable': '#e74c3c',
        'Not Assessed': '#95a5a6',
    }
    return mapping.get(reliability, '#95a5a6')


def render_cell(value: object, color: str | None = None) -> str:
    style = 'font-size:11px;vertical-align:top;'
    if color:
        style += f'background-color:{color};color:white;font-weight:bold;'
    return f'<td style="{style}">{html.escape(str(value))}</td>'


def build_table_html(rcm_data: dict) -> str:
    headers = [
        'Risk ID',
        'Objective ID',
        'Sub-Process',
        'Process',
        'Objective',
        'Risk Sources',
        'Source References',
        'Risk Statement',
        'Category',
        'Impact',
        'Likelihood',
        'Inherent Risk',
        'Inherent Rating',
        'Control ID',
        'Control Description',
        'Control Owner',
        'Frequency',
        'Evidence Type',
        'Exec Type',
        'Nature',
        'Significance',
        'Design Effectiveness',
        'Design Gap',
        'System',
        'Report',
        'ITGC Dependency',
        'IPE Validation',
        'Control Reliability',
        'Additional ITGC Control',
        'Final Residual Risk',
        'Final Rating',
        'Residual Change',
        'New UC6 Risk',
        'Source Use Cases',
    ]

    thead = ''.join(
        f'<th style="background-color:#2c3e50;color:white;">{html.escape(header)}</th>'
        for header in headers
    )

    body_rows: list[str] = []
    for risk in rcm_data.get('risks', []):
        stage1 = risk.get('stage1', {})
        stage2 = risk.get('stage2', {})
        stage3 = risk.get('stage3', {})
        assessments = {
            assessment.get('control_id'): assessment
            for assessment in stage3.get('controls_it_assessment', [])
        }

        for control in stage2.get('controls', []):
            assessment = assessments.get(control.get('control_id'), {})
            inherent_score = stage2.get('inherent_risk_score', '')
            final_score = stage3.get('final_residual_risk', stage2.get('preliminary_residual_risk', ''))
            reliability = assessment.get('control_reliability', 'Not Assessed')

            row = ''.join([
                render_cell(risk.get('risk_id', '')),
                render_cell(stage1.get('objective_id', '')),
                render_cell(stage1.get('sub_process_name', 'N/A')),
                render_cell(stage1.get('process_name', '')),
                render_cell(stage1.get('objective', '')),
                render_cell(', '.join(stage1.get('risk_sources', []))),
                render_cell(', '.join(stage1.get('source_references', []))),
                render_cell(stage1.get('risk_statement', '')),
                render_cell(stage1.get('risk_category', '')),
                render_cell(stage2.get('inherent_impact', '')),
                render_cell(stage2.get('inherent_likelihood', '')),
                render_cell(inherent_score, get_risk_color(float(inherent_score)) if inherent_score != '' else None),
                render_cell(stage2.get('inherent_risk_rating', '')),
                render_cell(control.get('control_id', '')),
                render_cell(control.get('description', '')),
                render_cell(control.get('control_owner', '')),
                render_cell(control.get('frequency', '')),
                render_cell(control.get('evidence_type', '')),
                render_cell(control.get('execution_type', '')),
                render_cell(control.get('nature', '')),
                render_cell(control.get('significance', '')),
                render_cell(control.get('control_design_effectiveness', '')),
                render_cell(stage2.get('design_gap_type', '')),
                render_cell(assessment.get('system_name', '')),
                render_cell(assessment.get('report_name', '')),
                render_cell(', '.join(assessment.get('itgc_dependency_type', []))),
                render_cell(assessment.get('ipe_validation_level', 'N/A')),
                render_cell(reliability, get_control_color(reliability)),
                render_cell(assessment.get('itgc_control_description', '')),
                render_cell(final_score, get_risk_color(float(final_score)) if final_score != '' else None),
                render_cell(stage3.get('final_residual_rating', stage2.get('preliminary_residual_rating', ''))),
                render_cell(stage3.get('residual_risk_change', 0.0)),
                render_cell(stage3.get('new_risk_description', '')),
                render_cell(', '.join(stage1.get('source_use_cases', []))),
            ])
            body_rows.append(f'<tr>{row}</tr>')

    return f'<table><thead><tr>{thead}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'


def main() -> None:
    parser = argparse.ArgumentParser(description='Export RCM JSON to styled HTML')
    parser.add_argument('--input-json', default='outputs/rcm_output.json', help='Input RCM JSON path')
    parser.add_argument('--output-html', default='outputs/rcm_output.html', help='Output HTML path')
    parser.add_argument('--title', default='Risk Control Matrix', help='HTML title')
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_path = Path(args.output_html)
    rcm_data = json.loads(input_path.read_text())
    html_table = build_table_html(rcm_data)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{args.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 32px; background-color: #f5f6fa; }}
        h1 {{ color: #2c3e50; }}
        .legend {{ margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .legend span {{ display: inline-block; padding: 5px 15px; margin-right: 12px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px; }}
        .table-wrap {{ overflow-x: auto; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 8px; }}
        table {{ border-collapse: collapse; width: 100%; min-width: 1800px; }}
        th, td {{ border: 1px solid #e0e0e0; padding: 10px; text-align: left; }}
        th {{ background-color: #2c3e50; color: white; font-weight: bold; position: sticky; top: 0; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:hover {{ background-color: #e8f4f8; }}
    </style>
</head>
<body>
    <h1>{args.title}</h1>
    <div class="legend">
        <strong>Risk Score:</strong>
        <span style="background-color:#27ae60;">Low (1-9)</span>
        <span style="background-color:#f39c12;">Medium (10-15)</span>
        <span style="background-color:#e74c3c;">High (16-25)</span>
        <br><br>
        <strong>Control Reliability:</strong>
        <span style="background-color:#27ae60;">Reliable</span>
        <span style="background-color:#f39c12;">Partially Reliable</span>
        <span style="background-color:#e74c3c;">Unreliable</span>
        <span style="background-color:#95a5a6;">Not Assessed</span>
    </div>
    <div class="table-wrap">
        {html_table}
    </div>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f'HTML written to: {output_path}')


if __name__ == '__main__':
    main()
