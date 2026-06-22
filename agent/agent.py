"""
==============================================================================
 AI-Studio  |  GenAI Agent
==============================================================================

 [목적]
   LLM Agent 를 MLflow 에 등록하고
   API 서빙 후 Trace / Session 이 기록되는 구조를 정의한다.

 [실행]
   python agent.py
   → MLflow 에 Agent 등록만 수행 (대화 실행 없음)
   → 서빙 후 agent_client.py 로 API 호출

 [서빙]
   mlflow models serve -m "models://<registered_model>/1" --port 5001

 [입력 스키마]
   { "inputs": [{
       "question":   "질문 텍스트",
       "session_id": "sess-xxxxxxxx",
       "user_id":    "user-001",
       "history":    "[{\"role\":\"user\",\"content\":\"...\"}]"
   }]}

 [출력 스키마]
   [{ "question": "...", "answer": "...", "session_id": "..." }]

 [에셋 추가 시 참고]
   서빙 환경에서는 원본 파이썬 파일이 없으므로
   모든 연결 정보는 Artifact 로 등록해야 한다.
   load_context() 에서 로드해서 self 에 저장 후 사용.

   현재 등록 Artifact:
     - llm_conn.json  ← LLM 연결 정보

   에셋 추가 시:
     # artifacts 에 추가
     # "rag_conn":    "rag_conn.json"
     # "tool_conn":   "tool_conn.json"
     # "prompt_conf": "prompt_conf.json"

     # load_context() 에서 추가 로드
     # self.rag_conn  = json.load(open(context.artifacts["rag_conn"]))
     # self.tool_conn = json.load(open(context.artifacts["tool_conn"]))
==============================================================================
"""

import os
import json
import uuid
import mlflow
import mlflow.pyfunc
from mlflow.models import infer_signature


# =============================================================================
# [0-A]  MLflow 연결 정보  ← TODO 를 실제 값으로 채운다
# =============================================================================
MLFLOW_CONN = {
    "tracking_uri":     TODO,   # 예: http://mlflow.internal:5000
    "username":         TODO,   # MLflow 접속 ID
    "password":         TODO,   # MLflow 접속 PW
    "experiment_name":  TODO,   # 등록할 Experiment 이름
    "registered_model": TODO,   # 모델 레지스트리 등록명
}


# =============================================================================
# [0-B]  LLM 연결 정보  ← TODO 를 실제 값으로 채운다
# =============================================================================
LLM_CONN = {
    "base_url":    TODO,   # 예: http://qwen.internal:8000/v1
    "api_key":     TODO,   # 인증 키 (없으면 TODO 그대로)
    "model":       TODO,   # 예: qwen2.5-7b-instruct
    "temperature": 0.2,
}

# 에셋 추가 시 연결 정보 형태 참고
# RAG_CONN = {
#     "vector_db":  TODO,   # 예: milvus / opensearch
#     "host":       TODO,
#     "port":       TODO,
#     "collection": TODO,
#     "top_k":      3,
# }
# TOOL_CONN = {
#     "endpoint_url": TODO,
#     "api_key":      TODO,
# }
# PROMPT_CONF = {
#     "name":    TODO,
#     "version": TODO,
#     "system":  TODO,
# }


# =============================================================================
# [1]  유틸
# =============================================================================
def _is_set(value) -> bool:
    """값이 실제로 채워졌는지 확인."""
    return isinstance(value, str) and bool(value) and value != "{TODO}"


def _clean_text(s: str) -> str:
    """
    한글 응답의 surrogate 문자 제거.
    Qwen 응답이 바이트 경계에서 잘리면 surrogate 가 생겨
    MLflow Trace 저장 시 utf-8 오류가 발생한다.
    """
    if not isinstance(s, str):
        return s
    return s.encode("utf-8", "surrogatepass").decode("utf-8", "ignore")


# =============================================================================
# [2]  LLM 호출
# =============================================================================
def call_llm(messages: list, llm_conn: dict) -> str:
    """사내 Qwen (OpenAI 호환 API) 호출."""
    api_key = llm_conn["api_key"] if _is_set(llm_conn.get("api_key", "")) else "not-needed"

    try:
        from openai import OpenAI
        client = OpenAI(base_url=llm_conn["base_url"], api_key=api_key)
        resp = client.chat.completions.create(
            model=llm_conn["model"],
            messages=messages,
            temperature=llm_conn.get("temperature", 0.2),
        )
        return _clean_text(resp.choices[0].message.content)

    except ImportError:
        # openai 패키지 없을 때 urllib 폴백
        import urllib.request
        url = llm_conn["base_url"].rstrip("/") + "/chat/completions"
        payload = json.dumps({
            "model":       llm_conn["model"],
            "messages":    messages,
            "temperature": llm_conn.get("temperature", 0.2),
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        if _is_set(llm_conn.get("api_key", "")):
            req.add_header("Authorization", f"Bearer {llm_conn['api_key']}")
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return _clean_text(data["choices"][0]["message"]["content"])


# =============================================================================
# [3]  ModelWrapper  —  MLflow PythonModel (pyfunc)
# =============================================================================
class ModelWrapper(mlflow.pyfunc.PythonModel):
    """
    MLflow pyfunc 서빙을 위한 Wrapper.
    서빙 환경에서 원본 파이썬 파일이 없으므로
    모든 연결 정보는 load_context() 에서 Artifact 로 로드한다.
    """

    def load_context(self, context):
        """서빙 시 MLflow 가 자동 호출. Artifact 에서 연결 정보 로드."""
        # LLM 연결 정보 로드
        with open(context.artifacts["llm_conn"], "r", encoding="utf-8") as f:
            self.llm_conn = json.load(f)

        # 에셋 추가 시 여기에 로드 추가
        # with open(context.artifacts["rag_conn"], "r") as f:
        #     self.rag_conn = json.load(f)
        # with open(context.artifacts["tool_conn"], "r") as f:
        #     self.tool_conn = json.load(f)
        # with open(context.artifacts["prompt_conf"], "r") as f:
        #     self.prompt_conf = json.load(f)

    @mlflow.trace(name="agent_pipeline", span_type="CHAIN")
    def _run(self, question: str, history: list = None,
             session_id: str = None, user_id: str = None) -> dict:
        """
        파이프라인 실행.
        각 turn 을 session_id 로 묶어 MLflow Sessions 탭에 기록.
        """
        # ── Trace 에 session / user 태그 추가
        if session_id or user_id:
            meta = {}
            if session_id:
                meta["mlflow.trace.session"] = session_id
            if user_id:
                meta["mlflow.trace.user"] = user_id
            try:
                mlflow.update_current_trace(metadata=meta)
            except TypeError:
                try:
                    mlflow.update_current_trace(tags=meta)
                except Exception:
                    pass
            except Exception:
                pass

        # ── 메시지 구성 (history + 질문)
        messages = list(history) if history else []

        # 에셋 추가 시 여기에 System Prompt / RAG / Tool 결과 추가
        # if self.prompt_conf.get("system"):
        #     messages.insert(0, {"role": "system", "content": self.prompt_conf["system"]})
        # context_text = rag_search(question, self.rag_conn)
        # tool_result  = call_tool(question, self.tool_conn)

        messages.append({"role": "user", "content": question})

        # ── LLM 호출
        answer = call_llm(messages, self.llm_conn)

        return {
            "question":   question,
            "answer":     answer,
            "session_id": session_id,
        }

    def predict(self, context, model_input, params=None):
        """
        MLflow 서빙 인터페이스.

        입력 필드:
          question   : 질문 텍스트
          session_id : 대화 세션 ID (없으면 자동 생성)
          user_id    : 사용자 ID (선택)
          history    : 이전 대화 JSON 문자열
                       예) "[{\"role\":\"user\",\"content\":\"안녕\"}]"

        입력 형식 (KServe):
          { "input": ["<JSON 문자열>"] }
          JSON 문자열 안에 question / session_id / user_id / history 포함.

        출력:
          ["답변 문자열", ...]   ← 답변만 문자열 리스트로 반환
          (Trace / Session 은 _run() 안에서 기록되므로 영향 없음)
        """
        # ── 입력 정규화: {"input": [...]} / DataFrame / dict / list 모두 대응
        if hasattr(model_input, "to_dict"):
            # DataFrame → records
            recs = model_input.to_dict("records")
            raw_items = [r.get("input", r) for r in recs]
        elif isinstance(model_input, dict):
            raw_items = model_input.get("input", [model_input])
        else:
            raw_items = list(model_input)

        params    = params or {}
        p_session = params.get("session_id")
        p_user    = params.get("user_id")

        results = []
        for item in raw_items:
            # item 이 JSON 문자열이면 파싱, dict 면 그대로, 그 외엔 question 으로 취급
            if isinstance(item, str):
                try:
                    payload = json.loads(item)
                    if not isinstance(payload, dict):
                        payload = {"question": item}
                except (json.JSONDecodeError, TypeError):
                    payload = {"question": item}
            elif isinstance(item, dict):
                payload = item
            else:
                payload = {"question": str(item)}

            q   = payload.get("question", "")
            sid = payload.get("session_id", p_session) or "sess-" + uuid.uuid4().hex[:8]
            uid = payload.get("user_id", p_user)

            # history: list 또는 JSON 문자열 모두 대응
            raw_history = payload.get("history", [])
            if isinstance(raw_history, str):
                try:
                    history = json.loads(raw_history)
                except (json.JSONDecodeError, TypeError):
                    history = []
            else:
                history = raw_history or []

            out = self._run(q, history=history, session_id=sid, user_id=uid)
            # 답변 문자열만 반환
            results.append(out["answer"])

        return results


# =============================================================================
# [4]  MLflow 등록
# =============================================================================
def register_agent():
    """ModelWrapper 를 MLflow 에 등록한다."""

    # MLflow 연결
    if not _is_set(MLFLOW_CONN["tracking_uri"]):
        raise ValueError("MLFLOW_CONN.tracking_uri 가 입력되지 않았습니다.")

    if _is_set(MLFLOW_CONN["username"]):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_CONN["username"]
    if _is_set(MLFLOW_CONN["password"]):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_CONN["password"]

    mlflow.set_tracking_uri(MLFLOW_CONN["tracking_uri"])
    mlflow.set_experiment(MLFLOW_CONN["experiment_name"])

    # Artifact 파일 생성 — 연결 정보 저장
    llm_conn_file = "llm_conn.json"
    with open(llm_conn_file, "w", encoding="utf-8") as f:
        json.dump(LLM_CONN, f, ensure_ascii=False, indent=2)

    # 에셋 추가 시 Artifact 파일 추가
    # rag_conn_file  = "rag_conn.json"
    # tool_conn_file = "tool_conn.json"
    # with open(rag_conn_file, "w")  as f: json.dump(RAG_CONN,  f)
    # with open(tool_conn_file, "w") as f: json.dump(TOOL_CONN, f)

    print("=" * 60)
    print(" MLflow Agent 등록 시작")
    print("=" * 60)

    with mlflow.start_run(run_name="agent-register") as run:

        mlflow.log_params({
            "llm_model":   LLM_CONN["model"],
            "temperature": LLM_CONN["temperature"],
        })
        mlflow.set_tags({
            "app_type": "genai",
            "stage":    "register",
        })

        # 서명 — KServe { "input": ["<JSON 문자열>"] } 형식
        example_inner = json.dumps({
            "question":   "안녕하세요",
            "session_id": "sess-example",
            "user_id":    "user-001",
            "history":    [],
        }, ensure_ascii=False)
        example = {"input": [example_inner]}
        signature = infer_signature(
            example,
            ["답변 문자열 예시"],
        )

        # Artifact 등록 — 에셋 추가 시 여기에 추가
        artifacts = {
            "llm_conn": llm_conn_file,
            # "rag_conn":    rag_conn_file,
            # "tool_conn":   tool_conn_file,
            # "prompt_conf": prompt_conf_file,
        }

        log_kwargs = dict(
            python_model     = ModelWrapper(),
            artifacts        = artifacts,
            signature        = signature,
            input_example    = example,
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

    print()
    print("  등록 완료.")
    print(f"  MLflow UI : {MLFLOW_CONN['tracking_uri']}")
    print()
    print("  서빙 명령어:")
    print(f"  mlflow models serve -m 'models://{MLFLOW_CONN['registered_model']}/1' --port 5001")
    print("=" * 60)


# =============================================================================
# [5]  실행
# =============================================================================
def safe_main():
    try:
        register_agent()
    except ValueError as e:
        print(f"[오류] {e}")
    except Exception as e:
        print(f"[오류] 등록 중 예외 발생: {e}")
        raise


if __name__ == "__main__":
    safe_main()
