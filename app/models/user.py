from app.db.database import Base
from sqlalchemy import Column,Integer,String,TIMESTAMP,text,Boolean
from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

class UserRole(PyEnum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"


    id = Column(Integer,primary_key=True)
    username = Column(String,nullable=False)
    email = Column(String,unique=True,nullable=False)
    password = Column(String,nullable=False)
    role = Column(SAEnum(UserRole,values_callable=lambda x:[e.value for e in x]),default=UserRole.USER,nullable=False)
    github_name = Column(String,nullable=True)
    is_active = Column(Boolean,server_default="True",nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text('now()'),nullable=False)

    reviews = relationship("CodeReview",back_populates="user")
    sessions = relationship("CodebaseSession",back_populates="user")