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
import time
import sys
import threading
import urllib.request
import urllib.error

import builtins as _builtins

# stdout/stderr 를 surrogate 가 와도 죽지 않는 모드로 재구성 (가능한 환경에서)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass


def _safe_print(*args, **kwargs):
    """surrogate(이모지 등)가 어디서 섞여 들어와도 출력이 죽지 않게 정화 후 print."""
    def clean(a):
        s = a if isinstance(a, str) else str(a)
        return s.encode("utf-8", "replace").decode("utf-8", "replace")
    safe_args = [clean(a) for a in args]
    _builtins.print(*safe_args, **kwargs)


# 이 모듈 안의 모든 print 호출을 안전 버전으로 대체
print = _safe_print


# =============================================================================
# [0] 설정 (TODO 를 실제 값으로 채운다)
# =============================================================================
# 서빙 엔드포인트
API_URL = TODO
# LLM 인증 키 (비어있으면 서버가 에러 반환)
LLM_API_KEY = TODO
# 응답 대기 최대 시간(초). 긴 답변 대비 넉넉히.
REQUEST_TIMEOUT = 180


# =============================================================================
# [1] API 호출
# =============================================================================

def _post(payload_obj: dict):
    """공통 POST. 응답에서 aiu_output 을 꺼내 반환한다."""
    # 보낼 데이터에 surrogate(키/URL 복붙 시 섞일 수 있음)가 있어도 인코딩이 죽지 않게 정화
    body_text = json.dumps({"input": [payload_obj]}, ensure_ascii=False)
    payload = body_text.encode("utf-8", "replace")
    req = urllib.request.Request(API_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            # 1) 바이트 디코딩  2) 살아남은 surrogate 까지 완전 제거 후 처리
            raw = resp.read().decode("utf-8", "replace")
            raw = raw.encode("utf-8", "replace").decode("utf-8", "replace")
            return _extract_output(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"API 오류 {e.code} {e.reason}\n---- 응답 본문 ----\n{_try_pretty(body)}")
    except urllib.error.URLError as e:
        # 타임아웃도 URLError 로 들어온다
        reason = getattr(e, "reason", e)
        raise RuntimeError(f"연결 실패/타임아웃: {reason}\n  -> API_URL/타임아웃 확인: {API_URL} ({REQUEST_TIMEOUT}s)")


def fetch_prompts() -> list:
    """서버에서 등록된 프롬프트 목록을 받아온다.
    반환: [{"name": str, "versions": int}] 또는 ["이름", ...] (구버전 호환)
    """
    out = _post({"mode": "list_prompts", "llm_api_key": LLM_API_KEY})
    if isinstance(out, dict) and "prompts" in out:
        return out["prompts"]
    return []


def fetch_versions(prompt_id: str) -> list:
    """특정 프롬프트의 버전 번호 목록을 서버에서 받아온다. (예: [1, 2, 3])"""
    out = _post({"mode": "list_versions", "prompt_id": prompt_id, "llm_api_key": LLM_API_KEY})
    if isinstance(out, dict) and "versions" in out:
        return out["versions"]
    return []


def ask(query: str, prompt_id: str, session_id: str, prompt_version=None, user_id: str = "client-user") -> str:
    """질문 1건을 고른 prompt_id(+version) 와 함께 보낸다. (system_message 는 보내지 않음)"""
    payload = {
        "query":       query,
        "prompt_id":   prompt_id,
        "llm_api_key": LLM_API_KEY,
        "session_id":  session_id,
        "user_id":     user_id,
    }
    if prompt_version is not None:
        payload["prompt_version"] = prompt_version
    return _post(payload)


def _try_pretty(text: str) -> str:
    """HTTP 오류 본문이 JSON 이면 들여쓰기해서 반환한다."""
    try:
        return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError):
        return text


def _safe_str(v) -> str:
    """surrogate(이모지 등에서 발생)가 섞여 있어도 출력/인코딩에서 죽지 않게 정화한다."""
    s = v if isinstance(v, str) else str(v)
    return s.encode("utf-8", "replace").decode("utf-8", "replace")


def _extract_output(raw: str):
    """서버 응답에서 aiu_output 을 꺼낸다. output 중첩/predictions 등에 대응."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _safe_str(raw)

    if isinstance(data, dict) and "predictions" in data:
        data = data["predictions"]
    if isinstance(data, dict) and "output" in data and isinstance(data["output"], dict):
        data = data["output"]

    if isinstance(data, dict):
        val = data.get("aiu_output", data)
        # aiu_output 이 dict(예: 프롬프트 목록 {"prompts": [...]})면 그대로,
        # 문자열(답변)이면 surrogate 정화
        return _safe_str(val) if isinstance(val, str) else val
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            val = first.get("aiu_output", first)
            return _safe_str(val) if isinstance(val, str) else val
        return _safe_str(first) if isinstance(first, str) else first
    return _safe_str(data) if isinstance(data, str) else data


# =============================================================================
# [2] 프롬프트 선택
# =============================================================================

def _prompt_name(p):
    """목록 항목에서 이름을 꺼낸다. dict({name,versions}) / 문자열 둘 다 대응."""
    return p["name"] if isinstance(p, dict) else p


def _prompt_vcount(p):
    """목록 항목에서 버전 개수를 꺼낸다. 없으면 None."""
    return p.get("versions") if isinstance(p, dict) else None


def choose_prompt():
    """시작 시 프롬프트 목록을 보여주고 하나 고르게 한다. 그다음 버전을 고르게 한다.
    반환: (prompt_id, prompt_version)
      - 프롬프트 미선택(기본) → ("", None)
      - 버전 미선택(최신)      → (이름, None)
      - 버전 선택              → (이름, 버전번호)
    """
    try:
        prompts = fetch_prompts()
    except RuntimeError as e:
        print(f"[목록 조회 실패] {e}\n  -> 기본 프롬프트로 진행합니다.\n")
        return "", None

    if not prompts:
        print("등록된 프롬프트가 없습니다. 기본 프롬프트로 진행합니다.\n")
        return "", None

    # --- 1단계: 프롬프트 선택 ---
    print("\n사용할 프롬프트를 고르세요: (MLflow > GenAI > Prompts 에 등록하실 수 있습니다.)")
    for i, p in enumerate(prompts, 1):
        name = _prompt_name(p)
        vc = _prompt_vcount(p)
        label = f"{name}  [버전 {vc}개]" if vc else name
        print(f"  [{i}] {label}")
    print("  [0] 기본 프롬프트 사용")

    chosen = None
    while True:
        sel = input("프롬프트 번호 선택> ").strip()
        if sel == "0" or sel == "":
            return "", None
        if sel.isdigit() and 1 <= int(sel) <= len(prompts):
            chosen = prompts[int(sel) - 1]
            break
        print("  올바른 번호를 입력하세요.")

    name = _prompt_name(chosen)

    # --- 2단계: 버전 선택 ---
    try:
        versions = fetch_versions(name)
    except RuntimeError as e:
        print(f"[버전 조회 실패] {e}\n  -> 최신 버전으로 진행합니다.\n")
        return name, None

    if not versions:
        print(f"  '{name}' 의 버전 목록을 가져오지 못했습니다. 최신 버전으로 진행합니다.\n")
        return name, None

    print(f"\n'{name}' 의 버전을 고르세요:")
    for v in versions:
        print(f"  [{v}] 버전 {v}")
    print("  [0] 최신 버전 사용")

    while True:
        sel = input("버전 번호 선택> ").strip()
        if sel == "0" or sel == "":
            return name, None
        if sel.isdigit() and int(sel) in versions:
            return name, int(sel)
        print("  올바른 버전 번호를 입력하세요.")


# =============================================================================
# [3] 대화 루프
# =============================================================================

def _ask_with_spinner(query: str, prompt_id: str, session_id: str, prompt_version=None):
    """답변을 기다리는 동안 '🐋 답변 생성 중... (Ns)' 를 실시간 표시한다."""
    result = {}
    def worker():
        try:
            result["answer"] = ask(query, prompt_id, session_id, prompt_version)
        except Exception as e:      # noqa: BLE001 - 스레드 예외를 메인으로 전달
            result["error"] = e

    t = threading.Thread(target=worker, daemon=True)
    start = time.time()
    t.start()
    # 0.2초 간격으로 경과 시간 갱신
    while t.is_alive():
        sec = int(time.time() - start)
        print(f"\r🐋 답변 생성 중... ({sec}s)", end="", flush=True)
        t.join(timeout=0.2)
    # 스피너 줄 지우기
    print("\r" + " " * 40 + "\r", end="", flush=True)

    if "error" in result:
        raise result["error"]
    return result.get("answer", "")


def chat_loop():
    """프롬프트 선택 -> 버전 선택 -> 질문/답변 반복. 멀티턴은 session_id 로 묶인다."""
    prompt_id, prompt_version = choose_prompt()
    session_id = "sess-" + uuid.uuid4().hex[:8]

    print("\n🐋 Agent Client")
    print("=" * 60)
    print(f"  API      : {API_URL}")
    print(f"  Session  : {session_id}")
    if prompt_id:
        print(f"  Prompt   : {prompt_id}  " + (f"v{prompt_version}" if prompt_version else "(최신)"))
    else:
        print(f"  Prompt   : (기본)")
    print(f"  종료     : exit / quit / 빈 줄")
    print("=" * 60 + "\n")

    while True:
        try:
            query = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if query.lower() in ("exit", "quit", ""):
            break

        try:
            answer = _ask_with_spinner(query, prompt_id, session_id, prompt_version)
        except RuntimeError as e:
            print(f"[HTTP 오류]\n{e}\n")
            continue
        except Exception as e:      # noqa: BLE001
            print(f"[알 수 없는 오류] {type(e).__name__}: {e}\n")
            continue

        # 빈 응답이면 조용히 넘기지 말고 표시
        if answer is None or (isinstance(answer, str) and answer.strip() == ""):
            print("[경고] 응답이 비어 있습니다. (서버 로그/세션을 확인하세요)\n")
            continue

        if isinstance(answer, str) and answer.startswith("[AGENT ERROR]"):
            print(f"[서버 내부 오류]\n{answer}\n")
            continue

        # 출력 직전 최종 방어: surrogate 가 남아 있어도 print 가 죽지 않게 정화
        answer = _safe_str(answer)
        print(f"답변> {answer}\n")

    print(f"  대화 종료  (session: {session_id})")
    print(f"  MLflow Sessions 탭에서 '{session_id}' 로 확인 가능")
    print("  세션 평가는 judge_eval.py 스크립트로 별도 실행\n")


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
