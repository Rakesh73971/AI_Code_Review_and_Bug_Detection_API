from app.ai.chains.review_chain import run_review_chain
from app.ai.schemas.review_output import ReviewOutput

def test_run_review_chain_with_rag():
    code = "def add(a, b):\n    return a + b"
    result, doc_sources = run_review_chain(language="python", code=code, use_rag=True)
    
    assert isinstance(result, ReviewOutput)
    assert result.quality_score == 85
    assert len(result.bugs_found) == 1
    assert result.bugs_found[0].severity == "critical"
    assert len(doc_sources) == 1
    assert doc_sources[0]["source"] == "official_docs.md"

def test_run_review_chain_without_rag():
    code = "def add(a, b):\n    return a + b"
    result, doc_sources = run_review_chain(language="python", code=code, use_rag=False)
    
    assert isinstance(result, ReviewOutput)
    assert result.quality_score == 85
    assert len(doc_sources) == 0
