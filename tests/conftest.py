import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import datetime

from app.db.database import Base, get_db
from app.main import app
from app.core.oauth2 import create_access_token
from app.models.user import User, UserRole

# Set up SQLite in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Register PG-compatible 'now()' function on SQLite
@event.listens_for(engine, "connect")
def register_sqlite_functions(dbapi_connection, connection_record):
    dbapi_connection.create_function("now", 0, lambda: datetime.datetime.utcnow().isoformat())

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# ----------------- Mocking AI Components -----------------
from langchain_core.language_models.chat_models import SimpleChatModel
from langchain_core.messages import AIMessageChunk, AIMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.embeddings import Embeddings

class MockLLM(SimpleChatModel):
    @property
    def _llm_type(self) -> str:
        return "mock_gemini"

    def _call(self, messages, stop=None, run_manager=None, **kwargs) -> str:
        return "Mocked LLM Response"

    async def astream(self, *args, **kwargs):
        yield AIMessageChunk(content="Mocked ")
        yield AIMessageChunk(content="streamed ")
        yield AIMessageChunk(content="response")

    def with_structured_output(self, schema, **kwargs):
        mock_structured = MagicMock()
        from app.ai.schemas.review_output import ReviewOutput, BugFinding, SeveritySummary
        review_out = ReviewOutput(
            bugs_found=[
                BugFinding(line=5, severity="critical", description="Mock bug description", suggested_fix="def fix_code():\n    pass")
            ],
            severity_summary=SeveritySummary(critical=1, warning=0, info=0),
            suggestions=["Mock suggestion 1", "Mock suggestion 2"],
            quality_score=85
        )
        mock_structured.return_value = review_out
        mock_structured.invoke.return_value = review_out
        return mock_structured

class MockEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[0.1] * 768 for _ in texts]
    def embed_query(self, text):
        return [0.1] * 768

@pytest.fixture(autouse=True)
def mock_ai_services():
    mock_llm = MockLLM()
    mock_embeddings = MockEmbeddings()
    
    # Mock Chroma vector database
    mock_chroma_class = MagicMock()
    mock_chroma_instance = MagicMock()
    mock_chroma_class.return_value = mock_chroma_instance
    
    mock_retriever = MagicMock()
    mock_chroma_instance.as_retriever.return_value = mock_retriever
    
    from langchain_core.documents import Document
    mock_retriever.invoke.return_value = [
        Document(
            page_content="Mock documentation context showing best practices.",
            metadata={"source": "official_docs.md", "framework": "fastapi"}
        )
    ]

    patches = [
        # Original definitions (for dynamic imports)
        patch("app.ai.llm.get_llm", return_value=mock_llm),
        patch("app.ai.llm.get_embeddings", return_value=mock_embeddings),
        patch("app.ai.rag.vectorstore.Chroma", new=mock_chroma_class),
        
        # Module-level imports (bound at import time)
        patch("app.ai.chains.review_chain.get_llm", return_value=mock_llm),
        patch("app.ai.chains.chat_chain.get_llm", return_value=mock_llm),
    ]

    opened_patches = [p.start() for p in patches]
    yield
    for p in patches:
        p.stop()

# ----------------- Auth Helpers -----------------
@pytest.fixture
def test_user(db_session):
    from app.core.utils import hash_password
    user = User(
        username="testuser",
        email="testuser@example.com",
        password=hash_password("password123"),
        role=UserRole.USER,
        github_name="test_github_user",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_admin(db_session):
    from app.core.utils import hash_password
    user = User(
        username="adminuser",
        email="adminuser@example.com",
        password=hash_password("password123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def user_token(test_user):
    return create_access_token(data={"user_id": test_user.id})

@pytest.fixture
def admin_token(test_admin):
    return create_access_token(data={"user_id": test_admin.id})

@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}

@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
