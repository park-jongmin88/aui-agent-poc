"""
list_versions 로직 검증 스크립트 (test2.py)

목적: prompt.py 의 list_versions(순차 탐색) 로직을 '서버와 동일한 인증 환경'에서
      그대로 돌려, [1,2,3] 같은 버전 목록이 제대로 나오는지 확인한다.

판정:
  - [1,2,3] 처럼 나오면  -> 로직은 정상. 서버 반영/호출 문제 (재서빙 확인)
  - [] 빈 리스트면        -> 로직/인증 문제

[사용법]
  1. 아래 TODO 3개와 PROMPT_NAME 을 채운다. (judge_eval.py 와 동일 값)
  2. python test2.py
"""

import os

# =============================================================================
# 설정
# =============================================================================
MLFLOW_TRACKING_URI = "TODO"
MLFLOW_USERNAME     = "TODO"
MLFLOW_PASSWORD     = "TODO"

PROMPT_NAME = "PROMPT_CHILD"   # 버전이 여러 개 있는 프롬프트
MAX_SCAN    = 100             # prompt.py 와 동일


def list_versions(name, max_scan=MAX_SCAN):
    """prompt.py 의 list_versions 와 '완전히 동일한' 로직."""
    import mlflow
    nums = []
    v = 1
    while v <= max_scan:
        try:
            mlflow.genai.load_prompt(name, version=v)
            nums.append(v)
            v += 1
        except Exception:
            break
    return nums


def main():
    # 서버와 동일하게 Basic 인증 설정
    os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD

    import mlflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    print("=" * 60)
    print(f" list_versions 로직 검증 : {PROMPT_NAME}")
    print(f" tracking_uri : {MLFLOW_TRACKING_URI}")
    print("=" * 60)

    # ---------------------------------------------------------------
    # [7] list_versions 로직 그대로 (한 번에)
    # ---------------------------------------------------------------
    print("\n[7] list_versions(PROMPT_NAME) 결과")
    result = list_versions(PROMPT_NAME)
    print(f"    -> {result}")

    # ---------------------------------------------------------------
    # [8] 단계별 추적 (어디서 멈추는지 자세히)
    # ---------------------------------------------------------------
    print("\n[8] 버전별 로드 상세 (멈추는 지점 확인)")
    v = 1
    while v <= 10:   # 최대 10까지만 자세히
        try:
            p = mlflow.genai.load_prompt(PROMPT_NAME, version=v)
            print(f"    v{v}  OK  (version={getattr(p, 'version', '?')})")
            v += 1
        except Exception as e:
            print(f"    v{v}  중단 -> {type(e).__name__}: {e}")
            break

    # ---------------------------------------------------------------
    # [9] 판정
    # ---------------------------------------------------------------
    print("\n" + "=" * 60)
    if result:
        print(f" 판정: 로직 정상 (버전 {result}).")
        print("       서버에서 빈 리스트가 나온다면 -> 재서빙/호출 문제.")
    else:
        print(" 판정: 빈 리스트. v1 부터 로드 실패.")
        print("       -> 인증 또는 프롬프트 이름 문제일 수 있음. [8] 상세 확인.")
    print("=" * 60)


if __name__ == "__main__":
    main()
