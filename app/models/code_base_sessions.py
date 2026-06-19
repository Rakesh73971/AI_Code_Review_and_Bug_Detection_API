from app.db.database import Base
from sqlalchemy import Column,Integer,ForeignKey,String,TIMESTAMP,text
from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

class SessionState(PyEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

class CodebaseSession(Base):
    __tablename__="codebase_sessions"

    id = Column(Integer,primary_key=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=False)
    project_name = Column(String,nullable=False)
    chroma_collection_id = Column(String,unique=True,nullable=False)
    file_count = Column(Integer,default=0,nullable=False)
    status = Column(SAEnum(SessionState,values_callable=lambda x:[e.value for e in x]),default=SessionState.PROCESSING,nullable=False)
    task_id = Column(String,nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text("now()"),nullable=False)
    user = relationship("User",back_populates="sessions")
    messages = relationship("ChatMessage",back_populates="sessions")
