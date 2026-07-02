"""
==============================================================================
 judge_register.py - Judge(LLM 평가자) 등록 전용 스크립트
==============================================================================
 MLflow 정석 방식(make_judge)으로 judge 를 만들어 experiment 에 등록한다.
 평가 실행은 evaluate.py 가 담당한다 (등록/평가 분리).

 [흐름]
   1. MLflow 연결 (+ gateway 호출용 Basic 인증)
   2. 평가지(채점 기준) 선택        - mocks/judge_templates.json 에서 숫자로 선택
   3. 평가용 LLM 선택               - MLflow AI Gateway 목록에서 숫자로 선택
   4. make_judge + register()      - Judges 탭에 등록
   5. 자동 트래킹 on/off 선택       - on 이면 sample_rate 도 선택
        on  → judge.register().start(ScorerSamplingConfig(sample_rate=...))
              새로 들어오는 trace 를 judge 가 자동 채점 (1시간 내 trace 대상)
        off → 등록만 (평가는 evaluate.py 로 수동 실행)

 [사용]
   1. 아래 [입력] 채운다 (MLflow 정보만 - 나머지는 실행 중 선택).
   2. python judge_register.py

 요구: pip install mlflow litellm   (gateway judge 호출에 litellm 필요)
==============================================================================
"""

import os
import sys
import json
import base64
import logging

import mlflow
from mlflow.genai.judges import make_judge
from mlflow.genai.scorers import ScorerSamplingConfig

# gateway 조회 공통 모듈 (agent.py 와 공유)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "assets"))
from gateway_utils import list_gateway_endpoints, prompt_pick_endpoint  # noqa: E402

# MLflow 자동 태깅 403 경고 억제 (부가기능 실패라 등록엔 지장 없음)
logging.getLogger("mlflow.tracking.client").setLevel(logging.ERROR)


# #############################################################################
# [입력] ★ MLflow 정보만 채우세요 (나머지는 실행 중 선택)
# #############################################################################

MLFLOW_TRACKING_URI = TODO   # 예: "http://mlflow.도메인.com"
MLFLOW_USERNAME     = TODO
MLFLOW_PASSWORD     = TODO
MLFLOW_EXPERIMENT   = TODO   # trace 가 쌓이는 experiment. 예: "aiu-agent"

# 평가지 목업 파일 (지금은 파일. 나중에 프롬프트/DB 로 바뀔 수 있음)
JUDGE_TEMPLATES_PATH = os.path.join(_HERE, "mocks", "judge_templates.json")


# #############################################################################
# 공통 유틸
# #############################################################################

def _is_set(v) -> bool:
    return isinstance(v, str) and bool(v) and v != "{TODO}"


def _connect():
    """MLflow 접속 + gateway(litellm) 호출용 Basic 인증 헤더 주입."""
    if _is_set(MLFLOW_USERNAME):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    if _is_set(MLFLOW_PASSWORD):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # gateway 는 HTTP Basic 인증을 요구한다. judge 가 gateway 모델을 호출할 때
    # (내부적으로 litellm.completion) 매번 Authorization 헤더가 실리도록 패치한다.
    if _is_set(MLFLOW_USERNAME) and _is_set(MLFLOW_PASSWORD):
        basic = base64.b64encode(
            f"{MLFLOW_USERNAME}:{MLFLOW_PASSWORD}".encode("utf-8")
        ).decode("ascii")
        _patch_litellm_basic_auth(f"Basic {basic}")
        os.environ.setdefault("OPENAI_API_KEY", "gateway-basic-auth")


def _patch_litellm_basic_auth(auth_header: str):
    """litellm.completion(및 acompletion)에 Authorization 헤더를 강제 주입."""
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
    print("[정보] litellm 호출에 Basic 인증 헤더를 주입하도록 설정했습니다.")


def _pick_number(prompt_text: str, count: int, allow_zero_label: str = "") -> int:
    """1~count 중 하나를 고르게 한다. allow_zero_label 이 있으면 0 도 허용.
    반환: 고른 정수 (0 or 1..count)."""
    while True:
        sel = input(prompt_text).strip()
        if allow_zero_label and sel == "0":
            return 0
        if sel.isdigit() and 1 <= int(sel) <= count:
            return int(sel)
        print("  올바른 번호를 입력하세요.")


# #############################################################################
# 단계별 선택
# #############################################################################

def _load_templates() -> list:
    """평가지 목업 파일을 읽는다."""
    with open(JUDGE_TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _pick_template(templates: list) -> dict:
    """평가지를 숫자로 선택한다."""
    print("\n[1/3] 평가지(채점 기준)를 선택하세요:")
    for i, t in enumerate(templates, 1):
        print(f"    [{i}] {t.get('label', t['name'])}  - {t.get('description', '')}")
    idx = _pick_number("  번호 선택: ", len(templates))
    return templates[idx - 1]


def _pick_llm() -> str:
    """gateway 에서 평가용 LLM 을 선택해 'gateway:/<이름>' 형식으로 반환한다."""
    print("\n[2/3] 평가용 LLM(gateway 엔드포인트)을 선택하세요:")
    print("Gateway 엔드포인트 조회 중 ...", end=" ", flush=True)
    endpoints = list_gateway_endpoints(MLFLOW_TRACKING_URI, MLFLOW_USERNAME, MLFLOW_PASSWORD)
    print(f"완료 ({len(endpoints)}개)")
    chosen = prompt_pick_endpoint(endpoints, "평가용 LLM 엔드포인트", required=True)
    return f"gateway:/{chosen.get('name')}"


def _pick_auto_tracking() -> float:
    """자동 트래킹 여부 + sample_rate 를 선택한다.
    반환: sample_rate(0.1~1.0) 또는 None(자동트래킹 끔)."""
    print("\n[3/3] 자동 트래킹(새 trace 를 judge 가 자동 채점)을 켤까요?")
    print("    [1] 켜기")
    print("    [2] 끄기 (등록만 - 평가는 evaluate.py 로 수동 실행)")
    on = _pick_number("  번호 선택: ", 2)
    if on == 2:
        return None

    print("\n  샘플링 비율(자동 채점할 trace 비율)을 선택하세요:")
    for i in range(1, 11):
        rate = i / 10
        pct = int(rate * 100)
        note = " - 전부 평가" if i == 10 else (" - 절반만 평가" if i == 5 else "")
        print(f"    [{i}] {rate:.1f} ({pct}%{note})")
    idx = _pick_number("  번호 선택: ", 10)
    return idx / 10


# #############################################################################
# 등록
# #############################################################################

def register():
    if not _is_set(MLFLOW_TRACKING_URI):
        print("[중지] MLFLOW_TRACKING_URI 를 먼저 채우세요 ([입력]).")
        return

    _connect()
    exp = mlflow.set_experiment(MLFLOW_EXPERIMENT)

    templates = _load_templates()
    tmpl = _pick_template(templates)         # [1/3] 평가지
    judge_model = _pick_llm()                # [2/3] gateway LLM
    sample_rate = _pick_auto_tracking()      # [3/3] 자동 트래킹 (+비율)

    judge = make_judge(
        name=tmpl["name"],
        instructions=tmpl["instructions"],
        model=judge_model,
        feedback_value_type=int,             # 1~5 정수
    )
    registered = judge.register(experiment_id=exp.experiment_id)

    print("\n" + "=" * 60)
    print(" Judge 등록 완료")
    print(f"  평가지     : {tmpl.get('label', tmpl['name'])} ({tmpl['name']})")
    print(f"  평가 LLM   : {judge_model}")
    print(f"  experiment : {MLFLOW_EXPERIMENT} (id={exp.experiment_id})")

    if sample_rate is not None:
        try:
            registered.start(sampling_config=ScorerSamplingConfig(sample_rate=sample_rate))
            print(f"  자동 트래킹: 켜짐 (sample_rate={sample_rate:.1f}, {int(sample_rate*100)}%)")
            print("    → 새로 들어오는 trace 를 judge 가 자동 채점합니다 (1시간 내 trace 대상).")
        except Exception as e:
            print(f"  자동 트래킹: 시작 실패 - {type(e).__name__}: {e}")
            print("    (등록 자체는 완료됨. 이 서버/버전이 자동 채점을 지원하지 않을 수 있음.)")
    else:
        print("  자동 트래킹: 꺼짐 (평가는 evaluate.py 로 수동 실행)")

    print("  → MLflow > GenAI > Judges 에서 확인")
    print("=" * 60)
    return registered


def safe_main():
    try:
        register()
    except KeyboardInterrupt:
        print("\n(취소)")
    except Exception as e:
        import traceback
        print(f"\n[오류] {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    safe_main()
