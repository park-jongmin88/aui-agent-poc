---
name: train
description: "현재 작업 폴더의 run.py를 실행해 모델을 학습하고 MLflow에 등록한다. 작업 순서 4단계. 다음과 같은 요청에 사용: '학습해줘', '학습 시작해줘', '실행해줘', '돌려줘', 'MLflow에 등록해줘', '훈련시켜줘', '모델 학습시켜줘', '바로 학습할게', '로컬 테스트 건너뛰고 학습해줘'."
---
# train - 모델 학습 및 MLflow 등록

## 경로 기준 (중요)
- **모든 경로는 스크립트가 자동으로 계산한다. 에이전트가 직접 경로를 추론하거나 판단하지 않는다.**
- 현재 작업 디렉토리(cwd)나 OS 경로와 무관하게 동작한다.
- 경로를 "못 찾는다"고 판단하기 전에 반드시 스크립트를 먼저 실행해 결과를 확인한다.

## 게이트 조건
- status=validated 또는 status=local_tested 없으면 차단
- "먼저 validate(검증)를 실행해주세요" 안내

## 스크립트 호출 방식
```
python skills/train/scripts/run_train.py [폴더명] --check-only   # 사전 확인
python skills/train/scripts/run_train.py [폴더명]                # 실제 실행
# 폴더명 생략 시 .current 자동 사용
```
실행 중 스트리밍:
- `{"status": "running", "message": "..."}` → 시작 안내
- `{"status": "progress", "line": "..."}` → 각 출력 라인
- `{"status": "ok", "data": {...}}` → 완료

## 절차

### 1. 현재 작업 폴더 + 게이트 확인

### 2. localrun 선택지 (validated 상태일 때만)
```
로컬에서 먼저 테스트할까요, 바로 MLflow에 등록할까요?
  1) 로컬 테스트 먼저 (권장)
  2) 바로 MLflow 등록
```
local_tested 상태면 바로 진행

### 3. ML 패키지 확인
- 보통 install 시 mlflow 등이 이미 설치되어 있어 이 단계는 건너뜁니다.
- 만약 `python -c "import mlflow"` 가 실패하면:
  ```
  ML 패키지(mlflow 등)가 없습니다.
  install을 다시 실행하면 requirements.txt 전체가 자동 설치됩니다.
  ```

### 4. 사전 확인
```
python skills/train/scripts/run_train.py --check-only
```
- 실패 시 `data.message` 안내 후 중단

### 5. 최종 확인 후 실행
```
아래 정보로 학습을 시작합니다:
  실험명: {experiment_name}
  모델명: {model_name}
  MLflow: {mlflow_uri}
진행할까요?
```
```
python skills/train/scripts/run_train.py
```
- progress 라인을 실시간 출력
- 완료 시 `data` 파싱:
  ```
  ✓ 학습 완료 ({elapsed}s)
    run_id : {run_id}
    모델명 : {model}
    accuracy: {accuracy}  (있을 때)
  ```
- `.aiu_state.json`에 status=trained, last_run_id 자동 저장 (스크립트가 처리)
- 하단 툴바 자동 갱신

## 주의
- 병렬 tool call 사용 금지 (순차 실행 필수)
- 학습은 시간이 오래 걸릴 수 있음
