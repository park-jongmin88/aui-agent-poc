import argparse
import ast
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from ai_studio_process import AI_STUDIO_PROCESS_STEPS

SAMPLES_DIR = ROOT / "samples"
PROJECT_PREPARE_SELECTED_MODEL_SCRIPT = Path(".opencode") / "scripts" / "04-train-model" / "prepare_selected_model.py"
PS_BOOTSTRAP_SKLEARN_COMMAND = r"python .opencode/scripts/02-sample-bootstrap/bootstrap_sample_project.py --project . --sample sklearn --execute"
PS_PREPARE_MODEL_COMMAND = r"python .opencode/scripts/02-model-select/select_model.py --project . --model <번호 또는 상대경로>"
SAMPLE_OPTIONS = ["sklearn", "pytorch", "tensorflow"]
SAMPLE_PROJECT_NAMES = {f"{name}_sample" for name in SAMPLE_OPTIONS}
ENTRYPOINTS = [
    "runtest_2.py",
    "runtest.py",
    "run_test.py",
    "train.py",
    "run_model.py",
    "run.py",
    "main.py",
    "app.py",
    "scripts/train.py",
]
REQUIRED_DIRS = ["aiu_custom", "local_serving", "saved_model"]
ARTIFACT_DIRS = ["saved_model", "model", "artifacts"]
MLFLOW_OUTPUT_DIRS = {"metrics", "params", "artifacts", "tags", "code"}
ARTIFACT_SUFFIXES = {".pkl", ".joblib", ".pt", ".pth", ".h5", ".keras", ".onnx", ".safetensors", ".bst", ".ubj"}
AI_STUDIO_ENV_KEYS = [
    "mlflow_tracking_uri",
    "mlflow_tracking_username",
    "mlflow_tracking_password",
    "mlflow_experiment_name",
    "mlflow_register_model_name",
]
ENV_SETTING_FILE_NAMES = [".env"]
AUTO_DEFAULT_SETTING_KEYS = {
    "mlflow_experiment_name",
    "mlflow_register_model_name",
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
MODEL_SETTING_FILES = [
    "runtest_2.py",
    "runtest.py",
    "run_test.py",
    "run_model.py",
]
MODEL_SCAN_SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".opencode",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "ai_studio",
    "build",
    "dist",
    "env",
    "node_modules",
    "venv",
}

SETTING_ALIASES = {
    "mlflow_tracking_uri": {
        "mlflow_tracking_uri",
        "tracking_uri",
        "MLFLOW_TRACKING_URI",
    },
    "mlflow_tracking_username": {
        "mlflow_tracking_username",
        "tracking_username",
        "mlflow_username",
        "username",
        "MLFLOW_TRACKING_USERNAME",
    },
    "mlflow_tracking_password": {
        "mlflow_tracking_password",
        "tracking_password",
        "mlflow_password",
        "password",
        "MLFLOW_TRACKING_PASSWORD",
    },
    "mlflow_experiment_name": {
        "mlflow_experiment_name",
        "experiment_name",
        "MLFLOW_EXPERIMENT_NAME",
    },
    "mlflow_register_model_name": {
        "mlflow_register_model_name",
        "register_model_name",
        "registered_model_name",
        "MLFLOW_REGISTER_MODEL_NAME",
    },
}

ALIAS_TO_SETTING = {
    alias: setting_key
    for setting_key, aliases in SETTING_ALIASES.items()
    for alias in aliases
}


@dataclass
class EnvVarStatus:
    name: str
    status: str


@dataclass
class TrainingReport:
    project_path: str
    model_found: bool
    selected_sample: str | None
    work_path: str
    entrypoint: str | None
    command: list[str]
    executed: bool
    return_code: int | None
    artifacts: list[str] = field(default_factory=list)
    preflight: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    process_checklist: list[EnvVarStatus] = field(default_factory=list)


def has_model_project(project: Path) -> bool:
    if is_opencode_sample_source(project):
        return False
    markers = [
        "runtest_2.py",
        "runtest.py",
        "run_test.py",
        "train.py",
        "run_model.py",
        "predict.py",
        "input_example.json",
        "MLmodel",
    ]
    if any((project / name).exists() for name in markers):
        return True
    if find_entrypoint_candidates(project):
        return True
    if any((project / name).exists() for name in ARTIFACT_DIRS):
        return True
    if find_artifacts(project):
        return True
    return False


def is_sample_project(project: Path) -> bool:
    return project.name in SAMPLE_PROJECT_NAMES


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


def find_entrypoint(project: Path) -> Path | None:
    candidates = find_entrypoint_candidates(project)
    return candidates[0] if candidates else None


def find_entrypoint_candidates(project: Path) -> list[Path]:
    found = []
    for name in ENTRYPOINTS:
        candidate = project / name
        if candidate.exists() and candidate.is_file():
            found.append(candidate)
    found.extend(sorted(path for path in project.glob("*.py") if path.is_file()))
    return unique_paths(found)


def resolve_entrypoint(project: Path, entrypoint_name: str | None) -> tuple[Path | None, list[Path], str | None]:
    candidates = find_entrypoint_candidates(project)
    if entrypoint_name:
        candidate = (project / entrypoint_name).resolve()
        try:
            candidate.relative_to(project)
        except ValueError:
            return None, candidates, "entrypoint_outside_project"
        if not candidate.exists() or not candidate.is_file():
            return None, candidates, f"entrypoint_not_found:{entrypoint_name}"
        return candidate, candidates, None
    return find_entrypoint(project), candidates, None


def project_relative_path(path: Path, project: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.name


def find_workspace_root(project: Path) -> Path | None:
    for candidate in [project, *project.parents]:
        if (candidate / PROJECT_PREPARE_SELECTED_MODEL_SCRIPT).is_file():
            return candidate
    return None


def build_command(python_bin: str, entrypoint: Path, prepare_only: bool, project: Path) -> list[str]:
    cmd = ["python", project_relative_path(entrypoint, project)]
    if prepare_only and entrypoint.name in {"run_model.py", "register_model.py"}:
        cmd.append("--prepare-only")
    return cmd


def iter_project_files(project: Path):
    for root, dirs, files in os.walk(project):
        root_path = Path(root)
        try:
            relative_parts = root_path.relative_to(project).parts
        except ValueError:
            dirs[:] = []
            continue
        if any(part in MODEL_SCAN_SKIP_DIRS for part in relative_parts):
            dirs[:] = []
            continue
        dirs[:] = [dirname for dirname in dirs if dirname not in MODEL_SCAN_SKIP_DIRS]
        for filename in files:
            yield root_path / filename


def find_artifacts(project: Path) -> list[str]:
    found: list[str] = []
    for name in ARTIFACT_DIRS:
        path = project / name
        if path.is_file() or (path.is_dir() and any(child.name != ".gitkeep" for child in path.iterdir())):
            found.append(str(path))
    for ai_studio in [project / "ai_studio"]:
        if not ai_studio.exists():
            continue
        for path in ai_studio.rglob("*"):
            if path.name == "meta.yaml":
                continue
            if path.is_file() and any(part in MLFLOW_OUTPUT_DIRS for part in path.relative_to(ai_studio).parts):
                found.append(str(path))
    for path in iter_project_files(project):
        if path.name == "model_info.json":
            continue
        if path.is_file() and (path.suffix.lower() in ARTIFACT_SUFFIXES or path.name in {"MLmodel", "python_model.pkl"}):
            found.append(str(path))
    return sorted(set(found))


def missing_required_dirs(project: Path) -> list[str]:
    return [name for name in REQUIRED_DIRS if not (project / name).is_dir()]


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_setting_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in parse_env_file(path).items():
        setting_key = ALIAS_TO_SETTING.get(key)
        if setting_key is not None:
            values[setting_key] = value
    return values


def setting_env_file(project: Path) -> Path:
    for name in ENV_SETTING_FILE_NAMES:
        path = project / name
        if path.exists():
            return path
    return project / ".env"


def literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript):
        return literal_string(node.slice)
    return None


def record_setting(values: dict[str, str], key: str | None, value: str | None) -> None:
    if key is None or value is None:
        return
    setting_key = ALIAS_TO_SETTING.get(key)
    if setting_key and value:
        values[setting_key] = value


def parse_python_string_assignments(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return values
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = literal_string(node.value)
            for target in node.targets:
                record_setting(values, target_name(target), value)
        elif isinstance(node, ast.AnnAssign):
            record_setting(values, target_name(node.target), literal_string(node.value))
        elif isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values):
                record_setting(values, literal_string(key_node), literal_string(value_node))
    return values


def find_model_settings(project: Path, entrypoint: Path | None = None) -> dict[str, str]:
    if entrypoint is not None:
        values = parse_python_string_assignments(entrypoint)
        if values:
            return values
    for name in MODEL_SETTING_FILES:
        path = project / name
        if path.exists():
            return parse_python_string_assignments(path)
    return {}


def validate_mlflow_tracking_url(value: str) -> str | None:
    tracking_uri = str(value or "").strip()
    if not tracking_uri:
        return None

    lowered = tracking_uri.lower()
    if lowered.startswith(("sqlite:", "file:")):
        return "invalid_remote_tracking_uri:sqlite_or_file"
    if not lowered.startswith(("http://", "https://")):
        return "invalid_remote_tracking_uri:scheme"

    parsed = urlparse(tracking_uri)
    hostname = (parsed.hostname or "").lower()
    if hostname in {"localhost", "0.0.0.0", "::1"} or hostname.startswith("127."):
        return "invalid_remote_tracking_uri:local_address"
    return None


def missing_ai_studio_env(project: Path, entrypoint: Path | None = None) -> list[str]:
    path = setting_env_file(project)
    values = parse_setting_env_file(path)
    missing = []
    if not path.exists():
        missing.append(".env")
    if not values:
        missing.append(".env_settings")
    for key in AI_STUDIO_ENV_KEYS:
        if key in AUTO_DEFAULT_SETTING_KEYS:
            continue
        if key not in values or values[key] == "":
            missing.append(key)
    return missing


def remote_tracking_uri_failure(project: Path, entrypoint: Path | None = None) -> str | None:
    values = parse_setting_env_file(setting_env_file(project))
    tracking_uri = str(values.get("mlflow_tracking_uri") or "").strip()
    return validate_mlflow_tracking_url(tracking_uri)


def checklist_status(condition: bool) -> str:
    return "done" if condition else "pending"


def is_filesystem_root(path: Path) -> bool:
    return path.parent == path


def is_opencode_sample_source(path: Path) -> bool:
    parts = path.resolve().parts
    if ".opencode" in parts:
        return True
    for index, part in enumerate(parts[:-1]):
        if part == ".opencode" and parts[index + 1] in {"sample", "samples"}:
            return True
    return False


def run_command(cmd: list[str], cwd: Path) -> int:
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def is_runtest_2_entrypoint(entrypoint: Path | None, project: Path) -> bool:
    if entrypoint is None:
        return False
    try:
        return entrypoint.resolve().relative_to(project.resolve()).as_posix() == "runtest_2.py"
    except ValueError:
        return entrypoint.name == "runtest_2.py"


def sync_selected_model_runtime_before_registration(project: Path, python_bin: str) -> tuple[list[str], list[str]]:
    workspace_root = find_workspace_root(project)
    if workspace_root is None:
        return [], [f"preflight_script_missing:{PROJECT_PREPARE_SELECTED_MODEL_SCRIPT.as_posix()}"]
    cmd = [
        python_bin,
        PROJECT_PREPARE_SELECTED_MODEL_SCRIPT.as_posix(),
        "--project",
        ".",
        "--sync-runtime",
        "--execute",
    ]
    result = subprocess.run(
        cmd,
        cwd=workspace_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        detail_lines = (result.stderr or result.stdout or "").strip().splitlines()
        detail = detail_lines[-1] if detail_lines else "unknown"
        return [], [f"selected_model_runtime_sync_failed:{detail}"]
    return [
        "5번 실행 전 선택 모델 기준 런타임 재검증/변환 완료",
        "runtest_2.py, aiu_custom/, local_serving/, config/, input_example.json, requirements.txt 동기화",
    ], []


def main():
    parser = argparse.ArgumentParser(description="Run local training for an existing project after .env checks.")
    parser.add_argument("--project", default=".", help="user-specified model project folder")
    parser.add_argument("--python", default="python", help="Python interpreter to use")
    parser.add_argument("--execute", action="store_true", help="actually run the selected command")
    parser.add_argument("--entrypoint", help="training/model creation file confirmed by the user, relative to --project")
    parser.add_argument("--force-sample", action="store_true", help="deprecated; use bootstrap_sample_project.py for sample folder copy")
    parser.add_argument("--prepare-only", action="store_true", help="prefer prepare-only mode when supported")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    project = resolve_workspace_project(args.project)
    if not project.exists():
        raise FileNotFoundError(f"project folder not found: {project}")
    if is_filesystem_root(project):
        raise ValueError("drive/root scan is not allowed. 선택한 워크스페이스 루트로 이동한 뒤 --project . 로 실행하세요.")
    if is_opencode_sample_source(project):
        raise ValueError(".opencode/는 번들 스킬 원본이라 실행/분석 대상이 아닙니다. 실제 모델 프로젝트 폴더를 --project로 지정하세요.")

    failures: list[str] = []
    next_steps: list[str] = []
    preflight: list[str] = []
    selected_sample = None
    model_found = has_model_project(project)
    work_path = project

    if not model_found:
        failures.append("model_not_found")
        failures.append("sample_bootstrap_required: choose one of sklearn, pytorch, tensorflow and copy the sample folder first")
        next_steps.append(PS_BOOTSTRAP_SKLEARN_COMMAND)

    entrypoint = None
    entrypoint_candidates: list[Path] = []
    cmd = []
    if model_found:
        entrypoint, entrypoint_candidates, entrypoint_error = resolve_entrypoint(work_path, args.entrypoint)
        if entrypoint_error:
            failures.append(entrypoint_error)
        if entrypoint is None:
            failures.append("missing_train_entrypoint")
            if entrypoint_error == "entrypoint_not_found":
                next_steps.append("실행 파일을 찾지 못했습니다. 사용자가 실제 학습/모델 생성 Python 파일을 프로젝트에 직접 넣어주세요.")
                next_steps.append("파일을 넣은 뒤 --entrypoint <file>로 다시 실행하세요.")
            elif entrypoint_error and entrypoint_error.startswith("entrypoint_not_found:"):
                next_steps.append("지정한 실행 파일이 없습니다. 파일명을 확인하거나 해당 Python 파일을 프로젝트에 직접 넣어주세요.")
            else:
                next_steps.append("실제 사용하는 Python 실행 파일명을 알려주세요. 예: --entrypoint train.py")
            if entrypoint_candidates:
                next_steps.append("Entrypoint candidates: " + ", ".join(str(path.relative_to(work_path)) for path in entrypoint_candidates))
        else:
            cmd = build_command(args.python, entrypoint, args.prepare_only, work_path)

    if args.execute and model_found and entrypoint is not None and is_runtest_2_entrypoint(entrypoint, work_path):
        sync_messages, sync_failures = sync_selected_model_runtime_before_registration(work_path, args.python)
        preflight.extend(sync_messages)
        if sync_failures:
            failures.extend(sync_failures)
            next_steps.append("먼저 모델 선택 단계로 돌아가 선택 모델을 다시 준비하세요.")
            next_steps.append(PS_PREPARE_MODEL_COMMAND)

    missing_env = missing_ai_studio_env(work_path, entrypoint)
    remote_uri_failure = remote_tracking_uri_failure(work_path, entrypoint)

    return_code = None
    if args.execute and cmd and any(failure.startswith("selected_model_runtime_sync_failed") for failure in failures):
        next_steps.append("런타임 변환 실패로 원격 MLflow 등록 실행을 중단했습니다.")
    elif args.execute and cmd and remote_uri_failure:
        failures.append(remote_uri_failure)
        next_steps.append("5번 원격 MLflow 등록 실행에는 원격 MLflow URL이 필요합니다.")
        next_steps.append(".env의 mlflow_tracking_uri에 원격 http:// 또는 https:// URI를 직접 입력하세요.")
        next_steps.append("localhost, 127.0.0.1, 0.0.0.0, file://, sqlite: tracking URI는 5번에서 사용할 수 없습니다.")
    elif args.execute and cmd and missing_env:
        failures.append("execution_blocked_missing_env")
        next_steps.append("MLflow 필수 환경변수가 비어 있어 실행을 중단했습니다.")
        next_steps.append(
            ".env에 mlflow_tracking_uri, mlflow_tracking_username, mlflow_tracking_password를 직접 입력한 뒤 다시 실행하세요."
        )
    elif args.execute and cmd:
        return_code = run_command(cmd, cwd=work_path)
        if return_code != 0:
            failures.append("runtime_error")
    elif cmd:
        next_steps.append("Run again with --execute to start training or model export.")

    artifacts = find_artifacts(work_path)
    missing_dirs = missing_required_dirs(work_path)
    if missing_dirs:
        failures.extend(f"missing_required_dir:{name}" for name in missing_dirs)
    if missing_env:
        failures.extend(f"missing_env:{name}" for name in missing_env)
    if args.execute and return_code == 0 and not artifacts:
        failures.append("artifact_not_created")

    existing_model_flow = model_found and not is_sample_project(work_path)
    if existing_model_flow:
        mlflow_run_status = "blocked" if (missing_env or remote_uri_failure) else ("done" if args.execute and return_code == 0 else "사용자 선택")
        step_statuses = (
            "done" if artifacts else "needs_input",
            "done" if artifacts else "needs_input",
            "done" if not (missing_env or remote_uri_failure) else "needs_input",
            "done" if (work_path / "runtest_2.py").exists() and (work_path / "requirements.txt").exists() else "pending",
            mlflow_run_status,
            "사용자 선택",
            "needed" if failures else "사용자 선택",
        )
        process_checklist = [
            EnvVarStatus(f"{index}. {title}", status)
            for index, (title, status) in enumerate(zip(AI_STUDIO_PROCESS_STEPS, step_statuses), start=1)
        ]
    else:
        mlflow_run_status = "blocked" if (missing_env or remote_uri_failure) else ("done" if args.execute and return_code == 0 else "pending")
        process_checklist = [
            EnvVarStatus("1. 환경 검증", "done" if not missing_env else "needs_input"),
            EnvVarStatus("2. 샘플 규격 확인/보충", "done" if not missing_dirs else "needs_scaffold"),
            EnvVarStatus("3. 환경 변수 입력/export", "done" if not missing_env else "needs_input"),
            EnvVarStatus("4. 패키지 설치", "manual_check"),
            EnvVarStatus("5. 모델 실행 및 원격 MLflow 기록", mlflow_run_status),
            EnvVarStatus("6. 산출물 확인", "done" if artifacts else "pending"),
        ]

    report = TrainingReport(
        project_path=str(project),
        model_found=model_found,
        selected_sample=selected_sample,
        work_path=str(work_path),
        entrypoint=str(entrypoint) if entrypoint else None,
        command=cmd,
        executed=args.execute,
        return_code=return_code,
        artifacts=artifacts,
        preflight=preflight,
        failures=failures,
        next_steps=next_steps,
        process_checklist=process_checklist,
    )

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print("Project: .")
        print("Work path: .")
        print(f"Model found: {report.model_found}")
        print(f"Selected sample: {report.selected_sample or 'none'}")
        print(f"Entrypoint: {report.entrypoint or 'missing'}")
        print(f"Command: {' '.join(report.command) if report.command else 'none'}")
        print(f"Executed: {report.executed}")
        print(f"Return code: {report.return_code}")
        if report.preflight:
            print("Preflight:")
            for item in report.preflight:
                print(f"- {item}")
        print("Process checklist:")
        for item in report.process_checklist:
            print(f"- {item.name}: {item.status}")
        print("Metrics and artifacts:")
        for artifact in report.artifacts:
            print(f"- {artifact}")
        if report.failures:
            print("Failures:")
            for failure in report.failures:
                print(f"- {failure}")
        if report.next_steps:
            print("Next steps:")
            for step in report.next_steps:
                print(f"- {step}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
