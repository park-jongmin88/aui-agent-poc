# GenAI Agent

MLflow 에 LLM Agent 를 등록하고 API 서빙 후 대화하는 구조입니다.  
Trace / Session 이 MLflow 에 자동 기록됩니다.

---

## 파일 구성

```
agent/
  agent.py          # MLflow 등록 + ModelWrapper (pyfunc)
  client.py         # API 호출 + 멀티턴 대화
  requirements.txt  # 의존성
  README.md
```

---

## 사용 순서

### 1. 설치

```bash
pip install -r agent/requirements.txt
```

### 2. TODO 채우기

**agent.py**

```python
MLFLOW_CONN = {
    "tracking_uri":     "http://mlflow.internal:5000",
    "username":         "admin",
    "password":         "password",
    "experiment_name":  "my-agent",
    "registered_model": "my-agent",
}

LLM_CONN = {
    "base_url":    "http://qwen.internal:8000/v1",
    "api_key":     "not-needed",
    "model":       "qwen2.5-7b-instruct",
    "temperature": 0.2,
}
```

**client.py**

```python
API_URL = "http://localhost:5001/invocations"
```

### 3. MLflow 등록

```bash
python agent/agent.py
```

출력 예시:
```
============================================================
 MLflow Agent 등록 시작
============================================================
  run_id    : abc123...
  model_uri : runs:/abc123/genai_agent
  registry  : my-agent  v1

  등록 완료.
  MLflow UI : http://mlflow.internal:5000
============================================================
```

### 4. 서빙

```bash
mlflow models serve -m "models://my-agent/1" --port 5001
```

### 5. 대화

```bash
python agent/client.py
```

출력 예시:
```
============================================================
 GenAI Agent Client
============================================================
  API     : http://localhost:5001/invocations
  Session : sess-a1b2c3d4
  종료    : exit / quit / 빈 줄
============================================================

질문> 안녕하세요
답변> 안녕하세요! 무엇을 도와드릴까요?

질문> exit
  대화 종료 — 1 turn  (session: sess-a1b2c3d4)
  MLflow Sessions 탭에서 'sess-a1b2c3d4' 로 확인 가능
```

---

## MLflow 확인

| 항목 | 위치 |
|------|------|
| 등록된 모델 | MLflow UI > Models |
| 실험 Run | MLflow UI > Experiments |
| Trace (호출 기록) | MLflow UI > Traces 탭 |
| Session (대화 묶음) | MLflow UI > Sessions 탭 |

---

## 에셋 추가 시 참고

서빙 환경에서는 원본 파이썬 파일이 없으므로  
모든 연결 정보는 **Artifact 로 등록** 해야 합니다.

`agent.py` 에서 주석 처리된 부분을 참고하세요.

```python
# [0] 연결 정보 정의
# RAG_CONN  = { "host": TODO, "collection": TODO, ... }
# TOOL_CONN = { "endpoint_url": TODO, "api_key": TODO }

# [4] artifacts 에 추가
# artifacts = {
#     "llm_conn":  "llm_conn.json",
#     "rag_conn":  "rag_conn.json",   ← 추가
#     "tool_conn": "tool_conn.json",  ← 추가
# }

# load_context() 에서 로드
# self.rag_conn  = json.load(open(context.artifacts["rag_conn"]))
# self.tool_conn = json.load(open(context.artifacts["tool_conn"]))
```

---

## 의존성

| 패키지 | 버전 |
|--------|------|
| mlflow | 3.10.0 |
| openai | 2.43.0 |
