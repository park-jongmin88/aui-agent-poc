"""
==============================================================================
 config.py - 에이전트 설정 모음
==============================================================================
 등록(agent.py)과 서빙(aiu_custom/model_wrapper.py)이 함께 참조하는 설정.
 한 곳에서 관리해 순환 import 없이 양쪽이 같은 값을 본다.

 TODO 표시된 값은 실제 환경값으로 채운다.
==============================================================================
"""

import os

# =============================================================================
# [0] 켤 에셋 (선언형) - 리스트 순서가 곧 실행 순서
# =============================================================================
# 현재는 prompt -> rag -> tool -> llm 사용.
ENABLED_ASSETS = ["prompt", "rag", "tool", "llm"]


# =============================================================================
# [1] MLflow 접속 정보
# =============================================================================
MLFLOW_CONN = {
    "tracking_uri":     TODO,
    "username":         TODO,
    "password":         TODO,
    "experiment_name":  TODO,
    "registered_model": TODO,
}


# =============================================================================
# [2] LLM 서버 고정값 (api_key 는 호출 시 client 가 보낸 값으로 채워짐)
# =============================================================================
# base_url
LLM_BASE_URL = TODO
# model 이름
LLM_MODEL = TODO


# =============================================================================
# [3] 에셋별 연결정보. 켜는 에셋만 채우면 된다. (prompt/llm 은 자동 구성)
# =============================================================================
ASSET_CONN = {
    "prompt": {
        # 프롬프트 로드 실패 시 폴백 시스템 메시지
        "default_system": "당신은 친절한 Agent 입니다.",
        # 프롬프트 별칭 (prompts:/<이름>@<alias>)
        "alias": "production",
    },
    # rag: 목업(mock) 사용 중. Milvus 연결 시 mode 를 "milvus" 로 바꾼다.
    "rag": {"mode": "mock", "top_k": 3},
    # --- 실제 Milvus 연결 (iflow_aiu_collection, default DB, vector 1024 / L2) ---
    # 자격증명은 코드에 박지 말고 환경변수(또는 k8s Secret)로 주입한다.
    # "rag": {
    #     "mode":       "milvus",
    #     "uri":        os.getenv("MILVUS_URI", ""),
    #     "user":       os.getenv("MILVUS_USER", ""),
    #     "password":   os.getenv("MILVUS_PASSWORD", ""),
    #     "db_name":    "default",
    #     "collection": "iflow_aiu_collection",
    #     "top_k":      3,
    #     # TODO 임베딩 모델 확인: 적재 때와 동일해야 함. 현재 기본값 bge-m3(1024).
    #     #      iflow 적재 담당자/스크립트에 실제 모델 확인 후 교체.
    #     "embed_model": os.getenv("RAG_EMBED_MODEL", "BAAI/bge-m3"),
    # },
    # tool: 목업(mock) 사용 중. 실제 API 연동 시 mode="real" 로 교체.
    "tool": {"mode": "mock"},
    # "tool": {"mode": "real", "endpoint_url": "...", "api_key": "..."},
    # judge 는 서빙에서 분리됨. 평가는 judge_eval.py (make_judge) 로 별도 실행.
}
