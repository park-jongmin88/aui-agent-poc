# aiu-agent (POC)

🐳 AI STUDIO 자동화 어시스턴트 — LangChain DeepAgents 기반 프로세스 CLI 자동화.

---

## 설치

| 환경 | 명령 |
|---|---|
| Windows | `install.bat` |
| macOS / Linux / Codespaces | `./install.sh` |

처음 한 번만 실행합니다. 설치 중 입력은 필요 없습니다:

1. 가상환경 생성
2. 필요 패키지 설치
3. `config.json` 없으면 자동 생성
4. `start.bat` / `start.sh` 생성

### ML 작업 전 추가 설치

학습/추론 기능을 사용하려면 ML 패키지를 추가 설치하세요:

```bash
# Windows
.venv\Scripts\python -m pip install -r setting\requirements-ml.txt

# Linux/Mac/Codespaces
.venv/bin/python -m pip install -r setting/requirements-ml.txt
```

---

## 실행

설치 후 생성된 파일로 실행합니다:

| 환경 | 명령 |
|---|---|
| Windows | `start.bat` |
| macOS / Linux / Codespaces | `./start.sh` |

처음 실행 시 LLM 설정이 없으면 입력을 요청합니다.

---

## LLM 설정

`config.json` 파일을 편집합니다. `config.sample.json` 을 참고하세요.

```json
{
  "llm": {
    "active": "my-llm",
    "providers": [
      {
        "name": "my-llm",
        "type": "openai",
        "base_url": "http://your-llm-server:8000/v1",
        "api_key": "your-api-key",
        "model": "your-model-name"
      }
    ]
  }
}
```

- `active`: 현재 사용할 LLM의 `name` 값
- `type`: `openai` (OpenAI 호환) | `anthropic` (Anthropic API)
- 여러 LLM을 등록하고 CLI에서 `/llm` 으로 전환 가능
- 수정 후 `/reload` 로 즉시 반영
- **형상에 포함되지 않습니다** (`.gitignore`)

### MLflow 설정

각 모델 폴더의 `run.py` 섹션 2에 직접 기입합니다:

```python
MLFLOW_TRACKING_URI = "http://your-mlflow:5000"
MLFLOW_USERNAME = ""
MLFLOW_PASSWORD = ""
```

---

## 사용법

```
> 1번 준비해줘

────────────────────────────────────────────────────

🐳 workspace/models/sklearn_sample 폴더를 분석했습니다...
  (2.1s)

────────────────────────────────────────────────────
>
```

### 작업 순서

| 단계 | 예시 요청 | 스킬 |
|---|---|---|
| 1. 준비 | "1번 준비해줘", "sklearn_sample 시작해줘" | init |
| 2. 검증 | "검증해줘", "이상없어?" | validate |
| 3. 학습 | "학습 시작해줘", "MLflow에 등록해줘" | train |
| 4. 확인 | "결과 확인해줘", "추론 테스트해줘" | predict |
| 5. 배포 | "배포해줘" (POC: 안내만) | deploy |

### 명령어

| 명령 | 설명 |
|---|---|
| `/? /help` | 도움말 |
| `/list` | 작업 폴더 목록 (번호로 선택) |
| `/llm` | LLM 목록 + 전환 |
| `/config` | 현재 설정 |
| `/reload` | config.json 재로드 |
| `/log` | 마지막 로그 |
| `/clear` | 대화 초기화 |
| `/exit` | 종료 |

---

## 구조

```
main.py                 진입점 (CLI 대화 루프)
agent.md                에이전트 정의
config.json             LLM 설정 (없으면 자동 생성, 형상 제외)
config.sample.json      설정 예시 (형상 포함)
install.bat / .sh       최초 설치 → start.bat / start.sh 생성
start.bat / .sh         이후 실행
skills/
  common/               공통 유틸리티
  init/                 폴더 분석 + run.py 생성
  validate/             run.py 9섹션 검증
  train/                학습 실행 + MLflow 등록
  predict/              추론 테스트
  deploy/               배포 (POC: 안내만)
workspace/
  models/               작업 폴더 (샘플 3종 포함)
  templates/            run.py 베이스 템플릿
  results/              학습 결과물
  local_test/           로컬 추론 테스트
setting/
  requirements.txt      에이전트 구동 패키지
  requirements-ml.txt   ML 작업 패키지
```
