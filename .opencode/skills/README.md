# OpenCode MLflow Skills

이 폴더는 ML 전문가와 주니어가 같은 흐름으로 MLflow 모델 프로젝트를 점검할 수 있게 돕는 OpenCode skill 모음입니다.

## Workflow

```text
01. Project Analyze
   model_found: true | false 결정
   모델 있음이면 루트/data 모델 목록과 사용할 모델을 먼저 확정

02. Sample Bootstrap
   모델이 없으면 1 sklearn / 2 pytorch / 3 tensorflow 선택

03. Environment Check
   Python 3.11.9, dependency, MLflow 3.13.0, 원격 MLflow 서버 version, 설정 상태 확인

04. Train Model
   선택 모델 기준 runtest_2.py 변환 또는 실제 entrypoint 실행

05. Inference Test
   input_example 기반 predict contract와 schema 확인
```

## Existing Model Process

전제:

- 실행 기준은 Windows PowerShell이다. 사용자는 먼저 직접 선택한 워크스페이스 루트로 이동한 뒤 `python .opencode/scripts/...` 명령을 실행한다.
- 예: `cd '<선택한 프로젝트 경로>'`
- 모든 스크립트 명령은 `--project .`로 실행한다. 절대경로를 넣지 않는다.
- 모델 경로 입력은 선택한 워크스페이스 기준 상대경로만 사용한다. 예: `data\pytorch_cnn\cnn_model.pt`
- 절대경로 예시인 `C:\...`, `/Users/...`, `/home/...`는 모델 선택/스크립트 명령에 사용하지 않는다.
- 사용자가 가져온 모델 파일은 현재 프로젝트 루트 바로 아래 또는 현재 프로젝트의 `data/**` 하위 트리 어디에나 둘 수 있다.
- 모델 검색은 사용자가 선택한 `--project` 폴더 안에서만 수행한다. 검색 범위는 선택한 워크스페이스 루트 바로 아래 모델 파일과 그 안의 `data/**` 트리다.
- 모델 연결은 선택한 워크스페이스 경로 기준 상대경로를 사용한다.
- 상위 폴더, 홈 디렉터리, 드라이브 루트, 임의 하위 폴더, 번들 샘플 폴더를 자동 검색하지 않는다.
- `data/sklearn/model.pkl`, `data/checkpoints/model.pt`처럼 `data/` 아래 폴더명이 달라도 모델로 인식한다.
- 지원 확장자: `.pkl`, `.joblib`, `.pt`, `.pth`, `.onnx`, `.h5`, `.keras`, `.safetensors`, `.bst`, `.ubj`.
- 선택 모델 파일은 템플릿 폴더로 복사하지 않고, 변환된 코드는 선택 모델 원본 경로에 연결한다.
- 모델 선택 단계에서는 사용할 모델만 확정하고 이후 단계가 같은 선택 모델을 계속 사용한다.
- 템플릿 변환은 사용자가 4번을 선택했을 때만 실행한다.
- 4번 템플릿 변환에서 기존 `runtest.py`를 읽기 전용으로 참조해 `runtest_2.py`를 변환한다.
- 4번 템플릿 변환에서 템플릿을 복사한 뒤 `aiu_custom/`, `local_serving/`, `saved_model/`, `config/config.json`, `input_example.json`을 선택 모델 기준으로 변환한다.
- `data/`와 `requirements.txt`는 템플릿에서 복사하지 않고, `requirements.txt`는 3번 환경검증에서 워크스페이스 루트에 변환한다.
- 사용자에게 프로세스를 보여줄 때는 현재 복사/변환 흐름만 보여주고 하위 호환 또는 미사용 경로 설명은 넣지 않는다.
- 복사된 템플릿 파일 구성은 고정하지 않고 비교/수정하지 않는다.
- `data/` 원본에는 새 파일을 생성하지 않는다.
- 기존 `runtest.py`는 선택 모델명 작업 폴더에 복사된 템플릿을 기준으로 읽기 전용 참조한다.
- 기존 `runtest.py` 또는 `run_test.py`는 덮어쓰지 않는다.
- 기존 `runtest.py`는 절대 수정하지 않고 `runtest_2.py`만 선택 모델 기준으로 변환한다.
- `runtest_2.py`는 참조한 `runtest.py` 구조를 기반으로 변환한다.
- 모델 경로/MODEL_KIND/로더는 선택 모델 실행/등록 연결부 기준으로 변환한다.
- 선택된 모델 종류에 맞춰 `load_selected_model()`, `required_package`, `load_hint` 연결부를 변환한다.
- 3번 환경변수 체크는 선택 모델명 작업 폴더의 `.env` 파일을 기준으로 5개 값을 확인한다.
- `.env` 필수 키: `mlflow_tracking_uri`, `mlflow_tracking_username`, `mlflow_tracking_password`, `mlflow_experiment_name`, `mlflow_register_model_name`.
- `mlflow_tracking_uri`은 사용자가 직접 입력하되, 5번 실행에서는 원격 `http://` 또는 `https://` URI만 허용한다. `localhost`, `127.0.0.1`, `0.0.0.0`, `file://`, `sqlite:`는 차단한다.
- `mlflow_experiment_name`, `mlflow_register_model_name`은 선택 모델 파일명에서 확장자를 제거한 이름 기준으로 자동 생성한다.
- secret 값은 출력하지 않고 `set`, `empty`, `missing` 상태만 확인한다.

```text
Step 1. 모델 목록 확인
        현재 --project 루트 바로 아래와 그 안의 data/**에서 지원 모델 확장자 10개를 검색한다.
Step 2. 모델 선택
        model_artifact_paths를 선택한 워크스페이스 기준 상대경로 알파벳 순서로 번호 표시한다.
        `python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>`를 실행하면 그 모델을 새 선택값으로 반영한다.
        PowerShell에서 `--model3`, `--model 3`, `data\...`, `data￦...` 입력을 모두 2번 선택값으로 정규화한다.
        같은 파일 목록이면 분석 화면과 준비 스크립트의 번호가 항상 같다.
        이후 `--model` 없이 진행하는 단계는 저장된 선택 모델을 계속 사용한다.
        이미 준비된 선택 모델은 --model selected로 재사용한다.
        runtest_2.py 안의 경로는 선택 기준으로 사용하지 않는다.
        선택이 없으면 자동 준비를 진행하지 않고 선택 요청으로 멈춘다.
        모델 선택 후에도 3~7번을 자동 실행하지 않고, 사용자가 선택한 단계 1개만 실행한다.
Step 3. 환경 검증
        사용자가 3번을 선택했을 때만 실행한다.
        선택 모델명 작업 폴더의 .env 파일에서 MLflow 5개 값 상태를 확인한다.
        requirements.txt 필수 5개 패키지는 .opencode/scripts/03-environment-check/requirements.required.txt 기준을 사용하며 절대 제거하지 않는다.
        Python 3.13에서 kserve 호환성 문제가 있어도 kserve==0.15.0은 제거하지 않고 Python 3.11.9 환경으로 전환하도록 안내한다.
        변환된 코드 import 기준 추가 Python 패키지가 필요하면 requirements.txt 반영 필요 여부만 안내한다.
        로컬 dependency 설치는 자동 실행하지 않는다.
Step 4. 템플릿 변환
        사용자가 4번을 선택했을 때만 실행한다.
        워크스페이스 루트 아래 선택 모델명 작업 폴더를 만들고 .opencode/samples/pytorch_sample/ 템플릿을 먼저 복사한다.
        복사된 모든 템플릿 파일을 다시 읽은 뒤 선택 모델 기준 연결부만 최소 변환한다.
        기존 runtest.py를 읽기 전용으로 참조해 runtest_2.py를 변환한다.
        복사된 템플릿 기준으로 선택 모델 경로와 모델 형식 연결부를 수정한다.
        `--sync-runtime`은 이미 선택된 모델 기준으로 런타임 파일을 다시 맞출 때 사용한다.
        내부 일치 검증은 선택된 runtest_2.py와 런타임 파일 기준으로 수행한다.
Step 5. 원격 MLflow 등록 실행
        사용자가 5번을 선택했을 때만 실행한다.
        run_training.py가 먼저 선택 모델 기준으로 runtest_2.py와 런타임 파일을 재검증/변환한 뒤 원격 MLflow 등록을 실행한다.
Step 6. 추론 테스트
        선택 모델 환경으로 변환된 local serving 입력/출력 스키마를 확인한다.
        사용자가 6번을 선택했을 때만 진행한다.
        자동 실행하지 않는다.
        local_serving/ 폴더는 Step 4 템플릿 변환 시퀀스에서 선택 모델 기준으로 변환되어 있어야 한다.
Step 7. 오류 재실행
        사용자가 7번을 선택했을 때만 진행한다.
        MLflow 등록 또는 추론 테스트 중 오류가 있으면 Failures와 오류 메시지를 기준으로 수정한 뒤 실패한 단계부터 다시 실행한다.
```

```text
python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
python .opencode/scripts/02-model-select/select_model.py --project . --model 1
```

## Folder Order

```text
01-agent-mlflow-skill-project-analyze
02-agent-mlflow-skill-sample-bootstrap
03-agent-mlflow-skill-environment-check
04-agent-mlflow-skill-train-model
06-agent-mlflow-skill-inference-test
```

폴더명은 순서 표시용입니다. 각 `SKILL.md`의 `name:` 값은 기존 호출 호환성을 위해 변경하지 않습니다.

## Script Map

스킬별 대표 스크립트는 아래만 먼저 봅니다. 실제 구현 파일은 스킬 목록 기준 폴더에 있습니다.
같은 매핑은 `.opencode/scripts/skill_script_map.json`에도 있습니다.
상세 정리표는 `.opencode/scripts/SCRIPT_INDEX.md`에 있습니다.

```text
01 Project Analyze
   01-project-analyze/validate_mlflow_project.py
        04-train-model/prepare_selected_model.py

02 Sample Bootstrap
   02-sample-bootstrap/bootstrap_sample_project.py

02 Model Select
   02-model-select/select_model.py

03 Environment Check
   03-environment-check/check_environment.py
   03-environment-check/response_speed_check.py
   03-environment-check/apply_index_ignore.py

04 Train Model / Selected Model Build
   04-train-model/prepare_selected_model.py
   04-train-model/run_training.py
   04-train-model/adapt_ai_studio.py

05 Inference Test
   06-inference-test/test_inference.py
   generated: inferencetest.py

QA / Maintenance
   qa-maintenance/doctor.py
   qa-maintenance/test_local_sample.py
   SCRIPT_INDEX.md
   MAINTENANCE.md
```

## Doctor

전체 흐름을 한 번에 점검할 때는 doctor를 먼저 실행합니다.

```text
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project .
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project . --entrypoint runtest.py
```

doctor는 실행 파일 확정, 샘플 규격, `.env` MLflow 5개 값, 산출물 상태를 한 화면에 보여줍니다.
`requirements.txt`가 있으면 pip 필요 패키지, 현재 설치 여부, 설치된 버전, 요구 버전, 버전 불일치도 함께 보여줍니다.
`run.py`처럼 실행 파일명이 사용자마다 달라도 루트의 단일 `.py` 파일은 자동으로 잡습니다. 여러 후보가 있으면 `--entrypoint <file>`로 확정합니다.
실행 파일을 찾지 못하면 자동 생성하지 않고, 사용자가 실제 학습/모델 생성 Python 파일을 직접 넣도록 안내합니다.

AI Studio/MLflow 연결부를 실제로 보강해야 하면 먼저 dry-run을 실행합니다.

```text
python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint <file>
python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint <file> --execute
```

## Common UI Pattern

각 스킬은 `판단 결과`를 먼저 보여주고, 자세한 설명은 접기 영역에 둡니다.

```text
Result First
Workflow
What To Do Now
Output Contract
Commands
Artifact Map
details: 자세한 판단 기준
details: 문제 해결
details: 전문가 상세
details: Safety 규칙
```

## Status Meaning

```text
pass:
  정상 또는 다음 단계 진행 가능

warn:
  진행 가능하지만 호환성/권한/환경 확인 필요

needs_user_input:
  사용자가 값, 파일명, 샘플 선택, 덮어쓰기 여부를 결정해야 함

blocked:
  현재 단계 진행 불가. 원인 해결 필요
```

## Artifact Map

```text
local metrics   -> ai_studio/metrics/
local code      -> ai_studio/code/
MLflow artifact -> artifact_path="ai_studio" 아래 code/
tracking target -> 사용자가 입력한 원격 MLflow tracking 서버
```

## Shared Safety

- Launch 모드는 읽기 전용입니다.
- Build 모드에서만 파일 복사, 수정, 설치, 실행을 수행합니다.
- secret 값은 출력하지 않고 `set`, `empty`, `missing` 상태만 표시합니다.
- Bun은 사용하지 않습니다.
- JavaScript 패키지 설치가 필요하고 `package.json`이 있으면 `npm i`만 사용합니다.
- 폐쇄망에서는 `requirements.txt` 기준으로 내부 `http://` PyPI/Nexus 미러를 사용합니다.
- torch는 SSL/HTTPS 인덱스로 직접 설치하지 않습니다. 내부 `http://` PyPI/Nexus 미러만 사용합니다.
- PyTorch CPU wheel의 Nexus proxy upstream 참고 URI는 `https://download.pytorch.org/whl/cpu`입니다.
- Windows에서는 `standaloneExecutable` 또는 native executable 흐름보다 Python script 흐름을 우선합니다.
- 폐쇄망 응답이 느리면 `python .opencode/scripts/03-environment-check/response_speed_check.py --project .` 후 `python .opencode/scripts/03-environment-check/apply_index_ignore.py --project .`를 실행합니다.
