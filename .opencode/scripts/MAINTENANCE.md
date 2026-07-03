# Scripts Maintenance Guide

이 문서는 `.opencode/scripts` 코드를 유지보수하는 사람을 위한 설명서입니다. 사용법은 `README.md`, 운영 속도 기준은 `.opencode/performance/CLOSED_NETWORK_SPEED.md`를 봅니다.

## Design Rule

```text
Ai Studio 모드  -> 읽기/분석/안내만 수행
Ai Studio 빌드 모드   -> 복사/수정/설치/실행 가능
scripts      -> 폐쇄망에서도 동작하도록 표준 라이브러리 중심
```

공통 원칙:

- secret 값은 출력하지 않습니다. password/token은 `set`, `missing`, `empty` 상태만 보여줍니다.
- 사용자가 만든 모델 파일은 덮어쓰지 않습니다. 덮어쓰기는 `--force`처럼 명시된 경우만 허용합니다.
- Windows 폐쇄망을 우선 고려합니다.
- Bun은 사용하지 않습니다.
- Python 기준 버전은 `3.11.9`입니다.

## Skill Script Overview

스킬 목록 기준 사람이 읽는 정리표는 `.opencode/scripts/SCRIPT_INDEX.md`입니다.
도구가 읽는 스킬-스크립트 매핑의 단일 기준은 `.opencode/scripts/skill_script_map.json`입니다.
실제 구현 파일은 스킬 목록 기준 폴더에 두고, 실행도 해당 폴더 경로를 직접 사용합니다.
문서를 수정할 때는 아래 표, `SCRIPT_INDEX.md`, JSON을 함께 맞춥니다.

```text
01 Project Analyze
  01-project-analyze/validate_mlflow_project.py      상세 프로젝트 분석
  launch_workspace_summary.py                        Windows 런치 분석 명령 호환
  04-train-model/prepare_selected_model.py           모델 목록 확인

02 Sample Bootstrap
  02-sample-bootstrap/bootstrap_sample_project.py    sklearn/pytorch/tensorflow 샘플 복사

02 Model Select
  02-model-select/select_model.py                    2번 모델 선택 전용 PowerShell 안전 wrapper

03 Environment Check
  03-environment-check/check_environment.py          Python, requirements.txt, MLflow 설정 확인
  03-environment-check/response_speed_check.py       폐쇄망 속도 진단
  03-environment-check/apply_index_ignore.py         인덱싱 제외 적용

04 Train Model / Selected Model Build
  04-train-model/prepare_selected_model.py           1번 모델 목록 확인 + 4번 템플릿 변환
  04-train-model/run_training.py                     5번 원격 MLflow 등록 실행
  04-train-model/adapt_ai_studio.py                  사용자 임의 run.py 보강용 보조 스크립트

05 Inference Test
  06-inference-test/test_inference.py                수동 추론 계약 점검

QA / Maintenance
  qa-maintenance/doctor.py                           전체 워크플로우 상태 1페이지 점검
  qa-maintenance/test_local_sample.py                번들 샘플 QA
  SCRIPT_INDEX.md                 스킬 목록 기준 스크립트 정리표
```

고정 7단계 매핑:

```text
1 모델 목록 확인                  -> prepare_selected_model.py --project .
2 모델 선택                       -> 02-model-select/select_model.py --model <번호|경로>
3 환경 검증      -> check_environment.py
4 템플릿 변환                     -> prepare_selected_model.py --model selected --execute
5 원격 MLflow 등록 실행           -> run_training.py --execute
6 추론 테스트                     -> inferencetest.py
7 오류 재실행                     -> 실패 단계 스크립트 재실행
```

## doctor.py

책임:

- OpenCode 패키지 상태를 확인합니다.
- 01~05 스킬 폴더가 순서대로 있는지 확인합니다.
- Python 3.11.9 여부를 확인합니다.
- `requirements.txt` 기준 pip 패키지 설치/버전 상태를 요약합니다.
- 선택 모델 변환은 고정 파일 목록만을 전제로 설명하지 말고, 복사된 템플릿 폴더 내부에서 실제 존재하는 파일과 선택 모델 실행/등록에 필요한 연결부를 기준으로 설명합니다.
- 실행 파일 후보를 확정하거나 사용자 입력 필요 상태를 표시합니다.
- 실행 파일이 Ai Studio/MLflow 규격에 맞게 수정이 필요한지 확인합니다.
- 샘플 규격 폴더/파일 누락을 찾습니다.
- `.env`의 MLflow 5개 값을 확인합니다.
- 산출물 후보를 확인합니다.

주요 수정 위치:

```text
EXPECTED_PYTHON_VERSION    Python 기준 버전
SKILL_FOLDERS              스킬 폴더 순서
SAMPLE_SPEC_DIRS           필수 폴더
SAMPLE_SPEC_FILES          필수 파일
ENTRYPOINT_CANDIDATES      실행 파일 후보
MLFLOW_SOURCE_KEYS         필수 MLflow 소스 키
SETTING_ALIASES            사용자가 다르게 쓴 설정명 허용 목록
```

주의:

- `mlflow_tracking_password` 값은 절대 evidence에 그대로 넣지 않습니다.
- `.opencode/` 전체는 사용자 모델 산출물로 오인하지 않도록 스캔에서 제외합니다.
- 실행 파일 후보가 여러 개면 `--entrypoint <file>`로 사용자가 실제 파일을 확정해야 합니다.
- `--strict-exit`은 QA 자동화용입니다. 일반 사용 흐름에서는 기본 exit code 0을 유지합니다.

## adapt_ai_studio.py

책임:

- 사용자가 가져온 `run.py`, `train.py`, `main.py` 등 임의 실행 파일을 분석합니다.
- 프레임워크 후보를 추정합니다.
- dry-run에서 수정 계획만 출력합니다.
- `--execute`일 때만 entrypoint를 백업하고 Ai Studio/MLflow adapter block을 삽입합니다.
- 부족한 scaffold 파일을 새로 만듭니다.

주요 수정 위치:

```text
FRAMEWORK_RULES             프레임워크 추정 규칙
REQUIREMENT_BY_FRAMEWORK    프레임워크별 최소 requirements
requirements.required.txt   생성 requirements.txt의 필수 패키지 기준
ENTRYPOINT_HINTS            실행 파일 후보
adapter_block()             entrypoint에 삽입할 Ai Studio/MLflow helper
model_wrapper_template()    aiu_custom/predict.py 템플릿
local_serving_template()    local_serving/serve.py 템플릿
adapt_entrypoint()          백업 생성과 adapter block 삽입
```

주의:

- 기본은 dry-run입니다. 실제 수정은 `--execute`가 있어야 합니다.
- 실행 파일을 찾지 못하면 새 실행 파일을 만들지 않습니다. 사용자가 실제 파일을 직접 넣고 `--entrypoint <file>`로 지정해야 합니다.
- entrypoint 수정 전 `<file>.ai_studio.bak` 백업을 만듭니다.
- 기존 adapter block이 있으면 `--force` 없이는 다시 쓰지 않습니다.
- 모델별 학습/추론 로직은 자동으로 해석하지 않습니다. adapter block과 wrapper TODO를 넣어 Ai Studio 연결부를 보강합니다.
- secret 값은 생성하지 않습니다. 사용자가 소스의 설정 블록에 직접 입력합니다.

## validate_mlflow_project.py

책임:

- 프로젝트 후보를 선택합니다.
- requirements, entrypoint, artifact, config, input_example을 분석합니다.
- 프레임워크 후보를 보수적으로 추정합니다.
- 샘플 규격 부족분을 `next_steps`로 안내합니다.

주요 수정 위치:

```text
select_project()           명시 경로 또는 현재 폴더만 선택
ENTRYPOINT_NAMES           일반 실행 파일 후보
TRAINING_ENTRYPOINT_NAMES  실제 사용하는 Python 실행 파일 후보
REQUIRED_DIRS              필수 샘플 폴더
SAMPLE_SPEC_FILES          필수 샘플 파일
AI_STUDIO_ENV_KEYS         필수 설정 키
ARTIFACT_SUFFIXES          모델 파일 확장자
```

주의:

- `select_project()`는 명시 경로를 최우선으로 둡니다.
- `score_project()`는 품질 점수가 아니라 후보 선택용 힌트입니다.
- `write_permission_check()`는 임시 파일만 만들고 삭제합니다.

## bootstrap_sample_project.py

책임:

- 번들 샘플 목록을 보여줍니다.
- 샘플을 폴더째 복사합니다.
- 기존 모델에는 부족한 scaffold만 보충합니다.
- 생성 산출물과 캐시는 복사하지 않습니다.

주요 수정 위치:

```text
SAMPLES                    선택 가능한 샘플 3개
IGNORED_NAMES              복사 제외 이름
GENERATED_ROOT_DIRS        복사 제외 생성 폴더
REQUIRED_PROJECT_DIRS      샘플에 반드시 있어야 할 폴더
SCAFFOLD_ROOT_NAMES        기존 모델에 보충 가능한 루트 항목
build_tod_guide()          복사 후 사용자에게 보여줄 TODO 단계
```

주의:

- 기본 복사 모드는 `folder`입니다. 루트에 파일을 흩뿌리지 않습니다.
- `runtest.py`가 이미 있으면 `run_model.py`는 굳이 복사하지 않습니다.
- Windows 호환성을 위해 `shutil.copyfile()`을 사용합니다.
- `--force` 없이 기존 파일을 덮어쓰지 않습니다.

## check_environment.py

책임:

- Python 버전, venv, dependency 파일, 설치 패키지를 확인합니다.
- `requirements.txt`의 필요 패키지, 요구 버전, 현재 설치 버전, 미설치/버전 불일치를 확인합니다.
- 환경 변수 `MLFLOW_*` 상태를 확인합니다.
- 현재 워크스페이스 루트의 `.env` 값을 파싱합니다.
- 사용자가 직접 `.env`에 입력해야 하는 값만 알려줍니다.

주요 수정 위치:

```text
ENV_KEYS                   확인할 MLFLOW 환경 변수
AI_STUDIO_ENV_KEYS         소스 설정 키 5개, 이 중 experiment/register 이름은 자동 기본값 허용
MODEL_SETTING_FILES        설정을 읽을 파일 우선순위
ENTRYPOINTS                실행 파일 후보
SETTING_ALIASES            설정명 alias
CORE_PACKAGES              설치 여부를 확인할 핵심 패키지
EXPECTED_PYTHON_VERSION    Python 기준 버전
REQUIREMENT_OPERATORS      자동 비교할 버전 연산자
```

주의:

- 환경변수 체크 기준 파일은 현재 워크스페이스 루트의 `.env`입니다.
- `run.py`처럼 이름이 다른 단일 Python 파일도 설정 파일 후보로 사용합니다.
- AST 파싱은 문자열 literal만 안전하게 읽습니다. 동적 표현식은 값을 추론하지 않습니다.
- password는 값이 있어도 `set`만 출력합니다.
- 복잡한 pip specifier는 `version_unchecked`로 표시하고 사용자가 호환성을 직접 확인하게 합니다.

## run_training.py

책임:

- entrypoint 후보를 찾습니다.
- 실행 전 체크리스트를 만듭니다.
- `--execute`가 있을 때만 실제 학습/모델 생성 명령을 실행합니다.
- 실행 후 모델 산출물과 Ai Studio 산출물 여부를 확인합니다.

주요 수정 위치:

```text
ENTRYPOINTS                실행 파일 후보
REQUIRED_DIRS              실행 전 확인할 샘플 폴더
ARTIFACT_DIRS              산출물 폴더 후보
MLFLOW_OUTPUT_DIRS         MLflow/Ai Studio 출력 폴더 후보
AI_STUDIO_ENV_KEYS         실행 전 필요한 설정 키
MODEL_SETTING_FILES        설정 파일 후보
```

주의:

- 실행 파일이 여러 개이면 사용자 확정을 요청해야 합니다.
- `--execute`가 없으면 실제 명령을 실행하지 않습니다.
- `build_command()`는 `--prepare-only` 옵션이 있을 때만 추가합니다.

## test_inference.py

책임:

- `input_example.json`을 읽습니다.
- 모델 경로를 찾습니다.
- `mlflow.pyfunc` 또는 `aiu_custom.predict.ModelWrapper`로 추론을 시도합니다.
- 결과가 JSON 직렬화 가능한지 확인합니다.

주요 수정 위치:

```text
find_input_example()       입력 예시 파일 후보
find_model_path()          모델 경로 후보
run_pyfunc()               MLflow pyfunc 추론
run_aiu_custom()           aiu_custom wrapper 추론
```

주의:

- `--execute`가 없으면 실제 추론을 실행하지 않는 방향을 유지합니다.
- 외부 서버 호출은 하지 않습니다.
- 실패 원인은 `failures`에 누적합니다.


## response_speed_check.py

책임:

- OpenCode 응답/인덱싱 지연 원인을 찾습니다.
- ignore 패턴이 적용되어 있는지 확인합니다.
- 무거운 폴더와 큰 파일 후보를 보여줍니다.

주요 수정 위치:

```text
EXPECTED_IGNORE_PATTERNS   반드시 들어가야 하는 ignore 패턴
SLOW_DIR_NAMES             느려질 수 있는 폴더명
LARGE_SUFFIXES             대형 파일로 볼 확장자
scan_workspace()           파일 트리 스캔 정책
```

주의:

- `.opencode/` 내부는 불필요한 경고와 대형 `node_modules` 스캔에서 제외합니다.
- 기본 exit code는 fail이 있을 때만 1입니다.
- 대용량 파일 내용을 읽지 말고 stat만 사용합니다.

## apply_index_ignore.py

책임:

- `.ignore`, `.rgignore`, `.gitignore`에 관리 블록을 추가/갱신합니다.
- 폐쇄망 OpenCode 인덱싱 범위를 줄입니다.

주요 수정 위치:

```text
PATTERNS                   인덱싱 제외 패턴
TARGET_FILES               갱신할 ignore 파일 목록
managed_block()            관리 블록 생성
replace_or_append()        기존 관리 블록 교체 정책
```

주의:

- 관리 블록 밖의 사용자 ignore 내용은 보존합니다.
- 패턴을 추가하면 `.opencode/indexing/closed-network.ignore`도 같이 맞춥니다.

## test_local_sample.py

책임:

- 번들 샘플을 venv에서 테스트합니다.
- requirements 설치, prepare/register, run_model 실행을 검증합니다.

주요 수정 위치:

```text
SAMPLE_PATHS               테스트할 샘플 폴더
python_in_venv()           Windows/POSIX venv python 경로
ensure_venv()              venv 생성/재생성
test_sample()              샘플별 테스트 순서
```

주의:

- 폐쇄망 QA에서는 `--skip-install`을 사용합니다.
- Python 버전이 `3.11.9`가 아니면 실패하도록 유지합니다.
- 네트워크 설치가 필요한 상황에서는 내부 http:// PyPI/Nexus 미러와 requirements.txt 고정 버전을 우선 안내합니다.

## test_7_step_flow.py

책임:

- Windows/PowerShell 기준으로 모델 있음 AI Studio 7단계가 흐름대로 작동하는지 테스트합니다.
- 모델 목록 확인, 모델 선택, 환경 점검, 템플릿 변환, 원격 등록 차단/실행, 오류 재실행을 순서대로 검증합니다.
- 6번 추론 테스트는 기본 실행하지 않습니다. 사용자가 `--run-inference`를 명시했을 때만 실행합니다.
- 기본값은 원격 MLflow 서버를 호출하지 않고, `.env` 미입력 시 5번 단계가 안전하게 차단되는지 확인합니다.
- 숫자 선택(`--model 3`)과 Windows 백슬래시 경로(`data\...`)를 모두 검증합니다.

주요 수정 위치:

```text
REQUIRED_GENERATED_PATHS   4번 템플릿 변환 산출물 목록
verify_generated_files()   saved_model 경로, source_path, MLmodel 상대경로 검증
main()                     1~7단계 실행 순서
```

사용 예:

```text
python .opencode/scripts/qa-maintenance/test_7_step_flow.py --project . --model 3
python .opencode/scripts/qa-maintenance/test_7_step_flow.py --project . --model data/pytorch_cnn/cnn_model.pt
python .opencode/scripts/qa-maintenance/test_7_step_flow.py --project . --model 3 --run-remote
```

## Change Checklist

코드 수정 후 아래를 확인합니다.

```text
python -m py_compile .opencode/scripts/*.py
python -m json.tool .opencode/opencode.json
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project .opencode/samples/pytorch_sample --entrypoint run_model.py
python .opencode/scripts/03-environment-check/response_speed_check.py --project .
```

샘플 복사 로직을 바꿨다면 추가로 확인합니다.

```text
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --list
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample pytorch
```

## Common Failure Meaning

```text
warn:
  진행은 가능하지만 사용자 확인 또는 호환성 확인이 필요합니다.

fail/block:
  현재 단계 진행 전 수정이 필요합니다.

missing:
  파일, 폴더, 값이 없습니다.

empty:
  키는 있지만 값이 빈 문자열입니다.

set:
  값이 있습니다. secret 값 자체는 출력하지 않습니다.
```
