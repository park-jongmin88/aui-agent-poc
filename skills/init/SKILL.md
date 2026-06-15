---
name: init
description: "workspace/models/ 하위 폴더를 분석해 run.py를 생성한다. 작업 순서 1단계. 다음과 같은 요청에 사용: '준비해줘', '시작해줘', '폴더 분석해줘', '작업 시작', '학습 준비해줘', 'sklearn_sample로 시작해줘', '1번 폴더로 해줘', '처음부터 시작할게'."
---
# init - 작업 폴더 분석 및 run.py 생성

## 개념
- 모델 폴더의 `source/` 안 파일들을 분석해 `run.py`를 생성한다
- 생성된 `run.py`는 해당 모델 폴더 안에 저장된다
- `.current`에 현재 작업 폴더를 기록한다

## 절차

### 1. 폴더 선택
- 폴더가 지정되지 않으면 `skills/init/scripts/analyze_folder.py` 를 인자 없이 실행
- 번호가 붙은 목록을 보여주고 사용자에게 번호로 선택받기
- 선택 후 `.current` 업데이트

### 2. MLflow 설정 확인
- `config.json`의 `mlflow.tracking_uri` 확인
- 비어있거나 미설정이면 대화로 입력받기:
  ```
  MLflow 서버 주소가 설정되지 않았습니다.
  주소를 입력해주세요 (예: http://mlflow:5000):
  계정이 필요하면 username/password도 입력해주세요 (없으면 Enter):
  ```
- 입력받은 값을 `config.json`에 저장

### 3. 실험명/모델명 설정
- 폴더명 기반으로 자동 제안:
  ```
  아래 정보로 run.py를 생성할게요:

  1) 실험명(EXPERIMENT_NAME) : sklearn_sample
  2) 모델명(MODEL_NAME)      : sklearn_sample_model
  3) 이대로 진행
  ```
- 번호 선택으로 수정 가능, 수정 후 다시 확인
- 확정된 값은 `.aiu_state.json`에 저장

### 4. 폴더 분석
- `skills/init/scripts/analyze_folder.py <폴더명>` 실행
- 분석 결과(mode, framework, 파일 목록)를 사용자에게 보고
- run.py가 이미 있으면 덮어쓸지 확인

### 5. run.py 생성
- `skills/init/scripts/generate_run.py <폴더명> <실험명> <모델명>` 실행
- `workspace/templates/run.py` 기반으로 생성
- 섹션 2를 자동으로 채움:
  - `MLFLOW_TRACKING_URI` ← config.json 값
  - `MLFLOW_USERNAME` ← config.json 값
  - `MLFLOW_PASSWORD` ← config.json 값
  - `EXPERIMENT_NAME` ← 사용자 확인값
  - `MODEL_NAME` ← 사용자 확인값
- 섹션 3~5는 분석 결과(mode)에 따라 자동 생성
- 생성 후 `.aiu_state.json`에 `status: initialized` 저장
- validate 실행 권장

## 주의
- `workspace/templates/` 원본은 절대 수정하지 않는다
- `source/` 안의 원본 파일은 삭제/수정하지 않는다
