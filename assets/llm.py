"""
llm 에셋 - LangChain 체인으로 답변을 생성해 ctx["answer"] 에 채운다.
RAG/Tool 이 채운 ctx["context"], ctx["tools_result"] 가 있으면
system_message 하나로 합쳐서 넣는다. (system 메시지를 여러 개 보내면
Qwen 등 일부 모델이 400 BadRequest 를 반환하므로 단일 system 으로 유지)

[Gateway 방식]
  실제 LLM 접속정보(주소·키)는 MLflow AI Gateway 가 갖고 있다. 이 에셋은
  client 로부터 키를 받지 않고, gateway 의 OpenAI 호환 엔드포인트를 부른다.
    base_url : {MLFLOW_TRACKING_URI}/gateway/mlflow/v1   (agent.py 가 conn 에 채워줌)
    model    : gateway 에 등록된 엔드포인트 이름          (agent.py 등록 시 선택)
    인증     : gateway 는 MLflow 로그인 Basic 인증을 요구한다 (judge_eval 과 동일 방식).
               api_key 필드는 게이트웨이가 무시하므로 "dummy" 로 채우고,
               실제 인증은 default_headers 의 Authorization: Basic ... 으로 보낸다.
"""

import base64

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import mlflow

NAME = "llm"


def _basic_auth_header(username: str, password: str) -> dict:
    """MLflow 아이디/비번으로 Basic 인증 헤더를 만든다. (judge_eval / gateway_utils 와 동일 로직)"""
    user = username if isinstance(username, str) else ""
    pw = password if isinstance(password, str) else ""
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def build(conn: dict):
    """ChatOpenAI 체인을 gateway 방식으로 만든다.

    conn 예시 (agent.py 등록 시 채워짐):
      {
        "base_url": "http://mlflow.도메인.com/gateway/mlflow/v1",
        "model":    "my-chat-endpoint",        # gateway 엔드포인트 이름
        "mlflow_username": "...", "mlflow_password": "...",  # Basic 인증용 (MLflow 계정 재사용)
        "temperature": 0,
      }
    """
    headers = _basic_auth_header(
        conn.get("mlflow_username", ""), conn.get("mlflow_password", "")
    )
    model = ChatOpenAI(
        model=conn["model"],
        api_key="dummy",              # gateway 가 인증을 처리하므로 실제 값 불필요
        base_url=conn["base_url"],
        default_headers=headers,      # gateway Basic 인증
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


def _safe_text(s) -> str:
    """LLM 응답에 깨진 surrogate(이모지 등에서 발생)가 있어도 JSON 직렬화가 죽지 않게 정리."""
    if not isinstance(s, str):
        return s
    return s.encode("utf-8", "replace").decode("utf-8", "replace")


@mlflow.trace(name="asset.llm", span_type="CHAIN")
def run(ctx: dict, resource) -> dict:
    """체인을 invoke 해서 답변을 ctx["answer"] 에 저장한다."""
    answer = resource.invoke({
        "system_message": _merge_system(ctx),
        "query":          ctx["query"],
    })
    ctx["answer"] = _safe_text(answer)
    return ctx

