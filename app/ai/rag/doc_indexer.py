from langchain_core.documents import Document

from app.ai.rag.vectorstore import get_docs_vectorstore

LANGUAGE_DOC_SOURCES = {
    "python": [
        "https://docs.python.org/3/tutorial/errors.html",
    ],
    "javascript": [
        "https://fastapi.tiangolo.com/tutorial/first-steps/",
    ]
}

FRAMEWORK_DOC_URLS = [
    "https://fastapi.tiangolo.com/tutorial/first-steps/",
]



def _load_url_documents(urls: list[str], source: str) -> list[Document]:
    from langchain_community.document_loaders import WebBaseLoader

    loader = WebBaseLoader(urls)
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = source
        doc.metadata["framework"] = source
    return docs


def index_official_docs() -> dict:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    all_docs: list[Document] = []

    for language, urls in LANGUAGE_DOC_SOURCES.items():
        all_docs.extend(_load_url_documents(urls, language))

    all_docs.extend(_load_url_documents(FRAMEWORK_DOC_URLS, "framework"))

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(all_docs)

    vectorstore = get_docs_vectorstore()
    try:
        existing = vectorstore.get()
        if existing and existing.get("ids"):
            vectorstore.delete(ids=existing["ids"])
    except Exception:
        pass

    vectorstore = get_docs_vectorstore()

    
    # Safe batching to prevent Gemini Embeddings 429 rate limit
    import time
    batch_size = 40
    delay = 2.0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vectorstore.add_documents(batch)
        if i + batch_size < len(chunks):
            time.sleep(delay)

    return {
        "documents_loaded": len(all_docs),
        "chunks_indexed": len(chunks),
        "collection": vectorstore._collection.name,
    }

