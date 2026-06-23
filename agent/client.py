"""
==============================================================================
 AI-Studio | GenAI Agent Client (client.py)
==============================================================================
 서빙된 모델 엔드포인트에 질문을 보내 대화하는 검증용 프로그램.
 같은 session_id 로 보내면 MLflow Sessions 탭에 한 대화로 묶인다.

 [작동 순서]
   1. python client.py -> safe_main() -> chat_loop()
   2. 대화 시작 시 session_id 1개 생성 (대화 전체를 묶는 키)
   3. 질문 입력 -> call_api() 로 POST -> 답변 출력
   4. exit/quit/빈 줄 이면 종료

 [전송 형식 - custom_server.py 계약]
   { "input":[{ query, system_message, llm_api_key, session_id, user_id }] }
 [응답 형식]  { ... "output": { "aiu_output": "답변" } }  중 aiu_output 추출
==============================================================================
"""

import json
import uuid
import urllib.request
import urllib.error


# =============================================================================
# [0] 설정 (TODO 를 실제 값으로 채운다)
# =============================================================================
# 서빙 엔드포인트
API_URL = TODO
# LLM 인증 키 (비어있으면 서버가 에러 반환)
LLM_API_KEY = TODO
# 시스템 프롬프트
SYSTEM_MESSAGE = "당신은 친절한 Agent 입니다."


# =============================================================================
# [1] API 호출
# =============================================================================

def call_api(query: str, session_id: str, user_id: str = "client-user") -> str:
    """질문 1건을 custom_server 계약 형식으로 POST 하고 답변 문자열을 반환한다."""
    payload = json.dumps({
        "input": [{
            "query":          query,
            "system_message": SYSTEM_MESSAGE,
            "llm_api_key":    LLM_API_KEY,
            "session_id":     session_id,
            "user_id":        user_id,
        }]
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            return _extract_answer(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"API 오류 {e.code} {e.reason}\n---- 응답 본문 ----\n{_try_pretty(body)}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"연결 실패: {e.reason}\n  -> API_URL 을 확인하세요: {API_URL}")


def _try_pretty(text: str) -> str:
    """HTTP 오류 본문이 JSON 이면 들여쓰기해서 반환한다."""
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        return text


def _extract_answer(raw: str) -> str:
    """서버 응답에서 aiu_output(답변)만 꺼낸다. output 중첩/predictions 등에 대응."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    if isinstance(data, dict) and "predictions" in data:
        data = data["predictions"]
    # custom_server 응답: {..., "output": {"aiu_output": ...}}
    if isinstance(data, dict) and "output" in data and isinstance(data["output"], dict):
        data = data["output"]

    if isinstance(data, dict):
        return str(data.get("aiu_output", json.dumps(data, ensure_ascii=False)))
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return str(first.get("aiu_output", json.dumps(first, ensure_ascii=False)))
        return str(first)
    return str(data)


# =============================================================================
# [2] 대화 루프
# =============================================================================

def chat_loop():
    """질문을 받아 call_api() 로 보내고 답변을 출력한다(멀티턴은 session_id 로 묶임)."""
    session_id = "sess-" + uuid.uuid4().hex[:8]

    print("\n🐋 Agent Client")
    print("=" * 60)
    print(f"  API             : {API_URL}")
    print(f"  Session         : {session_id}")
    print(f"  시스템 프롬프트 : {SYSTEM_MESSAGE}")
    print(f"  종료            : exit / quit / 빈 줄")
    print("=" * 60 + "\n")

    turn = 0
    while True:
        try:
            query = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if query.lower() in ("exit", "quit", ""):
            break

        try:
            answer = call_api(query, session_id)
        except RuntimeError as e:
            print(f"[HTTP 오류]\n{e}\n")
            continue

        if isinstance(answer, str) and answer.startswith("[AGENT ERROR]"):
            print(f"[서버 내부 오류]\n{answer}\n")
            continue

        print(f"답변> {answer}\n")
        turn += 1

    print(f"  대화 종료 - {turn} turn  (session: {session_id})")
    print(f"  MLflow Sessions 탭에서 '{session_id}' 로 확인 가능\n")


# =============================================================================
# [3] 실행 진입점
# =============================================================================

def safe_main():
    """API_URL 입력 여부 확인 후 대화 루프를 시작한다."""
    if not API_URL or str(API_URL) == "TODO":
        print("[오류] API_URL 이 입력되지 않았습니다.")
        return
    try:
        chat_loop()
    except Exception as e:
        print(f"[오류] {e}")
        raise


if __name__ == "__main__":
    safe_main()
