"""
tool 에셋 - 질문에 맞는 도구(API)를 호출해 결과를 ctx["tools_result"] 에 채운다.
LLM 은 이 결과를 참고자료로 받아 답변한다.

[목업 / 실제 분리]
   mode="mock" : POC용. mocks/tool_apis.json 의 trigger_keywords 매칭으로
                 해당 도구의 mock_response 를 반환. 매칭된 도구는 '전부' 호출.
   mode="real" : 실제 API 호출. _build_real / _run_real 의 TODO 만 채우면 전환.
                 (실제 단계에서는 키워드 매칭 대신 LLM function calling 으로 도구 선택)

   build/run 은 mode 에 따라 '분기'만 한다. 목업/실제 로직은 서로 다른 함수에 분리.
"""

NAME = "tool"


def build(conn: dict):
    """mode 에 따라 목업/실제 리소스를 준비한다."""
    mode = (conn or {}).get("mode", "mock")
    if mode == "real":
        return _build_real(conn)
    return _build_mock(conn)


def run(ctx: dict, resource) -> dict:
    """질문에 맞는 도구를 호출해 ctx["tools_result"] 를 채운다."""
    if resource["mode"] == "real":
        ctx["tools_result"] = _run_real(ctx["query"], resource)
    else:
        ctx["tools_result"] = _run_mock(ctx["query"], resource)
    return ctx


# =============================================================================
# [목업] mode="mock" - 키워드 매칭으로 도구 선택, 매칭된 도구 전부 호출
# =============================================================================

def _build_mock(conn: dict):
    """도구 정의(json)를 읽어 둔다. (conn: {mock_path})"""
    import json
    with open(conn["mock_path"], encoding="utf-8") as f:
        tools = json.load(f)["tools"]
    return {"mode": "mock", "tools": tools}


def _pick_mock_response(query: str, tool: dict) -> str:
    """도구의 mock_response 가 dict 면 query 안의 키로, 문자열이면 그대로 반환."""
    resp = tool["mock_response"]
    if isinstance(resp, dict):
        for key, val in resp.items():
            if key != "default" and key.lower() in query.lower():
                return val
        return resp.get("default", "")
    return resp


def _run_mock(query: str, resource) -> str:
    """trigger_keywords 가 걸리는 도구를 모두 호출해 결과를 합친다."""
    q = (query or "").lower()
    lines = []
    for tool in resource["tools"]:
        if any(k.lower() in q for k in tool.get("trigger_keywords", [])):
            result = _pick_mock_response(query, tool)
            lines.append(f"[{tool['name']}] {result}")
    return "\n".join(lines)


# =============================================================================
# [실제] mode="real" - TODO: 실제 API 연동 시 이 두 함수만 채운다
# =============================================================================

def _build_real(conn: dict):
    """실제 도구 클라이언트/스펙을 준비한다. (conn: {endpoint_url, api_key, ...})"""
    # TODO 실제 API 클라이언트 준비
    #   - 도구 스펙(function schema) 구성
    #   - LLM function calling 으로 도구 선택하도록 llm 에셋과 연계 검토
    raise NotImplementedError("실제 tool 연동 미구현 - ASSET_CONN['tool']['mode']='mock' 사용")


def _run_real(query: str, resource) -> str:
    """LLM 이 고른 도구를 실제 호출해 결과를 합친다."""
    # TODO 실제 도구 호출
    #   - function calling 결과로 호출할 도구/인자 결정
    #   - 각 API 엔드포인트 호출 후 결과 join
    raise NotImplementedError("실제 tool 호출 미구현 - ASSET_CONN['tool']['mode']='mock' 사용")
