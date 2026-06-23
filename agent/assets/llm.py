"""
llm 에셋 - LangChain 체인으로 답변을 생성해 ctx["answer"] 에 채운다.
RAG/Tool 이 채운 ctx["context"], ctx["tools_result"] 가 있으면 함께 프롬프트에 넣는다.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

NAME = "llm"


def build(conn: dict):
    """ChatOpenAI 체인을 만든다. (conn: {base_url, model, temperature, api_key})"""
    model = ChatOpenAI(
        model=conn["model"],
        api_key=conn.get("api_key", ""),
        base_url=conn["base_url"],
        temperature=conn.get("temperature", 0),
        max_retries=2,
    )
    # context / tools_result 슬롯은 비어 있으면 무시되도록 프롬프트에 함께 둔다
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        ("system", "참고자료:\n{context}"),
        ("system", "도구결과:\n{tools_result}"),
        ("user", "{query}"),
    ])
    return prompt | model | StrOutputParser()


def run(ctx: dict, resource) -> dict:
    """체인을 invoke 해서 답변을 ctx["answer"] 에 저장한다."""
    ctx["answer"] = resource.invoke({
        "query":          ctx["query"],
        "system_message": ctx.get("system_message", ""),
        "context":        ctx.get("context", "") or "(없음)",
        "tools_result":   ctx.get("tools_result", "") or "(없음)",
    })
    return ctx
