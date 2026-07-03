---
name: agent-mlflow-skill-sample-bootstrap
description: Use when the user says "sklearn", "pytorch", "tensorflow", "샘플 생성", "폴더째 복사", "모델이 없음", or sample bootstrap; selects one bundled sample and copies the sample folder into the workspace.
license: MIT
compatibility: opencode
metadata:
  flow: ml-workspace-development
  stage: 00-sample-bootstrap
  step: 0
---

# Sample Bootstrap

## Result First

```text
판단 결과: pass | needs_user_input | blocked
현재 단계: 0. 샘플 선택/복사
현재 대상: workspace root
핵심 판단: model_found: false일 때만 샘플 복사
다음 단계: 1. 환경 검증
```

## Workflow

```text
1. 프로젝트 분석
2. 모델 없음 확인
3. 샘플 선택
4. 샘플 폴더째 복사
5. TODO Guide 출력
6. 환경 검증으로 이동
```

## What To Do Now

```text
모델이 없으면 아래 중 하나를 선택한다.

1 -> sklearn
2 -> pytorch
3 -> tensorflow
```

Build 모드에서 사용자가 `1`, `2`, `3`만 입력해도 즉시 샘플 선택으로 처리한다.

## Output Contract

```text
반드시 보여줄 값:
- selected_sample
- sample_source_path
- target_project_path
- copy_mode: folder
- skipped_existing_files 또는 ignored_generated_files
- TODO Guide
```

샘플 복사 후 출력 UI:

```text
판단 결과: pass
selected_sample: pytorch
target_project_path: ./pytorch_sample
copy_mode: folder

TODO Guide
1. 환경 검증
2. 샘플 규격 확인/보충
3. 환경 변수 입력/export
4. 패키지 설치
5. 모델 실행 및 원격 MLflow 기록
6. 산출물 확인
```

## Commands

```text
샘플 목록:
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --list

복사 전 확인:
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample pytorch

실제 복사:
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample pytorch --execute

기존 모델 골격 보충:
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample pytorch --scaffold-existing --execute
```

<details>
<summary>자세한 판단 기준 보기</summary>

```text
pass:
- 선택한 샘플 폴더가 워크스페이스 아래로 복사됨
- 기존 대상 폴더가 있으면 누락 항목만 보충됨

needs_user_input:
- 샘플 선택이 없거나 모호함
- 덮어쓰기 여부를 사용자가 결정해야 함

blocked:
- model_found: true인데 샘플 복사를 요청함
- 샘플 원본이 없음
- 대상 경로를 쓸 수 없음
```

선택 매핑:

```text
1 | 1번 | 첫 번째 | sklearn | 사이킷런 -> sklearn
2 | 2번 | 두 번째 | pytorch | torch | 파이토치 -> pytorch
3 | 3번 | 세 번째 | tensorflow | tf | keras | 텐서플로우 | 케라스 -> tensorflow
```

</details>

<details>
<summary>문제 해결 보기</summary>

```text
증상: Build 모드에서 2를 눌렀는데 생성되지 않음
원인: 숫자 입력을 샘플 선택으로 처리하지 못함
조치: 2 -> pytorch로 즉시 매핑하고 copy command를 실행한다.

증상: save/saved_model 폴더가 빠짐
원인: 기존 폴더 보충 로직 누락
조치: 같은 copy command를 --force 없이 다시 실행해 누락 파일만 보충한다.

증상: runtest.py가 있는데 run_model.py가 새로 생김
원인: 기존 entrypoint 보호 누락
조치: runtest.py가 있으면 run_model.py를 복사하지 않는다.
```

</details>

<details>
<summary>전문가 상세 보기</summary>

복사 방식:

```text
copy_mode: folder
./sklearn_sample/
./pytorch_sample/
./tensorflow_sample/
```

필수 샘플 폴더:

```text
aiu_custom/
local_serving/
saved_model/
```

복사 제외:

```text
.venv/
__pycache__/
data/
ai_studio/
mlflow.db
.DS_Store
model/
artifacts/ai_studio/
```

</details>

<details>
<summary>Safety 규칙 보기</summary>

- 사용자 선택 없이 임의로 샘플을 복사하지 않는다.
- 모델이 발견된 워크스페이스에서는 샘플 선택을 요청하지 않는다.
- 대상 샘플 폴더가 이미 있으면 기존 파일은 유지하고 누락된 파일/폴더만 보충한다.
- `--force`는 사용자가 명시적으로 요청한 경우에만 사용한다.
- secret 값은 복사 후에도 출력하지 않는다.

</details>
