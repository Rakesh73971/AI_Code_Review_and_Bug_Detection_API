from langchain_core.prompts import ChatPromptTemplate

from app.ai.llm import get_llm
from app.ai.prompts.chat_prompt import CHAT_HUMAN_PROMPT, CHAT_SYSTEM_PROMPT
from app.ai.rag.retriever import retrieve_codebase_context


def _format_history(messages: list[dict]) -> str:
    if not messages:
        return "No prior conversation."
    lines = []
    for msg in messages:
        lines.append(f"{msg['role']}: {msg['content']}")
    return "\n".join(lines)


def run_chat_chain(
    collection_name: str,
    question: str,
    history: list[dict],
) -> tuple[str, list[dict]]:
    code_context, doc_sources = retrieve_codebase_context(collection_name, question)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHAT_SYSTEM_PROMPT),
            ("human", CHAT_HUMAN_PROMPT),
        ]
    )
    chain = prompt | get_llm()
    response = chain.invoke(
        {
            "history": _format_history(history),
            "code_context": code_context,
            "question": question,
        }
    )
    answer = response.content if hasattr(response, "content") else str(response)
    return answer, doc_sources
