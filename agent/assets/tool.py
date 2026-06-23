"""
tool 에셋 [확장 템플릿] - 외부 도구 실행 결과를 ctx["tools_result"] 에 채운다.
사용하려면: ENABLED_ASSETS 에 "tool" 추가 + ASSET_CONN["tool"] 채우기 + 아래 TODO 구현.
"""

NAME = "tool"


def build(conn: dict):
    """도구 호출에 필요한 설정을 준비한다. (conn: {endpoint_url, api_key})"""
    # TODO 도구 클라이언트/스펙 준비해서 반환
    return {"conn": conn}


def run(ctx: dict, resource) -> dict:
    """필요한 도구를 호출해 ctx["tools_result"] 에 넣는다. (TOOL 단계)"""
    # TODO 도구 실행 구현 후 ctx["tools_result"] 채우기
    return ctx
