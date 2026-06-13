---
name: predict
description: "MLflow에 등록된 모델을 로컬에서 로드해 추론을 수행한다(local_test). '추론', '예측', '테스트' 요청 시 사용."
---
# predict - 로컬 추론 테스트

## 절차
1. 사용자에게 모델명과 버전(또는 latest)을 확인한다.
2. local_test/ 폴더에 테스트 스크립트가 있으면 활용하고, 없으면 아래 패턴으로 작성을 제안한다:
   - `mlflow.pyfunc.load_model("models:/<모델명>/<버전>")` 으로 로드
   - run.py의 인풋 샘플 형식으로 predict 호출
3. 추론 결과를 사용자에게 보고한다.

## 주의
- MLflow 연결이 필요한 스킬이다. 연결 실패 시 .env 설정 확인을 안내한다.
