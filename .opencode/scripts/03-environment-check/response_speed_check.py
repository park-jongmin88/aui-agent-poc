#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


EXPECTED_IGNORE_PATTERNS = [
    ".opencode/",
    ".opencode/node_modules/",
    ".venv/",
    "node_modules/",
    "ai_studio/tracking/",
        "ai_studio/metrics/",
    "ai_studio/code/",
    "saved_model/",
    "datasets/",
    "*.pt",
    "*.pth",
    "*.onnx",
    "*.h5",
    "*.keras",
    "*.pkl",
    "*.joblib",
    "*.safetensors",
    "*.bst",
    "*.ubj",
]

SLOW_DIR_NAMES = {
    ".opencode",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "ai_studio",
    "artifacts",
    "build",
    "checkpoints",
    "data",
    "dataset",
    "datasets",
    "dist",
    "lightning_logs",
    "mlartifacts",
    "model",
    "models",
    "node_modules",
    "runs",
    "saved_model",
    "venv",
    "wandb",
    "wheelhouse",
    "__pycache__",
}

LARGE_SUFFIXES = {
    ".csv",
    ".h5",
    ".joblib",
    ".keras",
    ".npy",
    ".npz",
    ".onnx",
    ".parquet",
    ".pkl",
    ".pt",
    ".pth",
    ".safetensors",
    ".bst",
    ".ubj",
    ".tar",
    ".gz",
    ".whl",
    ".zip",
}


def resolve_workspace_project(raw_project: str) -> Path:
    raw = raw_project.strip()
    if raw in {"<workspace-root>", "<current-project-folder>", "<model-project-folder>"}:
        raw = "."
    elif "<" in raw or ">" in raw:
        raise ValueError("replace placeholder project path before running, for example: --project .")

    project = Path(raw).expanduser().resolve()
    parts = project.parts
    if ".opencode" in parts:
        opencode_index = parts.index(".opencode")
        if opencode_index > 0:
            return Path(*parts[:opencode_index]).resolve()
    return project


@dataclass
class Finding:
    status: str
    name: str
    detail: str
    action: str


def rel(path: Path, root: Path) -> str:
    try:
        value = path.relative_to(root).as_posix()
    except ValueError:
        value = path.as_posix()
    return value or "."


def should_report_slow_dir(path: Path, root: Path) -> bool:
    value = rel(path, root)
    if value == ".opencode" or value.startswith(".opencode/"):
        return False
    return True


def load_ignore_text(project: Path) -> str:
    parts = []
    for name in (".ignore", ".rgignore", ".gitignore"):
        path = project / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def check_ignore(project: Path) -> list[Finding]:
    text = load_ignore_text(project)
    if not text.strip():
        return [
            Finding(
                "warn",
                "ignore files",
                ".ignore, .rgignore, .gitignore ignore block is missing",
                "Run: python .opencode/scripts/03-environment-check/apply_index_ignore.py --project .",
            )
        ]

    missing = [pattern for pattern in EXPECTED_IGNORE_PATTERNS if pattern not in text]
    if missing:
        return [
            Finding(
                "warn",
                "ignore patterns",
                "missing: " + ", ".join(missing),
                "Run: python .opencode/scripts/03-environment-check/apply_index_ignore.py --project .",
            )
        ]
    return [
        Finding(
            "pass",
            "ignore patterns",
            "closed-network index ignore patterns are present",
            "No action needed",
        )
    ]


def check_opencode_config(project: Path) -> list[Finding]:
    path = project / ".opencode" / "opencode.json"
    if not path.exists():
        return [
            Finding(
                "warn",
                "opencode config",
                ".opencode/opencode.json not found",
                "Keep the package .opencode folder at the workspace root",
            )
        ]
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            Finding(
                "fail",
                "opencode config",
                f"JSON parse error at line {exc.lineno}: {exc.msg}",
                "Fix .opencode/opencode.json before running OpenCode",
            )
        ]
    return [
        Finding(
            "pass",
            "opencode config",
            ".opencode/opencode.json is valid JSON",
            "No action needed",
        )
    ]


def scan_workspace(project: Path, max_files: int, large_mb: int) -> tuple[list[Finding], bool]:
    findings: list[Finding] = []
    slow_dirs: list[tuple[str, int]] = []
    large_files: list[tuple[str, float]] = []
    visited_files = 0
    truncated = False
    large_bytes = large_mb * 1024 * 1024

    for current, dirnames, filenames in os.walk(project):
        current_path = Path(current)
        relative_parts = current_path.relative_to(project).parts if current_path != project else ()

        if ".git" in relative_parts:
            dirnames[:] = []
            continue

        kept_dirs = []
        for dirname in dirnames:
            dir_path = current_path / dirname
            is_slow = dirname in SLOW_DIR_NAMES or "wheelhouse" in dir_path.parts
            if is_slow and should_report_slow_dir(dir_path, project):
                try:
                    immediate_count = sum(1 for _ in os.scandir(dir_path))
                except OSError:
                    immediate_count = -1
                slow_dirs.append((rel(dir_path, project), immediate_count))
            if dirname in {".git", ".opencode", "node_modules", ".venv", "venv", "__pycache__", "wheelhouse"}:
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            visited_files += 1
            file_path = current_path / filename
            suffix = file_path.suffix.lower()
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size >= large_bytes or suffix in LARGE_SUFFIXES:
                large_files.append((rel(file_path, project), size / 1024 / 1024))
            if visited_files >= max_files:
                truncated = True
                dirnames[:] = []
                break
        if truncated:
            break

    if slow_dirs:
        top_dirs = sorted(slow_dirs, key=lambda item: item[1], reverse=True)[:10]
        detail = ", ".join(f"{path}({count if count >= 0 else '?'})" for path, count in top_dirs)
        findings.append(
            Finding(
                "warn",
                "slow directories",
                detail,
                "Apply ignore rules and keep generated/data/model folders out of OpenCode indexing",
            )
        )
    else:
        findings.append(
            Finding(
                "pass",
                "slow directories",
                "no common heavy generated folders found",
                "No action needed",
            )
        )

    if large_files:
        top_files = sorted(large_files, key=lambda item: item[1], reverse=True)[:10]
        detail = ", ".join(f"{path}({size:.1f}MB)" for path, size in top_files)
        findings.append(
            Finding(
                "warn",
                "large files",
                detail,
                "Move datasets/model binaries under ignored folders or add explicit ignore patterns",
            )
        )
    else:
        findings.append(
            Finding(
                "pass",
                "large files",
                f"no files over {large_mb}MB or known model/data suffixes found in scanned range",
                "No action needed",
            )
        )

    if truncated:
        findings.append(
            Finding(
                "warn",
                "scan limit",
                f"stopped after {max_files} files",
                "This workspace is large; apply ignore rules before opening OpenCode",
            )
        )

    return findings, truncated


def render_text(project: Path, findings: list[Finding]) -> None:
    print("OpenCode closed-network response speed check")
    print("Project: .")
    print("")

    for index, finding in enumerate(findings, start=1):
        print(f"{index}. [{finding.status}] {finding.name}")
        print(f"   detail: {finding.detail}")
        print(f"   action: {finding.action}")

    has_warn_or_fail = any(item.status in {"warn", "fail"} for item in findings)
    print("")
    print("Recommended fast path:")
    print("1. python .opencode/scripts/03-environment-check/apply_index_ignore.py --project .")
    print("2. Restart/Open OpenCode after ignore files are applied.")
    print("3. In Ai Studio 모드, answer with model_found + one next action only.")
    print("4. In Ai Studio 빌드 모드, run scripts directly instead of re-scanning the full tree.")
    if has_warn_or_fail:
        print("")
        print("TODO:")
        print("- Fix warn/fail items above before long model analysis.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose OpenCode response speed issues in closed-network ML workspaces.")
    parser.add_argument("--project", default=".", help="workspace root")
    parser.add_argument("--max-files", type=int, default=50000, help="stop scan after this many files")
    parser.add_argument("--large-mb", type=int, default=50, help="large file threshold in MB")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    project = resolve_workspace_project(args.project)
    if not project.exists():
        raise SystemExit(f"project not found: {project}")

    findings: list[Finding] = []
    findings.extend(check_opencode_config(project))
    findings.extend(check_ignore(project))
    scan_findings, _ = scan_workspace(project, args.max_files, args.large_mb)
    findings.extend(scan_findings)

    if args.json:
        print(json.dumps({"project": ".", "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    else:
        render_text(project, findings)

    return 1 if any(item.status == "fail" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
