import uuid

from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from app.ai.rag.codebase_indexer import index_codebase_zip
from app.ai.rag.doc_indexer import index_official_docs
from app.models.code_base_sessions import CodebaseSession, SessionState
from app.models.user import User


def index_docs_service() -> dict:
    return index_official_docs()


def upload_and_index_codebase_service(
    db: Session,
    project_name: str,
    zip_file: UploadFile,
    current_user: User,
) -> CodebaseSession:
    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="upload must be a .zip file",
        )

    zip_bytes = zip_file.file.read()
    collection_id = f"session_{current_user.id}_{uuid.uuid4().hex[:12]}"
    task_id = uuid.uuid4().hex

    db_session = CodebaseSession(
        user_id=current_user.id,
        project_name=project_name,
        chroma_collection_id=collection_id,
        file_count=0,
        status=SessionState.PROCESSING,
        task_id=task_id,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    try:
        result = index_codebase_zip(collection_id, zip_bytes)
        db_session.file_count = result["file_count"]
        db_session.status = SessionState.READY if result["file_count"] > 0 else SessionState.FAILED
    except Exception as exc:
        db_session.status = SessionState.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"failed to index codebase: {exc}",
        ) from exc

    db.commit()
    db.refresh(db_session)
    return db_session
