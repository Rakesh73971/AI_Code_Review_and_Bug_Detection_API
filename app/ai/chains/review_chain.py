from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm import get_llm
from app.ai.prompts.review_prompt import REVIEW_HUMAN_PROMPT, REVIEW_SYSTEM_PROMPT
from app.ai.rag.retriever import retrieve_doc_context
from app.ai.schemas.review_output import ReviewOutput


def run_review_chain(language: str, code: str, use_rag: bool = True) -> tuple[ReviewOutput, list[dict]]:
    doc_context = "No documentation context available."
    doc_sources: list[dict] = []

    if use_rag:
        doc_context, doc_sources = retrieve_doc_context(code[:800], language)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REVIEW_SYSTEM_PROMPT),
            ("human", REVIEW_HUMAN_PROMPT),
        ]
    )
    structured_llm = get_llm().with_structured_output(ReviewOutput)
    chain = prompt | structured_llm
    result = chain.invoke(
        {
            "language": language,
            "code": code,
            "doc_context": doc_context,
        }
    )
    return result, doc_sources

