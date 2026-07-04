#!/usr/bin/env python3
"""트래킹 URL 에서 MLflow 버전 조회.

- .env 의 MLFLOW_TRACKING_URI 로 표준 버전 API 호출
- 성공: 조회된 버전 반환
- 실패: URL 재확인 안내 + 기본값 3.10.0

사용: python .opencode/scripts/00-setup/fetch_mlflow_version.py --project .
"""

# --- Windows/CP949 콘솔에서도 한글이 깨지지 않도록 stdout/stderr를 UTF-8로 강제 ---
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
# --- end UTF-8 guard ---

import argparse
import json
import sys
from pathlib import Path

DEFAULT_VERSION = "3.10.0"


def parse_env(path: Path) -> dict:
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def fetch_version(tracking_uri: str) -> str | None:
    """MLflow 표준 버전 엔드포인트 호출.
    MLflow 서버는 GET {uri}/version 에 버전 문자열을 반환한다.
    """
    import urllib.request
    base = tracking_uri.rstrip("/")
    # 표준 버전 조회 엔드포인트
    for path in ("/version", "/api/2.0/mlflow/version"):
        try:
            req = urllib.request.Request(base + path)
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8").strip().strip('"')
                # 버전 형태(x.y.z)만 취함
                if body and body[0].isdigit():
                    return body
        except Exception:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    values = parse_env(project / ".env")
    tracking_uri = values.get("MLFLOW_TRACKING_URI", "").strip()

    if not tracking_uri:
        print(json.dumps({
            "status": "no_uri",
            "version": DEFAULT_VERSION,
            "message": "MLFLOW_TRACKING_URI 가 비어 있습니다. .env 를 확인하세요. "
                       f"기본값 {DEFAULT_VERSION} 을 사용합니다.",
        }, ensure_ascii=False))
        return

    version = fetch_version(tracking_uri)

    if version:
        print(json.dumps({
            "status": "ok",
            "version": version,
            "tracking_uri": tracking_uri,
            "message": f"MLflow 버전 조회 성공: {version}",
        }, ensure_ascii=False))
    else:
        # 조회 실패 → URL 재확인 안내 + 기본값
        print(json.dumps({
            "status": "fetch_failed",
            "version": DEFAULT_VERSION,
            "tracking_uri": tracking_uri,
            "message": f"버전 조회 실패. 트래킹 URL 을 재확인하세요: {tracking_uri} "
                       f"(기본값 {DEFAULT_VERSION} 사용)",
        }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"status": "error", "version": DEFAULT_VERSION,
                          "message": f"버전 조회 오류: {e} (기본값 {DEFAULT_VERSION})"},
                         ensure_ascii=False))
        sys.exit(1)
