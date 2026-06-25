"""
==============================================================================
 judge_eval.py - MLflow GenAI Judge 등록 + 평가 스크립트 (서빙과 분리)
==============================================================================
 MLflow 정석 방식(make_judge)으로 judge 를 만들어 experiment 에 등록하고,
 쌓인 trace 를 평가한다. 결과는 MLflow > GenAI > Judges 및 Traces 에 남는다.

 [서빙과의 관계]
   서빙(에이전트)은 평소처럼 대화하며 trace 만 남긴다.
   judge 는 이 스크립트로 '나중에 따로' 실행한다. (서빙에 judge 코드 없음)
   AI Gateway 는 이 스크립트 실행 시에만 필요하다. (서빙에는 불필요)

 [요구 버전]
   make_judge API: MLflow >= 3.4.0  (우리 환경 3.10.0 → OK)

 [사용]
   1. 아래 TODO (MLFLOW, EXPERIMENT, JUDGE_MODEL) 채운다.
   2. python judge_eval.py register   # judge 를 experiment 에 등록 (Judges 탭)
   3. python judge_eval.py evaluate   # 최근 trace 들을 평가
==============================================================================
"""

import sys
import os
import json

import mlflow
from mlflow.genai.judges import make_judge


# =============================================================================
# [1] 설정 (TODO 를 실제 값으로 채운다)
# =============================================================================
# MLflow 접속
MLFLOW_TRACKING_URI = TODO
MLFLOW_USERNAME      = TODO
MLFLOW_PASSWORD      = TODO

# 평가 대상/등록 experiment (trace 가 쌓이는 그 experiment)
EXPERIMENT_NAME = TODO

# judge 가 사용할 평가 모델 (AI Gateway 엔드포인트)
#   형식: "gateway:/<엔드포인트명>"
#   - <엔드포인트명> 은 MLflow AI Gateway 엔드포인트 목록의 name 컬럼 값 (chat 타입)
#   - 반드시 "gateway:/" 접두사를 붙인다. (접두사 없이 이름만 넣으면 Malformed URI 오류)
#   - 예) 엔드포인트 name 이 hcp_latest 이면 →  "gateway:/hcp_latest"
#   주의: gateway 방식은 litellm 이 필요하다. (pip install litellm)
JUDGE_MODEL = TODO   # 예: "gateway:/hcp_latest"

# judge 이름 (Judges 탭에 표시되는 이름)
JUDGE_NAME = "answer_quality"


# =============================================================================
# [2] 평가 기준 (자연어 instructions, 5등급)
# =============================================================================
# 우리 trace 는 agent_pipeline span 안에 질문/답변이 들어있어, root span 에서
# inputs/outputs 자동 추출이 안 될 수 있다. 그래서 {{ trace }} 변수를 쓴다.
#   - {{ trace }} : judge 가 trace 전체를 탐색해 질문/답변을 알아서 찾아 평가한다.
#   - 주의: {{ trace }} 는 {{ inputs }}/{{ outputs }} 와 함께 쓸 수 없다. (단독 사용)
#   - 템플릿 변수는 중괄호 2개 형식만 허용. 커스텀 변수는 지원 안 됨.
JUDGE_INSTRUCTIONS = (
    "주어진 {{ trace }} 는 사용자 질문에 에이전트가 답한 한 번의 대화 기록이다.\n"
    "trace 에서 사용자 질문과 에이전트의 최종 답변을 찾아, 답변의 품질을 평가하라.\n\n"
    "다음 세 가지를 종합적으로 고려한다.\n"
    "- 정확성: 질문에 맞고 사실에 부합하는가\n"
    "- 도움됨: 사용자에게 실제로 유용한가\n"
    "- 명확성: 이해하기 쉽고 잘 정리되어 있는가\n\n"
    "위를 종합하여 아래 5등급 중 하나의 정수로 평가하라.\n"
    "- 5: 매우 우수 (정확하고 매우 유용하며 명확함)\n"
    "- 4: 우수 (대체로 정확하고 유용함)\n"
    "- 3: 보통 (무난하나 일부 부족함)\n"
    "- 2: 미흡 (부정확하거나 불충분함)\n"
    "- 1: 매우 미흡 (잘못되었거나 도움이 되지 않음)\n\n"
    "평가 점수(정수)와 함께 그 이유를 간단히 제시하라."
)


def _connect():
    """MLflow 접속 + gateway 호출용 Basic 인증 헤더 설정.

    AI Gateway 는 MLflow Tracking Server 위에서 동작하고 HTTP Basic 인증을 요구한다.
    judge 가 gateway 모델을 호출할 때 'Authorization: Basic <base64(아이디:비번)>' 를
    헤더에 실어 보내도록 설정한다.
    (브라우저 'Try in Browser' 가 보내던 것과 동일한 헤더를 재현)
    """
    # 1) MLflow Tracking 서버 접속용 (trace 조회 등)
    if _is_set(MLFLOW_USERNAME):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    if _is_set(MLFLOW_PASSWORD):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # 2) gateway(LiteLLM) 호출용 Basic 인증 헤더 직접 주입
    #    아이디:비번 을 base64 로 인코딩해 Authorization 헤더로 보낸다.
    if _is_set(MLFLOW_USERNAME) and _is_set(MLFLOW_PASSWORD):
        import base64
        basic = base64.b64encode(
            f"{MLFLOW_USERNAME}:{MLFLOW_PASSWORD}".encode("utf-8")
        ).decode("ascii")
        auth_header = f"Basic {basic}"

        # LiteLLM 이 요청에 추가로 실어 보내는 헤더 (gateway 통과용)
        #   LiteLLM 은 LITELLM_EXTRA_HEADERS / extra_headers 를 요청 헤더에 병합한다.
        os.environ["LITELLM_EXTRA_HEADERS"] = json.dumps({"Authorization": auth_header})

        # 일부 경로는 OpenAI 호환 키를 요구하므로, 빈 키로 인한 사전 차단을 막기 위해
        # 더미 키도 채워둔다 (실제 인증은 위 Basic 헤더가 담당).
        os.environ.setdefault("OPENAI_API_KEY", "gateway-basic-auth")


def _is_set(v) -> bool:
    return isinstance(v, str) and bool(v) and v != "{TODO}"


def _build_judge():
    """make_judge 로 judge 인스턴스를 만든다. (5등급 정수)"""
    return make_judge(
        name=JUDGE_NAME,
        instructions=JUDGE_INSTRUCTIONS,
        model=JUDGE_MODEL,
        feedback_value_type=int,   # 5등급 정수 점수
    )


# =============================================================================
# [3] register - judge 를 experiment 에 등록 (Judges 탭에 남김)
# =============================================================================
def register():
    _connect()
    exp = mlflow.set_experiment(EXPERIMENT_NAME)
    judge = _build_judge()
    registered = judge.register(experiment_id=exp.experiment_id)
    print("=" * 60)
    print(" Judge 등록 완료")
    print(f"  name        : {JUDGE_NAME}")
    print(f"  experiment  : {EXPERIMENT_NAME} (id={exp.experiment_id})")
    print(f"  model       : {JUDGE_MODEL}")
    print("  → MLflow > GenAI > Judges 에서 확인")
    print("=" * 60)
    return registered


# =============================================================================
# [4] evaluate - 최근 trace 들을 평가 (결과를 Traces 에 Feedback 으로 부착)
# =============================================================================
def evaluate(max_results: int = 50):
    _connect()
    exp = mlflow.set_experiment(EXPERIMENT_NAME)
    judge = _build_judge()

    # 평가 대상 trace 수집 (이 experiment 의 최근 trace)
    traces = mlflow.search_traces(
        experiment_ids=[exp.experiment_id],
        max_results=max_results,
        return_type="list",
    )
    if not traces:
        print("평가할 trace 가 없습니다. 먼저 에이전트와 대화해 trace 를 쌓으세요.")
        return None

    print(f"  평가 대상 trace: {len(traces)} 건")

    # judge 를 scorer 로 넘겨 평가. 결과는 각 trace 에 Feedback 으로 자동 부착됨.
    results = mlflow.genai.evaluate(
        data=traces,
        scorers=[judge],
    )
    print("=" * 60)
    print(" 평가 완료")
    print(f"  metrics: {results.metrics}")
    print("  → MLflow Traces 탭에서 각 trace 의 평가(Feedback) 확인")
    print("=" * 60)
    return results


def _usage():
    print("사용법: python judge_eval.py [register|evaluate]")
    print("  register  judge 를 experiment 에 등록 (Judges 탭)")
    print("  evaluate  최근 trace 들을 평가")


if __name__ == "__main__":
    if not _is_set(MLFLOW_TRACKING_URI):
        print("[오류] 상단 TODO (MLFLOW_TRACKING_URI 등) 를 먼저 채우세요.")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "register":
        register()
    elif cmd == "evaluate":
        evaluate()
    else:
        _usage()
