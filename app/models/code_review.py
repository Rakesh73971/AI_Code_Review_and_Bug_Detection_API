from app.db.database import Base
from sqlalchemy import Column,Integer,ForeignKey,Text,JSON,String,TIMESTAMP,text
from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

class Language(PyEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    SQL = "sql"
    JAVA = "java"


class ReviewSource(PyEnum):
    manual = "MANUAL"
    GITHUB_PR =  "github_pr"





class CodeReview(Base):
    __tablename__ = "code_reviews"

    id = Column(Integer,primary_key=True)
    user_id = Column(Integer,ForeignKey('users.id'),nullable=False)
    language = Column(SAEnum(Language,values_callable=lambda x:[e.value for e in x]),nullable=False)
    original_code = Column(Text,nullable=False)
    bugs_found = Column(JSON,nullable=True)
    severity_summary = Column(JSON,nullable=True)
    suggestions = Column(JSON,nullable=True)
    quality_score = Column(Integer,nullable=True)
    doc_sources_used = Column(JSON,nullable=True)
    source = Column(SAEnum(ReviewSource,values_callable=lambda x:[e.value for e in x]),default=ReviewSource.MANUAL,nullable=False)
    github_pr_url = Column(String,nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text("now()"),nullable=False)
    user = relationship("User",back_populates="reviews")


