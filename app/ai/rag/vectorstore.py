from pathlib import Path

from langchain_community.vectorstores import Chroma

from app.ai.llm import get_embeddings
from app.db.config import settings


def get_chroma_persist_dir() -> Path:
    path = Path(settings.chroma_persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_docs_vectorstore() -> Chroma:
    return Chroma(
        collection_name=settings.docs_collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(get_chroma_persist_dir()),
    )


def get_codebase_vectorstore(collection_name: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(get_chroma_persist_dir()),
    )
