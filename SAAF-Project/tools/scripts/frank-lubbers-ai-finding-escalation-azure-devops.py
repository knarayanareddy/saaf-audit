"""
AI Finding Escalation Agent — pushes OWASP & hallucination findings to Azure DevOps.

Usage:
    python tools/scripts/frank-lubbers-ai-finding-escalation-azure-devops.py \
        --findings findings.json \
        --org-url https://dev.azure.com/your-org \
        --project your-project \
        --source owasp|hallucination

Environment variables required:
    ANTHROPIC_API_KEY   — Claude API key
    AZURE_DEVOPS_PAT    — Azure DevOps Personal Access Token
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

RISK_TO_PRIORITY = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Informational": 4,
}

WORK_ITEM_TYPE = {
    "owasp": "Issue",
    "hallucination": "Task",
}

SYSTEM_PROMPT = """You are an AI audit finding escalation specialist.
Your role is to classify audit findings from AI governance checks and prepare them for entry into Azure DevOps.
Always preserve the original finding ID, observation, and recommendation in the work item description.
Never omit a finding — if a work item cannot be created, log it as a failed escalation with the reason.
Return only valid JSON. No extra text."""

USER_PROMPT_TEMPLATE = """Classify this audit finding for escalation to Azure DevOps as a {work_item_type}.
Return a JSON object with these fields:
- "title": concise work item title (max 100 chars)
- "description": one paragraph for the engineering team explaining what was found and what to do
- "priority": integer 1-4 (1=Critical, 2=High, 3=Medium, 4=Low)

Finding:
{finding}"""


def enrich_finding(
    finding: dict,
    work_item_type: str,
    client: anthropic.Anthropic,
) -> dict:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                work_item_type=work_item_type,
                finding=json.dumps(finding, indent=2),
            ),
        }],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def create_work_item(
    org_url: str,
    project: str,
    pat: str,
    title: str,
    description: str,
    priority: int,
    work_item_type: str,
    finding_id: str,
) -> Optional[dict]:
    try:
        from azure.devops.connection import Connection
        from msrest.authentication import BasicAuthentication
    except ImportError:
        log.error("azure-devops package not installed. Run: pip install azure-devops")
        return None

    credentials = BasicAuthentication("", pat)
    connection = Connection(base_url=org_url, creds=credentials)
    wit_client = connection.clients.get_work_item_tracking_client()

    document = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description",
         "value": f"<b>SAAF Finding ID:</b> {finding_id}<br><br>{description}"},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": priority},
    ]

    work_item = wit_client.create_work_item(document, project, work_item_type)
    return {
        "id": work_item.id,
        "url": work_item.url.replace("_apis/wit/workItems", "_workitems/edit"),
    }


def escalate(
    findings: list[dict],
    source: str,
    org_url: str,
    project: str,
    pat: str,
    client: anthropic.Anthropic,
) -> dict:
    work_item_type = WORK_ITEM_TYPE[source]
    results = []
    created = 0
    failed = 0

    for finding in findings:
        finding_id = finding.get("id", "unknown")
        log.info("Processing finding %s ...", finding_id)

        try:
            enriched = enrich_finding(finding, work_item_type, client)
            priority = enriched.get("priority") or RISK_TO_PRIORITY.get(finding.get("risk_rating", "Low"), 3)

            item = create_work_item(
                org_url=org_url,
                project=project,
                pat=pat,
                title=enriched["title"],
                description=enriched["description"],
                priority=priority,
                work_item_type=work_item_type,
                finding_id=finding_id,
            )

            if item:
                results.append({
                    "finding_id": finding_id,
                    "source_agent": f"llm-{source}-agent",
                    "work_item_type": work_item_type,
                    "azure_devops_work_item_id": item["id"],
                    "url": item["url"],
                    "priority": priority,
                    "escalation_status": "created",
                })
                created += 1
                log.info("Created %s #%s: %s", work_item_type, item["id"], item["url"])
            else:
                raise RuntimeError("Work item creation returned None")

        except Exception as exc:
            log.warning("Failed to escalate %s: %s", finding_id, exc)
            results.append({
                "finding_id": finding_id,
                "source_agent": f"llm-{source}-agent",
                "work_item_type": work_item_type,
                "escalation_status": "failed",
                "error": str(exc),
            })
            failed += 1

    return {
        "push_report": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "total_findings": len(findings),
            "created": created,
            "failed": failed,
        },
        "work_items": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Escalate SAAF findings to Azure DevOps")
    parser.add_argument("--findings", required=True, help="Path to JSON file with findings array")
    parser.add_argument("--org-url", required=True, help="Azure DevOps org URL (https://dev.azure.com/your-org)")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--source", required=True, choices=["owasp", "hallucination"],
                        help="Source agent type")
    parser.add_argument("--output", help="Write push report to this file (default: stdout)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify findings with Claude but skip Azure DevOps creation")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat and not args.dry_run:
        log.error("AZURE_DEVOPS_PAT environment variable not set")
        sys.exit(1)

    findings_path = Path(args.findings)
    if not findings_path.exists():
        log.error("Findings file not found: %s", findings_path)
        sys.exit(1)

    findings = json.loads(findings_path.read_text(encoding="utf-8"))
    if isinstance(findings, dict) and "findings" in findings:
        findings = findings["findings"]

    log.info("Loaded %d findings from %s", len(findings), findings_path)

    client = anthropic.Anthropic(api_key=api_key)

    if args.dry_run:
        log.info("Dry run — classifying findings without creating work items")
        work_item_type = WORK_ITEM_TYPE[args.source]
        for finding in findings:
            enriched = enrich_finding(finding, work_item_type, client)
            print(json.dumps({"finding_id": finding.get("id"), "enriched": enriched}, indent=2))
        return

    report = escalate(
        findings=findings,
        source=args.source,
        org_url=args.org_url,
        project=args.project,
        pat=pat,
        client=client,
    )

    output = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        log.info("Push report written to %s", args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()
