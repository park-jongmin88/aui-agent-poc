"""
prompt 에셋 - MLflow Prompt Registry 에서 시스템 프롬프트를 불러와 ctx 에 채운다.

[A 원칙] 프롬프트의 주인은 서버다. client 는 어떤 프롬프트를 쓸지 'id 만' 고른다.
         실제 프롬프트 텍스트는 항상 MLflow 에서 로드한다.

[성능] 같은 prompt_id 는 매 호출마다 다시 받지 않고 캐시한다.
       (load_prompt 는 MLflow 서버 왕복이라 매번 호출하면 응답이 크게 느려진다)

[우선순위]
   1. client 가 고른 ctx["prompt_id"] 로 (캐시 우선) 로드
   2. 로드 실패(미선택/레지스트리 오류) -> default_system 폴백
"""

import mlflow

NAME = "prompt"


def build(conn: dict):
    """폴백 프롬프트/별칭 + 프롬프트 캐시를 준비한다."""
    return {
        "default": (conn or {}).get("default_system", ""),
        "alias":   (conn or {}).get("alias", "production"),
        "cache":   {},   # prompt_id -> system_message 문자열
    }


def list_prompts() -> list:
    """등록된 프롬프트 이름 목록을 반환한다. (client 가 시작 시 고르도록)"""
    try:
        results = mlflow.genai.search_prompts()
        return [p.name for p in results]
    except Exception:
        return []


def _load_system(pid: str, resource) -> str:
    """prompt_id 로 system_message 를 얻는다. 캐시에 있으면 그대로, 없으면 1회 로드 후 캐시."""
    cache = resource["cache"]
    if pid in cache:
        return cache[pid]
    uri = pid if str(pid).startswith("prompts:/") else f"prompts:/{pid}@{resource['alias']}"
    text = mlflow.genai.load_prompt(uri).format()
    cache[pid] = text
    return text


def run(ctx: dict, resource) -> dict:
    """client 가 고른 prompt_id 로 system_message 를 채운다. (캐시 사용)"""
    pid = ctx.get("prompt_id")
    if pid:
        try:
            ctx["system_message"] = _load_system(pid, resource)
            return ctx
        except Exception:
            pass
    ctx["system_message"] = resource.get("default", "")
    return ctx
