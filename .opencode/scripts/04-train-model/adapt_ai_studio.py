#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path


START = "# >>> AI Studio MLflow adapter >>>"
END = "# <<< AI Studio MLflow adapter <<<"

REQUIRED_DIRS = ["aiu_custom", "local_serving", "saved_model"]
REQUIRED_FILES = ["input_example.json", "requirements.txt"]
ENTRYPOINT_HINTS = [
                        "runtest.py",
    "run_test.py",
    "run_model.py",
    "run.py",
    "train.py",
    "main.py",
    "app.py",
    "scripts/train.py",
]

FRAMEWORK_RULES = [
    ("qwen", ["qwen", "AutoModelForCausalLM", "AutoTokenizer"]),
    ("huggingface", ["transformers", "AutoModel", "AutoTokenizer", "pipeline("]),
    ("pytorch", ["import torch", "from torch", "torch.", ".pt", ".pth"]),
    ("tensorflow", ["tensorflow", "keras", ".keras", ".h5", "SavedModel"]),
    ("sklearn", ["sklearn", "scikit-learn", "joblib", ".pkl"]),
    ("xgboost", ["xgboost", ".bst", ".ubj"]),
    ("lightgbm", ["lightgbm"]),
]

REQUIREMENT_BY_FRAMEWORK = {
    "qwen": ["mlflow", "transformers", "torch", "accelerate", "safetensors"],
    "huggingface": ["mlflow", "transformers", "torch", "safetensors"],
    "pytorch": ["mlflow", "torch"],
    "tensorflow": ["mlflow", "tensorflow"],
    "sklearn": ["mlflow", "scikit-learn", "joblib"],
    "xgboost": ["mlflow", "xgboost"],
    "lightgbm": ["mlflow", "lightgbm"],
    "unknown": ["mlflow"],
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
class AdaptReport:
    project_path: str
    entrypoint: str | None
    framework: str
    execute: bool
    planned_changes: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def unique_paths(paths: list[Path]) -> list[Path]:
    unique = []
    seen = set()
    for path in paths:
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def find_entrypoints(project: Path) -> list[Path]:
    found = []
    for name in ENTRYPOINT_HINTS:
        candidate = project / name
        if candidate.is_file():
            found.append(candidate)
    found.extend(path for path in project.glob("*.py") if path.is_file())
    return unique_paths(found)


def resolve_entrypoint(project: Path, entrypoint_name: str | None) -> tuple[Path | None, list[Path], str | None]:
    candidates = find_entrypoints(project)
    if entrypoint_name:
        candidate = Path(entrypoint_name)
        path = candidate if candidate.is_absolute() else project / candidate
        path = path.resolve()
        try:
            path.relative_to(project)
        except ValueError:
            return None, candidates, "entrypoint_outside_project"
        if not path.exists():
            return None, candidates, f"entrypoint_not_found:{entrypoint_name}"
        return path, candidates, None
    if len(candidates) == 1:
        return candidates[0], candidates, None
    if not candidates:
        return None, candidates, "entrypoint_not_found"
    return None, candidates, "entrypoint_ambiguous"


def detect_framework(project: Path, entrypoint: Path | None) -> str:
    texts = []
    if entrypoint is not None:
        texts.append(read_text(entrypoint))
    requirements = project / "requirements.txt"
    if requirements.exists():
        texts.append(read_text(requirements))
    joined = "\n".join(texts)
    lowered = joined.lower()
    for framework, hints in FRAMEWORK_RULES:
        for hint in hints:
            if hint.lower() in lowered:
                return framework
    return "unknown"


def infer_import_packages(entrypoint: Path | None) -> list[str]:
    if entrypoint is None or not entrypoint.exists():
        return []
    try:
        tree = ast.parse(read_text(entrypoint))
    except SyntaxError:
        return []
    packages = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            packages.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            packages.append(node.module.split(".")[0])
    ignored = {"os", "sys", "json", "pathlib", "typing", "logging", "io", "time", "math", "random", "tempfile"}
    return sorted({name for name in packages if name not in ignored and not name.startswith("_")})


def insertion_index(lines: list[str]) -> int:
    index = 0
    if lines and lines[0].startswith("#!"):
        index = 1
    while index < len(lines) and (not lines[index].strip() or lines[index].startswith("#")):
        index += 1
    if index < len(lines) and lines[index].lstrip().startswith(('"""', "'''")):
        quote = lines[index].lstrip()[:3]
        index += 1
        while index < len(lines):
            if quote in lines[index]:
                index += 1
                break
            index += 1
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("from __future__ import"):
            index += 1
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        break
    return index


def adapter_block(framework: str) -> str:
    return f'''
{START}
# This block is intentionally generic. Keep model-specific training code below
# unchanged, then call/use these helpers where the model is saved or logged.
import json as _ai_studio_json
import os as _ai_studio_os
from pathlib import Path as _AIStudioPath

AI_STUDIO_PROJECT_DIR = _AIStudioPath(__file__).resolve().parent
AI_STUDIO_DIR = AI_STUDIO_PROJECT_DIR / "ai_studio"
AI_STUDIO_CODE_DIR = AI_STUDIO_DIR / "code"
AI_STUDIO_METRICS_DIR = AI_STUDIO_DIR / "metrics"
AI_STUDIO_TRACKING_DIR = AI_STUDIO_DIR / "tracking"

# 사용자가 직접 입력합니다. password 값은 출력하지 않습니다.
mlflow_tracking_uri = globals().get("mlflow_tracking_uri", "")
mlflow_tracking_username = globals().get("mlflow_tracking_username", "")
mlflow_tracking_password = globals().get("mlflow_tracking_password", "")
mlflow_experiment_name = globals().get("mlflow_experiment_name", "{framework}")
mlflow_register_model_name = globals().get("mlflow_register_model_name", "{framework}_model")


def export_ai_studio_mlflow_env() -> None:
    if not mlflow_tracking_uri:
        raise ValueError("mlflow_tracking_uri_required: set remote MLflow tracking URL before deployment")
    exports = {{
        "MLFLOW_TRACKING_URI": mlflow_tracking_uri,
        "MLFLOW_TRACKING_USERNAME": mlflow_tracking_username,
        "MLFLOW_TRACKING_PASSWORD": mlflow_tracking_password,
        "MLFLOW_EXPERIMENT_NAME": mlflow_experiment_name,
        "MLFLOW_REGISTER_MODEL_NAME": mlflow_register_model_name,
    }}
    for name, value in exports.items():
        if value:
            _ai_studio_os.environ[name] = value


def ensure_ai_studio_dirs() -> None:
    AI_STUDIO_CODE_DIR.mkdir(parents=True, exist_ok=True)
    AI_STUDIO_METRICS_DIR.mkdir(parents=True, exist_ok=True)


def write_ai_studio_summary(payload: dict | None = None) -> _AIStudioPath:
    ensure_ai_studio_dirs()
    summary_path = AI_STUDIO_CODE_DIR / "training_summary.json"
    summary_path.write_text(
        _ai_studio_json.dumps(payload or {{"framework": "{framework}", "status": "completed"}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary_path


def log_ai_studio_tree_to_mlflow(root: _AIStudioPath, artifact_path: str) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative_parent = path.parent.relative_to(root).as_posix()
            target_path = artifact_path if relative_parent == "." else f"{{artifact_path}}/{{relative_parent}}"
            mlflow.log_artifact(str(path), artifact_path=target_path)


def log_ai_studio_artifacts_to_mlflow() -> None:
    try:
        import mlflow
    except Exception as exc:
        print(f"MLflow import failed; local ai_studio outputs are available. reason={{exc}}")
        return
    export_ai_studio_mlflow_env()
    try:
        mlflow.set_tracking_uri(_ai_studio_os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment(mlflow_experiment_name)
        with mlflow.start_run(run_name=mlflow_register_model_name):
            log_ai_studio_tree_to_mlflow(AI_STUDIO_CODE_DIR, "ai_studio/code")
            log_ai_studio_tree_to_mlflow(AI_STUDIO_METRICS_DIR, "ai_studio/metrics")
    except Exception as exc:
        print(f"MLflow logging failed; local ai_studio outputs are available. reason={{exc}}")


export_ai_studio_mlflow_env()
ensure_ai_studio_dirs()
{END}
'''.strip()


def model_wrapper_template(framework: str) -> str:
    return f'''"""AI Studio pyfunc wrapper template.

Keep the model-specific loading and predict logic here. This file is created
only when missing; it is not meant to overwrite a user's existing wrapper.
"""


class ModelWrapper:
    framework = "{framework}"

    def __init__(self):
        self.model = None

    def load_context(self, context):
        # TODO: load model artifacts from context.artifacts or saved_model/.
        return None

    def predict(self, context, model_input):
        # TODO: replace with model-specific inference logic.
        return model_input
'''


def local_serving_template() -> str:
    return '''import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        body = json.dumps({"received": json.loads(payload) if payload else {}}).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
'''


def write_if_missing(path: Path, text: str, execute: bool, changed: list[str], skipped: list[str]) -> None:
    if path.exists():
        skipped.append(f"exists: {path.name if path.parent == path.parent.parent else path.as_posix()}")
        return
    if execute:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    changed.append(path.as_posix())


def adapt_entrypoint(entrypoint: Path, framework: str, execute: bool, force: bool, changed: list[str], skipped: list[str]) -> None:
    text = read_text(entrypoint)
    if START in text and END in text and not force:
        skipped.append(f"adapter_exists: {entrypoint}")
        return
    block = adapter_block(framework)
    if START in text and END in text and force:
        next_text = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.DOTALL)
    else:
        lines = text.splitlines()
        index = insertion_index(lines)
        lines[index:index] = ["", block, ""]
        next_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    if execute:
        backup = entrypoint.with_suffix(entrypoint.suffix + ".ai_studio.bak")
        if not backup.exists():
            shutil.copyfile(entrypoint, backup)
            changed.append(backup.as_posix())
        entrypoint.write_text(next_text, encoding="utf-8")
    changed.append(entrypoint.as_posix())


def build_report(project: Path, entrypoint_arg: str | None, sample: str, execute: bool, force: bool) -> AdaptReport:
    entrypoint, candidates, error = resolve_entrypoint(project, entrypoint_arg)
    framework = detect_framework(project, entrypoint)
    report = AdaptReport(
        project_path=str(project),
        entrypoint=str(entrypoint) if entrypoint else None,
        framework=framework,
        execute=execute,
    )

    if error:
        report.failures.append(error)
        if candidates:
            report.warnings.append("entrypoint candidates: " + ", ".join(rel(path, project) for path in candidates))
        if error == "entrypoint_not_found":
            report.next_steps.append("실행 파일을 찾지 못했습니다. 사용자가 실제 학습/모델 생성 Python 파일을 프로젝트에 직접 넣어주세요.")
            report.next_steps.append("파일을 넣은 뒤 --entrypoint <file>로 다시 실행하세요.")
        elif error == "entrypoint_ambiguous":
            report.next_steps.append("실행 파일 후보가 여러 개입니다. 사용자가 실제 사용하는 파일명을 직접 지정해야 합니다.")
            report.next_steps.append("예: python .opencode/scripts/04-train-model/adapt_ai_studio.py --project . --entrypoint run.py")
        elif error.startswith("entrypoint_not_found:"):
            report.next_steps.append("지정한 실행 파일이 없습니다. 파일명을 확인하거나 해당 Python 파일을 프로젝트에 직접 넣어주세요.")
        else:
            report.next_steps.append("실제 학습/모델 생성 파일을 --entrypoint <file>로 지정하세요.")
        return report

    assert entrypoint is not None
    imports = infer_import_packages(entrypoint)
    required_packages = sorted(set(REQUIREMENT_BY_FRAMEWORK.get(framework, ["mlflow"]) + imports))
    report.planned_changes.extend(
        [
            f"adapt_entrypoint: {rel(entrypoint, project)}",
            "create_if_missing: aiu_custom/predict.py",
            "create_if_missing: local_serving/serve.py",
            "create_if_missing: saved_model/",
            "create_if_missing: input_example.json",
            "create_or_extend_if_missing: requirements.txt",
        ]
    )

    if not execute:
        report.next_steps.append("검토 후 실제 수정하려면 같은 명령에 --execute를 추가하세요.")
        return report

    changed = report.changed_files
    skipped = report.skipped
    for dirname in REQUIRED_DIRS:
        path = project / dirname
        if path.exists():
            skipped.append(f"exists: {dirname}/")
        else:
            path.mkdir(parents=True, exist_ok=True)
            changed.append(path.as_posix())

    write_if_missing(project / "aiu_custom" / "predict.py", model_wrapper_template(framework), execute, changed, skipped)
    write_if_missing(project / "local_serving" / "serve.py", local_serving_template(), execute, changed, skipped)
    write_if_missing(project / "input_example.json", '{\n  "inputs": []\n}\n', execute, changed, skipped)

    requirements = project / "requirements.txt"
    if requirements.exists():
        existing = read_text(requirements)
        additions = [pkg for pkg in required_packages if pkg.lower() not in existing.lower()]
        if additions:
            requirements.write_text(existing.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")
            changed.append(requirements.as_posix())
        else:
            skipped.append("requirements already covers inferred packages")
    else:
        requirements.write_text("\n".join(required_packages) + "\n", encoding="utf-8")
        changed.append(requirements.as_posix())

    adapt_entrypoint(entrypoint, framework, execute, force, changed, skipped)
    report.next_steps.extend(
        [
            "수정된 entrypoint의 TODO와 MLflow 설정값 5개를 확인하세요.",
            f"python .opencode/scripts/qa-maintenance/doctor.py --workspace . --project . --entrypoint {rel(entrypoint, project)}",
            f"python .opencode/scripts/03-environment-check/check_environment.py --project . --entrypoint {rel(entrypoint, project)}",
        ]
    )
    return report


def print_text(report: AdaptReport) -> None:
    print("AI Studio Adapter")
    print("Project: .")
    print(f"Entrypoint: {report.entrypoint or 'missing'}")
    print(f"Framework: {report.framework}")
    print(f"Execute: {report.execute}")
    if report.planned_changes:
        print("\nPlanned changes:")
        for item in report.planned_changes:
            print(f"- {item}")
    if report.changed_files:
        print("\nChanged files:")
        for item in report.changed_files:
            print(f"- {item}")
    if report.skipped:
        print("\nSkipped:")
        for item in report.skipped:
            print(f"- {item}")
    if report.warnings:
        print("\nWarnings:")
        for item in report.warnings:
            print(f"- {item}")
    if report.failures:
        print("\nFailures:")
        for item in report.failures:
            print(f"- {item}")
    if report.next_steps:
        print("\nNext steps:")
        for item in report.next_steps:
            print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Adapt an arbitrary Python model entrypoint for AI Studio/MLflow workflow.")
    parser.add_argument("--project", default=".", help="model project folder")
    parser.add_argument("--entrypoint", help="actual local training/model creation file, such as run.py")
    parser.add_argument("--sample", choices=["sklearn", "pytorch", "tensorflow"], default="pytorch", help="scaffold hint")
    parser.add_argument("--execute", action="store_true", help="apply changes; default is dry-run")
    parser.add_argument("--force", action="store_true", help="replace existing adapter block")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    project = resolve_workspace_project(args.project)
    if not project.exists():
        raise SystemExit(f"project not found: {project}")
    report = build_report(project, args.entrypoint, args.sample, args.execute, args.force)
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
