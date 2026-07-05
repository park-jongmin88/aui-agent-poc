#!/usr/bin/env python3
"""시작 시 .env 체크 (무조건 발동 규칙 01-env-check).

- 루트 .env 존재/필수값 확인
- 없으면 템플릿 생성 후 작성 안내
- 결과를 JSON 으로 출력

사용: python .opencode/scripts/00-setup/check_env.py --project .
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
import subprocess
from pathlib import Path

ENV_TEMPLATE = (
    "MLFLOW_TRACKING_URI=\n"
    "MLFLOW_TRACKING_USERNAME=\n"
    "MLFLOW_TRACKING_PASSWORD=\n"
    "MLFLOW_VERSION=\n"
)

REQUIRED_KEYS = ["MLFLOW_TRACKING_URI"]
OPTIONAL_KEYS = ["MLFLOW_TRACKING_USERNAME", "MLFLOW_TRACKING_PASSWORD"]


def parse_env(path: Path) -> dict:
    result = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    env_path = project / ".env"

    # 1. .env 없으면 생성 후 안내
    if not env_path.exists():
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")
        print(json.dumps({
            "status": "created",
            "env_path": ".env",
            "ready": False,
            "message": ".env 파일이 없어 새로 생성했습니다. "
                       "MLFLOW_TRACKING_URI 등 값을 작성한 뒤 다시 시작하세요.",
            "required": REQUIRED_KEYS,
        }, ensure_ascii=False))
        return

    # 2. 필수값 확인
    values = parse_env(env_path)
    missing = [k for k in REQUIRED_KEYS if not values.get(k, "").strip()]

    if missing:
        print(json.dumps({
            "status": "incomplete",
            "env_path": ".env",
            "ready": False,
            "missing": missing,
            "message": f"필수 값이 비어 있습니다: {', '.join(missing)}. "
                       "값을 작성한 뒤 다시 시작하세요.",
        }, ensure_ascii=False))
        return

    # 3. 통과 — mlflow 버전도 함께 조회해 사용자에게 알려준다.
    mlflow_version = None
    version_source = None
    version_note = None
    try:
        fetch = Path(__file__).resolve().parent / "fetch_mlflow_version.py"
        if fetch.exists():
            proc = subprocess.run(
                [sys.executable, str(fetch), "--project", str(project)],
                capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
            )
            vdata = json.loads(proc.stdout.strip() or "{}")
            mlflow_version = vdata.get("version")
            status = vdata.get("status")
            # 출처를 사람이 읽기 쉽게 변환
            if status == "env":
                version_source = ".env 의 MLFLOW_VERSION 고정값"
            elif status == "ok":
                version_source = "트래킹 서버 조회"
            elif status in {"fetch_failed", "no_uri"}:
                version_source = "기본값 (서버 조회 실패)"
                version_note = "트래킹 URL 로 실제 연결되지 않아 기본 버전을 사용합니다. 실제 서버 버전과 다를 수 있습니다."
            else:
                version_source = status
    except Exception:
        pass

    result = {
        "status": "ok",
        "env_path": ".env",
        "ready": True,
        "tracking_uri_set": bool(values.get("MLFLOW_TRACKING_URI", "").strip()),
        "username_set": bool(values.get("MLFLOW_TRACKING_USERNAME", "").strip()),
        "password_set": bool(values.get("MLFLOW_TRACKING_PASSWORD", "").strip()),
        "mlflow_version": mlflow_version,
        "mlflow_version_source": version_source,
        "message": f"MLflow 연결 정보 확인 완료. 사용할 MLflow 버전: {mlflow_version} ({version_source}).",
    }
    if version_note:
        result["mlflow_version_note"] = version_note
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"status": "error", "ready": False,
                          "message": f"env 체크 오류: {e}"}, ensure_ascii=False))
        sys.exit(1)
