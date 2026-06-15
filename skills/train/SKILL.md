---
name: train
description: "workspace/run.py 를 실행해 모델을 학습하고 MLflow에 등록한다. 작업 순서 3단계 (validate 후). 다음과 같은 요청에 사용: '학습해줘', '학습 시작해줘', '실행해줘', '돌려줘', 'MLflow에 등록해줘', '훈련시켜줘', '트레이닝 시작해', '모델 학습시켜줘', '학습 돌려줘', '결과 MLflow에 올려줘'."
---
# train - 모델 학습 및 MLflow 등록

## 개념
workspace/run.py 를 실행해 학습하고 결과를 MLflow에 등록한다.
최종 결과물은 MLflow 모델 레지스트리에 등록된 모델이다.

## 절차
1. skills/train/scripts/run_train.py --check-only 를 실행해 run.py 존재 및 MLflow 설정 확인
   - run.py 없으면 → "먼저 준비(init)가 필요합니다" 안내
   - MLflow 미설정 → "섹션 2의 MLFLOW_TRACKING_URI 를 설정해주세요" 안내
2. 확인 완료 후 실행 의사를 사용자에게 확인
3. skills/train/scripts/run_train.py 실행
   - 실시간 출력을 사용자에게 스트리밍
   - 완료 시 run_id, 모델명, accuracy 등 결과 요약 출력
4. 실패 시 마지막 오류 로그를 보여주고 원인 안내

## 주의
- 학습은 시간이 오래 걸릴 수 있으므로 실행 전 반드시 사용자 확인
- MLflow 연결 정보는 workspace/run.py 섹션 2에 있음
- 병렬 tool call 사용 금지 (순차 실행 필수)
