# AI Studio Script Index

이 문서는 `.opencode/skills` 01~05 목록에 맞춘 스크립트 정리표입니다.

실제 구현 파일은 스킬 목록 기준 폴더에 둡니다.

## 01 Project Analyze

Skill folder:
`01-agent-mlflow-skill-project-analyze`

Primary scripts:

- `01-project-analyze/validate_mlflow_project.py` - 상세 워크스페이스 분석
- `launch_workspace_summary.py` - 기존 런치 분석 명령 호환 wrapper
- `04-train-model/prepare_selected_model.py` - 모델 목록 확인

## 02 Sample Bootstrap

Skill folder:
`02-agent-mlflow-skill-sample-bootstrap`

Primary scripts:

- `02-sample-bootstrap/bootstrap_sample_project.py` - 모델 없음 상태에서 sklearn/pytorch/tensorflow 샘플 복사

## 02 Model Select

Skill folder:
`04-agent-mlflow-skill-train-model`

Primary scripts:

- `02-model-select/select_model.py` - 2번 모델 선택 전용 wrapper. PowerShell의 `--model3`, `data\...`, `data￦...` 입력을 정규화한 뒤 선택 모델만 고정

## 03 Environment Check

Skill folder:
`03-agent-mlflow-skill-environment-check`

Primary scripts:

- `03-environment-check/check_environment.py` - Python, requirements.txt, MLflow 입력값, 패키지 상태 확인

Support scripts:

- `03-environment-check/response_speed_check.py` - 폐쇄망/Windows 응답 속도 및 인덱싱 진단
- `03-environment-check/apply_index_ignore.py` - `.opencode/`, `.opencode/node_modules/`, 생성물, 모델 파일 인덱싱 제외 적용

Required files:

- `03-environment-check/requirements.required.txt` - 생성되는 `requirements.txt`의 필수 5개 패키지 기준

## 04 Train Model / Selected Model Build

Skill folder:
`04-agent-mlflow-skill-train-model`

Primary scripts:

- `04-train-model/prepare_selected_model.py` - 2번 모델 선택 고정, 4번 템플릿 변환
- `04-train-model/run_training.py` - 5번 원격 MLflow 등록 실행

Support scripts:

- `04-train-model/adapt_ai_studio.py` - 사용자 임의 `run.py` 보강용 보조 스크립트

## 05 Inference Test

Skill folder:
`06-agent-mlflow-skill-inference-test`

Primary scripts:

- `06-inference-test/test_inference.py` - 추론 계약 점검

Generated runtime entrypoint:

- `inferencetest.py` - 4번 템플릿 변환이 프로젝트 루트에 생성

## Fixed 7-Step Process Map

```text
1. 모델 목록 확인                  -> 04-train-model/prepare_selected_model.py --project .
2. 모델 선택                       -> 02-model-select/select_model.py --model <번호|경로>
3. 환경 검증      -> 03-environment-check/check_environment.py
4. 템플릿 변환                     -> 04-train-model/prepare_selected_model.py --model selected --execute
5. 원격 MLflow 등록 실행           -> 04-train-model/run_training.py --execute
6. 추론 테스트                     -> inferencetest.py
7. 오류 재실행                     -> 실패 단계 스크립트 재실행
```

## QA / Maintenance

Scripts:

- `qa-maintenance/doctor.py` - 전체 상태 1페이지 점검
- `qa-maintenance/test_local_sample.py` - 번들 샘플 QA
- `qa-maintenance/test_7_step_flow.py` - 모델 있음 기준 AI Studio 7단계 흐름 QA

Documents:

- `README.md` - 사용자/운영용 스크립트 가이드
- `MAINTENANCE.md` - 유지보수 상세 문서
- `SCRIPT_INDEX.md` - 스킬 목록 기준 스크립트 정리표
- `skill_script_map.json` - 도구가 읽는 스킬-스크립트 매핑
