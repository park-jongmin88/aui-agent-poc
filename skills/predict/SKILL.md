---
name: predict
description: "MLflow에 등록된 모델을 로컬에서 로드해 추론 테스트를 수행한다. 작업 순서 4단계 (train 후). 다음과 같은 요청에 사용: '추론해줘', '예측해줘', '테스트해줘', '결과 확인해줘', '잘 됐는지 확인해줘', '모델 동작 확인해줘', '등록된 모델로 예측해줘', '로컬에서 확인해줘'."
---
# predict - 추론 테스트

## 절차
1. skills/predict/scripts/run_predict.py 실행
   - workspace/run.py 에서 MLflow 설정과 MODEL_NAME 자동 파싱
   - 최신 버전(latest) 모델 로드
2. 결과를 사용자에게 보고
3. 실패 시 원인 안내 (MLflow 연결, 모델 없음 등)

## 주의
- mlflow, scikit-learn 등 ML 패키지 필요 (requirements-ml.txt)
