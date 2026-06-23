"""
prompt 에셋 - MLflow Prompt Registry 에서 시스템 프롬프트를 불러와 ctx 에 채운다.

[A 원칙] 프롬프트의 주인은 서버다. client 는 어떤 프롬프트를 쓸지 'id 만' 고른다.
         실제 프롬프트 텍스트는 항상 MLflow 에서 로드한다.

[우선순위]
   1. client 가 고른 ctx["prompt_id"] 로 MLflow 에서 로드
   2. 로드 실패(미선택/레지스트리 오류) -> default_system 폴백
"""

import mlflow

NAME = "prompt"


def build(conn: dict):
    """기본 폴백 프롬프트와 별칭(alias)을 준비한다. (conn: {default_system, alias})"""
    return {
        "default": (conn or {}).get("default_system", ""),
        "alias":   (conn or {}).get("alias", "production"),
    }


def list_prompts() -> list:
    """등록된 프롬프트 이름 목록을 반환한다. (client 가 시작 시 고르도록)"""
    try:
        results = mlflow.genai.search_prompts()
        return [p.name for p in results]
    except Exception:
        return []


def run(ctx: dict, resource) -> dict:
    """client 가 고른 prompt_id 로 프롬프트를 로드해 system_message 를 채운다."""
    pid = ctx.get("prompt_id")
    if pid:
        try:
            uri = pid if str(pid).startswith("prompts:/") else f"prompts:/{pid}@{resource['alias']}"
            prompt = mlflow.genai.load_prompt(uri)
            ctx["system_message"] = prompt.format()
            return ctx
        except Exception:
            pass
    # 폴백
    ctx["system_message"] = resource.get("default", "")
    return ctx
