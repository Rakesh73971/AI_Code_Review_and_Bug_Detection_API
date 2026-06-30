from fastapi import APIRouter, Depends, status

from app.ai.services.rag_service import index_docs_service
from app.core.oauth2 import get_admin_user
from app.models.user import User

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.post("/index-docs", status_code=status.HTTP_200_OK)
def index_documentation(current_user: User = Depends(get_admin_user)):
    return index_docs_service()
