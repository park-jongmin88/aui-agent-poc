"""
==============================================================================
 evaluate.py - 등록된 Judge 로 trace 를 평가하는 스크립트
==============================================================================
 judge_register.py 로 등록해 둔 judge 를 골라 최근 trace 들을 평가한다.
 결과는 각 trace 에 Feedback(점수)으로 부착된다.

 [흐름]
   1. MLflow 연결 (+ gateway 호출용 Basic 인증)
   2. 등록된 judge 목록 조회 → 숫자로 선택
      (LLM 모델은 judge 가 등록 시 이미 갖고 있으므로 여기서 선택하지 않는다)
   3. 최근 trace 수집 → mlflow.genai.evaluate 로 채점

 [사용]
   1. 아래 [입력] 채운다 (MLflow 정보).
   2. python evaluate.py

 요구: pip install mlflow litellm
==============================================================================
"""

import os
import sys
import base64
import logging

import mlflow

# judge 등록 스크립트와 인증 로직을 공유한다 (litellm Basic 인증 패치 등).
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

# MLflow 자동 태깅 403 경고 등 반복 경고 억제 (부가기능 실패라 평가엔 지장 없음).
logging.getLogger("mlflow.tracking.client").setLevel(logging.ERROR)
logging.getLogger("mlflow.tracking._model_registry.client").setLevel(logging.ERROR)
logging.getLogger("mlflow.models.evaluation").setLevel(logging.ERROR)
logging.getLogger("mlflow.genai").setLevel(logging.ERROR)


# #############################################################################
# [입력] ★ MLflow 정보만 채우세요
# #############################################################################

MLFLOW_TRACKING_URI = TODO   # 예: "http://mlflow.도메인.com"
MLFLOW_USERNAME     = TODO
MLFLOW_PASSWORD     = TODO
MLFLOW_EXPERIMENT   = TODO   # trace 가 쌓이는 experiment. 예: "aiu-agent"

# 평가할 최근 trace 최대 개수
MAX_TRACES = 50


# #############################################################################
# 공통 유틸
# #############################################################################

def _is_set(v) -> bool:
    return isinstance(v, str) and bool(v) and v != "{TODO}"


def _require_litellm() -> bool:
    """litellm 설치 여부를 시작 시점에 확인한다.
    gateway judge 는 litellm 을 통해 호출되므로 없으면 진행이 무의미하다.
    없으면 설치 안내를 출력하고 False 를 반환한다 (호출부에서 즉시 종료)."""
    try:
        import litellm  # noqa: F401
        return True
    except ImportError:
        print("=" * 60)
        print(" [중지] litellm 이 설치돼 있지 않습니다.")
        print(" gateway judge 로 평가하려면 litellm 이 필요합니다.")
        print("")
        print(" 아래 명령으로 설치한 뒤 다시 실행하세요:")
        print("     pip install litellm")
        print("=" * 60)
        return False


def _connect():
    """MLflow 접속 + gateway(litellm) 호출용 Basic 인증 헤더 주입.
    (judge 가 gateway 모델을 호출하므로 evaluate 에서도 동일 인증이 필요하다.)"""
    if _is_set(MLFLOW_USERNAME):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    if _is_set(MLFLOW_PASSWORD):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    if _is_set(MLFLOW_USERNAME) and _is_set(MLFLOW_PASSWORD):
        basic = base64.b64encode(
            f"{MLFLOW_USERNAME}:{MLFLOW_PASSWORD}".encode("utf-8")
        ).decode("ascii")
        _patch_litellm_basic_auth(f"Basic {basic}")
        os.environ.setdefault("OPENAI_API_KEY", "gateway-basic-auth")


def _patch_litellm_basic_auth(auth_header: str):
    """litellm.completion 에 Authorization 헤더를 강제 주입."""
    try:
        import litellm
    except ImportError:
        print("[경고] litellm 이 설치돼 있지 않습니다. (pip install litellm)")
        return
    if getattr(litellm, "_aiu_basic_auth_patched", False):
        return

    def _merge_headers(kwargs):
        eh = dict(kwargs.get("extra_headers") or {})
        eh.setdefault("Authorization", auth_header)
        kwargs["extra_headers"] = eh
        return kwargs

    _orig = litellm.completion
    def _completion(*a, **k):
        return _orig(*a, **_merge_headers(k))
    litellm.completion = _completion

    if hasattr(litellm, "acompletion"):
        _orig_a = litellm.acompletion
        async def _acompletion(*a, **k):
            return await _orig_a(*a, **_merge_headers(k))
        litellm.acompletion = _acompletion

    litellm._aiu_basic_auth_patched = True


def _pick_number(prompt_text: str, count: int) -> int:
    while True:
        sel = input(prompt_text).strip()
        if sel.isdigit() and 1 <= int(sel) <= count:
            return int(sel)
        print("  올바른 번호를 입력하세요.")


# #############################################################################
# 평가
# #############################################################################

def _pick_registered_judge(experiment_id: str):
    """등록된 judge(scorer) 목록을 조회해 숫자로 선택한다."""
    print("\n등록된 judge 조회 중 ...", end=" ", flush=True)
    scorers = list(mlflow.genai.list_scorers(experiment_id=experiment_id))
    print(f"완료 ({len(scorers)}개)")
    if not scorers:
        raise RuntimeError(
            "등록된 judge 가 없습니다. judge_register.py 로 먼저 judge 를 등록하세요."
        )
    print("\n평가에 사용할 judge 를 선택하세요:")
    for i, s in enumerate(scorers, 1):
        name = getattr(s, "name", "?")
        model = getattr(s, "model", "")
        extra = f"  (model: {model})" if model else ""
        print(f"    [{i}] {name}{extra}")
    idx = _pick_number("  번호 선택: ", len(scorers))
    return scorers[idx - 1]


def evaluate():
    if not _is_set(MLFLOW_TRACKING_URI):
        print("[중지] MLFLOW_TRACKING_URI 를 먼저 채우세요 ([입력]).")
        return

    # judge 선택 전에 litellm 부터 확인 (고른 뒤 실패하는 것 방지).
    if not _require_litellm():
        return

    _connect()
    exp = mlflow.set_experiment(MLFLOW_EXPERIMENT)

    judge = _pick_registered_judge(exp.experiment_id)

    # 최근 trace 수집
    traces = mlflow.search_traces(
        experiment_ids=[exp.experiment_id],
        max_results=MAX_TRACES,
        return_type="list",
    )
    if not traces:
        print("평가할 trace 가 없습니다. 먼저 에이전트와 대화해 trace 를 쌓으세요.")
        return None

    print(f"\n평가 대상 trace: {len(traces)} 건")
    print("평가 중 ... (judge LLM 호출)")

    results = mlflow.genai.evaluate(
        data=traces,
        scorers=[judge],
    )

    print("\n" + "=" * 60)
    print(" 평가 완료")
    print(f"  judge   : {getattr(judge, 'name', '?')}")
    print(f"  metrics : {results.metrics}")
    print("  → MLflow Traces 탭에서 각 trace 의 평가(Feedback) 확인")
    print("=" * 60)
    return results


def safe_main():
    try:
        evaluate()
    except KeyboardInterrupt:
        print("\n(취소)")
    except Exception as e:
        import traceback
        print(f"\n[오류] {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    safe_main()
