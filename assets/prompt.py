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


def list_versions(name: str, max_scan: int = 100) -> list:
    """특정 프롬프트의 버전 번호 목록을 반환한다. (예: [1, 2, 3])
    UI 2단계용: 프롬프트를 고르면 그 안의 버전들을 보여주고 하나를 고르게 한다.

    [중요] MlflowClient().search_prompt_versions 는 Databricks 백엔드 전용이라
    OSS(자체 호스팅) MLflow 에서는 동작하지 않는다(버전이 0으로 나옴).
    그래서 OSS 호환을 위해 버전 1 부터 load_prompt 로 순차 탐색한다.
    프롬프트 버전은 1,2,3... 으로 연속 증가하므로, 로드 실패가 나오면 거기서 멈춘다.

    이 함수는 '최초 선택 화면(목록 표시)' 에서만 호출된다.
    실제 대화 추론 경로에서는 호출되지 않으므로, 약간의 탐색 비용은 문제되지 않는다.
    """
    nums = []
    v = 1
    while v <= max_scan:
        try:
            mlflow.genai.load_prompt(name, version=v)
            nums.append(v)
            v += 1
        except Exception:
            break
    return nums


def _load_system(pid: str, version, resource) -> str:
    """prompt_id(+version) 로 system_message 를 얻는다.
    캐시에 있으면 그대로, 없으면 1회 로드 후 캐시.
    version 이 없으면 이름만으로 로드 → MLflow 가 최신 버전을 준다.

    정확한 API:
      mlflow.genai.load_prompt("name", version=3)        # 특정 버전
      mlflow.genai.load_prompt("name")                    # 최신
      mlflow.genai.load_prompt("prompts:/name/3")         # URI 도 가능
    """
    cache = resource["cache"]

    # 이미 완전한 URI 를 보냈으면 그대로 사용
    if str(pid).startswith("prompts:/"):
        key = pid
        if key in cache:
            return cache[key]
        text = mlflow.genai.load_prompt(pid).format()
        cache[key] = text
        return text

    ver = version if version not in (None, "", "latest") else None
    key = f"{pid}@{ver if ver is not None else 'latest'}"
    if key in cache:
        return cache[key]

    if ver is not None:
        prompt = mlflow.genai.load_prompt(pid, version=int(ver))
    else:
        prompt = mlflow.genai.load_prompt(pid)   # 버전 생략 → 최신
    text = prompt.format()
    cache[key] = text
    return text


@mlflow.trace(name="asset.prompt", span_type="CHAIN")
def run(ctx: dict, resource) -> dict:
    """client 가 고른 prompt_id(+prompt_version) 로 system_message 를 채운다. (캐시 사용)
    실패하거나 미선택이면 default 로 폴백한다.

    [진단] 로드 실패 시 예외를 삼키지 않고 trace span 에 기록한다.
           (prompt_id/version 은 정상인데 default 로 폴백되는 원인을 추적하기 위함)
    """
    import traceback as _tb

    pid = ctx.get("prompt_id")
    version = ctx.get("prompt_version")   # 없으면 최신 버전 사용

    # 진단: 무엇으로 로드를 시도하는지 span 에 남긴다.
    try:
        span = mlflow.get_current_active_span()
        if span is not None:
            span.set_attribute("prompt.pid", str(pid))
            span.set_attribute("prompt.version", str(version))
            span.set_attribute("prompt.mlflow_version", getattr(mlflow, "__version__", "?"))
    except Exception:
        span = None

    if pid:
        try:
            ctx["system_message"] = _load_system(pid, version, resource)
            if span is not None:
                span.set_attribute("prompt.loaded", "ok")
            return ctx
        except Exception as e:
            # 예외를 삼키지 말고 무엇이 왜 실패했는지 span 에 기록한다.
            if span is not None:
                span.set_attribute("prompt.loaded", "FAILED -> default 폴백")
                span.set_attribute("prompt.error_type", type(e).__name__)
                span.set_attribute("prompt.error_msg", str(e)[:500])
                span.set_attribute("prompt.error_trace", _tb.format_exc()[-1500:])
    ctx["system_message"] = resource.get("default", "")
    return ctx
