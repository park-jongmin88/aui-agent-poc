# OpenCode MLflow Scripts

이 폴더는 `.opencode/skills`의 MLflow 흐름을 보조하는 로컬 스크립트를 포함한다. 모델이 있으면 모델 목록 확인부터 시작하는 7단계, 모델이 없으면 샘플 복사 후 6단계로 진행한다.

대상은 사용자가 지정한 모델 프로젝트 폴더다.
사용자 모델 파일은 현재 프로젝트 루트 바로 아래 또는 현재 프로젝트의 `data/**` 하위 트리 어디에나 둘 수 있으며, 자동 준비 시 모델 파일을 템플릿 폴더로 복사하지 않고 선택한 원본 경로에 연결하도록 코드를 변환한다.
`data/` 아래 폴더명은 고정값이 아니며 사용자 프로젝트마다 다를 수 있다.
예: `model.joblib`, `data/<임의폴더>/model.joblib`, `data/sklearn/model.pkl`, `data/checkpoints/model.pt`
모델 있음 흐름에서는 기존 `runtest.py`를 워크스페이스 루트에서 읽기 전용으로 참조하고, 선택 모델 기준 `runtest_2.py`를 변환한다.
모델 선택 단계는 사용할 모델만 확정한다. 4번 템플릿 변환을 사용자가 선택하면 워크스페이스 루트 아래에 선택 모델명 작업 폴더를 만들고, `.opencode/samples/pytorch_sample/` 내부 템플릿을 그 폴더로 복사한다. 이후 복사된 모든 템플릿 파일을 다시 읽고 선택 모델 기준으로 필요한 연결부만 최소 변환한다. 템플릿의 `data/`와 `requirements.txt`는 복사하지 않고, 환경검증 단계에서 모델명 작업 폴더의 `requirements.txt`를 변환한다.
모델 선택 명령은 1~2번에서 선택 모델을 확정한다. 3번 환경검증은 환경변수/requirements만 처리하고 템플릿을 복사하지 않는다. 4번 템플릿 변환은 사용자가 선택했을 때만 실행한다. `--sync-runtime`은 이미 변환된 `runtest_2.py` 기준으로 런타임 파일을 다시 맞출 때만 사용한다.
기존 `runtest.py`는 수정하지 않는다.
선택 모델에 맞는 실행/등록 파일은 `runtest_2.py`로만 변환한다.
Windows에서 MLflow에 업로드할 모델 원본 `path`는 Windows native 상대경로를 유지한다. 예: `saved_model\cnn_model.pt`. 모델 `url`과 config artifact `uri`는 KServe/서버 해석 기준과 맞추기 위해 `saved_model/cnn_model.pt`, `config/config.json` 형식으로 기록한다.
KServe/Linux에서 실제 읽는 경로는 MLflow가 모델 패키지 내부에 만든 `path: artifacts/...`이며, `aiu_custom/model.py`는 `context.artifacts`를 통해 이 Linux 경로를 읽는다.

스킬 목록 기준 스크립트 정리는 `.opencode/scripts/SCRIPT_INDEX.md`를 먼저 본다.
유지보수자는 `.opencode/scripts/MAINTENANCE.md`에서 각 스크립트의 책임, 주요 함수, 수정 포인트, 주의사항을 확인한다.

## Skill Script Map

먼저 이 표만 봅니다. 스킬에서 직접 쓰는 대표 스크립트는 아래 흐름으로 고정합니다.
실제 구현 파일은 스킬 목록 기준 폴더에 있습니다. 실행도 해당 폴더 경로를 직접 사용합니다.
도구가 읽을 수 있는 같은 매핑은 `.opencode/scripts/skill_script_map.json`에 있습니다.
사람이 읽는 상세 정리표는 `.opencode/scripts/SCRIPT_INDEX.md`에 있습니다.

```text
01 Project Analyze
    01-project-analyze/validate_mlflow_project.py      상세 분석
    launch_workspace_summary.py                        기존 런치 분석 명령 호환
   04-train-model/prepare_selected_model.py           모델 목록/선택

02 Sample Bootstrap
   02-sample-bootstrap/bootstrap_sample_project.py    sklearn/pytorch/tensorflow 샘플 복사

02 Model Select
   02-model-select/select_model.py                   2번 모델 선택 전용 PowerShell 안전 wrapper

03 Environment Check
   03-environment-check/check_environment.py          Python, requirements.txt, MLflow 설정 확인
   03-environment-check/response_speed_check.py       폐쇄망 속도 진단
   03-environment-check/apply_index_ignore.py         인덱싱 제외 적용

04 Train Model / Selected Model Build
   04-train-model/prepare_selected_model.py           runtest.py 참조 + runtest_2.py 변환
   04-train-model/run_training.py                     확정 entrypoint 실행
   04-train-model/adapt_ai_studio.py                  사용자 임의 run.py 보강용 보조 스크립트

05 Inference Test
   06-inference-test/test_inference.py                수동 추론 계약 점검
   transformed: inferencetest.py

QA / Maintenance
   qa-maintenance/doctor.py                           전체 상태 1페이지 점검
   qa-maintenance/test_local_sample.py                번들 샘플 QA
   qa-maintenance/test_7_step_flow.py                 AI Studio 7단계 흐름 QA
   SCRIPT_INDEX.md                 스킬 목록 기준 스크립트 정리표
   MAINTENANCE.md                  유지보수 상세 문서
```

## TODO Script Map

사용자에게 보이는 TODO 단계는 아래 스크립트로 연결합니다.

```text
1. 모델 목록 확인                  -> prepare_selected_model.py
2. 모델 선택                       -> 02-model-select/select_model.py --model <번호|경로>
3. 환경 검증      -> 사용자가 3번 선택 시 check_environment.py --entrypoint runtest_2.py
4. 템플릿 변환                     -> 사용자가 4번 선택 시 prepare_selected_model.py --model selected --execute
5. 원격 MLflow 등록 실행           -> 사용자가 5번 선택 시 run_training.py --entrypoint runtest_2.py --execute
6. 추론 테스트                     -> 사용자가 6번 선택 시 python inferencetest.py
7. 오류 재실행                     -> 사용자가 7번 선택 시 Failures 기준으로 실패한 단계부터 재실행
```

화면에 표시된 모델 번호나 TODO 단계 번호는 숫자 키로 입력하면 바로 선택/실행한다. 4번 템플릿 변환은 사용자가 4번을 선택했을 때만 실행한다.
모델 목록이 표시되면 맨 처음에 `사용자는 숫자 예시 1번부터 선택합니다`를 강조해서 보여준다.
자연어로도 선택할 수 있다. 예: `첫 번째 모델`, `파이토치 모델`, `data/... 사용`.
모델 선택 명령에서 `python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>`를 실행하면 그 모델을 새 선택값으로 반영한다.
이후 단계는 저장된 선택 모델을 재사용하고, 4번 템플릿 변환은 반드시 `--model selected`로 실행한다.
이미 선택된 모델이 있을 때 `prepare_selected_model.py --model <다른번호> --execute`가 들어오면 모델을 바꾸지 않고 2번 선택 스크립트로 다시 선택하도록 차단한다.
여러 모델이 있어도 `runtest_2.py`, `aiu_custom/`, `local_serving/`, `config/`, `input_example.json` 변환은 현재 선택 모델 하나만 기준으로 수행한다.
`runtest_2.py` 안의 모델 경로는 변환 결과물일 뿐 선택 기준으로 사용하지 않는다.

기존 모델 흐름에서 `runtest_2.py`가 있으면 Ai Studio 빌드 모드 숫자 입력은 TODO 단계로 처리한다.

```text
1 -> python .opencode/scripts/launch_workspace_summary.py .
2 -> python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>
3 -> python .opencode/scripts/03-environment-check/check_environment.py --project . --entrypoint runtest_2.py
4 -> python .opencode/scripts/04-train-model/prepare_selected_model.py --project . --model selected --execute
5 -> python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint runtest_2.py --execute
6 -> 사용자가 선택하면 python inferencetest.py
7 -> Failures와 오류 메시지 기준으로 수정 후 실패한 단계부터 재실행
```

6번 추론 테스트는 자동 실행하지 않는다. 사용자가 6번을 선택하거나 QA에서 `--run-inference`를 명시한 경우에만 실행한다.

Windows PowerShell에서는 선택 프로젝트의 실행 폴더로 이동한 뒤 실행한다.

```powershell
cd '<selected-project-path>'
python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint runtest_2.py --execute

python inferencetest.py
```

워크스페이스 첫 분석은 아래 명령으로 실행한다. 기존 런치 가이드 호환 명령도 같은 분석 스크립트로 연결된다.

```powershell
python .opencode/scripts/launch_workspace_summary.py .
python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
```

`1~2`는 모델 목록 확인 -> 모델 선택 흐름이다. `3`은 환경 검증이며, 템플릿을 복사하지 않는다. `4` 템플릿 변환은 사용자가 선택했을 때 실행되며, `input_example.json`, `config/config.json`도 선택 모델 기준으로 변환한다. 템플릿 복사에서는 `data/`와 `requirements.txt`를 복사하지 않는다.
필수 패키지 기준은 `03-environment-check/requirements.required.txt`에서 관리한다.

`3`은 모델 환경변수와 패키지 상태 체크다. 선택 모델명 작업 폴더에 `requirements.txt`가 없으면 필수 5개 기준으로 변환하고, 변환된 코드 import 기준 추가 Python 패키지가 필요하면 `requirements.txt`를 변환한다. 이때도 필수 패키지 5개는 절대 제거하지 않는다. 선택 모델명 작업 폴더에 `.env`가 없으면 MLflow 5개 키만 `""` 값으로 생성하고, 이미 있으면 복사하거나 덮어쓰지 않는다. MLflow 설정은 선택 모델명 작업 폴더의 `.env` 5개 값을 `set`, `empty`, `missing` 상태로만 표시한다. secret 값은 출력하지 않는다.

패키지 설치 기준:

```text
JavaScript 프로젝트(package.json 있음) -> npm i
Python 샘플/모델(requirements.txt 있음) -> 로컬 자동 설치 안 함, requirements.txt 변환과 상태 확인만 수행
폐쇄망 PC -> 필요 시 사용자가 내부 http:// PyPI/Nexus 미러로 직접 설치
PyTorch CPU wheel Nexus upstream -> https://download.pytorch.org/whl/cpu
torch SSL 설치 금지 -> https://download.pytorch.org, https://pypi.org 인덱스를 직접 쓰지 않고 http:// 내부 미러만 사용
Bun 사용 금지 -> opencode Bun 런타임이 파일 트리 오류 처리 중 세그멘테이션 폴트를 낼 수 있으므로 bun, bunx, bun install, bun run 실행하지 않음
```

## Closed-Network Response Speed

OpenCode가 폐쇄망 Windows에서 응답하거나 파일 트리를 인덱싱하는 속도가 느리면 먼저 진단을 실행한다.

```text
python .opencode/scripts/03-environment-check/response_speed_check.py --project .
```

그 다음 ignore 파일을 적용한다.

```text
python .opencode/scripts/03-environment-check/apply_index_ignore.py --project .
```

이 명령은 워크스페이스 루트의 `.ignore`, `.rgignore`, `.gitignore`에 관리 블록을 추가한다. 제외 대상은 `.opencode/`, `.opencode/node_modules/`, `.venv/`, `node_modules/`, `ai_studio/tracking/`, `ai_studio/code/`, `saved_model/`, `datasets/`, `*.pt`, `*.pkl`, `*.safetensors`, `*.bst`, `*.ubj` 같은 스킬 번들/생성물/대용량 모델 파일이다.

자세한 운영 기준은 `.opencode/performance/CLOSED_NETWORK_SPEED.md`를 본다.

## Scripts

### doctor.py

Ai Studio/빌드/skills/sample/env 상태를 한 화면에서 점검한다. 주니어 QA나 폐쇄망 Windows에서 먼저 실행하기 좋다.

```text
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project .
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project . --entrypoint runtest.py
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project . --entrypoint run.py
python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project . --json
```

확인 항목:

```text
1. OpenCode 패키지/opencode.json/01~06 스킬 폴더
2. Python 3.11.9 환경
3. requirements.txt 패키지 설치/버전 상태
4. model_artifact_paths와 MODEL_KIND
5. 실행 파일 확정
6. Ai Studio 코드 적합성
7. `.env` MLflow 5개 값과 requirements.txt 상태
```

### prepare_selected_model.py

현재 프로젝트 루트 바로 아래와 `data/**` 아래 모델 파일 목록을 만들고, 사용자가 선택한 모델 기준으로 기존 `runtest.py`를 참조해 `runtest_2.py`만 변환한다.
`runtest_2.py`는 외부 데이터셋을 다운로드하지 않고 MODEL_KIND에 맞는 synthetic `input_example.json`으로 변환한다.
기존 `runtest.py`는 수정하지 않고 참조만 한다.
PyTorch/safetensors 모델은 `.opencode/samples/pytorch_sample/` 내부를 참조해서 선택 모델 실행/등록에 필요한 연결부만 안전하게 변환한다. 샘플 `requirements.txt`는 참조하지 않는다.
선택 모델 경로와 `MODEL_KIND`를 반영한다.
`runtest_2.py` 변환 시퀀스는 `모델 선택 -> 모델 형식 확인 -> 기존 runtest.py 읽기 전용 참조 -> 선택 모델 경로와 MODEL_KIND를 반영한 연결부 변환 -> 변환 결과 검증` 순서로 수행한다.

```text
python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
python .opencode/scripts/02-model-select/select_model.py --project . --model 1
python .opencode/scripts/02-model-select/select_model.py --project . --model model.joblib
python .opencode/scripts/02-model-select/select_model.py --project . --model 'data\<임의폴더>\model.joblib'
python .opencode/scripts/02-model-select/select_model.py --project . --model 'data\torch\model.pt'
python .opencode/scripts/04-train-model/prepare_selected_model.py --project . --model selected --execute
# 보정용: 이미 선택된 모델 기준으로 런타임 파일만 다시 맞출 때 사용
python .opencode/scripts/04-train-model/prepare_selected_model.py --project . --sync-runtime --execute
```

숫자 선택은 프로젝트 기준 상대경로 알파벳 정렬의 `model_artifact_paths` 순서를 사용한다. 같은 파일 목록이면 분석 화면과 준비 스크립트의 번호가 항상 같다. 자동 재실행에는 실제 모델 경로 또는 `--model selected`도 사용할 수 있다.

출력 항목:

```text
model_artifact_paths
selected_model_path
MODEL_KIND
reference_entrypoint: runtest.py, run_test.py 중 하나
transformed_entrypoint: runtest_2.py
```

지원 모델 형식:

```text
.pkl        -> sklearn_pickle
.joblib     -> sklearn_joblib
.pt, .pth   -> pytorch
.onnx       -> onnx
.keras      -> tensorflow_keras
.h5         -> tensorflow_h5
.safetensors -> safetensors
.bst        -> xgboost_bst
.ubj        -> xgboost_ubj
```

### adapt_ai_studio.py

사용자가 가져온 임의 Python 실행 파일을 Ai Studio/MLflow 연결 형식에 맞게 보강한다. 기본은 dry-run이며, `--execute`를 붙인 경우에만 실제 파일을 수정한다.
실행 파일을 찾지 못하면 자동 생성하지 않는다. 사용자가 실제 학습/모델 생성 Python 파일을 프로젝트에 직접 넣고 `--entrypoint <file>`로 지정해야 한다.
파일 후보가 여러 개일 때도 추측하지 않고 사용자가 직접 지정한다.

```text
python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint run.py
python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint run.py --execute
```

수정 방식:

```text
- entrypoint 백업 생성: <file>.ai_studio.bak
- `.env` MLflow 5개 값, MLFLOW_* export helper 삽입
- ai_studio/metrics, ai_studio/code 경로 helper 삽입
- aiu_custom/predict.py, local_serving/serve.py, saved_model/, input_example.json 보충
- requirements.txt가 없으면 프레임워크/Import 기반 최소 패키지 작성
- 루트/data 모델 원본은 복사하거나 이동하지 않음
```

기존 파일은 기본적으로 덮어쓰지 않는다. 이미 adapter block이 있으면 `--force`가 없을 때 건너뛴다.

### validate_mlflow_project.py

모델 프로젝트 폴더를 분석한다.

```text
python .opencode/scripts/01-project-analyze/validate_mlflow_project.py --project .
python .opencode/scripts/01-project-analyze/validate_mlflow_project.py --project . --json
python .opencode/scripts/launch_workspace_summary.py .
```

### bootstrap_sample_project.py

모델 프로젝트 폴더에 실행 가능한 모델이 없을 때, 샘플 3개 중 하나를 선택해 워크스페이스 아래로 샘플 폴더째 복사한다.

선택 가능한 샘플은 원본에 `aiu_custom/`, `local_serving/`, `saved_model/` 기본 폴더가 있어야 한다.

샘플 목록:

```text
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --list
```

복사 전 확인:

```text
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample sklearn
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample pytorch
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample tensorflow
```

실제 폴더 복사:

```text
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample sklearn --execute
```

기존 모델이 있지만 샘플 규격 폴더/파일이 부족한 경우, 기존 모델 파일을 덮어쓰지 않고 없는 골격만 복사한다.

```text
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample pytorch --scaffold-existing --execute
```

복사 대상은 소스 구조 중심이며 `data/`, `.venv/`, `__pycache__/`, `model/`, `artifacts/ai_studio/`, `ai_studio/`, `mlflow.db` 같은 샘플 데이터/생성 산출물은 제외한다.

복사 후 `aiu_custom/`, `local_serving/`, `saved_model/` 필수 폴더는 항상 복사된 샘플 폴더 안에 보장한다.

복사 후 다음 단계는 아래 순서로 안내한다.

```text
1. 환경 검증
2. 샘플 규격 확인/보충
3. 환경 변수 입력/export
4. 패키지 설치
5. 모델 실행 및 원격 MLflow 기록
6. 산출물 확인
```

기존 파일이 있을 때 덮어쓰기는 사용자가 명시적으로 요청한 경우에만 사용한다.

```text
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample sklearn --execute --force
```

### check_environment.py

Python 3.11.9, dependency, MLflow 3.13.0, 원격 MLflow 서버 version, `.env` 상태를 확인한다.
Python 기준 버전은 3.11.9이다. 다른 버전이면 `version_mismatch:python`으로 분류한다.
`requirements.txt`가 있으면 필요한 pip 패키지 목록, 현재 설치 여부, 설치된 버전, 요구 버전, 버전 불일치 여부를 함께 출력한다.
환경검증 화면에는 설치 기준 파일을 `requirements.txt`로 별도 표시한다.
환경검증은 현재 워크스페이스에 실제 존재하는 Python 파일들의 import를 확인해 누락된 Python 패키지를 `requirements.txt`에 추가한다. 대표 예시는 `runtest_2.py`, `aiu_custom/model.py`, `aiu_custom/predict.py`, `inferencetest.py`다. 패키지 불일치/미설치가 있어도 로컬 dependency 설치는 자동 실행하지 않고, 상태와 필요 시 사용자 직접 설치 명령만 안내한다.
`mlflow_tracking_uri`이 있으면 원격 MLflow 서버의 `/version`을 확인하고, 서버 version과 로컬 `mlflow` 설치 version 및 `requirements.txt` 요구 version이 다르면 불일치로 표시한다.
Python 버전이 다르면 `차단 항목 요약`에 다음 형식으로 표시한다.

```text
1. Python 버전 차이 (<현재버전> vs 기대 3.11.9) → 호환성 확인 필요
```

Secret 값은 출력하지 않고 `set`, `empty`, `missing` 상태만 출력한다.

MLflow 인증용 환경 변수는 다음 이름을 사용한다.

```text
MLFLOW_TRACKING_URI
MLFLOW_TRACKING_USERNAME
MLFLOW_TRACKING_PASSWORD
MLFLOW_EXPERIMENT_NAME
MLFLOW_REGISTER_MODEL_NAME
MLFLOW_EXPERIMENT_ID
```

`MLFLOW_EXPERIMENT_PASSWORD`는 올바른 MLflow 인증 환경변수가 아니다.

학습 모델 생성 필수 파일:

```text
.env
```

사용자가 직접 입력할 키:

```text
mlflow_tracking_uri
mlflow_tracking_username
mlflow_tracking_password
```

자동 생성되는 키:

```text
mlflow_experiment_name
mlflow_register_model_name
```

작성 예시:

```text
mlflow_tracking_uri=http://<tracking-server>
mlflow_tracking_username=
mlflow_tracking_password=
```

사용자는 선택 모델명 작업 폴더의 `.env`에 MLflow 5개 값을 직접 입력한다.
`mlflow_tracking_uri`은 원격 MLflow/리포트 URI만 사용한다. `http://` 또는 `https://`를 입력하고, `file://` 로컬 tracking은 사용하지 않는다.
tracking URL, username, password 중 하나라도 비어 있으면 학습 테스트 실행을 중단한다. 사용자가 값을 직접 입력한 뒤 다시 실행한다.
환경 변수 입력 후 `run_model.py`는 설정 블록 값을 아래 환경 변수로 export한다.

```text
mlflow_tracking_uri -> MLFLOW_TRACKING_URI
mlflow_tracking_username -> MLFLOW_TRACKING_USERNAME
mlflow_tracking_password -> MLFLOW_TRACKING_PASSWORD
mlflow_experiment_name -> MLFLOW_EXPERIMENT_NAME
mlflow_register_model_name -> MLFLOW_REGISTER_MODEL_NAME
```

원격 배포 기본값은 `mlflow_tracking_uri = ""`이다. 자동 tracking URI나 로컬 테스트용 URI를 넣지 않으므로 사용자가 직접 원격 MLflow/리포트 URI를 입력해야 한다. MLflow artifact는 `artifact_path="ai_studio"` 아래 `ai_studio/code` 구조로 기록하고, 확인용 산출물은 `ai_studio/metrics/`, `ai_studio/code/`에 생성한다.
Windows 워크스페이스 기준으로 준비/등록을 실행하며, MLflow에 전달하는 `code_paths`는 `aiu_custom`, 모델 artifact uri는 `saved_model\...`, config artifact uri는 `config/config.json` 같은 상대경로를 사용한다. KServe에 올라간 뒤에는 MLflow가 넘겨주는 Linux 컨테이너 내부 `context.artifacts["model"]`, `context.artifacts["config"]` 경로를 최우선으로 사용한다. Windows 로컬 절대경로는 KServe 런타임 경로로 사용하지 않는다.

PyTorch 샘플 기본값은 `mlflow_experiment_name=pytorch_sample`, `mlflow_register_model_name=pytorch_sample_model`이다.
`mlflow_tracking_password` 값은 출력하지 않는다.

```text
python .opencode/scripts/03-environment-check/check_environment.py --project .
python .opencode/scripts/03-environment-check/check_environment.py --project . --entrypoint run.py
python .opencode/scripts/03-environment-check/check_environment.py --project . --json
```

### run_training.py

기존 모델 프로젝트를 실행한다. 모델이 없고 샘플을 가져와야 하면 먼저 `bootstrap_sample_project.py`로 사용자가 선택한 샘플 폴더를 복사한다.

기본값은 안전 모드다. 실제 실행은 `--execute`를 명시해야 한다.
실행 전 `.env` 필수 키가 있는지 확인한다.

```text
python .opencode/scripts/04-train-model/run_training.py --project .
python .opencode/scripts/04-train-model/run_training.py --project . --execute
```

폐쇄망 모델 선택 샘플:

```text
sklearn
pytorch
tensorflow
```

다른 샘플은 임의로 선택하지 않는다.

### test_local_sample.py

선택형 샘플 자체를 테스트한다.

```text
python .opencode/scripts/qa-maintenance/test_local_sample.py --sample sklearn
python .opencode/scripts/qa-maintenance/test_local_sample.py --sample all
```

### test_7_step_flow.py

Windows/PowerShell 기준으로 모델 있음 7단계가 순서대로 끊기지 않는지 테스트한다.

```text
python .opencode/scripts/qa-maintenance/test_7_step_flow.py --project . --model 3
python .opencode/scripts/qa-maintenance/test_7_step_flow.py --project . --model data/pytorch_cnn/cnn_model.pt
```

기본 동작은 원격 MLflow 서버를 호출하지 않고, `.env` 미입력 시 5번 단계가 안전하게 차단되는지 확인한다. 숫자 선택(`--model 3`)과 Windows 백슬래시 경로(`data\...`)를 모두 검증할 수 있다. 실제 원격 등록까지 검증할 때만 `--run-remote`를 붙인다.

### inferencetest.py

`prepare_selected_model.py --execute`가 선택 모델 기준으로 변환하는 원격 추론 테스트 파일이다. 사용자가 `req_url`에 배포된 추론 URL을 직접 입력하고, `input_example.json`을 HTTP POST로 전송한다.

기본 실행은 화면 출력만 수행하며 원격 추론 URL은 사용자가 직접 입력한다.

PowerShell에서는 선택 프로젝트 루트에서 실행한다.

```powershell
python inferencetest.py
```

## Safety

- 실제 학습/추론 실행은 `--execute`가 있을 때만 수행한다.
- secret 값은 출력하지 않는다.
- 샘플 원본은 직접 수정하지 않는다.
- 모델 프로젝트 폴더에 기존 작업 경로가 있으면 기본적으로 덮어쓰지 않는다.
