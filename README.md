# aiu-agent (POC)

🐳 AI STUDIO 자동화 어시스턴트 — LangChain DeepAgents 기반 프로세스 CLI 자동화.

---

## ⚠ 사전 준비 (설치 전 필수 확인)

이 프로그램을 설치하기 전에 아래 항목을 먼저 확인하세요.

### 1. Python 설치
- **Python 3.10 이상** 필요
- 설치 확인: `python --version` (Windows) / `python3 --version` (Linux/Mac)
- 미설치 시 [python.org](https://www.python.org/downloads/) 또는 사내 배포 채널에서 설치
- Windows 설치 시 **"Add Python to PATH"** 체크 필수
- `where python` 으로 경로가 안 나오면 PATH 미등록 상태입니다 (이 경우 install.bat이 자동으로 `py` 런처를 사용합니다)

### 2. pip 인덱스(사내 넥서스) 설정
- 사내망에서는 pip이 **사내 넥서스**를 바라보도록 설정되어 있어야 합니다.
- 설정 확인:
  ```bash
  pip config list
  ```
  `global.index-url` 또는 `global.index` 에 사내 넥서스 주소가 보이면 정상입니다.
- 설정이 없다면 아래로 등록하세요 (주소는 사내 가이드 참고):
  ```bash
  pip config set global.index-url https://<사내-넥서스-주소>/simple
  pip config set global.trusted-host <사내-넥서스-호스트>
  ```

### 3. 네트워크
- 사내 넥서스 또는 PyPI에 접근 가능한 네트워크 환경이어야 합니다.
- 오프라인/속도 개선이 필요하면 아래 **wheel 미리 받기**를 이용하세요.

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

---

## 설치 절차 (wheel 기반)

설치는 **wheel 준비 → install** 2단계입니다.

### 1단계: wheel 받기

wheels/ 폴더가 없으면 install이 안내하며 중단됩니다. 먼저 wheel을 받으세요:

```bash
# Windows
setting\download_wheels.bat

# Linux/Mac
./setting/download_wheels.sh
```

→ `wheels/` 폴더에 모든 의존성이 받아집니다.

### 2단계: install

```bash
# Windows
install.bat

# Linux/Mac
./install.sh
```

→ `wheels/` 를 확인하고 로컬 wheel로 설치합니다 (네트워크 불필요).
→ 완료되면 `start` 로 실행하라고 안내합니다.

### 관리자 배포 (권장)

관리자가 미리 `download_wheels` 를 실행해 `wheels/` 를 만든 뒤,
**폴더째 동봉해서 배포**하면 사용자는 `install` 만 실행하면 됩니다.
(용량이 크면 `wheels/` 를 빼고 배포 → 사용자가 1단계부터 직접 실행)

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
| 6. 로컬 서빙 | "로컬 서버 띄워줘", "서버 꺼줘" | local_serve | 선택 (local_run 후) |
| 7. 배포 | "배포해줘" | deploy | POC: 안내만 |

> **로컬 서빙은 local_run을 거쳐야 합니다.** train은 MLflow에만 등록하므로
> 로컬 모델 파일(`workspace/results/`)이 없어, 서빙하려면 먼저 `로컬 실행해줘`로 local_run을 실행하세요.

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
  common/               공통 유틸 (게이트, 상태관리, MLflow 설정, Win/Linux 프로세스 제어)
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
  requirements.txt          전체 의존성 (install 시 일괄 설치)
  download_wheels.bat/.sh   wheel 미리 받기 (관리자/배포용)
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
