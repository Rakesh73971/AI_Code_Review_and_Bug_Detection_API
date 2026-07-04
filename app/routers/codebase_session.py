from fastapi import APIRouter, status, Depends, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from jose import jwt
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


@router.websocket("/{session_id}/ask-ws")
async def ws_chat(websocket: WebSocket, session_id: int, token: str = None, db: Session = Depends(get_db)):
    await websocket.accept()
    user = None
    if token:
        user = get_ws_user(token, db)
    if not user:
        await websocket.send_json({"error": "Unauthorized token"})
        await websocket.close()
        return
        
    from app.services.codebase_session_service import _get_session_or_404
    try:
        session = _get_session_or_404(db, session_id, user)
    except Exception as exc:
        await websocket.send_json({"error": str(exc)})
        await websocket.close()
        return
        
    from app.models.code_base_sessions import SessionState
    if session.status != SessionState.READY:
        await websocket.send_json({"error": "Codebase session is not ready for chat"})
        await websocket.close()
        return
        
    try:
        while True:
            data = await websocket.receive_json()
            question = data.get("question")
            if not question:
                await websocket.send_json({"error": "Missing question"})
                continue
                
            # Get prior history
            from app.models.chat_messages import ChatMessage, MessageRole
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
            
            # Retrieve codebase context
            from app.ai.rag.retriever import retrieve_codebase_context
            code_context, doc_sources = retrieve_codebase_context(session.chroma_collection_id, question)
            
            # Send a start message
            await websocket.send_json({"type": "start"})
            
            # Stream the chat response
            from app.ai.llm import get_llm
            from langchain_core.prompts import ChatPromptTemplate
            from app.ai.prompts.chat_prompt import CHAT_SYSTEM_PROMPT, CHAT_HUMAN_PROMPT
            
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", CHAT_SYSTEM_PROMPT),
                    ("human", CHAT_HUMAN_PROMPT),
                ]
            )
            
            chain = prompt | get_llm()
            
            from app.ai.chains.chat_chain import _format_history
            
            full_answer_text = []
            async for chunk in chain.astream({
                "history": _format_history(history),
                "code_context": code_context,
                "question": question,
            }):
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
                full_answer_text.append(content)
                
            accumulated_answer = "".join(full_answer_text)
            
            # Save messages in history DB
            user_message = ChatMessage(
                session_id=session_id,
                role=MessageRole.USER,
                content=question,
            )
            assistant_message = ChatMessage(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=accumulated_answer,
                doc_sources=doc_sources,
            )
            db.add(user_message)
            db.add(assistant_message)
            db.commit()
            
            await websocket.send_json({"type": "done", "answer": accumulated_answer})
            
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass
