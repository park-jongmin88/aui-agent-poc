#!/usr/bin/env python3
"""Compatibility wrapper for Windows/PowerShell model preparation commands.

Accepts common typo forms such as:

    python .opencode/scripts/prepare_select_model.py --project . -- model 2 execute
    python .opencode/scripts/prepare_select_model.py --project . --model2 execute

The canonical implementation lives at:

    .opencode/scripts/04-train-model/prepare_selected_model.py
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREPARE_SELECTED_MODEL_SCRIPT = ROOT / "04-train-model" / "prepare_selected_model.py"
PREPARE_SELECTED_MODEL_COMMAND = ".opencode/scripts/04-train-model/prepare_selected_model.py"
PATH_SEPARATOR_TRANSLATION = str.maketrans({
    "\\": "/",
    "＼": "/",
    "￦": "/",
    "₩": "/",
})


def normalize_path_like(value: str) -> str:
    translated = value.strip().strip('"').strip("'").translate(PATH_SEPARATOR_TRANSLATION)
    return re.sub(r"/+", "/", translated)


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
            normalized.append("--execute")
            index += 1
            continue
        match = re.fullmatch(r"--model(.+)", arg)
        if match and match.group(1) and not match.group(1).startswith(("=", "-")):
            normalized.extend(["--model", normalize_path_like(match.group(1))])
        elif normalized and normalized[-1] in {"--model", "--project"}:
            normalized.append(normalize_path_like(arg))
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
    module = load_prepare_module()
    normalized = normalize_argv(sys.argv[1:])
    if "--model" in normalized and "--select-only" not in normalized and "--sync-runtime" not in normalized:
        normalized.append("--select-only")
    sys.argv = [PREPARE_SELECTED_MODEL_COMMAND, *normalized]
    return int(module.main())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
