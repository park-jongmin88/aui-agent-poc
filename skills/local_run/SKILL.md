---
name: local_run
description: "run.py를 MLflow 등록 없이 로컬에서만 실행해 모델 동작을 확인한다. 선택 단계 (validate 후, train 전). 다음과 같은 요청에 사용: '로컬에서 테스트해줘', '로컬 실행해줘', 'MLflow 없이 돌려봐', '동작 확인해줘', '먼저 테스트해보고 싶어', '로컬에서 먼저 확인해줘'."
---
# local_run - 로컬 테스트 (선택 단계)

## 게이트 조건
- status=validated 없으면 차단
- "먼저 validate(검증)를 실행해주세요" 안내

## 개념
- MLflow 서버 없이 로컬에서만 학습 수행
- 결과 모델은 workspace/results/<모델명>/ 에 저장
- 동작 확인 후 이상 없으면 train(MLflow 등록)으로 진행

## 절차

### 1. 현재 작업 폴더 + 게이트 확인

### 2. ML 패키지 설치 확인
- mlflow import 실패 시 설치 안내 (train과 동일)

### 3. 로컬 실행
- `skills/local_run/scripts/run_local.py` 실행
- run.py의 MLflow 등록 부분을 비활성화하고 실행
- 실시간 출력 스트리밍
- 결과 모델을 workspace/results/<모델명>/ 에 저장

### 4. 결과 보고
```
✓ 로컬 테스트 완료
  모델 저장: workspace/results/sklearn_sample/model.pkl
  accuracy: 0.9234
  → 이상 없으면 'MLflow에 등록해줘'로 train을 진행하세요
  → 로컬 서빙 테스트: '로컬 서버 띄워줘'
```
- `.aiu_state.json`에 `status=local_tested` 저장

### 5. 로컬 서빙 연계
- 로컬 테스트 완료 후 로컬 서빙 바로 가능
- "로컬 서버 띄워줘" 요청 시 local_serve 스킬 실행
