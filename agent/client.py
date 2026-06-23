"""
==============================================================================
 AI-Studio | GenAI Agent Client (client.py)
==============================================================================
 서빙된 모델 엔드포인트에 질문을 보내 대화하는 검증용 프로그램.

 [작동 순서]
   1. python client.py -> safe_main() -> chat_loop()
   2. 시작 시 서버에서 프롬프트 목록을 받아 사용자가 하나 고른다 (mode=list_prompts)
   3. 대화 session_id 1개 생성
   4. 질문 입력 -> 고른 prompt_id 와 함께 POST -> 답변 출력
   5. exit/quit/빈 줄 이면 종료

 [A 원칙] system_message 는 client 가 보내지 않는다. 프롬프트는 서버가 로드한다.
          client 는 어떤 프롬프트를 쓸지 prompt_id(이름)만 고른다.

 [전송 형식 - custom_server.py 계약]
   목록 조회 : { "input":[{ "mode":"list_prompts", "llm_api_key":... }] }
   대화      : { "input":[{ query, prompt_id, llm_api_key, session_id, user_id }] }
 [응답 형식]  { ... "output": { "aiu_output": ... } }  중 aiu_output 추출
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


# =============================================================================
# [1] API 호출
# =============================================================================

def _post(payload_obj: dict):
    """공통 POST. 응답에서 aiu_output 을 꺼내 반환한다."""
    payload = json.dumps({"input": [payload_obj]}).encode("utf-8")
    req = urllib.request.Request(API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return _extract_output(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"API 오류 {e.code} {e.reason}\n---- 응답 본문 ----\n{_try_pretty(body)}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"연결 실패: {e.reason}\n  -> API_URL 을 확인하세요: {API_URL}")


def fetch_prompts() -> list:
    """서버에서 등록된 프롬프트 이름 목록을 받아온다."""
    out = _post({"mode": "list_prompts", "llm_api_key": LLM_API_KEY})
    if isinstance(out, dict) and "prompts" in out:
        return out["prompts"]
    return []


def ask(query: str, prompt_id: str, session_id: str, user_id: str = "client-user") -> str:
    """질문 1건을 고른 prompt_id 와 함께 보낸다. (system_message 는 보내지 않음)"""
    return _post({
        "query":       query,
        "prompt_id":   prompt_id,
        "llm_api_key": LLM_API_KEY,
        "session_id":  session_id,
        "user_id":     user_id,
    })


def _try_pretty(text: str) -> str:
    """HTTP 오류 본문이 JSON 이면 들여쓰기해서 반환한다."""
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        return text


def _extract_output(raw: str):
    """서버 응답에서 aiu_output 을 꺼낸다. output 중첩/predictions 등에 대응."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw

    if isinstance(data, dict) and "predictions" in data:
        data = data["predictions"]
    if isinstance(data, dict) and "output" in data and isinstance(data["output"], dict):
        data = data["output"]

    if isinstance(data, dict):
        return data.get("aiu_output", data)
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first.get("aiu_output", first)
        return first
    return data


# =============================================================================
# [2] 프롬프트 선택
# =============================================================================

def choose_prompt() -> str:
    """시작 시 프롬프트 목록을 보여주고 하나 고르게 한다. (못 고르면 빈 값=서버 폴백)"""
    try:
        prompts = fetch_prompts()
    except RuntimeError as e:
        print(f"[목록 조회 실패] {e}\n  -> 기본 프롬프트로 진행합니다.\n")
        return ""

    if not prompts:
        print("등록된 프롬프트가 없습니다. 기본 프롬프트로 진행합니다.\n")
        return ""

    print("\n사용할 프롬프트를 고르세요: (MLflow > GenAI > Prompts 에 등록하실 수 있습니다.)")
    for i, name in enumerate(prompts, 1):
        print(f"  [{i}] {name}")
    print("  [0] 기본 프롬프트 사용")

    while True:
        sel = input("번호 선택> ").strip()
        if sel == "0" or sel == "":
            return ""
        if sel.isdigit() and 1 <= int(sel) <= len(prompts):
            return prompts[int(sel) - 1]
        print("  올바른 번호를 입력하세요.")


# =============================================================================
# [3] 대화 루프
# =============================================================================

def chat_loop():
    """프롬프트 선택 -> 질문/답변 반복. 멀티턴은 session_id 로 묶인다."""
    prompt_id = choose_prompt()
    session_id = "sess-" + uuid.uuid4().hex[:8]

    print("\n🐋 Agent Client")
    print("=" * 60)
    print(f"  API      : {API_URL}")
    print(f"  Session  : {session_id}")
    print(f"  Prompt   : {prompt_id or '(기본)'}")
    print(f"  종료     : exit / quit / 빈 줄")
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
            answer = ask(query, prompt_id, session_id)
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
# [4] 실행 진입점
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
