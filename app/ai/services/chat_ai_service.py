from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.ai.chains.chat_chain import run_chat_chain
from app.ai.schemas.chat_output import ChatRequest, ChatResponse
from app.models.chat_messages import ChatMessage, MessageRole
from app.models.code_base_sessions import SessionState
from app.models.user import User
from app.services.codebase_session_service import _get_session_or_404


def ask_codebase_service(
    db: Session,
    session_id: int,
    request: ChatRequest,
    current_user: User,
) -> ChatResponse:
    session = _get_session_or_404(db, session_id, current_user)
    if session.status != SessionState.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="codebase session is not ready for chat",
        )

    prior_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history = [
        {
            "role": msg.role.value if hasattr(msg.role, "value") else msg.role,
            "content": msg.content,
        }
        for msg in prior_messages
    ]

    answer, doc_sources = run_chat_chain(
        collection_name=session.chroma_collection_id,
        question=request.question,
        history=history,
    )

    user_message = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=request.question,
    )
    assistant_message = ChatMessage(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=answer,
        doc_sources=doc_sources,
    )
    db.add(user_message)
    db.add(assistant_message)
    db.commit()

    return ChatResponse(answer=answer, doc_sources=doc_sources)
