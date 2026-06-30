from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.oauth2 import get_current_user
from app.models.user import User
from app.schemas.code_review import CodeReviewCreate, CodeReviewUpdate, CodeReviewResponse
from app.ai.schemas.review_output import CodeReviewRequest
from app.ai.services.review_ai_service import analyze_code_service
from app.services.code_review_service import (
    create_code_review_service,
    get_code_reviews_service,
    get_code_review_service,
    update_code_review_service,
    delete_code_review_service,
)

router = APIRouter(
    prefix="/code-reviews",
    tags=["Code Reviews"],
)


@router.post("/analyze", status_code=status.HTTP_201_CREATED, response_model=CodeReviewResponse)
def analyze_code(
    request: CodeReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analyze_code_service(db, request, current_user)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CodeReviewResponse)
def create_code_review(
    review: CodeReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_code_review_service(db, review, current_user)


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[CodeReviewResponse])
def get_code_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_code_reviews_service(db, current_user)


@router.get("/{review_id}", status_code=status.HTTP_200_OK, response_model=CodeReviewResponse)
def get_code_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_code_review_service(db, review_id, current_user)


@router.put("/{review_id}", status_code=status.HTTP_200_OK, response_model=CodeReviewResponse)
def update_code_review(
    review_id: int,
    review: CodeReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_code_review_service(db, review_id, review, current_user)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_code_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_code_review_service(db, review_id, current_user)

