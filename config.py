"""
==============================================================================
 config.py - 에이전트 설정
==============================================================================
 ★ 채우는 곳은 아래 [입력란] 한 군데입니다. 그 아래 [조립부]는 건드리지 않습니다.

 순서:
   [입력란]  사용자가 실제로 채우는 값 (TODO 를 실제값으로)
   [조립부]  위 입력값을 코드가 쓰는 형태로 묶음 (수정 불필요)

 - TODO 는 실제 환경값으로 바꿉니다. 각 줄 옆 주석에 예시가 있습니다.
 - 키/비밀번호 등 민감정보는 코드에 직접 쓰지 말고 환경변수로 주입합니다.
   (아래 입력란에서 os.getenv(...) 로 표시된 항목)
==============================================================================
"""

import os

# #############################################################################
# [입력란] ★ 여기만 채우세요
# #############################################################################

# ── 1. MLflow 정보 (필수) ───────────────────────────────────────────────────
MLFLOW_TRACKING_URI = TODO   # 예: "http://mlflow.도메인.com"
MLFLOW_USERNAME     = TODO
MLFLOW_PASSWORD     = TODO
MLFLOW_EXPERIMENT   = TODO   # 예: "aiu-agent"
MLFLOW_MODEL_NAME   = TODO   # 등록 모델명. 예: "aiu-agent-model"

# ── 2. LLM 정보 (필수) ──────────────────────────────────────────────────────
#   api_key 는 호출 시 client 가 보낸 값으로 채워지므로 여기 두지 않습니다.
LLM_BASE_URL = TODO          # 예: "http://llm.도메인.com/v1"
LLM_MODEL    = TODO          # 예: "gpt-4o" 또는 사내 등록 모델명

# ── 3. 사용할 에셋 (실행 순서대로) ──────────────────────────────────────────
#   여기 적은 에셋만 동작합니다. 빼면 그 에셋 정보는 채워져 있어도 무시됩니다.
ENABLED_ASSETS = ["prompt", "rag", "tool", "llm"]

# ── 4. 에셋별 입력값 (위 ENABLED_ASSETS 에서 켠 것만 채우면 됨) ──────────────

# 4-1) prompt
PROMPT_DEFAULT_SYSTEM = "당신은 친절한 Agent 입니다."   # 프롬프트 로드 실패 시 폴백

# 4-2) rag  ── 기본 "milvus"(실제 벡터DB). 임시로 목업 쓰려면 "mock".
RAG_MODE  = "milvus"        # 기본 "milvus"(실제 벡터DB). 임시 목업은 "mock"
RAG_TOP_K = 3
#   Milvus / 임베딩 입력값 (milvus 모드에서 사용)
#   Milvus 접속 (키/비번은 환경변수로 주입)
MILVUS_URI        = os.getenv("MILVUS_URI", TODO)        # 예: "http://milvus.도메인.com:19530"
MILVUS_USER       = os.getenv("MILVUS_USER", "")
MILVUS_PASSWORD   = os.getenv("MILVUS_PASSWORD", "")
MILVUS_COLLECTION = "iflow_aiu_collection"               # 적재해 둔 컬렉션
#   임베딩 서버 (문서 적재 때 쓴 그 서버 = LLM 과 분리된 서브도메인)
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", TODO)       # 예: "http://embedding.llm.도메인.com/v1"
EMBED_API_KEY  = os.getenv("EMBED_API_KEY", "")          # LLM 키와 형태 동일(값은 별도일 수 있음)
EMBED_MODEL    = "bge-m3"                                # 적재 때와 동일해야 검색 정확

# 4-3) tool  ── "mock"=목업 / "real"=실제 API
TOOL_MODE = "mock"           # "mock" | "real"
# TOOL_ENDPOINT = os.getenv("TOOL_ENDPOINT", TODO)
# TOOL_API_KEY  = os.getenv("TOOL_API_KEY", "")


# #############################################################################
# [조립부] 위 입력값을 코드가 쓰는 형태로 묶음 — 수정할 필요 없음
# #############################################################################

MLFLOW_CONN = {
    "tracking_uri":     MLFLOW_TRACKING_URI,
    "username":         MLFLOW_USERNAME,
    "password":         MLFLOW_PASSWORD,
    "experiment_name":  MLFLOW_EXPERIMENT,
    "registered_model": MLFLOW_MODEL_NAME,
}

ASSET_CONN = {
    "prompt": {
        "default_system": PROMPT_DEFAULT_SYSTEM,
    },
    "rag": {
        "mode":           RAG_MODE,
        "top_k":          RAG_TOP_K,
        # milvus 일 때 사용
        "uri":            MILVUS_URI,
        "user":           MILVUS_USER,
        "password":       MILVUS_PASSWORD,
        "db_name":        "default",
        "collection":     MILVUS_COLLECTION,
        "nprobe":         16,                 # IVF_FLAT 검색 파라미터 (nlist=128 기준)
        "embed_base_url": EMBED_BASE_URL,
        "embed_api_key":  EMBED_API_KEY,
        "embed_model":    EMBED_MODEL,
    },
    "tool": {
        "mode":           TOOL_MODE,
        # "endpoint_url": TOOL_ENDPOINT,
        # "api_key":      TOOL_API_KEY,
    },
    # judge 는 서빙에서 분리됨. 평가는 judge_eval.py (make_judge) 로 별도 실행.
}
