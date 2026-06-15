"""
aiu-agent 스킬 스크립트 공통 유틸리티
"""
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = ROOT / "workspace"
MODELS_DIR = WORKSPACE_DIR / "models"
TEMPLATES_DIR = WORKSPACE_DIR / "templates"
CURRENT_FILE = WORKSPACE_DIR / ".current"
CONFIG_PATH = ROOT / "config.json"

# 단계 순서 정의 (optional 단계는 별도 표시)
STAGE_ORDER = ["initialized", "validated", "trained", "predicted"]
STAGE_OPTIONAL = ["local_tested"]  # local_run은 선택 단계

STAGE_NEXT = {
    "initialized":  "validate 실행 필요",
    "validated":    "local_run(선택) 또는 train 실행 가능",
    "local_tested": "train 실행 가능",
    "trained":      "predict 실행 가능",
    "predicted":    "deploy 가능",
}

STAGE_REQUIRED = {
    "validate":   "initialized",
    "local_run":  "validated",
    "train":      "validated",   # local_tested도 허용 (둘 다 통과로 간주)
    "predict":    "trained",
    "deploy":     "predicted",
}


def ok(data: dict):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def fail(message: str):
    print(json.dumps({"status": "error", "message": message}, ensure_ascii=False),
          file=sys.stderr)
    sys.exit(1)


def check_gate(folder: Path, skill: str) -> tuple[bool, str]:
    """단계 게이트 확인. (통과여부, 안내메시지) 반환."""
    required = STAGE_REQUIRED.get(skill)
    if not required:
        return True, ""

    state = get_state(folder)
    current_status = state.get("status", "")

    # train은 validated 또는 local_tested 둘 다 허용
    if skill == "train":
        if current_status in ("validated", "local_tested"):
            return True, ""
        return False, (
            f"train 실행 전에 validate가 필요합니다.\n"
            f"현재 상태: {current_status or '없음'}\n"
            f"'검증해줘' 를 먼저 실행하세요."
        )

    if current_status == required or _status_after(current_status, required):
        return True, ""

    skill_name_map = {
        "validate": "검증(validate)",
        "local_run": "로컬 테스트(local_run)",
        "train": "학습(train)",
        "predict": "추론(predict)",
        "deploy": "배포(deploy)",
    }
    required_name_map = {
        "initialized": "init(준비)",
        "validated": "validate(검증)",
        "local_tested": "local_run(로컬 테스트)",
        "trained": "train(학습)",
        "predicted": "predict(추론)",
    }
    return False, (
        f"{skill_name_map.get(skill, skill)} 실행 전에 "
        f"{required_name_map.get(required, required)}가 필요합니다.\n"
        f"현재 상태: {current_status or '없음'}"
    )


def _status_after(current: str, required: str) -> bool:
    """현재 상태가 required 이후 단계인지 확인."""
    try:
        return STAGE_ORDER.index(current) > STAGE_ORDER.index(required)
    except ValueError:
        return False


def get_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_mlflow_config() -> dict:
    cfg = get_config()
    return cfg.get("mlflow", {"tracking_uri": "", "username": "", "password": ""})


def save_mlflow_config(tracking_uri: str, username: str = "", password: str = ""):
    cfg = get_config()
    cfg["mlflow"] = {"tracking_uri": tracking_uri, "username": username, "password": password}
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def is_mlflow_configured() -> bool:
    uri = get_mlflow_config().get("tracking_uri", "")
    return bool(uri) and "your-mlflow" not in uri


def is_ml_installed() -> bool:
    try:
        import mlflow
        return True
    except ImportError:
        return False


def get_current_folder() -> Path | None:
    if not CURRENT_FILE.exists():
        return None
    name = CURRENT_FILE.read_text(encoding="utf-8").strip()
    if not name:
        return None
    folder = MODELS_DIR / name
    return folder if folder.exists() else None


def set_current_folder(name: str):
    CURRENT_FILE.write_text(name, encoding="utf-8")


def get_state(folder: Path) -> dict:
    state_file = folder / ".aiu_state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_state(folder: Path, **kwargs):
    state = get_state(folder)
    state.update(kwargs)
    state["updated_at"] = datetime.now().isoformat()
    (folder / ".aiu_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_model_folders() -> list[dict]:
    if not MODELS_DIR.exists():
        return []
    result = []
    for i, d in enumerate(sorted(MODELS_DIR.iterdir()), 1):
        if d.is_dir() and not d.name.startswith('.'):
            state = get_state(d)
            source_files = list((d / "source").iterdir()) if (d / "source").exists() else []
            result.append({
                "no": i,
                "name": d.name,
                "path": str(d),
                "has_run_py": (d / "run.py").exists(),
                "source_files": [f.name for f in source_files if f.is_file()],
                "status": state.get("status"),
                "last_action": state.get("last_action"),
                "last_run_id": state.get("last_run_id"),
                "last_run_at": state.get("last_run_at"),
                "experiment_name": state.get("experiment_name"),
                "model_name": state.get("model_name"),
                "ml_installed": state.get("ml_installed", False),
            })
    return result


def get_model_folder(name_or_no) -> Path | None:
    folders = list_model_folders()
    if not folders:
        return None
    if str(name_or_no).isdigit():
        no = int(name_or_no)
        for f in folders:
            if f["no"] == no:
                return Path(f["path"])
    for f in folders:
        if f["name"] == str(name_or_no):
            return Path(f["path"])
    return None
