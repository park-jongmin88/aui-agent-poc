# aiu-agent (POC)

ML/DL 개발자를 위한 AI STUDIO 프로세스 CLI 자동화 — LangChain DeepAgents 기반.

## Quick Start
1. (권장) `config.yaml` 을 열어 TODO 항목(사내 LLM 주소/키/모델명)을 먼저 작성
   - 미리 작성하지 않아도 됩니다. 실행 중 물어보면 대화형으로 입력 가능
2. 실행
   - Windows: `quickstart.bat`
   - Linux/Mac/Codespaces: `./quickstart.sh`
3. 설치(진행 상황 표시) → 설정(미설정이면 즉시 입력) → LLM 연결 체크 통과 시 **자동으로 CLI(`aiu>`)에 진입**합니다

설치가 끝나면 자동으로 CLI에 진입하며, 이때 `aiu-agent-run.bat`(Windows) /
`aiu-agent-run.sh`(Linux/Mac)이 생성됩니다. **다음부터는 이 파일로 바로 실행**하세요.
(내부적으로 `.venv` 의 python으로 `main.py` 를 호출합니다.
`--setup` 설치+진입 / `--check` 체크만 / 인자 없음 체크+진입)

## 설정
- `config.yaml` : LLM 목록(여러 개 등록 가능, `/llm` 으로 전환), 넥서스 주소.
  수정 후 CLI에서 `/reload` 로 즉시 반영. **이 파일은 형상에 올리지 않습니다(.gitignore).**
- MLflow 주소/계정 : 각 모델 폴더 `run.py` 의 섹션 2에 직접 기입.
  작업 중 주소가 바뀌면 run.py만 고치면 다음 train부터 자동 반영됩니다.

## 구조
```
main.py          진입점 (CLI 대화 루프, --setup/--check 모드)
agent.md         프로젝트 정의 (항상 로드)
config.yaml      LLM/넥서스 설정 (없으면 자동 생성, 형상 제외)
quickstart.bat   Windows 설치+실행
quickstart.sh    Linux/Mac 설치+실행
skills/          5개 스킬 (init / validate / train / deploy / predict)
template/        run.py 베이스 템플릿 (9-섹션 표준)
setting/         config.json, requirements.txt
model/           모델 폴더 목록 - 폴더 안 파일은 run.py 생성용 기초 자료 (동작 샘플 3종 포함)
model_result/    학습 결과물
local_test/      MLflow 등록 모델 로컬 검증
```

## 스킬 사용 예
```
aiu> my_model 폴더 자료로 run.py 만들어줘  → init
aiu> 내 run.py 양식 맞는지 봐줘            → validate
aiu> sklearn_sample 학습해줘               → train
aiu> 방금 등록한 모델 추론 테스트           → predict
```
