from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.core.oauth2 import get_current_user
from app.models.user import User
from app.schemas.chat_message import ChatMessageCreate, ChatMessageUpdate, ChatMessageResponse
from app.services.chat_message_service import (
    create_chat_message_service,
    get_chat_messages_service,
    get_chat_message_service,
    update_chat_message_service,
    delete_chat_message_service,
)

router = APIRouter(
    prefix="/sessions/{session_id}/messages",
    tags=["Chat Messages"],
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ChatMessageResponse)
def create_chat_message(
    session_id: int,
    message: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_chat_message_service(db, session_id, message, current_user)


@router.get("/", status_code=status.HTTP_200_OK, response_model=List[ChatMessageResponse])
def get_chat_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_chat_messages_service(db, session_id, current_user)


@router.get("/{message_id}", status_code=status.HTTP_200_OK, response_model=ChatMessageResponse)
def get_chat_message(
    session_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_chat_message_service(db, session_id, message_id, current_user)


@router.put("/{message_id}", status_code=status.HTTP_200_OK, response_model=ChatMessageResponse)
def update_chat_message(
    session_id: int,
    message_id: int,
    message: ChatMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_chat_message_service(db, session_id, message_id, message, current_user)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_message(
    session_id: int,
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_chat_message_service(db, session_id, message_id, current_user)
