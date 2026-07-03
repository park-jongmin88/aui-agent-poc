# 작업 가이드 (WORK_GUIDE)

회사 버전(엔진 수정본)에서 이 프로젝트 구조에 맞춰 작업할 때 참고하는 문서.
아래 **유지 필수** 항목만 지키면, 내부 로직·문서·GLM 규칙은 자유롭게 바꿔도 흐름이 깨지지 않는다.

---

## 1. 반드시 유지해야 할 것 (건드리면 깨짐)

### 1-1. ModelWrapper 형태 계약
엔진(`scripts/04-train-model/prepare_selected_model.py`)이 템플릿을 아래 구조로 변환한다.
GLM 규칙을 넣더라도 **이 뼈대(클래스/메서드 시그니처)는 유지**한다.

```python
class ModelWrapper(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        # context.artifacts["config"], context.artifacts["model"] 로 로드
        ...
    def predict(self, context, model_input, params=None):
        ...

def predict(payload):          # 로컬 단독 추론 진입점
    wrapper = ModelWrapper()
    return wrapper.predict(None, payload)
```

- `class ModelWrapper(mlflow.pyfunc.PythonModel)` — pyfunc 표준, 이름 고정
- `load_context(self, context)` — artifacts 에서 config/model 로드
- `predict(self, context, model_input, params=None)` — 시그니처 유지
- 파일 최하단 `def predict(payload)` — 로컬 추론 진입점 유지

### 1-2. 폴더/파일 이름 (엔진이 하드코딩으로 탐색)
```
<모델>/
  aiu_custom/predict.py      ← ModelWrapper 위치 (폴더/파일명 고정)
  local_serving/serve.py
  saved_model/
  run_model.py
  input_example.json
  requirements.txt
```
- `aiu_custom`, `local_serving`, `saved_model` 이름을 바꾸면 엔진이 못 찾는다.
- `aiu` = AI stUdio 약자 (정상). `aiu_studio` 같은 조합은 잘못된 표기.

### 1-3. input_example.json (KServe 형식)
```json
{"inputs": [{"data": ...}]}
```
- predict 의 payload 파싱이 이 형식을 기준으로 한다.

### 1-4. 7단계 고정 정의
`scripts/ai_studio_process.py` 의 `AI_STUDIO_PROCESS_STEPS` 는 정확히 7개.
- 개수를 바꾸면 런타임 에러(`must stay exactly 7 steps`).
- 바꿀 때는 `AGENTS.md` 3번 표 + 프로세스 이미지도 함께 수정한다.

### 1-5. 매핑 정합성 (셋이 서로 참조)
```
skills/<스킬폴더>/SKILL.md  ↔  scripts/skill_script_map.json  ↔  scripts/<스크립트>
```
- 스킬 폴더명 / 스크립트 경로 중 하나를 바꾸면 나머지도 맞춘다.

### 1-6. 경로 규칙
- artifact `path` 는 OS 상대경로, `uri` 는 항상 `/`(forward slash).
- 사용자 대상 명령은 `data/...` 상대경로만. 절대경로(`C:\...`, `/home/...`) 금지.

---

## 2. 자유롭게 바꿔도 되는 것

- **predict 내부 로직** — GLM 규칙, 서버 배포용 payload(예: trace_id / logger / aiu_output / aiu_monitoring 등).
  단 1-1 의 뼈대(클래스·메서드 시그니처)는 유지.
- **requirements.txt** — 각 폴더 안에서 실제 import 하는 패키지를 추가 (오히려 채워야 함).
- **문서 내용** — AGENTS.md, README 등. 형태 계약만 안 깨면 자유.
- **samples 내용** — 폴더 구조 유지하면서 코드 채우기.

---

## 3. 정리 규칙 (지저분한 파일 정돈 시)

이 저장소는 아래 기준으로 정리되어 있다. 회사 버전 정리 시에도 동일하게 적용한다.

- **루트 중복 제거**: opencode 실행 래퍼(cmd/ps1)의 루트/`.opencode` 중복, ignore 파일 중복 정리.
- **불필요 폴더 삭제**: `qa-maintenance/`(테스트), `templates/`(samples 와 중복) 등.
- **문서 통합**: 흐름 설명이 여러 md(GUIDE/TABLE/EXPLANATION/ARCHITECTURE)에 흩어지지 않게 **AGENTS.md 한 곳**으로 통합.
- **비텍스트 문서 제거**: LLM 이 참조하기 어려운 docx/pdf 는 skills/ 에서 제거(md 만 유지).
- **최상위 진입점**: `opencode.json` 의 `instructions` 는 `.opencode/AGENTS.md` 를 가리킨다.

---

## 4. 핵심 요약

> **폴더명(aiu_custom 등) + ModelWrapper 인터페이스 + 7단계 + 매핑 정합성** 만 지키면,
> 내부 로직(predict, GLM 규칙)·문서·requirements 는 자유롭게 바꿔도 흐름이 유지된다.
