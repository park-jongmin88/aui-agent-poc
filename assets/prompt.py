"""
prompt 에셋 - MLflow Prompt Registry 에서 시스템 프롬프트를 불러와 ctx 에 채운다.

[A 원칙] 프롬프트의 주인은 서버다. client 는 어떤 프롬프트를 쓸지 'id(+버전)만' 고른다.
         실제 프롬프트 텍스트는 항상 MLflow 에서 로드한다.

[버전 선택] 프롬프트는 이름별로 여러 버전(v1, v2, ...)이 쌓인다.
   - client 가 prompt_id + (선택)prompt_version 을 보낸다.
   - prompt_version 이 있으면 그 버전을, 없으면 '최신 버전' 을 로드한다.
   - 별칭(@production)에 의존하지 않는다. (별칭 미부여 프롬프트도 정상 로드)
   - UI 는 "프롬프트 선택 -> 버전 선택" 2단계로 하나를 확정한다.

[성능] 같은 (prompt_id, version) 은 매 호출마다 다시 받지 않고 캐시한다.
       (load_prompt 는 MLflow 서버 왕복이라 매번 호출하면 응답이 크게 느려진다)

[우선순위]
   1. client 가 고른 prompt_id (+version) 로 (캐시 우선) 로드
   2. 프롬프트 목록 자체가 없거나 / 로드 실패 -> default_system 폴백
"""

import mlflow

NAME = "prompt"


def build(conn: dict):
    """폴백 프롬프트 + 프롬프트 캐시를 준비한다."""
    return {
        "default": (conn or {}).get("default_system", ""),
        "cache":   {},   # "id@version" -> system_message 문자열
    }


def list_prompts() -> list:
    """등록된 프롬프트 목록을 [{name, versions}] 형태로 반환한다.
    UI 1단계용:  PROMPT_A [3]  (versions=버전 개수)
    목록이 없으면 빈 리스트 -> 호출측은 default 로 간다.
    """
    out = []
    try:
        results = mlflow.genai.search_prompts()
    except Exception:
        return []
    for p in results:
        try:
            vers = list_versions(p.name)
            out.append({"name": p.name, "versions": len(vers)})
        except Exception:
            out.append({"name": p.name, "versions": 0})
    return out


def list_versions(name: str) -> list:
    """특정 프롬프트의 버전 번호 목록을 반환한다. (예: [1, 2, 3])
    UI 2단계용: 프롬프트를 고르면 그 안의 버전들을 보여주고 하나를 고르게 한다.
    """
    try:
        vers = mlflow.genai.search_prompt_versions(name)
        nums = []
        for v in vers:
            n = getattr(v, "version", None)
            if n is not None:
                nums.append(int(n))
        return sorted(nums)
    except Exception:
        return []


def _latest_version(name: str):
    """이름의 최신(가장 큰) 버전 번호를 반환한다. 없으면 None."""
    nums = list_versions(name)
    return max(nums) if nums else None


def _load_system(pid: str, version, resource) -> str:
    """prompt_id(+version) 로 system_message 를 얻는다.
    캐시에 있으면 그대로, 없으면 1회 로드 후 캐시.
    version 이 없으면 최신 버전을 사용한다.
    """
    # 이미 완전한 URI 를 보냈으면 그대로 사용
    if str(pid).startswith("prompts:/"):
        uri = pid
        key = pid
    else:
        ver = version if version not in (None, "", "latest") else _latest_version(pid)
        if ver is None:
            # 버전을 알 수 없으면 이름만으로 로드 시도 (MLflow 가 최신을 줄 수도 있음)
            uri = f"prompts:/{pid}"
            key = f"{pid}@?"
        else:
            uri = f"prompts:/{pid}/{ver}"
            key = f"{pid}@{ver}"

    cache = resource["cache"]
    if key in cache:
        return cache[key]
    text = mlflow.genai.load_prompt(uri).format()
    cache[key] = text
    return text


@mlflow.trace(name="asset.prompt", span_type="CHAIN")
def run(ctx: dict, resource) -> dict:
    """client 가 고른 prompt_id(+prompt_version) 로 system_message 를 채운다. (캐시 사용)
    실패하거나 미선택이면 default 로 폴백한다.
    """
    pid = ctx.get("prompt_id")
    version = ctx.get("prompt_version")   # 없으면 최신 버전 사용
    if pid:
        try:
            ctx["system_message"] = _load_system(pid, version, resource)
            return ctx
        except Exception:
            pass
    ctx["system_message"] = resource.get("default", "")
    return ctx
