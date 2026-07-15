# opencode 첫 응답 속도 개선 (인덱싱 최적화)

opencode 첫 실행 시 워크스페이스 전체 인덱싱 때문에 첫 응답(인사)까지 느립니다. git 추적은 그대로 유지(모든 파일 커밋)하면서 opencode 탐색 속도만 개선하는 방법입니다.

## 배경

- opencode는 내부적으로 ripgrep을 사용하며, 프로젝트 **루트의 `.ignore`** 파일을 존중합니다. `.ignore`는 git과 무관하게 opencode의 검색·목록·인덱싱에서만 경로를 제외하므로, git 커밋 대상은 바뀌지 않습니다.
- 인덱싱 제외는 반드시 **프로젝트 루트**의 `.ignore`에 있어야 동작합니다. `.opencode/` 하위에 두면 그 폴더 내부만 제어되어 인덱싱 속도에는 영향이 없습니다.
- `opencode.json`이 `.opencode/agents/aistudio.md`를 직접 참조하므로 **`.opencode/`를 통째로 제외하면 안 됩니다.** opencode가 읽어야 하는 `agents/`, `skills/`는 남기고, 무거운 하위 폴더/파일만 제외합니다.

## 적용 방법

1. 프로젝트 루트에 `.ignore` 파일을 생성합니다. (이미 있으면 아래 내용을 병합)
2. 아래 내용을 넣습니다. 폴더 구조는 `.opencode/`, `data/`, `workspace/` 기준입니다.
3. 적용 후 opencode 세션을 재시작하거나 워크스페이스를 다시 로드합니다.

## 루트 `.ignore` 내용

```
# opencode(ripgrep) 인덱싱 제외 — git 추적과 무관, 첫 응답 속도 개선용

# .opencode 는 통째 제외 금지 (opencode.json 이 agents/aistudio.md 를 참조).
# 무거운 하위만 제외:
.opencode/node_modules/
.opencode/**/__pycache__/
.opencode/**/*.whl

# 모델 바이너리 (data/ 폴더 구조는 남기고 큰 파일만 제외)
data/**/*.pt
data/**/*.pth
data/**/*.pkl
data/**/*.joblib
data/**/*.h5
data/**/*.keras
data/**/*.safetensors
data/**/*.onnx
data/**/*.bin

# 작업 산출물
workspace/**/saved_model/
workspace/**/mlruns/
workspace/**/mlartifacts/
workspace/**/__pycache__/

# 공통 무거운 폴더/파일
.venv/
venv/
node_modules/
__pycache__/
*.log
*.csv
*.parquet
*.npy
*.npz
```

## 주의

- `.opencode/agents/`, `.opencode/skills/`는 **제외하지 않습니다.** opencode가 지침·스킬을 읽어야 하므로 반드시 인덱싱에 남겨야 합니다.
- `data/` 폴더 자체는 제외하지 않고(모델 목록 조회 필요), 안의 **큰 바이너리 파일만** 제외합니다.
- 위 목록에 실제로 없는 경로가 있어도 무방합니다(무시됨).
- 적용 후에도 느리면 `du -sh .opencode/* data/* workspace/*`로 용량이 큰 폴더를 찾아 제외 목록에 추가합니다.

## 동작 원리 요약

| 두는 곳 | 인덱싱 속도 영향 | git 영향 |
|---|---|---|
| 루트 `.ignore` | 있음 (ripgrep이 읽어 제외) | 없음 (git 무관) |
| 루트 `.gitignore` | 있음 | 있음 (커밋 제외됨) |
| `.opencode/` 안 | 없음 (그 폴더 내부만 제어) | — |

git에는 전부 올리고 opencode 인덱싱만 가볍게 하려면 **루트 `.ignore`**가 정답입니다.
