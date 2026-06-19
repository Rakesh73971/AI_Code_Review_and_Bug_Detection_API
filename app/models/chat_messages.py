from app.db.database import Base
from sqlalchemy import Column,Integer,ForeignKey,Text,JSON,TIMESTAMP,text
from sqlalchemy import Enum as SAEnum
from enum import Enum as PyEnum
from sqlalchemy.orm import relationship


class MessageRole(PyEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(Base):
    __tablename__="chat_messages"

    id = Column(Integer,primary_key=True)
    session_id = Column(Integer,ForeignKey("codebase_sessions.id"),nullable=False)
    role = Column(SAEnum(MessageRole,values_callable=lambda x:[e.value for e in x]),nullable=False)
    content = Column(Text,nullable=False)
    doc_sources = Column(JSON,nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text("now()"),nullable=False)
    session = relationship("CodebaseSession",back_populates="messages")