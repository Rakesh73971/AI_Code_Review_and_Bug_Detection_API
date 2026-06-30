from sqlalchemy.orm import Session

from app.ai.chains.review_chain import run_review_chain
from app.ai.schemas.review_output import CodeReviewRequest
from app.models.code_review import CodeReview, ReviewSource
from app.models.user import User


def analyze_code_service(db: Session, request: CodeReviewRequest, current_user: User) -> CodeReview:
    review_output, doc_sources = run_review_chain(
        language=request.language,
        code=request.original_code,
        use_rag=request.use_rag,
    )

    db_review = CodeReview(
        user_id=current_user.id,
        language=request.language,
        original_code=request.original_code,
        bugs_found=[bug.model_dump() for bug in review_output.bugs_found],
        severity_summary=review_output.severity_summary.model_dump(),
        suggestions=review_output.suggestions,
        quality_score=review_output.quality_score,
        doc_sources_used=doc_sources,
        source=ReviewSource.MANUAL,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

