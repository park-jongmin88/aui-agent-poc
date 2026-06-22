# GenAI Agent (LLM + MLflow Trace/Session)

LLM Agent 를 MLflow pyfunc 모델로 등록하고, KServe 엔드포인트로 서빙한 뒤
API 호출로 대화하면서 **Trace / Session 을 MLflow GenAI 메뉴에 기록**하는 구조입니다.

> 현재 단계: 파이프라인 중 **LLM 단계만** 연결되어 있습니다.
> RAG / Tool / Prompt 는 주석으로 자리만 잡아두었고, 이후 단계적으로 붙입니다.

---

## 동작 흐름

```
[1] agent.py 실행
      └─ MLflow 에 ModelWrapper(pyfunc) 등록  (대화 없음, 등록만)

[2] 모델 서빙  (포탈 / KServe 엔드포인트)
      └─ /v1/models/<model>:predict  엔드포인트 생성

[3] client.py 실행
      └─ 엔드포인트로 질문 전송 → 답변 수신 (멀티턴 대화)

[4] MLflow GenAI 메뉴
      └─ Trace : LLM 호출 단위 기록
         Session : 같은 session_id 대화 묶음
```

핵심: **Trace / Session 기록은 모델 엔드포인트(predict) 안에서 일어납니다.**
클라이언트가 MLflow 에 직접 붙지 않습니다. (B안)

---

## 파일 구성

```
agent/
  agent.py          # 올라갈 모델  (ModelWrapper + MLflow 등록)
  client.py         # 엔드포인트 호출용 임시 대화 프로그램
  requirements.txt  # 의존성
  test_llm.py       # LLM 통신 단독 점검
  README.md
```

| 파일 | 역할 |
|------|------|
| `agent.py` | MLflow 에 등록되는 **모델 본체**. `ModelWrapper.predict()` 가 서빙 진입점 |
| `client.py` | 서빙된 **엔드포인트를 호출**하는 임시 대화 클라이언트 |
| `test_llm.py` | 서빙 전에 **LLM(Qwen) 통신만** 따로 확인 |

---

## 사용 순서

### 1. 설치

```bash
pip install -r agent/requirements.txt
```

### 2. agent.py — 상단 TODO 채우기

```python
MLFLOW_CONN = {
    "tracking_uri":     "http://mlflow.internal:5000",
    "username":         "...",
    "password":         "...",
    "experiment_name":  "genai-agent",
    "registered_model": "genai-agent",
}

LLM_CONN = {
    "base_url":    "http://qwen.internal:8000/v1",
    "api_key":     "not-needed",
    "model":       "qwen2.5-7b-instruct",
    "temperature": 0.2,
}
```

### 3. MLflow 등록

```bash
python agent/agent.py
```

→ run_id / model_uri 출력. 대화는 하지 않고 **등록만** 합니다.

### 4. 서빙

포탈에서 등록된 모델을 서빙하거나, 로컬에서:

```bash
mlflow models serve -m "models://<registered_model>/1" --port 5001
```

### 5. client.py — API_URL 채우고 대화

```python
API_URL = "http://<model>.<project>.<host>/v1/models/<model>:predict"
```

```bash
python agent/client.py
```

```
질문> 안녕하세요
[응답 원본] ...
```

### 6. MLflow GenAI 메뉴 확인

| 확인 항목 | 위치 |
|-----------|------|
| Trace (LLM 호출 기록) | Experiment > Traces |
| Session (대화 묶음) | Experiment > Sessions (같은 session_id) |

---

## 입력 / 출력 형식

서빙 표준(MLflow pyfunc) 형식입니다. `predict()` 가 DataFrame 으로 받아
`question` 컬럼을 사용합니다.

**입력**
```json
{
  "inputs": [
    {
      "question":   "안녕하세요",
      "session_id": "sess-abc123",
      "user_id":    "user-001",
      "history":    "[]"
    }
  ]
}
```

- `question` : 질문 (필수)
- `session_id` : 대화 세션 ID (없으면 자동 생성)
- `user_id` : 사용자 ID (선택)
- `history` : 이전 대화 JSON 문자열 (멀티턴용, 클라이언트가 누적해 전달)

**출력**
```json
["답변 문자열", ...]
```

답변 문자열 리스트로 반환합니다.

---

## 설계 메모

### signature 를 주지 않는다
`infer_signature()` 로 입력 스키마를 강제하면, 포탈이 자동으로 붙이는 필드
(`logger`, `aiu_ver`, `trace_id` 등)와 충돌해 **enforce schema 에러**가 납니다.
그래서 `signature` 없이 `input_example` 만 등록합니다.

### 모든 연결 정보는 Artifact 로 등록
서빙 환경에는 원본 파이썬 파일이 없습니다.
`LLM_CONN` 은 `llm_conn.json` 으로 저장해 Artifact 로 등록하고,
`load_context()` 에서 로드해 `self.llm_conn` 으로 사용합니다.

> 에셋(RAG / Tool / Prompt)이 추가되면 동일하게
> `artifacts` 에 파일 추가 → `load_context()` 에서 로드 → `_run()` 에서 사용.
> (현재는 주석으로 자리만 표시)

### Trace / Session 기록
`_run()` 에서 `mlflow.update_current_trace(session_id=..., user=...)` 전용 인자로
기록합니다. predict 종료 시 `flush_trace_async_logging()` 으로 UI 반영을 앞당깁니다.

```
@mlflow.trace(span_type=AGENT)  _run        ← 파이프라인 전체
  └─ @mlflow.trace(span_type=LLM)  call_llm  ← LLM 호출
```

### history (멀티턴)
서빙은 stateless 이므로 클라이언트(`client.py`)가 history 를 누적해
매 호출마다 JSON 문자열로 전달합니다.

---

## 이후 추가 예정

| 단계 | 내용 |
|------|------|
| RAG | Vector DB 검색 → `rag_conn.json` Artifact + `_run()` 에 단계 추가 |
| Tool | MCP Tool 호출 → `tool_conn.json` Artifact + `_run()` 에 단계 추가 |
| Prompt | System Prompt 주입 → `prompt_conf.json` Artifact |

---

## 에이전트 에러 처리 (공식 규격)

서빙 환경에서 client 는 보통 HTTP 500 본문 일부만 받기 때문에,
서버(predict) 안에서 무슨 오류가 났는지 파악하기 어렵다.
이를 해결하기 위해 **서버 오류를 응답 본문에 담아 client 까지 그대로 전달**하는
규격을 정한다. 앞으로 추가되는 모든 에셋(RAG / Tool / Prompt / Judge)도
이 규격을 따른다.

### 규격 1 — 서버는 죽지 않고 오류를 응답에 담는다

`predict()` 의 질문 처리 루프를 `try/except` 로 감싼다.
예외가 나면 서버가 500 으로 죽는 대신, **정상 200 응답**으로
아래 형식의 문자열을 답변 자리에 담아 반환한다.

```
[AGENT ERROR]
type   : <예외 타입>
message: <예외 메시지>
question: <질문>
session : <session_id>
---- traceback ----
<traceback 전체>
```

핵심: `[AGENT ERROR]` 프리픽스로 시작한다. (client 가 이 프리픽스로 오류를 판별)

### 규격 2 — client 는 세 가지를 구분한다

| 상황 | 표시 | history 누적 |
|------|------|--------------|
| 정상 답변 | `답변> ...` | O |
| 서버 내부 오류 (200 + `[AGENT ERROR]`) | `[서버 내부 오류] ...` | X |
| HTTP 오류 (500/400 등) | `[HTTP 오류]` + 본문 펼침 | X |

- HTTP 오류 본문이 JSON 이면 들여쓰기해서 보기 좋게 출력한다.
- 오류 응답은 history 에 쌓지 않는다. (다음 턴 오염 방지)

### 규격 3 — 에셋 추가 시 동일 패턴 적용

새 에셋(RAG / Tool / Prompt)을 `_run()` 에 추가할 때도
각 단계에서 같은 방식으로 오류를 담는다. 단계명을 함께 표기하면
어느 단계에서 실패했는지 바로 알 수 있다.

```python
# 예시 — RAG 단계
try:
    context = rag_search(question, self.rag_conn)
except Exception as e:
    return _agent_error("RAG", e, question, session_id)   # [AGENT ERROR] stage=RAG ...
```

> 권장: 공통 헬퍼 `_agent_error(stage, exc, question, session_id)` 를 두고
> 모든 에셋이 같은 포맷을 재사용한다. (에러 처리 규격화)

이렇게 하면 어떤 에셋에서 문제가 생겨도 client 화면에서
`[AGENT ERROR]` 한 형식으로 원인·단계·traceback 을 한 번에 확인할 수 있다.

---

## 의존성

| 패키지 | 버전 |
|--------|------|
| mlflow | 3.10.0 |
| openai | 2.43.0 |
| kserve | 0.15.0 |
