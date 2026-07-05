from fastapi import APIRouter, status, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import func
from sqlalchemy.orm import Session
from jose import jwt
from typing import List
from app.db.database import get_db
from app.core.oauth2 import get_current_user, get_admin_user
from app.models.user import User
from app.models.code_review import CodeReview
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


@router.get("/analytics", status_code=status.HTTP_200_OK)
def get_code_review_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
):
    # Total reviews
    total_reviews = db.query(CodeReview).count()
    
    # Average quality score
    avg_score_res = db.query(func.avg(CodeReview.quality_score)).scalar()
    average_quality_score = float(avg_score_res) if avg_score_res is not None else 0.0

    # Counts by language
    lang_counts = db.query(CodeReview.language, func.count(CodeReview.id)).group_by(CodeReview.language).all()
    language_distribution = {
        lang.value if hasattr(lang, "value") else str(lang): count for lang, count in lang_counts
    }

    # Counts by source (MANUAL vs. GITHUB_PR)
    src_counts = db.query(CodeReview.source, func.count(CodeReview.id)).group_by(CodeReview.source).all()
    source_distribution = {
        src.value if hasattr(src, "value") else str(src): count for src, count in src_counts
    }

    # Get severity counts from JSON summaries
    all_reviews = db.query(CodeReview.severity_summary).all()
    severity_totals = {"critical": 0, "warning": 0, "info": 0}
    for (summary,) in all_reviews:
        if summary:
            if isinstance(summary, dict):
                severity_totals["critical"] += summary.get("critical", 0)
                severity_totals["warning"] += summary.get("warning", 0)
                severity_totals["info"] += summary.get("info", 0)

    return {
        "total_reviews": total_reviews,
        "average_quality_score": round(average_quality_score, 1),
        "bug_severity_summary": severity_totals,
        "language_distribution": language_distribution,
        "source_distribution": source_distribution
    }



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


def get_ws_user(token: str, db: Session) -> User:
    from app.core.oauth2 import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


@router.websocket("/ws")
async def ws_code_review(websocket: WebSocket, token: str = None, db: Session = Depends(get_db)):
    await websocket.accept()
    user = None
    if token:
        user = get_ws_user(token, db)
    if not user:
        await websocket.send_json({"error": "Unauthorized token"})
        await websocket.close()
        return
        
    try:
        while True:
            data = await websocket.receive_json()
            language = data.get("language")
            code = data.get("code")
            use_rag = data.get("use_rag", True)
            
            if not language or not code:
                await websocket.send_json({"error": "Missing language or code"})
                continue
                
            # 1. Fetch RAG context and details
            doc_context = "No documentation context available."
            doc_sources = []
            if use_rag:
                try:
                    from app.ai.rag.retriever import retrieve_doc_context
                    doc_context, doc_sources = retrieve_doc_context(code[:800], language)
                except Exception:
                    pass
            
            # Send a start message
            await websocket.send_json({"type": "start"})
            
            # 2. Setup prompt and stream target model
            from app.ai.llm import get_llm
            from langchain_core.prompts import ChatPromptTemplate
            
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "You are an expert code reviewer and bug detection assistant. Review the user's code for bugs, security issues, performance issues, and style violations. Frame your answer in clean Markdown, including Bug Findings (with line numbers if possible), Severity Summary (critical/warning/info count), Suggestions, and a Quality Score (0-100). Use the documentation context to ground your review."),
                    ("human", "Language: {language}\n\nDocumentation Context:\n{doc_context}\n\nCode to review:\n```{language}\n{code}\n```"),
                ]
            )
            
            chain = prompt | get_llm()
            full_review_text = []
            async for chunk in chain.astream({"language": language, "doc_context": doc_context, "code": code}):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if isinstance(content, list):
                    texts = []
                    for part in content:
                        if isinstance(part, str):
                            texts.append(part)
                        elif isinstance(part, dict) and "text" in part:
                            texts.append(part["text"])
                    content = "".join(texts)
                
                await websocket.send_json({"type": "token", "token": content})
                full_review_text.append(content)
            
            accumulated_text = "".join(full_review_text)
            
            # 3. Trigger structured analysis in the background to persist review in Postgres
            from app.ai.schemas.review_output import ReviewOutput
            try:
                structured_llm = get_llm().with_structured_output(ReviewOutput)
                extraction_prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an assistant that extracts code review results into a structured format. Extract the bugs found, severity summary, suggestions, and quality score from the review text."),
                    ("human", "Review text:\n{review_text}")
                ])
                extraction_chain = extraction_prompt | structured_llm
                structured_res = extraction_chain.invoke({"review_text": accumulated_text})
                
                # Save database record
                from app.models.code_review import CodeReview, ReviewSource
                db_review = CodeReview(
                    user_id=user.id,
                    language=language,
                    original_code=code,
                    bugs_found=[bug.model_dump() for bug in structured_res.bugs_found] if hasattr(structured_res, "bugs_found") else None,
                    severity_summary=structured_res.severity_summary.model_dump() if hasattr(structured_res, "severity_summary") else None,
                    suggestions=structured_res.suggestions if hasattr(structured_res, "suggestions") else None,
                    quality_score=structured_res.quality_score if hasattr(structured_res, "quality_score") else None,
                    doc_sources_used=doc_sources,
                    source=ReviewSource.MANUAL
                )
                db.add(db_review)
                db.commit()
                db.refresh(db_review)
                
                await websocket.send_json({"type": "done", "review_id": db_review.id})
            except Exception as exc:
                await websocket.send_json({"type": "done", "error": f"Failed to save review details: {exc}"})
                
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass

