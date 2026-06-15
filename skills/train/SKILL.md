---
name: train
description: "현재 작업 폴더의 run.py를 실행해 모델을 학습하고 MLflow에 등록한다. 작업 순서 4단계. 다음과 같은 요청에 사용: '학습해줘', '학습 시작해줘', '실행해줘', '돌려줘', 'MLflow에 등록해줘', '훈련시켜줘', '모델 학습시켜줘', '바로 학습할게', '로컬 테스트 건너뛰고 학습해줘'."
---
# train - 모델 학습 및 MLflow 등록

## 게이트 조건
- status=validated 또는 status=local_tested 없으면 차단
- "먼저 validate(검증)를 실행해주세요" 안내

## 절차

### 1. 현재 작업 폴더 + 게이트 확인

### 2. local_run 선택지 제공 (validated 상태일 때만)
```
로컬에서 먼저 테스트할까요, 바로 MLflow에 등록할까요?
  1) 로컬 테스트 먼저 (권장 — MLflow 등록 없이 동작 확인)
  2) 바로 MLflow 등록
```
- local_tested 상태면 이 선택지 생략하고 바로 진행

### 3. ML 패키지 설치 확인
- mlflow import 실패 시:
```
학습을 실행하려면 ML 패키지가 필요합니다.
포함: mlflow, scikit-learn, pandas, numpy
지금 설치할까요?
```
- 확인 시 setting/requirements-ml.txt 설치
- `.aiu_state.json`에 `ml_installed: true` 기록

### 4. run.py 확인
- `skills/train/scripts/run_train.py --check-only` 실행
- MLflow 미설정 → config.json 확인 안내

### 5. 최종 확인 후 학습 실행
```
아래 정보로 학습을 시작합니다:
  실험명: my-experiment
  모델명: my-model
  MLflow: http://mlflow:5000
진행할까요?
```
- `skills/train/scripts/run_train.py` 실행
- 실시간 출력 스트리밍
- 완료 시 run_id, 메트릭 요약 출력
- `.aiu_state.json`에 `status=trained`, `last_run_id` 저장

## 주의
- 병렬 tool call 사용 금지
