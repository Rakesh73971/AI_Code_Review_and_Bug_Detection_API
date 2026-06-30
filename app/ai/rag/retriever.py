from langchain_core.documents import Document

from app.ai.rag.vectorstore import get_codebase_vectorstore, get_docs_vectorstore


def _format_docs(docs: list[Document]) -> str:
    if not docs:
        return "No relevant documentation found."
    parts = []
    for doc in docs:
        source = doc.metadata.get("source") or doc.metadata.get("file_path") or "unknown"
        parts.append(f"[{source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def _doc_sources(docs: list[Document]) -> list[dict]:
    sources = []
    for doc in docs:
        sources.append(
            {
                "source": doc.metadata.get("source") or doc.metadata.get("file_path"),
                "framework": doc.metadata.get("framework"),
                "snippet": doc.page_content[:300],
            }
        )
    return sources


def retrieve_doc_context(query: str, language: str, k: int = 4) -> tuple[str, list[dict]]:
    vectorstore = get_docs_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(f"{language} {query}")
    return _format_docs(docs), _doc_sources(docs)


def retrieve_codebase_context(collection_name: str, question: str, k: int = 6) -> tuple[str, list[dict]]:
    vectorstore = get_codebase_vectorstore(collection_name)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(question)
    return _format_docs(docs), _doc_sources(docs)
