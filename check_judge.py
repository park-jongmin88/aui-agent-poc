"""
check_judge.py - 등록된 judge 확인용 (진단 스크립트)

  등록된 judge 목록과, 각 judge 에 gateway 인증 헤더(extra_headers)가
  저장됐는지 확인한다. (자동 평가 권한 문제 진단용)

  config.py 의 MLFLOW_CONN 을 그대로 사용하므로, 프로젝트 폴더에서
  그냥 실행하면 된다:

      python check_judge.py
"""

import os
import mlflow

from config import MLFLOW_CONN

# MLflow 접속 (config.py 재사용)
os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_CONN["username"]
os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_CONN["password"]
mlflow.set_tracking_uri(MLFLOW_CONN["tracking_uri"])

exp = mlflow.set_experiment(MLFLOW_CONN["experiment_name"])
print(f"experiment : {MLFLOW_CONN['experiment_name']}  (id={exp.experiment_id})")

from mlflow.genai import list_scorers

scorers = list(list_scorers(experiment_id=exp.experiment_id))
print(f"등록된 judge : {len(scorers)}개\n")

for s in scorers:
    r = repr(s)
    has_header = "extra_headers" in r and "Authorization" in r
    print(f"  - {getattr(s, 'name', '?')}")
    print(f"      model         : {getattr(s, 'model', '?')}")
    print(f"      인증헤더 저장 : {'있음 O' if has_header else '없음 X'}")
    print(f"      repr          : {r[:200]}")
    print()
