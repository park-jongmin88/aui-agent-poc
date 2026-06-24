# 개발 TODO

추가 개발건 목록. 위 체크리스트로 진행 상황을 관리하고, 아래 상세를 보며 하나씩 구현한다.

---


## ✅ 완료

- [x] **에셋 모듈화** — `agent.py` 는 조립만, 기능은 `assets/` 로 분리
- [x] **프롬프트 선택** — MLflow Prompts 에서 로드, client 는 id 만 선택 (A 원칙)
- [x] **Trace / Session** — 3.10 표준 metadata 키로 기록
- [x] **system 단일화** — system 메시지 1개로 합쳐 400 BadRequest 해결
- [x] **rag 목업** — mocks/ json 으로 검색 동작 (Milvus 연결은 TODO 분리)
- [x] **tool 목업** — 가상 API 8종, 키워드 매칭으로 다중 호출 (실제 연동 TODO 분리)
- [x] **에셋 트레이스** — 각 에셋(prompt/rag/tool/llm) run 에 span 추가. 보따리(ctx) 흐름이 트레이스 트리에 보임
- [x] **judge 사후 평가** — 세션 종료 시 답변을 LLM 으로 채점(정확성/도움됨/명확성). 평가모델 분리는 TODO
- [x] **구조 분리** — config.py(설정) + aiu_custom/(ModelWrapper) + assets/ + agent.py(등록). 서빙 진입점 aiu_custom.predict.ModelWrapper 로 표준화

---


## ⬜ 할 일

- [ ] **1. LLM 모델 선택** — base_url(공급자 API)에서 모델 목록 받아 고르기 *(다음 1순위)*
- [ ] **2. judge 평가모델 분리** — 현재 생성 LLM 재사용(POC). 평가 전용 모델로 외부화 (self-bias 해소)
- [ ] **3. rag 실제 연결** — Milvus 연결 (목업 완료, 실제 검색 TODO만 남음)
- [ ] **4. tool 실제 연동** — 실제 API + LLM function calling (목업 완료)
- [ ] **5. 프롬프트 태그 필터** — 에이전트/유저별로 프롬프트 거르기 *(선택)*
- [ ] **6. 빌더 연동** — 모델/프롬프트/judge 를 포탈 DB 로 외부화 *(장기·보류)*

### 의존 관계

```
LLM 모델 선택 ─┐
프롬프트 선택 ─┴─→ 빌더에서 DB 외부화로 통합
judge ───────────→ 사후 평가 (독립)
rag / tool ──────→ 보따리에 자료 추가 (독립)
```

<br>


---


# 상세


## 1. LLM 모델 선택

**목표:** 지금 `agent.py` 에 `LLM_MODEL` 이 하드코딩돼 있다. 이를 프롬프트처럼 **목록에서 고르는** 방식으로 바꾼다.

**방식:** 프롬프트 선택과 동일 패턴 (agent 경유 = B안)

```
client 시작
  ├─ 1. mode="list_models"  → agent 가 공급자 API /v1/models 호출 → 목록 반환
  │       └ 사용자가 모델 선택
  └─ 2. mode="list_prompts" → 프롬프트 선택 (기존)
        ↓
  대화 전송: query + model_id + prompt_id
```

**구현 포인트**
- `predict()` 에 `mode="list_models"` 분기 추가
- 모델 목록 조회: `OpenAI(base_url, api_key).models.list()`
- 입력에 `model_id` 필드 추가 (ctx 에도)
- llm 에셋: 고른 `model_id` 로 체인 재생성 (현재 api_key 바뀔 때 재생성하는 로직 확장)
- client: ① 모델 선택 → ② 프롬프트 선택 → 대화

**나중에 (빌더)**
- 모델 목록 출처: 공급자 API → **포탈 DB** 로 전환 (구조는 그대로)

---


## 2. judge — 사후 평가

**목표:** 대화 세션이 끝나면 judge 가 한 번 돌아 답변 품질을 채점한다.

**실행 시점:** 대화 중이 아니라 **세션 끝에 한 번** (실시간 X → 응답 지연/비용 방지)

**재료:** 이미 쌓이는 Trace / Session 이 그대로 평가 대상

**API** (MLflow 3.10 호환 확인됨)
```python
from mlflow.genai.judges import make_judge

judge = make_judge(
    name="quality",
    instructions="Rate the quality of {{ outputs }} for {{ inputs }}. Score 1-5.",
    model=JUDGE_MODEL,        # 하드코딩 X → 설정으로 외부화
)
results = mlflow.genai.evaluate(data=traces, scorers=[judge])
```

**구현 포인트**
- 트리거 방식: `mode="judge"` (list_prompts 와 같은 패턴) 또는 별도 스크립트
- judge 모델: **생성용 LLM 과 별개로** 지정 가능하게 설정으로 빼둠
- 위치 결정 필요: `assets/judge.py`(에셋) vs `evaluate.py`(별도 스크립트)
  - "마지막에 한번" 성격이면 에셋보다 **별도 트리거** 가 맞음

**미정**
- 평가 기준(무엇을 채점할지) — criteria 정해지면 instructions 작성

---


## 3. rag 에셋  (목업 완료 / 실제 연결 TODO)

**목표:** 질문 관련 문서를 검색해 `ctx["context"]` 에 넣는다. LLM 이 그 자료를 참고해 답변.

**현재 상태 — 목업 동작 중**
- `ENABLED_ASSETS = ["prompt", "rag", "llm"]` 로 켜져 있음
- `ASSET_CONN["rag"] = {"mode": "mock", "top_k": 3}`
- 목업 데이터: `agent/mocks/rag_documents.json` (딥러닝/ML/GenAI 20건)
- 검색 방식: 키워드 매칭 (`_search_mock`) → 실제 벡터검색의 입출력만 흉내
- 등록 시 json 을 Artifact("rag_mock")로 패키징, `load_context` 가 경로 주입

**목업 / 실제 분리 (rag.py)**
```
build()  -> mode "mock"   -> _build_mock      (json 로드)
            mode "milvus" -> _build_milvus    ← TODO
run()    -> mode "mock"   -> _search_mock     (키워드 매칭)
            mode "milvus" -> _search_milvus   ← TODO
```
- build/run 은 분기만. 목업/실제 로직은 서로 다른 함수라 섞이지 않음.

**실제 연결 시 (Milvus) 할 일 — TODO**
- `_build_milvus()` : pymilvus 연결 + collection.load() + 임베딩 함수 준비
- `_search_milvus()`: query 임베딩 → 벡터 검색 → 본문 join
- `ASSET_CONN["rag"]` 를 `{"mode":"milvus", host, port, collection, top_k}` 로 교체
- → 이 두 함수와 conn 한 줄만 바꾸면 전환 완료 (나머지 코드 불변)

**다른 에셋도 동일 패턴**
- tool 등도 `mode` 분기로 목업/실제를 나눈다. 목업 데이터는 `mocks/<에셋>_*.json`.

---


## 4. tool 에셋  (목업 완료 / 실제 연동 TODO)

**목표:** 질문에 맞는 도구(API)를 호출해 `ctx["tools_result"]` 에 넣는다.

**현재 상태 — 목업 동작 중**
- `ENABLED_ASSETS = ["prompt", "rag", "tool", "llm"]` 로 켜져 있음
- `ASSET_CONN["tool"] = {"mode": "mock"}`
- 목업 데이터: `agent/mocks/tool_apis.json` (가상 API 8종)
  - weather / datetime / calculator / gpu_status / model_registry / mlflow_experiment / dataset / training_job
- 선택 방식: `trigger_keywords` 매칭 → **매칭된 도구 전부 호출**
- 등록 시 json 을 Artifact("tool_mock")로 패키징

**목업 / 실제 분리 (tool.py)**
```
build()  -> mode "mock" -> _build_mock    (json 로드)
            mode "real" -> _build_real    ← TODO
run()    -> mode "mock" -> _run_mock      (키워드 매칭 + 다중 호출)
            mode "real" -> _run_real      ← TODO
```

**실제 연동 시 할 일 — TODO**
- `_build_real()` : 실제 API 클라이언트 + function schema 구성
- `_run_real()`   : **LLM function calling** 으로 도구 선택 → 실제 호출 → 결과 join
  - 목업은 키워드 매칭이지만, 실제는 LLM 이 도구를 고르도록 전환
- `ASSET_CONN["tool"]` 를 `{"mode":"real", endpoint_url, api_key}` 로 교체

**LangChain Tool 전환 (실제 연동 시 함께 검토)**
- 도구를 LangChain `@tool` / `bind_tools` 로 정의 → LLM 이 function calling 으로 선택·호출
- 장점: 도구 호출이 autolog 트레이스에 **자동 기록**, LLM 이 유연하게 도구 선택, 실제 연동 구조와 일치
- 주의(지금 바로 안 가는 이유):
  - LLM 호출이 1회 더 생김 (도구 선택 + 답변) → 응답 지연/비용 증가
  - 도구마다 명확한 함수 시그니처(입력/타입/설명) 필요 → 목업 `mock_response` 구조 변환 필요
  - 모델의 function calling 지원 여부 확인 필요 (Qwen 등)
  - 목업/실제 분리(`mode`)가 복잡해질 수 있음
- → **실제 도구 연동 단계에서** LangChain Tool 로 구현. 목업 단계에선 키워드 매칭 유지.
  (rag 도 마찬가지로 실제 연동 시 LangChain Retriever 로 전환 검토)

---


## 5. 프롬프트 태그 필터 (선택)

**목표:** 지금 `search_prompts()` 는 전역 목록을 다 가져온다. 에이전트/유저별로 거른다.

**구현 포인트**
- 프롬프트 등록 시 태그 부여 (예: `agent: aiu`, `user: ...`)
- `search_prompts()` 에서 태그로 필터링
- 빌더에서 "내 프롬프트만" 보여줄 때 필요

---


## 6. 빌더 연동 (장기·보류)

**목표:** 포탈 빌더에서 사용자가 모델/프롬프트/에셋을 골라 에이전트를 배포한다.

**구현 포인트**
- `ENABLED_ASSETS` 가 곧 빌더 화면의 체크박스
- LLM 모델 / 프롬프트 / judge 모델 → **AI Studio DB 로 외부화** (코드/Artifact 고정 → DB 동적 조회)
- 로그인 → user_id 확보 → 호출 시 전달 → user 기준 설정/권한 조회
- 시크릿(api_key 등) 평문 저장 금지 (암호화 / Vault)
- MLflow session_id ↔ 포탈 로그인 세션 연결

> 소스/폴더 레벨의 에셋 추가가 안정화된 뒤 착수.
