#!/usr/bin/env python3
"""Step 2 wrapper: lock the selected model for the AI Studio flow.

PowerShell users often pass paths with backslashes or Korean Won signs. This
wrapper normalizes only the model selector, then delegates to the canonical
prepare_selected_model.py implementation with --select-only.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
PREPARE_SELECTED_MODEL_SCRIPT = ROOT / "scripts" / "04-train-model" / "prepare_selected_model.py"
PREPARE_SELECTED_MODEL_COMMAND = ".opencode/scripts/04-train-model/prepare_selected_model.py"
PATH_SEPARATOR_TRANSLATION = str.maketrans({
    "\\": "/",
    "＼": "/",
    "￦": "/",
    "₩": "/",
})


def normalize_model_selector(value: str) -> str:
    selector = value.strip().strip('"').strip("'")
    if selector.lower() in {"selected", "current", "last", "기존", "현재", "선택"}:
        return selector
    if selector.isdigit():
        return selector
    return re.sub(r"/+", "/", selector.translate(PATH_SEPARATOR_TRANSLATION)).strip("/")


def normalize_argv(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--" and index + 1 < len(argv):
            next_arg = argv[index + 1]
            if next_arg in {"model", "project"}:
                normalized.append(f"--{next_arg}")
                index += 2
                continue
        if arg in {"model", "project"}:
            normalized.append(f"--{arg}")
            index += 1
            continue
        if arg in {"execute", "실행"}:
            index += 1
            continue
        match = re.fullmatch(r"--model(.+)", arg)
        if match and match.group(1) and not match.group(1).startswith(("=", "-")):
            normalized.extend(["--model", match.group(1)])
        else:
            normalized.append(arg)
        index += 1
    return normalized


def load_prepare_module():
    spec = importlib.util.spec_from_file_location("prepare_selected_model_impl", PREPARE_SELECTED_MODEL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load prepare script: {PREPARE_SELECTED_MODEL_COMMAND}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Step 2: select and lock a model for the AI Studio flow.")
    parser.add_argument("model_arg", nargs="?", help="model number or project-relative path")
    parser.add_argument("--project", default=".", help="workspace/model project folder")
    parser.add_argument("--model", help="model number or project-relative path")
    parser.add_argument("--dry-run", action="store_true", help="show the selected model without writing config/config.json")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--verbose", action="store_true", help="print detailed model list and next steps")
    args = parser.parse_args(normalize_argv(sys.argv[1:]))

    raw_model = args.model or args.model_arg
    if not raw_model:
        parser.error("2번 모델 선택에는 --model <번호|경로> 또는 위치 인자 <번호|경로>가 필요합니다.")

    module = load_prepare_module()
    delegated_args = SimpleNamespace(
        project=args.project,
        model=normalize_model_selector(raw_model),
        execute=not args.dry_run,
        force=False,
        select_only=True,
        sync_runtime=False,
        json=args.json,
        verbose=args.verbose,
    )
    report = module.build_report(delegated_args)
    if args.json:
        import json

        from dataclasses import asdict

        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        module.print_report(report, verbose=args.verbose)
    return 1 if report.failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
