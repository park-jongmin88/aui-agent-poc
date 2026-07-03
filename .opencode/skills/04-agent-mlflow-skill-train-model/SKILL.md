---
name: agent-mlflow-skill-train-model
description: Use when the user asks "학습 실행", "모델 생성", "runtest.py", "run_model.py", "run.py", "saved_model 확인", "artifact 생성", or train model; checks local training entrypoint, model artifact creation, config, and input example.
license: MIT
compatibility: opencode
metadata:
  flow: ml-workspace-development
  stage: 03-train-model
  step: 3
---

# Local Training And Model Creation

## Result First

```text
판단 결과: pass | warn | needs_user_input | blocked
현재 단계: 5. 원격 MLflow 등록 실행
현재 대상: selected_project_path 또는 copied sample folder
핵심 판단: entrypoint 확정, 실행 성공, ai_studio 산출물 생성
다음 단계: 추론 테스트
```

## Workflow

```text
실행 기준: Windows PowerShell
   - 사용자가 직접 선택한 워크스페이스 루트에서 실행한다.
   - 예: cd '<선택한 프로젝트 경로>'
   - 모델 경로는 선택한 워크스페이스 기준 상대경로를 사용한다.

1. 모델 목록 확인
2. 모델 선택
   - `python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>`를 실행하면 그 모델을 새 선택값으로 반영한다.
   - PowerShell에서 `--model3`, `--model 3`, `data\...`, `data￦...` 입력을 모두 2번 선택으로 처리한다.
   - 번호 선택은 화면에 표시된 프로젝트 상대경로 알파벳 정렬 목록을 그대로 사용한다.
   - 번호 선택 후 프레임워크/확장자 기준으로 다시 정렬하거나 다른 모델로 해석하지 않는다.
   - 스크립트가 출력한 `선택 모델`과 `MODEL_KIND`를 최종 결과로 신뢰한다.
   - 이후 단계는 저장된 선택 모델을 계속 사용한다.
   - 4번 템플릿 변환은 반드시 `--model selected`로 실행한다.
   - 이미 선택된 모델이 있을 때 4번에서 모델 번호를 다시 넘기지 않는다.
   - 여러 모델이 있어도 스킬 변환 대상은 현재 선택 모델 하나로 유지한다.
   - `runtest_2.py` 안의 모델 경로를 다시 선택 기준으로 삼지 않는다.
3. 환경 검증
4. 템플릿 변환 (사용자 선택)
5. 원격 MLflow 등록 실행 (사용자 선택)
6. 추론 테스트 (사용자 선택)
7. 오류 재실행 (사용자 선택)
```

## What To Do Now

```text
1. 기존 모델이면 프로젝트 루트 전체와 data/** 모델 목록을 먼저 보여준다.
2. 사용할 모델을 번호 또는 경로로 선택한다.
3. MODEL_KIND를 확장자 기준으로 판별한다.
4. 워크스페이스 루트 아래에 선택 모델명 작업 폴더를 만들고, `.opencode/samples/pytorch_sample/` 템플릿을 그 폴더로 복사한 뒤, 복사된 모든 템플릿 파일을 다시 읽고 선택 모델 기준 연결부만 최소 변환한다. 단, 템플릿 `requirements.txt`는 복사하지 않는다.
5. 워크스페이스 루트의 runtest.py를 우선 읽기 전용으로 참조하고, 복사된 템플릿 파일을 선택 모델 연결부만 안전하게 변환한다.
6. 기존 runtest.py 또는 run_test.py는 절대 수정하지 않고 runtest_2.py만 선택 모델 기준으로 변환한다.
7. 모델 파일은 템플릿 폴더로 복사하지 않는다.
8. 실행 전 MLflow/AI Studio 설정 블록을 확인한다.
```

## Output Contract

```text
반드시 보여줄 값:
- 판단 결과
- 선택된 entrypoint
- 실행 command
- 실행 여부와 return code
- 생성된 metrics/code 산출물
- 누락된 산출물
- 다음 단계
```

성공 출력 UI:

```text
판단 결과: pass
entrypoint: run_model.py
command: python run_model.py
local outputs:
- ai_studio/metrics/
- ai_studio/code/
MLflow artifact:
- artifact_path="ai_studio" 아래 code/
- uri는 Windows 워크스페이스 상대경로 기준으로 업로드
- path는 MLflow 모델 패키지 내부 Linux 경로 artifacts/... 기준
```

## Commands

```text
실행 파일 자동 판단:
python .opencode/scripts/04-train-model/run_training.py --project .

원격 MLflow 등록 실행:
python .opencode/scripts/04-train-model/run_training.py --project . --execute
python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint runtest_2.py --execute

명시적 entrypoint 실행:
python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint <file> --execute
python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint run.py --execute

선택 모델 준비:
python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
python .opencode/scripts/02-model-select/select_model.py --project . --model 1
python .opencode/scripts/02-model-select/select_model.py --project . --model 'data\torch\model.pt'
python .opencode/scripts/04-train-model/prepare_selected_model.py --project . --model selected --execute

AI Studio/MLflow 연결부 보강 dry-run:
python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint <file>

AI Studio/MLflow 연결부 실제 보강:
python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint <file> --execute
```

## Artifact Map

```text
local metrics   -> ai_studio/metrics/
local code      -> ai_studio/code/
MLflow artifact -> artifact_path="ai_studio" 아래 code/
tracking target -> 사용자가 입력한 원격 MLflow tracking 서버
reference model -> saved_model/, model/, framework native model file
artifact uri    -> Windows 상대경로 사용, 예: saved_model\model.pt, config\config.json
artifact path   -> Linux 패키지 내부 경로 사용, 예: artifacts/model.pt, artifacts/config.json
kserve path     -> Linux 컨테이너의 context.artifacts 경로 사용
forbidden       -> Windows 로컬 절대경로를 KServe 런타임 경로로 사용 금지
```

<details>
<summary>자세한 판단 기준 보기</summary>

```text
pass:
- entrypoint가 확정됨
- 실행이 완료됨
- ai_studio/metrics 또는 ai_studio/code 산출물이 생성됨

warn:
- Python 버전 경고가 있지만 실행은 가능함
- MLflow logging은 실패했지만 로컬 ai_studio 산출물은 생성됨
- entrypoint는 있으나 AI Studio/MLflow 연결부 보강이 필요함

needs_user_input:
- entrypoint 후보가 여러 개임
- entrypoint 파일을 찾지 못해 사용자가 실제 파일을 직접 넣어야 함
- 기존 artifact 덮어쓰기 가능성이 있음

entrypoint를 찾지 못한 경우:
- 자동으로 run.py를 생성하지 않는다.
- 사용자가 실제 학습/모델 생성 Python 파일을 프로젝트에 직접 넣게 안내한다.
- 파일을 넣은 뒤 --entrypoint <file>로 다시 실행한다.
- tracking URL, username, password는 사용자가 직접 입력해야 함
- 5번 원격 MLflow 등록 실행의 tracking URI는 원격 `http://` 또는 `https://` URL이어야 하며 `localhost`, `127.0.0.1`, `0.0.0.0`, `file://`, `sqlite:`는 차단한다.
- mlflow_experiment_name, mlflow_register_model_name은 자동 생성 가능
- tracking URL, username, password 중 하나라도 비어 있으면 학습 테스트를 실행하지 않고 사용자가 직접 입력 후 다시 실행하도록 안내한다.

blocked:
- 학습/모델 생성 entrypoint 없음
- MLflow 필수 입력값 미입력
- 실행 후 산출물이 없음
- 필수 입력 데이터/config 없음
```

</details>

<details>
<summary>문제 해결 보기</summary>

```text
증상: run_model.py가 없다는 이유로 중단됨
원인: 실제 entrypoint 확인 없이 run_model.py로 고정함
조치: train.py, runtest.py, scripts/train.py 등 후보를 찾고 사용자에게 실제 파일명을 확인한다.

증상: 모델 실행 후 산출물이 안 보임
원인: model_info.json만 확인하거나 ai_studio/code 기준이 빠짐
조치: ai_studio/metrics, ai_studio/code, MLflow artifact_path="ai_studio" 아래 code/를 확인한다.

증상: Windows native 실행 실패
원인: standalone/native executable 경로 사용
조치: python entrypoint, mlflow.pyfunc, aiu_custom wrapper 기반 실행으로 우회한다.
```

</details>

<details>
<summary>전문가 상세 보기</summary>

기존 모델 흐름:

```text
1. 모델 목록 확인
2. 모델 선택
3. 환경 검증
   필수 패키지 5개는 항상 유지하고, 모델 형식별 추가 패키지만 반영
4. 템플릿 변환
   사용자가 4번 선택 시 실행. 템플릿 복사 후, 복사된 템플릿 기준으로 선택 모델 경로와 모델 형식 연결부를 수정
5. 원격 MLflow 등록 실행
   사용자가 5번을 선택했을 때만 실행
6. 추론 테스트
   사용자가 6번을 선택했을 때만 실행
7. 오류 재실행
   사용자가 7번을 선택했을 때만 실행
```

샘플 모델 흐름:

```text
1. selected_sample 확인
2. target_project_path 확인
3. aiu_custom/, local_serving/, saved_model/ 확인
4. 복사된 템플릿 내부에서 실제 존재하는 파일과 필요한 연결부 확인
5. run_model.py 또는 runtest.py 실행
6. ai_studio 산출물 확인
```

</details>

<details>
<summary>Safety 규칙 보기</summary>

- 오래 걸리는 학습은 예상 비용과 시간을 먼저 설명한다.
- 기존 artifact를 덮어쓸 수 있으면 실행 전 사용자 확인을 받는다.
- 샘플 원본을 직접 수정하지 않는다.
- 원격 학습이나 외부 데이터 다운로드는 기본 동작으로 가정하지 않는다.
- secret 값은 출력하지 않는다.
- Windows native/standalone executable 실행은 기본 경로로 안내하지 않는다.
- 기존 루트/data 모델 원본을 이동하거나 템플릿 폴더로 복사하지 않는다.
- 복사된 템플릿 내부 파일 구성은 고정하지 않고 비교/수정하지 않는다.

</details>
