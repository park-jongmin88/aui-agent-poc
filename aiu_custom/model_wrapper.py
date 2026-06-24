"""
==============================================================================
 aiu_custom/model_wrapper.py - 서빙되는 모델 본체 (ModelWrapper)
==============================================================================
 custom_server.py(서빙 이미지)가 로드하는 MLflow pyfunc 모델.
 설정은 config.py 에서, 파이프라인 로직은 assets/ 에서 가져온다.

 [작동]
   load_context() : 서빙 시작 시 1회. autolog + 에셋 모듈 로드 + 워밍업
   predict()      : custom_server 진입점. input[0] 파싱 -> _run -> {"aiu_output":...}
   _run()         : 켜진 에셋을 순서대로 실행 (prompt -> rag -> tool -> llm)
==============================================================================
"""

import os
import uuid
import mlflow
import mlflow.pyfunc

from assets import new_ctx, load_asset
from config import ENABLED_ASSETS, LLM_BASE_URL, LLM_MODEL, ASSET_CONN


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
    """에셋별 build() 에 넘길 conn 을 만든다. llm 은 api_key, rag/tool(mock)은 mock_path 주입."""
    if name == "llm":
        return {
            "base_url":    LLM_BASE_URL,
            "model":       LLM_MODEL,
            "temperature": 0,
            "api_key":     api_key,
        }
    conn = dict(ASSET_CONN.get(name, {}))
    if name == "rag" and conn.get("mode", "mock") == "mock" and artifacts:
        conn["mock_path"] = artifacts.get("rag_mock", "")
    if name == "tool" and conn.get("mode", "mock") == "mock" and artifacts:
        conn["mock_path"] = artifacts.get("tool_mock", "")
    return conn


class ModelWrapper(mlflow.pyfunc.PythonModel):

    def load_context(self, context):
        """서빙 시작 시 1회. autolog 켜고, 켜진 에셋 모듈을 import 해둔다."""
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", ""))
        exp = os.getenv("MLFLOW_EXPERIMENT_NAME", "")
        if exp:
            mlflow.set_experiment(exp)
        mlflow.langchain.autolog()

        self.assets = {name: load_asset(name) for name in ENABLED_ASSETS}
        self.resources = {}
        self._api_key = None
        self._artifacts = dict(getattr(context, "artifacts", {}) or {})

        # 워밍업: MLflow 첫 연결(콜드 스타트)을 서빙 시작 시점으로 옮겨 첫 질문 504 예방.
        try:
            if "prompt" in self.assets and hasattr(self.assets["prompt"], "list_prompts"):
                self.assets["prompt"].list_prompts()
        except Exception:
            pass

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
