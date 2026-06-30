from langchain_core.documents import Document

from app.ai.rag.vectorstore import get_docs_vectorstore

LANGUAGE_DOC_SOURCES = {
    "python": [
        "https://docs.python.org/3/tutorial/errors.html",
        "https://docs.python.org/3/library/exceptions.html",
    ],
    "javascript": [
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Control_flow_and_error_handling",
    ],
    "sql": [
        "https://www.postgresql.org/docs/current/sql-syntax.html",
    ],
    "java": [
        "https://docs.oracle.com/javase/tutorial/essential/exceptions/",
    ],
}

FRAMEWORK_DOC_URLS = [
    "https://fastapi.tiangolo.com/tutorial/first-steps/",
    "https://fastapi.tiangolo.com/tutorial/security/",
    "https://docs.djangoproject.com/en/stable/topics/http/urls/",
    "https://docs.djangoproject.com/en/stable/topics/db/models/",
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
        vectorstore.delete_collection()
    except Exception:
        pass

    vectorstore = get_docs_vectorstore()
    vectorstore.add_documents(chunks)

    return {
        "documents_loaded": len(all_docs),
        "chunks_indexed": len(chunks),
        "collection": vectorstore._collection.name,
    }
