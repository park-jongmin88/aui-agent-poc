"""
==============================================================================
 AI-Studio | GenAI Agent (agent.py)
==============================================================================
 LangChain 기반 LLM Agent 를 MLflow pyfunc 모델로 "등록" 한다.
 등록된 모델은 custom_server.py(서빙 이미지)가 감싸 KServe 로 서빙한다.

 [작동 순서]
   1. (등록) python agent.py 실행 -> register_agent() 호출
   2. LLM_CONN 을 llm_conn.json 으로 저장 -> Artifact 로 함께 등록
   3. ModelWrapper 를 MLflow pyfunc 모델로 log_model
   4. (서빙) custom_server.py 가 모델 로드 -> load_context() 1회 실행 (autolog 켜짐)
   5. (호출) custom_server 가 predict() 호출:
        입력  { "input":[{query, system_message, llm_api_key, session_id}], trace_id, pis_name ... }
        출력  { "aiu_output": "답변" }
   6. predict() -> _run() -> chain.invoke() 실행. LangChain autolog 가 트레이스 자동 기록.

 [custom_server.py 계약]
   - 입력 핵심은 model_input["input"][0] 의 dict
   - 출력은 반드시 {"aiu_output": ...}

 [확장]
   RAG / Tool / Prompt 추가 시 _get_chain() 의 프롬프트와 load_context() 의
   에셋 로드 부분에 단계를 끼워넣는다. (아래 [확장] 주석 위치 참고)
==============================================================================
"""

import os
import json
import uuid
import mlflow
import mlflow.pyfunc
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# =============================================================================
# [0] 연결 정보 (TODO 를 실제 값으로 채운다)
# =============================================================================
MLFLOW_CONN = {
    "tracking_uri":     TODO,
    "username":         TODO,
    "password":         TODO,
    "experiment_name":  TODO,
    "registered_model": TODO,
}

# base_url / model 은 서버 고정값. api_key 는 호출 시 client 가 보낸 값을 사용.
LLM_CONN = {
    "base_url":    TODO,
    "model":       TODO,
    "temperature": 0,
}


# =============================================================================
# [1] 유틸
# =============================================================================

def _is_set(value) -> bool:
    """값이 실제로 채워졌는지(TODO/빈값이 아닌지) 판단한다."""
    return isinstance(value, str) and bool(value) and value != "{TODO}"


def _agent_error(stage: str, exc: Exception, query: str, session_id: str) -> str:
    """예외를 '[AGENT ERROR]' 로 시작하는 진단 문자열로 만든다(서버는 죽지 않음)."""
    import traceback
    tb = traceback.format_exc()
    return (
        "[AGENT ERROR]\n"
        f"stage  : {stage}\n"
        f"type   : {type(exc).__name__}\n"
        f"message: {exc}\n"
        f"query  : {query}\n"
        f"session: {session_id}\n"
        "---- traceback ----\n"
        f"{tb}"
    )


# =============================================================================
# [2] ModelWrapper - 서빙되는 모델 본체
# =============================================================================

class ModelWrapper(mlflow.pyfunc.PythonModel):

    def load_context(self, context):
        """서빙 시작 시 1회 호출. MLflow tracking 설정 + LangChain autolog + 연결정보 로드."""
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", ""))
        exp = os.getenv("MLFLOW_EXPERIMENT_NAME", "")
        if exp:
            mlflow.set_experiment(exp)
        mlflow.langchain.autolog()   # LangChain 체인/LLM 호출 트레이스 자동 기록

        with open(context.artifacts["llm_conn"], "r", encoding="utf-8") as f:
            self.llm_conn = json.load(f)

        # [확장] 다른 에셋 로드
        # with open(context.artifacts["rag_conn"], "r") as f:  self.rag_conn = json.load(f)
        # with open(context.artifacts["tool_conn"], "r") as f: self.tool_conn = json.load(f)

        self._api_key = None
        self.chain = None

    def _get_chain(self, api_key: str):
        """ChatOpenAI + 프롬프트 + 파서로 LangChain 체인을 만든다. (api_key 바뀔 때만 재생성)"""
        model = ChatOpenAI(
            model=self.llm_conn["model"],
            api_key=api_key,
            base_url=self.llm_conn["base_url"],
            temperature=self.llm_conn.get("temperature", 0),
            max_retries=2,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}"),
            # [확장] ("system", "참고자료:\n{context}"),   # RAG 검색결과 주입
            ("user", "{query}"),
        ])
        return prompt | model | StrOutputParser()

    @mlflow.trace(name="agent_pipeline")
    def _run(self, query: str, system_message: str, api_key: str,
             session_id: str, user_id: str, trace_id: str) -> str:
        """질문 1건 처리. Trace 에 session/user 기록 후 체인 호출. (autolog 가 하위 span 기록)"""
        # Trace 에 session/user 기록 (같은 session_id 끼리 Sessions 탭에 묶임)
        # MLflow 3.10 은 session_id= 파라미터 미지원(3.11+). Sessions 탭은
        # metadata 의 표준 키 'mlflow.trace.session' / 'mlflow.trace.user' 를 읽는다.
        try:
            mlflow.update_current_trace(
                metadata={
                    "mlflow.trace.session": session_id,
                    "mlflow.trace.user":    user_id or "aiu-user",
                    "app_type":             "genai",
                },
                tags={"trace_id": trace_id or ""},
            )
        except Exception:
            pass

        # api_key 가 바뀌었을 때만 체인 재생성
        if api_key != self._api_key:
            self.chain = self._get_chain(api_key)
            self._api_key = api_key

        # [확장] RAG/Tool 단계는 여기서 호출해 invoke 입력에 함께 넣는다
        # context = rag_search(query, self.rag_conn)
        return self.chain.invoke({"query": query, "system_message": system_message or ""})

    def predict(self, context, model_input, params=None):
        """custom_server 진입점. input[0] 에서 query 등을 꺼내 _run() 실행 후 {"aiu_output":...} 반환."""
        # custom_server 계약: model_input["input"] = [{query, system_message, llm_api_key, session_id}]
        try:
            items = model_input["input"]
        except (TypeError, KeyError):
            items = model_input if isinstance(model_input, list) else [model_input]

        trace_id = model_input.get("trace_id", "") if isinstance(model_input, dict) else ""

        info = items[0] if items else {}
        query          = str(info.get("query", "")).strip()
        system_message = info.get("system_message", "")
        api_key        = info.get("llm_api_key", "")
        session_id     = info.get("session_id") or trace_id or "sess-" + uuid.uuid4().hex[:8]
        user_id        = info.get("user_id")

        # llm_api_key 미입력 시 호출하지 않고 에러 반환
        if not api_key:
            return {"aiu_output": "[AGENT ERROR] llm_api_key 가 비어있습니다. 키를 입력하세요."}

        # 본 처리 (연결 실패 등 예외는 응답에 담아 반환)
        try:
            answer = self._run(query, system_message, api_key, session_id, user_id, trace_id)
        except Exception as e:
            answer = _agent_error("LLM", e, query, session_id)

        # Trace 즉시 반영
        flush = getattr(mlflow, "flush_trace_async_logging", None)
        if callable(flush):
            try:
                flush(terminate=False)
            except Exception:
                pass

        return {"aiu_output": answer}


# =============================================================================
# [3] MLflow 등록
# =============================================================================

def register_agent():
    """ModelWrapper 와 llm_conn.json(Artifact)을 MLflow 에 등록한다."""
    if not _is_set(MLFLOW_CONN["tracking_uri"]):
        raise ValueError("MLFLOW_CONN.tracking_uri 가 입력되지 않았습니다.")

    if _is_set(MLFLOW_CONN["username"]):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_CONN["username"]
    if _is_set(MLFLOW_CONN["password"]):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_CONN["password"]

    mlflow.set_tracking_uri(MLFLOW_CONN["tracking_uri"])
    mlflow.set_experiment(MLFLOW_CONN["experiment_name"])

    # 연결 정보를 Artifact 파일로 저장 (서빙 환경에서 load_context 가 읽음)
    llm_conn_file = "llm_conn.json"
    with open(llm_conn_file, "w", encoding="utf-8") as f:
        json.dump(LLM_CONN, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(" MLflow Agent 등록 시작")
    print("=" * 60)

    with mlflow.start_run(run_name="agent-register") as run:
        mlflow.log_params({"llm_model": LLM_CONN["model"], "temperature": LLM_CONN["temperature"]})
        mlflow.set_tags({"app_type": "genai", "stage": "register"})

        # signature 는 주지 않음 (custom_server 가 붙이는 필드와 충돌 방지)
        input_example = {
            "input": [{
                "query":          "안녕하세요",
                "system_message": "당신은 친절한 Agent 입니다.",
                "llm_api_key":    "test-key",
                "session_id":     "sess-example",
            }]
        }

        artifacts = {"llm_conn": llm_conn_file}

        log_kwargs = dict(
            python_model     = ModelWrapper(),
            artifacts        = artifacts,
            input_example    = input_example,
            # pip 버전 고정 필수 (포탈이 'mlflow==' 패턴으로 버전 파싱)
            pip_requirements = [
                "mlflow==3.10.0",
                "cloudpickle==3.1.2",
                "langchain-openai==1.2.1",
                "langchain==1.2.15",
                "pandas==2.3.3",
                "kserve==0.15.0",
            ],
        )

        try:
            model_info = mlflow.pyfunc.log_model(name="genai_agent", **log_kwargs)
        except TypeError:
            model_info = mlflow.pyfunc.log_model(artifact_path="genai_agent", **log_kwargs)

        print(f"  run_id    : {run.info.run_id}")
        print(f"  model_uri : {model_info.model_uri}")

        if _is_set(MLFLOW_CONN["registered_model"]):
            mv = mlflow.register_model(model_info.model_uri, MLFLOW_CONN["registered_model"])
            print(f"  registry  : {MLFLOW_CONN['registered_model']}  v{mv.version}")

    print("\n  등록 완료.")
    print(f"  MLflow UI : {MLFLOW_CONN['tracking_uri']}\n")
    print("=" * 60)


# =============================================================================
# [4] 실행 진입점
# =============================================================================

def safe_main():
    """register_agent() 를 감싸 오류를 보기 좋게 출력한다."""
    try:
        register_agent()
    except ValueError as e:
        print(f"[오류] {e}")
    except Exception as e:
        print(f"[오류] 등록 중 예외 발생: {e}")
        raise


if __name__ == "__main__":
    safe_main()
