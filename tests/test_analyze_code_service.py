from app.ai.services.review_ai_service import analyze_code_service
from app.ai.schemas.review_output import CodeReviewRequest
from app.models.code_review import CodeReview, ReviewSource, Language

def test_analyze_code_service(db_session, test_user):
    req = CodeReviewRequest(
        language="python",
        original_code="def buggy():\n    pass",
        use_rag=True
    )
    
    review = analyze_code_service(db_session, req, test_user)
    
    assert review is not None
    assert review.id is not None
    assert review.user_id == test_user.id
    assert review.language == Language.PYTHON
    assert review.original_code == req.original_code
    assert review.bugs_found == [{"line": 5, "severity": "critical", "description": "Mock bug description", "suggested_fix": "def fix_code():\n    pass"}]
    assert review.severity_summary == {"critical": 1, "warning": 0, "info": 0}
    assert review.suggestions == ["Mock suggestion 1", "Mock suggestion 2"]
    assert review.quality_score == 85
    assert review.source == ReviewSource.MANUAL
