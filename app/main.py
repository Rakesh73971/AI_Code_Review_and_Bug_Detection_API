from fastapi import FastAPI
from app.db.database import Base, engine
from app.routers import user, oauth, code_review, codebase_session, chat_message, rag
from app.models import user as user_model
from app.models import code_review as code_review_model
from app.models import code_base_sessions as codebase_session_model
from app.models import chat_messages as chat_message_model

app = FastAPI(title="AI Code Review and Bug Detection")

app.include_router(oauth.router)
app.include_router(user.router)
app.include_router(code_review.router)
app.include_router(codebase_session.router)
app.include_router(chat_message.router)
app.include_router(rag.router)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "AI Code Review and Bug Detection API"}
