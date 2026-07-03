#!/usr/bin/env python3
"""시작 시 .env 체크 (무조건 발동 규칙 01-env-check).

- 루트 .env 존재/필수값 확인
- 없으면 템플릿 생성 후 작성 안내
- 결과를 JSON 으로 출력

사용: python .opencode/scripts/00-setup/check_env.py --project .
"""
import argparse
import json
import sys
from pathlib import Path

ENV_TEMPLATE = (
    "# MLflow 연결 정보 (Ai Studio 에이전트가 시작 시 확인)\n"
    "# 값을 채운 뒤 저장하세요. TRACKING_URI 는 필수입니다.\n"
    "MLFLOW_TRACKING_URI=\n"
    "MLFLOW_TRACKING_USERNAME=\n"
    "MLFLOW_TRACKING_PASSWORD=\n"
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

    # 3. 통과
    print(json.dumps({
        "status": "ok",
        "env_path": ".env",
        "ready": True,
        "tracking_uri_set": bool(values.get("MLFLOW_TRACKING_URI", "").strip()),
        "username_set": bool(values.get("MLFLOW_TRACKING_USERNAME", "").strip()),
        "password_set": bool(values.get("MLFLOW_TRACKING_PASSWORD", "").strip()),
        "message": "MLflow 연결 정보 확인 완료.",
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"status": "error", "ready": False,
                          "message": f"env 체크 오류: {e}"}, ensure_ascii=False))
        sys.exit(1)
