"""
==============================================================================
 AI-Studio  |  GenAI Agent Client
==============================================================================

 [목적]
   model_agent.py 로 등록 + 서빙된 MLflow 엔드포인트에
   API 로 질문을 보내고 대화한다.
   각 대화는 session_id 로 묶여 MLflow Sessions 탭에 기록된다.

 [실행]
   python agent_client.py

 [전제]
   MLflow 서빙이 완료된 상태
   예) mlflow models serve -m "models:/genai_agent/1" --port 5001

 [멀티턴]
   클라이언트가 history 를 직접 누적하고 매 호출마다 JSON 문자열로 전달.
   API 서버는 stateless 이므로 history 는 클라이언트 책임.
==============================================================================
"""

import json
import uuid
import urllib.request
import urllib.error


# =============================================================================
# [0]  API 엔드포인트 설정  ← TODO 를 실제 값으로 채운다
# =============================================================================
API_URL = TODO   # 예: http://localhost:5001/invocations
                 # 또는 AI-Studio 서빙 엔드포인트 URL


# =============================================================================
# [1]  API 호출
# =============================================================================
def call_api(question: str, history: list, session_id: str, user_id: str = "client-user") -> str:
    """
    KServe 서빙 엔드포인트에 POST 요청을 보내고 답변을 반환한다.

    스웨거 입력 형식:  { "input": ["<문자열>"] }
    → 문자열 하나만 보낼 수 있으므로,
      question / session_id / user_id / history 를 JSON 으로 직렬화해
      문자열 하나에 담아서 전달한다.

    입력 스키마:
      { "input": ["{\"question\":\"...\",\"session_id\":\"...\",\"history\":[...]}"] }

    출력:
      서버 응답 원본 (가공 없이 그대로 반환)
    """
    # question + 메타 정보를 JSON 문자열 하나로 직렬화
    inner = json.dumps({
        "question":   question,
        "session_id": session_id,
        "user_id":    user_id,
        "history":    history,
    }, ensure_ascii=False)

    payload = json.dumps({
        "input": [inner]
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            # 응답을 가공하지 않고 온 모양 그대로 반환
            return raw

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"API 오류 {e.code}: {body}")

    except urllib.error.URLError as e:
        raise RuntimeError(f"연결 실패: {e.reason}\n  → API_URL 을 확인하세요: {API_URL}")


# =============================================================================
# [2]  대화 루프
# =============================================================================
def chat_loop():
    """
    터미널에서 대화.
    history 를 클라이언트에서 누적 → 매 호출마다 전달 → 멀티턴 유지.
    같은 session_id 로 묶여 MLflow Sessions 탭에 기록됨.
    """
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

    history = []   # [{"role": "user", "content": "..."}, {"role": "assistant", ...}]
    turn    = 0

    while True:
        try:
            question = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if question.lower() in ("exit", "quit", ""):
            break

        try:
            answer = call_api(question, history, session_id)
        except RuntimeError as e:
            print(f"[오류] {e}\n")
            continue

        print(f"[응답 원본]\n{answer}\n")

        # 다음 턴을 위해 history 누적 (raw 응답 그대로)
        history.append({"role": "user",      "content": question})
        history.append({"role": "assistant",  "content": answer})
        turn += 1

    print(f"  대화 종료 — {turn} turn  (session: {session_id})")
    print(f"  MLflow Sessions 탭에서 '{session_id}' 로 확인 가능")
    print()


# =============================================================================
# [3]  실행
# =============================================================================
def safe_main():
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
