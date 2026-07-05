import io
import zipfile
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.rag.vectorstore import get_codebase_vectorstore

CODE_EXTENSIONS = {".py", ".js", ".ts", ".sql", ".java"}


def _extract_code_files_from_zip(zip_bytes: bytes) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = Path(info.filename)
            if path.suffix.lower() not in CODE_EXTENSIONS:
                continue
            content = archive.read(info).decode("utf-8", errors="ignore")
            if content.strip():
                files.append((str(path), content))
    return files


def index_codebase_zip(collection_name: str, zip_bytes: bytes) -> dict:
    code_files = _extract_code_files_from_zip(zip_bytes)
    if not code_files:
        return {"file_count": 0, "chunks_indexed": 0}

    documents = [
        Document(
            page_content=content,
            metadata={"source": file_path, "file_path": file_path},
        )
        for file_path, content in code_files
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    chunks = splitter.split_documents(documents)

    vectorstore = get_codebase_vectorstore(collection_name)
    try:
        existing = vectorstore.get()
        if existing and existing.get("ids"):
            vectorstore.delete(ids=existing["ids"])
    except Exception:
        pass

    vectorstore = get_codebase_vectorstore(collection_name)

    
    # Safe batching to prevent Gemini Embeddings 429 rate limit
    import time
    batch_size = 40
    delay = 2.0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vectorstore.add_documents(batch)
        if i + batch_size < len(chunks):
            time.sleep(delay)

    return {"file_count": len(code_files), "chunks_indexed": len(chunks)}

