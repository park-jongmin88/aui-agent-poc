# 사용 설명서

aiu-agent 의 개념, 작업 흐름, 용어를 정리한 매뉴얼입니다.

---

## 1. 한 줄 정의

> ML/DL 개발자가 "학습해줘"라고 말하면, AI가 알아서 코드를 만들고 MLflow에 등록해주는 대화형 CLI 도구.

인프라 지식 없이 자연어로 ML 워크플로우를 실행하는 것이 목표입니다.

---

## 2. 핵심 용어

| 용어 | 뜻 |
|---|---|
| **DeepAgents** | LangChain 기반 에이전트 프레임워크. 대화를 받아 어떤 스킬을 쓸지 판단 |
| **스킬(skill)** | 하나의 작업 단위 (init, validate, train...). 각 폴더에 SKILL.md + 스크립트 |
| **SKILL.md** | 스킬 설명서. "이런 요청이 오면 이 스크립트 실행" 을 LLM에게 알려줌 |
| **게이트(gate)** | 단계 순서 강제. 검증 안 하면 학습 못 하게 막는 안전장치 |
| **상태(state)** | `.aiu_state.json`. 현재 어느 단계까지 왔는지 기록 |
| **pyfunc** | MLflow의 범용 모델 포맷. 어떤 프레임워크든 같은 방식으로 등록 |
| **ModelWrapper** | 모델을 pyfunc으로 감싸는 클래스. 추론 인터페이스 표준화 |
| **wheel** | 미리 받아둔 파이썬 패키지. 설치를 빠르게 + 매번 넥서스를 안 거쳐도 됨 |

---

## 3. 작업 흐름

```
0. 모델 선택   "/list" 또는 "폴더 목록 보여줘"
       ↓
1. 준비(init)         "sklearn_sample 준비해줘"
       ↓              → source/ 분석 → run.py + model_wrapper.py 생성
2. 검증(validate)     "검증해줘"
       ↓              → run.py 9섹션 구조 / TODO 확인
3. 로컬테스트(localrun) "로컬에서 돌려봐"  (선택)
       ↓              → MLflow 없이 학습, results/ 에 저장
4. 학습(train)        "학습 시작해줘"
       ↓              → run.py 실행 → MLflow에 pyfunc 등록
5. 추론(predict)      "결과 확인해줘"
       ↓              → 등록 모델 로드 → input_example.json 으로 추론
6. 로컬서빙(localserve) "서버 띄워줘"  (선택)
       ↓              → FastAPI 서버 → POST /predict
7. 배포(deploy)       "배포해줘"  (POC: 안내만)
```

**게이트 규칙:** 각 단계는 앞 단계를 통과해야 진행됩니다. 순서를 건너뛰면 차단하고 안내합니다.

---

## 4. 모델 폴더 구조

```
workspace/models/<모델명>/
  source/              원본 자료 (CSV, pkl 등 / 수정 금지)
  run.py               학습+등록 코드 (init이 생성)
  model_wrapper.py     pyfunc 래퍼 (init이 생성, 수정 가능)
  input_example.json   추론 입력 예시 (run.py 실행 시 생성)
  .aiu_state.json      현재 단계 상태
```

---

## 5. 모드 (init이 판별)

source/ 안에 무엇이 있느냐에 따라 run.py 생성 방식이 달라집니다.

| 모드 | 조건 | 데이터/모델 준비 |
|---|---|---|
| **DATA_ONLY** | CSV만 있음 | 데이터 로드 → 학습 |
| **LOAD_MODEL** | pkl/pt/h5 있음 | 저장된 모델 로드 |
| **RUN_CODE** | .py 있음 | 커스텀 코드 활용 |
| **TEMPLATE** | 빈 폴더 | 빈 템플릿 |

> **중요:** 모드는 "데이터를 어떻게 준비하느냐"의 차이일 뿐,
> **등록은 전부 pyfunc + ModelWrapper로 통일**됩니다.

---

## 6. run.py 9섹션 구조

init이 생성하는 run.py는 항상 이 구조입니다.

```
1. 임포트
2. MLflow 연동      ← 환경 바뀌면 여기만 수정
3. 데이터 준비       (모드별로 다름)
4. 모델 준비         (모드별로 다름)
5. 트레이닝
6. 인풋 샘플         → input_example.json (KServe 형식) 생성
7. MLflow 로깅       → pyfunc + ModelWrapper로 등록
8. Dataset 로깅      → mlflow.data로 train/test 추적
9. 런 스타트         → 전체 실행
```

검증(validate)은 이 9섹션이 다 있는지, TODO가 남았는지 확인합니다.

---

## 7. 상태 흐름

```
initialized(0) → validated(1) → [local_tested(1.5)] → trained(2) → predicted(3) → deployed(4)
```

- `local_tested` 는 선택 단계라 validated와 trained 사이(1.5)
- **localserve는 local_tested에서만** 동작 (results/ 에 로컬 모델 필요)
- train만 하면 MLflow에만 있고 로컬 파일이 없어서 서빙 안 됨

---

## 8. 재작업 / 파일 점검

### 이전 단계로 되돌리기
"다시 학습", "재학습", "다시 검증" 등을 요청하면 해당 단계로 상태를 되돌리고 재실행합니다.
(되돌릴 때 이후 단계의 기록은 삭제됩니다)

### 파일 직접 수정/삭제 시
- **run.py 삭제** → init부터 다시 (강제)
- **results/ 모델 삭제** → 로컬 테스트 단계로 되돌림 (강제)
- **run.py 수정** → "다시 검증을 권장합니다" 안내 (강제 아님)

---

## 9. 설정 (config.json)

```
llm:
  active: 사용할 LLM 이름
  providers:
    - name, type(openai/anthropic), base_url, api_key, model
      temperature(기본 0), max_tokens(기본 1024), timeout(기본 120)
mlflow:
  tracking_uri, username, password
```

- LLM 옵션은 속도 최적화 기본값이 적용됩니다 (temperature=0, max_tokens=1024)
- 세션 중 `/llm` 으로 LLM 전환 가능

---

## 10. 명령어

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

---

## 11. 한눈에 보는 전체 그림

```
[관리자] download_wheels → wheels/ 동봉 배포
                                ↓
[사용자] install → start → 대화 시작
                                ↓
        "준비해줘" → init  → run.py + model_wrapper.py
        "검증해줘" → validate
        "돌려봐"   → localrun (로컬 학습)
        "학습해줘" → train → MLflow에 pyfunc 등록
        "확인해줘" → predict (input_example.json 추론)
        "띄워줘"   → localserve (FastAPI)
        "배포해줘" → deploy
                                ↓
            모든 모델 = pyfunc + ModelWrapper로 MLflow 등록
```

---

## 심화 참고 문서

| 문서 | 내용 |
|---|---|
| [mlflow_api.md](mlflow_api.md) | MLflow 핵심 API 요약 |
| [mlflow_registry.md](mlflow_registry.md) | Model Registry, 버전 관리 |
| [ml_guide.md](ml_guide.md) | 프레임워크별 학습 패턴, 평가 지표 |
| [runpy_patterns.md](runpy_patterns.md) | 데이터 타입별 run.py 완성 패턴 |
| [troubleshooting.md](troubleshooting.md) | 오류 해결 가이드 |
