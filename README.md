# AI-Studio GenAI Agent (POC)

LangChain 기반 LLM Agent 를 **MLflow pyfunc 모델**로 등록하고,
`custom_server.py`(서빙 이미지)가 감싸 **KServe** 로 서빙하는 구조다.
호출마다 MLflow 에 **Trace(호출 기록)** 와 **Session(대화 묶음)** 이 남는다.

이 버전의 핵심은 **에셋(asset) 모듈화**다.
`agent.py` 는 "무엇을 켤지" 선언하고 "순서대로 실행"만 하며,
실제 기능(LLM/RAG/Tool/Judge)은 `agent/assets/` 안의 개별 파일에 있다.
개발자는 **파일 하나 추가 + 리스트에 한 줄**로 기능을 확장한다.

---

## 폴더 구조

```
README.md                  # 이 문서
agent/
  ├── agent.py             # 진입점: 에셋 조립 + MLflow 등록 (로직 없음, 얇게 유지)
  ├── client.py            # 서빙 엔드포인트 호출 테스트용 대화 프로그램
  ├── requirements.txt     # 서빙 환경 의존성 (버전 고정)
  └── assets/              # 에셋 모듈 모음 (여기에 추가)
      ├── __init__.py      # 에셋 공통 규약 + ctx 생성/로더
      ├── prompt.py        # [구현] 시스템 프롬프트 구성
      ├── llm.py           # [구현] LangChain 체인으로 답변 생성
      ├── rag.py           # [템플릿] 검색 -> ctx["context"]
      ├── tool.py          # [템플릿] 도구 -> ctx["tools_result"]
      └── judge.py         # [템플릿] 평가 -> ctx["score"]
```

---

## 동작 흐름

1. `python agent.py` → MLflow 에 모델 등록 (`assets/` 도 함께 패키징)
2. 서빙 이미지가 `custom_server.py` 로 모델을 감쌈
3. 서빙 시작 → `load_context()` 1회 (autolog 켜짐, 에셋 모듈 로드)
4. 호출 → `predict()` → `_run()` → **켜진 에셋을 순서대로 실행**
5. LangChain autolog + `update_current_trace()` 로 Trace/Session 기록

```
predict()
  └─ _run()                         @mlflow.trace (agent_pipeline)
        ├─ update_current_trace()   세션/유저 기록
        └─ for name in ENABLED_ASSETS:
              ctx = assets[name].run(ctx, resource)   # prompt -> llm -> ...
```

---

## 에셋 규약

모든 에셋 파일(`assets/*.py`)은 아래 형태를 따른다.

```python
NAME = "rag"                          # ENABLED_ASSETS 항목과 매칭되는 이름

def build(conn: dict):
    """등록/로드 시 1회. 연결정보로 준비된 객체(체인/클라이언트 등)를 반환."""
    ...

def run(ctx: dict, resource) -> dict:
    """호출마다. ctx(대화 맥락)를 받아 자기 칸을 채우고 반환."""
    ...
```

### ctx — 파이프라인 맥락

에셋들이 순서대로 주고받는 공용 보따리. 각 에셋은 자기 칸만 채운다.

| 키 | 채우는 에셋 | 설명 |
|----|-------------|------|
| `query` | (입력) | 사용자 질문 |
| `system_message` | prompt | 시스템 프롬프트 |
| `context` | rag | 검색 결과 |
| `tools_result` | tool | 도구 실행 결과 |
| `answer` | llm | 생성된 답변 (최종 반환값) |
| `score` | judge | 평가 결과 |

---

## 에셋 추가하는 법 (3단계)

예) RAG 를 켜고 싶다면:

**1) `agent/assets/rag.py` 작성** — `NAME`/`build`/`run` 규약대로 (템플릿 이미 있음)

**2) `agent.py` 의 `ENABLED_ASSETS` 에 추가** — 리스트 순서가 실행 순서다
```python
ENABLED_ASSETS = ["prompt", "rag", "llm"]
```

**3) 연결정보가 필요하면 `agent.py` 의 `ASSET_CONN` 에 추가**
```python
ASSET_CONN = {
    "rag": {"vector_db": "milvus", "host": "...", "port": 19530, "collection": "...", "top_k": 5},
}
```

→ 끝. `agent.py` 의 실행 로직은 건드리지 않는다. (루프가 알아서 순서대로 돌린다)

---

## custom_server.py 계약

서빙 래퍼가 모델을 호출할 때의 입출력 형식은 고정이다.

**입력** — `predict(model_input)` 으로 들어오는 dict:
```json
{
  "trace_id": "...",
  "pis_name": "...",
  "logger": "<함수>",
  "input": [
    {
      "query": "HI!",
      "system_message": "당신은 친절한 Agent 입니다.",
      "llm_api_key": "사용자키",
      "session_id": "sess-abc123"
    }
  ]
}
```

**출력** — 반드시 `aiu_output` 키를 포함:
```json
{ "aiu_output": "답변 문자열" }
```

> `aiu_output` 이 없으면 custom_server 가 예외 경로로 빠지며
> `UnboundLocalError: log_data` 등 연쇄 오류가 난다. (서버측 코드라 우리가 못 고침)

### 입력 필드 (`input[0]`)

| 키 | 출처 | 용도 | 비고 |
|----|------|------|------|
| `query` | client | 사용자 질문 | 필수 |
| `system_message` | client | 시스템 프롬프트 | 선택 |
| `llm_api_key` | client | LLM 인증 키 | 비면 에러 반환 |
| `session_id` | client | 대화 세션 묶음 | 없으면 trace_id 폴백 |
| `user_id` | client | 사용자 식별 | 선택 |

---

## Trace / Session 기록

| 지점 | 기록 |
|------|------|
| `_run()` 진입 | `agent_pipeline` span |
| `update_current_trace()` | `mlflow.trace.session` / `mlflow.trace.user` (표준 metadata 키) |
| 에셋 `run()` | LangChain autolog 가 LLM span 자동 기록 |
| `predict()` 종료 | `flush_trace_async_logging` 로 즉시 전송 |

> **주의 (MLflow 3.10):** `update_current_trace(session_id=...)` 파라미터는 3.11+ 전용이다.
> 3.10 에서는 `metadata` 의 `mlflow.trace.session` / `mlflow.trace.user` 표준 키로 넣어야
> Sessions 탭에 묶인다.

---

## 등록 / 서빙 / 테스트

### 등록
```bash
# agent.py 상단 TODO (MLFLOW_CONN, LLM_BASE_URL, LLM_MODEL) 채운 뒤
python agent.py
```

### 서빙
포탈/KServe 파이프라인에서 등록 모델을 서빙한다. (`custom_server.py` 가 감쌈)

### 테스트
```bash
# client.py 상단 TODO (API_URL, LLM_API_KEY) 채운 뒤
python client.py
```
같은 `session_id` 로 멀티턴 → MLflow **Sessions** 탭에서 묶여 보인다.

---

## 설계 원칙

1. **agent.py 는 얇게** — 조립과 선언만. 기능은 에셋에.
2. **연결정보는 코드에 박지 않는다** — `conn.json` Artifact + `load_context()` 로드.
3. **signature 는 주지 않는다** — custom_server 가 붙이는 필드와 충돌(enforce schema) 방지. `input_example` 만.
4. **에러는 서버를 죽이지 않는다** — 예외는 `{"aiu_output": "[AGENT ERROR] ..."}` 로 반환.
5. **pip 버전 고정 필수** — 포탈이 `mlflow==` 패턴으로 버전 파싱.

---

## 확장 로드맵 (TODO)

| 에셋 | 상태 | 채우는 ctx | 메모 |
|------|------|-----------|------|
| prompt | ✅ 구현 | `system_message` | 현재 client 가 전달. 추후 서버/DB 관리로 이전 |
| llm | ✅ 구현 | `answer` | LangChain `ChatOpenAI` + autolog |
| rag | ⬜ 템플릿 | `context` | Milvus 등 vector DB 검색 |
| tool | ⬜ 템플릿 | `tools_result` | 외부 API / 함수 호출 |
| judge | ⬜ 템플릿 | `score` | 응답 품질 평가, 보통 맨 뒤 |

### 그 외 예정
- **헬스체크** — KServe 는 커스텀 엔드포인트 불가 → `predict()` 안에서 `mode=healthcheck` 분기로 각 에셋 ping
- **빌더 연동 (보류)** — `ENABLED_ASSETS` 가 곧 빌더 화면의 체크박스. LLM/에셋 연결정보를 AI Studio DB 로 외부화하고, 로그인 user_id 기준으로 조회. 시크릿은 평문 저장 금지(암호화/Vault). MLflow session_id 와 포탈 로그인 세션 연결.

> 빌더 항목은 현재 **보류**. 소스/폴더 레벨의 에셋 추가를 먼저 안정화한 뒤 착수한다.
