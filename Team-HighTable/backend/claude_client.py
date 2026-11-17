from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List

from models import AnalysisResponse, AnalyzeRequest, SimilarIssue
from teammate_client import _field

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"


class ClaudeAnalyzer:
    """Uses the Anthropic API to analyse audit issues and generate recommendations."""

    def __init__(self, api_key: str, teammate_base_url: str) -> None:
        import anthropic  # type: ignore

        self._client = anthropic.Anthropic(api_key=api_key)
        self._teammate_base_url = teammate_base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _issue_url(self, issue_id: str) -> str:
        # NOTE: The exact hash-route format may need adjustment depending on
        # the TeamMate+ frontend version in use.
        return f"{self._teammate_base_url}/#/issues/{issue_id}"

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Extract and parse JSON from Claude's response, handling ```json fences."""
        # Try to find a ```json ... ``` block first
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fenced:
            return json.loads(fenced.group(1).strip())
        # Fall back to parsing the whole response as JSON
        return json.loads(text.strip())

    def _build_prompt(
        self,
        current_issue: AnalyzeRequest,
        similar_issues: List[Dict[str, Any]],
    ) -> str:
        similar_summaries: List[str] = []
        for i, issue in enumerate(similar_issues, start=1):
            issue_id = str(_field(issue, "id", "Id", "issueId", "IssueId") or "unknown")
            title = _field(issue, "title", "Title") or "(no title)"
            description = _field(issue, "description", "Description") or "(no description)"
            recs = issue.get("_recommendations", [])
            rec_texts: List[str] = []
            for rec in recs:
                rec_title = _field(rec, "title", "Title") or ""
                rec_desc = _field(rec, "description", "Description", "text", "Text") or ""
                rec_texts.append(f"  - {rec_title}: {rec_desc}".strip(" -"))
            recs_block = "\n".join(rec_texts) if rec_texts else "  (no recommendations recorded)"

            similar_summaries.append(
                f"[Issue {i}] ID: {issue_id}\n"
                f"Title: {title}\n"
                f"Description: {description}\n"
                f"Recommendations:\n{recs_block}"
            )

        similar_block = "\n\n---\n\n".join(similar_summaries) if similar_summaries else "(none found)"

        return f"""You are an expert internal audit advisor with deep knowledge of audit methodology, risk management, and remediation best practices.

An auditor is working on the following issue:

CURRENT ISSUE
Title: {current_issue.title}
Description: {current_issue.description}

The following historical audit issues are the most semantically similar. All of them have been Closed-Verified, meaning they were formally remediated and closed.

HISTORICAL SIMILAR ISSUES
{similar_block}

Your tasks:
1. For each historical issue, assess how relevant it is to the current issue (1–10 scale) and briefly explain why.
2. Based on patterns across the successfully remediated historical issues, draft a comprehensive recommendation for the current issue.
3. Identify the key recurring themes across these issues.

Respond ONLY with valid JSON in the following structure (no preamble, no explanation outside the JSON):

{{
  "similar_issues_analysis": [
    {{
      "issue_id": "<id of the historical issue>",
      "relevance_score": <integer 1-10>,
      "explanation": "<one or two sentences explaining relevance>"
    }}
  ],
  "draft_recommendation": "<full, actionable recommendation text for the current issue, drawing on what worked historically>",
  "key_themes": ["<theme 1>", "<theme 2>", "..."]
}}
"""

    def _call_claude_sync(self, prompt: str) -> str:
        """Synchronous Claude API call — intended to be run via asyncio.to_thread."""
        message = self._client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        current_issue: AnalyzeRequest,
        similar_issues: List[Dict[str, Any]],
    ) -> AnalysisResponse:
        """Analyse the current issue against similar historical issues and return structured results."""
        prompt = self._build_prompt(current_issue, similar_issues)

        logger.info("Calling Claude %s for analysis (prompt length: %d chars)", MODEL, len(prompt))
        raw_response = await asyncio.to_thread(self._call_claude_sync, prompt)
        logger.info("Received Claude response (%d chars)", len(raw_response))

        parsed = self._extract_json(raw_response)

        # Build a lookup from issue_id → analysis entry
        analysis_by_id: Dict[str, Dict[str, Any]] = {}
        for entry in parsed.get("similar_issues_analysis", []):
            analysis_by_id[str(entry.get("issue_id", ""))] = entry

        # Map similar_issues (in order) → SimilarIssue objects
        result_issues: List[SimilarIssue] = []
        for issue in similar_issues:
            issue_id = str(
                _field(issue, "id", "Id", "issueId", "IssueId") or "unknown"
            )
            title = _field(issue, "title", "Title") or "(no title)"
            description = _field(issue, "description", "Description") or ""
            recs = issue.get("_recommendations", [])
            rec_strings: List[str] = []
            for rec in recs:
                rec_title = _field(rec, "title", "Title") or ""
                rec_desc = _field(rec, "description", "Description", "text", "Text") or ""
                combined = ": ".join(filter(None, [rec_title, rec_desc]))
                if combined:
                    rec_strings.append(combined)

            analysis_entry = analysis_by_id.get(issue_id, {})
            raw_score = analysis_entry.get("relevance_score", 5)
            # Normalise 1–10 → 0.0–1.0
            normalised_score = float(max(1, min(10, raw_score))) / 10.0
            explanation = analysis_entry.get(
                "explanation", "Semantically similar to the current issue."
            )

            result_issues.append(
                SimilarIssue(
                    id=issue_id,
                    title=title,
                    description=description,
                    recommendations=rec_strings,
                    relevance_score=normalised_score,
                    explanation=explanation,
                    url=self._issue_url(issue_id),
                )
            )

        draft_recommendation: str = parsed.get(
            "draft_recommendation",
            "No draft recommendation was generated.",
        )
        key_themes: List[str] = parsed.get("key_themes", [])

        return AnalysisResponse(
            similar_issues=result_issues,
            draft_recommendation=draft_recommendation,
            key_themes=key_themes,
        )
