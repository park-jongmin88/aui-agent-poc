# Closed-Network Speed Guide

폐쇄망 OpenCode 응답이 느릴 때는 먼저 파일 트리 인덱싱 범위를 줄입니다. ML 프로젝트는 `.venv`, wheelhouse, MLflow tracking, dataset, model binary가 커서 채팅 응답까지 느려질 수 있습니다.

## Quick Fix

```text
python .opencode/scripts/03-environment-check/response_speed_check.py --project .
python .opencode/scripts/03-environment-check/apply_index_ignore.py --project .
```

그 다음 OpenCode 세션을 다시 열거나 워크스페이스를 다시 로드합니다.

## Fast Operating Rule

```text
Ai Studio 모드:
  1. Ai Studio 출력
  2. workspace 분석
  3. model_found 결과와 다음 1개 행동만 안내

Ai Studio 빌드 모드:
  1. 필요한 스크립트만 직접 실행
  2. 전체 폴더 재스캔 반복 금지
  3. 샘플/모델 산출물은 ignore 대상 폴더에 유지
```

## Keep Out Of Index

```text
.venv/
node_modules/
mlruns/
ai_studio/tracking/
ai_studio/metrics/
ai_studio/code/
saved_model/
datasets/
*.pt
*.pkl
*.safetensors
```

## Windows

```text
Windows PowerShell:
  python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
  python .opencode/scripts/response_speed_check.py --project .
  python .opencode/scripts/apply_index_ignore.py --project .
```

PowerShell에서 실패 메시지가 필요하면 `||` 대신 아래처럼 확인합니다.

```powershell
python .opencode/scripts/04-train-model/prepare_selected_model.py --project .
if ($LASTEXITCODE -ne 0) { "script_not_found" }
```

## Notes

- Bun은 사용하지 않습니다.
- JavaScript 프로젝트에서 `package.json`이 있으면 `npm i`만 사용합니다.
- 폐쇄망 패키지는 `requirements.txt`와 내부 `http://` PyPI/Nexus 미러를 우선합니다.
- `.opencode` 폴더는 스킬 번들이므로 워크스페이스 분석/인덱싱에서는 제외합니다.
- 데이터셋이나 모델 바이너리를 분석해야 할 때는 폴더 전체를 열지 말고 필요한 파일명만 지정합니다.
