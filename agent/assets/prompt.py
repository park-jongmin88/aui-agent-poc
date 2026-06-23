"""
prompt 에셋 - 시스템 프롬프트를 ctx 에 구성한다.
현재는 호출 시 client 가 보낸 system_message 를 그대로 사용한다.
[확장] 서버/DB 에서 버전 관리되는 프롬프트를 불러오려면 build() 에서 받아 둔다.
"""

NAME = "prompt"


def build(conn: dict):
    """기본 프롬프트 등을 준비한다. (conn 예: {"default_system": "..."})"""
    return {"default_system": (conn or {}).get("default_system", "")}


def run(ctx: dict, resource) -> dict:
    """system_message 가 비어 있으면 기본값으로 채운다."""
    if not ctx.get("system_message"):
        ctx["system_message"] = resource.get("default_system", "")
    return ctx
