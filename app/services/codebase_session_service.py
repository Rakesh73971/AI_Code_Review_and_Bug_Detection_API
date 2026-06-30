from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.code_base_sessions import CodebaseSession, SessionState
from app.models.user import User


def _is_admin(user: User) -> bool:
    role_value = user.role.value if hasattr(user.role, "value") else user.role
    return role_value == "admin"


def _get_session_or_404(db: Session, session_id: int, current_user: User) -> CodebaseSession:
    session = db.query(CodebaseSession).filter(CodebaseSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"codebase session with id {session_id} not found",
        )
    if session.user_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="not authorized to access this codebase session",
        )
    return session


def create_codebase_session_service(db: Session, session, current_user: User):
    session_data = session.model_dump()
    if session_data.get("status") is None:
        session_data["status"] = SessionState.PROCESSING
    if session_data.get("file_count") is None:
        session_data["file_count"] = 0

    db_session = CodebaseSession(user_id=current_user.id, **session_data)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_codebase_sessions_service(db: Session, current_user: User):
    query = db.query(CodebaseSession)
    if not _is_admin(current_user):
        query = query.filter(CodebaseSession.user_id == current_user.id)
    return query.all()


def get_codebase_session_service(db: Session, session_id: int, current_user: User):
    return _get_session_or_404(db, session_id, current_user)


def update_codebase_session_service(db: Session, session_id: int, session_update, current_user: User):
    db_session = _get_session_or_404(db, session_id, current_user)
    update_data = session_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_session, key, value)

    db.commit()
    db.refresh(db_session)
    return db_session


def delete_codebase_session_service(db: Session, session_id: int, current_user: User):
    db_session = _get_session_or_404(db, session_id, current_user)
    db.delete(db_session)
    db.commit()
    return None
