from typing import Optional

from pydantic import BaseModel, Field


class BugFinding(BaseModel):
    line: Optional[int] = None
    severity: str = Field(description="One of: critical, warning, info")
    description: str
    suggested_fix: Optional[str] = None


class SeveritySummary(BaseModel):
    critical: int = 0
    warning: int = 0
    info: int = 0


class ReviewOutput(BaseModel):
    bugs_found: list[BugFinding] = Field(default_factory=list)
    severity_summary: SeveritySummary
    suggestions: list[str] = Field(default_factory=list)
    quality_score: int = Field(ge=0, le=100)


class CodeReviewRequest(BaseModel):
    language: str
    original_code: str
    use_rag: bool = True
