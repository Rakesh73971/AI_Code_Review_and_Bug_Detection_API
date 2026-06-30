from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.chat_messages import ChatMessage
from app.models.user import User
from app.services.codebase_session_service import _get_session_or_404


def _get_message_or_404(db: Session, session_id: int, message_id: int, current_user: User) -> ChatMessage:
    _get_session_or_404(db, session_id, current_user)
    message = (
        db.query(ChatMessage)
        .filter(ChatMessage.id == message_id, ChatMessage.session_id == session_id)
        .first()
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"chat message with id {message_id} not found",
        )
    return message


def create_chat_message_service(db: Session, session_id: int, message, current_user: User):
    _get_session_or_404(db, session_id, current_user)
    db_message = ChatMessage(session_id=session_id, **message.model_dump())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


def get_chat_messages_service(db: Session, session_id: int, current_user: User):
    _get_session_or_404(db, session_id, current_user)
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()


def get_chat_message_service(db: Session, session_id: int, message_id: int, current_user: User):
    return _get_message_or_404(db, session_id, message_id, current_user)


def update_chat_message_service(db: Session, session_id: int, message_id: int, message_update, current_user: User):
    db_message = _get_message_or_404(db, session_id, message_id, current_user)
    update_data = message_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_message, key, value)

    db.commit()
    db.refresh(db_message)
    return db_message


def delete_chat_message_service(db: Session, session_id: int, message_id: int, current_user: User):
    db_message = _get_message_or_404(db, session_id, message_id, current_user)
    db.delete(db_message)
    db.commit()
    return None
