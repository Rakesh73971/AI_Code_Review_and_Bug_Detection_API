from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.code_review import CodeReview, ReviewSource
from app.models.user import User


def _is_admin(user: User) -> bool:
    role_value = user.role.value if hasattr(user.role, "value") else user.role
    return role_value == "admin"


def _get_review_or_404(db: Session, review_id: int, current_user: User) -> CodeReview:
    review = db.query(CodeReview).filter(CodeReview.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"code review with id {review_id} not found",
        )
    if review.user_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized to access this code review",
        )
    return review


def create_code_review_service(db: Session, review, current_user: User):
    review_data = review.model_dump()
    if review_data.get("source") is None:
        review_data["source"] = ReviewSource.MANUAL

    db_review = CodeReview(user_id=current_user.id, **review_data)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_code_reviews_service(db: Session, current_user: User):
    query = db.query(CodeReview)
    if not _is_admin(current_user):
        query = query.filter(CodeReview.user_id == current_user.id)
    return query.all()


def get_code_review_service(db: Session, review_id: int, current_user: User):
    return _get_review_or_404(db, review_id, current_user)


def update_code_review_service(db: Session, review_id: int, review_update, current_user: User):
    db_review = _get_review_or_404(db, review_id, current_user)
    update_data = review_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_review, key, value)

    db.commit()
    db.refresh(db_review)
    return db_review


def delete_code_review_service(db: Session, review_id: int, current_user: User):
    db_review = _get_review_or_404(db, review_id, current_user)
    db.delete(db_review)
    db.commit()
    return None
