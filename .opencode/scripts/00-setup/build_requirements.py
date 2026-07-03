#!/usr/bin/env python3
"""config/dependencies.md 를 기준으로 requirements.txt 를 생성/갱신.

- dependencies.md 의 "필수 의존성" + "추가 의존성" 을 읽는다
- {version} 을 트래킹 URL 조회 버전으로 치환 (없으면 3.10.0)
- 대상 폴더의 requirements.txt 에 반영 (기존 항목과 병합, 중복 제거)

사용:
  python .opencode/scripts/00-setup/build_requirements.py --project . --target data/<모델폴더>
"""
import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_VERSION = "3.10.0"


def find_repo_root(start: Path) -> Path:
    """.opencode 를 포함하는 루트를 찾는다."""
    cur = start.resolve()
    for _ in range(6):
        if (cur / ".opencode").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()


def parse_dependencies_md(md_path: Path) -> list[str]:
    """dependencies.md 에서 `- 패키지` 줄만 추출 (주석 # 제외)."""
    deps = []
    if not md_path.exists():
        return deps
    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        # "- pkg" 형태만, "# 예시" 주석은 제외
        m = re.match(r"^-\s+(.+)$", s)
        if m:
            item = m.group(1).strip()
            # 인라인 주석 제거
            item = item.split("#")[0].strip()
            if item:
                deps.append(item)
    return deps


def get_mlflow_version(repo_root: Path) -> tuple[str, str]:
    """fetch_mlflow_version.py 를 호출해 버전을 얻는다. (version, source)"""
    import subprocess
    script = repo_root / ".opencode" / "scripts" / "00-setup" / "fetch_mlflow_version.py"
    try:
        out = subprocess.run(
            [sys.executable, str(script), "--project", str(repo_root)],
            capture_output=True, text=True, timeout=20,
        )
        data = json.loads(out.stdout.strip().splitlines()[-1])
        return data.get("version", DEFAULT_VERSION), data.get("status", "unknown")
    except Exception:
        return DEFAULT_VERSION, "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--target", required=True, help="requirements 를 넣을 폴더")
    ap.add_argument("--execute", action="store_true", help="실제 파일 작성")
    args = ap.parse_args()

    repo_root = find_repo_root(Path(args.project))
    md_path = repo_root / ".opencode" / "config" / "dependencies.md"
    target_dir = (repo_root / args.target).resolve()

    # 버전 조회 + 의존성 읽기
    version, ver_status = get_mlflow_version(repo_root)
    deps = parse_dependencies_md(md_path)
    resolved = [d.replace("{version}", version) for d in deps]

    # 기존 requirements 병합
    req_path = target_dir / "requirements.txt"
    existing = []
    if req_path.exists():
        existing = [l.strip() for l in req_path.read_text(encoding="utf-8").splitlines()
                    if l.strip() and not l.startswith("#")]

    # 병합 (강제 의존성 우선, 패키지명 기준 중복 제거)
    def pkg_name(spec):
        return re.split(r"[=<>~!]", spec)[0].strip().lower()

    merged = {}
    for spec in resolved + existing:  # resolved(강제)가 먼저 → 우선
        name = pkg_name(spec)
        if name not in merged:
            merged[name] = spec

    final_lines = list(merged.values())

    result = {
        "status": "ok",
        "mlflow_version": version,
        "version_status": ver_status,
        "target": str(target_dir.relative_to(repo_root)) if target_dir.is_relative_to(repo_root) else str(target_dir),
        "forced": resolved,
        "final": final_lines,
    }

    if args.execute:
        target_dir.mkdir(parents=True, exist_ok=True)
        req_path.write_text("\n".join(final_lines) + "\n", encoding="utf-8")
        result["written"] = str(req_path.name)
        result["message"] = f"requirements.txt 작성 완료 (mlflow=={version}, kserve 포함)"
    else:
        result["message"] = "미리보기 (--execute 로 실제 작성)"

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"requirements 생성 오류: {e}"},
                         ensure_ascii=False))
        sys.exit(1)
