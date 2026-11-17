import anthropic
import json
from typing import Optional

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an expert internal auditor with deep experience in Operational and IT audits.
Your task is to generate professional, structured audit report content based on the inputs provided.
Always respond with valid JSON matching the exact structure requested.
Be thorough, professional, and use formal audit language appropriate for the report type."""

def generate_report_content(
    audit_type: str,
    auditee_name: str,
    audit_period: str,
    auditor_name: str,
    scope: str,
    objectives: str,
    methodology: str,
    free_text_notes: Optional[str],
    structured_data_summary: Optional[str],
    form_data: Optional[dict],
    template_placeholders: list[str],
) -> dict:
    """Call Claude to generate audit report content for each detected placeholder."""

    inputs_summary = _build_inputs_summary(
        audit_type, auditee_name, audit_period, auditor_name,
        scope, objectives, methodology, free_text_notes,
        structured_data_summary, form_data
    )

    placeholder_list = "\n".join(f'- "{p}"' for p in template_placeholders)

    prompt = f"""Based on the following audit information, generate content for each placeholder found in the Word template.

## Audit Information
{inputs_summary}

## Placeholders to fill
The Word template contains these placeholders. Generate appropriate content for each one:
{placeholder_list}

## Instructions
- For findings, format as a numbered list with: Finding title, Observation, Risk/Impact, Recommendation
- For executive summary, write 2-3 concise paragraphs
- For conclusion, write 1-2 paragraphs
- Keep all content professional and formal
- If a placeholder is not relevant to the audit type, write "N/A"

Respond ONLY with a JSON object where keys are the placeholder names (without {{ }}) and values are the content strings.
Example: {{"EXECUTIVE_SUMMARY": "...", "FINDINGS": "..."}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)


def _build_inputs_summary(
    audit_type, auditee_name, audit_period, auditor_name,
    scope, objectives, methodology, free_text_notes,
    structured_data_summary, form_data
) -> str:
    parts = [
        f"**Audit Type**: {audit_type}",
        f"**Auditee / Organization**: {auditee_name}",
        f"**Audit Period**: {audit_period}",
        f"**Lead Auditor**: {auditor_name}",
        f"**Scope**: {scope}",
        f"**Objectives**: {objectives}",
        f"**Methodology**: {methodology}",
    ]
    if free_text_notes:
        parts.append(f"**Auditor Notes / Observations**:\n{free_text_notes}")
    if structured_data_summary:
        parts.append(f"**Structured Data Summary (from uploaded file)**:\n{structured_data_summary}")
    if form_data:
        findings_text = "\n".join(
            f"  Finding {i+1}: {f.get('title','')}\n  Observation: {f.get('observation','')}\n  Risk: {f.get('risk','')}\n  Recommendation: {f.get('recommendation','')}"
            for i, f in enumerate(form_data.get("findings", []))
        )
        if findings_text:
            parts.append(f"**Findings from Form**:\n{findings_text}")
    return "\n".join(parts)
