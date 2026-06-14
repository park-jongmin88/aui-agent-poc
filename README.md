# aiu-agent (POC)

🐳 AI STUDIO 자동화 어시스턴트 — LangChain DeepAgents 기반 프로세스 CLI 자동화.

## 설치

| 환경 | 실행 |
|---|---|
| Windows | `install.bat` |
| macOS / Linux (Codespaces 포함) | `./install.sh` |

처음 한 번만 실행하면 됩니다:

1. 가상환경 생성 + 필요한 패키지 설치 (진행 상황이 화면에 표시됩니다)
2. `config.yaml` 이 없으면 자동 생성. LLM 정보가 비어있으면 그 자리에서 입력받습니다
3. LLM 연결 확인 후 **자동으로 CLI에 진입**합니다

설치 후 `start.bat`(Windows) / `start.sh`(macOS·Linux)로 바로 실행하세요.

## 설정
- `config.yaml`: LLM 목록 (여러 개 등록 가능, `/llm` 으로 전환)
  - `active`: 현재 사용할 LLM의 name 값을 지정
  - `type`: `openai` (OpenAI 호환) | `anthropic` (Anthropic API)
  - 수정 후 `/reload` 로 즉시 반영
  - **형상에 올리지 않습니다 (.gitignore)**
- MLflow 주소/계정: 각 모델 폴더 `run.py` 섹션 2에 직접 기입

## 사용

```
> 작업 목록 보여줘

🐳 ─────────────────────────────────────────────
[에이전트 응답...]
  (3.2s)
```

주요 명령어:

| 명령 | 설명 |
|---|---|
| `/? /help` | 도움말 (할 수 있는 작업 안내 포함) |
| `/list` | 작업 목록 (workspace/models/) |
| `/llm` | LLM 목록 + 전환 |
| `/config` | 현재 설정 |
| `/reload` | config.yaml 재로드 |
| `/log` | 마지막 로그 |
| `/clear` | 대화 초기화 |
| `/exit` | 종료 |

## 구조

```
main.py              진입점 (CLI 대화 루프)
agent.md             에이전트 정의 (항상 로드)
config.yaml          LLM 설정 (없으면 자동 생성, 형상 제외)
install.bat/sh       최초 설치 → start.bat/sh 생성
start.bat/sh         이후 실행
skills/              5개 스킬 (init/validate/train/deploy/predict)
workspace/
  models/            작업 대상 모델 폴더 (샘플 3종 포함)
  templates/         run.py 베이스 템플릿 (9-섹션 표준)
  results/           학습 결과물
  local_test/        MLflow 등록 모델 로컬 추론 테스트
setting/             requirements.txt
```

## 스킬 사용 예
```
> workspace/models/my_model 폴더로 run.py 만들어줘   → init
> 내 run.py 양식 맞는지 봐줘                         → validate
> sklearn_sample 학습해줘                             → train
> 방금 등록한 모델 추론 테스트                         → predict
```
