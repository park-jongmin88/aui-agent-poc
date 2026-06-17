"""
skills/deploy/scripts/deploy_client.py

AI Studio 포탈 배포 API 클라이언트.
- AIStudioAPIClient: REST API 래퍼 (모든 호출이 _request 로 모임)
- deploy_model(): 배포 전체 흐름 (생성 → RUNNING 폴링 → URL 반환)

※ 실제 AI Studio API 스펙에 맞춰 TODO 부분을 채워야 동작합니다.
   현재는 POC 골격입니다.
"""
import json
import time


# ── 기본 엔드포인트 리소스 설정 ──────────────────────────────
DEFAULT_RESOURCES = {
    "cpu":    "1",       # TODO: 실제 리소스 단위 확인
    "memory": "2Gi",
    "gpu":    "0",
    "replicas": 1,
}


class APIConfig:
    """API 접속 설정."""
    def __init__(self, api_url: str, system_key: str = "", project_id: str = ""):
        self.api_url     = api_url.rstrip("/")
        self.system_key  = system_key
        self.project_id  = project_id


class AIStudioAPIClient:
    """AI Studio 포탈 REST API 클라이언트.
    모든 호출은 _request(method, path, **kwargs) 로 모인다.
    """

    def __init__(self, config: APIConfig):
        self.config = config

    def _request(self, method: str, path: str, **kwargs):
        """모든 API 호출의 단일 진입점."""
        import requests
        url = f"{self.config.api_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Content-Type", "application/json")
        if self.config.system_key:
            # TODO: 실제 인증 헤더 형식 확인
            headers["Authorization"] = f"Bearer {self.config.system_key}"
        resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text

    # ── 조회 계열 ──
    def get_user_info(self):
        return self._request("GET", "/user")                       # TODO: 경로 확인

    def list_projects(self):
        return self._request("GET", "/projects")                   # TODO

    def get_models(self, project_id: str):
        return self._request("GET", f"/projects/{project_id}/models")   # TODO

    def get_model_version(self, project_id: str, model_nm: str):
        return self._request("GET", f"/projects/{project_id}/models/{model_nm}/versions")  # TODO

    def list_endpoints(self, project_id: str):
        return self._request("GET", f"/projects/{project_id}/endpoints")  # TODO

    def get_endpoint(self, project_id: str, endpoint_id: str):
        return self._request("GET", f"/projects/{project_id}/endpoints/{endpoint_id}")  # TODO

    # ── 배포 계열 ──
    def create_endpoint(self, project_id: str, body: dict):
        return self._request("POST", f"/projects/{project_id}/endpoints", data=json.dumps(body))  # TODO

    def delete_endpoint(self, project_id: str, endpoint_id: str):
        return self._request("DELETE", f"/projects/{project_id}/endpoints/{endpoint_id}")  # TODO

    def stop_endpoint(self, project_id: str, endpoint_id: str):
        return self._request("POST", f"/projects/{project_id}/endpoints/{endpoint_id}/stop")  # TODO

    def start_endpoint(self, project_id: str, endpoint_id: str):
        return self._request("POST", f"/projects/{project_id}/endpoints/{endpoint_id}/start")  # TODO


def deploy_model(client: AIStudioAPIClient, project_id: str, model_nm: str,
                 model_ver: str, dependencies: list, resources: dict = None,
                 poll_timeout: int = 300, on_progress=None):
    """배포 전체 흐름.
    1. Endpoint 생성 API 호출
    2. RUNNING 상태까지 폴링
    3. Endpoint URL 반환
    """
    resources = resources or DEFAULT_RESOURCES

    def _log(msg):
        if on_progress:
            on_progress(msg)

    # Endpoint 생성 Request body
    body = {
        "model_name":    model_nm,
        "model_version": model_ver,
        "dependencies":  dependencies,   # requirements.txt 내용
        "resources":     resources,
        # TODO: 실제 API 가 요구하는 추가 필드
    }

    _log(f"Endpoint 생성 요청: {model_nm} v{model_ver}")
    created = client.create_endpoint(project_id, body)

    endpoint_id = created.get("endpoint_id") or created.get("id")  # TODO: 응답 필드 확인
    if not endpoint_id:
        raise RuntimeError(f"Endpoint 생성 응답에 ID가 없습니다: {created}")

    # RUNNING 폴링
    _log("RUNNING 상태 대기 중...")
    deadline = time.time() + poll_timeout
    endpoint_url = None
    while time.time() < deadline:
        info = client.get_endpoint(project_id, endpoint_id)
        status = info.get("status", "")                 # TODO: 상태 필드 확인
        if status == "RUNNING":
            endpoint_url = info.get("url") or info.get("endpoint_url")  # TODO
            break
        time.sleep(5)

    if not endpoint_url:
        raise TimeoutError(f"Endpoint가 {poll_timeout}초 내에 RUNNING 되지 않았습니다.")

    _log(f"배포 완료: {endpoint_url}")
    return {
        "endpoint_id":  endpoint_id,
        "endpoint_url": endpoint_url,
        "status":       "RUNNING",
    }
