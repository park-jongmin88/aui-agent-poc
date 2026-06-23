# GenAI Agent 확장 로드맵 (TODO)

현재는 **LLM 단계만** 구현되어 있다. (LangChain + MLflow autolog)
아래는 앞으로 붙일 에셋과, 각 단계를 `agent.py` 어디에 끼워넣는지 정리한 것이다.

---

## 현재 상태

| 단계 | 상태 | 비고 |
|------|------|------|
| LLM | ✅ 완료 | LangChain `ChatOpenAI` + autolog |
| Trace / Session | ✅ 완료 | `update_current_trace()` 로 세션 묶음 |
| 에러 처리 규격 | ✅ 완료 | `{"aiu_output": "[AGENT ERROR]..."}` |
| RAG | ⬜ 예정 | Milvus 등 vector DB |
| Tool | ⬜ 예정 | 외부 API / 함수 호출 |
| Prompt 관리 | ⬜ 예정 | 버전 관리된 시스템 프롬프트 |
| Judge | ⬜ 예정 | 응답 품질 평가 |
| 헬스체크 | ⬜ 예정 | 에셋 정상 작동 점검 |
| 빌더 연동 | ⬜ 보류 | 연결정보 DB 외부화 + 사용자 인증 |

---

## 확장 시 공통 패턴

새 에셋을 붙일 때 항상 아래 3곳을 함께 수정한다.

1. **연결정보 상수 추가** — 파일 상단에 `RAG_CONN = TODO` 형태
2. **Artifact 저장** — `register_agent()` 에서 json 으로 저장 → `artifacts` dict 에 키 추가
3. **로드** — `load_context()` 에서 `self.rag_conn = json.load(...)`

---

## 1. RAG (검색 증강)

**목표:** 질문과 관련된 문서를 vector DB 에서 검색해 프롬프트에 주입한다.

- 연결정보: `RAG_CONN = {vector_db, host, port, collection, top_k}`
- `_get_chain()` 프롬프트에 context 슬롯 추가:
  ```python
  ("system", "참고자료:\n{context}"),
  ```
- `_run()` 에서 검색 후 invoke 입력에 포함:
  ```python
  context = rag_search(query, self.rag_conn)   # RETRIEVER span
  self.chain.invoke({"query": query, "system_message": ..., "context": context})
  ```

---

## 2. Tool (외부 호출)

**목표:** 계산기, 검색, 사내 API 등 외부 기능을 호출한다.

- 연결정보: `TOOL_CONN = {endpoint_url, api_key}`
- LangChain `bind_tools` 또는 Agent 구조로 전환
- `_run()` 에 Tool 호출 단계 삽입 (TOOL span)

---

## 3. Prompt 관리

**목표:** 시스템 프롬프트를 코드 밖에서 버전 관리한다.

- 연결정보: `PROMPT_CONF = {name, version, system}`
- MLflow Prompt Registry 활용 검토
- 현재는 client 가 `system_message` 로 직접 전달 → 추후 서버 관리로 이전

---

## 4. Judge (품질 평가)

**목표:** 생성된 응답을 별도 LLM 으로 평가/스코어링한다.

- 응답 생성 후 Judge 체인으로 평가 → Trace 에 점수 기록
- 샘플폴더 `registry/judge.py` 참고

---

## 5. 헬스체크

**목표:** 파이프라인 각 에셋(LLM/RAG/Tool)이 정상인지 점검한다.

- KServe 는 커스텀 엔드포인트 추가 불가 → `predict()` 안에서 모드 분기로 처리
- 입력에 모드 플래그 추가:
  ```python
  if info.get("mode") == "healthcheck":
      return {"aiu_output": self._healthcheck()}  # 각 에셋 ping
  ```

---

## 6. 빌더 연동 (보류)

**목표:** 포탈 빌더에서 사용자가 LLM/에셋을 선택·배포한다.

- LLM 연결정보를 **AI Studio DB 로 외부화** (코드/Artifact 고정 → DB 동적 조회)
- 포탈 **로그인 → user_id 확보 → 에이전트 호출 시 전달**
- user_id 기준으로 DB 에서 해당 사용자의 LLM 설정/권한 조회
- `api_key` 등 시크릿은 평문 저장 금지 (암호화 / Vault)
- MLflow `session_id` 와 포탈 로그인 세션 연결 → 대화 히스토리 추적

> 이 항목은 현재 명시적으로 **보류**. LLM 통신 + 로그/트레이스/세션 안정화 후 착수.
