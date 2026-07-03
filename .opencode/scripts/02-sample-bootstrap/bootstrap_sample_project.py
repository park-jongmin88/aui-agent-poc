import argparse
import importlib.util
import json
import shutil
import sys
from argparse import Namespace
from dataclasses import asdict, dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from ai_studio_process import format_todo_guide

SAMPLES_DIR = ROOT / "samples"

SAMPLES = {
    "sklearn": {
        "path": "sklearn_sample",
        "label": "sklearn 모델",
        "description": "폐쇄망에서 사용자가 sklearn 모델 코드와 데이터를 넣는 기본 샘플",
    },
    "pytorch": {
        "path": "pytorch_sample",
        "label": "PyTorch 모델",
        "description": "폐쇄망에서 사용자가 PyTorch 모델 코드와 데이터를 넣는 기본 샘플",
    },
    "tensorflow": {
        "path": "tensorflow_sample",
        "label": "TensorFlow/Keras 모델",
        "description": "폐쇄망에서 사용자가 TensorFlow/Keras 모델 코드와 데이터를 넣는 기본 샘플",
    },
}

IGNORED_NAMES = {
    ".DS_Store",
    "__pycache__",
    ".venv",
    "data",
    "venv",
    "env",
    "ai_studio",
    "mlflow.db",
}

GENERATED_ROOT_DIRS = {
    "model",
}

GENERATED_PATH_PREFIXES = {
    ("artifacts", "ai_studio"),
}

REQUIRED_PROJECT_DIRS = [
    "aiu_custom",
    "local_serving",
    "saved_model",
]

SCAFFOLD_ROOT_NAMES = {
    "aiu_custom",
    "config",
    "local_serving",
    "saved_model",
    "requirements.txt",
    "input_example.json",
    "inferencetest.py",
    "config.json",
    "model_config.json",
    "mlflow_config.json",
    "config.yaml",
    "config.yml",
    "run_model.py",
    ".gitkeep",
}

CONFIG_ROOT_FILES = {
    "config.json",
    "model_config.json",
    "mlflow_config.json",
    "config.yaml",
    "config.yml",
}

SELECTED_MODEL_LOCKED_RELATIVE_PATHS = {
    "runtest_2.py",
    "requirements.txt",
    "input_example.json",
    "aiu_custom/model.py",
    "aiu_custom/predict.py",
    "inferencetest.py",
    "config/config.json",
}
SAMPLE_COPY_IGNORE_FILES = {
    "runtest_2.py",
}

IGNORABLE_PROJECT_ROOT_NAMES = {
    ".git",
    ".gitignore",
    ".opencode",
    ".DS_Store",
}


@dataclass
class BootstrapReport:
    project_path: str
    selected_sample: str | None
    sample_source_path: str | None
    target_project_path: str | None
    copy_mode: str
    execute: bool
    project_empty: bool
    copied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    tod_guide: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def list_samples() -> list[dict[str, str]]:
    rows = []
    for key, meta in SAMPLES.items():
        source = SAMPLES_DIR / meta["path"]
        rows.append(
            {
                "key": key,
                "label": meta["label"],
                "description": meta["description"],
                "source_path": str(source),
                "available": str(source.exists()).lower(),
                "required_dirs": str(has_required_dirs(source)).lower(),
            }
        )
    return rows


def has_required_dirs(sample: Path) -> bool:
    return all((sample / name).is_dir() for name in REQUIRED_PROJECT_DIRS)


def is_project_empty(project: Path) -> bool:
    if not project.exists():
        return True
    for child in project.iterdir():
        if child.name not in IGNORABLE_PROJECT_ROOT_NAMES:
            return False
    return True


def should_ignore(path: Path) -> bool:
    parts = path.parts
    if any(part in IGNORED_NAMES for part in parts):
        return True
    if parts and parts[0] in GENERATED_ROOT_DIRS:
        return True
    return any(parts[: len(prefix)] == prefix for prefix in GENERATED_PATH_PREFIXES)


def iter_sample_files(sample: Path, skip_run_model: bool = False):
    for path in sample.rglob("*"):
        relative = path.relative_to(sample)
        if skip_run_model and relative == Path("run_model.py"):
            continue
        if relative.as_posix() in SAMPLE_COPY_IGNORE_FILES:
            continue
        if should_ignore(relative):
            continue
        yield path


def is_scaffold_path(relative: Path) -> bool:
    return bool(relative.parts) and relative.parts[0] in SCAFFOLD_ROOT_NAMES


def append_unique(items: list[str], item: str) -> None:
    if item not in items:
        items.append(item)


def display_path(path: Path) -> str:
    return path.as_posix()


def route_scaffold_relative(relative: Path) -> Path:
    return relative


def copy_file(source: Path, target: Path) -> None:
    # copyfile avoids Windows metadata/permission edge cases that can affect copy2.
    shutil.copyfile(source, target)


def resolve_project_arg(raw_project: str) -> Path:
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


def reference_runtest_path(project: Path) -> Path | None:
    for name in ["runtest.py"]:
        path = project / name
        if path.exists():
            return path
    return None


def selected_model_locked(project: Path) -> bool:
    if (project / "runtest_2.py").is_file():
        return True
    config_path = project / "config" / "config.json"
    if not config_path.is_file():
        return False
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    model = payload.get("model", {}) if isinstance(payload, dict) else {}
    source_path = model.get("model_relative_path") or model.get("runtime_model_path") or model.get("source_path")
    return isinstance(source_path, str) and bool(source_path.strip())


def copy_existing_project_scaffold(sample: Path, project: Path, execute: bool) -> tuple[Path, list[str], list[str]]:
    copied: list[str] = []
    skipped: list[str] = []
    skip_run_model = bool(reference_runtest_path(project)) or any((project / name).exists() for name in ["run_model.py", "train.py"])
    model_locked = selected_model_locked(project)

    for source in iter_sample_files(sample, skip_run_model=skip_run_model):
        relative = source.relative_to(sample)
        if not is_scaffold_path(relative):
            continue

        target_relative = route_scaffold_relative(relative)
        target = project / target_relative
        if source.is_dir():
            if target.exists():
                append_unique(skipped, display_path(target_relative) + "/")
                continue
            if execute:
                target.mkdir(parents=True, exist_ok=True)
            append_unique(copied, display_path(target_relative) + "/")
            continue

        if target.exists():
            if model_locked and target_relative.as_posix() in SELECTED_MODEL_LOCKED_RELATIVE_PATHS:
                append_unique(skipped, display_path(target_relative) + " selected_model_locked")
                continue
            append_unique(skipped, display_path(target_relative))
            continue

        if execute:
            target.parent.mkdir(parents=True, exist_ok=True)
            copy_file(source, target)
        append_unique(copied, display_path(target_relative))

    for name in REQUIRED_PROJECT_DIRS:
        target = project / name
        if execute:
            target.mkdir(parents=True, exist_ok=True)
        entry = f"{name}/"
        if entry not in copied and target.exists():
            append_unique(skipped, entry)
        elif entry not in copied:
            append_unique(copied, entry)

    return project, copied, skipped


def copy_sample(sample: Path, project: Path, force: bool, execute: bool, copy_mode: str) -> tuple[Path, list[str], list[str]]:
    target_root = project / sample.name if copy_mode == "folder" else project
    copied: list[str] = []
    skipped: list[str] = []
    skip_run_model = bool(reference_runtest_path(project) or reference_runtest_path(target_root))
    model_locked = selected_model_locked(target_root)

    if target_root.exists() and copy_mode == "folder" and force and execute:
        shutil.rmtree(target_root)

    for source in iter_sample_files(sample, skip_run_model=skip_run_model):
        relative = source.relative_to(sample)
        target_relative = route_scaffold_relative(relative)
        target = target_root / target_relative
        display_relative = Path(sample.name) / target_relative if copy_mode == "folder" else target_relative

        if source.is_dir():
            if target.exists() and not force:
                skipped.append(display_path(display_relative) + "/")
                continue
            if execute:
                target.mkdir(parents=True, exist_ok=True)
            copied.append(display_path(display_relative) + "/")
            continue

        if target.exists() and not force:
            if model_locked and target_relative.as_posix() in SELECTED_MODEL_LOCKED_RELATIVE_PATHS:
                skipped.append(display_path(display_relative) + " selected_model_locked")
                continue
            skipped.append(display_path(display_relative))
            continue

        if execute:
            target.parent.mkdir(parents=True, exist_ok=True)
            copy_file(source, target)
        copied.append(display_path(display_relative))

    for name in REQUIRED_PROJECT_DIRS:
        target = target_root / name
        display_relative = Path(sample.name) / name if copy_mode == "folder" else Path(name)
        if execute:
            target.mkdir(parents=True, exist_ok=True)
        entry = f"{display_path(display_relative)}/"
        if entry not in copied:
            copied.append(entry)

    return target_root, copied, skipped


def build_tod_guide(target_project_path: Path, runtest_path: Path | None) -> list[str]:
    if runtest_path:
        try:
            entrypoint = runtest_path.relative_to(target_project_path).as_posix()
        except ValueError:
            entrypoint = runtest_path.as_posix()
    else:
        entrypoint = "run_model.py"
    return [
        "1. 환경 검증: python .opencode/scripts/03-environment-check/check_environment.py --project .",
        "2. 샘플 규격 확인/보충: 워크스페이스 루트에 복사된 템플릿 폴더 내부 파일들을 확인한다. 대표 예시: aiu_custom/, local_serving/, saved_model/, requirements.txt, input_example.json",
        f"3. 환경 변수 입력/export: {entrypoint}의 설정 블록 값을 직접 입력하고 실행 시 MLFLOW_*로 export한다.",
        "4. 패키지 설치: requirements.txt 기준으로 내부 http:// PyPI/Nexus 미러를 사용해 설치한다. SSL/HTTPS 인덱스 직접 설치는 사용하지 않는다.",
        f"5. 모델 실행 및 원격 MLflow 기록: python {entrypoint}",
        "6. 산출물 확인: MLflow artifact_path='ai_studio' 아래 ai_studio/code 또는 로컬 ai_studio/metrics, ai_studio/code 생성 여부를 확인한다.",
    ]


def build_next_steps(sample_key: str, target_project_path: Path, runtest_path: Path | None) -> list[str]:
    tod_guide = build_tod_guide(target_project_path, runtest_path)
    return [
        tod_guide[0],
        f"선택 샘플: {sample_key}",
    ]


def main():
    parser = argparse.ArgumentParser(description="Bootstrap one bundled offline model sample folder into a workspace.")
    parser.add_argument("--project", default=".", help="target workspace root")
    parser.add_argument("--sample", choices=sorted(SAMPLES), help="sample key: sklearn, pytorch, tensorflow")
    parser.add_argument("--model", help="existing-model compatibility: delegate to prepare_selected_model.py")
    parser.add_argument("--copy-mode", choices=["folder", "root"], default="root", help="copy sample contents into the workspace root by default; use folder to keep the sample folder name")
    parser.add_argument("--scaffold-existing", action="store_true", help="copy only missing sample-spec scaffold files into an existing model project without overwriting")
    parser.add_argument("--list", action="store_true", help="list selectable samples")
    parser.add_argument("--execute", action="store_true", help="copy files into the workspace")
    parser.add_argument("--force", action="store_true", help="allow overwriting existing files")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    if args.model:
        module_path = ROOT / "scripts" / "04-train-model" / "prepare_selected_model.py"
        spec = importlib.util.spec_from_file_location("prepare_selected_model_impl", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load script: {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        build_selected_model_report = module.build_report
        print_selected_model_report = module.print_report

        delegated_args = Namespace(
            project=args.project,
            model=args.model,
            execute=args.execute,
            force=args.force,
            json=args.json,
        )
        report = build_selected_model_report(delegated_args)
        if args.json:
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        else:
            print("[route] --model은 기존 모델 변환 흐름이므로 prepare_selected_model.py로 처리합니다.")
            print_selected_model_report(report)
        return

    if args.list:
        rows = list_samples()
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for row in rows:
                print(f"{row['key']}: {row['label']} - {row['description']}")
                print(f"  source: {row['source_path']}")
                print(f"  available: {row['available']}")
        return

    if not args.sample:
        raise ValueError("--sample is required unless --list is used")

    project = resolve_project_arg(args.project)
    sample_meta = SAMPLES[args.sample]
    sample_source = SAMPLES_DIR / sample_meta["path"]
    failures: list[str] = []
    copied: list[str] = []
    skipped: list[str] = []
    target_project_path: Path | None = None

    if not sample_source.exists():
        failures.append(f"sample_not_found:{sample_source}")
    elif not has_required_dirs(sample_source):
        failures.append(f"sample_missing_required_dirs:{','.join(REQUIRED_PROJECT_DIRS)}")

    project_empty = is_project_empty(project)
    if project.exists() and not project.is_dir():
        failures.append(f"project_is_not_directory:{project}")
    if not failures:
        if args.execute:
            project.mkdir(parents=True, exist_ok=True)
        try:
            if args.scaffold_existing:
                target_project_path, copied, skipped = copy_existing_project_scaffold(
                    sample_source,
                    project,
                    execute=args.execute,
                )
            else:
                target_project_path, copied, skipped = copy_sample(
                    sample_source,
                    project,
                    force=args.force,
                    execute=args.execute,
                    copy_mode=args.copy_mode,
                )
        except Exception as exc:
            failures.append(str(exc))

    runtest_path = None
    if not failures and target_project_path:
        runtest_path = reference_runtest_path(target_project_path) or reference_runtest_path(project)

    report = BootstrapReport(
        project_path=str(project),
        selected_sample=args.sample,
        sample_source_path=str(sample_source),
        target_project_path=str(target_project_path) if target_project_path else None,
        copy_mode="scaffold_existing" if args.scaffold_existing else args.copy_mode,
        execute=args.execute,
        project_empty=project_empty,
        copied=copied,
        skipped=skipped,
        failures=failures,
        tod_guide=build_tod_guide(target_project_path, runtest_path)
        if not failures and target_project_path
        else [],
        next_steps=build_next_steps(
            args.sample,
            target_project_path,
            runtest_path,
        )
        if not failures and target_project_path
        else [],
    )

    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print("Project: .")
        print(f"Selected sample: {report.selected_sample}")
        print(f"Sample source: {Path(report.sample_source_path).name}")
        print(f"Target project path: {'.' if report.target_project_path else 'not prepared'}")
        print(f"Copy mode: {report.copy_mode}")
        print(f"Project empty: {report.project_empty}")
        print(f"Execute: {report.execute}")
        print(f"Copied entries: {len(report.copied)}")
        if report.skipped:
            print("Skipped existing files:")
            for item in report.skipped:
                print(f"- {item}")
        if report.failures:
            print("Failures:")
            for failure in report.failures:
                print(f"- {failure}")
        if report.tod_guide:
            print(format_todo_guide(("샘플 흐름", "샘플 선택 완료", "사용자 선택", "사용자 선택", "사용자 선택", "사용자 선택", "사용자 선택")))
        if report.next_steps:
            print("Next steps:")
            for step in report.next_steps:
                print(f"- {step}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
