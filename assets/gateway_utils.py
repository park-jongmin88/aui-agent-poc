"""
==============================================================================
 assets/gateway_utils.py  -  MLflow AI Gateway 조회 공통 유틸
==============================================================================
 agent.py(등록 시 대화형 선택)와 mlflow_inspect.py(단순 조회) 가 함께 쓰는
 gateway REST 호출 로직. 한 곳에서 관리해 두 파일이 같은 방식으로 gateway 를
 부르게 한다. (추후 UI 로 agent 를 구성하게 되면 이 모듈이 그 백엔드 로직이 됨)

 [경로] mlflow 의 get_deploy_client().list_endpoints() 는 옛 경로(/api/2.0/endpoints/)
        를 호출해 3.x 서버에서 404 가 난다. 3.x 실제 경로(MLflow UI 가 쓰는 경로):
            /api/3.0/mlflow/gateway/endpoints/list      (목록)
            /api/3.0/mlflow/gateway/endpoints/{name}    (상세, 없을 수 있음)
        (브라우저는 ajax-api 를 쓰지만 프로그램은 api 가 표준 - 둘 다 폴백 시도)

 [인증] gateway 호출도 MLflow 로그인 권한이 필요하다 (judge_eval 과 동일 방식).
        Authorization: Basic base64(MLFLOW_USERNAME:MLFLOW_PASSWORD)
        이 정보는 이미 agent 등록에 쓰는 MLflow 접속정보와 같으므로 재사용한다.
        (별도의 gateway 전용 키를 새로 관리할 필요가 없다.)
==============================================================================
"""

import base64


def basic_auth_headers(username: str, password: str) -> dict:
    """MLflow 아이디/비번으로 Basic 인증 헤더를 만든다. (judge_eval 방식과 동일)"""
    user = username if isinstance(username, str) else ""
    pw = password if isinstance(password, str) else ""
    token = base64.b64encode(f"{user}:{pw}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def gateway_get(tracking_uri: str, username: str, password: str, path_suffix: str):
    """3.x gateway REST 경로를 Basic 인증 헤더로 호출한다.
    api / ajax-api 두 prefix 를 순서대로 시도(폴백)한다.

    Args:
        tracking_uri: MLflow 서버 주소 (예: "http://mlflow.도메인.com")
        username, password: MLflow 로그인 정보 (Basic 인증에 사용)
        path_suffix: "endpoints/list" 또는 "endpoints/{name}" 등

    Returns:
        (json dict, 실제 사용된 url)

    Raises:
        PermissionError: 401/403 (인증/권한 문제 - 바로 원인이 분명하므로 폴백 없이 즉시 알림)
        Exception: 그 외 실패 (마지막 시도의 예외)
    """
    import requests

    if not isinstance(tracking_uri, str) or not tracking_uri:
        raise ValueError("tracking_uri 가 비어 있습니다.")

    base = tracking_uri.rstrip("/")
    headers = basic_auth_headers(username, password)
    last_exc = None
    for prefix in ("api", "ajax-api"):
        url = f"{base}/{prefix}/3.0/mlflow/gateway/{path_suffix}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                return r.json(), url
            if r.status_code in (401, 403):
                raise PermissionError(
                    f"{r.status_code} 인증/권한 거부 (MLflow 아이디/비번 확인). url={url}"
                )
            last_exc = RuntimeError(f"HTTP {r.status_code} at {url} - {r.text[:200]}")
        except PermissionError:
            raise
        except Exception as e:
            last_exc = e
    raise last_exc if last_exc else RuntimeError("gateway 조회 실패 (원인 불명)")


def list_gateway_endpoints(tracking_uri: str, username: str, password: str) -> list:
    """gateway 에 등록된 엔드포인트 목록을 가져온다.
    반환: [{"name": ..., "endpoint_type": ..., "model": {...}}, ...]
    """
    data, _ = gateway_get(tracking_uri, username, password, "endpoints/list")
    return data.get("endpoints", []) if isinstance(data, dict) else []


def filter_by_type(endpoints: list, type_keyword: str) -> list:
    """endpoint_type 문자열에 특정 키워드(chat/embedding/completion 등)가
    포함된 것만 걸러낸다. 대소문자 구분 없음.
    """
    kw = type_keyword.lower()
    out = []
    for ep in endpoints:
        etype = str(ep.get("endpoint_type") or ep.get("task") or "").lower()
        if kw in etype:
            out.append(ep)
    return out


def prompt_pick_endpoint(endpoints: list, prompt_label: str = "엔드포인트"):
    """엔드포인트 목록을 번호로 보여주고 사용자가 고르게 한다. (CLI 대화형)
    나중에 UI 로 옮길 때는 이 함수의 '선택 로직'만 폼 제출로 바꾸면 된다.

    Returns: 선택한 endpoint dict, 또는 None(취소/목록없음)
    """
    if not endpoints:
        print(f"  [경고] 사용 가능한 {prompt_label}가 없습니다.")
        return None

    print(f"\n  사용할 {prompt_label}를 선택하세요:")
    for i, ep in enumerate(endpoints, 1):
        name = ep.get("name", "?")
        etype = ep.get("endpoint_type") or ep.get("task") or "?"
        model = ep.get("model") or {}
        model_name = model.get("name", "") if isinstance(model, dict) else ""
        extra = f" (model: {model_name})" if model_name else ""
        print(f"    [{i}] {name}  [{etype}]{extra}")
    print(f"    [0] 건너뛰기 (나중에 직접 입력)")

    while True:
        sel = input(f"  번호 선택: ").strip()
        if sel == "0":
            return None
        if sel.isdigit() and 1 <= int(sel) <= len(endpoints):
            return endpoints[int(sel) - 1]
        print("  올바른 번호를 입력하세요.")
