"""
==============================================================================
 AI-Studio | GenAI Agent (agent.py)
==============================================================================
 LLM 기반 GenAI Agent 를 MLflow pyfunc 모델로 "등록" 한다.
 등록된 모델은 custom_server.py(서빙 이미지)가 감싸 KServe 로 서빙한다.

 [작동 순서]
   1. (등록) python agent.py 실행 -> register_agent() 호출
   2. LLM_CONN 을 llm_conn.json 으로 저장 -> Artifact 로 함께 등록
   3. ModelWrapper 를 MLflow pyfunc 모델로 log_model
   4. (서빙) custom_server.py 가 모델 로드 -> load_context() 1회 실행
   5. (호출) custom_server 가 predict() 호출:
        입력  { "input":[{query, system_message, llm_api_key, session_id}], trace_id, pis_name, logger ... }
        출력  { "aiu_output": "답변" }
   6. predict() -> _run() -> call_llm() 순으로 실행되며 Trace/Session 기록

 [custom_server.py 계약]
   - 입력 핵심은 model_input["input"][0] 의 dict
   - 출력은 반드시 {"aiu_output": ...} (이 키 없으면 서버측 예외)
==============================================================================
"""

import os
import json
import uuid
import mlflow
import mlflow.pyfunc
from mlflow.entities import SpanType


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

# base_url / model 은 서버 고정값. api_key 는 호출 시 client 가 보낸 값을 우선 사용.
LLM_CONN = {
    "base_url":    TODO,
    "model":       TODO,
    "temperature": 0.2,
}


# =============================================================================
# [1] 유틸
# =============================================================================

def _is_set(value) -> bool:
    """값이 실제로 채워졌는지(TODO/빈값이 아닌지) 판단한다."""
    return isinstance(value, str) and bool(value) and value != "{TODO}"


def _clean_text(s: str) -> str:
    """LLM 응답의 깨진 surrogate 문자를 제거해 안전한 문자열로 만든다."""
    if not isinstance(s, str):
        return s
    return s.encode("utf-8", "surrogatepass").decode("utf-8", "ignore")


def _agent_error(stage: str, exc: Exception, question: str, session_id: str) -> str:
    """예외를 '[AGENT ERROR]' 로 시작하는 진단 문자열로 만든다(서버는 죽지 않음)."""
    import traceback
    tb = traceback.format_exc()
    return (
        "[AGENT ERROR]\n"
        f"stage  : {stage}\n"
        f"type   : {type(exc).__name__}\n"
        f"message: {exc}\n"
        f"question: {question}\n"
        f"session : {session_id}\n"
        "---- traceback ----\n"
        f"{tb}"
    )


# =============================================================================
# [2] LLM 호출
# =============================================================================

@mlflow.trace(name="llm_call", span_type=SpanType.LLM)
def call_llm(messages: list, llm_conn: dict, api_key: str) -> str:
    """메시지 배열을 Qwen(OpenAI 호환 API)에 보내 답변 텍스트를 받는다. (LLM span)"""
    from openai import OpenAI
    client = OpenAI(base_url=llm_conn["base_url"], api_key=api_key)
    resp = client.chat.completions.create(
        model=llm_conn["model"],
        messages=messages,
        temperature=llm_conn.get("temperature", 0.2),
    )
    return _clean_text(resp.choices[0].message.content)


# =============================================================================
# [3] ModelWrapper - 서빙되는 모델 본체
# =============================================================================

class ModelWrapper(mlflow.pyfunc.PythonModel):

    def load_context(self, context):
        """서빙 시작 시 1회 호출. Artifact(llm_conn.json)를 읽어 self 에 보관한다."""
        with open(context.artifacts["llm_conn"], "r", encoding="utf-8") as f:
            self.llm_conn = json.load(f)

    @mlflow.trace(name="agent_pipeline", span_type=SpanType.AGENT)
    def _run(self, query: str, system_message: str, api_key: str,
             session_id: str, user_id: str, trace_id: str) -> str:
        """질문 1건 처리. Trace 에 session/user 기록 후 system+user 메시지로 LLM 호출. (AGENT span)"""
        # Trace 에 session/user 기록 (같은 session_id 끼리 Sessions 탭에 묶임)
        try:
            mlflow.update_current_trace(
                user=user_id or "aiu-user",
                session_id=session_id,
                tags={"session_id": session_id, "trace_id": trace_id or ""},
                metadata={"app_type": "genai"},
            )
        except Exception:
            pass

        # 메시지 구성: system -> user
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": query})

        return call_llm(messages, self.llm_conn, api_key)

    def predict(self, context, model_input, params=None):
        """custom_server 진입점. input[0] 에서 query 등을 꺼내 _run() 실행 후 {"aiu_output":...} 반환."""
        # custom_server 계약: model_input["input"] = [{query, system_message, llm_api_key, session_id}]
        try:
            items = model_input["input"]
        except (TypeError, KeyError):
            # 폴백: dict 가 아니거나 input 키가 없으면 그대로 리스트로 간주
            items = model_input if isinstance(model_input, list) else [model_input]

        trace_id = ""
        if isinstance(model_input, dict):
            trace_id = model_input.get("trace_id", "")

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
# [4] MLflow 등록
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
        mlflow.log_params({
            "llm_model":   LLM_CONN["model"],
            "temperature": LLM_CONN["temperature"],
        })
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
            pip_requirements = ["mlflow==3.10.0", "openai==2.43.0", "kserve==0.15.0"],
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
# [5] 실행 진입점
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
