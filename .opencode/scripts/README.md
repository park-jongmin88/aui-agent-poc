# OpenCode MLflow Scripts

`.opencode/skills` 의 MLflow 흐름을 보조하는 로컬 스크립트 모음. 모델이 있으면 7단계, 없으면 샘플 복사 후 진행한다.

- 스킬-스크립트 매핑: `skill_script_map.json` (도구용), `SCRIPT_INDEX.md` (사람용)
- 유지보수 상세: `MAINTENANCE.md`

## 경로 규칙 (MLmodel artifact)

- 모델 `path`: Windows native 상대경로 유지. 예: `saved_model\cnn_model.pt`
- 모델 `url` / config `uri`: KServe/서버 기준 forward slash. 예: `saved_model/cnn_model.pt`, `config/config.json`
- KServe/Linux 실제 경로: MLflow 패키지 내부 `path: artifacts/...`. `aiu_custom/model.py` 가 `context.artifacts` 로 읽는다.

## 스킬-스크립트 흐름

```text
00 Setup             00-setup/check_env.py, fetch_mlflow_version.py, build_requirements.py
01 Project Analyze   01-project-analyze/validate_mlflow_project.py
                     04-train-model/prepare_selected_model.py (모델 목록/선택)
02 Sample Bootstrap  02-sample-bootstrap/bootstrap_sample_project.py
02 Model Select      02-model-select/select_model.py (PowerShell 안전 wrapper)
03 Environment Check 03-environment-check/check_environment.py
                     03-environment-check/response_speed_check.py, apply_index_ignore.py
04 Train Model       04-train-model/prepare_selected_model.py (핵심 엔진)
                     04-train-model/run_training.py (확정 entrypoint 실행)
                     04-train-model/adapt_ai_studio.py (보조)
06 Inference Test    06-inference-test/test_inference.py
```

## 입력 케이스

선택한 `data/<폴더>` 내용으로 처리가 갈린다 (엔진이 자동 감지):

- 모델만 → 학습 없이 로드해 등록
- 자료만 → 학습 후 등록
- 둘 다 → `--register`(등록) / `--train`(학습) 선택, 기본은 등록

## 생성 폴더 (data/<모델>_MMDD_SEQ/)

- `source/` 입력 원본 (읽기 전용) / `saved_model/` 등록될 모델 (결과)
- `aiu_custom/` ModelWrapper + 로더 / `config/` 메타 / `local_serving/` 로컬 추론
- `runtest_2.py` 학습·등록 / `input_example.json` / `requirements.txt` / `README.md`(자동)

입력(source)과 출력(saved_model)을 분리한다.

## 주요 스크립트

### 00-setup/
- `check_env.py` — `.env` 확인 (없으면 생성 후 안내, `MLFLOW_TRACKING_URI` 필수)
- `fetch_mlflow_version.py` — 트래킹 URL 로 버전 조회 (실패 시 3.10.0)
- `build_requirements.py` — `config/dependencies.md` 기준 requirements 생성

### 04-train-model/prepare_selected_model.py
핵심 엔진. 워크스페이스 분석 → 모델 선택 → 템플릿 변환(source/saved_model 준비, runtest_2/predict 작성)까지 담당.
`--project`, `--model <번호|경로>`, `--execute`, `--train`, `--register` 등을 받는다.

### 04-train-model/run_training.py
확정된 entrypoint(`runtest_2.py`)를 실행해 학습·MLflow 등록을 수행한다.

### 01-project-analyze/validate_mlflow_project.py
워크스페이스를 상세 분석하고 모델 유무·필수 파일을 점검한다.

### 02-sample-bootstrap/bootstrap_sample_project.py
모델이 없을 때 sklearn/pytorch/tensorflow 샘플을 루트로 복사한다.

### 03-environment-check/check_environment.py
Python·requirements·MLflow 설정을 확인한다. (속도 진단·인덱스 제외는 보조 스크립트)

### 06-inference-test/test_inference.py
`input_example.json` / `predict.py` 기준으로 추론 계약을 점검한다.

## Safety

- API key·password·token 값은 출력하지 않는다 (`set`/`empty`/`missing` 로만 보고).
- `.env`, 대용량 artifact 는 git 에 올리지 않는다.
- 설치·학습·추론은 사용자가 요청할 때만 실행한다.
