# aiu-agent (POC)

🐳 AI STUDIO 자동화 어시스턴트 — LangChain DeepAgents 기반 ML/DL 프로세스 CLI 자동화.

---

## ⚠ 사전 준비 (설치 전 필수 확인)

### 1. Python 설치
- **Python 3.10 이상** 필요 (`Path | None` union 문법 사용)
- 확인: `python --version` (Windows) / `python3 --version` (Linux/Mac)
- 미설치 시 [python.org](https://www.python.org/downloads/) 또는 사내 배포 채널에서 설치
- Windows 설치 시 **"Add Python to PATH"** 체크 필수
- `where python` 으로 경로가 안 나오면 PATH 미등록 (이 경우 install.bat이 자동으로 `py` 런처 사용)

### 2. pip 인덱스 (사내 넥서스) 설정
- 사내망에서는 pip이 **사내 넥서스**를 바라보도록 설정되어 있어야 합니다.
- 확인: `pip config list`
  - `global.index-url` 에 넥서스 주소가 보이면 정상
- 설정 안 되어 있으면 (주소는 사내 가이드 참고):
  ```bash
  pip config set global.index-url https://<사내-넥서스-주소>/simple
  pip config set global.trusted-host <사내-넥서스-호스트>
  ```

### 3. 네트워크
- wheel 다운로드 시 넥서스에 접근 가능한 환경이어야 합니다.
- **wheel 동봉 배포본을 받은 경우 네트워크 불필요** → 바로 install 가능

---

## 설치 절차

설치는 **wheel 받기 → install** 2단계입니다.

### 1단계: wheel 받기 (관리자 / 처음 설치 시)

```bash
# Windows
setting\download_wheels.bat

# Linux/Mac
./setting/download_wheels.sh
```

→ `wheels/` 폴더에 모든 의존성 wheel이 받아집니다.
→ **관리자가 wheels 폴더를 동봉해서 배포하면 이 단계 불필요.**

### 2단계: install

```bash
# Windows
install.bat

# Linux/Mac
./install.sh
```

→ `wheels/` 확인 후 로컬 wheel로 설치 (네트워크 불필요)
→ `wheels/` 없으면 안내 후 중단 (1단계부터 실행)
→ 완료되면 start 명령 안내

### 3단계: 실행

```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

---

## 배포 구조 (관리자용)

```
관리자
  1. download_wheels 실행 → wheels/ 생성
  2. 프로젝트 + wheels/ 폴더째 ZIP 배포

사용자
  1. ZIP 압축 해제
  2. install.bat 실행 → wheels에서 설치
  3. start.bat 실행
```

wheels 폴더 용량이 크면 제외하고 배포 가능
(이 경우 사용자가 넥서스에서 직접 download_wheels 실행)

---

## 작업 순서

각 단계는 이전 단계 통과 후에만 진행 가능합니다.

| 단계 | 예시 요청 | 스킬 | 비고 |
|---|---|---|---|
| 1. 준비 | "1번 준비해줘", "sklearn_sample 시작해줘" | init | 필수 |
| 2. 검증 | "검증해줘", "이상없어?" | validate | 필수 |
| 3. 로컬 테스트 | "로컬 실행해줘", "MLflow 없이 돌려봐" | localrun | **선택** |
| 4. 학습 | "학습 시작해줘", "MLflow에 등록해줘" | train | 필수 |
| 5. 추론 테스트 | "결과 확인해줘", "추론 테스트해줘" | predict | 필수 |
| 6. 로컬 서빙 | "로컬 서버 띄워줘", "서버 꺼줘" | localserve | 선택 (localrun 후) |
| 7. 배포 | "배포해줘" | deploy | POC: 안내만 |

> **로컬 서빙은 localrun을 거쳐야 합니다.**
> train은 MLflow에만 등록하므로 로컬 모델 파일이 없습니다.
> 서빙하려면 먼저 `로컬 실행해줘`로 localrun을 실행하세요.

---

## 프로젝트 구조

```
install.bat / install.sh     설치 스크립트
start.bat / start.sh         실행 스크립트 (install이 생성)
main.py                      에이전트 진입점
agent.md                     에이전트 정의 (게이트, 작업흐름)
config.json                  LLM + MLflow 설정 (.gitignore)
config.sample.json           설정 예시 (참고용)

setting/
  requirements.txt           전체 의존성 (install 시 일괄 설치)
  download_wheels.bat/.sh    wheel 받기 (관리자/배포용)

wheels/                      wheel 파일 모음 (.gitignore)

skills/
  common/                    공통 유틸 (게이트, 상태관리, Win/Linux 프로세스 제어)
  init/                      폴더 분석 + run.py 자동 생성
  validate/                  run.py 9섹션 구조/내용 검증
  localrun/                  MLflow 없이 로컬 학습 테스트 (선택)
  train/                     학습 실행 + MLflow 등록
  predict/                   MLflow 모델 추론 테스트
  localserve/                로컬 FastAPI 서빙 (선택)
  deploy/                    배포 (POC: 안내만)

docs/
  mlflow_api.md              MLflow 핵심 API 요약
  mlflow_registry.md         Model Registry, 버전 관리
  ml_guide.md                sklearn/PyTorch/TensorFlow 패턴, 평가 지표
  runpy_patterns.md          데이터 타입별 run.py 완성 패턴
  troubleshooting.md         에러 해결 가이드

workspace/
  .current                   현재 작업 폴더명
  models/                    작업 폴더 모음
    <모델명>/
      source/                원본 자료 (수정금지)
      run.py                 init이 자동 생성 (pyfunc 등록)
      model_wrapper.py       pyfunc ModelWrapper (init 생성, 수정 가능)
      input_example.json     run.py 실행 시 자동 생성 (KServe 형식)
      .aiu_state.json        단계 상태
  templates/                 run.py 베이스 (수정금지)
  results/                   localrun 결과물 (로컬 모델 파일)
```

---

## 의존성

```
# 에이전트 구동
deepagents, langchain-openai, langchain-anthropic

# CLI UI
rich, prompt_toolkit

# ML 작업
mlflow, scikit-learn, pandas, numpy, joblib

# 로컬 서빙
fastapi, uvicorn
```

---

## LLM 설정 (config.json)

install 후 처음 start 시 대화로 입력받아 자동 생성됩니다.
`config.sample.json`을 참고해 미리 작성할 수도 있습니다.

지원 타입:
- `openai` — OpenAI 호환 엔드포인트 (Groq, Ollama, 사내 LLM 등)
- `anthropic` — Anthropic Claude API

세션 중 `/llm` 명령으로 LLM 전환 가능.

---

## 명령어

| 명령 | 설명 |
|---|---|
| `/help`, `/?` | 명령어 목록 |
| `/list` | 작업 폴더 목록 |
| `/llm` | LLM 목록 + 전환 |
| `/config` | 현재 설정 확인 |
| `/reload` | 설정 재로드 |
| `/log` | 마지막 로그 |
| `/clear` | 대화 초기화 |
| `/exit`, `/quit` | 종료 |
