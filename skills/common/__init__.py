"""
aiu-agent 스킬 스크립트 공통 유틸리티
Windows / Linux / macOS 공통 동작 보장
"""
import json
import sys
import os
import platform
from pathlib import Path
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = ROOT / "workspace"
MODELS_DIR    = WORKSPACE_DIR / "models"
TEMPLATES_DIR = WORKSPACE_DIR / "templates"
RESULTS_DIR   = WORKSPACE_DIR / "results"
CURRENT_FILE  = WORKSPACE_DIR / ".current"
CONFIG_PATH   = ROOT / "config.json"

STAGE_ORDER    = ["initialized", "validated", "trained", "predicted"]
STAGE_OPTIONAL = ["local_tested"]

STAGE_REQUIRED = {
    "validate":    "initialized",
    "localrun":    "validated",
    "train":       "validated",
    "predict":     "trained",
    "deploy":      "predicted",
    "localserve":  None,  # local_tested 또는 trained — check_gate에서 별도 처리
}


# ── 출력 유틸 ────────────────────────────────────────────────

def ok(data: dict):
    """성공 응답 출력 후 종료."""
    try:
        print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    except Exception:
        print(json.dumps({"status": "ok", "data": {"message": str(data)}}, ensure_ascii=False))
    sys.exit(0)


def fail(message: str):
    """실패 응답 출력 후 종료. 절대 예외 발생시키지 않는다."""
    try:
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False),
              file=sys.stderr)
    except Exception:
        print(json.dumps({"status": "error", "message": "알 수 없는 오류"}, ensure_ascii=False),
              file=sys.stderr)
    sys.exit(1)


def progress(message: str):
    """진행 상태 출력. 종료하지 않는다."""
    try:
        print(json.dumps({"status": "progress", "line": message}, ensure_ascii=False), flush=True)
    except Exception:
        pass


# ── 게이트 ──────────────────────────────────────────────────

def check_gate(folder: Path, skill: str) -> tuple:
    """단계 게이트 확인. (통과여부, 안내메시지) 반환."""
    try:
        # localserve: local_tested 만 허용 (results/ 에 로컬 모델이 있어야 함)
        if skill == "localserve":
            status = get_state(folder).get("status", "")
            if status == "local_tested":
                return True, ""
            # trained/predicted 상태지만 local_run을 안 한 경우 명확히 안내
            if status in ("trained", "predicted", "deployed"):
                return False, (
                    "로컬 서빙은 로컬 테스트(local_run) 결과물이 필요합니다.\n"
                    "학습(train)은 MLflow에만 등록하므로 로컬 모델 파일이 없습니다.\n"
                    "'로컬 실행해줘'로 local_run을 먼저 실행하세요."
                )
            return False, (
                "로컬 서빙 전에 로컬 테스트(local_run)가 필요합니다.\n"
                f"현재 상태: {status or '없음'}\n'로컬 실행해줘'를 먼저 실행하세요."
            )

        required = STAGE_REQUIRED.get(skill)
        if not required:
            return True, ""

        state = get_state(folder)
        current = state.get("status", "")

        # train: validated 또는 local_tested 둘 다 허용
        if skill == "train":
            if current in ("validated", "local_tested", "trained", "predicted"):
                return True, ""
            return False, (
                "학습(train) 전에 검증(validate)이 필요합니다.\n"
                f"현재 상태: {current or '없음'}\n'검증해줘'를 먼저 실행하세요."
            )

        if _is_status_reached(current, required):
            return True, ""

        label_map = {
            "initialized":  "init(준비)",
            "validated":    "validate(검증)",
            "local_tested": "local_run(로컬 테스트)",
            "trained":      "train(학습)",
            "predicted":    "predict(추론)",
        }
        skill_map = {
            "validate":   "검증(validate)",
            "localrun":   "로컬 테스트(local_run)",
            "train":      "학습(train)",
            "predict":    "추론(predict)",
            "deploy":     "배포(deploy)",
        }
        return False, (
            f"{skill_map.get(skill, skill)} 전에 "
            f"{label_map.get(required, required)}가 필요합니다.\n"
            f"현재 상태: {current or '없음'}"
        )
    except Exception as e:
        return False, f"게이트 확인 중 오류: {e}"


def _is_status_reached(current: str, required: str) -> bool:
    """현재 상태가 required 이상인지 확인.
    local_tested(선택 단계)는 validated와 trained 사이로 취급한다."""
    try:
        # 순서 점수: local_tested는 validated(1)와 trained(2) 사이 = 1.5
        rank = {
            "initialized":  0,
            "validated":    1,
            "local_tested": 1.5,
            "trained":      2,
            "predicted":    3,
            "deployed":     4,
        }
        cur = rank.get(current, -1)
        req = rank.get(required, 999)
        return cur >= req
    except Exception:
        return False


# ── 파일 점검 / 단계 되돌리기 ────────────────────────────────

# 상태 → 그 상태가 되려면 있어야 하는 파일
STATE_RANK = {
    "initialized": 0, "validated": 1, "local_tested": 1.5,
    "trained": 2, "predicted": 3, "deployed": 4,
}


def _file_hash(path: Path) -> str:
    """파일 내용 해시 (수정 감지용)."""
    import hashlib
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def check_files_consistency(folder: Path) -> dict:
    """상태와 실제 파일이 일치하는지 점검.
    반환: {
        "ok": bool,
        "forced_status": 되돌려야 할 상태 또는 None,
        "warnings": [안내 메시지...],
        "message": 종합 안내
    }
    """
    try:
        state   = get_state(folder)
        status  = state.get("status", "")
        rank    = STATE_RANK.get(status, 0)

        run_py      = folder / "run.py"
        results_dir = RESULTS_DIR / folder.name
        warnings    = []
        forced      = None  # 강제로 되돌릴 상태

        # ── 1. 삭제 감지 (강제 되돌림) ──
        # run.py 없음 → initialized 이전으로 (init 필요)
        if rank >= 1 and not run_py.exists():
            return {
                "ok": False,
                "forced_status": None,  # init부터 다시
                "warnings": ["run.py가 없습니다. 준비(init)부터 다시 해야 합니다."],
                "message": "run.py가 삭제되었습니다.\n'준비해줘'로 init부터 다시 시작하세요.",
                "need_init": True,
            }

        # local_tested 인데 results/ 모델 파일 없음 → validated로 되돌림
        if status == "local_tested":
            has_model = results_dir.exists() and any(
                f.suffix in (".pkl", ".joblib", ".pt", ".h5") for f in results_dir.iterdir()
            ) if results_dir.exists() else False
            if not has_model:
                forced = "validated"
                warnings.append("로컬 테스트 결과물(results/)이 없습니다. 로컬 테스트를 다시 해야 합니다.")

        # ── 2. run.py 수정 감지 (안내만) ──
        if rank >= 1 and run_py.exists():
            saved_hash = state.get("run_py_hash", "")
            cur_hash   = _file_hash(run_py)
            if saved_hash and cur_hash and saved_hash != cur_hash:
                warnings.append(
                    "run.py가 검증 이후 수정되었습니다. 다시 검증(validate)을 권장합니다."
                )

        if forced:
            set_state(folder, status=forced)
            return {
                "ok": False,
                "forced_status": forced,
                "warnings": warnings,
                "message": "\n".join(warnings) + f"\n→ 상태를 '{forced}'로 되돌렸습니다.",
            }

        if warnings:
            return {"ok": True, "forced_status": None, "warnings": warnings,
                    "message": "\n".join(warnings)}

        return {"ok": True, "forced_status": None, "warnings": [], "message": ""}
    except Exception as e:
        return {"ok": True, "forced_status": None, "warnings": [],
                "message": f"(파일 점검 생략: {e})"}


def rewind_to(folder: Path, target_status: str):
    """명시적 재작업: 상태를 target_status로 되돌린다 (A 방식).
    이후 단계 기록(run_id 등)은 정리한다."""
    try:
        target_rank = STATE_RANK.get(target_status, 0)
        clear_keys = []
        # trained 미만으로 되돌리면 학습 기록 삭제
        if target_rank < 2:
            clear_keys += ["last_run_id", "last_run_at"]
        # local_tested 미만이면 로컬 결과 기록 삭제
        if target_rank < 1.5:
            clear_keys += ["local_results_dir"]

        kwargs = {"status": target_status}
        for k in clear_keys:
            kwargs[k] = None  # None = 삭제
        set_state(folder, **kwargs)
        return True
    except Exception:
        return False


# ── 설정 ────────────────────────────────────────────────────

def get_config() -> dict:
    """config.json 로드. 실패 시 빈 dict 반환."""
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def get_mlflow_config() -> dict:
    """config.json의 mlflow 섹션 반환."""
    try:
        return get_config().get("mlflow", {
            "tracking_uri": "", "username": "", "password": ""
        })
    except Exception:
        return {"tracking_uri": "", "username": "", "password": ""}


def save_mlflow_config(tracking_uri: str, username: str = "", password: str = ""):
    """MLflow 설정을 config.json에 저장."""
    try:
        cfg = get_config()
        cfg["mlflow"] = {
            "tracking_uri": tracking_uri,
            "username": username,
            "password": password,
        }
        CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        fail(f"config.json 저장 실패: {e}")


def is_mlflow_configured() -> bool:
    """MLflow 주소 설정 여부 확인."""
    try:
        uri = get_mlflow_config().get("tracking_uri", "")
        return bool(uri) and "your-mlflow" not in uri
    except Exception:
        return False


def is_ml_installed() -> bool:
    """mlflow 패키지 설치 여부 확인."""
    try:
        import mlflow
        return True
    except ImportError:
        return False


# ── 폴더/상태 관리 ─────────────────────────────────────────

def get_current_folder() -> Path | None:
    """현재 작업 폴더 반환. 없거나 유효하지 않으면 None."""
    try:
        if not CURRENT_FILE.exists():
            return None
        name = CURRENT_FILE.read_text(encoding="utf-8").strip()
        if not name:
            return None
        folder = MODELS_DIR / name
        return folder if folder.exists() else None
    except Exception:
        return None


def set_current_folder(name: str):
    """현재 작업 폴더 설정."""
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        CURRENT_FILE.write_text(name, encoding="utf-8")
    except Exception as e:
        fail(f".current 파일 저장 실패: {e}")


def get_state(folder: Path) -> dict:
    """모델 폴더의 작업 상태 반환. 읽기 실패 시 빈 dict."""
    try:
        state_file = folder / ".aiu_state.json"
        if not state_file.exists():
            return {}
        text = state_file.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else {}
    except Exception:
        return {}


def set_state(folder: Path, **kwargs):
    """모델 폴더의 작업 상태 업데이트. 기존 상태에 병합."""
    try:
        state = get_state(folder)
        # None 값은 해당 키 삭제
        for k, v in kwargs.items():
            if v is None and k in state:
                del state[k]
            elif v is not None:
                state[k] = v
        state["updated_at"] = datetime.now().isoformat()
        state_file = folder / ".aiu_state.json"
        # 원자적 쓰기: 임시 파일에 먼저 쓰고 rename
        tmp = state_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(state_file)
    except Exception as e:
        # 상태 저장 실패는 치명적이지 않으므로 경고만
        progress(f"[경고] 상태 저장 실패: {e}")


def list_model_folders() -> list:
    """workspace/models/ 하위 폴더 목록 반환."""
    try:
        if not MODELS_DIR.exists():
            return []
        result = []
        for i, d in enumerate(sorted(MODELS_DIR.iterdir()), 1):
            if not d.is_dir() or d.name.startswith("."):
                continue
            try:
                state = get_state(d)
                source_dir = d / "source"
                source_files = []
                if source_dir.exists():
                    source_files = [f.name for f in source_dir.iterdir() if f.is_file()]
                result.append({
                    "no": i,
                    "name": d.name,
                    "path": str(d),
                    "has_run_py": (d / "run.py").exists(),
                    "source_files": source_files,
                    "status": state.get("status"),
                    "last_action": state.get("last_action"),
                    "last_run_id": state.get("last_run_id"),
                    "last_run_at": state.get("last_run_at"),
                    "experiment_name": state.get("experiment_name"),
                    "model_name": state.get("model_name"),
                    "ml_installed": state.get("ml_installed", False),
                })
            except Exception:
                continue
        return result
    except Exception:
        return []


def get_model_folder(name_or_no) -> Path | None:
    """이름 또는 번호로 모델 폴더 반환."""
    try:
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
    except Exception:
        return None


# ── 프로세스 관리 (Windows/Linux 공통) ─────────────────────

def kill_process(pid: int) -> bool:
    """프로세스 종료. Windows/Linux 공통."""
    try:
        if IS_WINDOWS:
            import subprocess
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        else:
            import signal
            try:
                os.kill(pid, signal.SIGTERM)
                import time; time.sleep(0.5)
                try:
                    os.kill(pid, 0)  # 아직 살아있으면
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # 이미 종료됨
            except ProcessLookupError:
                pass
            return True
    except Exception:
        return False


def is_process_alive(pid: int) -> bool:
    """프로세스 생존 여부 확인. Windows/Linux 공통."""
    try:
        if IS_WINDOWS:
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=3
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, PermissionError, OSError):
        return False
    except Exception:
        return False


# ── 경로 유틸 ───────────────────────────────────────────────

def safe_path_str(p: Path) -> str:
    """경로를 문자열로 변환. Windows 역슬래시를 슬래시로 통일."""
    try:
        return str(p).replace("\\", "/")
    except Exception:
        return str(p)


def safe_unlink(p: Path):
    """파일 삭제. 없거나 실패해도 무시."""
    try:
        if p and p.exists():
            p.unlink()
    except Exception:
        pass
