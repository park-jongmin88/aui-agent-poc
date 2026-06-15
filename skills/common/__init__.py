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


def ok(data: dict):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def fail(message: str):
    print(json.dumps({"status": "error", "message": message}, ensure_ascii=False),
          file=sys.stderr)
    sys.exit(1)


def get_config() -> dict:
    """config.json 로드."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_mlflow_config() -> dict:
    """config.json의 mlflow 섹션 반환."""
    cfg = get_config()
    return cfg.get("mlflow", {
        "tracking_uri": "",
        "username": "",
        "password": ""
    })


def save_mlflow_config(tracking_uri: str, username: str = "", password: str = ""):
    """MLflow 설정을 config.json에 저장."""
    cfg = get_config()
    cfg["mlflow"] = {
        "tracking_uri": tracking_uri,
        "username": username,
        "password": password
    }
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def is_mlflow_configured() -> bool:
    """MLflow 주소가 설정됐는지 확인."""
    uri = get_mlflow_config().get("tracking_uri", "")
    return bool(uri) and "your-mlflow" not in uri


def is_ml_installed() -> bool:
    """ML 패키지(mlflow 등) 설치 여부 확인."""
    try:
        import mlflow
        return True
    except ImportError:
        return False


def get_current_folder() -> Path | None:
    """현재 작업 폴더 반환."""
    if not CURRENT_FILE.exists():
        return None
    name = CURRENT_FILE.read_text(encoding="utf-8").strip()
    if not name:
        return None
    folder = MODELS_DIR / name
    return folder if folder.exists() else None


def set_current_folder(name: str):
    """현재 작업 폴더 설정."""
    CURRENT_FILE.write_text(name, encoding="utf-8")


def get_state(folder: Path) -> dict:
    """모델 폴더의 작업 상태 반환."""
    state_file = folder / ".aiu_state.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def set_state(folder: Path, **kwargs):
    """모델 폴더의 작업 상태 업데이트."""
    state = get_state(folder)
    state.update(kwargs)
    state["updated_at"] = datetime.now().isoformat()
    (folder / ".aiu_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_model_folders() -> list[dict]:
    """workspace/models/ 하위 폴더 목록 반환."""
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
                "last_action": state.get("last_action"),
                "last_run_id": state.get("last_run_id"),
                "last_run_at": state.get("last_run_at"),
                "status": state.get("status"),
                "experiment_name": state.get("experiment_name"),
                "model_name": state.get("model_name"),
            })
    return result


def get_model_folder(name_or_no) -> Path | None:
    """이름 또는 번호로 모델 폴더 반환."""
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
