#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat


SUPPORTED_MODEL_KINDS = {
    ".pkl": "sklearn_pickle",
    ".joblib": "sklearn_joblib",
    ".pt": "pytorch",
    ".pth": "pytorch",
    ".onnx": "onnx",
    ".keras": "tensorflow_keras",
    ".h5": "tensorflow_h5",
    ".safetensors": "safetensors",
    ".bst": "xgboost_bst",
    ".ubj": "xgboost_ubj",
}
DATA_FILE_SUFFIXES = {".csv"}
CODE_SCAN_SUFFIXES = {".py", ".ipynb"}
CODE_SCAN_SKIP_FILES = {"runtest_2.py"}
TRAINING_CODE_PATTERN = re.compile(
    r"("
    r"\bmodel\.fit\s*\(|"
    r"\bmodel\.compile\s*\(|"
    r"\btorch\.save\s*\("
    r")",
    re.IGNORECASE,
)
GENERIC_MODEL_STEMS = {
    "best",
    "checkpoint",
    "final",
    "model",
    "pytorch_model",
    "weights",
}

REFERENCE_ENTRYPOINTS = [
    "runtest.py",
    "run_test.py",
]
PROTECTED_REFERENCE_ENTRYPOINTS = set(REFERENCE_ENTRYPOINTS)
PYTHON_ENTRYPOINTS = [
    "runtest.py",
    "run_test.py",
    "run_model.py",
    "run.py",
    "main.py",
    "train.py",
    "app.py",
]
ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from ai_studio_process import format_model_selection_hint, format_todo_guide

TEMPLATE_SAMPLE_DIR_NAME = "pytorch_sample"
TRAIN_MODEL_TEMPLATE_ROOT = ROOT / "samples"
TEMPLATE_SAMPLE_DIR = TRAIN_MODEL_TEMPLATE_ROOT / TEMPLATE_SAMPLE_DIR_NAME
REQUIRED_REQUIREMENTS_FILE = ROOT / "scripts" / "03-environment-check" / "requirements.required.txt"
CHECK_ENVIRONMENT_SCRIPT = ROOT / "scripts" / "03-environment-check" / "check_environment.py"
PREPARE_SELECTED_MODEL_SCRIPT = ROOT / "scripts" / "04-train-model" / "prepare_selected_model.py"
RUN_TRAINING_SCRIPT = ROOT / "scripts" / "04-train-model" / "run_training.py"
PYTORCH_REFERENCE_DIR = TEMPLATE_SAMPLE_DIR
PYTORCH_REFERENCE_ENTRYPOINT = PYTORCH_REFERENCE_DIR / "runtest.py"
PS_CHECK_ENV_COMMAND = r"python .opencode/scripts/03-environment-check/check_environment.py --project . --entrypoint runtest_2.py"
PS_RUN_TRAINING_COMMAND = r"python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint runtest_2.py --execute"
PS_PREPARE_MODEL_COMMAND = r"python .opencode/scripts/02-model-select/select_model.py --project . --model <번호 또는 경로>"

REFERENCE_ENTRYPOINT_BY_KIND = {
    "pytorch": PYTORCH_REFERENCE_ENTRYPOINT,
    "safetensors": PYTORCH_REFERENCE_ENTRYPOINT,
    "sklearn_pickle": ROOT / "samples" / "sklearn_sample" / "run_model.py",
    "sklearn_joblib": ROOT / "samples" / "sklearn_sample" / "run_model.py",
    "xgboost_bst": ROOT / "samples" / "sklearn_sample" / "run_model.py",
    "xgboost_ubj": ROOT / "samples" / "sklearn_sample" / "run_model.py",
    "tensorflow_keras": ROOT / "samples" / "tensorflow_sample" / "run_model.py",
    "tensorflow_h5": ROOT / "samples" / "tensorflow_sample" / "run_model.py",
    "tensorflow_saved_model": ROOT / "samples" / "tensorflow_sample" / "run_model.py",
}
ai_STUDIO_COPY_IGNORE_DIRS = {"__pycache__", "code", "config", "data", "metrics", "saved_model", "tracking"}
ai_STUDIO_COPY_IGNORE_FILES = {
    ".env",
    "runtest.py",
    "runtest_2.py",
    "run_model.py",
    "runt_model.py",
    "requirements.txt",
    "input_example.json",
}
FORBIDDEN_RUNTEST_SELECTED_MODEL_MARKERS = (
    "PROJECT_DIR = Path(__file__).resolve().parent",
    "SOURCE_MODEL_PATH",
    "DATA_MODEL_PATH",
    "MODEL_KIND",
    "MODEL_LOAD_HINT",
    "INPUT_EXAMPLE_PATH",
    "CONFIG_DIR",
    "CONFIG_PATH",
    "MODEL_DIR",
    "MODEL_PATH = MODEL_DIR",
)
SELECTED_MODEL_LOCKED_RELATIVE_PATHS = {
    "runtest_2.py",
    "requirements.txt",
    "input_example.json",
    "aiu_custom/model.py",
    "inferencetest.py",
    "config/config.json",
}
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
MLFLOW_SETTING_NAMES = {
    "mlflow_tracking_uri",
    "mlflow_tracking_username",
    "mlflow_tracking_password",
    "mlflow_experiment_name",
    "mlflow_register_model_name",
}
MODEL_RELATED_SETTING_NAMES = {
    "SOURCE_MODEL_PATH",
    "DATA_MODEL_PATH",
    "MODEL_PATH",
    "MODEL_OUTPUT_DIR",
    "MODEL_OUTPUT_PATH",
    "CONFIG_DIR",
    "CONFIG_PATH",
    "MODEL_KIND",
    "source_model_path",
    "data_model_path",
    "model_path",
    "model_dir",
    "model_output_dir",
    "model_output_path",
    "saved_model_dir",
    "config_dir",
    "config_path",
    "MODEL_FILE",
    "model_file",
    "CHECKPOINT_PATH",
    "checkpoint_path",
    "MODEL_LOAD_HINT",
    "model_load_hint",
    "REQUIRED_PACKAGE",
    "required_package",
    "INPUT_EXAMPLE_PATH",
    "input_example_path",
    "INPUT_EXAMPLE_FILE",
    "input_example_file",
    "SAMPLE_INPUT_PATH",
    "sample_input_path",
    "AI_STUDIO_DIR",
    "AI_STUDIO_CODE_DIR",
    "AI_STUDIO_METRICS_DIR",
    "AI_STUDIO_TRACKING_DIR",
    "PROJECT_DIR",
}
MODEL_PATH_VARIABLE_NAMES = {
    "SOURCE_MODEL_PATH",
    "DATA_MODEL_PATH",
    "MODEL_PATH",
    "source_model_path",
    "data_model_path",
    "model_path",
    "MODEL_FILE",
    "model_file",
    "CHECKPOINT_PATH",
    "checkpoint_path",
}
INPUT_EXAMPLE_VARIABLE_NAMES = {
    "INPUT_EXAMPLE_PATH",
    "input_example_path",
    "INPUT_EXAMPLE_FILE",
    "input_example_file",
    "SAMPLE_INPUT_PATH",
    "sample_input_path",
}
DATA_PREP_VARIABLE_NAMES = {
    "dataset",
    "dataloader",
    "features",
    "input_example",
    "labels",
    "loader",
    "sample_data",
    "sample_input",
    "batch_size",
    "test_df",
    "test_dataset",
    "test_loader",
    "test_x",
    "test_y",
    "train_df",
    "train_dataset",
    "train_loader",
    "train_x",
    "train_y",
    "x_test",
    "x_train",
    "y_test",
    "y_train",
}
DATA_PREP_CALL_PATTERN = re.compile(
    r"\b(TensorDataset|TensorDastaset|DataLoader|load_diabetes|load_iris|FashionMNIST|MNIST)\s*\("
)
MODEL_PREP_VARIABLE_NAMES = {
    "classifier",
    "clf",
    "criterion",
    "estimator",
    "model",
    "net",
    "optimizer",
    "regressor",
}
MODEL_PREP_CALL_PATTERN = re.compile(
    r"\b("
    r"ElasticNet|LinearRegression|LogisticRegression|RandomForestClassifier|RandomForestRegressor|"
    r"DecisionTreeClassifier|DecisionTreeRegressor|XGBClassifier|XGBRegressor|"
    r"ImageClassifier|Imageclassifier|torchvision\.models\.[A-Za-z_][A-Za-z0-9_]*|"
    r"nn\.Sequential|torch\.nn\.Sequential|keras\.Sequential|tf\.keras\.Sequential"
    r")\s*\("
)
MODEL_TRAIN_CALL_PATTERN = re.compile(
    r"\b("
    r"(?:model|clf|classifier|regressor|estimator|net)\.fit|"
    r"(?:model|net)\.train|"
    r"optimizer\.step|loss\.backward|criterion\("
    r")"
)
SUMMARY_VARIABLE_NAMES = {
    "summary",
    "summary_file",
    "summary_json",
    "summary_path",
    "model_summary",
    "training_summary",
}
SUMMARY_PATH_VARIABLE_NAMES = {
    "summary_file",
    "summary_json",
    "summary_path",
}
SUMMARY_CALL_PATTERN = re.compile(r"(?<![A-Za-z0-9_])summary\s*\(|\.\s*summary\s*\(")
MODEL_COMMENT_HINT_PATTERN = re.compile(
    r"(모델|로드|로딩|추론|model|load|loading|predict|inference|"
    r"sklearn|scikit|joblib|pickle|pytorch|torch|tensorflow|keras|onnx|xgboost|safetensors)",
    re.IGNORECASE,
)
MODEL_IMPORT_PACKAGE_NAMES = {
    "joblib": "joblib",
    "sklearn": "joblib",
    "torch": "torch",
    "tensorflow": "tensorflow",
    "keras": "tensorflow",
    "onnxruntime": "onnxruntime",
    "xgboost": "xgboost",
    "safetensors": "safetensors",
}
ALWAYS_KEEP_IMPORT_MODULES = {
    "sys",
    "io",
    "os",
    "json",
    "joblib",
    "mlflow",
    "logging",
}
MODEL_PATH_REFERENCE_PATTERN = re.compile(
    r"(?P<path>[A-Za-z0-9가-힣_./\\() -]+(?:"
    + "|".join(re.escape(suffix) for suffix in sorted(SUPPORTED_MODEL_KINDS, key=len, reverse=True))
    + r"))",
    re.IGNORECASE,
)
PATH_SEPARATOR_TRANSLATION = str.maketrans({
    "\\": "/",
    "＼": "/",
    "￦": "/",
    "₩": "/",
})
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"^[A-Za-z]:/")


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
PATH_LIKE_STRING_PATTERN = re.compile(
    r"("
    r"(?:/mnt|/data|/home|/workspace|/tmp|ai_studio|data|models?|artifacts?|saved_model)"
    r"[A-Za-z0-9가-힣_./\\＼￦₩() -]*"
    r")",
    re.IGNORECASE,
)
PYTHON_STRING_LITERAL_PATTERN = re.compile(
    r"(?P<prefix>[rRuUbBfF]*)(?P<quote>['\"])(?P<body>(?:\\.|[^\\])*?)(?P=quote)"
)
MODEL_LOADER_CALL_PATTERN = re.compile(
    r"\b("
    r"joblib\.load|"
    r"pickle\.load|"
    r"torch\.load|"
    r"tf\.keras\.models\.load_model|"
    r"keras\.models\.load_model|"
    r"onnxruntime\.InferenceSession|"
    r"ort\.InferenceSession|"
    r"mlflow\.pyfunc\.load_model|"
    r"load_file"
    r")\s*\("
)
MODEL_KIND_DETAILS = {
    "sklearn_pickle": {
        "required_package": "joblib",
        "load_hint": "joblib.load(MODEL_PATH)",
        "loader": """def load_selected_model():\n    import joblib\n\n    return joblib.load(MODEL_PATH)\n""",
    },
    "sklearn_joblib": {
        "required_package": "joblib",
        "load_hint": "joblib.load(MODEL_PATH)",
        "loader": """def load_selected_model():\n    import joblib\n\n    return joblib.load(MODEL_PATH)\n""",
    },
    "pytorch": {
        "required_package": "torch",
        "load_hint": "torch.load(MODEL_PATH, map_location='cpu', weights_only=False)",
        "loader": """def load_selected_model():\n    import torch\n\n    try:\n        return torch.load(MODEL_PATH, map_location=\"cpu\", weights_only=False)\n    except TypeError:\n        return torch.load(MODEL_PATH, map_location=\"cpu\")\n""",
    },
    "onnx": {
        "required_package": "onnxruntime",
        "load_hint": "onnxruntime.InferenceSession(str(MODEL_PATH))",
        "loader": """def load_selected_model():\n    import onnxruntime as ort\n\n    return ort.InferenceSession(str(MODEL_PATH))\n""",
    },
    "tensorflow_keras": {
        "required_package": "tensorflow",
        "load_hint": "tf.keras.models.load_model(MODEL_PATH)",
        "loader": """def load_selected_model():\n    import tensorflow as tf\n\n    return tf.keras.models.load_model(MODEL_PATH)\n""",
    },
    "tensorflow_h5": {
        "required_package": "tensorflow",
        "load_hint": "tf.keras.models.load_model(MODEL_PATH)",
        "loader": """def load_selected_model():\n    import tensorflow as tf\n\n    return tf.keras.models.load_model(MODEL_PATH)\n""",
    },
    "tensorflow_saved_model": {
        "required_package": "tensorflow",
        "load_hint": "tf.keras.models.load_model(MODEL_PATH)",
        "loader": """def load_selected_model():\n    import tensorflow as tf\n\n    return tf.keras.models.load_model(MODEL_PATH)\n""",
    },
    "safetensors": {
        "required_package": "safetensors",
        "load_hint": "safetensors.torch.load_file(str(MODEL_PATH))",
        "loader": """def load_selected_model():\n    from safetensors.torch import load_file\n\n    return load_file(str(MODEL_PATH))\n""",
    },
    "xgboost_bst": {
        "required_package": "xgboost",
        "load_hint": "xgboost.Booster().load_model(str(MODEL_PATH))",
        "loader": """def load_selected_model():\n    import xgboost as xgb\n\n    booster = xgb.Booster()\n    booster.load_model(str(MODEL_PATH))\n    return booster\n""",
    },
    "xgboost_ubj": {
        "required_package": "xgboost",
        "load_hint": "xgboost.Booster().load_model(str(MODEL_PATH))",
        "loader": """def load_selected_model():\n    import xgboost as xgb\n\n    booster = xgb.Booster()\n    booster.load_model(str(MODEL_PATH))\n    return booster\n""",
    },
}


@dataclass
class PreparedModelReport:
    project_path: str
    data_root: str
    model_artifact_paths: list[str]
    training_code_paths: list[str]
    data_file_paths: list[str]
    entrypoint_paths: list[str]
    selected_model_path: str | None
    model_kind: str | None
    reference_entrypoint: str | None
    generated_entrypoint: str
    generated_inference_test: str
    execute: bool
    work_project_path: str | None = None
    requested_model_path: str | None = None
    model_selection_locked: bool = False
    locked_model_path: str | None = None
    required_requirements: list[str] = field(default_factory=list)
    additional_requirements: list[str] = field(default_factory=list)
    prepared_paths: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)


def rel(path: Path, base: Path) -> str:
    try:
        return normalize_path_text(path.relative_to(base).as_posix())
    except ValueError:
        try:
            return normalize_path_text(os.path.relpath(path, base))
        except ValueError:
            return normalize_path_text(path.as_posix())


def windows_relative_path(path: Path, base: Path) -> str:
    return rel(path, base).replace("/", "\\")


def normalize_path_text(value: str) -> str:
    return re.sub(r"/+", "/", value.translate(PATH_SEPARATOR_TRANSLATION))


def is_absolute_model_selector(value: str) -> bool:
    normalized = normalize_path_text(value.strip())
    return normalized.startswith("/") or WINDOWS_ABSOLUTE_PATH_PATTERN.match(normalized) is not None


def normalize_path_literal_text(value: str) -> str:
    if not any(separator in value for separator in ["\\", "＼", "￦", "₩"]):
        return value
    return PATH_LIKE_STRING_PATTERN.sub(lambda match: normalize_path_text(match.group(0)), value)


def is_saved_model_dir(path: Path) -> bool:
    return path.is_dir() and (path / "saved_model.pb").is_file()


def model_kind(path: Path) -> str | None:
    if is_saved_model_dir(path):
        return "tensorflow_saved_model"
    return SUPPORTED_MODEL_KINDS.get(path.suffix.lower())


def model_sort_key(path: Path, project: Path) -> str:
    try:
        relative = path.resolve().relative_to(project.resolve())
    except ValueError:
        relative = path
    return normalize_path_text(str(relative)).lower()


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


def scan_model_artifacts(project: Path) -> list[Path]:
    if is_opencode_sample_source(project):
        return []
    found: list[Path] = []

    # Search only the selected project root and its data/** tree. Do not scan
    # arbitrary sibling folders or the whole drive/workspace.
    for path in project.iterdir():
        if (path.is_file() or path.is_dir()) and model_kind(path):
            found.append(path)

    data_root = project / "data"
    if not data_root.is_dir():
        return sorted(set(found), key=lambda path: model_sort_key(path, project))

    for path in data_root.rglob("*"):
        try:
            relative_parts = path.relative_to(project).parts
        except ValueError:
            continue
        if any(part in MODEL_SCAN_SKIP_DIRS for part in relative_parts):
            continue
        if (path.is_file() or path.is_dir()) and model_kind(path):
            found.append(path)
    return sorted(set(found), key=lambda path: model_sort_key(path, project))


def scan_data_files(project: Path) -> list[Path]:
    if is_opencode_sample_source(project):
        return []
    found: list[Path] = []
    for path in project.iterdir():
        if path.is_file() and path.suffix.lower() in DATA_FILE_SUFFIXES:
            found.append(path)

    data_root = project / "data"
    if data_root.is_dir():
        for path in data_root.rglob("*"):
            try:
                relative_parts = path.relative_to(project).parts
            except ValueError:
                continue
            if any(part in MODEL_SCAN_SKIP_DIRS for part in relative_parts):
                continue
            if path.is_file() and path.suffix.lower() in DATA_FILE_SUFFIXES:
                found.append(path)
    return sorted(set(found))


def read_code_text(path: Path) -> str:
    if path.suffix.lower() == ".ipynb":
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            return ""
        cells = payload.get("cells", []) if isinstance(payload, dict) else []
        chunks: list[str] = []
        for cell in cells:
            if not isinstance(cell, dict) or cell.get("cell_type") != "code":
                continue
            source = cell.get("source", "")
            if isinstance(source, list):
                chunks.append("".join(str(item) for item in source))
            elif isinstance(source, str):
                chunks.append(source)
        return "\n".join(chunks)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def scan_training_code(project: Path) -> list[Path]:
    if is_opencode_sample_source(project):
        return []
    found: list[Path] = []
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
            path = root_path / filename
            if filename in CODE_SCAN_SKIP_FILES or path.suffix.lower() not in CODE_SCAN_SUFFIXES:
                continue
            if TRAINING_CODE_PATTERN.search(read_code_text(path)):
                found.append(path)
    return sorted(set(found), key=lambda path: model_sort_key(path, project))


def training_code_run_hint(project: Path, training_code_paths: list[str]) -> str:
    python_entrypoints = [path for path in training_code_paths if Path(path).suffix.lower() == ".py"]
    if python_entrypoints:
        return (
            "실행 예: python .opencode/scripts/04-train-model/run_training.py --project . "
            f"--entrypoint {powershell_quote_path(Path(python_entrypoints[0]))} --execute"
        )
    return "노트북 학습 코드는 먼저 .py entrypoint로 변환한 뒤 run_training.py --entrypoint <파일.py>로 실행하세요."


def find_python_entrypoints(project: Path) -> list[Path]:
    if is_opencode_sample_source(project):
        return []
    found: list[Path] = []
    for name in PYTHON_ENTRYPOINTS:
        path = project / name
        if path.is_file():
            found.append(path)
    found.extend(sorted(path for path in project.glob("*.py") if path.is_file()))
    return sorted(set(found))


def artifacts_under(path: Path) -> list[Path]:
    if (path.is_file() or path.is_dir()) and model_kind(path):
        return [path]
    if not path.is_dir():
        return []
    found = []
    for child in path.rglob("*"):
        if (child.is_file() or child.is_dir()) and model_kind(child):
            found.append(child)
    project = path if path.is_dir() else path.parent
    return sorted(set(found), key=lambda item: model_sort_key(item, project))


def resolve_single_artifact(project: Path, candidates: list[Path], raw: str) -> tuple[Path | None, str | None]:
    candidates = sorted(set(path.resolve() for path in candidates), key=lambda path: model_sort_key(path, project))
    if len(candidates) == 1:
        return candidates[0], None
    if not candidates:
        return None, f"model_path_not_found:{raw}"
    relative_candidates = ", ".join(rel(path, project) for path in candidates[:10])
    suffix = "" if len(candidates) <= 10 else f", ...(+{len(candidates) - 10})"
    return None, f"model_path_ambiguous:{raw}:[{relative_candidates}{suffix}]"


def match_model_by_text(project: Path, models: list[Path], raw: str) -> tuple[Path | None, str | None]:
    value = normalize_path_text(raw.strip()).strip("/")
    lowered = value.lower()
    matches = []
    for model in models:
        relative = rel(model, project)
        relative_lower = relative.lower()
        parts_lower = [part.lower() for part in Path(relative).parts]
        if lowered in {
            model.name.lower(),
            model.stem.lower(),
            model.parent.name.lower(),
            relative_lower,
        }:
            matches.append(model)
            continue
        if lowered in parts_lower or relative_lower.endswith("/" + lowered):
            matches.append(model)
    return resolve_single_artifact(project, matches, raw)


def selected_model_from_config(project: Path) -> tuple[Path | None, str | None, str | None]:
    config_path = project / "config" / "config.json"
    if not config_path.is_file():
        return None, None, "selected_model_config_missing"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, None, f"selected_model_config_parse_error:{exc.lineno}"
    model = payload.get("model") if isinstance(payload, dict) else None
    if not isinstance(model, dict):
        return None, None, "selected_model_config_model_missing"
    source_path = model.get("source_path") or model.get("original_path") or model.get("path") or model.get("model_relative_path") or model.get("runtime_model_path") or model.get("relative_path")
    kind = model.get("model_kind") or model.get("kind")
    if not isinstance(source_path, str) or not source_path.strip():
        return None, kind if isinstance(kind, str) else None, "selected_model_config_source_path_missing"
    normalized = normalize_path_text(source_path.strip())
    candidate = Path(normalized).expanduser()
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    if not candidate.exists():
        return candidate, kind if isinstance(kind, str) else None, f"selected_model_config_not_found:{source_path}"
    return candidate, kind if isinstance(kind, str) else None, None


def stored_selected_model_path(project: Path) -> Path | None:
    selected_model, _kind, _error = selected_model_from_config(project)
    return selected_model


def eval_project_path_expr(node: ast.AST, project: Path, symbols: dict[str, Path | str] | None = None) -> Path | str | None:
    symbols = symbols or {}
    if isinstance(node, ast.Name):
        if node.id == "PROJECT_DIR":
            return project
        if node.id == "AI_STUDIO_DIR":
            return project
        if node.id in symbols:
            return symbols[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = eval_project_path_expr(node.left, project, symbols)
        right = eval_project_path_expr(node.right, project, symbols)
        if left is None or right is None:
            return None
        return Path(left) / str(right)
    return None


def selected_model_from_runtest_2(project: Path) -> tuple[Path | None, str | None, str | None]:
    runtest_2 = project / "runtest_2.py"
    if not runtest_2.is_file():
        return None, None, "runtest_2_missing"
    try:
        tree = ast.parse(runtest_2.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError as exc:
        return None, None, f"runtest_2_parse_error:{exc.lineno}"

    selected_model: Path | None = None
    selected_kind: str | None = None
    symbols: dict[str, Path | str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        value = eval_project_path_expr(node.value, project, symbols)
        for target_name in targets:
            if value is not None:
                symbols[target_name] = value
        if "SOURCE_MODEL_PATH" in targets:
            if value is not None:
                selected_model = Path(value)
                if not selected_model.is_absolute():
                    selected_model = project / selected_model
                selected_model = selected_model.resolve()
        if "MODEL_KIND" in targets and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            selected_kind = node.value.value

    if selected_model is None:
        return None, selected_kind, "runtest_2_source_model_path_missing"
    if selected_kind is None:
        return selected_model, None, "runtest_2_model_kind_missing"
    if not selected_model.exists():
        return selected_model, selected_kind, f"runtest_2_selected_model_not_found:{rel(selected_model, project)}"
    return selected_model, selected_kind, None


def current_selected_model_path(project: Path) -> Path | None:
    # Later TODO steps reuse the stored selection when no new model is given.
    # runtest_2.py is a generated artifact and must not become the selection source.
    return stored_selected_model_path(project)


def is_selected_model_alias(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"selected", "current", "last", "기존", "현재", "선택"}


def resolve_model_selection(project: Path, models: list[Path], raw: str | None) -> tuple[Path | None, str | None]:
    current_selected = current_selected_model_path(project)
    if not raw:
        if current_selected is not None and current_selected.exists():
            return current_selected, None
        return None, "model_selection_required"
    value = normalize_path_text(raw.strip())
    if is_selected_model_alias(value):
        if current_selected is not None:
            return current_selected, None
        return None, "stored_model_selection_missing"
    # A new explicit --model value means the user is choosing a model again.
    # Later TODO steps reuse the stored model only when --model is omitted or set
    # to selected/current.
    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(models):
            return models[index - 1], None
        return None, f"model_index_out_of_range:{value}"

    if is_absolute_model_selector(value):
        return None, "model_path_must_be_project_relative"

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    if candidate.exists():
        return resolve_single_artifact(project, artifacts_under(candidate), value)
    return match_model_by_text(project, models, value)


def requested_model_path_from_raw(project: Path, models: list[Path], raw: str | None) -> Path | None:
    if not raw:
        return None
    value = normalize_path_text(raw.strip())
    if is_selected_model_alias(value):
        return current_selected_model_path(project)
    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(models):
            return models[index - 1]
        return None
    if is_absolute_model_selector(value):
        return None
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = project / candidate
    candidate = candidate.resolve()
    if candidate.exists():
        return candidate
    resolved, _error = resolve_single_artifact(project, artifacts_under(candidate), value)
    if resolved is not None:
        return resolved
    resolved, _error = match_model_by_text(project, models, value)
    return resolved


def ensure_under_project(project: Path, model_path: Path) -> bool:
    try:
        model_path.resolve().relative_to(project.resolve())
        return True
    except ValueError:
        return False


def find_reference_entrypoint(project: Path, kind: str | None = None) -> Path | None:
    for name in REFERENCE_ENTRYPOINTS:
        candidate = project / name
        if candidate.is_file():
            return candidate
    sample_reference = REFERENCE_ENTRYPOINT_BY_KIND.get(kind or "")
    if sample_reference is not None and sample_reference.is_file():
        return sample_reference
    return None


def runtest_generation_reference(kind: str | None, reference: Path) -> Path:
    if kind in {"pytorch", "safetensors"} and PYTORCH_REFERENCE_ENTRYPOINT.is_file():
        return PYTORCH_REFERENCE_ENTRYPOINT
    return reference


def preserve_reference_code(reference: Path) -> bool:
    if reference.resolve() == PYTORCH_REFERENCE_ENTRYPOINT.resolve():
        return True
    if not PYTORCH_REFERENCE_ENTRYPOINT.is_file():
        return False
    try:
        if file_sha256(reference) == file_sha256(PYTORCH_REFERENCE_ENTRYPOINT):
            return True
    except OSError:
        return False
    text = reference.read_text(encoding="utf-8", errors="ignore")
    pytorch_sample_markers = [
        "TinyTorchModel",
        "def prepare_data(",
        "def train_model(",
        "def compute_metrics(",
        "mlflow.pyfunc.log_model(",
    ]
    return all(marker in text for marker in pytorch_sample_markers)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_mlflow_name(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_").lower()
    return normalized or fallback


def powershell_quote_path(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def powershell_set_project_location(path: Path) -> str:
    return f"Set-Location -LiteralPath {powershell_quote_path(path)}"


def powershell_python_script(path: Path, *args: str) -> str:
    command = f"python {powershell_quote_path(path)}"
    if args:
        command += " " + " ".join(args)
    return command


def absolute_path_text(path: Path) -> str:
    return str(path.resolve())


def runtime_path_expr(path: Path, constructor: str = "_aiPath") -> str:
    return f"{constructor}({absolute_path_text(path)!r})"


def selected_model_display_name(project: Path, selected_model: Path) -> str:
    stem = selected_model.stem
    parent_name = selected_model.parent.name
    try:
        relative_parts = selected_model.relative_to(project).parts
    except ValueError:
        relative_parts = selected_model.parts
    if stem.lower() in GENERIC_MODEL_STEMS and parent_name not in {"", ".", "data"}:
        return parent_name
    if len(relative_parts) >= 3 and relative_parts[0] == "data" and stem.lower() in GENERIC_MODEL_STEMS:
        return relative_parts[-2]
    return stem


def safe_folder_name(value: str, fallback: str = "selected_model") -> str:
    normalized = re.sub(r"[^A-Za-z0-9가-힣_.-]+", "_", value.strip())
    normalized = normalized.strip("._-")
    return normalized or fallback


def selected_model_work_dir(project: Path, selected_model: Path) -> Path:
    folder_name = safe_folder_name(selected_model_display_name(project, selected_model), selected_model.stem or selected_model.name)
    return project / folder_name


def default_mlflow_names(project: Path, selected_model: Path) -> tuple[str, str]:
    experiment_name = safe_mlflow_name(selected_model_display_name(project, selected_model), "ai_studio")
    return experiment_name, f"{experiment_name}_model"


def model_profile(project: Path, selected_model: Path, kind: str) -> dict[str, str]:
    details = MODEL_KIND_DETAILS.get(kind, {})
    linux_path = rel(selected_model, project)
    windows_url = windows_relative_path(selected_model, project)
    saved_model_linux_path = f"saved_model/{selected_model.name}"
    saved_model_windows_path = saved_model_linux_path.replace("/", "\\")
    return {
        "model_name": selected_model.name,
        "selected_model_name": selected_model_display_name(project, selected_model),
        "model_suffix": selected_model.suffix.lower(),
        "model_kind": kind,
        "url": saved_model_linux_path,
        "path": saved_model_windows_path,
        "model_relative_path": saved_model_windows_path,
        "runtime_model_path": saved_model_windows_path,
        "saved_model_url": saved_model_linux_path,
        "saved_model_path": saved_model_windows_path,
        "source_url": linux_path,
        "source_path": windows_url,
        "linux_path": linux_path,
        "linux_saved_model_path": saved_model_linux_path,
        "linux_source_path": linux_path,
        "model_parent": rel(selected_model.parent, project),
        "required_package": details.get("required_package", "unknown"),
        "load_hint": details.get("load_hint", "custom loader required"),
    }


def runtime_project_path_expr(project: Path, path: Path) -> str:
    relative = rel(path, project)
    if Path(relative).is_absolute():
        return f'_aiPath({relative!r})'
    return f'AI_STUDIO_DIR / "{relative}"'


def reference_display_path(reference: Path) -> str:
    try:
        return ".opencode/" + normalize_path_text(reference.resolve().relative_to(ROOT).as_posix())
    except ValueError:
        return normalize_path_text(reference.as_posix())


def reference_scope_display_path(kind: str | None, reference: Path) -> str:
    if kind in {"pytorch", "safetensors"} and PYTORCH_REFERENCE_DIR.is_dir():
        return f"{reference_display_path(PYTORCH_REFERENCE_DIR)} (requirements.txt 제외)"
    return reference_display_path(reference)


def conversion_reference_step(kind: str, reference: Path) -> str:
    display_path = reference_scope_display_path(kind, reference)
    if kind in {"pytorch", "safetensors"}:
        return f"4. PyTorch 참조 영역 확인: {display_path}"
    return f"4. 선택 모델 기준 참조: {display_path}"


def runtest_2_sequence(project: Path, selected_model: Path, kind: str, reference: Path) -> list[str]:
    return [
        f"1. 선택 모델 경로 및 형식 확인: {rel(selected_model, project)} / MODEL_KIND={kind}",
        f"2. samples/pytorch_sample/ 템플릿을 모델 작업 폴더로 복사: {rel(selected_model_work_dir(project, selected_model), project)}",
        f"3. 참조 영역 확인: {reference_scope_display_path(kind, reference)}",
        "4. runtest.py 참조해서 runtest_2.py 변환",
        "5. 복사된 템플릿 기준으로 선택 모델 경로와 모델 형식 연결부 수정",
        "6. 변환 결과 검증",
    ]


def copy_template_sample_folder(project: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    copied: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    target = project
    if not TEMPLATE_SAMPLE_DIR.is_dir():
        failures.append(f"pytorch_sample_folder_missing:{TEMPLATE_SAMPLE_DIR}")
        return copied, skipped, failures
    if target.exists() and not target.is_dir():
        failures.append(f"workspace_target_not_directory:{target}")
        return copied, skipped, failures
    current_selected = current_selected_model_path(project)
    selected_model_locked = current_selected is not None and current_selected.exists()
    if execute:
        for source in TEMPLATE_SAMPLE_DIR.rglob("*"):
            relative = source.relative_to(TEMPLATE_SAMPLE_DIR)
            if any(part in ai_STUDIO_COPY_IGNORE_DIRS for part in relative.parts):
                continue
            if relative.as_posix() in ai_STUDIO_COPY_IGNORE_FILES:
                continue
            destination = target / relative
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if relative.as_posix() in PROTECTED_REFERENCE_ENTRYPOINTS and destination.exists():
                skipped.append(f"{relative.as_posix()} protected_existing_reference")
                continue
            if selected_model_locked and relative.as_posix() in SELECTED_MODEL_LOCKED_RELATIVE_PATHS and destination.exists():
                skipped.append(f"{relative.as_posix()} selected_model_locked")
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        runtest_path = target / "runtest.py"
        if runtest_path.is_file():
            runtest_text = runtest_path.read_text(encoding="utf-8", errors="ignore")
            forbidden_markers = [
                marker
                for marker in FORBIDDEN_RUNTEST_SELECTED_MODEL_MARKERS
                if marker in runtest_text
            ]
            if forbidden_markers:
                failures.append(
                    "runtest.py_selected_model_constants_forbidden:"
                    + ",".join(forbidden_markers)
                )
    copied.append(".opencode/samples/pytorch_sample/* -> model work folder (data/, requirements.txt 제외)")
    return copied, skipped, failures


def ensure_aiu_custom_template_copied(project: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    template_dir = TEMPLATE_SAMPLE_DIR / "aiu_custom"
    target_dir = project / "aiu_custom"
    if not template_dir.is_dir():
        failures.append(f"aiu_custom_template_missing:{template_dir}")
        return changed, skipped, failures
    template_files = [
        path.relative_to(template_dir).as_posix()
        for path in template_dir.rglob("*")
        if path.is_file()
        and not any(part in ai_STUDIO_COPY_IGNORE_DIRS for part in path.relative_to(template_dir).parts)
    ]
    if not template_files:
        failures.append("aiu_custom_template_files_empty")
        return changed, skipped, failures
    if not execute:
        skipped.append("aiu_custom/ template copy verification:dry_run")
        return changed, skipped, failures
    missing = [relative for relative in template_files if not (target_dir / relative).is_file()]
    if missing:
        failures.append("aiu_custom_template_copy_missing:" + ",".join(missing))
        return changed, skipped, failures
    changed.append("aiu_custom/ template copied")
    return changed, skipped, failures


def copied_template_relative_files() -> list[str]:
    if not TEMPLATE_SAMPLE_DIR.is_dir():
        return []
    files: list[str] = []
    for source in TEMPLATE_SAMPLE_DIR.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(TEMPLATE_SAMPLE_DIR)
        if any(part in ai_STUDIO_COPY_IGNORE_DIRS for part in relative.parts):
            continue
        if relative.as_posix() in ai_STUDIO_COPY_IGNORE_FILES:
            continue
        files.append(relative.as_posix())
    return sorted(files)


def read_copied_template_files(project: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    relative_files = copied_template_relative_files()
    if not relative_files:
        failures.append("copied_template_files_empty")
        return changed, skipped, failures
    if not execute:
        skipped.append("copied template files read:dry_run")
        return changed, skipped, failures
    read_count = 0
    for relative in relative_files:
        path = project / relative
        if not path.is_file():
            failures.append(f"copied_template_file_missing:{relative}")
            continue
        try:
            path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            failures.append(f"copied_template_file_read_failed:{relative}:{exc}")
            continue
        read_count += 1
    if not failures:
        changed.append(f"copied template files re-read ({read_count})")
    return changed, skipped, failures


def ensure_runtime_directories(project: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    runtime_dirs = ["config", "saved_model", "local_serving"]
    if not execute:
        skipped.extend(f"{name}/:dry_run" for name in runtime_dirs)
        return changed, skipped, failures
    for name in runtime_dirs:
        path = project / name
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            failures.append(f"runtime_dir_create_failed:{name}:{exc}")
            continue
        changed.append(f"{name}/")
    return changed, skipped, failures


def ensure_model_work_dir(project: Path, work_project: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    if not execute:
        skipped.append(f"{rel(work_project, project)}/:dry_run")
        return changed, skipped, failures
    try:
        work_project.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        failures.append(f"model_work_dir_create_failed:{rel(work_project, project)}:{exc}")
        return changed, skipped, failures
    changed.append(f"{rel(work_project, project)}/ model work folder")
    return changed, skipped, failures


def write_saved_model(project: Path, selected_model: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "saved_model" / selected_model.name
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    if not execute:
        skipped.append("saved_model selected artifact:dry_run")
        return changed, skipped, failures
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if selected_model.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(selected_model, target)
        else:
            shutil.copy2(selected_model, target)
    except OSError as exc:
        failures.append(f"saved_model_copy_failed:{rel(selected_model, project)}:{exc}")
        return changed, skipped, failures
    changed.append(f"saved_model/{selected_model.name} (selected model copy)")
    return changed, skipped, failures


def split_inline_comment(value: str) -> tuple[str, str]:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            return value[:index].rstrip(), value[index:].rstrip()
    return value.rstrip(), ""


def assignment_line(name: str, expression: str, comment: str) -> str:
    suffix = f"  {comment}" if comment else ""
    return f"{name} = {expression}{suffix}\n"


def converted_assignment_comment(name: str, selected_relative: str, kind: str, load_hint: str, required_package: str) -> str | None:
    if name in {"MODEL_KIND"}:
        return f"# Ai Studio 변환: 선택 모델 종류 {kind}"
    if name in {"MODEL_LOAD_HINT", "model_load_hint"}:
        return f"# Ai Studio 변환: 선택 모델 로더 {load_hint}"
    if name in {"REQUIRED_PACKAGE", "required_package"}:
        return f"# Ai Studio 변환: 선택 모델 필요 패키지 {required_package}"
    if name in DATA_PREP_VARIABLE_NAMES:
        return f"# Ai Studio 변환: 선택 모델 {kind} 기준 데이터 준비 값"
    if name in MODEL_PREP_VARIABLE_NAMES:
        return f"# Ai Studio 변환: 선택 모델 {kind} 기준 모델 준비 값"
    if name in SUMMARY_VARIABLE_NAMES:
        return f"# Ai Studio 변환: 선택 모델 {kind} 기준 요약 산출물"
    if name in MODEL_RELATED_SETTING_NAMES:
        return f"# Ai Studio 변환: 선택 모델 {selected_relative} 기준 경로"
    return None


def replacement_expression(name: str, replacements: dict[str, str]) -> str | None:
    if name in replacements:
        return replacements[name]
    lower_name = name.lower()
    if lower_name in replacements:
        return replacements[lower_name]
    return None


def text_contains_model_path(value: str) -> bool:
    return any(suffix in value.lower() for suffix in SUPPORTED_MODEL_KINDS)


def rewrite_model_comment(comment: str, selected_relative: str, kind: str, load_hint: str) -> str:
    if not text_contains_model_path(comment):
        if MODEL_COMMENT_HINT_PATTERN.search(comment):
            return f"# Ai Studio 변환: 선택 모델 {selected_relative} 기준 (MODEL_KIND={kind}, loader={load_hint})"
        return comment
    prefix = "#"
    body = comment[1:].strip() if comment.lstrip().startswith("#") else comment.strip()
    converted = MODEL_PATH_REFERENCE_PATTERN.sub(selected_relative, body)
    if converted == body:
        return f"# Ai Studio 변환: 선택 모델 {selected_relative} 기준 (MODEL_KIND={kind}, loader={load_hint})"
    return f"{prefix} Ai Studio 변환: {converted}"


def model_path_literal_expression(token_text: str) -> str | None:
    try:
        value = ast.literal_eval(token_text)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, str) or not text_contains_model_path(value):
        return None
    if MODEL_PATH_REFERENCE_PATTERN.search(value):
        return "str(MODEL_PATH)"
    return None


def rewrite_model_string_literals(line: str, selected_relative: str, kind: str, load_hint: str) -> str:
    if not text_contains_model_path(line) and not MODEL_COMMENT_HINT_PATTERN.search(line):
        return line
    suffix = "\n" if line.endswith("\n") else ""
    body = line.rstrip("\n")
    if body.lstrip().startswith("#"):
        indent = body[: len(body) - len(body.lstrip())]
        return f"{indent}{rewrite_model_comment(body.lstrip(), selected_relative, kind, load_hint)}{suffix}"

    code, comment = split_inline_comment(body)

    def replace_literal(match: re.Match[str]) -> str:
        literal = match.group(0)
        if "f" in match.group("prefix").lower():
            return literal
        expression = model_path_literal_expression(literal)
        return expression if expression else literal

    converted_code = PYTHON_STRING_LITERAL_PATTERN.sub(replace_literal, code)
    converted_comment = rewrite_model_comment(comment, selected_relative, kind, load_hint) if comment else ""
    if converted_comment:
        return f"{converted_code}  {converted_comment}{suffix}"
    return f"{converted_code}{suffix}"


def rewrite_path_separator_literals(line: str) -> str:
    if not any(separator in line for separator in ["\\", "＼", "￦", "₩"]):
        return line
    suffix = "\n" if line.endswith("\n") else ""
    body = line.rstrip("\n")

    def replace_literal(match: re.Match[str]) -> str:
        literal = match.group(0)
        if "f" in match.group("prefix").lower():
            return literal
        raw_body = match.group("body")
        raw_normalized = normalize_path_literal_text(raw_body)
        if raw_normalized != raw_body:
            quote = match.group("quote")
            escaped = raw_normalized.replace("\\", "\\\\")
            if quote == '"':
                escaped = escaped.replace('"', '\\"')
            else:
                escaped = escaped.replace("'", "\\'")
            return f"{match.group('prefix')}{quote}{escaped}{quote}"
        try:
            value = ast.literal_eval(literal)
        except (SyntaxError, ValueError):
            return literal
        if not isinstance(value, str):
            return literal
        normalized = normalize_path_literal_text(value)
        if normalized == value:
            return literal
        quote = match.group("quote")
        escaped = normalized.replace("\\", "\\\\")
        if quote == '"':
            escaped = escaped.replace('"', '\\"')
        else:
            escaped = escaped.replace("'", "\\'")
        return f"{match.group('prefix')}{quote}{escaped}{quote}"

    return PYTHON_STRING_LITERAL_PATTERN.sub(replace_literal, body) + suffix


def input_example_literal_expression(token_text: str) -> str | None:
    try:
        value = ast.literal_eval(token_text)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, str):
        return None
    normalized = normalize_path_text(value)
    if normalized == "input_example.json":
        return "str(INPUT_EXAMPLE_PATH)"
    if normalized in {"sample_input.json", "example.json"}:
        return "str(INPUT_EXAMPLE_PATH)"
    return None


def rewrite_input_example_literals(line: str) -> str:
    if not any(name in line for name in ["input_example.json", "sample_input.json", "example.json"]):
        return line
    suffix = "\n" if line.endswith("\n") else ""
    body = line.rstrip("\n")

    def replace_literal(match: re.Match[str]) -> str:
        literal = match.group(0)
        if "f" in match.group("prefix").lower():
            return literal
        expression = input_example_literal_expression(literal)
        return expression if expression else literal

    return PYTHON_STRING_LITERAL_PATTERN.sub(replace_literal, body) + suffix


def loader_call_uses_model_path(code: str) -> bool:
    if "MODEL_PATH" in code:
        return True
    return any(re.search(rf"\b{re.escape(name)}\b", code) for name in MODEL_PATH_VARIABLE_NAMES)


def rewrite_model_loader_line(line: str, kind: str, load_hint: str) -> str:
    code, comment = split_inline_comment(line.rstrip("\n"))
    if not MODEL_LOADER_CALL_PATTERN.search(code) or not loader_call_uses_model_path(code):
        return line
    suffix = "\n" if line.endswith("\n") else ""
    indent = code[: len(code) - len(code.lstrip())]
    stripped_code = code.strip()
    if "=" in stripped_code:
        lhs = stripped_code.split("=", 1)[0].strip()
        converted_code = f"{indent}{lhs} = load_selected_model()"
    else:
        converted_code = f"{indent}load_selected_model()"
    converted_comment = f"# Ai Studio 변환: 선택 모델 종류 {kind}, 로더 {load_hint}"
    return f"{converted_code}  {converted_comment}{suffix}"


def rewrite_data_prep_call_line(line: str, kind: str) -> str:
    code, comment = split_inline_comment(line.rstrip("\n"))
    if not DATA_PREP_CALL_PATTERN.search(code):
        return line
    suffix = "\n" if line.endswith("\n") else ""
    indent = code[: len(code) - len(code.lstrip())]
    stripped_code = code.strip()
    converted_comment = f"# Ai Studio 변환: 선택 모델 {kind} 기준 synthetic input_example 사용"
    if "=" in stripped_code:
        lhs = stripped_code.split("=", 1)[0].strip()
        name = lhs.split(",", 1)[0].strip()
        if name in {"train_loader", "test_loader", "dataloader", "loader"}:
            converted_code = f"{indent}{lhs} = _aiu_model_input_example()[\"inputs\"]"
        elif name in {"train_dataset", "test_dataset", "dataset"}:
            converted_code = f"{indent}{lhs} = _aiu_model_input_example()"
        else:
            converted_code = f"{indent}{lhs} = _aiu_model_input_example()"
    else:
        converted_code = f"{indent}_aiu_model_input_example()"
    return f"{converted_code}  {converted_comment}{suffix}"


def rewrite_model_prep_line(line: str, kind: str) -> str:
    code, comment = split_inline_comment(line.rstrip("\n"))
    suffix = "\n" if line.endswith("\n") else ""
    indent = code[: len(code) - len(code.lstrip())]
    stripped_code = code.strip()

    if MODEL_TRAIN_CALL_PATTERN.search(code):
        return (
            f"{indent}# Ai Studio 변환: 선택 모델 {kind}은 이미 학습된 모델을 로드하므로 원본 학습 호출을 실행하지 않습니다.{suffix}"
            f"{indent}# {stripped_code}{suffix}"
        )

    if not MODEL_PREP_CALL_PATTERN.search(code):
        return line

    converted_comment = f"# Ai Studio 변환: 선택 모델 {kind} 기준 load_selected_model() 사용"
    if "=" in stripped_code:
        lhs = stripped_code.split("=", 1)[0].strip()
        first_name = lhs.split(",", 1)[0].strip()
        if first_name not in MODEL_PREP_VARIABLE_NAMES:
            return line
        return f"{indent}{lhs} = load_selected_model()  {converted_comment}{suffix}"
    return (
        f"{indent}# Ai Studio 변환: 선택 모델 {kind}은 load_selected_model()으로 준비됩니다.{suffix}"
        f"{indent}# {stripped_code}{suffix}"
    )


def collapse_multiline_model_prep_calls(text: str, kind: str) -> str:
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    assignment_pattern = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
    while index < len(lines):
        line = lines[index]
        match = assignment_pattern.match(line.rstrip("\n"))
        if not match:
            output.append(line)
            index += 1
            continue

        indent, name, expression = match.groups()
        if name not in MODEL_PREP_VARIABLE_NAMES or not MODEL_PREP_CALL_PATTERN.search(expression):
            output.append(line)
            index += 1
            continue

        balance = expression.count("(") - expression.count(")")
        if balance <= 0:
            output.append(line)
            index += 1
            continue

        skipped = [line.rstrip("\n")]
        index += 1
        while index < len(lines) and balance > 0:
            continuation = lines[index]
            skipped.append(continuation.rstrip("\n"))
            balance += continuation.count("(") - continuation.count(")")
            index += 1

        output.append(
            f"{indent}{name} = load_selected_model()  "
            f"# Ai Studio 변환: 선택 모델 {kind} 기준 load_selected_model() 사용\n"
        )
        for skipped_line in skipped:
            if skipped_line.strip():
                output.append(f"{indent}# {skipped_line.lstrip()}\n")
    return "".join(output)


def rewrite_summary_line(line: str, kind: str) -> str:
    code, comment = split_inline_comment(line.rstrip("\n"))
    if not SUMMARY_CALL_PATTERN.search(code):
        return line

    stripped_code = code.strip()
    if stripped_code.startswith("def "):
        return line

    suffix = "\n" if line.endswith("\n") else ""
    indent = code[: len(code) - len(code.lstrip())]
    converted_comment = f"# Ai Studio 변환: 선택 모델 {kind} 기준 요약으로 대체"

    if "=" in stripped_code:
        lhs = stripped_code.split("=", 1)[0].strip()
        first_name = lhs.split(",", 1)[0].strip()
        expression = "_aiu_write_summary()" if first_name in SUMMARY_PATH_VARIABLE_NAMES else "_aiu_model_summary()"
        return f"{indent}{lhs} = {expression}  {converted_comment}{suffix}"

    if stripped_code.startswith("return "):
        return f"{indent}return _aiu_model_summary()  {converted_comment}{suffix}"

    if stripped_code.startswith("print("):
        return f"{indent}print(_aiu_model_summary())  {converted_comment}{suffix}"

    return (
        f"{indent}# Ai Studio 변환: 원본 summary 호출은 선택 모델 요약으로 대체합니다.{suffix}"
        f"{indent}_aiu_model_summary()  {converted_comment}{suffix}"
    )


def import_package_for_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    match = re.match(r"import\s+([A-Za-z_][A-Za-z0-9_]*)\b", stripped)
    if match:
        module_name = match.group(1)
        package_name = MODEL_IMPORT_PACKAGE_NAMES.get(module_name)
        return (module_name, package_name) if package_name else None
    match = re.match(r"from\s+([A-Za-z_][A-Za-z0-9_]*)\b\s+import\s+", stripped)
    if match:
        module_name = match.group(1)
        package_name = MODEL_IMPORT_PACKAGE_NAMES.get(module_name)
        return (module_name, package_name) if package_name else None
    return None


def rewrite_model_import_line(line: str, required_package: str) -> str:
    package = import_package_for_line(line)
    if package is None:
        return line
    module_name, package_name = package
    if module_name in ALWAYS_KEEP_IMPORT_MODULES:
        return line
    if package_name == required_package:
        return line
    suffix = "\n" if line.endswith("\n") else ""
    indent = line[: len(line) - len(line.lstrip())]
    original = line.rstrip("\n")
    return (
        f"{indent}# Ai Studio 변환: 선택 모델 로더는 {required_package} 기준이라 {module_name} import를 비활성화합니다.{suffix}"
        f"{indent}# {original.lstrip()}{suffix}"
    )


def rewrite_reference_line(line: str, selected_relative: str, kind: str, load_hint: str, required_package: str) -> str:
    import_converted = rewrite_model_import_line(line, required_package)
    if import_converted != line:
        return import_converted
    converted = rewrite_model_string_literals(line, selected_relative, kind, load_hint)
    converted = rewrite_path_separator_literals(converted)
    converted = rewrite_input_example_literals(converted)
    converted = rewrite_data_prep_call_line(converted, kind)
    converted = rewrite_model_prep_line(converted, kind)
    converted = rewrite_summary_line(converted, kind)
    return rewrite_model_loader_line(converted, kind, load_hint)


def rewrite_preserved_line(line: str) -> str:
    converted = rewrite_path_separator_literals(line)
    return rewrite_input_example_literals(converted)


SAFE_EXECUTION_REGISTRATION_FIELDS = {
    "AI_STUDIO_DIR",
    "PROJECT_DIR",
    "SOURCE_MODEL_PATH",
    "DATA_MODEL_PATH",
    "MODEL_PATH",
    "MODEL_KIND",
    "MODEL_LOAD_HINT",
    "INPUT_EXAMPLE_PATH",
    "CONFIG_DIR",
    "CONFIG_PATH",
    "mlflow_tracking_uri",
    "mlflow_tracking_username",
    "mlflow_tracking_password",
    "mlflow_experiment_name",
    "mlflow_register_model_name",
}


def transform_reference_text(
    reference_text: str,
    injected_block: str,
    replacements: dict[str, str],
    selected_relative: str,
    kind: str,
    load_hint: str,
    required_package: str,
    preserve_code: bool = False,
) -> str:
    if not preserve_code:
        reference_text = collapse_multiline_model_prep_calls(reference_text, kind)
    lines = reference_text.splitlines(keepends=True)
    output: list[str] = []
    inserted = False
    future_import_pattern = re.compile(r"^\s*from\s+__future__\s+import\s+")
    import_pattern = re.compile(r"^\s*(import\s+[A-Za-z_][A-Za-z0-9_]*(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?|from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import\s+.+)")
    assignment_pattern = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    while insert_at < len(lines) and re.match(r"^#.*coding[:=]", lines[insert_at]):
        insert_at += 1
    while insert_at < len(lines):
        line = lines[insert_at]
        if not line.strip():
            insert_at += 1
            continue
        if future_import_pattern.match(line):
            insert_at += 1
            continue
        break
    while insert_at < len(lines):
        line = lines[insert_at]
        if not line.strip():
            next_index = insert_at + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and import_pattern.match(lines[next_index]):
                insert_at += 1
                continue
            break
        if import_pattern.match(line):
            balance = line.count("(") - line.count(")")
            insert_at += 1
            while balance > 0 and insert_at < len(lines):
                balance += lines[insert_at].count("(") - lines[insert_at].count(")")
                insert_at += 1
            continue
        break

    for index, line in enumerate(lines):
        if not preserve_code and index == insert_at and not inserted:
            output.append(injected_block)
            inserted = True

        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        if not preserve_code and stripped.startswith("#") and not re.match(r"^#.*coding[:=]", stripped):
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines):
                next_stripped = lines[next_index].lstrip()
                next_match = assignment_pattern.match(next_stripped.rstrip("\n"))
                if next_match:
                    next_name = next_match.group(1)
                    if replacement_expression(next_name, replacements) is not None:
                        converted_comment = converted_assignment_comment(next_name, selected_relative, kind, load_hint, required_package)
                        if converted_comment:
                            output.append(f"{indent}{converted_comment}\n")
                            continue
        match = assignment_pattern.match(stripped.rstrip("\n"))
        if not match:
            output.append(rewrite_preserved_line(line) if preserve_code else rewrite_reference_line(line, selected_relative, kind, load_hint, required_package))
            continue

        name, raw_value = match.groups()
        expression = replacement_expression(name, replacements)
        if expression is None:
            output.append(rewrite_preserved_line(line) if preserve_code else rewrite_reference_line(line, selected_relative, kind, load_hint, required_package))
            continue
        if preserve_code and name not in SAFE_EXECUTION_REGISTRATION_FIELDS:
            output.append(rewrite_preserved_line(line))
            continue

        if not preserve_code and name in MLFLOW_SETTING_NAMES and not indent:
            output.append(f"# Ai Studio preserved original assignment; value is defined in the conversion block above.\n")
            output.append(f"# {line.rstrip()}\n")
            continue
        if not preserve_code and name in MLFLOW_SETTING_NAMES:
            output.append(rewrite_preserved_line(line) if preserve_code else rewrite_reference_line(line, selected_relative, kind, load_hint, required_package))
            continue

        _, comment = split_inline_comment(raw_value)
        converted_comment = None if preserve_code else converted_assignment_comment(name, selected_relative, kind, load_hint, required_package)
        if converted_comment:
            comment = converted_comment
        output.append(f"{indent}{assignment_line(name, expression, comment)}")

    if not preserve_code and not inserted:
        output.insert(0, injected_block)

    if output and not output[-1].endswith("\n"):
        output[-1] += "\n"
    return "".join(output)


def aiu_injected_block(project: Path, selected_model: Path, kind: str, reference: Path) -> str:
    selected_relative = rel(selected_model, project)
    reference_expr = runtime_project_path_expr(project, reference)
    ai_studio_path = project
    selected_model_expr = runtime_project_path_expr(project, selected_model)
    input_example_expr = 'AI_STUDIO_DIR / "input_example.json"'
    config_dir_expr = 'AI_STUDIO_DIR / "config"'
    config_path_expr = 'AI_STUDIO_DIR / "config" / "config.json"'
    model_output_dir_expr = 'AI_STUDIO_DIR / "saved_model"'
    model_output_path_expr = 'AI_STUDIO_DIR / "saved_model" / "model.pkl"'
    default_experiment_name, default_register_model_name = default_mlflow_names(project, selected_model)
    profile = model_profile(project, selected_model, kind)
    details = MODEL_KIND_DETAILS.get(kind, {})
    required_package = details.get("required_package", "unknown")
    load_hint = details.get("load_hint", "custom loader required")
    loader = details.get(
        "loader",
        """def load_selected_model():\n    raise ValueError(f\"unsupported MODEL_KIND: {MODEL_KIND}\")\n""",
    )
    data_prep = aiu_data_prep_block(kind)
    todo_guide_text = format_todo_guide(
        (
            "완료",
            "완료",
            "확인 필요",
            "완료",
            "완료",
            "선택 시",
            "오류 시",
        )
    )
    return f'''

# --- Ai Studio selected model conversion ---
# 선택된 모델을 먼저 판별하고, 원본 모델 경로를 직접 읽도록 변환합니다.
# MODEL_KIND에 맞는 load_selected_model()으로 워크스페이스 템플릿 코드를 선택 모델 기준으로 변환합니다.
# 이 블록은 자동 변환되지만 아래 원본 runtest.py 구조와 주석은 최대한 유지합니다.
import os
import atexit as _aiu_atexit
import json as _aiu_json
from pathlib import Path as _aiPath

AI_STUDIO_DIR = _aiPath(__file__).resolve().parent
ORIGINAL_MODEL_PATH = {selected_model_expr}
SOURCE_MODEL_PATH = {selected_model_expr}
DATA_MODEL_PATH = SOURCE_MODEL_PATH
MODEL_PATH = SOURCE_MODEL_PATH
INPUT_EXAMPLE_PATH = {input_example_expr}
CONFIG_DIR = {config_dir_expr}
CONFIG_PATH = {config_path_expr}
MODEL_OUTPUT_DIR = {model_output_dir_expr}
MODEL_OUTPUT_PATH = {model_output_path_expr}
MODEL_KIND = "{kind}"
MODEL_PROFILE = {json.dumps(profile, ensure_ascii=False, indent=4)}
ai_REQUIRED_PACKAGE = "{required_package}"
ai_LOAD_HINT = "{load_hint}"
REFERENCE_ENTRYPOINT = {reference_expr}

# 자주 쓰는 소문자 변수명도 선택 모델 및 ai_studio 산출물 경로를 보도록 맞춥니다.
source_model_path = str(SOURCE_MODEL_PATH)
data_model_path = str(DATA_MODEL_PATH)
model_path = str(MODEL_PATH)
input_example_path = str(INPUT_EXAMPLE_PATH)
config_dir = str(CONFIG_DIR)
config_path = str(CONFIG_PATH)
model_dir = str(MODEL_OUTPUT_DIR)
model_output_dir = str(MODEL_OUTPUT_DIR)
model_output_path = str(MODEL_OUTPUT_PATH)
saved_model_dir = str(MODEL_OUTPUT_DIR)

# Step 5 원격 MLflow 등록 실행 중 상대경로 산출물은 선택한 현재 프로젝트 경로 아래에 생성되도록 고정합니다.
os.chdir(AI_STUDIO_DIR)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MLflow/AI Studio settings
# tracking URL, username, password는 사용자가 직접 입력합니다.
# experiment/model name은 선택 모델 파일명 기준으로 자동 생성됩니다.
# password 값은 출력하지 않습니다.
mlflow_tracking_uri = ""
mlflow_tracking_username = ""
mlflow_tracking_password = ""
mlflow_experiment_name = "{default_experiment_name}"
mlflow_register_model_name = "{default_register_model_name}"

effective_mlflow_tracking_uri = mlflow_tracking_uri

{loader}

{data_prep}

_aiu_missing_mlflow_settings = [
    _aiu_name
    for _aiu_name, _aiu_value in {{
        "mlflow_tracking_uri": mlflow_tracking_uri,
        "mlflow_tracking_username": mlflow_tracking_username,
        "mlflow_tracking_password": mlflow_tracking_password,
    }}.items()
    if not str(_aiu_value).strip()
]
if _aiu_missing_mlflow_settings:
    print("원격 MLflow 등록 실행을 위해 MLflow 설정을 .env에 직접 입력하세요.")
    print("missing settings:")
    for _aiu_name in _aiu_missing_mlflow_settings:
        print(f"- {{_aiu_name}}")
    print("비밀번호 값은 출력하지 않습니다.")
    raise SystemExit(0)

for _aiu_env_name, _aiu_env_value in {{
    "MLFLOW_TRACKING_URI": effective_mlflow_tracking_uri,
    "MLFLOW_TRACKING_USERNAME": mlflow_tracking_username,
    "MLFLOW_TRACKING_PASSWORD": mlflow_tracking_password,
    "MLFLOW_EXPERIMENT_NAME": mlflow_experiment_name,
    "MLFLOW_REGISTER_MODEL_NAME": mlflow_register_model_name,
}}.items():
    if _aiu_env_value:
        os.environ[_aiu_env_name] = _aiu_env_value

def _aiu_print_existing_model_tod():
    print({todo_guide_text!r})

_aiu_atexit.register(_aiu_print_existing_model_tod)
# --- /Ai Studio selected model conversion ---

'''


def aiu_data_prep_payload(kind: str) -> str:
    if kind in {"pytorch", "safetensors"}:
        return '''{
        "inputs": [
            {
                "name": "synthetic_image",
                "shape": [1, 1, 28, 28],
                "datatype": "FP32",
                "data": [0.0 for _ in range(1 * 1 * 28 * 28)],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(MODEL_PATH),
    }'''
    if kind in {"sklearn_pickle", "sklearn_joblib", "xgboost_bst", "xgboost_ubj"}:
        return '''{
        "inputs": [
            {
                "name": "synthetic_tabular",
                "shape": [1, 4],
                "datatype": "FP32",
                "data": [[0.0, 0.0, 0.0, 0.0]],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(MODEL_PATH),
    }'''
    if kind == "onnx":
        return '''{
        "inputs": [
            {
                "name": "input",
                "shape": [1, 4],
                "datatype": "FP32",
                "data": [[0.0, 0.0, 0.0, 0.0]],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(MODEL_PATH),
    }'''
    if kind in {"tensorflow_keras", "tensorflow_h5"}:
        return '''{
        "inputs": [
            {
                "name": "synthetic_tensor",
                "shape": [1, 4],
                "datatype": "FP32",
                "data": [[0.0, 0.0, 0.0, 0.0]],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(MODEL_PATH),
    }'''
    return '''{
        "inputs": [
            {
                "name": "synthetic_input",
                "shape": [1],
                "datatype": "FP32",
                "data": [0.0],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(MODEL_PATH),
    }'''


def aiu_data_prep_block(kind: str) -> str:
    payload = aiu_data_prep_payload(kind)
    return f'''# 데이터 준비
# 선택 모델 종류에 맞는 최소 input_example으로 변환합니다.
# 외부 데이터셋(FashionMNIST 등)을 다운로드하지 않고 원격 배포/검증용 synthetic 입력만 만듭니다.
# MODEL_KIND={kind} 기준으로 변환된 데이터 준비 코드입니다.
import json as _aiu_json

try:
    INPUT_EXAMPLE_PATH
except NameError:
    INPUT_EXAMPLE_PATH = AI_STUDIO_DIR / "input_example.json"

def _aiu_flat_zeros(size):
    return [0.0 for _ in range(size)]

def _aiu_model_input_example():
    return {payload}

def _aiu_model_summary():
    return {{
        "model_kind": MODEL_KIND,
        "model_path": str(MODEL_PATH),
        "input_example_path": str(INPUT_EXAMPLE_PATH),
    }}

def _aiu_write_summary():
    try:
        summary_dir = AI_STUDIO_CODE_DIR
    except NameError:
        summary_dir = AI_STUDIO_DIR / "code"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "training_summary.json"
    summary_path.write_text(_aiu_json.dumps(_aiu_model_summary(), ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_path

def _aiu_write_input_example():
    INPUT_EXAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = _aiu_model_input_example()
    INPUT_EXAMPLE_PATH.write_text(_aiu_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

input_example = _aiu_write_input_example()
'''


def insert_preserved_data_prep_block(text: str, kind: str) -> str:
    if "_aiu_model_input_example" in text:
        return text
    marker = "\ndef load_selected_model"
    block = "\n\n" + aiu_data_prep_block(kind).rstrip() + "\n"
    if marker in text:
        return text.replace(marker, block + marker, 1)
    main_marker = "\ndef main"
    if main_marker in text:
        return text.replace(main_marker, block + main_marker, 1)
    return text.rstrip() + block


def selected_model_input_example_payload(kind: str) -> str:
    if kind in {"pytorch", "safetensors"}:
        return '''{
        "inputs": [
            {
                "name": "selected_pytorch_tensor",
                "shape": [1, 1, 28, 28],
                "datatype": "FP32",
                "data": [0.0 for _ in range(1 * 1 * 28 * 28)],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(SOURCE_MODEL_PATH),
    }'''
    if kind in {"sklearn_pickle", "sklearn_joblib", "xgboost_bst", "xgboost_ubj"}:
        return '''{
        "inputs": [
            {
                "name": "selected_tabular",
                "shape": [1, 4],
                "datatype": "FP32",
                "data": [[0.0, 0.0, 0.0, 0.0]],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(SOURCE_MODEL_PATH),
    }'''
    if kind == "onnx":
        return '''{
        "inputs": [
            {
                "name": "input",
                "shape": [1, 4],
                "datatype": "FP32",
                "data": [[0.0, 0.0, 0.0, 0.0]],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(SOURCE_MODEL_PATH),
    }'''
    if kind in {"tensorflow_keras", "tensorflow_h5"}:
        return '''{
        "inputs": [
            {
                "name": "selected_tensor",
                "shape": [1, 4],
                "datatype": "FP32",
                "data": [[0.0, 0.0, 0.0, 0.0]],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(SOURCE_MODEL_PATH),
    }'''
    return '''{
        "inputs": [
            {
                "name": "selected_input",
                "shape": [1],
                "datatype": "FP32",
                "data": [0.0],
            }
        ],
        "model_kind": MODEL_KIND,
        "model_path": str(SOURCE_MODEL_PATH),
    }'''


def selected_model_input_example_block(kind: str) -> str:
    payload = selected_model_input_example_payload(kind)
    return f'''
def selected_model_input_example():
    # Ai Studio 변환: 선택 모델 종류에 맞는 배포용 synthetic input_example입니다.
    return {payload}


def write_selected_input_example():
    input_example = selected_model_input_example()
    INPUT_EXAMPLE_PATH.write_text(
        json.dumps(input_example, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return input_example
'''


def selected_model_input_example_data(project: Path, selected_model: Path, kind: str) -> dict:
    if kind in {"pytorch", "safetensors"}:
        payload = {
            "inputs": [
                {
                    "name": "selected_pytorch_tensor",
                    "shape": [1, 1, 28, 28],
                    "datatype": "FP32",
                    "data": [0.0 for _ in range(1 * 1 * 28 * 28)],
                }
            ],
        }
    elif kind in {"sklearn_pickle", "sklearn_joblib", "xgboost_bst", "xgboost_ubj", "onnx", "tensorflow_keras", "tensorflow_h5"}:
        payload = {
            "inputs": [
                {
                    "name": "selected_tabular",
                    "shape": [1, 4],
                    "datatype": "FP32",
                    "data": [[0.0, 0.0, 0.0, 0.0]],
                }
            ],
        }
    else:
        payload = {"inputs": []}
    payload["model_kind"] = kind
    selected_windows_path = windows_relative_path(selected_model, project)
    saved_model_linux_path = f"saved_model/{selected_model.name}"
    saved_model_windows_path = f"saved_model\\{selected_model.name}"
    payload["url"] = saved_model_linux_path
    payload["path"] = saved_model_windows_path
    payload["model_path"] = payload["path"]
    payload["source_path"] = selected_windows_path
    return payload


def selected_model_data_config(project: Path, selected_model: Path, kind: str) -> dict:
    input_example = selected_model_input_example_data(project, selected_model, kind)
    inputs = input_example.get("inputs", [])
    first_input = inputs[0] if inputs and isinstance(inputs[0], dict) else {}
    return {
        "training_data_source": "not_embedded",
        "training_data_note": "실제 학습 데이터 원본은 config.json에 저장하지 않습니다.",
        "dataset_path": None,
        "input_example": "input_example.json",
        "input_schema": {
            "name": first_input.get("name"),
            "shape": first_input.get("shape"),
            "datatype": first_input.get("datatype"),
        },
        "model_kind": kind,
        "url": f"saved_model/{selected_model.name}",
        "path": f"saved_model\\{selected_model.name}",
        "model_path": f"saved_model\\{selected_model.name}",
        "source_path": windows_relative_path(selected_model, project),
    }


def selected_model_config_data(project: Path, selected_model: Path, kind: str) -> dict:
    experiment_name, registered_model_name = default_mlflow_names(project, selected_model)
    return {
        "model": model_profile(project, selected_model, kind),
        "data": selected_model_data_config(project, selected_model, kind),
        "mlflow": {
            "artifact_path": "ai_studio",
            "experiment_name": experiment_name,
            "registered_model_name": registered_model_name,
        },
        "runtime": {
            "entrypoint": "runtest_2.py",
            "model_entrypoint": "aiu_custom/model.py",
            "predict_entrypoint": "aiu_custom/predict.py",
            "input_example": "input_example.json",
            "inference_test": "inferencetest.py",
        },
        "policy": {
            "copy_model_to_ai_studio": False,
            "model_source": "selected_project_model_path",
            "secret_output": "masked",
        },
    }


def ensure_workspace_code_paths(text: str) -> str:
    if "mlflow.pyfunc.log_model(" not in text or "code_paths=" in text:
        return text
    marker = "            pip_requirements=\"requirements.txt\","
    code_paths_line = '            code_paths=["aiu_custom"],\n'
    if marker in text:
        return text.replace(marker, code_paths_line + marker, 1)
    marker = "            registered_model_name=mlflow_register_model_name,\n"
    if marker in text:
        return text.replace(marker, marker + code_paths_line, 1)
    return text


def normalize_existing_code_paths(text: str) -> str:
    if "code_paths" not in text:
        return text
    selected_code_path = '"aiu_custom"'

    text = re.sub(
        r'(?m)^(\s*)"code_paths"\s*:\s*\[[^\]]*\](\s*,?)$',
        rf'\1"code_paths": [{selected_code_path}]\2',
        text,
    )
    text = re.sub(
        r'(?m)^(\s*)code_paths\s*=\s*\[[^\]]*\](\s*,?)$',
        rf'\1code_paths=[{selected_code_path}]\2',
        text,
    )
    return text


def constant_free_loader_text(kind: str) -> str:
    if kind in {"sklearn_pickle", "sklearn_joblib", "xgboost_pickle"}:
        return '''def load_selected_model():
    import joblib

    return joblib.load(selected_model_path())
'''
    if kind in {"pytorch", "safetensors"}:
        return '''def load_selected_model():
    import torch

    try:
        return torch.load(selected_model_path(), map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(selected_model_path(), map_location="cpu")
'''
    if kind == "onnx":
        return '''def load_selected_model():
    import onnxruntime as ort

    return ort.InferenceSession(server_upload_path(selected_model_path()))
'''
    if kind in {"tensorflow_keras", "tensorflow_h5"}:
        return '''def load_selected_model():
    import tensorflow as tf

    return tf.keras.models.load_model(selected_model_path())
'''
    return '''def load_selected_model():
    raise ValueError("unsupported selected model type")
'''


def reference_style_input_example_code(
    kind: str,
    input_example: dict,
    saved_model_url: str,
    saved_model_path: str,
    source_model_path: str,
) -> str:
    if kind in {"pytorch", "safetensors"}:
        return f'''sample_shape = [1, 1, 28, 28]
sample_data = [0.0] * 784

request_input_example = {{
    "inputs": [
        {{
            "name": "selected_pytorch_tensor",
            "shape": sample_shape,
            "datatype": "FP32",
            "data": sample_data,
        }}
    ],
    "model_kind": model_kind,
    "url": {saved_model_url!r},
    "path": {saved_model_path!r},
    "model_path": {saved_model_path!r},
    "source_path": {source_model_path!r},
}}
'''
    return f'''request_input_example = {repr(input_example)}
'''


def reference_style_loader_code(kind: str) -> str:
    if kind in {"sklearn_pickle", "sklearn_joblib", "xgboost_pickle"}:
        return '''def load_selected_model():
    import joblib

    return joblib.load(selected_model_path)
'''
    if kind in {"pytorch", "safetensors"}:
        return '''def load_selected_model():
    import torch

    try:
        return torch.load(selected_model_path, map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(selected_model_path, map_location="cpu")
'''
    if kind == "onnx":
        return '''def load_selected_model():
    import onnxruntime as ort

    return ort.InferenceSession(selected_model_path)
'''
    if kind in {"tensorflow_keras", "tensorflow_h5"}:
        return '''def load_selected_model():
    import tensorflow as tf

    return tf.keras.models.load_model(selected_model_path)
'''
    return '''def load_selected_model():
    raise ValueError(f"unsupported selected model type: {model_kind}")
'''


def generated_constant_free_runtest_text(project: Path, selected_model: Path, kind: str, reference: Path | None = None) -> str:
    selected_relative = rel(selected_model, project)
    selected_windows_relative = windows_relative_path(selected_model, project)
    saved_model_relative = f"saved_model/{selected_model.name}"
    saved_model_windows_relative = saved_model_relative.replace("/", "\\")
    saved_model_windows_relative = f"saved_model\\{selected_model.name}"
    selected_linux_relative = normalize_path_text(selected_relative)
    saved_model_linux_relative = saved_model_relative
    default_experiment_name, default_register_model_name = default_mlflow_names(project, selected_model)
    profile = model_profile(project, selected_model, kind)
    input_example = selected_model_input_example_data(project, selected_model, kind)
    config = selected_model_config_data(project, selected_model, kind)
    config_literal = pformat(config, width=100, sort_dicts=False)
    loader = reference_style_loader_code(kind)
    input_example_code = reference_style_input_example_code(
        kind,
        input_example,
        saved_model_linux_relative,
        saved_model_windows_relative,
        selected_windows_relative,
    ).rstrip()
    reference_header = ""
    if reference is not None:
        reference_header = (
            f"# 참조 영역: {reference_scope_display_path(kind, reference)}\n"
            f"# 참조 파일: {reference_display_path(reference)}\n"
        )
    return f'''{reference_header}import io
import inspect
import json
import logging
import os
import sys
from urllib.parse import quote

import mlflow

from aiu_custom.predict import ModelWrapper


logging.getLogger("mlflow").setLevel(logging.ERROR)


# ------------------------------------------------------------
# Windows 인코딩 문제 해결
# ------------------------------------------------------------
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ------------------------------------------------------------
# MLflow 환경 설정
# ------------------------------------------------------------
# 할당받은 MLflow Tracking Server URI / 계정 정보 기재
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)


def load_env_file(path):
    values = {{}}
    if not os.path.isfile(path):
        return values
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


for _env_key, _env_value in load_env_file(os.path.join(project_dir, ".env")).items():
    _export_name = {{
        "mlflow_tracking_uri": "MLFLOW_TRACKING_URI",
        "mlflow_tracking_username": "MLFLOW_TRACKING_USERNAME",
        "mlflow_tracking_password": "MLFLOW_TRACKING_PASSWORD",
        "mlflow_experiment_name": "MLFLOW_EXPERIMENT_NAME",
        "mlflow_register_model_name": "MLFLOW_REGISTER_MODEL_NAME",
    }}.get(_env_key, _env_key)
    if _env_value and not os.environ.get(_export_name):
        os.environ[_export_name] = _env_value


mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "")
mlflow_tracking_username = os.environ.get("MLFLOW_TRACKING_USERNAME", "")
mlflow_tracking_password = os.environ.get("MLFLOW_TRACKING_PASSWORD", "")

mlflow_experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME", {default_experiment_name!r})
mlflow_register_model_name = os.environ.get("MLFLOW_REGISTER_MODEL_NAME", {default_register_model_name!r})

os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "TRUE"
os.environ["MLFLOW_TRACKING_USERNAME"] = mlflow_tracking_username
os.environ["MLFLOW_TRACKING_PASSWORD"] = mlflow_tracking_password


def normalize_local_path(path):
    value = str(path).replace("＼", os.sep).replace("￦", os.sep).replace("₩", os.sep)
    return os.path.abspath(os.path.normpath(value))


def workspace_path(*parts):
    return normalize_local_path(os.path.join(project_dir, *parts))


def split_relative_path(path):
    value = str(path).replace("\\\\", "/").replace("＼", "/").replace("￦", "/").replace("₩", "/")
    return [part for part in value.split("/") if part and part != "."]


def workspace_relative_path(path):
    parts = split_relative_path(path)
    return workspace_path(*parts) if parts else workspace_path(str(path))


def relative_basename(path):
    parts = split_relative_path(path)
    return parts[-1] if parts else os.path.basename(str(path))


def first_existing_file(label, candidates):
    normalized_candidates = [normalize_local_path(candidate) for candidate in candidates]
    for candidate in normalized_candidates:
        if os.path.isfile(candidate) or os.path.isdir(candidate):
            return candidate
    print(f"파일 또는 폴더를 찾을 수 없습니다: {{label}}")
    print("확인한 경로:")
    for candidate in normalized_candidates:
        print(f"- {{candidate}}")
    raise FileNotFoundError(f"{{label}} not found")


def mlflow_artifact_uri(path):
    # MLmodel artifacts.*.uri에는 절대경로가 아니라 프로젝트 기준 상대경로를 기록합니다.
    absolute_path = normalize_local_path(path)
    relative_path = os.path.relpath(absolute_path, project_dir)
    return os.path.normpath(relative_path)


def mlflow_config_artifact_uri(path):
    # config uri는 MLflow/KServe 서버 해석과 문서 기준을 맞추기 위해 POSIX 상대경로를 사용합니다.
    absolute_path = normalize_local_path(path)
    relative_path = os.path.relpath(absolute_path, project_dir)
    return relative_path.replace(chr(92), "/")


def handle_mlflow_connection_error(exc):
    message = str(exc)
    if "sqlite3.OperationalError" in message and "disk I/O error" in message:
        print("MLflow 서버 저장소 오류: SQLite disk I/O error가 발생했습니다.")
        print("원인 후보: MLflow 서버가 sqlite/mlflow.db backend로 떠 있고, 해당 경로 권한/잠금/드라이브 I/O 문제가 있습니다.")
        print("조치: mlflow_tracking_uri를 원격 MLflow 서버 URI로 바꾸거나, 서버 backend-store-uri와 artifact-root 경로 권한을 확인하세요.")
        print("주의: runtest_2.py에서는 로컬 sqlite/file tracking을 사용하지 않습니다.")
        raise SystemExit(1)
    raise exc


missing_mlflow_settings = [
    name
    for name, value in {{
        "mlflow_tracking_uri": mlflow_tracking_uri,
        "mlflow_tracking_username": mlflow_tracking_username,
        "mlflow_tracking_password": mlflow_tracking_password,
    }}.items()
    if not str(value).strip()
]

if missing_mlflow_settings:
    print("원격 MLflow 등록 실행을 위해 MLflow 설정을 .env에 직접 입력하세요.")
    print("missing settings:")
    for name in missing_mlflow_settings:
        print(f"- {{name}}")
    print("비밀번호 값은 출력하지 않습니다.")
    raise SystemExit(0)

try:
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(mlflow_experiment_name)
except Exception as exc:
    handle_mlflow_connection_error(exc)


# ------------------------------------------------------------
# 데이터 준비
# ------------------------------------------------------------
selected_model_path = first_existing_file(
    "selected_model",
    [
        workspace_relative_path({saved_model_windows_relative!r}),
        workspace_relative_path({selected_windows_relative!r}),
        workspace_path("saved_model", {selected_model.name!r}),
        workspace_path({selected_model.name!r}),
    ],
)
model_kind = {kind!r}

{input_example_code}

input_example_path = workspace_path("input_example.json")
with open(input_example_path, "w", encoding="utf-8") as f:
    json.dump(request_input_example, f, indent=2, ensure_ascii=False)

mlflow_input_example = request_input_example


# ------------------------------------------------------------
# 모델 준비
# ------------------------------------------------------------
{loader}

model = load_selected_model()


def compute_metrics(loaded_model):
    return {{
        "model_loaded": 1.0 if loaded_model is not None else 0.0,
    }}


# ------------------------------------------------------------
# Config 저장
# ------------------------------------------------------------
config_dir = "config"
config_dir_path = workspace_path(config_dir)
os.makedirs(config_dir_path, exist_ok=True)

config_path = workspace_path(config_dir, "config.json")

params = {config_literal}
params["model"]["url"] = {saved_model_linux_relative!r}
params["model"]["path"] = {saved_model_windows_relative!r}
params["model"]["runtime_model_path"] = {saved_model_windows_relative!r}
params["model"]["model_relative_path"] = {saved_model_windows_relative!r}
params["model"]["linux_path"] = {saved_model_linux_relative!r}
params["model"]["source_path"] = {selected_windows_relative!r}
params["model"]["linux_source_path"] = {selected_linux_relative!r}

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(params, f, indent=4, ensure_ascii=False)


# ------------------------------------------------------------
# MLflow Dataset 정의
# ------------------------------------------------------------
mlflow_train_ds = None
mlflow_test_ds = None


def mlflow_ui_urls(experiment_id: str, run_id: str | None = None) -> dict[str, str]:
    base_url = str(mlflow_tracking_uri).strip().rstrip("/")
    urls = {{
        "tracking_uri": base_url,
        "experiment_url": f"{{base_url}}/#/experiments/{{experiment_id}}",
        "experiment_models_url": f"{{base_url}}/#/experiments/{{experiment_id}}/models",
        "traces_url": f"{{base_url}}/#/experiments/{{experiment_id}}/traces?startTime=ALL",
    }}
    if run_id:
        urls["run_url"] = f"{{base_url}}/#/experiments/{{experiment_id}}/runs/{{run_id}}"
    if mlflow_register_model_name:
        model_name = quote(mlflow_register_model_name, safe="")
        urls["registered_model_url"] = f"{{base_url}}/#/models/{{model_name}}"
    return urls


def print_mlflow_ui_urls(experiment_id: str, run_id: str | None = None) -> None:
    urls = mlflow_ui_urls(experiment_id, run_id)
    print("MLflow Tracking URI:", urls["tracking_uri"])
    print("MLflow Experiment URI:", urls["experiment_url"])
    print("MLflow Experiment Models URI:", urls["experiment_models_url"])
    print("MLflow Traces URI:", urls["traces_url"])
    if "run_url" in urls:
        print("MLflow Run URI:", urls["run_url"])
    if "registered_model_url" in urls:
        print("MLflow Registered Model URI:", urls["registered_model_url"])


def ensure_registered_model(model_info) -> str:
    model_name = str(mlflow_register_model_name).strip()
    if not model_name:
        return "skipped: mlflow_register_model_name empty"

    try:
        client = mlflow.tracking.MlflowClient()
        client.get_registered_model(model_name)
        return f"exists: {{model_name}}"
    except Exception:
        pass

    model_uri = getattr(model_info, "model_uri", "")
    if not model_uri:
        return "failed: model_uri missing"

    try:
        registered = mlflow.register_model(model_uri=model_uri, name=model_name)
        version = getattr(registered, "version", "unknown")
        return f"registered: {{model_name}}, version={{version}}"
    except Exception as exc:
        return f"failed: {{type(exc).__name__}}: {{exc}}"


# ------------------------------------------------------------
# 모델 학습 / 평가 / 로깅
# ------------------------------------------------------------
with mlflow.start_run(run_name=mlflow_register_model_name) as run:
    if mlflow_train_ds is not None:
        mlflow.log_input(mlflow_train_ds, context="training")
    if mlflow_test_ds is not None:
        mlflow.log_input(mlflow_test_ds, context="test")

    mlflow.set_tag("data.name", "selected_model")
    mlflow.set_tag("model.type", params["model"]["model_name"])
    mlflow.set_tag("framework", model_kind)

    mlflow.log_params(
        {{
            "model_name": params["model"]["model_name"],
            "model_kind": model_kind,
            "model_url": {saved_model_linux_relative!r},
            "model_path": {saved_model_windows_relative!r},
        }}
    )

    metrics = compute_metrics(model)
    mlflow.log_metrics(metrics)

    # --------------------------------------------------------
    # 모델 파일 저장
    # --------------------------------------------------------
    model_dir = "saved_model"
    model_dir_path = workspace_path(model_dir)
    os.makedirs(model_dir_path, exist_ok=True)

    model_path = workspace_path(model_dir, relative_basename(selected_model_path))
    if os.path.abspath(selected_model_path) != os.path.abspath(model_path):
        with open(selected_model_path, "rb") as src, open(model_path, "wb") as dst:
            dst.write(src.read())

    aiu_custom_path = "aiu_custom"

    # --------------------------------------------------------
    # MLflow PyFunc 모델 로깅
    # --------------------------------------------------------
    log_model_args = {{
        "artifact_path": "ai_studio",
        "python_model": ModelWrapper(),
        "code_paths": [aiu_custom_path],
        "artifacts": {{
            "model": mlflow_artifact_uri(model_path),
            "config": mlflow_config_artifact_uri(config_path),
        }},
        "input_example": mlflow_input_example,
        "pip_requirements": "requirements.txt",
    }}

    if mlflow_register_model_name:
        log_model_args["registered_model_name"] = mlflow_register_model_name

    if "name" in inspect.signature(mlflow.pyfunc.log_model).parameters:
        log_model_args["name"] = log_model_args.pop("artifact_path")

    model_info = mlflow.pyfunc.log_model(**log_model_args)
    registry_status = ensure_registered_model(model_info)

    print("MLflow Run ID:", run.info.run_id)
    print("Model URI:", model_info.model_uri)
    print("MLflow Registry:", registry_status)
    print("Selected Model:", selected_model_path)
    print("Model saved:", model_path)
    print("Metrics:", metrics)
    print_mlflow_ui_urls(run.info.experiment_id, run.info.run_id)
'''


def generated_selected_model_runtest_text(project: Path, selected_model: Path, kind: str, reference: Path) -> str:
    selected_relative = rel(selected_model, project)
    text = reference.read_text(encoding="utf-8", errors="ignore")
    default_experiment_name, default_register_model_name = default_mlflow_names(project, selected_model)
    details = MODEL_KIND_DETAILS.get(kind, {})
    load_hint = details.get("load_hint", "custom loader required")
    loader = details.get(
        "loader",
        """def load_selected_model():\n    raise ValueError(f\"unsupported model kind: {MODEL_KIND}\")\n""",
    )
    loader = loader.replace("MODEL_PATH", "SOURCE_MODEL_PATH")
    selected_path_expr = "PROJECT_DIR" + "".join(f" / {json.dumps(part, ensure_ascii=False)}" for part in Path(selected_relative).parts)
    selected_connection_block = f'''
{loader}
{selected_model_input_example_block(kind)}

def normalize_upload_uri(path) -> str:
    value = str(path).replace("＼", os.sep).replace("￦", os.sep).replace("₩", os.sep)
    return os.path.normpath(value)


def server_upload_path(path: Path) -> str:
    # MLmodel artifacts.*.uri에는 절대경로가 아니라 프로젝트 기준 상대경로를 기록합니다.
    return server_relative_path(path)


def server_relative_path(path: Path) -> str:
    try:
        return normalize_upload_uri(Path(path).resolve().relative_to(PROJECT_DIR.resolve()))
    except ValueError:
        return normalize_upload_uri(path)


def validate_server_upload_paths(paths: dict[str, Path]) -> list[str]:
    missing = []
    for name, path in paths.items():
        if not Path(path).exists():
            missing.append(f"{{name}}:{{server_upload_path(path)}}")
    return missing


'''
    original_path_block = '''PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_MODEL_PATH = PROJECT_DIR / "data" / "torch" / "model.pt"
DATA_MODEL_PATH = SOURCE_MODEL_PATH
MODEL_KIND = "pytorch"
MODEL_LOAD_HINT = "torch.load(MODEL_PATH, map_location='cpu')"
INPUT_EXAMPLE_PATH = PROJECT_DIR / "input_example.json"
CONFIG_DIR = PROJECT_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "config.json"
MODEL_DIR = PROJECT_DIR / "saved_model"
MODEL_PATH = MODEL_DIR / "model.pt"'''
    text = text.replace("import mlflow\n", "")
    text = re.sub(r"(?m)^SOURCE_MODEL_PATH\s*=.*$", f"SOURCE_MODEL_PATH = {selected_path_expr}", text, count=1)
    text = re.sub(r"(?m)^DATA_MODEL_PATH\s*=.*$", "DATA_MODEL_PATH = SOURCE_MODEL_PATH", text, count=1)
    text = re.sub(r"(?m)^MODEL_KIND\s*=.*$", f"MODEL_KIND = {kind!r}", text, count=1)
    text = re.sub(r"(?m)^MODEL_LOAD_HINT\s*=.*$", f"MODEL_LOAD_HINT = {load_hint.replace('MODEL_PATH', 'SOURCE_MODEL_PATH')!r}", text, count=1)
    text = re.sub(r"(?m)^INPUT_EXAMPLE_PATH\s*=.*$", 'INPUT_EXAMPLE_PATH = PROJECT_DIR / "input_example.json"', text, count=1)
    text = re.sub(r"(?m)^CONFIG_DIR\s*=.*$", 'CONFIG_DIR = PROJECT_DIR / "config"', text, count=1)
    text = re.sub(r"(?m)^CONFIG_PATH\s*=.*$", 'CONFIG_PATH = CONFIG_DIR / "config.json"', text, count=1)
    text = re.sub(r"(?m)^MODEL_DIR\s*=.*$", 'MODEL_DIR = PROJECT_DIR / "saved_model"', text, count=1)
    if "def load_selected_model(" not in text:
        insert_marker = "\n# AI 환경 설정\n"
        if insert_marker in text:
            text = text.replace(insert_marker, "\n" + selected_connection_block.strip() + "\n" + insert_marker, 1)
        else:
            text = text.replace("configure_utf8_stdio()\n", "configure_utf8_stdio()\n\n" + selected_connection_block.strip() + "\n", 1)
    text = text.replace('mlflow_experiment_name = "pytorch_sample"', f"mlflow_experiment_name = {default_experiment_name!r}")
    text = text.replace('mlflow_register_model_name = "pytorch_sample_model"', f"mlflow_register_model_name = {default_register_model_name!r}")
    text = text.replace("runtest.py에 직접 입력하세요.", ".env에 직접 입력하세요.")
    text = text.replace(
        "    export_mlflow_environment()\n    mlflow.set_tracking_uri(mlflow_tracking_uri)",
        "    try:\n"
        "        import mlflow\n"
        "    except Exception as exc:\n"
        "        print(f\"MLflow import failed. Install packages from requirements.txt first. reason={exc}\")\n"
        "        return\n\n"
        "    export_mlflow_environment()\n"
        "    mlflow.set_tracking_uri(mlflow_tracking_uri)",
    )
    text = re.sub(
        r"(?m)^    model\s*=\s*TinyTorchModel\(.*\)\n",
        "    model = load_selected_model()\n"
        "    # 모델 준비: 선택된 모델을 그대로 사용하고 재학습하지 않습니다.\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^    train_x,\s*train_y,\s*test_x,\s*test_y\s*=\s*prepare_data\(\)\n",
        "    input_example = write_selected_input_example()\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^    train_model\(.*\)\n",
        "    # 선택 모델은 이미 학습된 모델이므로 원본 train_model 호출은 실행하지 않습니다.\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^    metrics\s*=\s*compute_metrics\(.*\)\n",
        "    metrics = {\"model_loaded\": 1.0 if model is not None else 0.0}\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^    input_example\s*=\s*write_input_example\(.*\)\n",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^    config\s*=\s*\{.*\"framework\".*\}\n",
        '    config = {"framework": MODEL_KIND, "model_path": server_relative_path(SOURCE_MODEL_PATH), "model_relative_path": '
        + repr(selected_relative)
        + "}\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^    torch\.save\(.*\)\n",
        "    selected_model_path = SOURCE_MODEL_PATH\n",
        text,
        count=1,
    )
    text = text.replace('        mlflow.set_tag("data.name", "synthetic_tensor(pytorch)")', '        mlflow.set_tag("data.name", "selected_model")')
    text = re.sub(
        r"(?m)^    with mlflow\.start_run\(run_name=mlflow_register_model_name\)(?: as run)?:$",
        "    upload_paths = {\"model\": selected_model_path, \"config\": CONFIG_PATH, \"code\": PROJECT_DIR / \"aiu_custom\"}\n"
        "    missing_upload_paths = validate_server_upload_paths(upload_paths)\n"
        "    if missing_upload_paths:\n"
        "        print(\"서버 업로드 경로를 찾을 수 없습니다. 아래 경로를 확인한 뒤 다시 실행하세요.\")\n"
        "        for item in missing_upload_paths:\n"
        "            print(f\"- {item}\")\n"
        "        return\n\n"
        "    with mlflow.start_run(run_name=mlflow_register_model_name) as run:",
        text,
        count=1,
    )
    text = text.replace("            artifacts={\n                \"model\": MODEL_PATH.as_posix(),", "            artifacts={\n                \"model\": server_upload_path(selected_model_path),")
    text = text.replace("            artifacts={\n                \"model\": MODEL_DIR.as_posix(),", "            artifacts={\n                \"model\": server_upload_path(selected_model_path),")
    text = text.replace("                \"model\": selected_model_path.as_posix(),", "                \"model\": server_upload_path(selected_model_path),")
    text = text.replace("                \"config\": CONFIG_PATH.as_posix(),", "                \"config\": server_upload_path(CONFIG_PATH),")
    text = text.replace(
        "            code_paths=[(Path(__file__).resolve().parent / \"aiu_custom\").as_posix()],",
        "            code_paths=[\"aiu_custom\"],",
    )
    text = text.replace('    print(f"model written: {MODEL_PATH}")', '    print(f"selected model: {selected_model_path}")')
    if "print_mlflow_ui_urls(run.info.experiment_id, run.info.run_id)" not in text:
        text = text.replace(
            '    print("MLflow model logged with artifact_path=\'ai_studio\'")',
            '    print("MLflow model logged with artifact_path=\'ai_studio\'")\n'
            '    print_mlflow_ui_urls(run.info.experiment_id, run.info.run_id)',
            1,
        )
    text = normalize_existing_code_paths(text)
    text = ensure_workspace_code_paths(text)
    return text.rstrip() + "\n"


def generated_runtest_text(project: Path, selected_model: Path, kind: str, reference: Path) -> str:
    generation_reference = runtest_generation_reference(kind, reference)
    return generated_constant_free_runtest_text(project, selected_model, kind, generation_reference)

    reference_text = reference.read_text(encoding="utf-8", errors="ignore")
    selected_relative = rel(selected_model, project)
    preserve_code = preserve_reference_code(reference)
    if preserve_code:
        return generated_selected_model_runtest_text(project, selected_model, kind, reference)
    path_constructor = "Path" if preserve_code else "_aiPath"
    ai_studio_path = project
    default_experiment_name, default_register_model_name = default_mlflow_names(project, selected_model)
    details = MODEL_KIND_DETAILS.get(kind, {})
    required_package = details.get("required_package", "unknown")
    load_hint = details.get("load_hint", "custom loader required")
    replacements = {
        "AI_STUDIO_DIR": f"{path_constructor}(__file__).resolve().parent",
        "PROJECT_DIR": f"{path_constructor}(__file__).resolve().parent",
        "AI_STUDIO_CODE_DIR": 'AI_STUDIO_DIR / "code"',
        "AI_STUDIO_METRICS_DIR": 'AI_STUDIO_DIR / "metrics"',
        "AI_STUDIO_TRACKING_DIR": "AI_STUDIO_DIR",
        "SOURCE_MODEL_PATH": f'AI_STUDIO_DIR / "{selected_relative}"',
        "DATA_MODEL_PATH": "SOURCE_MODEL_PATH",
        "MODEL_PATH": "SOURCE_MODEL_PATH",
        "CONFIG_DIR": 'AI_STUDIO_DIR / "config"',
        "CONFIG_PATH": 'AI_STUDIO_DIR / "config" / "config.json"',
        "MODEL_OUTPUT_DIR": 'AI_STUDIO_DIR / "saved_model"',
        "MODEL_OUTPUT_PATH": 'AI_STUDIO_DIR / "saved_model" / "model.pkl"',
        "MODEL_KIND": repr(kind),
        "MODEL_LOAD_HINT": repr(load_hint),
        "classifier": "load_selected_model()",
        "clf": "load_selected_model()",
        "INPUT_EXAMPLE_PATH": 'AI_STUDIO_DIR / "input_example.json"',
        "dataset": "_aiu_model_input_example()",
        "dataloader": '_aiu_model_input_example()["inputs"]',
        "features": '_aiu_model_input_example()["inputs"][0]["data"]',
        "input_example": "_aiu_write_input_example()",
        "input_example_path": "str(INPUT_EXAMPLE_PATH)",
        "loader": '_aiu_model_input_example()["inputs"]',
        "labels": "[]",
        "model": "load_selected_model()",
        "INPUT_EXAMPLE_FILE": "INPUT_EXAMPLE_PATH",
        "input_example_file": "str(INPUT_EXAMPLE_PATH)",
        "SAMPLE_INPUT_PATH": "INPUT_EXAMPLE_PATH",
        "sample_input_path": "str(INPUT_EXAMPLE_PATH)",
        "sample_data": '_aiu_model_input_example()["inputs"][0]["data"]',
        "sample_input": '_aiu_model_input_example()["inputs"][0]["data"]',
        "batch_size": "1",
        "criterion": "None",
        "estimator": "load_selected_model()",
        "net": "load_selected_model()",
        "optimizer": "None",
        "regressor": "load_selected_model()",
        "summary": "_aiu_model_summary()",
        "summary_file": "_aiu_write_summary()",
        "summary_json": "_aiu_write_summary()",
        "summary_path": "_aiu_write_summary()",
        "model_summary": "_aiu_model_summary()",
        "training_summary": "_aiu_model_summary()",
        "test_dataset": "_aiu_model_input_example()",
        "test_df": "_aiu_model_input_example()",
        "test_loader": '_aiu_model_input_example()["inputs"]',
        "test_x": '_aiu_model_input_example()["inputs"][0]["data"]',
        "test_y": "[]",
        "train_dataset": "_aiu_model_input_example()",
        "train_df": "_aiu_model_input_example()",
        "train_loader": '_aiu_model_input_example()["inputs"]',
        "train_x": '_aiu_model_input_example()["inputs"][0]["data"]',
        "train_y": "[]",
        "x_test": '_aiu_model_input_example()["inputs"][0]["data"]',
        "x_train": '_aiu_model_input_example()["inputs"][0]["data"]',
        "y_test": "[]",
        "y_train": "[]",
        "source_model_path": "str(SOURCE_MODEL_PATH)",
        "data_model_path": "str(DATA_MODEL_PATH)",
        "model_path": "str(MODEL_OUTPUT_PATH)",
        "model_dir": "str(MODEL_OUTPUT_DIR)",
        "model_output_dir": "str(MODEL_OUTPUT_DIR)",
        "model_output_path": "str(MODEL_OUTPUT_PATH)",
        "saved_model_dir": "str(MODEL_OUTPUT_DIR)",
        "config_dir": "str(CONFIG_DIR)",
        "config_path": "str(CONFIG_PATH)",
        "MODEL_FILE": "SOURCE_MODEL_PATH",
        "model_file": "str(MODEL_PATH)",
        "CHECKPOINT_PATH": "SOURCE_MODEL_PATH",
        "checkpoint_path": "str(MODEL_PATH)",
        "MODEL_LOAD_HINT": repr(load_hint) if preserve_code else "ai_LOAD_HINT",
        "model_load_hint": "ai_LOAD_HINT",
        "REQUIRED_PACKAGE": "ai_REQUIRED_PACKAGE",
        "required_package": "ai_REQUIRED_PACKAGE",
        "mlflow_tracking_uri": '""',
        "mlflow_tracking_username": '""',
        "mlflow_tracking_password": '""',
        "mlflow_experiment_name": repr(default_experiment_name),
        "mlflow_register_model_name": repr(default_register_model_name),
    }
    if preserve_code:
        replacements.update(
            {
                "mlflow_tracking_uri": '""',
                "mlflow_experiment_name": repr(default_experiment_name),
                "mlflow_register_model_name": repr(default_register_model_name),
            }
        )
    transformed = transform_reference_text(
        reference_text,
        aiu_injected_block(project, selected_model, kind, reference),
        replacements,
        selected_relative,
        kind,
        load_hint,
        required_package,
        preserve_code=preserve_code,
    )
    if preserve_code:
        transformed = insert_preserved_data_prep_block(transformed, kind)
    transformed = transformed.replace(
        "원격 MLflow 등록 실행을 위해 MLflow/AI Studio 설정을 runtest.py에 직접 입력하세요.",
        "원격 MLflow 등록 실행을 위해 MLflow 설정을 .env에 직접 입력하세요.",
    )
    transformed = normalize_existing_code_paths(transformed)
    transformed = ensure_workspace_code_paths(transformed)
    return transformed.rstrip() + "\n"


def rewrite_top_level_assignment(text: str, name: str, expression: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(name)}\s*=.*$")
    replacement = f"{name} = {expression}"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text


def replace_function_block(text: str, function_name: str, replacement: str) -> str:
    pattern = re.compile(
        rf"(?ms)^def\s+{re.escape(function_name)}\s*\([^)]*\):.*?(?=^def\s+|\Z)"
    )
    if pattern.search(text):
        return pattern.sub(replacement.rstrip() + "\n\n", text, count=1)
    return text.rstrip() + "\n\n" + replacement.rstrip() + "\n"


def generated_inferencetest_text() -> str:
    return f'''#!/usr/bin/env python3
import json
import requests
from urllib.parse import urlparse


req_url = ""


def validate_predict_url(url):
    value = url.strip()
    if not value:
        raise SystemExit("req_url에 원격 추론 :predict URL을 입력한 뒤 다시 실행하세요.")
    parsed = urlparse(value)
    if parsed.scheme not in {{"http", "https"}} or not parsed.netloc:
        raise SystemExit("req_url은 원격 http:// 또는 https:// URL이어야 합니다.")
    if not value.rstrip("/").endswith(":predict"):
        raise SystemExit("req_url은 배포된 원격 추론 URL의 :predict 경로여야 합니다. 예: http://server/v1/models/model:predict")
    return value


req_url = validate_predict_url(req_url)

with open("input_example.json", "r", encoding="utf-8") as f:
    data = json.load(f)

req_msg = json.dumps(data)
headers = {{"Content-Type": "application/json"}}

resp = requests.post(req_url, headers=headers, data=req_msg)

print("status_code:", resp.status_code)
try:
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
except ValueError:
    print(resp.text)


if __name__ == "__main__":
    pass
'''


def generated_model_text(project: Path, selected_model: Path, kind: str) -> str:
    details = MODEL_KIND_DETAILS.get(kind, {})
    required_package = details.get("required_package", "unknown")
    load_hint = details.get("load_hint", "custom loader required")
    loader = details.get(
        "loader",
        """def load_selected_model():\n    raise ValueError(f\"unsupported MODEL_KIND: {MODEL_KIND}\")\n""",
    )
    loader = loader.replace("MODEL_PATH", "_resolve_model_path()")
    return f'''from __future__ import annotations

import json
import os


def _workspace_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_config():
    config_path = _CONTEXT_ARTIFACT_CONFIG_PATH or os.path.join(_workspace_root(), "config", "config.json")
    if not os.path.isfile(config_path):
        return {{}}
    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _config_model():
    config = _load_config()
    model = config.get("model", {{}})
    return model if isinstance(model, dict) else {{}}


def _config_runtime():
    config = _load_config()
    runtime = config.get("runtime", {{}})
    return runtime if isinstance(runtime, dict) else {{}}


_CONTEXT_ARTIFACT_MODEL_PATH = None
_CONTEXT_ARTIFACT_CONFIG_PATH = None


def _normalize_server_path(raw_path):
    value = str(raw_path).replace("\\\\", "/").replace("＼", "/").replace("￦", "/").replace("₩", "/")
    while "//" in value and not value.startswith("//"):
        value = value.replace("//", "/")
    return value


def _looks_like_windows_drive_path(path):
    return len(path) >= 3 and path[1:3] == ":/" and path[0].isalpha()


def _reject_windows_path_on_linux(path, source):
    if os.name != "nt" and _looks_like_windows_drive_path(path):
        raise ValueError(
            f"{{source}}_windows_path_on_linux: KServe 컨테이너에서는 Linux artifact 경로를 사용해야 합니다. "
            "context.artifacts 기반 경로를 확인하세요."
        )


def _first_existing_path(candidates):
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return os.path.normpath(candidate)
    return os.path.normpath(candidates[0]) if candidates else None


def _split_relative_path(path):
    value = _normalize_server_path(path)
    return [part for part in value.split("/") if part and part != "."]


def _join_workspace_relative(workspace_root, path):
    parts = _split_relative_path(path)
    return os.path.join(workspace_root, *parts) if parts else os.path.join(workspace_root, str(path))


def _path_basename(path):
    parts = _split_relative_path(path)
    return parts[-1] if parts else os.path.basename(str(path))


def _resolve_model_path():
    if _CONTEXT_ARTIFACT_MODEL_PATH is not None:
        return _CONTEXT_ARTIFACT_MODEL_PATH
    model = _config_model()
    raw_path = model.get("path") or model.get("saved_model_path") or model.get("model_relative_path") or model.get("runtime_model_path") or model.get("relative_path") or model.get("source_path")
    if not raw_path:
        raise ValueError("selected_model_path_missing: selected model metadata")
    path = _normalize_server_path(raw_path)
    _reject_windows_path_on_linux(path, "selected_model")
    workspace_root = _workspace_root()
    if os.path.isabs(path):
        return _first_existing_path([path])
    return _first_existing_path([
        _join_workspace_relative(workspace_root, path),
        os.path.join(workspace_root, "saved_model", _path_basename(path)),
        os.path.join(workspace_root, _path_basename(path)),
    ])


def _context_artifact_path(context, name):
    if context is None or not hasattr(context, "artifacts"):
        return None
    artifact_path = context.artifacts.get(name)
    if not artifact_path:
        return None
    path = _normalize_server_path(artifact_path)
    _reject_windows_path_on_linux(path, f"context_artifact_{{name}}")
    workspace_root = _workspace_root()
    if os.path.isabs(path):
        return _first_existing_path([path])
    return _first_existing_path([
        _join_workspace_relative(workspace_root, path),
        os.path.join(workspace_root, _path_basename(path)),
    ])


def _model_kind():
    return str(_config_model().get("model_kind") or _config_model().get("kind") or "{kind}")


MODEL_KIND = _model_kind()
ai_REQUIRED_PACKAGE = str(_config_model().get("required_package") or "{required_package}")
ai_LOAD_HINT = str(_config_model().get("load_hint") or "{load_hint}")

# Ai Studio 변환: model.py에는 선택 모델 경로 설정을 직접 쓰지 않습니다.
# 모델 위치와 종류는 선택 모델 정보에서 읽습니다.
# MODEL_KIND={kind}, loader={load_hint}

{loader}


def _payload_to_model_input(payload):
    if isinstance(payload, dict):
        if isinstance(payload.get("inputs"), list) and payload["inputs"]:
            first_input = payload["inputs"][0]
            if isinstance(first_input, dict) and "data" in first_input:
                return {{
                    "data": first_input.get("data"),
                    "shape": first_input.get("shape"),
                }}
        for key in ["data", "instances", "features", "x"]:
            if key in payload:
                return payload[key]
    return payload


class ModelWrapper:
    def __init__(self):
        self.model = None
        self.artifact_model_path = None
        self.config_path = None

    def load_context(self, context=None):
        if self.model is None:
            artifact_model_path = _context_artifact_path(context, "model")
            config_path = _context_artifact_path(context, "config")
            self.artifact_model_path = artifact_model_path
            self.config_path = config_path
            if artifact_model_path is not None:
                global _CONTEXT_ARTIFACT_MODEL_PATH
                _CONTEXT_ARTIFACT_MODEL_PATH = artifact_model_path
            if config_path is not None:
                global _CONTEXT_ARTIFACT_CONFIG_PATH
                _CONTEXT_ARTIFACT_CONFIG_PATH = config_path
            self.model = load_selected_model()
        return self.model

    def predict(self, context, model_input):
        model = self.load_context(context)
        payload = _payload_to_model_input(model_input)

        if MODEL_KIND == "onnx":
            input_name = model.get_inputs()[0].name
            return model.run(None, {{input_name: payload}})

        if MODEL_KIND in {{"pytorch", "safetensors"}}:
            return _predict_torch_like(model, payload)

        if hasattr(model, "predict"):
            return model.predict(payload)

        if callable(model):
            return model(payload)

        return {{
            "status": "loaded",
            "model_kind": MODEL_KIND,
            "model_path": str(_resolve_model_path()),
            "input": payload,
        }}


def _predict_torch_like(model, payload):
    try:
        import torch

        if hasattr(model, "eval"):
            model.eval()
        shape = None
        if isinstance(payload, dict) and "data" in payload:
            shape = payload.get("shape")
            payload = payload.get("data")
        tensor_input = payload if hasattr(payload, "shape") else torch.tensor(payload, dtype=torch.float32)
        if shape:
            try:
                tensor_input = tensor_input.reshape(tuple(int(item) for item in shape))
            except Exception:
                pass
        with torch.no_grad():
            result = model(tensor_input) if callable(model) else model
        if hasattr(result, "detach"):
            result = result.detach().cpu().numpy()
        return result
    except Exception as exc:
        return {{
            "status": "loaded",
            "model_kind": MODEL_KIND,
            "model_path": str(_resolve_model_path()),
            "input": payload,
            "inference_error": str(exc),
        }}


def predict(payload):
    return ModelWrapper().predict(None, payload)
'''


def replace_class_method_block(text: str, class_name: str, method_name: str, replacement: str) -> str:
    pattern = re.compile(
        rf"(?ms)^class\s+{re.escape(class_name)}\b.*?(?=^(?:class|def)\s+|\Z)"
    )
    class_match = pattern.search(text)
    if not class_match:
        return text
    class_text = class_match.group(0)
    method_pattern = re.compile(
        rf"(?ms)^    def\s+{re.escape(method_name)}\s*\([^)]*\):.*?(?=^    def\s+|\Z)"
    )
    if method_pattern.search(class_text):
        updated_class = method_pattern.sub(replacement.rstrip() + "\n\n", class_text, count=1)
    else:
        updated_class = class_text.rstrip() + "\n\n" + replacement.rstrip() + "\n"
    return text[: class_match.start()] + updated_class + text[class_match.end() :]


def ensure_predict_imports(text: str) -> str:
    required_imports = [
        "import json",
        "from pathlib import Path",
        "import mlflow.pyfunc",
        "import torch",
    ]
    lines = text.splitlines()
    insert_index = 0
    while insert_index < len(lines) and (
        lines[insert_index].startswith("from __future__")
        or lines[insert_index].strip() == ""
    ):
        insert_index += 1
    for import_line in reversed(required_imports):
        if import_line not in text:
            lines.insert(insert_index, import_line)
    return "\n".join(lines).rstrip() + "\n"


def insert_before_model_wrapper_or_append(text: str, block: str) -> str:
    if "class ModelWrapper" in text:
        return text.replace("\nclass ModelWrapper", block.rstrip() + "\n\nclass ModelWrapper", 1)
    return text.rstrip() + "\n\n" + block.strip() + "\n"


def generated_predict_text(template_text: str, kind: str) -> str:
    text = template_text.strip() if template_text.strip() else (TEMPLATE_SAMPLE_DIR / "aiu_custom" / "predict.py").read_text(encoding="utf-8", errors="ignore")
    text = ensure_predict_imports(text)

    helper_block = f'''

def _payload_to_model_input(payload):
    if isinstance(payload, dict):
        if "inputs" in payload and payload["inputs"]:
            first_input = payload["inputs"][0]
            if isinstance(first_input, dict) and "data" in first_input:
                return first_input["data"]
        for key in ("data", "instances", "features", "x"):
            if key in payload:
                return payload[key]
    return payload


def _to_jsonable(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def _ai_payload_to_tensor(payload):
    if hasattr(payload, "shape"):
        return payload
    return torch.tensor(payload, dtype=torch.float32)


def _load_selected_model(model_path: Path, model_kind: str):
    if model_kind in {{"pytorch", "safetensors"}}:
        if model_kind == "safetensors":
            from safetensors.torch import load_file

            return load_file(str(model_path))
        try:
            return torch.load(model_path, map_location="cpu", weights_only=False)
        except TypeError:
            return torch.load(model_path, map_location="cpu")

    if model_kind in {{"sklearn_pickle", "sklearn_joblib"}}:
        import joblib

        return joblib.load(model_path)

    if model_kind == "onnx":
        import onnxruntime as ort

        return ort.InferenceSession(str(model_path))

    if model_kind in {{"tensorflow", "keras", "h5"}}:
        import tensorflow as tf

        return tf.keras.models.load_model(model_path)

    if model_kind in {{"xgboost_bst", "xgboost_ubj"}}:
        import xgboost as xgb

        booster = xgb.Booster()
        booster.load_model(str(model_path))
        return booster

    raise ValueError(f"unsupported MODEL_KIND: {{model_kind}}")


def _predict_loaded_model(model, model_kind: str, payload):
    if model_kind == "onnx":
        input_name = model.get_inputs()[0].name
        return _to_jsonable(model.run(None, {{input_name: payload}}))

    if model_kind in {{"pytorch", "safetensors"}}:
        if not callable(model):
            return {{
                "status": "loaded",
                "model_kind": model_kind,
                "detail": "선택 모델은 로드되었지만 callable PyTorch 모델이 아닙니다.",
            }}
        tensor_input = _ai_payload_to_tensor(payload)
        if hasattr(model, "eval"):
            model.eval()
        with torch.no_grad():
            return _to_jsonable(model(tensor_input))

    if hasattr(model, "predict"):
        return _to_jsonable(model.predict(payload))

    if callable(model):
        return _to_jsonable(model(payload))

    return {{
        "status": "loaded",
        "model_kind": model_kind,
        "input": payload,
    }}
'''
    if "def _load_selected_model(" not in text:
        text = insert_before_model_wrapper_or_append(text, helper_block)

    load_context_block = f'''    def load_context(self, context):
        config_path = Path(_normalize_path(context.artifacts["config"]))
        model_path = Path(_normalize_path(context.artifacts["model"]))
        config = json.loads(config_path.read_text(encoding="utf-8"))

        model_config = config.get("model", config)
        self.model_kind = str(model_config.get("model_kind") or model_config.get("kind") or "{kind}")
        self.model_path = model_path
        self.model = _load_selected_model(model_path, self.model_kind)
        if hasattr(self.model, "eval"):
            self.model.eval()

'''

    predict_block = '''    def predict(self, context, model_input, params=None):
        if not hasattr(self, "model"):
            return {
                "status": "model_not_loaded",
                "detail": "MLflow calls load_context() before predict().",
                "input": model_input,
            }
        payload = _payload_to_model_input(model_input)
        return _predict_loaded_model(self.model, self.model_kind, payload)
'''

    text = replace_class_method_block(text, "ModelWrapper", "load_context", load_context_block)
    text = replace_class_method_block(text, "ModelWrapper", "predict", predict_block)
    if "class ModelWrapper" not in text:
        text = text.rstrip() + "\n\nclass ModelWrapper(mlflow.pyfunc.PythonModel):\n" + load_context_block.rstrip() + "\n\n" + predict_block.rstrip() + "\n"
    if "def predict(payload)" not in text:
        text = text.rstrip() + "\n\n\ndef predict(payload):\n    wrapper = ModelWrapper()\n    return wrapper.predict(None, payload)\n"
    return text.rstrip() + "\n"


def requirements_packages_for_kind(kind: str) -> tuple[list[str], list[str], list[str]]:
    if REQUIRED_REQUIREMENTS_FILE.exists():
        required = [
            line.strip()
            for line in REQUIRED_REQUIREMENTS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    else:
        required = [
            "mlflow==3.10.0",
            "torch==2.12.1",
            "numpy==1.26.4",
            "kserve==0.15.0",
            "pandas==2.2.3",
        ]
    extras_by_kind = {
        "sklearn_pickle": ["scikit-learn==1.7.0", "joblib==1.5.1"],
        "sklearn_joblib": ["scikit-learn==1.7.0", "joblib==1.5.1"],
        "safetensors": ["safetensors==0.5.3"],
        "xgboost_bst": ["xgboost==3.0.2"],
        "xgboost_ubj": ["xgboost==3.0.2"],
    }
    inference_requirements = ["requests==2.32.4"]
    additional = inference_requirements + extras_by_kind.get(kind, [])
    packages = required + additional
    unique_packages: list[str] = []
    seen: set[str] = set()
    for package in packages:
        key = package.split("==", 1)[0].lower()
        if key in seen:
            continue
        seen.add(key)
        unique_packages.append(package)
    return required, additional, unique_packages


def generated_requirements_text(kind: str) -> str:
    _required, _additional, packages = requirements_packages_for_kind(kind)
    return "\n".join(packages) + "\n"


def ast_literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def existing_mlflow_settings(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return {}
    values: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = ast_literal_string(node.value)
        if value is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in MLFLOW_SETTING_NAMES and value:
                values[target.id] = value
    return values


def apply_existing_mlflow_settings(text: str, settings: dict[str, str]) -> str:
    for name, value in settings.items():
        text = re.sub(
            rf"(?m)^{re.escape(name)}\s*=\s*['\"].*?['\"]\s*$",
            f"{name} = {value!r}",
            text,
            count=1,
        )
    return text


def write_runtest_2(project: Path, selected_model: Path, kind: str, reference: Path, execute: bool, force: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "runtest_2.py"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    generation_reference = runtest_generation_reference(kind, reference)
    reference_digest_before = file_sha256(reference)
    existed_before = target.exists()
    if execute:
        target.parent.mkdir(parents=True, exist_ok=True)
        preserved_settings = existing_mlflow_settings(target)
        generated_text = generated_runtest_text(project, selected_model, kind, reference)
        target.write_text(apply_existing_mlflow_settings(generated_text, preserved_settings), encoding="utf-8")
        reference_digest_after = file_sha256(reference)
        if reference_digest_after != reference_digest_before:
            failures.append(f"reference_entrypoint_modified:{rel(reference, project)}")
            return changed, skipped, failures
    changed.append(
        "runtest_2.py transformed for selected model"
        if existed_before
        else "runtest_2.py transformed for selected model"
    )
    if generation_reference.resolve() != reference.resolve():
        changed.append(f"runtest_2.py reference scope: {reference_scope_display_path(kind, generation_reference)}")
    return changed, skipped, failures


def write_requirements(project: Path, kind: str, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "requirements.txt"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    existed_before = target.exists()
    if execute:
        target.write_text(generated_requirements_text(kind), encoding="utf-8")
    changed.append("requirements.txt transformed for selected model")
    return changed, skipped, failures


def write_input_example(project: Path, selected_model: Path, kind: str, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "input_example.json"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    existed_before = target.exists()
    if execute:
        target.write_text(
            json.dumps(selected_model_input_example_data(project, selected_model, kind), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    changed.append("input_example.json transformed for selected model")
    return changed, skipped, failures


def write_config_json(project: Path, selected_model: Path, kind: str, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "config" / "config.json"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    existed_before = target.exists()
    if execute:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(selected_model_config_data(project, selected_model, kind), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    changed.append("config/config.json transformed for selected model")
    return changed, skipped, failures


def write_inferencetest(project: Path, selected_model: Path, kind: str, reference: Path, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "inferencetest.py"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    existed_before = target.exists()
    if execute:
        reference_digest_before = file_sha256(reference)
        target.write_text(generated_inferencetest_text(), encoding="utf-8")
        reference_digest_after = file_sha256(reference)
        if reference_digest_after != reference_digest_before:
            failures.append(f"reference_entrypoint_modified:{rel(reference, project)}")
            return changed, skipped, failures
    changed.append("inferencetest.py transformed for selected model")
    return changed, skipped, failures


def write_aiu_model(project: Path, selected_model: Path, kind: str, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "aiu_custom" / "model.py"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    existed_before = target.exists()
    if execute:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(generated_model_text(project, selected_model, kind), encoding="utf-8")
    changed.append("aiu_custom/model.py transformed for selected model")
    return changed, skipped, failures


def write_aiu_predict(project: Path, selected_model: Path, kind: str, execute: bool) -> tuple[list[str], list[str], list[str]]:
    target = project / "aiu_custom" / "predict.py"
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []
    if not execute:
        skipped.append("aiu_custom/predict.py deployment entrypoint:dry_run")
        return changed, skipped, failures
    existed_before = target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        template_text = target.read_text(encoding="utf-8", errors="ignore")
    else:
        template_path = TEMPLATE_SAMPLE_DIR / "aiu_custom" / "predict.py"
        template_text = template_path.read_text(encoding="utf-8", errors="ignore") if template_path.is_file() else ""
    target.write_text(generated_predict_text(template_text, kind), encoding="utf-8")
    changed.append("aiu_custom/predict.py transformed for selected model")
    return changed, skipped, failures


def sync_selected_model_runtime(
    project: Path,
    selected_model: Path,
    kind: str,
    runtime_reference: Path,
    execute: bool,
    copy_template: bool = True,
) -> tuple[list[str], list[str], list[str]]:
    changed: list[str] = []
    skipped: list[str] = []
    failures: list[str] = []

    runtime_steps = [
        ensure_aiu_custom_template_copied(project, execute),
        read_copied_template_files(project, execute),
        ensure_runtime_directories(project, execute),
        write_requirements(project, kind, execute),
        write_input_example(project, selected_model, kind, execute),
        write_config_json(project, selected_model, kind, execute),
        write_saved_model(project, selected_model, execute),
        write_inferencetest(project, selected_model, kind, runtime_reference, execute),
        write_aiu_model(project, selected_model, kind, execute),
        write_aiu_predict(project, selected_model, kind, execute),
    ]
    if copy_template:
        runtime_steps.insert(0, copy_template_sample_folder(project, execute))

    for next_changed, next_skipped, next_failures in runtime_steps:
        changed.extend(next_changed)
        skipped.extend(next_skipped)
        failures.extend(next_failures)

    return changed, skipped, failures


def verify_selected_model_conversion(project: Path, selected_model: Path, kind: str, models: list[Path], execute: bool) -> tuple[list[str], list[str], list[str]]:
    if not execute:
        return [], ["selected_model_conversion_verification:dry_run"], []

    selected_relative = rel(selected_model, project)
    selected_windows_relative = windows_relative_path(selected_model, project)
    saved_model_relative = f"saved_model/{selected_model.name}"
    saved_model_windows_relative = saved_model_relative.replace("/", "\\")
    required_text_files = [
        project / "runtest_2.py",
        project / "aiu_custom" / "model.py",
        project / "inferencetest.py",
        project / "input_example.json",
        project / "config" / "config.json",
    ]
    changed = ["선택 모델 연결부 변환 검증"]
    failures: list[str] = []
    direct_selected_path_files = {
        "runtest_2.py",
        "input_example.json",
        "config/config.json",
    }

    for path in required_text_files:
        display_path = rel(path, project)
        if not path.is_file():
            failures.append(f"selected_model_conversion_missing:{display_path}")
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        normalized_text = normalize_path_text(text)
        if (
            display_path in direct_selected_path_files
            and selected_relative not in normalized_text
            and saved_model_relative not in normalized_text
            and selected_windows_relative not in text
            and saved_model_windows_relative not in text
        ):
            failures.append(f"selected_model_not_reflected:{display_path}:{selected_relative}")
        if display_path == "runtest_2.py":
            has_selected_path_connection = (
                "selected_model_path =" in text
                or "def selected_model_path(" in text
            )
            if "def load_selected_model(" not in text or not has_selected_path_connection:
                failures.append("runtest_2_selected_model_loader_missing:runtest_2.py")
            if (
                selected_relative not in normalized_text
                and saved_model_relative not in normalized_text
                and selected_windows_relative not in text
                and saved_model_windows_relative not in text
            ):
                failures.append("runtest_2_selected_artifact_path_missing:runtest_2.py")
            forbidden_runtest2_markers = [
                "PROJECT_DIR = Path(__file__).resolve().parent",
                "SOURCE_MODEL_PATH",
                "DATA_MODEL_PATH",
                "MODEL_KIND",
                "MODEL_LOAD_HINT",
                "INPUT_EXAMPLE_PATH",
                "CONFIG_DIR",
                "CONFIG_PATH",
                "MODEL_DIR",
                "MODEL_PATH =",
            ]
            embedded_constants = [name for name in forbidden_runtest2_markers if name in text]
            if embedded_constants:
                failures.append(f"runtest_2_selected_model_constants_forbidden:{','.join(embedded_constants)}")
            forbidden_helpers = [
                "_workspace_dir",
                "_selected_model_path",
                "_selected_model_kind",
                "selected_model_source_relative_path",
                "selected_model_runtime_relative_path",
                "selected_model_relative_path",
            ]
            embedded = [name for name in forbidden_helpers if name in text]
            if embedded:
                failures.append(f"runtest_2_should_preserve_format_without_helpers:{','.join(embedded)}")
        if display_path == "aiu_custom/model.py":
            if "def load_selected_model(" not in text:
                failures.append("aiu_custom_model_loader_missing:aiu_custom/model.py")
            if "_resolve_model_path()" not in text:
                failures.append("aiu_custom_model_selected_path_resolver_missing:aiu_custom/model.py")
            if kind not in text:
                failures.append(f"aiu_custom_model_kind_not_reflected:aiu_custom/model.py:{kind}")
        if display_path == "inferencetest.py":
            for marker in ['req_url = ""', 'requests.post(req_url', 'input_example.json']:
                if marker not in text:
                    failures.append(f"inferencetest_template_missing:{marker}")
        if display_path == "config/config.json":
            try:
                config = json.loads(text)
            except json.JSONDecodeError as exc:
                failures.append(f"selected_model_config_invalid_json:{exc.lineno}")
                config = {}
            model_config = config.get("model", {}) if isinstance(config, dict) else {}
            config_path = model_config.get("path") or model_config.get("model_relative_path") or model_config.get("runtime_model_path")
            config_source_path = model_config.get("source_path") or model_config.get("original_path")
            config_kind = model_config.get("model_kind")
            if normalize_path_text(str(config_path or "")) != normalize_path_text(saved_model_relative):
                failures.append(f"selected_model_config_path_mismatch:{config_path}->{saved_model_relative}")
            if normalize_path_text(str(config_source_path or "")) != normalize_path_text(selected_relative):
                failures.append(f"selected_model_config_source_path_mismatch:{config_source_path}->{selected_relative}")
            config_url = model_config.get("url")
            expected_url = saved_model_relative
            if config_url != expected_url:
                failures.append(f"selected_model_config_url_mismatch:{config_url}->{expected_url}")
            if config_kind != kind:
                failures.append(f"selected_model_config_kind_mismatch:{config_kind}->{kind}")

        for other_model in models:
            other_relative = rel(other_model, project)
            other_absolute = absolute_path_text(other_model)
            if display_path in direct_selected_path_files and other_relative != selected_relative and (other_relative in text or other_absolute in text):
                failures.append(f"stale_model_path_in_generated:{display_path}:{other_relative}")

    locked_model, locked_kind, locked_error = selected_model_from_config(project)
    if locked_error:
        failures.append(locked_error)
    elif locked_model is None or locked_model.resolve() != selected_model.resolve():
        locked_display = rel(locked_model, project) if locked_model else "missing"
        failures.append(f"selected_model_config_mismatch:{locked_display}->{selected_relative}")
    elif locked_kind and locked_kind != kind:
        failures.append(f"selected_model_kind_mismatch:{locked_kind}->{kind}")

    return changed, [], failures


def build_report(args: argparse.Namespace) -> PreparedModelReport:
    project = resolve_workspace_project(args.project)
    if not project.exists():
        raise FileNotFoundError(f"project folder not found: {project}")
    if is_filesystem_root(project):
        raise ValueError("drive/root scan is not allowed. 선택한 워크스페이스 루트로 이동한 뒤 --project . 로 실행하세요.")
    if is_opencode_sample_source(project):
        raise ValueError(".opencode/는 분석 대상이 아닙니다. 선택한 실제 모델 프로젝트 폴더를 --project로 지정하세요.")

    data_root = project / "data"
    models = scan_model_artifacts(project)
    training_code = scan_training_code(project)
    data_files = scan_data_files(project)
    entrypoints = find_python_entrypoints(project)
    model_paths = [rel(path, project) for path in models]
    training_code_paths = [rel(path, project) for path in training_code]
    data_paths = [rel(path, project) for path in data_files]
    entrypoint_paths = [rel(path, project) for path in entrypoints]
    requested_model = requested_model_path_from_raw(project, models, args.model)
    locked_model = current_selected_model_path(project)
    selected_model, selection_error = resolve_model_selection(project, models, args.model)
    selected_kind = model_kind(selected_model) if selected_model else None
    work_project = selected_model_work_dir(project, selected_model) if selected_model else project
    if args.sync_runtime:
        selected_model, selected_kind, selection_error = selected_model_from_config(project)
        if selected_model is not None and selected_kind is None:
            selected_kind = model_kind(selected_model)
        requested_model = selected_model
        locked_model = selected_model
        work_project = selected_model_work_dir(project, selected_model) if selected_model else project
    model_selection_locked = False

    report = PreparedModelReport(
        project_path=str(project),
        data_root=str(data_root),
        model_artifact_paths=model_paths,
        training_code_paths=training_code_paths,
        data_file_paths=data_paths,
        entrypoint_paths=entrypoint_paths,
        selected_model_path=rel(selected_model, project) if selected_model else None,
        model_kind=selected_kind,
        reference_entrypoint=None,
        generated_entrypoint="runtest_2.py",
        generated_inference_test="inferencetest.py",
        execute=args.execute,
        work_project_path=rel(work_project, project) if selected_model else None,
        requested_model_path=rel(requested_model, project) if requested_model else None,
        model_selection_locked=model_selection_locked,
        locked_model_path=rel(locked_model, project) if locked_model else None,
    )
    if selected_kind:
        required_requirements, additional_requirements, _packages = requirements_packages_for_kind(selected_kind)
        report.required_requirements = required_requirements
        report.additional_requirements = additional_requirements

    if not models:
        if training_code:
            report.next_steps.append("Case 1: 학습 코드가 감지되었습니다. 2번 목록의 학습 코드 후보에서 사용할 entrypoint를 확인하세요.")
            report.next_steps.append(f"감지된 학습 코드: {', '.join(training_code_paths[:5])}")
            report.next_steps.append(training_code_run_hint(project, training_code_paths))
            return report
        elif entrypoints and data_files:
            report.failures.append("model_artifact_missing_entrypoint_with_csv")
            report.next_steps.append("CSV 파일은 모델이 아니라 데이터로 판단합니다. Python 실행파일을 모델 생성/등록 entrypoint로 사용하세요.")
            report.next_steps.append(f"감지된 CSV 데이터: {', '.join(data_paths[:5])}")
            report.next_steps.append(f"감지된 Python 실행파일: {', '.join(entrypoint_paths[:5])}")
            report.next_steps.append(f"실행 예: python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint {powershell_quote_path(Path(entrypoint_paths[0]))} --execute")
        elif data_files:
            report.failures.append("csv_data_without_model_entrypoint")
            report.next_steps.append("CSV 파일은 모델이 아니라 데이터입니다. 모델을 생성/로드/등록하는 Python 실행파일을 프로젝트 루트에 넣어주세요.")
            report.next_steps.append(f"감지된 CSV 데이터: {', '.join(data_paths[:5])}")
        elif entrypoints:
            report.failures.append("entrypoint_without_model_artifact")
            report.next_steps.append("모델 artifact는 없지만 Python 실행파일이 있습니다. 해당 파일이 모델 생성/등록 entrypoint인지 확인해 실행하세요.")
            report.next_steps.append(f"실행 예: python .opencode/scripts/04-train-model/run_training.py --project . --entrypoint {powershell_quote_path(Path(entrypoint_paths[0]))} --execute")
        else:
            report.failures.append("model_artifact_paths_empty")
            report.next_steps.append("현재 프로젝트 루트 바로 아래 또는 data/** 아래에 .pkl, .joblib, .pt, .pth, .onnx, .keras, .h5, .safetensors, .bst, .ubj 모델 파일을 넣어주세요.")
    if selection_error and (models or args.model):
        report.failures.append(selection_error)
        if models:
            if selection_error == "model_path_must_be_project_relative":
                report.next_steps.append("모델 경로는 Windows 절대경로가 아니라 워크스페이스 기준 상대경로로 입력하세요.")
                report.next_steps.append(r"예: --model data\pytorch_cnn\cnn_model.pt 또는 --model data/pytorch_cnn/cnn_model.pt")
            else:
                report.next_steps.append("사용할 모델을 번호 또는 상대경로로 선택하세요. 예: --model 1, --model model.joblib, --model data/torch/model.pt")
            report.next_steps.append(
                r"2번 모델 선택 실행: python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>"
            )
    if selected_model and not ensure_under_project(project, selected_model):
        report.failures.append("selected_model_outside_project")
        report.next_steps.append("선택 모델은 현재 워크스페이스 루트 아래 상대경로여야 합니다.")
    if selected_model and selected_kind is None:
        report.failures.append("unsupported_model_suffix")

    if report.failures:
        return report
    current_selected = current_selected_model_path(project)
    if not args.model and current_selected is not None and selected_model is not None and current_selected.resolve() == selected_model.resolve():
        report.warnings.append(f"selected_model_reused:{rel(selected_model, project)}")
        report.next_steps.append(f"TODO 2는 이미 완료되어 현재 선택 모델을 유지합니다: {rel(selected_model, project)}")
    explicit_model_selection = bool(args.model and not is_selected_model_alias(args.model) and not args.sync_runtime)
    if (
        explicit_model_selection
        and not args.select_only
        and current_selected is not None
        and selected_model is not None
        and current_selected.resolve() != selected_model.resolve()
    ):
        attempted = rel(selected_model, project)
        report.selected_model_path = rel(current_selected, project)
        report.model_kind = model_kind(current_selected)
        report.locked_model_path = rel(current_selected, project)
        report.warnings.append(f"selected_model_change_blocked:{rel(current_selected, project)}!={attempted}")
        report.failures.append("selected_model_change_blocked_use_step2")
        report.next_steps.append(
            "이미 선택된 모델이 있습니다. 모델을 바꾸려면 2번 모델 선택 스크립트를 먼저 실행하세요: "
            "python .opencode/scripts/02-model-select/select_model.py --project . --model <번호|경로>"
        )
        report.next_steps.append(
            "4번 템플릿 변환은 처음 선택한 모델을 유지하므로 항상 --model selected로 실행합니다."
        )
        return report
    if (
        args.model
        and current_selected is not None
        and selected_model is not None
        and current_selected.resolve() != selected_model.resolve()
    ):
        report.warnings.append(
            f"selected_model_changed:{rel(current_selected, project)}->{rel(selected_model, project)}"
        )
        report.next_steps.append(f"선택 모델을 새 값으로 변경합니다: {rel(selected_model, project)}")

    if args.select_only or explicit_model_selection:
        changed, skipped, failures = write_config_json(project, selected_model, selected_kind, args.execute)
        report.prepared_paths.extend(["selected_model locked"] + changed)
        report.skipped.extend(skipped)
        report.failures.extend(failures)
        work_changed, work_skipped, work_failures = ensure_model_work_dir(project, work_project, args.execute)
        report.prepared_paths.extend(work_changed)
        report.skipped.extend(work_skipped)
        report.failures.extend(work_failures)
        if args.execute and not report.failures:
            report.next_steps.extend(
                [
                    "2번 모델 선택 완료: 선택 모델을 고정했습니다.",
                    f"작업 폴더: {rel(work_project, project)}",
                    "3번 환경 검증을 실행하세요.",
                    "4번 템플릿 변환은 사용자가 선택했을 때만 실행합니다.",
                    f"python .opencode/scripts/03-environment-check/check_environment.py --project {rel(work_project, project)} --entrypoint runtest_2.py",
                ]
            )
        elif not report.failures:
            report.next_steps.append("검토 후 --execute를 붙여 선택 모델을 고정하세요. 템플릿 변환은 --model selected --execute로 별도 실행합니다.")
        return report

    if args.sync_runtime:
        runtime_reference = work_project / "runtest_2.py"
        reference = find_reference_entrypoint(work_project, selected_kind)
        report.reference_entrypoint = rel(reference, project) if reference else None
        if reference is None:
            report.failures.append("reference_entrypoint_missing:runtest.py_or_run_test.py")
            report.next_steps.append(f"모델 작업 폴더에 기존 runtest.py 또는 run_test.py를 넣어주세요: {rel(work_project, project)}")
            return report

        changed, write_skipped, write_failures = write_runtest_2(work_project, selected_model, selected_kind, reference, args.execute, args.force)
        report.prepared_paths.extend(changed)
        report.skipped.extend(write_skipped)
        report.failures.extend(write_failures)
        if report.failures:
            return report

        if not runtime_reference.is_file():
            report.failures.append("runtest_2_missing")
            report.next_steps.append("먼저 모델 선택 후 runtest_2.py 변환을 실행하세요.")
            return report

        runtime_changed, runtime_skipped, runtime_failures = sync_selected_model_runtime(
            work_project,
            selected_model,
            selected_kind,
            runtime_reference,
            args.execute,
        )
        report.prepared_paths.extend(runtime_changed)
        report.skipped.extend(runtime_skipped)
        report.failures.extend(runtime_failures)

        if args.execute and not report.failures:
            report.next_steps.extend(
                [
                    "후속 변환 완료: 복사된 템플릿 폴더 내부에서 선택 모델 경로와 모델 형식 연결부를 수정했습니다.",
                    "선택 모델 변환 완료: 모델 목록 확인 -> 모델 선택 -> 템플릿 변환",
                    "다음은 3번 환경 검증입니다.",
                    f"python .opencode/scripts/03-environment-check/check_environment.py --project {rel(work_project, project)} --entrypoint runtest_2.py",
                ]
            )
        elif not report.failures:
            report.next_steps.append("검토 후 --execute를 붙여 선택 모델 기준으로 런타임 폴더/파일을 변환하세요.")
        return report

    template_changed, template_skipped, template_failures = copy_template_sample_folder(work_project, args.execute)
    report.prepared_paths.extend(template_changed)
    report.skipped.extend(template_skipped)
    report.failures.extend(template_failures)
    if report.failures:
        return report

    read_changed, read_skipped, read_failures = read_copied_template_files(work_project, args.execute)
    report.prepared_paths.extend(read_changed)
    report.skipped.extend(read_skipped)
    report.failures.extend(read_failures)
    if report.failures:
        return report

    reference = find_reference_entrypoint(work_project, selected_kind)
    report.reference_entrypoint = rel(reference, project) if reference else None
    if reference is None:
        report.failures.append("reference_entrypoint_missing:runtest.py_or_run_test.py")
        report.next_steps.append(f"모델 작업 폴더에 기존 runtest.py 또는 run_test.py를 넣어주세요: {rel(work_project, project)}")
        return report

    changed, write_skipped, write_failures = write_runtest_2(work_project, selected_model, selected_kind, reference, args.execute, args.force)
    report.prepared_paths.extend(changed)
    report.skipped.extend(write_skipped)
    report.failures.extend(write_failures)
    if report.failures:
        return report

    runtime_reference = work_project / "runtest_2.py"
    runtime_changed, runtime_skipped, runtime_failures = sync_selected_model_runtime(
        work_project,
        selected_model,
        selected_kind,
        runtime_reference,
        args.execute,
        copy_template=False,
    )
    report.prepared_paths.extend(runtime_changed)
    report.skipped.extend(runtime_skipped)
    report.failures.extend(runtime_failures)
    if report.failures:
        return report

    verify_changed, verify_skipped, verify_failures = verify_selected_model_conversion(work_project, selected_model, selected_kind, models, args.execute)
    report.prepared_paths.extend(verify_changed)
    report.skipped.extend(verify_skipped)
    report.failures.extend(verify_failures)

    if args.execute and not report.failures:
        report.next_steps.extend(
            [
                "모델 선택 완료: 모델 목록 확인 -> 모델 선택",
                f"선택 모델 유지: {rel(selected_model, project)}",
                f"작업 폴더: {rel(work_project, project)}",
                "PowerShell에서는 선택한 Windows 프로젝트 루트에서 실행하세요.",
                f"3번은 사용자가 선택해 실행합니다: python .opencode/scripts/03-environment-check/check_environment.py --project {rel(work_project, project)} --entrypoint runtest_2.py",
                "4번 템플릿 변환은 사용자가 선택했을 때만 진행합니다.",
                "5번 원격 MLflow 등록 실행은 사용자가 선택했을 때만 진행합니다.",
                "6번 추론 테스트와 7번 오류 재실행도 사용자가 선택했을 때만 진행합니다.",
            ]
        )
    elif not report.failures:
        report.next_steps.append("검토 후 --execute를 붙여 기존 runtest.py를 참조한 runtest_2.py를 변환하세요.")
    return report


def todo_statuses(report: PreparedModelReport) -> list[str]:
    model_selected = bool(report.selected_model_path)
    project_path = Path(report.project_path)
    work_path = project_path / report.work_project_path if report.work_project_path else project_path
    auto_ready = all(
        path in report.prepared_paths
        or f"{path} (refreshed)" in report.prepared_paths
        or any(item.startswith(f"{path} ") for item in report.prepared_paths)
        or (work_path / path).is_file()
        for path in [
            "runtest_2.py",
        ]
    )
    runtime_ready = all(
        (work_path / path).exists()
        for path in [
            "aiu_custom/model.py",
            "aiu_custom/predict.py",
            "inferencetest.py",
            "input_example.json",
            "config/config.json",
            "requirements.txt",
        ]
    )
    if report.model_artifact_paths:
        model_list_status = "완료"
    elif report.training_code_paths:
        model_list_status = "학습 코드 있음"
    elif report.entrypoint_paths:
        model_list_status = "실행파일 있음"
    elif report.data_file_paths:
        model_list_status = "데이터만 있음"
    else:
        model_list_status = "모델 없음"
    return [
        model_list_status,
        "완료" if model_selected else "대기",
        "사용자 선택" if model_selected else "2번 완료 후",
        "사용자 선택",
        "사용자 선택",
        "사용자 선택",
        "사용자 선택",
    ]


def print_todo_guide(report: PreparedModelReport) -> None:
    print(format_todo_guide(todo_statuses(report)))


def print_report(report: PreparedModelReport, verbose: bool = False) -> None:
    work_project = report.work_project_path or "."
    check_env_command = f"python .opencode/scripts/03-environment-check/check_environment.py --project {work_project} --entrypoint runtest_2.py"
    prepare_command = f"python .opencode/scripts/04-train-model/prepare_selected_model.py --project . --model selected --execute"
    run_training_command = f"python .opencode/scripts/04-train-model/run_training.py --project {work_project} --entrypoint runtest_2.py --execute"
    if (
        not verbose
        and report.execute
        and report.selected_model_path
        and not report.failures
        and "selected_model locked" in report.prepared_paths
    ):
        print("선택 결과:")
        print(f"- 선택 모델: {report.selected_model_path}")
        print(f"- MODEL_KIND: {report.model_kind or 'missing'}")
        print(f"- 작업 폴더: {work_project}")
        print_todo_guide(report)
        print("- 완료: 선택 모델 고정")
        print("- 다음: 3번 환경 검증")
        print("- 4번 템플릿 변환은 사용자가 선택했을 때만 실행")
        return

    if not verbose and report.execute and report.selected_model_path and not report.failures:
        print("준비 결과:")
        print(f"- 선택 모델: {report.selected_model_path}")
        print(f"- MODEL_KIND: {report.model_kind or 'missing'}")
        print(f"- 작업 폴더: {work_project}")
        print_todo_guide(report)
        print("- 완료: 템플릿 복사 후 선택 모델 형식에 맞게 변환")
        print("- 변환: runtest_2.py, aiu_custom/model.py, aiu_custom/predict.py")
        print("- 변환: inferencetest.py, config/config.json, input_example.json, requirements.txt")
        return

    print("Project: .")
    print("Data root: data")
    print("Scope: 선택한 워크스페이스 루트 기준")

    if report.model_artifact_paths or report.training_code_paths:
        data_model_count = sum(1 for path in report.model_artifact_paths if path == "data" or path.startswith("data/"))
        total_model_count = len(report.model_artifact_paths)
        selected_model_path = normalize_path_text(report.selected_model_path or "")
        print("\n모델 선택 화면")
        if report.selected_model_path:
            print(f"- 선택 모델: {report.selected_model_path}")
            print(f"- MODEL_KIND: {report.model_kind or 'missing'}")
            print(f"- 작업 폴더: {work_project}")
            print("- 이후 단계는 이 선택 모델 기준으로 계속 진행합니다.")
        else:
            print(format_model_selection_hint())
            if report.training_code_paths:
                print("- case 1: 학습 코드가 감지되었습니다. 아래 학습 코드 후보도 2번 목록에 표시합니다.")
            if total_model_count:
                if data_model_count == total_model_count:
                    print(f"- data 폴더에 {total_model_count}개 모델이 있습니다. 선택해주세요.")
                elif data_model_count:
                    print(f"- 프로젝트에 {total_model_count}개 모델이 있습니다. data 폴더 {data_model_count}개 포함, 선택해주세요.")
                else:
                    print(f"- 현재 프로젝트 루트 바로 아래에 {total_model_count}개 모델이 있습니다. 선택해주세요.")
        if report.model_artifact_paths:
            print("- 목록은 선택한 워크스페이스 기준 상대경로 알파벳 순서입니다.")
            if report.selected_model_path:
                print("- 아래 목록은 확인용입니다. 모델 변경은 2번 모델 선택 스크립트로만 진행합니다.")
            else:
                print("- 숫자키는 TODO 단계가 아니라 아래 모델 artifact 번호 선택입니다.")
            print("  모델 artifact 후보:")
            for index, path in enumerate(report.model_artifact_paths, start=1):
                marker = " <선택됨>" if normalize_path_text(path) == selected_model_path else ""
                print(f"  {index}. {path}{marker}")
        else:
            print("- 학습 코드는 아래 번호로 확인하고, 실행 시 --entrypoint 경로를 사용합니다.")
        if not report.selected_model_path:
            if report.model_artifact_paths:
                print(f"- 모델 artifact 선택 실행 예: {PS_PREPARE_MODEL_COMMAND}")
            if report.training_code_paths:
                print("  학습 코드 후보:")
                for index, path in enumerate(report.training_code_paths, start=1):
                    print(f"  {index}. {path}")
                print(f"- 학습 코드 실행 안내: {training_code_run_hint(Path(report.project_path), report.training_code_paths)}")
            print("- 선택 후 진행: 3번 환경 검증")
            print("- 4번 템플릿 변환은 사용자가 선택했을 때만 실행")

    print_todo_guide(report)

    if not verbose:
        if report.required_requirements:
            print("\nrequirements.txt 필수 항목:")
            print("- " + ", ".join(report.required_requirements))
        if report.prepared_paths:
            print("\n준비 결과:")
            if report.failures:
                print("- 실패")
            elif report.execute:
                print("- 완료: 템플릿 복사, runtest_2.py, requirements/input/config, 런타임 연결부 변환")
            else:
                print("- dry-run: --execute를 붙이면 실제 파일을 변환합니다.")
        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"- {warning}")
        if report.failures:
            print("\nFailures:")
            for failure in report.failures:
                print(f"- {failure}")
        print("\n다음 단계:")
        if report.failures:
            if report.next_steps:
                for step in report.next_steps[:3]:
                    print(f"- {step}")
            else:
                print("- 오류 항목을 수정한 뒤 같은 명령을 다시 실행하세요.")
        elif report.selected_model_path:
            print(f"- 3번 환경 검증은 사용자가 선택: {check_env_command}")
            print(f"- 4번 템플릿 변환은 사용자가 선택: {prepare_command}")
            print(f"- 5번 원격 MLflow 등록 실행은 사용자가 선택: {run_training_command}")
            print("- 6번 추론 테스트와 7번 오류 재실행도 사용자가 선택")
        elif report.next_steps:
            for step in report.next_steps[:3]:
                print(f"- {step}")
        return

    print("\nmodel_artifact_paths:")
    if report.model_artifact_paths:
        for index, path in enumerate(report.model_artifact_paths, start=1):
            print(f"{index}. {path}")
    else:
        print("- none")
    print("training_code_paths:")
    if report.training_code_paths:
        for index, path in enumerate(report.training_code_paths, start=1):
            print(f"{index}. {path}")
    else:
        print("- none")
    print("data_file_paths:")
    if report.data_file_paths:
        for index, path in enumerate(report.data_file_paths, start=1):
            print(f"{index}. {path}")
    else:
        print("- none")
    print("entrypoint_paths:")
    if report.entrypoint_paths:
        for index, path in enumerate(report.entrypoint_paths, start=1):
            print(f"{index}. {path}")
    else:
        print("- none")
    print(f"Selected model: {report.selected_model_path or 'missing'}")
    print(f"MODEL_KIND: {report.model_kind or 'missing'}")
    print(f"Work folder: {work_project}")
    print(f"Reference entrypoint: {report.reference_entrypoint or 'missing'}")
    print(f"Transformed entrypoint: {report.generated_entrypoint}")
    print(f"Execute: {report.execute}")
    if report.required_requirements or report.additional_requirements:
        print("requirements.txt transform:")
        if report.required_requirements:
            print("- required:")
            for item in report.required_requirements:
                print(f"  - {item}")
        if report.additional_requirements:
            print("- added for selected model:")
            for item in report.additional_requirements:
                print(f"  - {item}")
        else:
            print("- added for selected model: none")
    if report.prepared_paths:
        print("Prepared:")
        for item in report.prepared_paths:
            print(f"- {item}")
    if report.skipped:
        print("Skipped:")
        for item in report.skipped:
            print(f"- {item}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"- {warning}")
    if report.failures:
        print("Failures:")
        for failure in report.failures:
            print(f"- {failure}")
    if report.next_steps:
        print("Next steps:")
        for step in report.next_steps:
            print(f"- {step}")


def normalize_argv(argv: list[str]) -> list[str]:
    normalized: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--" and index + 1 < len(argv):
            next_arg = argv[index + 1]
            if next_arg in {"model", "project", "entrypoint"}:
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
            normalized.extend(["--model", match.group(1)])
        else:
            normalized.append(arg)
        index += 1
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a current project-root or data/** model artifact and generate workspace-root runtest_2.py without modifying runtest.py.")
    parser.add_argument("--project", default=".", help="model project folder")
    parser.add_argument("--model", help="model index from model_artifact_paths or a project-relative path")
    parser.add_argument("--execute", action="store_true", help="write the selected-model runtest_2.py or sync runtime files when --sync-runtime is used")
    parser.add_argument("--force", action="store_true", help="kept for compatibility; runtest_2.py is transformed for the selected model")
    parser.add_argument("--select-only", action="store_true", help="step 2 only: lock the selected model; do not copy or transform templates")
    parser.add_argument("--sync-runtime", action="store_true", help="reuse the selected model and transform runtime folders/files for that model")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    parser.add_argument("--verbose", action="store_true", help="print detailed model lists, prepared files, warnings, and next steps")
    args = parser.parse_args(normalize_argv(sys.argv[1:]))

    report = build_report(args)
    if args.json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    else:
        print_report(report, verbose=args.verbose)
    return 1 if report.failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        raise SystemExit(130)
