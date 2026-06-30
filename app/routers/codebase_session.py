from fastapi import APIRouter, status, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.oauth2 import get_current_user
from app.models.user import User
from app.schemas.codebase_session import (
    CodebaseSessionCreate,
    CodebaseSessionUpdate,
    CodebaseSessionResponse,
)
from app.ai.schemas.chat_output import ChatRequest, ChatResponse
from app.ai.services.chat_ai_service import ask_codebase_service
from app.ai.services.rag_service import upload_and_index_codebase_service
from app.services.codebase_session_service import (
    create_codebase_session_service,
    get_codebase_sessions_service,
    get_codebase_session_service,
    update_codebase_session_service,
    delete_codebase_session_service,
)

router = APIRouter(
    prefix="/sessions",
    tags=["Codebase Sessions"],
)


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=CodebaseSessionResponse)
def upload_codebase(
    project_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return upload_and_index_codebase_service(db, project_name, file, current_user)


@router.post("/{session_id}/ask", status_code=status.HTTP_200_OK, response_model=ChatResponse)
def ask_codebase(
    session_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ask_codebase_service(db, session_id, request, current_user)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CodebaseSessionResponse)
def create_codebase_session(
    session: CodebaseSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_codebase_session_service(db, session, current_user)


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[CodebaseSessionResponse])
def get_codebase_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_codebase_sessions_service(db, current_user)


@router.get("/{session_id}", status_code=status.HTTP_200_OK, response_model=CodebaseSessionResponse)
def get_codebase_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_codebase_session_service(db, session_id, current_user)


@router.put("/{session_id}", status_code=status.HTTP_200_OK, response_model=CodebaseSessionResponse)
def update_codebase_session(
    session_id: int,
    session: CodebaseSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_codebase_session_service(db, session_id, session, current_user)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_codebase_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_codebase_session_service(db, session_id, current_user)
