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


_SENSITIVE_KEYS = ("api_key", "llm_api_key", "apikey", "password", "passwd", "token", "secret", "authorization")

_TRACE_MASKING_REGISTERED = False


def _mask_value(v):
    """dict/list 안을 재귀적으로 돌며 민감 키의 값을 [REDACTED] 로 바꾼다."""
    if isinstance(v, dict):
        out = {}
        for k, val in v.items():
            if any(s in str(k).lower() for s in _SENSITIVE_KEYS):
                out[k] = "[REDACTED]"
            else:
                out[k] = _mask_value(val)
        return out
    if isinstance(v, (list, tuple)):
        return type(v)(_mask_value(x) for x in v)
    return v


def _mask_span(span):
    """span 의 input/output 에서 민감정보를 가린다. (span_processor 용)"""
    try:
        if getattr(span, "inputs", None):
            span.set_inputs(_mask_value(span.inputs))
    except Exception:
        pass
    try:
        if getattr(span, "outputs", None) is not None:
            span.set_outputs(_mask_value(span.outputs))
    except Exception:
        pass


def _register_trace_masking():
    """trace span 에서 민감정보를 가리는 필터를 1회 등록한다."""
    global _TRACE_MASKING_REGISTERED
    if _TRACE_MASKING_REGISTERED:
        return
    try:
        mlflow.tracing.configure(span_processors=[_mask_span])
        _TRACE_MASKING_REGISTERED = True
    except Exception:
        # 구버전 MLflow 에 span_processors 가 없으면 조용히 넘어간다.
        # (이 경우에도 _run 에서 api_key 를 인자에서 뺐으므로 핵심 노출은 막혀 있다.)
        pass


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

        # trace 에 api_key/비밀번호/토큰 등 민감정보가 남지 않도록 마스킹 필터 등록.
        # (모든 span 의 input/output/attribute 를 export 전에 검사해 가린다.)
        _register_trace_masking()

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

    def _run(self, query, system_message, api_key, session_id, user_id, trace_id, prompt_id="", prompt_version=None):
        """api_key 가 trace 인자로 기록되지 않도록, 먼저 리소스를 준비한 뒤
        api_key 를 제외한 인자만 traced 내부 함수로 넘긴다."""
        # 리소스 준비(키 사용)는 trace 바깥에서 수행 → api_key 가 trace 에 안 남는다.
        self._ensure_resources(api_key)
        return self._run_traced(query, system_message, session_id, user_id, trace_id, prompt_id, prompt_version)

    @mlflow.trace(name="agent_pipeline")
    def _run_traced(self, query, system_message, session_id, user_id, trace_id, prompt_id="", prompt_version=None):
        """Trace 에 session/user 기록 후, 켜진 에셋을 순서대로 실행해 답변을 만든다.
        (api_key 는 인자에 없으므로 trace 에 기록되지 않는다.)"""
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

        ctx = new_ctx(query, system_message, prompt_id, prompt_version)
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
        prompt_version = info.get("prompt_version", None)
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

        # 모드: 특정 프롬프트의 버전 목록 조회 (프롬프트 선택 후 버전 고르도록)
        if mode == "list_versions":
            try:
                if "prompt" in self.assets and hasattr(self.assets["prompt"], "list_versions"):
                    versions = self.assets["prompt"].list_versions(prompt_id)
                else:
                    versions = []
            except Exception as e:
                return {"aiu_output": _agent_error("LIST_VERSIONS", e, "", session_id)}
            return {"aiu_output": {"versions": versions}}

        if not api_key:
            return {"aiu_output": "[AGENT ERROR] llm_api_key 가 비어있습니다. 키를 입력하세요."}

        try:
            answer = self._run(query, system_message, api_key, session_id, user_id, trace_id, prompt_id, prompt_version)
        except Exception as e:
            answer = _agent_error("PIPELINE", e, query, session_id)

        flush = getattr(mlflow, "flush_trace_async_logging", None)
        if callable(flush):
            try:
                flush(terminate=False)
            except Exception:
                pass

        return {"aiu_output": answer}
