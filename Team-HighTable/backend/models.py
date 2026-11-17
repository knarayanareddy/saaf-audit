from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    title: str
    description: str
    issue_id: Optional[str] = None  # If provided, backend fetches from TeamMate


class SimilarIssue(BaseModel):
    id: str
    title: str
    description: str
    recommendations: List[str]
    relevance_score: float  # 0.0–1.0
    explanation: str
    url: str


class AnalysisResponse(BaseModel):
    similar_issues: List[SimilarIssue]
    draft_recommendation: str
    key_themes: List[str] = []
