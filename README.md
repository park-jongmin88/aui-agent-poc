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

## 설정

### LLM 설정 (config.json)

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
  },
  "mlflow": {
    "tracking_uri": "http://your-mlflow:5000",
    "username": "",
    "password": ""
  }
}
```

- `active`: 현재 사용할 LLM의 `name` 값
- `type`: `openai` (OpenAI 호환) | `anthropic` (Anthropic API)
- `mlflow`: 모든 모델 공통 MLflow 서버 정보 (init 시 자동 입력받기 가능)
- 여러 LLM 등록 후 `/llm` 으로 전환 가능
- 수정 후 `/reload` 로 즉시 반영
- **형상에 포함되지 않습니다** (`.gitignore`)

---

## 사용법

```
━━━ 📁 sklearn_sample  │  ✅init ──▶ [validate] ──▶ ○train ──▶ ○predict ──▶ ○deploy  │  groq: llama-3.3
❯ 검증해줘

────────────────────────────────────────────────────

🐳 run.py 검증 완료. 학습을 시작할 수 있습니다.
  (2.1s)

────────────────────────────────────────────────────

━━━ 📁 sklearn_sample  │  ✅init ──▶ ✅validate ──▶ [train] ──▶ ○predict ──▶ ○deploy  │  groq: llama-3.3
❯
```

### 하단 상태바

항상 하단에 고정 표시됩니다:
- `✅` 완료 단계 (초록)
- `[현재]` 진행 가능한 다음 단계 (파란 bold)
- `○` 미도달 단계 (회색)
- `❌` 실패 단계 (빨강)
- 모델 폴더 변경 시 자동 갱신

### 작업 순서

각 단계는 이전 단계 통과 후에만 진행 가능합니다.

| 단계 | 예시 요청 | 스킬 | 비고 |
|---|---|---|---|
| 1. 준비 | "1번 준비해줘", "sklearn_sample 시작해줘" | init | 필수 |
| 2. 검증 | "검증해줘", "이상없어?" | validate | 필수 |
| 3. 로컬 테스트 | "로컬 실행해줘", "MLflow 없이 돌려봐" | local_run | **선택** |
| 4. 학습 | "학습 시작해줘", "MLflow에 등록해줘" | train | 필수 |
| 5. 추론 테스트 | "결과 확인해줘", "추론 테스트해줘" | predict | 필수 |
| 6. 로컬 서빙 | "로컬 서버 띄워줘", "서버 꺼줘" | local_serve | 선택 |
| 7. 배포 | "배포해줘" | deploy | POC: 안내만 |

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
agent.md                에이전트 정의 (단계 게이트, 작업 흐름)
config.json             LLM + MLflow 설정 (자동 생성, 형상 제외)
config.sample.json      설정 예시 (형상 포함)
install.bat / .sh       최초 설치 → start.bat / start.sh 생성
start.bat / .sh         이후 실행
skills/
  common/               공통 유틸 (게이트, 상태관리, MLflow 설정)
  init/                 폴더 분석 + run.py 자동 생성
  validate/             run.py 9섹션 구조/내용 검증
  local_run/            MLflow 없이 로컬 학습 테스트 (선택)
  train/                학습 실행 + MLflow 등록
  predict/              MLflow 모델 추론 테스트
  local_serve/          로컬 FastAPI 서빙 (선택)
  deploy/               배포 (POC: 안내만)
workspace/
  .current              현재 작업 폴더명
  models/               작업 폴더 모음
    <모델명>/
      source/           원본 자료 (데이터, 코드, 모델파일)
      run.py            실행 파일 (init이 생성)
      .aiu_state.json   단계별 진행 상태 (toolbar 네비게이션 기반)
  templates/            run.py 베이스 템플릿 (수정 금지)
  results/              로컬 학습 결과물
setting/
  requirements.txt      에이전트 구동 패키지
  requirements-ml.txt   ML 작업 패키지 (학습/추론 시 설치)
```

## 샘플 모델 폴더

| 폴더 | 타입 | 설명 |
|---|---|---|
| `sklearn_sample/` | DATA_ONLY | CSV 분류 데이터 |
| `sklearn_pretrained/` | LOAD_MODEL | 학습된 RF 모델(.pkl) |
| `custom_code_sample/` | RUN_CODE | SVM 학습 코드(.py) |
| `multifile_sample/` | 혼합 | CSV + 전처리 코드 |
| `template_only/` | TEMPLATE | 완전 빈 폴더 |
| `pytorch_sample/` | TEMPLATE | PyTorch 시작용 |
| `tensorflow_sample/` | TEMPLATE | TF/Keras 시작용 |

각 폴더의 `source/README.md` 에서 상세 설명을 확인하세요.
