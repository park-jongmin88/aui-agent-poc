# 확장 계획 (README_TODO)

현재 소스(`agent.py` + `client.py`) 기준으로, 앞으로 파이프라인을 확장하면서
변경·추가할 것을 정리한다.

> 현재 단계: 파이프라인 중 **LLM 단계만** 연결됨.
> RAG / Tool / Prompt / Judge 는 미구현 (자리만 주석으로 표시).

---

## 1. 현재 구조 (지금)

```
agent/
  agent.py          # 모델 본체 — ModelWrapper(pyfunc) + 등록 + _run(LLM만)
  client.py         # 엔드포인트 호출 + 멀티턴 대화 (임시 프로그램)
  test_llm.py       # LLM 통신 단독 점검
  requirements.txt  # mlflow / openai / kserve
  README.md
  README_TODO.md    # (이 문서)
```

지금은 `agent.py` 한 파일에 Wrapper / 로직 / 등록이 모두 들어있다.
LLM 만 붙이는 단계라 단일 파일이 더 단순하고 적합하다.

---

## 2. 확장 후 목표 구조 (예정)

RAG / Tool / Prompt / Judge 가 붙으면 `agent.py` 한 파일이 커지므로,
역할별로 분리한다. (구조 기준은 검토했던 `offline_weather_agent` 샘플)

```
agent/
│
├── aiu_custom/              # 서빙 Wrapper (포탈 표준 구조)
│   ├── __init__.py
│   ├── model_wrapper.py     #   ModelWrapper 본체 (predict 진입점)
│   └── predict.py           #   predict 인터페이스
│
├── core/                    # 에이전트 로직 (확장 핵심 = 지금 _run 분리)
│   ├── __init__.py
│   ├── config.py            #   MLFLOW_CONN / LLM_CONN 등 설정
│   ├── core.py              #   _run 파이프라인 (Trace/Session 기록)
│   ├── llm.py               #   call_llm        ✅ 현재 구현
│   ├── retrieval.py         #   RAG 검색        ➕ 예정
│   ├── tools.py             #   Tool/MCP 호출   ➕ 예정
│   └── prompting.py         #   Prompt 로드     ➕ 예정
│
├── registry/                # MLflow 등록 스크립트
│   ├── __init__.py
│   ├── model.py             #   모델 등록 (지금 register_agent)
│   ├── prompt.py            #   Prompt Registry 등록   ➕ 예정
│   └── judge.py             #   Scorer/Judge 등록      ➕ 예정
│
├── run_model.py             # 실행 진입점 (config → 등록 오케스트레이션)
├── client.py                # 엔드포인트 호출 (임시 대화 프로그램)
├── test_llm.py              # LLM 통신 단독 점검
├── requirements.txt
├── README.md
└── README_TODO.md
```

분리는 **확장 시점에** 진행한다. 지금 당장 나누지 않는다.

---

## 3. 단계별 추가 항목

### 3-1. RAG (Vector DB / Milvus)
- `core/retrieval.py` 신규 — Milvus 검색 함수
- `agent.py` 등록 시 `rag_conn.json` 을 Artifact 로 추가
- `load_context()` 에서 `self.rag_conn` 로드
- `_run()` 에 검색 단계 추가 → 검색 결과를 messages 앞에 컨텍스트로 삽입
- `@mlflow.trace(span_type=RETRIEVER)` 로 검색 span 기록

### 3-2. Tool (MCP)
- `core/tools.py` 신규 — MCP 엔드포인트 호출 함수
- 등록 시 `tool_conn.json` Artifact 추가 → `load_context()` 로드
- `_run()` 에 Tool 호출 단계 추가
- `@mlflow.trace(span_type=TOOL)` 로 Tool span 기록
- 같은 유형 Tool 복수 선택 시 각각 호출

### 3-3. Prompt (Prompt Registry)
- `core/prompting.py` 신규 — MLflow Prompt Registry 에서 로드
- `registry/prompt.py` 신규 — 프롬프트 등록(`register_prompt`)
- 등록 시 `prompt_conf.json` Artifact 추가
- `_run()` 에서 System Prompt 를 messages 맨 앞에 삽입
- Prompt Registry 비었을 때 fallback 로컬 템플릿 사용

### 3-4. Scorer / Judge (목표 4번)
- `registry/judge.py` 신규 — LLM 자동 평가 기준 등록
- `mlflow.genai.evaluate()` 로 품질/안전성/사실성/간결성 평가
- 평가 결과는 MLflow Evaluation Run 으로 저장
- 평가 기준 설정은 포탈 DB(judge_config), 결과는 MLflow

---

## 4. 파이프라인 최종 형태 (목표)

```
INPUT (질문)
  → PROMPT  : System Prompt 주입 (Prompt Registry)
  → RAG     : Milvus 검색 → 컨텍스트
  → TOOL    : MCP 호출 → 도구 결과
  → LLM     : 전체 컨텍스트로 답변 생성
  → OUTPUT  : 답변 반환

각 단계 → @mlflow.trace span 기록
전체     → session_id 로 Sessions 묶음
```

---

## 5. 변경 시 주의 (이미 검증된 사항)

- **signature 는 주지 않는다.** `infer_signature()` 로 스키마를 강제하면
  포탈 자동 필드(`logger`, `aiu_ver`, `trace_id`)와 충돌해 enforce schema 에러.
  → `input_example` 만 등록한다.
- **모든 연결 정보는 Artifact 로 등록.** 서빙 환경엔 원본 파이썬 파일이 없다.
  에셋 추가 시 `xxx_conn.json` → `artifacts` → `load_context()` 순으로 동일 패턴.
- **Trace/Session 은 전용 인자로.**
  `update_current_trace(session_id=..., user=...)` 를 쓴다. (metadata 키 욱여넣기 X)
- **predict 종료 시 flush.** `flush_trace_async_logging(terminate=False)` 로 UI 반영.
- **predict 반환은 답변 문자열 리스트.** dict/DataFrame 직렬화 충돌 방지.
- **pip 버전 고정.** `mlflow==3.10.0`, `openai==2.43.0`, `kserve==0.15.0`
  (포탈 백엔드가 `extractVersion` 으로 버전을 파싱하므로 버전 없으면 등록 실패)
- **에러 처리 규격화.** 모든 에셋 단계는 예외 시 `_agent_error(stage, exc, q, sid)`
  헬퍼로 `[AGENT ERROR]` 포맷을 반환한다. (stage=RAG/TOOL/PROMPT/LLM …)
  서버는 죽지 않고, client 가 원인·단계·traceback 을 한 화면에서 확인. (README 참고)

---

## 6. client.py 관련

- `client.py` 는 **임시 대화 프로그램**이다. 모델 엔드포인트를 호출해
  Trace/Session 이 남는지 확인하는 용도.
- 실제 운영에서는 포탈이 엔드포인트를 호출하므로, client.py 는 검증용으로만 유지.
- 멀티턴은 client 가 history 를 누적해 매 호출마다 전달한다 (서빙은 stateless).
