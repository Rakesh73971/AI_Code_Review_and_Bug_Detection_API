from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class CodeReviewCreate(BaseModel):
    language: str
    original_code: str
    bugs_found: Optional[Any] = None
    severity_summary: Optional[Any] = None
    suggestions: Optional[Any] = None
    quality_score: Optional[int] = None
    doc_sources_used: Optional[Any] = None
    source: Optional[str] = None
    github_pr_url: Optional[str] = None


class CodeReviewUpdate(BaseModel):
    language: Optional[str] = None
    original_code: Optional[str] = None
    bugs_found: Optional[Any] = None
    severity_summary: Optional[Any] = None
    suggestions: Optional[Any] = None
    quality_score: Optional[int] = None
    doc_sources_used: Optional[Any] = None
    source: Optional[str] = None
    github_pr_url: Optional[str] = None


class CodeReviewResponse(BaseModel):
    id: int
    user_id: int
    language: str
    original_code: str
    bugs_found: Optional[Any] = None
    severity_summary: Optional[Any] = None
    suggestions: Optional[Any] = None
    quality_score: Optional[int] = None
    doc_sources_used: Optional[Any] = None
    source: str
    github_pr_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
