#!/usr/bin/env python3
"""Backward-compatible workspace analysis entrypoint.

Older launch guides call this file directly. Keep it as a thin wrapper around
the current project-analysis script so closed-network Windows setups do not fail
with "file not found".
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "01-project-analyze" / "validate_mlflow_project.py"


def normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    first = argv[0]
    if first.startswith("-"):
        return argv
    return ["--project", first, *argv[1:]]


if __name__ == "__main__":
    sys.argv[0] = str(TARGET)
    sys.argv[1:] = normalize_argv(sys.argv[1:])
    runpy.run_path(str(TARGET), run_name="__main__")
