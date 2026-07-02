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
import logging
import mlflow
import mlflow.pyfunc

from config import (
    ENABLED_ASSETS, MLFLOW_CONN, ASSET_CONN,
)
from aiu_custom.predict import ModelWrapper
from assets.gateway_utils import (
    list_gateway_endpoints, prompt_pick_endpoint,
)


# MLflow 가 프롬프트에 태그를 달려다 권한(403) 으로 실패할 때 나오는 경고를 숨긴다.
# ("Failed to tag prompt ... Permission denied" — 태그는 부가 기능이라 실패해도
#  등록/서빙에는 지장 없으므로, 반복되는 경고 소음만 억제한다.)
logging.getLogger("mlflow.tracking.client").setLevel(logging.ERROR)
logging.getLogger("mlflow.tracking._model_registry.client").setLevel(logging.ERROR)


# 의존성 파일 경로 (이 파일 기준 절대경로 → 실행 위치와 무관하게 찾음)
_REQUIREMENTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")


# =============================================================================
# 유틸
# =============================================================================

def _is_set(value) -> bool:
    """값이 실제로 채워졌는지(TODO/빈값이 아닌지) 판단한다."""
    return isinstance(value, str) and bool(value) and value != "{TODO}"


def _diagnose(e) -> str:
    """에러 내용을 보고 한국어로 원인을 추정한다 (등록 시점 진단용)."""
    s = str(e).lower()
    if "connection" in s or "refused" in s or "max retries" in s or "failed to establish" in s:
        return "MLflow 서버에 연결할 수 없습니다. tracking_uri 주소·포트가 맞는지, 서버가 켜져 있는지 확인하세요."
    if "401" in s or "unauthorized" in s:
        return "인증 실패입니다. MLFLOW_CONN 의 username/password 를 확인하세요."
    if "403" in s or "forbidden" in s or "permission" in s:
        return "권한이 없습니다. 해당 experiment/registry 에 접근 권한이 있는지 확인하세요."
    if "404" in s or "not found" in s or "does not exist" in s:
        return "대상을 찾을 수 없습니다. experiment_name / registered_model 이름을 확인하세요."
    if "timeout" in s or "timed out" in s:
        return "응답 시간 초과입니다. 네트워크 상태나 서버 부하를 확인하세요."
    if "name or service not known" in s or "nodename nor servname" in s or "getaddrinfo" in s:
        return "주소를 찾을 수 없습니다(DNS). tracking_uri 의 호스트명이 올바른지 확인하세요."
    if "ssl" in s or "certificate" in s:
        return "SSL/인증서 문제입니다. https 주소·인증서 설정을 확인하세요."
    return "자동 판별하지 못했습니다. 위의 원본 오류 메시지를 확인하세요."


def _step(name, fn, hint):
    """등록 단계 하나를 실행한다. 실패하면 [어느 항목 / 원본오류 / 한국어진단]을 출력하고 다시 올린다."""
    try:
        return fn()
    except Exception as e:
        import traceback
        print("\n" + "-" * 60)
        print(f"[등록 실패] {name}")
        print(f"  원본 오류 : {type(e).__name__}: {e}")
        print(f"  확인 사항 : {hint}")
        print(f"  추정 원인 : {_diagnose(e)}")
        print("  ---- 상세 traceback ----")
        traceback.print_exc()
        print("  ------------------------")
        print("-" * 60 + "\n")
        raise


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

    _step(
        "MLflow Tracking 연결 (set_tracking_uri)",
        lambda: mlflow.set_tracking_uri(MLFLOW_CONN["tracking_uri"]),
        "config.py 의 MLFLOW_CONN['tracking_uri'] 주소·포트를 확인하세요.",
    )
    _step(
        "Experiment 설정 (set_experiment)",
        lambda: mlflow.set_experiment(MLFLOW_CONN["experiment_name"]),
        "config.py 의 MLFLOW_CONN['experiment_name'] 이름과 접근 권한을 확인하세요.",
    )

    # ── Gateway LLM 선택 (필수) ──────────────────────────────────────
    # 이 프로젝트는 LLM 을 항상 MLflow AI Gateway 를 통해 사용한다.
    # (LLM_BASE_URL/LLM_MODEL 을 config.py 에 직접 적는 방식은 쓰지 않는다.)
    # 등록 시점에 gateway 의 chat 엔드포인트 목록을 조회해 화면에서 고른다.
    # (이 조회/선택 로직은 assets/gateway_utils.py 에 공통화돼 있어
    #  나중에 UI 로 agent 를 구성하게 되면 그 백엔드 로직으로 그대로 쓸 수 있다.)
    def _select_llm_gateway():
        print("\nGateway 엔드포인트 조회 중 ...", end=" ", flush=True)
        endpoints = list_gateway_endpoints(
            MLFLOW_CONN["tracking_uri"], MLFLOW_CONN["username"], MLFLOW_CONN["password"]
        )
        print(f"완료 ({len(endpoints)}개 엔드포인트)")
        if not endpoints:
            raise RuntimeError(
                "gateway 에 등록된 엔드포인트가 없습니다. "
                "MLflow AI Gateway 에 LLM 엔드포인트를 먼저 등록하세요."
            )
        # 타입 필터 없이 전체 목록에서 고른다.
        # (gateway 응답의 타입 필드가 환경마다 달라 chat 필터가 신뢰할 수 없음.
        #  사용자가 LLM 용 엔드포인트를 직접 고르는 것이 확실하다.)
        chosen = prompt_pick_endpoint(endpoints, "LLM gateway 엔드포인트", required=True)
        ep_name = chosen.get("name")
        base_url = f"{MLFLOW_CONN['tracking_uri'].rstrip('/')}/gateway/mlflow/v1"
        print(f"  -> 선택됨: {ep_name}  (base_url={base_url})")
        return base_url, ep_name

    llm_base_url, llm_model = _step(
        "Gateway LLM 엔드포인트 선택",
        _select_llm_gateway,
        "MLflow AI Gateway 에 chat 엔드포인트가 등록돼 있는지, "
        "MLFLOW_CONN 의 접속정보(아이디/비번)가 gateway 조회 권한이 있는지 확인하세요.",
    )

    # 에셋 구성 정보를 Artifact 로 남긴다 (추적/재현용)
    conn_file = "conn.json"
    with open(conn_file, "w", encoding="utf-8") as f:
        json.dump({
            "enabled_assets": ENABLED_ASSETS,
            "llm":  {"base_url": llm_base_url, "model": llm_model},
            "asset_conn": ASSET_CONN,
        }, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(" MLflow Agent 등록 시작")
    print(f"  enabled assets: {ENABLED_ASSETS}")
    print("=" * 60)

    with mlflow.start_run(run_name="agent-register") as run:
        mlflow.log_params({"llm_model": llm_model, "assets": ",".join(ENABLED_ASSETS)})
        mlflow.set_tags({"app_type": "genai", "stage": "register"})

        # [주의] input_example 은 넣지 않는다.
        #   input_example 이 있으면 MLflow 가 log_model 중에 그 예시로 모델을
        #   실제 로드(load_context)+예측(predict)해 시그니처를 추론하는데,
        #   이 과정에서 gateway/MLflow 연결·프롬프트 조회·직렬화가 등록 시점에
        #   일어나 불필요한 경고(403 태그)·로그·직렬화 오류를 유발한다.
        #   서빙엔 필요 없으므로 생략한다. (모델은 서빙 시점에만 실행되면 된다.)

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
            code_paths       = ["aiu_custom", "config.py", "assets", "mocks"],
            # 의존성은 requirements.txt 파일 한 곳에서 관리한다 (이중 관리 방지).
            # MLflow 가 이 파일을 읽어 모델에 박는다. 의존성 추가 시 requirements.txt 만 수정.
            pip_requirements = _REQUIREMENTS_PATH,
        )

        def _do_log_model():
            try:
                return mlflow.pyfunc.log_model(name="genai_agent", **log_kwargs)
            except TypeError:
                return mlflow.pyfunc.log_model(artifact_path="genai_agent", **log_kwargs)

        model_info = _step(
            "모델 업로드 (log_model)",
            _do_log_model,
            "code_paths/requirements, 그리고 MLflow 아티팩트 저장소(S3 등) 접근 권한을 확인하세요.",
        )

        print(f"  run_id    : {run.info.run_id}")
        print(f"  model_uri : {model_info.model_uri}")

        if _is_set(MLFLOW_CONN["registered_model"]):
            mv = _step(
                "모델 레지스트리 등록 (register_model)",
                lambda: mlflow.register_model(model_info.model_uri, MLFLOW_CONN["registered_model"]),
                "config.py 의 MLFLOW_CONN['registered_model'] 이름과 레지스트리 권한을 확인하세요.",
            )
            print(f"  registry  : {MLFLOW_CONN['registered_model']}  v{mv.version}")

    print("\n  등록 완료.\n" + "=" * 60)


def safe_main():
    """register_agent() 를 감싸 오류를 보기 좋게 출력한다.
    (단계별 상세 진단은 _step 에서 이미 출력되므로, 여기서는 요약만)"""
    try:
        register_agent()
    except ValueError as e:
        # 설정값 미입력 등 (TODO 안 채움)
        print(f"[오류] {e}")
    except Exception:
        # _step 에서 이미 항목별 한국어 진단을 출력했음
        print("[중단] 위의 '등록 실패' 항목을 확인해 설정을 고친 뒤 다시 실행하세요.")


if __name__ == "__main__":
    safe_main()


