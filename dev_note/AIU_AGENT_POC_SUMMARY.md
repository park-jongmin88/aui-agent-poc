# AI-Studio GenAI Agent POC — 최종 정리

> MLflow pyfunc 모델로 등록되어 KServe로 서빙되는 LangChain 기반 GenAI 에이전트.
> 이 문서는 프로젝트의 아키텍처, 설계 결정, 구현 상태를 정리한 것이다.
> 저장소: `park-jongmin88/aui-agent-poc` · 주 작업 브랜치: `gen-ai-agent`

---


## 1. 개요

에이전트는 **에셋(asset) 모듈을 조립**해 동작한다. `agent.py`는 "무엇을 켤지" 선언하고 "순서대로 실행"만 하며, 실제 기능은 각 에셋(`assets/*.py`)에 들어있다.

핵심 실행 흐름은 다음과 같다.

1. **대화 시작** — client가 MLflow에서 프롬프트 목록을 받아 하나 고른다. (프롬프트 텍스트의 주인은 서버, client는 id만 선택 = "A원칙")
2. **질문 진입** — 질문 한 건이 서빙 진입점(`aiu_custom.predict.ModelWrapper`)으로 들어온다.
3. **보따리(ctx) 파이프라인** — `prompt → rag → tool → llm` 순서로 각 에셋이 ctx의 자기 칸만 채우며 통과한다.
4. **반환** — `{"aiu_output": "답변"}` 형태로 반환. Trace/Session 자동 기록.
5. **평가(judge)** — 서빙과 분리된 별도 스크립트로 수행한다. 등록은 `judge_register.py`(평가지+gateway LLM 선택, 자동 트래킹 on/off), 평가는 `evaluate.py`(등록된 judge 로 trace 채점). MLflow 정석 방식(`make_judge`).


## 2. 폴더 구조

```
config.py            설정 (ENABLED_ASSETS, MLFLOW_CONN, LLM_*, ASSET_CONN)
agent.py             등록 전용 (register_agent)
client.py            서빙 엔드포인트 호출 테스트용 대화 프로그램
judge_register.py    judge 등록 (평가지+gateway LLM 선택, 자동 트래킹 on/off)
evaluate.py          평가 실행 (등록된 judge 로 trace 채점)
requirements.txt     서빙 의존성 (버전 고정)
agent_flow.png       동작 흐름 연필스케치 다이어그램
aiu_custom/          서빙되는 모델 본체
  ├── __init__.py
  ├── model_wrapper.py   ModelWrapper (load_context / predict / 파이프라인)
  └── predict.py         re-export (서빙 진입점)
assets/              에셋 모듈 모음 (기능 추가는 여기)
  ├── __init__.py        에셋 공통 규약 + ctx 생성/로더
  ├── prompt.py          [구현] MLflow Prompts 로드 (캐싱)
  ├── llm.py             [구현] LangChain 체인으로 답변 생성
  ├── rag.py             [구현] Milvus 연결 (iflow_aiu_collection, 1024, L2/IVF_FLAT) + 임베딩 bge-m3(분리 서버). mode=milvus 기본
  └── tool.py            [목업] mocks/ 가상 API 호출 (실제 연동 TODO)
mocks/               목업 데이터 (실제 연결 전 POC용)
  ├── rag_documents.json   딥러닝/ML/GenAI 문서 20건
  └── tool_apis.json       가상 API 8종
```


## 3. 핵심 설계 결정

### 3-1. 진입점 고정, 내용물 교체

서빙 컨테이너(`custom_server.py`)는 항상 같은 경로 `aiu_custom.predict.ModelWrapper`에서 모델을 찾는다. `predict.py`는 단 한 줄의 re-export(`from .model_wrapper import ModelWrapper`)다.

- **진입점(`predict.py`)은 고정** — 실제 코드가 바뀌어도 서빙이 찾는 자리는 변하지 않는다.
- **내용물(config / assets / mocks)은 교체** — 빌더는 config만 동적 생성하면 되고, ModelWrapper 코드는 여러 에이전트가 하나로 공유한다.

```
custom_server.py
   └─ aiu_custom.predict.ModelWrapper   ← 고정된 진입점
        └─ model_wrapper.py             ← 실제 로직 (바뀌어도 됨)
             ├─ config.py               ← 설정 (빌더가 교체)
             ├─ assets/                 ← 기능 (켜고 끔)
             └─ mocks/                  ← 데이터
```

### 3-2. config 분리로 순환 import 방지

설정을 `config.py`로 빼서 등록(`agent.py`)과 서빙(`aiu_custom`)이 같은 값을 참조한다. 순환 import가 없고, 양쪽이 일관된 설정을 본다.

### 3-3. 보따리(ctx) 방식 파이프라인

`ENABLED_ASSETS = ["prompt", "rag", "tool", "llm"]` (리스트 순서 = 실행 순서).

ctx는 에셋들이 순서대로 주고받는 "보따리"다.

```
ctx = { query, prompt_id, prompt_version, system_message, context, tools_result, answer, score }
```

각 에셋은 자기 칸만 채우고 다음 에셋에게 넘긴다. 검색(rag)·도구(tool)는 우리가 직접 채우고, LLM은 채워진 보조자료(prompt + context + tools)를 받아 답변만 작성한다.

에셋 공통 규약: 각 에셋은 `NAME`, `build(conn)`, `run(ctx, resource)`를 가진다.


## 4. custom_server.py 계약 (고정, 수정 불가)

- **입력**: `model_input["input"][0]` = `{query, system_message, session_id, prompt_id, prompt_version, user_id, mode}`, 그리고 `trace_id` 등. (LLM 인증은 gateway 가 처리하므로 llm_api_key 없음)
- **출력**: 반드시 `{"aiu_output": ...}` 키를 포함해야 한다. 없으면 custom_server 측에서 `UnboundLocalError: log_data` 연쇄 오류가 난다 (서버 측 코드라 수정 불가).
- 정상 응답 형태: `{...,"output":{"aiu_output":"답변"}}`.
- 에러는 서버를 죽이지 않고 `{"aiu_output":"[AGENT ERROR]..."}`로 반환한다.

### mode 분기 (predict 진입점)

- `mode="list_prompts"` — 대화 시작 전 프롬프트 목록 조회 (이름 + 버전 개수).
- `mode="list_versions"` — 특정 프롬프트의 버전 번호 목록 조회 (프롬프트 선택 후 버전 고르기).
- 그 외 — 일반 대화 파이프라인 실행.
- (KServe는 커스텀 엔드포인트 추가 불가 → predict 안에서 mode로 분기)

### 등록 규칙

- signature 금지 → `input_example`만 사용.
- pip 버전 고정 필수 (포탈이 `mlflow==` 패턴을 파싱함).
- `code_paths = ["aiu_custom", "config.py", "assets", "mocks"]` — 서빙 환경에서 import 가능하도록 패키지/설정 동봉.
- requirements (requirements.txt 파일 한 곳에서 관리): mlflow, cloudpickle, langchain, langchain-openai, openai==2.26.0, pandas, kserve, pymilvus==2.4.9, setuptools==75.8.0, marshmallow==3.26.2.
  - 의존성은 agent.py 에 박지 않고 `pip_requirements=requirements.txt`(파일 참조)로 일원화 — 이중 관리 제거.
  - RAG 의존성 주의: pymilvus → environs → marshmallow. marshmallow 4.x 는 `__version_info__` 제거로 깨짐 → **3.26.2 고정**. pymilvus 는 pkg_resources 필요 → **setuptools 포함**. (Python 3.12 슬림 이미지에서 필수)
- 권장 Python: **3.11.9** (kserve 0.15.0 호환; 3.13은 kserve 설치 안 됨).
- **코드 변경 시 재등록·재서빙 필수** — config(모델명 등)·model_wrapper·assets는 모두 서버 코드라 로컬만 고치면 반영되지 않는다. (client.py는 로컬 실행이라 재서빙 불필요)


## 5. 각 에셋 상세

### prompt (구현됨)
MLflow Prompt Registry에서 `prompt_id`로 텍스트를 로드한다.
- **A원칙**: 프롬프트 텍스트의 주인은 서버, client는 id만 선택. client가 보낸 system_message는 무시.
- **캐싱**: 같은 prompt_id는 첫 호출만 `load_prompt`, 이후 메모리 재사용 (응답 지연 해결의 핵심).
- 로드 실패 시 `default_system` 폴백.
- 프롬프트 타입은 **text** (chat 아님).
- **버전 선택**: 별칭(@production) 의존을 제거하고 버전 번호로 로드한다. client 가 `prompt_id` + `prompt_version` 을 보내면 `load_prompt(name, version=N)` 으로, 버전 생략 시 최신을 로드한다. "프롬프트 선택 → 버전 선택" 2단계. OSS MLflow 는 `search_prompt_versions`(Databricks 전용)가 없어 버전 목록을 load_prompt 순차탐색으로 조회한다. (→ PROMPT_VERSION.md)
- 미선택/로드 실패 시 default_system 으로 폴백.

### llm (구현됨, Gateway 방식)
LangChain 체인으로 답변 생성: `prompt | model | StrOutputParser()` (LCEL).
- **MLflow AI Gateway 로 호출** — LLM 접속정보(주소·키)는 client/config 에 두지 않는다. gateway 가 갖고 있다.
  - `base_url`: `{MLFLOW_TRACKING_URI}/gateway/mlflow/v1` (OpenAI 호환 엔드포인트)
  - `model`: gateway 에 등록된 엔드포인트 이름 (agent.py 등록 시 선택)
  - 인증: `default_headers` 에 `Authorization: Basic base64(MLFLOW_USERNAME:MLFLOW_PASSWORD)` — judge 등록(judge_register.py)과 동일한 방식으로 **MLflow 계정을 재사용**한다. `api_key` 필드는 "dummy" (gateway 가 무시).
- **등록 시 필수 선택** — `agent.py` 실행 시 `assets/gateway_utils.py` 로 gateway 의 chat 엔드포인트 목록을 조회해 화면에서 고른다. 목록이 없거나 조회가 실패하면 **등록 자체가 중단**된다 (config.py 에 주소를 직접 적는 옛 방식은 이 브랜치에서 완전히 제거함 — 폴백 없음).
- 선택한 엔드포인트 정보는 `conn.json`(Artifact)에 저장되고, 서빙 시작 시(`load_context`) 그 파일을 읽어 `ChatOpenAI` 를 구성한다. `conn.json` 이 없거나 llm 정보가 비면 서빙 시작이 명확한 에러로 실패한다 (조용히 넘어가지 않음).
- **client 는 더 이상 `llm_api_key` 를 보내지 않는다.** 서버(agent)가 이미 gateway 인증정보를 갖고 있기 때문. (→ `assets/gateway_utils.py` 는 `mlflow_inspect.py`(단독 조회 스크립트)와도 같은 로직을 공유한다.)
- **system 메시지 단일화**: context/tools_result를 하나의 system 메시지로 합친다. (system을 여러 개 보내면 Qwen 등 일부 모델이 400 BadRequest 반환)
- surrogate 정화(`_safe_text`) 포함.
- **리소스 빌드 시점 변경**: 예전엔 client 가 매번 다른 api_key 를 보낼 수 있어 요청마다 리소스를 재생성했지만, gateway 방식은 인증정보가 서버에 고정이므로 **서빙 시작 시 1회만 빌드**한다.

### rag (구현: Milvus + bge-m3)
질문 키워드로 문서를 검색해 `ctx["context"]`를 채운다.
- 기본 mode=mock: `mocks/rag_documents.json` (딥러닝/ML/GenAI 20건) 키워드 매칭.
- 실제 Milvus: `iflow_aiu_collection`(default DB), 필드 text/vector(1024), 인덱스 IVF_FLAT/L2/nprobe=16. 임베딩은 bge-m3 — 문서 적재 때 쓴 임베딩 서버(LLM 과 분리된 서브도메인 embedding.llm.도메인.com/v1)를 OpenAI 호환 API 로 호출. 환경변수 MILVUS_URI/USER/PASSWORD + EMBED_BASE_URL/EMBED_API_KEY 주입. 조회 동작 확인됨.
- `_build_mock`/`_search_mock` vs `_build_milvus`/`_search_milvus` 함수 분리. `_make_embedder` 는 openai 호환 API(`/v1/embeddings`, bge-m3) 호출 — torch 불필요, 적재 인프라와 벡터 일치.

### tool (목업)
질문에 맞는 도구(API)를 호출해 `ctx["tools_result"]`를 채운다.
- 목업: `mocks/tool_apis.json` (가상 API 8종: weather/datetime/calculator/gpu_status/model_registry/mlflow_experiment/dataset/training_job).
- `trigger_keywords` 매칭 → 매칭된 도구 전부 호출.
- `_run_mock` vs `_run_real`(TODO, LLM function calling) 분리.


## 6. 트레이스 / 세션 기록

LangChain `mlflow.langchain.autolog()` + 각 에셋 run의 `@mlflow.trace`로 보따리 흐름을 가시화한다.

```
agent_pipeline                  ← _run() (@mlflow.trace)
  └ asset.prompt   [CHAIN]
  └ asset.rag      [RETRIEVER]
  └ asset.tool     [TOOL]
  └ asset.llm      [CHAIN]      (+autolog RunnableSequence 중첩)
```

- LangChain autolog는 **LangChain 컴포넌트만** 자동 기록한다. rag/tool 목업은 순수 파이썬이라 수동 `@mlflow.trace`가 필요하다.
- **Session**: Sessions 탭은 metadata 표준키(`mlflow.trace.session`/`mlflow.trace.user`)를 읽는다 (mlflow 3.10). `update_current_trace`로 기록.


## 6-1. trace 보안 (민감정보 마스킹)

trace 에 api_key 등 민감정보가 남지 않도록 두 겹으로 방어한다.

1. **traced 인자 분리** — `_run` 은 api_key 를 받아 리소스만 준비하고, 실제 trace 가 붙는
   `_run_traced` 에는 api_key 를 넘기지 않는다. (`@mlflow.trace` 는 함수 인자를 자동 기록하므로,
   인자에서 빼면 span 에 안 남는다.)
2. **span_processor 마스킹** — 서빙 시작 시 마스킹 필터를 등록해, 모든 span 의 input/output 에서
   `api_key/llm_api_key/password/token/secret/authorization` 류 키의 값을 `[REDACTED]` 로 가린다.
   (`mlflow.tracing.configure(span_processors=[...])`. 구버전에 없으면 1번만으로도 핵심 노출은 차단.)

## 7. judge 평가 (MLflow 정석 make_judge, 등록/평가 분리)

평가는 서빙과 완전히 분리된 스크립트로 수행한다. **등록**과 **평가 실행**을 두 파일로 나눴다.
목적은 평가 결과를 **MLflow > GenAI > Judges**(및 Traces)에 남기는 것이다.

### 왜 정석 방식인가
- 직접 LLM을 호출해 점수를 반환하는 자체 구현(셀프judge)은 MLflow의 Judges 메뉴와 연동되지 않아 GenAI > Judges에 나타나지 않는다.
- `make_judge` + `register` + `mlflow.genai.evaluate`를 써야 Judges 탭에 등록되고, trace에 평가(Feedback)가 부착된다.
- 이에 따라 셀프judge(assets/judge.py 등)는 제거하고 정석 방식으로 전환했다.

### 등록 (judge_register.py)
실행하면 3단계를 숫자로 선택한다.
- **[1/3] 평가지 선택** — `mocks/judge_templates.json`(목업)에서 고른다. 5종: 정확성/유용성/안전성/간결성/종합품질. 나중에 프롬프트/DB로 소스만 바꿔도 "목록→선택" 흐름은 재사용된다.
- **[2/3] 평가용 LLM 선택** — MLflow AI Gateway 엔드포인트 목록에서 고른다(필수). `gateway:/<이름>` 형식으로 judge 에 박힌다. (agent.py 와 같은 `assets/gateway_utils.py` 재사용)
- **[3/3] 자동 트래킹 on/off** — 켜면 `sample_rate`(0.1~1.0)를 선택하고 `judge.register().start(ScorerSamplingConfig(sample_rate=...))` 로 새 trace 를 자동 채점한다(1시간 내 trace 대상). 끄면 등록만 하고 평가는 evaluate.py 로 수동 실행한다.

```python
from mlflow.genai.judges import make_judge
from mlflow.genai.scorers import ScorerSamplingConfig

judge = make_judge(
    name=tmpl["name"],
    instructions=tmpl["instructions"],   # {{ trace }} 변수 사용 (아래 규칙)
    model="gateway:/<엔드포인트명>",
    feedback_value_type=int,             # 1~5 정수
)
registered = judge.register(experiment_id=...)                 # Judges 탭 등록
registered.start(sampling_config=ScorerSamplingConfig(0.5))    # (선택) 자동 트래킹
```

### 평가 실행 (evaluate.py)
등록된 judge 를 목록에서 골라 최근 trace 를 채점한다. LLM 은 judge 가 등록 시 이미 갖고 있으므로 여기서 다시 고르지 않는다.
```python
judge = mlflow.genai.list_scorers(experiment_id=...)[선택]
mlflow.genai.evaluate(data=traces, scorers=[judge])   # trace 평가 → Feedback 부착
```

### 핵심 규칙
- **템플릿 변수**: 우리 trace 는 `agent_pipeline` span 안에 질문/답변이 들어 있어 root 에서 inputs/outputs 자동 추출이 안 될 수 있다. 그래서 평가지는 **`{{ trace }}`** 변수를 쓴다(judge 가 trace 전체를 탐색). `{{ trace }}` 는 `{{ inputs }}/{{ outputs }}` 와 함께 못 쓴다. 리터럴 중괄호는 `{{ }}` 로 이스케이프.
- **모델 지정**: `gateway:/<엔드포인트명>` (등록 시 gateway 목록에서 선택).
- **gateway 인증**: gateway 가 MLflow 서버 위에 있어 호출 시 MLflow Basic 인증(아이디:비번)을 요구한다. litellm.completion 을 래핑해 `Authorization: Basic` 헤더를 주입한다. (→ JUDGE_GATEWAY_AUTH.md)
- **자동 트래킹**: LLM judge 만 지원. `Scorer.start()/stop()/update()`, `ScorerSamplingConfig(sample_rate, filter_string)`. 켜진 뒤 1시간 내 trace 가 대상.
- **서빙과 분리**: judge 는 쌓인 trace 를 평가하므로 서빙과 타이밍 무관. AI Gateway 는 judge 실행 시에만 필요.
- **버전 요구**: `make_judge` >= 3.4.0. 자동 트래킹 API 는 현재 환경(3.13)에서 사용.

### 사용
```bash
python judge_register.py   # 평가지+LLM 선택, 자동 트래킹 설정, judge 등록
python evaluate.py         # 등록된 judge 로 최근 trace 평가
```


## 8. 프롬프트 ↔ 실험 관계 (참고)

MLflow는 프롬프트를 실험에 태그로 묶을 수 있다.
- `load_prompt`/`register_prompt`가 활성 run 안에서 호출되면 `PROMPT_EXPERIMENT_IDS_TAG_KEY` 태그로 실험에 연결된다.
- 저장은 전역, UI 표시만 실험별로 갈린다.
- `mlflow.genai.search_prompts()` (필터 없음)은 전역 전체를 가져온다 (현재 사용 중).
- 실험별 필터: `search_prompts(filter_string="experiment_id = '...'")`.
- UI URL: `<mlflow>/#/prompts` (전역, 실험 무관 전체 목록), `<mlflow>/#/experiments/<id>/prompts` (실험별).
- 50개 초과 시 페이지네이션 필요.


## 9. LangChain 활용 현황과 방향

**현재**: `assets/llm.py`만 LangChain(ChatOpenAI 체인) 사용 + autolog. 즉 Models + Prompts + Chains(LCEL) 기본 3요소만.

**방향 (실제 연동 단계에서 전환)**:
- rag → LangChain **Retriever** (Milvus 연동 시)
- tool → LangChain **Tool / bind_tools** (function calling — LLM이 도구 스스로 선택)

**필요성**: autolog가 검색·도구 호출까지 자동 트레이싱, 표준 인터페이스로 교체·조합 용이, 실제 연동 구조와 일치.

**지금 바로 안 가는 이유**: LLM 2회 호출로 느려짐(도구 선택 + 답변), 함수 시그니처 변환 필요, Qwen function calling 호환 확인 필요, mock/real 분리가 복잡해짐.


## 10. 트러블슈팅 (해결됨)

### 응답 지연 (504 / 14초)
- 원인: prompt 에셋이 매 질문마다 `load_prompt`로 MLflow 왕복.
- 해결: **프롬프트 캐싱** (2번째 질문부터 건너뜀).
- 재서빙 직후 첫 요청 504 + "activator request timeout"은 **KServe 콜드 스타트**(scale-to-zero에서 파드 깨우는 중). 첫 요청만 실패하고 다음부터 정상이면 정상 동작이다.
- **콜드 스타트 완화 워밍업**: `load_context`에서 `list_prompts()`를 미리 1회 호출해 MLflow 첫 연결을 서빙 시작 시점으로 옮긴다.
- 긴 설명형 질문만 504가 나면 LLM 생성 시간이 게이트웨이 타임아웃을 넘는 경우. max_tokens 제한 또는 타임아웃 조정으로 완화 가능. 평상시 속도 편차는 LLM 서버 부하에 따른 것.

### UnicodeEncodeError (surrogate)
- 원인: 응답/요청에 surrogate(깨진 이모지·유니코드, 키/URL 복붙 시 섞임)가 들어가 인코딩이 실패. 답변은 서버에서 정상 생성되어 트레이스엔 남지만 화면 출력/요청 전송에서 터짐.
- 해결: client에 **양방향 + 다층 방어**
  1. **요청 전송 시** `encode("utf-8","replace")` (보내는 쪽 빈틈 보강)
  2. 응답 수신 직후 이중 정화
  3. `_extract_output`에서 문자열만 정화 (dict인 프롬프트 목록은 보존 — 정화로 문자열화하면 목록이 깨져 "기본" 고정되는 버그가 있었음)
  4. `sys.stdout.reconfigure(errors="replace")` + `print`를 `_safe_print`로 전역 교체
- client.py만 수정이라 재서빙 불필요.

### 404 Model not found
- 원인: `config.py`의 `LLM_MODEL` 값이 실제 LLM 서버에 등록된 모델명과 불일치.
- 해결: `/v1/models`로 실제 모델 목록을 확인해 정확한 이름을 넣는다. 수정 후 **재등록·재서빙** 필요.

### 프롬프트 목록 안 나옴 / 405
- 원인: config(모델명) 등 서버 코드를 고치고 **재서빙하지 않아** 서버가 옛 코드로 동작.
- 해결: 최신 브랜치로 재등록·재서빙. (로컬 수정만으로는 서버에 반영되지 않음)

### judge 관련
- 셀프judge 시절 "결과 없음"으로 끝나던 문제: client가 모든 비정상 응답을 뭉개서 원인을 숨긴 것 → 케이스별 노출로 진단. 실제 원인은 judge 프롬프트의 JSON 예시 중괄호가 변수로 오해된 KeyError였고(`{{ }}` 이스케이프 필요), 이후 **셀프judge 자체를 제거하고 정석 make_judge로 전환**했다.


## 11. TODO (개발 예정)

1. **LLM 모델 선택** — `/v1/models`에서 목록 받아 고르기 (mode=list_models, model_id 추가). 모델명 하드코딩으로 인한 404를 방지. 다음 1순위.
2. **rag 실제 연결** — Milvus, LangChain Retriever.
3. **tool 실제 연동** — 실제 API + function calling, LangChain Tool 전환.
4. **프롬프트 태그 필터** — experiment_id 필터로 에이전트/유저별 분리.
5. **judge 고도화** — 평가 기준별 judge 분리, 자동 평가(sampling) 설정, 인간 피드백 정렬(align).
6. **빌더 연동** — config를 포탈 DB로 외부화, user_id 인증, 시크릿 암호화 (장기 보류).

### 미정 (방향만)
- **LLM 관리**: 향후 포탈 DB에서 관리 (현재 config.py 하드코딩).
- **Prompt 관리**: (A) 사용자별/시스템별 포탈 DB or (B) 현재처럼 MLflow Prompts. 미정.
- **빌더**: config.py 동적 생성 방향.
