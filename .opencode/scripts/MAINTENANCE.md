# Scripts Maintenance Guide

각 스크립트의 책임과 수정 시 주의점을 정리한다. 스킬-스크립트 매핑은 `skill_script_map.json`, 목록은 `SCRIPT_INDEX.md` 참고.

## Design Rule

- 핵심 엔진 `04-train-model/prepare_selected_model.py` 하나가 분석/선택/변환 로직을 담당한다.
- `select_model.py`, `prepare_select_model.py`, `launch_workspace_summary.py` 는 PowerShell 경로·오타를 정규화해 엔진에 위임하는 **얇은 래퍼**다. 엔진을 직접 수정하고, 래퍼는 손대지 않는 것을 원칙으로 한다.
- 무조건 발동 규칙은 `rules/always/`, 강제 의존성은 `config/dependencies.md` 로 관리한다 (코드 하드코딩 금지).

## 스크립트별 책임

### 00-setup/check_env.py
`.env` 존재/필수값 확인. 없으면 템플릿 생성 후 안내. `MLFLOW_TRACKING_URI` 필수. JSON 출력.
수정 포인트: 필수/선택 키(`REQUIRED_KEYS`).

### 00-setup/fetch_mlflow_version.py
트래킹 URL 표준 버전 API 조회. 실패 시 URL 재확인 안내 + 기본값 `3.10.0`.
수정 포인트: 조회 엔드포인트, `DEFAULT_VERSION`.

### 00-setup/build_requirements.py
`config/dependencies.md` 를 읽어 `{version}` 치환 후 requirements 생성. 기존 항목과 병합(강제 우선).
수정 포인트: 없음(의존성은 dependencies.md 에서).

### 04-train-model/prepare_selected_model.py (핵심 엔진)
워크스페이스 분석, 모델 선택, 템플릿 변환(source/saved_model 준비, runtest_2/predict 작성)을 담당.
- 입력 케이스 감지: `detect_source_case` / `resolve_source_case` (`--train`/`--register` 반영)
- 경로: `mlflow_artifact_uri`(uri, forward slash 상대경로), path 는 backslash
- requirements: `requirements_packages_for_kind` (기본 + kind별 CPU 프레임워크)
- predict 생성: `generated_predict_text` (ModelWrapper 형식)
주의: 4000줄 이상 검증된 엔진. 폴더/파일명(`aiu_custom`, `saved_model`, `config`, `local_serving`) 하드코딩 다수 — 이름 변경 시 연쇄 수정 필요.

### 04-train-model/run_training.py
확정 entrypoint(`runtest_2.py`) 실행. 필수 디렉토리 점검 후 학습·MLflow 등록.

### 04-train-model/adapt_ai_studio.py
사용자 임의 `run.py` 보강용 보조 스크립트.

### 01-project-analyze/validate_mlflow_project.py
워크스페이스 상세 분석, 모델 유무·필수 파일 점검.

### 02-sample-bootstrap/bootstrap_sample_project.py
모델 없음 상태에서 sklearn/pytorch/tensorflow 샘플을 루트로 복사.

### 02-model-select/select_model.py
2번 모델 선택 전용 PowerShell 안전 wrapper (엔진에 위임).

### 03-environment-check/check_environment.py
Python·requirements·MLflow 설정 확인. 보조: `response_speed_check.py`(속도 진단), `apply_index_ignore.py`(인덱싱 제외).

### 06-inference-test/test_inference.py
`input_example.json`/`predict.py` 기준 추론 계약 점검.

## Change Checklist

- 7단계를 바꾸면: `ai_studio_process.py` 의 `AI_STUDIO_PROCESS_STEPS` + `AGENTS.md` 4번 표를 함께 수정.
- 스킬/스크립트 매핑을 바꾸면: `skill_script_map.json` + `SCRIPT_INDEX.md` + `AGENTS.md` 5번 표.
- 의존성을 바꾸면: `config/dependencies.md` (코드 아님).
- 무조건 규칙을 추가하면: `rules/always/NN-<이름>.md`.

## Common Failure Meaning

- `runtime_dir_create_failed` : 작업 폴더 생성 실패 (권한/경로 확인).
- `source_copy_failed` : 원본 → source/ 복사 실패.
- MLflow uri 에 절대경로(`C:\...`) 노출 : `mlflow_artifact_uri` 의 상대경로 변환 확인.
