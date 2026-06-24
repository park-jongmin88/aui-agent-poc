"""
==============================================================================
 AI-Studio | GenAI Agent (agent.py) - 등록 진입점
==============================================================================
 ModelWrapper(aiu_custom)와 설정(config)을 조립해 MLflow pyfunc 모델로 등록한다.
 agent.py 는 '등록' 만 담당한다. 서빙 로직은 aiu_custom/, 설정은 config.py 에 있다.

 [구조]
   config.py              설정 (ENABLED_ASSETS, MLFLOW_CONN, LLM_*, ASSET_CONN)
   aiu_custom/            서빙 모델 본체
     ├── model_wrapper.py   ModelWrapper 클래스
     └── predict.py         re-export (서빙 진입점)
   assets/                에셋 파이프라인
   mocks/                 목업 데이터

 [작동 순서]
   1. python agent.py -> register_agent()
   2. config 의 설정을 conn.json 으로 저장 -> Artifact
   3. aiu_custom 의 ModelWrapper 를 log_model (code_paths 로 패키지 동봉)
   4. (서빙) custom_server.py 가 로드 -> aiu_custom.predict.ModelWrapper 사용

 [에셋 추가] config.ENABLED_ASSETS 에 이름 추가 + assets/<이름>.py 작성
==============================================================================
"""

import os
import json
import mlflow
import mlflow.pyfunc

from config import (
    ENABLED_ASSETS, MLFLOW_CONN, LLM_BASE_URL, LLM_MODEL, ASSET_CONN,
)
from aiu_custom.predict import ModelWrapper


# =============================================================================
# 유틸
# =============================================================================

def _is_set(value) -> bool:
    """값이 실제로 채워졌는지(TODO/빈값이 아닌지) 판단한다."""
    return isinstance(value, str) and bool(value) and value != "{TODO}"


# =============================================================================
# MLflow 등록
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

        # 서빙 환경에서 import 가능하도록 패키지/설정을 함께 동봉
        #   aiu_custom : ModelWrapper, config : 설정, assets : 파이프라인, mocks : 목업
        log_kwargs = dict(
            python_model     = ModelWrapper(),
            artifacts        = artifacts,
            input_example    = input_example,
            code_paths       = ["aiu_custom", "config.py", "assets", "mocks"],
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
