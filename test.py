"""
프롬프트 버전 로드 진단 스크립트 (test.py)

목적: OSS MLflow 에서 프롬프트 '버전 지정 로드' 가 되는지 직접 확인한다.
      list_versions(순차 탐색)가 빈 리스트를 주는 원인을 가른다.

[사용법]
  1. 아래 TODO 3개(URI/아이디/비번)와 PROMPT_NAME 을 채운다.
  2. python test.py
  3. 출력에서 어떤 방식이 되고 안 되는지 확인한다.
"""

import os

# =============================================================================
# 설정 (judge_eval.py 와 동일한 값으로 채운다)
# =============================================================================
MLFLOW_TRACKING_URI = "TODO"   # 예: http://mlflow.xxx.com
MLFLOW_USERNAME     = "TODO"
MLFLOW_PASSWORD     = "TODO"

PROMPT_NAME = "PROMPT_CHILD"   # 버전이 여러 개 있는 프롬프트 이름
SCAN_MAX    = 5                # 버전 1..SCAN_MAX 까지 시도


def main():
    # MLflow Basic 인증
    os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD

    import mlflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    print("=" * 60)
    print(f" 프롬프트 버전 로드 진단 : {PROMPT_NAME}")
    print(f" tracking_uri : {MLFLOW_TRACKING_URI}")
    print("=" * 60)

    # ---------------------------------------------------------------
    # 1) 이름만으로 로드 (최신)
    # ---------------------------------------------------------------
    print("\n[1] load_prompt(name)  -- 최신 버전")
    try:
        p = mlflow.genai.load_prompt(PROMPT_NAME)
        print(f"    OK  -> version={getattr(p, 'version', '?')}")
    except Exception as e:
        print(f"    실패: {type(e).__name__}: {e}")

    # ---------------------------------------------------------------
    # 2) version= 파라미터로 버전 지정 로드
    # ---------------------------------------------------------------
    print("\n[2] load_prompt(name, version=N)")
    for v in range(1, SCAN_MAX + 1):
        try:
            p = mlflow.genai.load_prompt(PROMPT_NAME, version=v)
            print(f"    v{v}  OK  -> version={getattr(p, 'version', '?')}")
        except Exception as e:
            print(f"    v{v}  실패: {type(e).__name__}: {e}")

    # ---------------------------------------------------------------
    # 3) URI 방식 (prompts:/name/N)
    # ---------------------------------------------------------------
    print("\n[3] load_prompt('prompts:/name/N')")
    for v in range(1, SCAN_MAX + 1):
        try:
            p = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}/{v}")
            print(f"    /{v}  OK  -> version={getattr(p, 'version', '?')}")
        except Exception as e:
            print(f"    /{v}  실패: {type(e).__name__}: {e}")

    # ---------------------------------------------------------------
    # 4) @latest 별칭
    # ---------------------------------------------------------------
    print("\n[4] load_prompt('prompts:/name@latest')")
    try:
        p = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@latest")
        print(f"    OK  -> version={getattr(p, 'version', '?')}")
    except Exception as e:
        print(f"    실패: {type(e).__name__}: {e}")

    # ---------------------------------------------------------------
    # 5) MlflowClient.search_prompt_versions (Databricks 전용일 수 있음)
    # ---------------------------------------------------------------
    print("\n[5] MlflowClient().search_prompt_versions(name)")
    try:
        from mlflow import MlflowClient
        resp = MlflowClient().search_prompt_versions(PROMPT_NAME)
        items = getattr(resp, "prompt_versions", resp)
        nums = [getattr(x, "version", None) for x in items]
        print(f"    OK  -> versions={nums}")
    except Exception as e:
        print(f"    실패: {type(e).__name__}: {e}")

    # ---------------------------------------------------------------
    # 6) search_prompts 로 그 프롬프트 객체에 버전 정보가 있는지
    # ---------------------------------------------------------------
    print("\n[6] search_prompts() 객체 속성 확인")
    try:
        results = mlflow.genai.search_prompts()
        for pr in results:
            if getattr(pr, "name", None) == PROMPT_NAME:
                attrs = {k: getattr(pr, k) for k in dir(pr)
                         if not k.startswith("_") and not callable(getattr(pr, k))}
                print(f"    찾음. 속성: {attrs}")
                break
        else:
            print("    목록에서 해당 프롬프트를 못 찾음")
    except Exception as e:
        print(f"    실패: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print(" 진단 끝. [2]/[3] 중 되는 방식으로 list_versions 를 맞추면 됩니다.")
    print("=" * 60)


if __name__ == "__main__":
    main()
