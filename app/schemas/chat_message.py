from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ChatMessageCreate(BaseModel):
    role: str
    content: str
    doc_sources: Optional[Any] = None


class ChatMessageUpdate(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    doc_sources: Optional[Any] = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    doc_sources: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True
