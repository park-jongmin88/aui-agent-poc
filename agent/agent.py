"""
==============================================================================
 AI-Studio  |  GenAI Agent  (agent.py)
==============================================================================

 [이 파일이 하는 일]
   LLM 기반 GenAI Agent 를 MLflow pyfunc 모델로 "등록" 한다.
   등록된 모델을 KServe 로 서빙하면, API 호출 때마다
   MLflow 에 Trace(호출 기록) 와 Session(대화 묶음) 이 남는다.

   이 파일을 실행하면 "등록만" 한다. 대화는 하지 않는다.
   대화는 서빙 후 client.py 가 엔드포인트를 호출해서 한다.

 [실행]
   python agent.py
     → MLflow 에 모델 등록 (run_id / model_uri 출력)

 [서빙]
   mlflow models serve -m "models://<registered_model>/1" --port 5001

 ----------------------------------------------------------------------------
 [읽는 순서 — 위에서 아래로]
   [0] 연결 정보 상수   MLFLOW_CONN / LLM_CONN      ← 사용자가 채우는 설정
   [1] 유틸 함수        _is_set / _clean_text / _agent_error
   [2] LLM 호출         call_llm()                  ← Qwen 호출 (LLM span)
   [3] 모델 본체        ModelWrapper                ← 서빙되는 클래스
                         ├ load_context()           Artifact 로드
                         ├ _run()                   파이프라인 (Trace/Session)
                         └ predict()                서빙 진입점
   [4] 등록             register_agent()            ← MLflow 에 올리기
   [5] 실행             safe_main()                 ← python agent.py 진입점
 ----------------------------------------------------------------------------

 [중요 설계 원칙]
   1. 서빙 환경에는 이 파이썬 파일이 없다.
      → 연결 정보(LLM_CONN 등)는 JSON 파일로 저장해 Artifact 로 등록하고,
        load_context() 에서 다시 읽어 self 에 담아 쓴다.
   2. signature(입력 스키마)는 주지 않는다.
      → 스키마를 강제하면 포탈이 자동으로 붙이는 필드(logger, aiu_ver,
        trace_id 등)와 충돌해 "enforce schema" 에러가 난다.
        input_example 만 등록한다.
   3. 에러는 서버를 죽이지 않고 응답에 담는다. (_agent_error 규격)
==============================================================================
"""

import os
import json
import uuid
import mlflow
import mlflow.pyfunc
from mlflow.entities import SpanType   # Trace span 종류 (AGENT / LLM / RETRIEVER ...)


# =============================================================================
# [0-A]  MLflow 연결 정보
# -----------------------------------------------------------------------------
#   MLflow 서버 접속과 등록 대상(Experiment / 모델명)을 정의한다.
#   TODO 자리를 실제 값으로 채운다. (따옴표 없는 TODO = 미입력 상태)
# =============================================================================
MLFLOW_CONN = {
    "tracking_uri":     TODO,   # MLflow 서버 주소.  예: http://mlflow.internal:5000
    "username":         TODO,   # MLflow 접속 ID
    "password":         TODO,   # MLflow 접속 PW
    "experiment_name":  TODO,   # 기록을 모을 Experiment 이름
    "registered_model": TODO,   # 모델 레지스트리 등록명 (서빙 시 이 이름 사용)
}


# =============================================================================
# [0-B]  LLM 연결 정보
# -----------------------------------------------------------------------------
#   사내 Qwen(OpenAI 호환 API) 접속 정보.
#   이 값은 등록 시 llm_conn.json 으로 저장되어 Artifact 로 함께 올라간다.
#   (서빙 환경에서 load_context() 가 다시 읽는다)
# =============================================================================
LLM_CONN = {
    "base_url":    TODO,   # LLM 엔드포인트.  예: http://qwen.internal:8000/v1
    "api_key":     TODO,   # 인증 키 (필요 없으면 TODO 그대로 둬도 됨)
    "model":       TODO,   # 모델명.  예: qwen2.5-7b-instruct
    "temperature": 0.2,    # 0 에 가까울수록 일관된 답변, 1 에 가까울수록 다양함
}

# ── 에셋 추가 시 연결 정보 형태 참고 (지금은 미사용) ─────────────────────────
#   RAG / Tool / Prompt 를 붙일 때 아래 형태로 상수를 추가하고,
#   register_agent() 에서 json 파일로 저장 → artifacts 에 등록,
#   load_context() 에서 로드하는 순서로 동일하게 처리한다.
# RAG_CONN = {
#     "vector_db":  TODO,   # 예: milvus / opensearch
#     "host":       TODO,
#     "port":       TODO,
#     "collection": TODO,
#     "top_k":      3,
# }
# TOOL_CONN = {
#     "endpoint_url": TODO,
#     "api_key":      TODO,
# }
# PROMPT_CONF = {
#     "name":    TODO,
#     "version": TODO,
#     "system":  TODO,      # System Prompt 내용
# }


# =============================================================================
# [1]  유틸 함수
# -----------------------------------------------------------------------------
#   여러 곳에서 공통으로 쓰는 작은 도우미 함수들.
# =============================================================================

def _is_set(value) -> bool:
    """
    값이 '실제로 채워졌는지' 판단한다.

    TODO 미입력 상태나 빈 문자열이면 False.
    설정값을 쓰기 전에 이 함수로 입력 여부를 확인한다.
    """
    return isinstance(value, str) and bool(value) and value != "{TODO}"


def _clean_text(s: str) -> str:
    """
    LLM 응답에서 깨진 surrogate 문자를 제거한다.

    Qwen 응답이 바이트 경계에서 잘리면 surrogate 문자가 섞일 수 있는데,
    이대로 MLflow Trace 에 저장하면 utf-8 인코딩 에러가 난다.
    encode/decode 를 한 번 거쳐 깨진 문자를 떨어내고 안전한 문자열로 만든다.
    """
    if not isinstance(s, str):
        return s
    return s.encode("utf-8", "surrogatepass").decode("utf-8", "ignore")


def _agent_error(stage: str, exc: Exception, question: str, session_id: str) -> str:
    """
    [에이전트 에러 처리 공식 규격]

    서빙 환경에서 client 는 보통 HTTP 500 본문 일부만 받기 때문에,
    서버 안에서 무슨 오류가 났는지 알기 어렵다.
    그래서 예외가 나면 traceback 전체를 '[AGENT ERROR]' 로 시작하는
    문자열로 만들어 '답변 자리' 에 담아 반환한다. (서버는 죽지 않는다)

    client 는 답변이 '[AGENT ERROR]' 로 시작하면 오류로 판별한다.

    [확장 시] RAG / Tool / Prompt / Judge 단계도 이 함수를 그대로 재사용한다.
              stage 인자에 단계명을 넣으면 어느 단계에서 터졌는지 바로 보인다.
        예) _agent_error("RAG",  e, q, sid)
            _agent_error("TOOL", e, q, sid)
            _agent_error("LLM",  e, q, sid)

    Args:
        stage      : 실패한 단계명 (PREDICT / RAG / TOOL / LLM ...)
        exc        : 발생한 예외 객체
        question   : 처리 중이던 질문
        session_id : 대화 세션 ID
    Returns:
        '[AGENT ERROR]' 로 시작하는 진단 문자열
    """
    import traceback
    tb = traceback.format_exc()
    return (
        "[AGENT ERROR]\n"
        f"stage  : {stage}\n"
        f"type   : {type(exc).__name__}\n"
        f"message: {exc}\n"
        f"question: {question}\n"
        f"session : {session_id}\n"
        "---- traceback ----\n"
        f"{tb}"
    )


# =============================================================================
# [2]  LLM 호출
# -----------------------------------------------------------------------------
#   메시지 배열을 받아 Qwen 에 보내고 답변 텍스트를 받아온다.
#   @mlflow.trace 로 감싸 'LLM' 타입 span 이 Trace 에 기록된다.
# =============================================================================

@mlflow.trace(name="llm_call", span_type=SpanType.LLM)
def call_llm(messages: list, llm_conn: dict) -> str:
    """
    사내 Qwen(OpenAI 호환 API)을 호출해 답변을 반환한다.

    openai 패키지가 있으면 그걸 쓰고, 없으면 urllib 로 직접 POST 한다.
    (서빙 이미지에 openai 가 없을 수도 있어 폴백 경로를 둔다)

    Args:
        messages : OpenAI chat 형식 [{"role": "user", "content": "..."}]
        llm_conn : LLM 연결 정보 (base_url / api_key / model / temperature)
    Returns:
        LLM 답변 텍스트 (surrogate 정리된 안전한 문자열)
    """
    # api_key 가 비어있으면 더미값으로 (인증 없는 내부 엔드포인트 대응)
    api_key = llm_conn["api_key"] if _is_set(llm_conn.get("api_key", "")) else "not-needed"

    try:
        # ── 경로 1: openai 패키지 사용
        from openai import OpenAI
        client = OpenAI(base_url=llm_conn["base_url"], api_key=api_key)
        resp = client.chat.completions.create(
            model=llm_conn["model"],
            messages=messages,
            temperature=llm_conn.get("temperature", 0.2),
        )
        return _clean_text(resp.choices[0].message.content)

    except ImportError:
        # ── 경로 2: openai 가 없으면 urllib 로 직접 호출
        import urllib.request
        url = llm_conn["base_url"].rstrip("/") + "/chat/completions"
        payload = json.dumps({
            "model":       llm_conn["model"],
            "messages":    messages,
            "temperature": llm_conn.get("temperature", 0.2),
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        if _is_set(llm_conn.get("api_key", "")):
            req.add_header("Authorization", f"Bearer {llm_conn['api_key']}")
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return _clean_text(data["choices"][0]["message"]["content"])


# =============================================================================
# [3]  ModelWrapper  —  MLflow pyfunc 모델 본체
# -----------------------------------------------------------------------------
#   실제로 MLflow 에 등록되고 서빙되는 클래스.
#   mlflow.pyfunc.PythonModel 을 상속하고 predict() 를 구현해야
#   KServe 가 호출할 수 있다.
#
#   메소드 호출 순서:
#     load_context()  (서빙 시작 시 1회)  →  predict()  (요청마다)  →  _run()
# =============================================================================

class ModelWrapper(mlflow.pyfunc.PythonModel):
    """
    서빙되는 모델 래퍼.

    핵심: 서빙 환경에는 이 .py 파일 바깥의 값(LLM_CONN 등)이 없다.
          그래서 연결 정보는 Artifact(json)로 등록하고
          load_context() 에서 읽어 self 에 담아 쓴다.
    """

    def load_context(self, context):
        """
        [서빙 시작 시 MLflow 가 1회 자동 호출]

        등록 때 함께 올린 Artifact(json)를 읽어 self 에 보관한다.
        이후 _run() / call_llm() 이 self.llm_conn 을 참조한다.

        Args:
            context : MLflow 가 주입. context.artifacts 에 등록된 파일 경로가 들어있다.
        """
        # LLM 연결 정보 로드 (등록 때 저장한 llm_conn.json)
        with open(context.artifacts["llm_conn"], "r", encoding="utf-8") as f:
            self.llm_conn = json.load(f)

        # ── 에셋 추가 시 여기에 로드 추가 ───────────────────────────────
        # with open(context.artifacts["rag_conn"], "r") as f:
        #     self.rag_conn = json.load(f)
        # with open(context.artifacts["tool_conn"], "r") as f:
        #     self.tool_conn = json.load(f)
        # with open(context.artifacts["prompt_conf"], "r") as f:
        #     self.prompt_conf = json.load(f)

    @mlflow.trace(name="agent_pipeline", span_type=SpanType.AGENT)
    def _run(self, question: str, history: list = None,
             session_id: str = None, user_id: str = None) -> dict:
        """
        [파이프라인 본체 — 질문 1건 처리]

        @mlflow.trace(AGENT) 로 감싸 'agent_pipeline' span 이 만들어지고,
        그 안에서 호출되는 call_llm() 의 LLM span 이 자식으로 붙는다.
        같은 session_id 의 호출들은 MLflow Sessions 탭에 하나로 묶인다.

        처리 순서:
          1) Trace 에 session/user 정보 기록
          2) history + 이번 질문으로 messages 구성
          3) call_llm() 으로 답변 생성
          4) 결과 dict 반환

        Args:
            question   : 사용자 질문
            history    : 이전 대화 [{"role":..., "content":...}, ...]
            session_id : 대화 세션 ID (같으면 한 대화로 묶임)
            user_id    : 사용자 ID
        Returns:
            {"question":..., "answer":..., "session_id":...}
        """
        # ── 1) Trace 에 session / user 기록 (전용 인자 방식) ─────────────
        #    session_id= / user= 전용 인자를 써야 GenAI Sessions/Traces 화면에
        #    안정적으로 묶인다. (metadata 에 키로 욱여넣는 방식은 불안정)
        try:
            mlflow.update_current_trace(
                user=user_id or "aiu-user",
                session_id=session_id or "aiu-session",
                tags={
                    "user_id":    user_id or "aiu-user",
                    "session_id": session_id or "aiu-session",
                },
                metadata={
                    "app_type": "genai",
                },
            )
        except TypeError:
            # 구버전 MLflow 호환: 전용 인자 미지원 시 metadata 로 폴백
            meta = {}
            if session_id:
                meta["mlflow.trace.session"] = session_id
            if user_id:
                meta["mlflow.trace.user"] = user_id
            try:
                mlflow.update_current_trace(metadata=meta)
            except Exception:
                pass
        except Exception:
            pass

        # ── 2) 메시지 구성 (이전 대화 history + 이번 질문) ────────────────
        messages = list(history) if history else []

        # ── 에셋 추가 시 여기에 단계 삽입 ──────────────────────────────
        #   순서: System Prompt → RAG 검색결과 → Tool 결과 → 질문
        # if self.prompt_conf.get("system"):
        #     messages.insert(0, {"role": "system", "content": self.prompt_conf["system"]})
        # context_text = rag_search(question, self.rag_conn)   # RETRIEVER span
        # tool_result  = call_tool(question, self.tool_conn)   # TOOL span

        messages.append({"role": "user", "content": question})

        # ── 3) LLM 호출 ────────────────────────────────────────────────
        answer = call_llm(messages, self.llm_conn)

        # ── 4) 결과 반환 ───────────────────────────────────────────────
        return {
            "question":   question,
            "answer":     answer,
            "session_id": session_id,
        }

    def predict(self, context, model_input, params=None):
        """
        [서빙 진입점 — KServe 가 호출하는 메소드]

        외부 요청은 무조건 이 predict() 로 들어온다. (MLflow pyfunc 규약)
        입력 형태가 환경마다 달라서(DataFrame / list / dict / str) 모두 받아
        DataFrame 으로 정규화한 뒤, 행마다 _run() 을 돌려 답변을 모은다.

        입력에서 사용하는 컬럼:
          - question   (필수) : 질문
          - session_id (선택) : 없으면 자동 생성
          - user_id    (선택)
          - history    (선택) : JSON 문자열 또는 list

        Returns:
            ["답변 문자열", ...]   ← 답변만 리스트로 반환
            (dict/DataFrame 으로 반환하면 서빙 직렬화에서 깨질 수 있어 문자열로 통일)
        """
        import pandas as pd

        # ── (a) 입력을 DataFrame 으로 정규화 ───────────────────────────
        if isinstance(model_input, pd.DataFrame):
            df = model_input
        elif isinstance(model_input, dict):
            df = pd.DataFrame(model_input)
        elif isinstance(model_input, list):
            # dict 리스트면 그대로, 문자열 리스트면 question 컬럼으로
            if model_input and isinstance(model_input[0], dict):
                df = pd.DataFrame(model_input)
            else:
                df = pd.DataFrame({"question": [str(x) for x in model_input]})
        else:
            df = pd.DataFrame({"question": [str(model_input)]})

        # question 컬럼이 없으면 첫 컬럼을 질문으로 간주
        if "question" not in df.columns and len(df.columns) > 0:
            df = df.rename(columns={df.columns[0]: "question"})

        # ── (b) params 기본값 (행에 값이 없을 때 사용) ─────────────────
        params    = params or {}
        p_session = params.get("session_id")
        p_user    = params.get("user_id")

        # ── (c) 컬럼별로 값 추출 (없는 컬럼은 None 리스트로 채움) ────────
        questions = df["question"].fillna("").astype(str).tolist()
        sessions  = df["session_id"].tolist() if "session_id" in df.columns else [None] * len(questions)
        users     = df["user_id"].tolist()    if "user_id"    in df.columns else [None] * len(questions)
        historys  = df["history"].tolist()    if "history"    in df.columns else [None] * len(questions)

        # ── (d) 행마다 _run() 실행 ─────────────────────────────────────
        results = []
        for q, sid, uid, raw_hist in zip(questions, sessions, users, historys):
            # session_id 없으면 자동 생성
            sid = sid or p_session or "sess-" + uuid.uuid4().hex[:8]
            uid = uid or p_user

            # history: JSON 문자열이면 파싱, list 면 그대로, 그 외엔 빈 리스트
            if isinstance(raw_hist, str):
                try:
                    history = json.loads(raw_hist)
                except (json.JSONDecodeError, TypeError):
                    history = []
            elif isinstance(raw_hist, list):
                history = raw_hist
            else:
                history = []

            # 서버 내부 오류는 죽지 않고 응답에 담는다 (에러 처리 공식 규격)
            try:
                out = self._run(q, history=history, session_id=sid, user_id=uid)
                results.append(out["answer"])
            except Exception as e:
                results.append(_agent_error("PREDICT", e, q, sid))

        # ── (e) Trace 를 UI 에 즉시 반영 (서빙 환경 유실 방지) ──────────
        flush = getattr(mlflow, "flush_trace_async_logging", None)
        if callable(flush):
            try:
                flush(terminate=False)
            except Exception:
                pass

        return results


# =============================================================================
# [4]  MLflow 등록
# -----------------------------------------------------------------------------
#   ModelWrapper 와 연결 정보(Artifact)를 MLflow 에 올린다.
#   python agent.py 실행 시 이 함수가 호출된다.
# =============================================================================

def register_agent():
    """
    ModelWrapper 를 MLflow 에 등록한다.

    순서:
      1) MLflow 접속 설정 (tracking_uri / 인증 / experiment)
      2) LLM_CONN 을 llm_conn.json 으로 저장 (Artifact 재료)
      3) Run 시작 → 파라미터/태그 기록
      4) input_example 준비 (signature 는 일부러 안 줌)
      5) log_model() 로 모델+Artifact 등록
      6) (선택) 모델 레지스트리에 등록
    """
    # ── 1) MLflow 접속 ─────────────────────────────────────────────────
    if not _is_set(MLFLOW_CONN["tracking_uri"]):
        raise ValueError("MLFLOW_CONN.tracking_uri 가 입력되지 않았습니다.")

    if _is_set(MLFLOW_CONN["username"]):
        os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_CONN["username"]
    if _is_set(MLFLOW_CONN["password"]):
        os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_CONN["password"]

    mlflow.set_tracking_uri(MLFLOW_CONN["tracking_uri"])
    mlflow.set_experiment(MLFLOW_CONN["experiment_name"])

    # ── 2) 연결 정보를 Artifact 파일로 저장 ────────────────────────────
    #    서빙 환경에서 load_context() 가 이 파일을 읽는다.
    llm_conn_file = "llm_conn.json"
    with open(llm_conn_file, "w", encoding="utf-8") as f:
        json.dump(LLM_CONN, f, ensure_ascii=False, indent=2)

    # ── 에셋 추가 시 Artifact 파일도 같이 저장 ─────────────────────────
    # rag_conn_file  = "rag_conn.json"
    # tool_conn_file = "tool_conn.json"
    # with open(rag_conn_file, "w")  as f: json.dump(RAG_CONN,  f)
    # with open(tool_conn_file, "w") as f: json.dump(TOOL_CONN, f)

    print("=" * 60)
    print(" MLflow Agent 등록 시작")
    print("=" * 60)

    # ── 3) Run 시작 ────────────────────────────────────────────────────
    with mlflow.start_run(run_name="agent-register") as run:

        # 어떤 설정으로 등록했는지 파라미터/태그로 남긴다
        mlflow.log_params({
            "llm_model":   LLM_CONN["model"],
            "temperature": LLM_CONN["temperature"],
        })
        mlflow.set_tags({
            "app_type": "genai",
            "stage":    "register",
        })

        # ── 4) 입력 예시 (signature 는 주지 않음) ──────────────────────
        #   signature 로 스키마를 강제하면 포탈이 자동으로 붙이는 필드
        #   (logger, aiu_ver, trace_id ...)와 충돌해 enforce schema 에러가 난다.
        #   input_example 만 주면 포탈이 무엇을 보내든 통과한다.
        import pandas as pd
        input_example = pd.DataFrame({
            "question":   ["안녕하세요"],
            "session_id": ["sess-example"],
            "user_id":    ["user-001"],
            "history":    ["[]"],
        })

        # ── 5) Artifact 묶음 (에셋 추가 시 여기에 키 추가) ─────────────
        artifacts = {
            "llm_conn": llm_conn_file,
            # "rag_conn":    rag_conn_file,
            # "tool_conn":   tool_conn_file,
            # "prompt_conf": prompt_conf_file,
        }

        log_kwargs = dict(
            python_model     = ModelWrapper(),
            artifacts        = artifacts,
            input_example    = input_example,
            # pip 버전 고정 필수: 포탈 백엔드가 'mlflow==' 패턴으로 버전을 파싱한다.
            # 버전이 없으면 extractVersion 이 null 을 반환해 등록이 실패한다.
            pip_requirements = ["mlflow==3.10.0", "openai==2.43.0", "kserve==0.15.0"],
        )

        # MLflow 버전별 인자명 차이 대응 (name= vs artifact_path=)
        try:
            model_info = mlflow.pyfunc.log_model(name="genai_agent", **log_kwargs)
        except TypeError:
            model_info = mlflow.pyfunc.log_model(artifact_path="genai_agent", **log_kwargs)

        print(f"  run_id    : {run.info.run_id}")
        print(f"  model_uri : {model_info.model_uri}")

        # ── 6) 모델 레지스트리 등록 (registered_model 채웠을 때만) ──────
        if _is_set(MLFLOW_CONN["registered_model"]):
            mv = mlflow.register_model(model_info.model_uri, MLFLOW_CONN["registered_model"])
            print(f"  registry  : {MLFLOW_CONN['registered_model']}  v{mv.version}")

    print()
    print("  등록 완료.")
    print(f"  MLflow UI : {MLFLOW_CONN['tracking_uri']}")
    print()
    print("  서빙 명령어:")
    print(f"  mlflow models serve -m 'models://{MLFLOW_CONN['registered_model']}/1' --port 5001")
    print("=" * 60)


# =============================================================================
# [5]  실행 진입점
# -----------------------------------------------------------------------------
#   python agent.py 로 실행하면 safe_main() → register_agent() 가 돈다.
# =============================================================================

def safe_main():
    """register_agent() 를 감싸 오류를 보기 좋게 출력한다."""
    try:
        register_agent()
    except ValueError as e:
        # 설정 미입력 등 사용자가 바로 고칠 수 있는 오류
        print(f"[오류] {e}")
    except Exception as e:
        # 그 외 예외는 메시지 출력 후 다시 raise (스택 확인용)
        print(f"[오류] 등록 중 예외 발생: {e}")
        raise


if __name__ == "__main__":
    safe_main()
