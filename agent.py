"""
==============================================================================
 AI-Studio | GenAI Agent (agent.py) - 모듈화 버전
==============================================================================
 에셋(assets/*.py)을 조립해 MLflow pyfunc 모델로 등록한다.
 agent.py 는 "무엇을 켤지" 선언하고 "순서대로 실행"만 한다. 로직은 각 에셋에 있다.

 [작동 순서]
   1. (등록) python agent.py -> register_agent()
   2. ENABLED_ASSETS / ASSET_CONN / LLM_CONN 을 conn.json 으로 저장 -> Artifact
   3. ModelWrapper 를 log_model
   4. (서빙) custom_server.py 가 로드 -> load_context() 에서 각 에셋 build()
   5. (호출) predict() -> _run() -> 켜진 에셋들을 순서대로 run()
   6. LangChain autolog + update_current_trace 로 Trace/Session 기록

 [custom_server.py 계약]
   입력  { "input":[{query, system_message, llm_api_key, session_id}], trace_id, ... }
   출력  { "aiu_output": "답변" }

 [에셋 추가] README 참고
   ENABLED_ASSETS 에 이름 추가 + assets/<이름>.py 작성 (+ 필요시 ASSET_CONN 채움)
==============================================================================
"""

import os
import json
import uuid
import mlflow
import mlflow.pyfunc

from assets import new_ctx, load_asset


# =============================================================================
# [0] 켤 에셋 (선언형) - 리스트 순서가 곧 실행 순서
# =============================================================================
# 현재는 prompt -> rag -> tool -> llm 사용. judge 는 구현 후 추가하면 켜진다.
ENABLED_ASSETS = ["prompt", "rag", "tool", "llm"]


# =============================================================================
# [1] 연결 정보 (TODO 를 실제 값으로 채운다)
# =============================================================================
# MLflow 접속 정보
MLFLOW_CONN = {
    "tracking_uri":     TODO,
    "username":         TODO,
    "password":         TODO,
    "experiment_name":  TODO,
    "registered_model": TODO,
}

# LLM 서버 고정값 (api_key 는 호출 시 client 가 보낸 값으로 채워짐)
# base_url
LLM_BASE_URL = TODO
# model 이름
LLM_MODEL = TODO

# 에셋별 연결정보. 켜는 에셋만 채우면 된다. (prompt/llm 은 아래에서 자동 구성)
ASSET_CONN = {
    "prompt": {
        # 프롬프트 로드 실패 시 폴백 시스템 메시지
        "default_system": "당신은 친절한 Agent 입니다.",
        # 프롬프트 별칭 (prompts:/<이름>@<alias>)
        "alias": "production",
    },
    # rag: 목업(mock) 사용 중. Milvus 연결 시 아래 주석 블록으로 교체.
    "rag": {"mode": "mock", "top_k": 3},
    # "rag": {"mode": "milvus", "host": "...", "port": 19530,
    #         "collection": "...", "top_k": 3},
    # tool: 목업(mock) 사용 중. 실제 API 연동 시 mode="real" 로 교체.
    "tool": {"mode": "mock"},
    # "tool": {"mode": "real", "endpoint_url": "...", "api_key": "..."},
    # "judge":{"base_url": "", "model": "", "criteria": ""},
}


# =============================================================================
# [2] 유틸
# =============================================================================

def _is_set(value) -> bool:
    """값이 실제로 채워졌는지(TODO/빈값이 아닌지) 판단한다."""
    return isinstance(value, str) and bool(value) and value != "{TODO}"


def _agent_error(stage: str, exc: Exception, query: str, session_id: str) -> str:
    """예외를 '[AGENT ERROR]' 진단 문자열로 만든다(서버는 죽지 않음)."""
    import traceback
    return (
        "[AGENT ERROR]\n"
        f"stage  : {stage}\n"
        f"type   : {type(exc).__name__}\n"
        f"message: {exc}\n"
        f"query  : {query}\n"
        f"session: {session_id}\n"
        "---- traceback ----\n"
        f"{traceback.format_exc()}"
    )


def _build_asset_conn(name: str, api_key: str, artifacts: dict = None) -> dict:
    """에셋별 build() 에 넘길 conn 을 만든다. llm 은 api_key, rag(mock)은 mock_path 주입."""
    if name == "llm":
        return {
            "base_url":    LLM_BASE_URL,
            "model":       LLM_MODEL,
            "temperature": 0,
            "api_key":     api_key,
        }
    conn = dict(ASSET_CONN.get(name, {}))
    # rag 가 목업 모드면 Artifact 로 패키징된 json 경로를 주입
    if name == "rag" and conn.get("mode", "mock") == "mock" and artifacts:
        conn["mock_path"] = artifacts.get("rag_mock", "")
    # tool 이 목업 모드면 도구 정의 json 경로를 주입
    if name == "tool" and conn.get("mode", "mock") == "mock" and artifacts:
        conn["mock_path"] = artifacts.get("tool_mock", "")
    return conn


# =============================================================================
# [3] ModelWrapper - 서빙되는 모델 본체
# =============================================================================

class ModelWrapper(mlflow.pyfunc.PythonModel):

    def load_context(self, context):
        """서빙 시작 시 1회. autolog 켜고, 켜진 에셋 모듈을 import 해둔다."""
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", ""))
        exp = os.getenv("MLFLOW_EXPERIMENT_NAME", "")
        if exp:
            mlflow.set_experiment(exp)
        mlflow.langchain.autolog()

        # 에셋 모듈 로드 (build 는 api_key 가 필요한 llm 때문에 호출 시점에 수행)
        self.assets = {name: load_asset(name) for name in ENABLED_ASSETS}
        self.resources = {}     # 에셋별 build() 결과 캐시
        self._api_key = None
        # Artifact 경로 보관 (rag 목업 json 등). 키 없으면 빈 dict.
        self._artifacts = dict(getattr(context, "artifacts", {}) or {})

    def _ensure_resources(self, api_key: str):
        """api_key 가 바뀌면 에셋 resource 를 (재)생성한다. llm 만 api_key 영향."""
        if api_key == self._api_key and self.resources:
            return
        self.resources = {
            name: self.assets[name].build(_build_asset_conn(name, api_key, self._artifacts))
            for name in ENABLED_ASSETS
        }
        self._api_key = api_key

    @mlflow.trace(name="agent_pipeline")
    def _run(self, query, system_message, api_key, session_id, user_id, trace_id, prompt_id=""):
        """Trace 에 session/user 기록 후, 켜진 에셋을 순서대로 실행해 답변을 만든다."""
        # Sessions 탭은 metadata 표준키(mlflow.trace.session/user)를 읽는다 (mlflow 3.10)
        try:
            mlflow.update_current_trace(
                metadata={
                    "mlflow.trace.session": session_id,
                    "mlflow.trace.user":    user_id or "aiu-user",
                    "app_type":             "genai",
                },
                tags={"trace_id": trace_id or "", "prompt_id": prompt_id or ""},
            )
        except Exception:
            pass

        self._ensure_resources(api_key)

        # 에셋 파이프라인 실행 (ctx 를 순서대로 통과시킨다)
        ctx = new_ctx(query, system_message, prompt_id)
        for name in ENABLED_ASSETS:
            ctx = self.assets[name].run(ctx, self.resources[name])

        return ctx.get("answer", "")

    def predict(self, context, model_input, params=None):
        """custom_server 진입점. input[0] 파싱 -> _run -> {"aiu_output":...} 반환."""
        try:
            items = model_input["input"]
        except (TypeError, KeyError):
            items = model_input if isinstance(model_input, list) else [model_input]

        trace_id = model_input.get("trace_id", "") if isinstance(model_input, dict) else ""

        info = items[0] if items else {}
        mode           = info.get("mode", "")
        query          = str(info.get("query", "")).strip()
        system_message = info.get("system_message", "")
        prompt_id      = info.get("prompt_id", "")
        api_key        = info.get("llm_api_key", "")
        session_id     = info.get("session_id") or trace_id or "sess-" + uuid.uuid4().hex[:8]
        user_id        = info.get("user_id")

        # 모드: 프롬프트 목록 조회 (대화 시작 전 client 가 고르도록)
        if mode == "list_prompts":
            try:
                names = self.assets["prompt"].list_prompts() if "prompt" in self.assets else []
            except Exception as e:
                return {"aiu_output": _agent_error("LIST_PROMPTS", e, "", session_id)}
            return {"aiu_output": {"prompts": names}}

        if not api_key:
            return {"aiu_output": "[AGENT ERROR] llm_api_key 가 비어있습니다. 키를 입력하세요."}

        try:
            answer = self._run(query, system_message, api_key, session_id, user_id, trace_id, prompt_id)
        except Exception as e:
            answer = _agent_error("PIPELINE", e, query, session_id)

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
    """ModelWrapper 와 conn.json(Artifact)을 MLflow 에 등록한다."""
    if not _is_set(MLFLOW_CONN["tracking_uri"]):
        raise ValueError("MLFLOW_CONN.tracking_uri 가 입력되지 않았습니다.")

    if _is_set(MLFLOW_CONN["username"]):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_CONN["username"]
    if _is_set(MLFLOW_CONN["password"]):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_CONN["password"]

    mlflow.set_tracking_uri(MLFLOW_CONN["tracking_uri"])
    mlflow.set_experiment(MLFLOW_CONN["experiment_name"])

    # 에셋 구성 정보를 Artifact 로 남긴다 (추적/재현용)
    conn_file = "conn.json"
    with open(conn_file, "w", encoding="utf-8") as f:
        json.dump({
            "enabled_assets": ENABLED_ASSETS,
            "llm":  {"base_url": LLM_BASE_URL, "model": LLM_MODEL},
            "asset_conn": ASSET_CONN,
        }, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(" MLflow Agent 등록 시작")
    print(f"  enabled assets: {ENABLED_ASSETS}")
    print("=" * 60)

    with mlflow.start_run(run_name="agent-register") as run:
        mlflow.log_params({"llm_model": LLM_MODEL, "assets": ",".join(ENABLED_ASSETS)})
        mlflow.set_tags({"app_type": "genai", "stage": "register"})

        input_example = {
            "input": [{
                "query":          "안녕하세요",
                "system_message": "당신은 친절한 Agent 입니다.",
                "llm_api_key":    "test-key",
                "session_id":     "sess-example",
            }]
        }

        # Artifact 구성: conn.json + (rag/tool 목업이면) 각 json
        artifacts = {"conn": conn_file}
        rag_conn = ASSET_CONN.get("rag", {})
        if "rag" in ENABLED_ASSETS and rag_conn.get("mode", "mock") == "mock":
            mock_json = os.path.join("mocks", "rag_documents.json")
            if os.path.exists(mock_json):
                artifacts["rag_mock"] = mock_json
        tool_conn = ASSET_CONN.get("tool", {})
        if "tool" in ENABLED_ASSETS and tool_conn.get("mode", "mock") == "mock":
            tool_json = os.path.join("mocks", "tool_apis.json")
            if os.path.exists(tool_json):
                artifacts["tool_mock"] = tool_json

        # 코드 디렉토리(assets 포함)를 함께 패키징해야 서빙에서 import 가능
        log_kwargs = dict(
            python_model     = ModelWrapper(),
            artifacts        = artifacts,
            input_example    = input_example,
            code_paths       = ["assets"],
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

    print("\n  등록 완료.\n" + "=" * 60)


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
