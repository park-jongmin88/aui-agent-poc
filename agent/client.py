"""
==============================================================================
 AI-Studio  |  GenAI Agent Client  (client.py)
==============================================================================

 [이 파일이 하는 일]
   agent.py 로 등록 + 서빙된 모델 엔드포인트에 질문을 보내고 대화한다.
   이 파일은 "서빙된 모델을 테스트" 하기 위한 임시 대화 프로그램이다.
   (실제 운영에서는 포탈이 엔드포인트를 호출하므로, 여기선 검증용으로만 쓴다)

   대화하면 같은 session_id 로 묶여 MLflow Sessions 탭에 기록된다.
   (Trace/Session 기록은 서버=agent.py 쪽에서 일어난다. client 는 호출만 함)

 [실행]
   python client.py

 [전제]
   모델이 서빙된 상태여야 한다.
   예) mlflow models serve -m "models:/genai_agent/1" --port 5001

 ----------------------------------------------------------------------------
 [읽는 순서 — 위에서 아래로]
   [0] API_URL              ← 호출할 엔드포인트 주소 (사용자가 채움)
   [1] call_api()           질문 1건을 서버로 보내고 답변을 받는다
       ├ _try_pretty()      HTTP 에러 본문을 보기 좋게 정리
       └ _extract_answer()  정상 응답에서 답변 문자열만 추출
   [2] chat_loop()          터미널 대화 루프 (history 누적 = 멀티턴)
   [3] safe_main()          python client.py 진입점
 ----------------------------------------------------------------------------

 [멀티턴 원리]
   서버(서빙)는 stateless 라 이전 대화를 기억하지 못한다.
   그래서 client 가 history 를 직접 누적해서 매 호출마다 함께 보낸다.

 [에러 표시 — agent.py 의 에러 처리 규격과 짝]
   정상 답변            → "답변> ..."
   서버 내부 오류        → 응답이 "[AGENT ERROR]" 로 시작 → "[서버 내부 오류]" 표시
   HTTP 오류(500 등)     → 예외 발생 → "[HTTP 오류]" + 본문 펼침
   (오류는 history 에 쌓지 않아 다음 턴을 오염시키지 않는다)
==============================================================================
"""

import json
import uuid
import urllib.request
import urllib.error


# =============================================================================
# [0]  API 엔드포인트 설정
# -----------------------------------------------------------------------------
#   호출할 서빙 엔드포인트 주소. TODO 를 실제 값으로 채운다.
# =============================================================================
API_URL = TODO   # 예: http://localhost:5001/invocations
                 # 또는 AI-Studio 서빙 엔드포인트 URL
                 #   (KServe 형식이면 .../v1/models/<model>:predict 일 수 있음)


# =============================================================================
# [1]  API 호출
# -----------------------------------------------------------------------------
#   질문 1건을 서버로 보내고, 답변 문자열을 돌려받는다.
# =============================================================================

def call_api(question: str, history: list, session_id: str, user_id: str = "client-user") -> str:
    """
    서빙 엔드포인트에 POST 요청을 보내고 답변을 반환한다.

    보내는 형식 (MLflow pyfunc 서빙, 레코드 지향):
      { "inputs": [{ "question": "...", "session_id": "...",
                     "user_id": "...", "history": "[...]" }] }
      - 서버의 predict() 가 이걸 DataFrame 으로 받아 "question" 컬럼을 쓴다.
      - history 는 list 를 그대로 못 보내므로 JSON 문자열로 직렬화해서 넣는다.

    Args:
        question   : 이번에 보낼 질문
        history    : 이전 대화 [{"role":..., "content":...}, ...]
        session_id : 대화 세션 ID (서버에서 Sessions 묶음 키로 사용)
        user_id    : 사용자 ID
    Returns:
        답변 문자열. (서버 내부 오류면 "[AGENT ERROR]..." 문자열이 올 수 있음)
    Raises:
        RuntimeError : HTTP 오류(500 등) 또는 연결 실패 시
    """
    # 요청 본문 구성 (history 는 JSON 문자열로 직렬화)
    payload = json.dumps({
        "dataframe_records": [{
            "question":   question,
            "session_id": session_id,
            "user_id":    user_id,
            "history":    json.dumps(history, ensure_ascii=False),  # list → JSON 문자열
        }]
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        # ── 정상 응답(200) ─────────────────────────────────────────────
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return _extract_answer(raw)

    except urllib.error.HTTPError as e:
        # ── HTTP 오류(500/400 등): 본문에 서버 스택이 들어있으므로 펼쳐서 보여줌
        body = e.read().decode("utf-8", "ignore")
        pretty = _try_pretty(body)
        raise RuntimeError(
            f"API 오류 {e.code} {e.reason}\n"
            f"---- 응답 본문 ----\n{pretty}"
        )

    except urllib.error.URLError as e:
        # ── 연결 자체 실패 (주소 오타 / 서버 미기동 등)
        raise RuntimeError(f"연결 실패: {e.reason}\n  → API_URL 을 확인하세요: {API_URL}")


def _try_pretty(text: str) -> str:
    """
    HTTP 오류 본문을 보기 좋게 정리한다.
    JSON 이면 들여쓰기해서 반환하고, JSON 이 아니면 원문 그대로 반환한다.
    """
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        return text


def _extract_answer(raw: str) -> str:
    """
    서버 정상 응답(200)에서 답변 문자열만 꺼낸다.

    서빙 환경/버전마다 응답 형태가 달라서 여러 형태를 모두 대응한다:
      {"predictions": ["답변"]}   (MLflow 서빙 표준)
      ["답변"]                    (리스트만)
      "답변"                      (문자열만)
      {"answer": "..."}           (dict)

    Args:
        raw : 서버가 준 응답 본문(문자열)
    Returns:
        답변 문자열 (파싱 실패 시 원문 그대로)
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw  # JSON 이 아니면 원문 그대로

    # {"predictions": [...]} 면 그 안을, 아니면 data 자체를 후보로
    if isinstance(data, dict):
        preds = data.get("predictions", data)
    else:
        preds = data

    # 리스트면 첫 항목 (문자열이면 그대로, dict 면 answer 키)
    if isinstance(preds, list) and preds:
        first = preds[0]
        if isinstance(first, dict):
            return first.get("answer", json.dumps(first, ensure_ascii=False))
        return str(first)
    # dict 면 answer 키
    if isinstance(preds, dict):
        return preds.get("answer", json.dumps(preds, ensure_ascii=False))
    return str(preds)


# =============================================================================
# [2]  대화 루프
# -----------------------------------------------------------------------------
#   터미널에서 질문을 입력받아 call_api() 로 보내고 답변을 출력한다.
#   history 를 누적해 멀티턴 대화를 유지한다.
# =============================================================================

def chat_loop():
    """
    터미널 대화 루프.

    동작:
      1) session_id 를 하나 만든다 (이 대화 전체를 묶는 키)
      2) 질문 입력 → call_api() 호출 → 답변 출력
      3) 정상 답변이면 history 에 누적 (다음 턴에 함께 전달 → 멀티턴)
      4) exit/quit/빈 줄 이면 종료

    오류 처리는 agent.py 의 에러 규격과 짝을 이룬다:
      - HTTP 오류        → "[HTTP 오류]"
      - 서버 내부 오류    → "[서버 내부 오류]" (응답이 [AGENT ERROR] 로 시작)
      - 오류는 history 에 쌓지 않는다
    """
    # 이 대화 전체를 묶는 세션 ID
    session_id = "sess-" + uuid.uuid4().hex[:8]

    print()
    print("=" * 60)
    print(" GenAI Agent Client")
    print("=" * 60)
    print(f"  API     : {API_URL}")
    print(f"  Session : {session_id}")
    print("  종료    : exit / quit / 빈 줄")
    print("=" * 60)
    print()

    history = []   # 누적 대화. [{"role":"user","content":...}, {"role":"assistant",...}]
    turn    = 0    # 정상 처리된 대화 턴 수

    while True:
        # ── 질문 입력 ──────────────────────────────────────────────────
        try:
            question = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if question.lower() in ("exit", "quit", ""):
            break

        # ── 서버 호출 ──────────────────────────────────────────────────
        try:
            answer = call_api(question, history, session_id)
        except RuntimeError as e:
            # HTTP 오류(500 등) — 서버가 에러 응답을 던진 경우
            print(f"[HTTP 오류]\n{e}\n")
            continue

        # ── 서버 내부 오류 (200 이지만 본문이 [AGENT ERROR] 로 시작) ────
        if isinstance(answer, str) and answer.startswith("[AGENT ERROR]"):
            print(f"[서버 내부 오류]\n{answer}\n")
            continue   # 오류는 history 에 쌓지 않는다

        # ── 정상 답변 출력 ─────────────────────────────────────────────
        print(f"답변> {answer}\n")

        # 다음 턴을 위해 history 누적 (정상 답변만)
        history.append({"role": "user",      "content": question})
        history.append({"role": "assistant",  "content": answer})
        turn += 1

    print(f"  대화 종료 — {turn} turn  (session: {session_id})")
    print(f"  MLflow Sessions 탭에서 '{session_id}' 로 확인 가능")
    print()


# =============================================================================
# [3]  실행 진입점
# -----------------------------------------------------------------------------
#   python client.py 로 실행하면 여기서 시작한다.
# =============================================================================

def safe_main():
    """
    API_URL 입력 여부를 확인한 뒤 대화 루프를 시작한다.
    미입력이면 안내만 하고 종료한다.
    """
    if not API_URL or str(API_URL) == "TODO":
        print("[오류] API_URL 이 입력되지 않았습니다.")
        print("  상단 API_URL 에 서빙 엔드포인트 주소를 입력하세요.")
        print("  예) API_URL = 'http://localhost:5001/invocations'")
        return
    try:
        chat_loop()
    except Exception as e:
        print(f"[오류] {e}")
        raise


if __name__ == "__main__":
    safe_main()
