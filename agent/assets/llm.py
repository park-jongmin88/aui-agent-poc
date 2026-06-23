"""
llm 에셋 - LangChain 체인으로 답변을 생성해 ctx["answer"] 에 채운다.
RAG/Tool 이 채운 ctx["context"], ctx["tools_result"] 가 있으면
system_message 하나로 합쳐서 넣는다. (system 메시지를 여러 개 보내면
Qwen 등 일부 모델이 400 BadRequest 를 반환하므로 단일 system 으로 유지)
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
    # system 은 1개만. 변수는 런타임에 합쳐 넣는다.
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_message}"),
        ("user", "{query}"),
    ])
    return prompt | model | StrOutputParser()


def _merge_system(ctx: dict) -> str:
    """system_message 에 context/tools_result 가 있으면 이어붙여 하나로 만든다."""
    sys = ctx.get("system_message", "") or ""
    if ctx.get("context"):
        sys += f"\n\n[참고자료]\n{ctx['context']}"
    if ctx.get("tools_result"):
        sys += f"\n\n[도구결과]\n{ctx['tools_result']}"
    return sys


def run(ctx: dict, resource) -> dict:
    """체인을 invoke 해서 답변을 ctx["answer"] 에 저장한다."""
    ctx["answer"] = resource.invoke({
        "system_message": _merge_system(ctx),
        "query":          ctx["query"],
    })
    return ctx
