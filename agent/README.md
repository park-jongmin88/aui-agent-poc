# AI-Studio GenAI Agent (POC)

LangChain 기반 LLM Agent 를 **MLflow pyfunc 모델**로 등록하고,
`custom_server.py`(서빙 이미지)가 감싸 **KServe** 로 서빙하는 구조다.
API 호출마다 MLflow 에 **Trace(호출 기록)** 와 **Session(대화 묶음)** 이 남는다.

---

## 파일 구성

| 파일 | 역할 |
|------|------|
| `agent.py` | 모델 정의 + MLflow 등록 (`python agent.py` 로 등록) |
| `client.py` | 서빙된 엔드포인트 호출 테스트용 대화 프로그램 |
| `requirements.txt` | 서빙 환경 의존성 (버전 고정) |

---

## 작동 순서

1. `python agent.py` 실행 → MLflow 에 모델 등록
2. `LLM_CONN` 이 `llm_conn.json` 으로 저장되어 Artifact 로 함께 등록됨
3. 서빙 이미지 빌드 시 `custom_server.py` 가 이 모델을 로드
4. 서빙 시작 시 `load_context()` 1회 실행 (LangChain autolog 켜짐)
5. 호출 시 `custom_server` → `predict()` → `_run()` → `chain.invoke()`
6. LangChain autolog 가 LLM 호출 트레이스를 자동 기록, `update_current_trace()` 로 세션 묶음

---

## custom_server.py 계약 (반드시 맞춰야 함)

서빙 래퍼(`custom_server.py`)가 모델을 호출할 때 주고받는 형식이 고정되어 있다.

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
  ],
  "custom_server_version": "..."
}
```

**출력** — 반드시 `aiu_output` 키를 포함해야 한다:

```json
{ "aiu_output": "답변 문자열" }
```

> `aiu_output` 키가 없으면 `custom_server` 가 예외 처리 경로로 빠지며
> `UnboundLocalError: log_data` 같은 연쇄 오류가 난다. (서버측 코드라 우리가 못 고침)

---

## 입력 필드 스펙 (`input[0]`)

| 키 | 출처 | 용도 | 비고 |
|----|------|------|------|
| `query` | client | 사용자 질문 | 필수 |
| `system_message` | client | 시스템 프롬프트 | 선택 |
| `llm_api_key` | client | LLM 인증 키 | 비면 에러 반환 |
| `session_id` | client | 대화 세션 묶음 키 | 없으면 `trace_id` 폴백 |
| `user_id` | client | 사용자 식별 | 선택 |

---

## 등록 / 서빙 / 테스트

### 1) 등록
```bash
# agent.py 상단 TODO (MLFLOW_CONN, LLM_CONN) 채운 뒤
python agent.py
```

### 2) 서빙
포탈/KServe 파이프라인에서 등록된 모델을 서빙한다.
(`custom_server.py` 가 이미지 빌드 시 모델을 감싼다)

### 3) 테스트
```bash
# client.py 상단 TODO (API_URL, LLM_API_KEY) 채운 뒤
python client.py
```
같은 `session_id` 로 멀티턴 대화 → MLflow **Sessions** 탭에서 묶여 보인다.

---

## 설계 원칙

1. **연결 정보는 코드에 박지 않는다** — `llm_conn.json` Artifact 로 저장 후 `load_context()` 에서 로드.
2. **signature 는 주지 않는다** — custom_server 가 붙이는 필드(`trace_id`, `logger` 등)와 충돌(enforce schema 에러) 방지. `input_example` 만 등록.
3. **에러는 서버를 죽이지 않는다** — 예외는 `{"aiu_output": "[AGENT ERROR] ..."}` 형태로 담아 반환.
4. **pip 버전 고정 필수** — 포탈 백엔드가 `mlflow==` 패턴으로 버전을 파싱한다. 버전 없으면 등록 실패.

---

## 트레이스 / 세션이 남는 지점

| 지점 | 기록 내용 |
|------|-----------|
| `_run()` 진입 | `agent_pipeline` span 시작 |
| `update_current_trace()` | session_id / user_id / 태그 |
| `chain.invoke()` | LangChain autolog 가 LLM span 자동 기록 |
| `predict()` 종료 | `flush_trace_async_logging` 로 즉시 전송 |
| `register_agent()` | 등록 Run (파라미터/태그) |
