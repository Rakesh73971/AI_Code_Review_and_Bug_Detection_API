from langchain_core.documents import Document
from app.ai.rag.retriever import (
    _format_docs,
    _doc_sources,
    retrieve_doc_context,
    retrieve_codebase_context
)

def test_format_docs():
    docs = [
        Document(page_content="content1", metadata={"source": "src1"}),
        Document(page_content="content2", metadata={"file_path": "path2"})
    ]
    res = _format_docs(docs)
    assert "[src1]\ncontent1" in res
    assert "[path2]\ncontent2" in res

def test_format_docs_empty():
    res = _format_docs([])
    assert res == "No relevant documentation found."

def test_doc_sources():
    docs = [
        Document(page_content="content1" * 100, metadata={"source": "src1", "framework": "fastapi"}),
        Document(page_content="content2", metadata={"file_path": "path2"})
    ]
    sources = _doc_sources(docs)
    assert len(sources) == 2
    assert sources[0]["source"] == "src1"
    assert sources[0]["framework"] == "fastapi"
    assert sources[0]["snippet"].startswith("content1")
    assert len(sources[0]["snippet"]) == 300
    assert sources[1]["source"] == "path2"

def test_retrieve_doc_context():
    formatted_context, sources = retrieve_doc_context("query", "python")
    assert "Mock documentation context showing best practices." in formatted_context
    assert len(sources) == 1
    assert sources[0]["source"] == "official_docs.md"

def test_retrieve_codebase_context():
    formatted_context, sources = retrieve_codebase_context("col_name", "question")
    assert "Mock documentation context showing best practices." in formatted_context
    assert len(sources) == 1
    assert sources[0]["source"] == "official_docs.md"
