# AI-Studio GenAI Agent (POC)

LangChain 기반 LLM 에이전트를 **MLflow pyfunc 모델**로 등록하고,
`custom_server.py`(서빙 이미지)가 감싸 **KServe** 로 서빙한다.
호출마다 MLflow 에 **Trace**(호출 기록)와 **Session**(대화 묶음)이 남는다.

이 버전의 핵심은 **에셋(asset) 모듈화**다.
`agent.py` 는 *무엇을 켤지 선언* 하고 *순서대로 실행* 만 한다.
실제 기능(프롬프트·LLM·RAG·도구·평가)은 `assets/` 안의 개별 파일에 있다.

> **개발자는 파일 하나 추가 + 리스트에 한 줄**로 기능을 확장한다.

<br>


---


# 1. 확장 로드맵


## 1-1. 에셋 현황

| 에셋 | 상태 | 채우는 칸 | 설명 |
|:--|:--:|:--|:--|
| `prompt` | ✅ 구현 | `system_message` | **MLflow Prompts** 에서 버전 번호로 로드 (client 가 프롬프트+버전 선택) |
| `llm` | ✅ 구현 | `answer` | **MLflow AI Gateway** 로 호출 (LangChain `ChatOpenAI` + autolog). 등록 시 gateway 엔드포인트 선택 필수 |
| `rag` | ✅ 구현 | `context` | 벡터DB 검색 동작 확인. Milvus(iflow_aiu_collection, 1024, L2/IVF_FLAT) + 임베딩 bge-m3(분리 서버). 기본 mode=milvus, mock 도 가능 |
| `tool` | 🟡 목업 | `tools_result` | 가상 API 8종. 키워드 매칭→목업응답, 실제 연동 TODO |
| `judge` | ⬜ 템플릿 | `score` | 응답 품질 평가 (보통 맨 뒤) |


## 1-2. 에셋 추가하는 법 — 3단계

예) RAG 를 켜고 싶다면:

```
1) assets/rag.py 작성        # NAME / build / run 규약대로 (템플릿 있음)

2) config.py 의 ENABLED_ASSETS 에 추가   # 리스트 순서 = 실행 순서
   ENABLED_ASSETS = ["prompt", "rag", "llm"]

3) (필요 시) config.py 의 ASSET_CONN 에 연결정보 추가
   ASSET_CONN = { "rag": {"mode": "milvus", "uri": ..., "collection": ..., "top_k": 3} }
```

→ `agent.py` 의 실행 로직은 **건드리지 않는다.** 파이프라인 루프가 알아서 순서대로 돌린다.


## 1-3. 그 외 예정

- **헬스체크** — KServe 는 커스텀 엔드포인트 추가 불가 → `predict()` 안에서 `mode` 분기로 처리 (현재 `list_prompts` 모드가 같은 방식)
- **빌더 연동 (보류)** — `ENABLED_ASSETS` 가 곧 빌더 화면의 체크박스. 연결정보를 AI Studio DB 로 외부화하고, 로그인 user_id 로 조회. 시크릿은 평문 저장 금지. → *소스 레벨 에셋 추가가 안정화된 뒤 착수.*

<br>


---


# 2. 전체 구조


## 2-1. 폴더

```
README.md
config.py            설정 (ENABLED_ASSETS, MLFLOW_CONN, LLM_*, ASSET_CONN)
agent.py             등록 진입점 (register_agent + 단계별 한국어 진단)
client.py            서빙 엔드포인트 호출 테스트용 (프롬프트+버전 2단계 선택)
judge_register.py    judge 등록 (평가지+gateway LLM 선택, 자동 트래킹 on/off)
evaluate.py          평가 실행 (등록된 judge 로 trace 채점)
mlflow_inspect.py    조회 헬퍼 (gateway/prompt/judge 확인용, 단독 실행)
requirements.txt     서빙 의존성 (버전 고정). agent.py 가 이 파일을 참조 — 의존성은 여기서만 관리
aiu_custom/          서빙되는 모델 본체
├── __init__.py
├── model_wrapper.py   ModelWrapper (load_context / predict / 파이프라인 + trace 마스킹)
└── predict.py         re-export (서빙 진입점)
assets/              에셋 모듈 모음 ← 기능 추가는 여기
├── __init__.py     에셋 공통 규약 + ctx 생성/로더 (prompt_version 포함)
├── prompt.py       [구현] MLflow Prompts 버전 번호 로드 (캐싱)
├── llm.py          [구현] LangChain 체인으로 답변 생성
├── rag.py          [구현] Milvus 연결 (iflow_aiu_collection, 1024, L2/IVF_FLAT) + 임베딩 bge-m3(분리 서버 API). mode=milvus 기본
├── tool.py         [목업] mocks/ 가상 API 호출 (실제 연동 TODO)
└── judge.py        [템플릿]
mocks/               목업 데이터 (실제 연결 전 POC용)
├── rag_documents.json   딥러닝/ML/GenAI 문서 20건
└── tool_apis.json       가상 API 8종 (날씨/시간/계산/GPU/모델/실험/데이터셋/학습)
dev_note/            개발 문서/다이어그램 (코드와 분리)
├── AIU_AGENT_POC_SUMMARY.md   아키텍처/설계결정 종합
├── JUDGE_GATEWAY_AUTH.md      judge gateway Basic 인증 트러블슈팅
├── PROMPT_VERSION.md          프롬프트 버전 처리(별칭→버전번호, OSS 순차탐색)
├── portal_arch_v6.png         포탈 x AGENT UI 구상도
├── agent_flow3.png            Agent POC 한눈에 보기
├── rag_flow.png               RAG 파이프라인 흐름도
└── mlflow_genai_overview.png  MLflow GenAI 탭 정리+관계도
```


## 2-2. aiu_custom/predict.py — 서빙 진입점

`custom_server.py`(서빙 이미지)는 **항상 같은 경로**에서 모델 클래스를 찾는다.
그 고정 경로가 `aiu_custom.predict.ModelWrapper` 다.

```python
# aiu_custom/predict.py — 내용은 한 줄 (re-export)
from .model_wrapper import ModelWrapper
```

- **왜 분리?** 실제 코드(`model_wrapper.py`)가 길어지거나 바뀌어도,
  서빙이 찾는 진입점(`predict.py`)은 변하지 않게 하기 위해서다.
- **빌더 관점** 진입점은 고정, 내용물(config / assets / mocks)만 갈아끼우면 된다.
  즉 에이전트마다 설정이 달라져도 `ModelWrapper` 코드는 하나로 공유한다.

```
custom_server.py
   └─ aiu_custom.predict.ModelWrapper   ← 고정된 진입점
        └─ model_wrapper.py             ← 실제 로직 (바뀌어도 됨)
             ├─ config.py               ← 설정 (빌더가 교체)
             ├─ assets/                 ← 기능 (켜고 끔)
             └─ mocks/                  ← 데이터
```


## 2-3. 한 번의 호출 흐름

```
predict()                          custom_server 진입점 (aiu_custom.predict.ModelWrapper)
  └─ _run()                        @mlflow.trace (agent_pipeline)
       ├─ update_current_trace()   session / user 기록
       └─ for name in ENABLED_ASSETS:
              ctx = assets[name].run(ctx, resource)
              #  prompt → rag → tool → llm  순서로 ctx(보따리)를 통과시킨다
```

<br>


---


# 3. 에셋 규약

모든 에셋 파일(`assets/*.py`)은 아래 형태를 따른다.

```python
NAME = "rag"                       # ENABLED_ASSETS 항목과 매칭되는 이름

def build(conn: dict):
    """등록/로드 시 1회. 연결정보로 준비된 객체(체인/클라이언트 등)를 반환."""
    ...

def run(ctx: dict, resource) -> dict:
    """호출마다. ctx(대화 맥락)를 받아 자기 칸을 채우고 반환."""
    ...
```


## ctx — 파이프라인 맥락 (에셋들이 순서대로 주고받는 보따리)

| 키 | 채우는 에셋 | 설명 |
|:--|:--|:--|
| `query` | (입력) | 사용자 질문 |
| `prompt_id` | (입력) | client 가 고른 프롬프트 이름 |
| `system_message` | prompt | 시스템 프롬프트 (서버에서 로드) |
| `context` | rag | 검색 결과 |
| `tools_result` | tool | 도구 실행 결과 |
| `answer` | llm | 생성된 답변 → 최종 반환값 |
| `score` | judge | 평가 결과 |

<br>


---


# 4. 프롬프트 동작 (중요)

**A 원칙 — 프롬프트의 주인은 서버다.**
client 는 프롬프트 내용을 들고 있지 않는다. 어떤 프롬프트를 쓸지 **이름(id)만 고른다.**
실제 텍스트는 항상 **MLflow Prompt Registry** 에서 로드한다.

```
client 시작
   │  서버에 목록 요청 (mode=list_prompts)
   ▼
[1] aiu-agent [3]  [2] it-tutor [2]  ...   ← 프롬프트명 [버전 개수]
   │  프롬프트 선택 → 버전 목록 요청 (mode=list_versions)
   ▼
[1] 버전 1   [2] 버전 2   [3] 버전 3   [0] 최신   ← 버전 선택 (2단계)
   │  이후 prompt_id + prompt_version 만 실어 보냄
   ▼
agent: prompt 에셋이 MLflow 에서 해당 버전 로드 → system_message 채움
   │  (로드 실패/미선택 시 default_system 으로 폴백)
   ▼
llm 에셋이 답변 생성
```

> 버전 조회 주의: `search_prompt_versions` 는 Databricks 전용이라 OSS 에서는 안 된다.
> `load_prompt(name, version=N)` 으로 v1 부터 순차탐색해 버전 목록을 얻는다. (→ dev_note/PROMPT_VERSION.md)

- **프롬프트 타입:** `text` (시스템 지시문 한 덩어리. role 구조는 llm 에셋이 짠다)
- **폴백:** `agent.py` 의 `ASSET_CONN["prompt"]["default_system"]`
- client 가 `system_message` 를 보내도 **무시** 된다 (A 원칙).

<br>


---


# 5. custom_server.py 계약

서빙 래퍼가 모델을 호출할 때의 입출력 형식은 **고정** 이다.


## 입력 — `predict(model_input)` 으로 들어오는 dict

```json
{
  "trace_id": "...",
  "pis_name": "...",
  "input": [
    {
      "query": "파이썬이 뭐야?",
      "prompt_id": "it-tutor",
      "session_id": "sess-abc123"
    }
  ]
}
```
> LLM 인증은 **MLflow AI Gateway** 가 처리한다. client 는 키를 보내지 않는다.


## 출력 — 반드시 `aiu_output` 키 포함

```json
{ "aiu_output": "답변 문자열" }
```

> ⚠️ `aiu_output` 이 없으면 custom_server 가 예외 경로로 빠지며
> `UnboundLocalError: log_data` 등 연쇄 오류가 난다. (서버측 코드라 수정 불가)


## 입력 필드 (`input[0]`)

| 키 | 출처 | 용도 | 비고 |
|:--|:--|:--|:--|
| `query` | client | 사용자 질문 | 대화 시 필수 |
| `prompt_id` | client | 쓸 프롬프트 이름 | 없으면 폴백 |
| `prompt_version` | client | 쓸 프롬프트 버전 번호 | 없으면 최신 |
| `session_id` | client | 대화 세션 묶음 | 없으면 trace_id 폴백 |
| `user_id` | client | 사용자 식별 | 선택 |
| `mode` | client | `list_prompts`/`list_versions` 면 목록 조회 | 없으면 일반 대화 |

<br>


---


# 6. Trace / Session 기록

| 지점 | 기록 |
|:--|:--|
| `_run()` 진입 | `agent_pipeline` span |
| `update_current_trace()` | `mlflow.trace.session` / `mlflow.trace.user` (표준 metadata 키) |
| 에셋 `run()` | LangChain autolog 가 LLM span 자동 기록 |
| `predict()` 종료 | `flush_trace_async_logging` 로 즉시 전송 |

> ⚠️ **MLflow 3.10 주의:** `update_current_trace(session_id=...)` 파라미터는 3.11+ 전용.
> 3.10 에서는 `metadata` 의 `mlflow.trace.session` / `mlflow.trace.user` **표준 키**로 넣어야
> Sessions 탭에 묶인다.

<br>


---


# 7. 등록 / 서빙 / 테스트

> **권장 환경:** Python **3.11.9** (kserve 0.15.0 호환). 가상환경 사용 권장.
> ```bash
> py -3.11 -m venv venv          # Windows
> venv\Scripts\activate
> pip install -r requirements.txt
> ```
> 로컬에서 등록/테스트만 한다면 kserve 는 빼고 설치해도 된다 (서빙 이미지에서만 필요).

```bash
# 1) 등록  — config.py 의 TODO(MLFLOW_CONN) 채운 뒤 실행.
#    등록 중 MLflow AI Gateway 의 chat 엔드포인트 목록을 조회해 보여주며,
#    화면에서 사용할 것을 선택한다 (필수 - 건너뛰기 없음).
python agent.py

# 2) 서빙  — 포탈/KServe 파이프라인에서 등록 모델을 서빙 (custom_server.py 가 감쌈)

# 3) 테스트 — client.py 상단 TODO(API_URL) 채운 뒤 실행.
#    LLM 인증은 gateway 가 처리하므로 client 는 키를 보내지 않는다.
python client.py
```

같은 `session_id` 로 멀티턴 → MLflow **Sessions** 탭에서 한 대화로 묶여 보인다.

<br>


---


# 8. 설계 원칙

1. **역할 분리** — 설정은 `config.py`, 서빙 모델은 `aiu_custom/`, 기능은 `assets/`, 등록은 `agent.py`.
2. **서빙 진입점 표준화** — `aiu_custom.predict.ModelWrapper` 로 일관 노출 (custom_server 가 찾는 경로).
2. **프롬프트 주인은 서버** — client 는 id 만 고른다 (A 원칙).
3. **연결정보는 코드에 박지 않는다** — `conn.json` Artifact + `load_context()` 로드.
4. **signature 는 주지 않는다** — custom_server 가 붙이는 필드와 충돌(enforce schema) 방지. `input_example` 만.
5. **에러는 서버를 죽이지 않는다** — 예외는 `{"aiu_output": "[AGENT ERROR] ..."}` 로 반환.
7. **민감정보는 trace 에 남기지 않는다** — api_key 는 traced 인자에서 제외 + span_processor 로 [REDACTED] 마스킹.
6. **pip 버전 고정 필수** — 포탈이 `mlflow==` 패턴으로 버전 파싱.
