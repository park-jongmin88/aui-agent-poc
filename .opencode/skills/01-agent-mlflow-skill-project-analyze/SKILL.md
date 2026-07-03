---
name: agent-mlflow-skill-project-analyze
description: Use when the user asks "분석해줘", "MLflow 모델 프로세스", "모델 있음/없음", "워크스페이스 분석", or project structure analysis; analyzes framework, entrypoint, artifact, config, input example, aiu_custom/local_serving/saved_model.
license: MIT
compatibility: opencode
metadata:
  flow: ml-workspace-development
  stage: 01-project-analyze
  step: 1
---

# Project Structure Analysis

## Result First

```text
판단 결과: pass | needs_user_input | blocked
현재 단계: 1. 프로젝트 분석
현재 대상: workspace root 또는 user project path
핵심 판단: model_found: true | false
다음 단계: 모델 있음 -> 루트/data 모델 목록과 사용할 모델 선택 / 모델 없음 -> 샘플 선택
```

## Workflow

```text
실행 기준: Windows PowerShell
   - 사용자가 직접 선택한 워크스페이스 루트에서 실행한다.
   - 예: cd '<선택한 프로젝트 경로>'
   - 모델 경로는 선택한 워크스페이스 기준 상대경로를 사용한다.

1. 모델 목록 확인
2. 모델 선택
3. 환경 검증
4. 템플릿 변환
5. 원격 MLflow 등록 실행
6. 추론 테스트
7. 오류 재실행
```

## What To Do Now

```text
1. 현재 워크스페이스 경로를 확인한다.
2. 프로젝트 루트 전체와 data/** 모델 원본 파일을 model_artifact_paths로 나열한다.
3. `.csv`는 모델이 아니라 데이터 파일로 data_file_paths에 표시한다.
4. `.opencode/` 전체는 스킬 번들이므로 분석 대상에서 제외한다.
5. 아래 3가지 케이스 중 하나로 먼저 분기한다.
6. case 1: `.py`, `.ipynb`에서 `model.fit()`, `model.compile()`, `torch.save()` 중 하나가 감지되면 학습 코드 있음으로 판단하고 해당 프레임워크 템플릿 변환을 안내한다.
7. case 2: 학습 코드는 없고 `.pth`, `.pt`, `.pkl`, `.joblib`, `.h5`, `.keras`, `.onnx`, `SavedModel` 폴더 등 Pre-trained 모델 파일만 있으면 모델 선택 흐름으로 안내한다.
8. case 3: 학습 코드와 모델 파일이 모두 없으면 샘플 선택 흐름으로 안내한다.
9. model_found 값은 case 1 또는 case 2이면 true, case 3이면 false로 표시한다.
10. case 1 학습 코드가 있으면 `.py`, `.ipynb` 학습 코드 후보를 2번 목록에 번호로 표시한다.
11. case 2 모델 artifact가 있으면 model_artifact_paths를 프로젝트 상대경로 알파벳 순서로 번호 표시하고, 모델이 없으면 1 sklearn / 2 pytorch / 3 tensorflow 선택지를 보여준다.
12. 번호 선택은 표시된 model_artifact_paths 순서 그대로 처리하며, 프레임워크/확장자 기준으로 다시 정렬하지 않는다.
```

## Output Contract

```text
반드시 보여줄 값:
- model_found: true | false
- analysis_case: case 1 training code | case 2 pre-trained model artifact | case 3 no model
- selected_project_path
- framework
- train_entrypoint
- inference_entrypoint
- model_artifact_path
- model_artifact_paths
- data_file_paths
- entrypoint_paths
- training_code_paths
- selected_data_model_path
- MODEL_KIND
- input_example_path
- 발견 항목
- 누락 항목
- 다음 단계
```

모델이 있으면:

```text
판단 결과: pass
model_found: true
다음 단계: 2. 모델 선택
```

모델이 없으면:

```text
판단 결과: needs_user_input
model_found: false
선택 가능:
1. sklearn
2. pytorch
3. tensorflow
```

<details>
<summary>자세한 판단 기준 보기</summary>

```text
pass:
- 실행 가능한 모델 구성 또는 entrypoint를 찾음

needs_user_input:
- 모델을 찾지 못했고 샘플 선택이 필요함
- 모델은 있으나 실제 학습/모델 생성 entrypoint 후보가 여러 개라 사용자 확인이 필요함

blocked:
- 지정한 프로젝트 경로가 없음
- 읽을 수 없는 경로이거나 분석 자체가 불가능함
```

모델 프로젝트 판단 기준:

```text
학습 entrypoint: train.py, scripts/train.py
실행/등록 entrypoint: runtest.py, run_model.py
추론 entrypoint: predict.py, app.py, main.py
필수 폴더: aiu_custom/, local_serving/, saved_model/
모델 wrapper: aiu_custom/model_wrapper.py, aiu_custom/predict.py
모델 artifact: ai_studio/, saved_model/, model/, artifacts/, .pkl, .joblib, .pt, .pth, .h5, .keras
사용자 모델 원본: *.pkl, *.joblib, *.pt, *.pth, *.onnx, *.h5, *.keras, *.safetensors, *.bst, *.ubj 또는 data/** 아래 같은 확장자
예: model.joblib, models/model.joblib, data/<임의폴더>/model.joblib, data/sklearn/model.pkl, data/checkpoints/model.pt, data/xgboost/model.ubj
MODEL_KIND: .pkl -> sklearn_pickle, .joblib -> sklearn_joblib, .pt/.pth -> pytorch, .onnx -> onnx, .keras -> tensorflow_keras, .h5 -> tensorflow_h5, .safetensors -> safetensors, .bst -> xgboost_bst, .ubj -> xgboost_ubj
MLflow model: MLmodel, python_model.pkl
입력 예제: input_example.json
```

</details>

<details>
<summary>문제 해결 보기</summary>

```text
증상: 모델이 있는데 샘플 선택지가 나옴
원인: entrypoint 또는 artifact 근거를 찾지 못함
조치: 실제 사용하는 학습 파일명과 모델 경로를 먼저 확정한다.

증상: run_model.py로 고정해서 안내됨
원인: 기존 모델 프로젝트의 실제 entrypoint 확인이 빠짐
조치: "실제 사용하는 Python 실행 파일명을 알려주세요."라고 묻는다.

증상: 샘플 규격 폴더가 부족함
원인: aiu_custom/, local_serving/, saved_model/ 등이 누락됨
조치: 샘플 선택 질문을 하지 말고 --scaffold-existing으로 부족한 골격만 보충한다.
```

</details>

<details>
<summary>전문가 상세 보기</summary>

Framework evidence:

```text
sklearn: sklearn, .pkl, .joblib, .fit()
pytorch: torch, .pt, .pth, state_dict
tensorflow: tensorflow, keras, .h5, .keras, saved_model.pb
huggingface: transformers, tokenizer files, model.safetensors
custom pyfunc: mlflow.pyfunc.PythonModel, aiu_custom, ModelWrapper
```

보충 명령:

```text
python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
python .opencode/scripts/02-model-select/select_model.py --project . --model 1
python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample <sklearn|pytorch|tensorflow> --scaffold-existing --execute
```

</details>

<details>
<summary>Safety 규칙 보기</summary>

- Launch 모드에서는 분석만 수행하고 파일을 수정하지 않는다.
- `.opencode/`는 번들/스킬 원본이므로 모델 프로젝트로 분석하지 않는다.
- 모델이 발견되면 `.opencode/samples` 선택을 요청하지 않는다.
- 샘플 규격 보충은 기존 모델 파일을 덮어쓰지 않는다.
- secret 값은 출력하지 않는다.
- 발견한 artifact를 이동하거나 복사하지 않는다.
- 루트/data 모델 원본을 템플릿 폴더로 복사하지 않는다.

</details>
