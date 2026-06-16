---
name: init
description: "workspace/models/ 하위 폴더를 분석해 run.py를 생성한다. 작업 순서 1단계. 다음과 같은 요청에 사용: '준비해줘', '시작해줘', '폴더 분석해줘', '작업 시작', '학습 준비해줘', 'sklearn_sample로 시작해줘', '1번 폴더로 해줘', '처음부터 시작할게', '폴더 목록 보여줘', '모델 목록', '작업 목록', '어떤 폴더 있어', '뭐 있어', '/list' 영어/추가 표현: '셋업해줘', '초기화', 'init', 'setup', 'run.py 생성', '이 폴더로 할게', 'ls', 'list', '목록', '뭐있어'."
---
# init - 작업 폴더 분석 및 run.py 생성

## 경로 기준 (중요)
- **모든 경로는 스크립트가 자동으로 계산한다. 에이전트가 직접 경로를 추론하거나 판단하지 않는다.**
- 현재 작업 디렉토리(cwd)나 OS 경로(`C:\` 등)와 무관하게 동작한다.
- workspace, models 등 모든 경로는 스크립트 실행 결과(JSON)에서 반환된 값을 사용한다.
- 경로를 "못 찾는다"고 판단하기 전에 반드시 스크립트를 먼저 실행해 결과를 확인한다.

## 개념
- 모델 폴더의 `source/` 안 파일들을 분석해 `run.py`를 생성한다
- 생성된 `run.py`는 해당 모델 폴더 안에 저장된다
- `.current`에 현재 작업 폴더를 기록한다

## 스크립트 호출 방식
모든 스크립트는 JSON을 stdout으로 반환한다.
```
{"status": "ok",    "data": {...}}   # 성공
{"status": "error", "message": "..."} # 실패 (stderr)
```
실패 시 message를 사용자에게 그대로 안내하고 중단한다.

## 절차

### 1. 폴더 선택
```
python skills/init/scripts/analyze_folder.py
```
- `data.action == "list"` → 폴더 목록을 번호와 함께 보여주고 선택받기
- 선택 후 `.current` 파일에 폴더명 기록

### 2. MLflow 설정 확인
- `config.json`의 `mlflow.tracking_uri` 확인
- 비어있으면 대화로 입력받아 `save_mlflow_config` 저장:
  ```
  MLflow 서버 주소를 입력해주세요 (예: http://mlflow:5000):
  계정이 필요하면 username/password도 입력해주세요 (없으면 Enter):
  ```

### 3. 실험명/모델명 설정
- 폴더명 기반으로 자동 제안 후 번호 선택으로 수정:
  ```
  아래 정보로 run.py를 생성할게요:
  1) 실험명(EXPERIMENT_NAME) : sklearn_sample
  2) 모델명(MODEL_NAME)      : sklearn_sample_model
  3) 이대로 진행
  ```

### 4. 모드 (데이터/모델 준비 방식)
- 폴더 내 파일 기반 자동 판별: LOAD_MODEL / RUN_CODE / DATA_ONLY / TEMPLATE
- 등록 방식은 항상 pyfunc + ModelWrapper (사내 표준)
- init이 run.py 와 함께 model_wrapper.py 도 생성한다 (이미 있으면 유지)

### 5. 폴더 분석
```
python skills/init/scripts/analyze_folder.py <폴더명>
```
- `data.mode`, `data.framework`, `data.files` 를 사용자에게 보고
- `data.has_run_py == true` 면 덮어쓸지 확인

### 5. run.py 생성
```
python skills/init/scripts/generate_run.py <폴더명> <실험명> <모델명>
```
- 성공 시 `data.message` 를 사용자에게 보여주기
- `data.todo_count > 0` 이면:
  ```
  TODO 항목 N개가 있습니다:
  (data.todo_items 목록)
  → '검증해줘'로 정확히 어떤 항목인지 확인하세요.
  ```
- 완료 후 validate 실행 권장

## 주의
- `workspace/templates/` 원본은 절대 수정하지 않는다
- `source/` 안의 원본 파일은 삭제/수정하지 않는다
- 병렬 tool call 사용 금지 (순차 실행 필수)
