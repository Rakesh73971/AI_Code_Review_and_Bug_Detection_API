from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CodebaseSessionCreate(BaseModel):
    project_name: str
    chroma_collection_id: str
    file_count: Optional[int] = 0
    status: Optional[str] = None
    task_id: str


class CodebaseSessionUpdate(BaseModel):
    project_name: Optional[str] = None
    chroma_collection_id: Optional[str] = None
    file_count: Optional[int] = None
    status: Optional[str] = None
    task_id: Optional[str] = None


class CodebaseSessionResponse(BaseModel):
    id: int
    user_id: int
    project_name: str
    chroma_collection_id: str
    file_count: int
    status: str
    task_id: str
    created_at: datetime

    class Config:
        from_attributes = True
