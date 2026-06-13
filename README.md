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
   - 모르는 항목은 Enter로 비워두고 나중에 `config.yaml` 을 직접 수정해도 됩니다
3. LLM 연결 확인 후 **자동으로 CLI에 진입**합니다

설치가 끝나면 `start.bat`(Windows) / `start.sh`(macOS·Linux)가 생성됩니다.
**다음부터는 이 파일로 바로 실행**하세요.

```
Windows : start.bat
그 외   : ./start.sh
```

(내부적으로 `.venv` 의 python으로 `main.py` 를 호출합니다.
`--setup` 설치+진입 / `--check` 체크만 / 인자 없음 체크+진입)

## 설정
- `config.yaml` : LLM 목록(여러 개 등록 가능, `/llm` 으로 전환), 넥서스 주소.
  수정 후 CLI에서 `/reload` 로 즉시 반영. **이 파일은 형상에 올리지 않습니다(.gitignore).**
- MLflow 주소/계정 : 각 모델 폴더 `run.py` 의 섹션 2에 직접 기입.
  작업 중 주소가 바뀌면 run.py만 고치면 다음 train부터 자동 반영됩니다.

## 사용
실행하면 환영 화면과 명령어 목록이 표시되고, `>` 프롬프트에 자연어로 요청하면 됩니다.

```
> sklearn_sample 학습해줘

🐳 ─────────────────────────────────────────────
[에이전트 응답...]
  (3.2s)
```

주요 명령어:

| 명령 | 설명 |
|---|---|
| `/help` | 명령어 목록 |
| `/skills` | 로드된 스킬 목록 |
| `/model` | model/ 하위 폴더 목록 |
| `/config` | 현재 설정 (키는 마스킹) |
| `/llm` | 등록된 LLM 목록 + 전환 |
| `/reload` | config.yaml 재로드 + 에이전트 재구성 |
| `/log` | 마지막 로그(에러 등) 자세히 보기 |
| `/clear` | 대화 히스토리 초기화 |
| `/exit` | 종료 |

오류가 발생하면 한글 안내와 짧은 로그가 함께 표시되며, 전체 내용은 `/log` 로 확인할 수 있습니다.

## 구조
```
main.py          진입점 (CLI 대화 루프, --setup/--check 모드)
agent.md         프로젝트 정의 (항상 로드)
config.yaml      LLM/넥서스 설정 (없으면 자동 생성, 형상 제외)
install.bat/sh   최초 설치 (실행 시 start.bat/sh 생성)
start.bat/sh     이후 실행
skills/          5개 스킬 (init / validate / train / deploy / predict)
template/        run.py 베이스 템플릿 (9-섹션 표준)
setting/         config.json, requirements.txt
model/           모델 폴더 목록 - 폴더 안 파일은 run.py 생성용 기초 자료 (동작 샘플 3종 포함)
model_result/    학습 결과물
local_test/      MLflow 등록 모델 로컬 검증
```

## 스킬 사용 예
```
> my_model 폴더 자료로 run.py 만들어줘   → init
> 내 run.py 양식 맞는지 봐줘             → validate
> sklearn_sample 학습해줘                → train
> 방금 등록한 모델 추론 테스트            → predict
```
