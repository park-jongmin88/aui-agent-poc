"""
aiu-agent 스킬 스크립트 공통 유틸리티
모든 스크립트는 이 모듈을 사용한다.

출력 규약:
  - 성공: sys.stdout에 JSON {"status": "ok", "data": {...}}
  - 실패: sys.exit(1) + sys.stderr에 에러 메시지
"""
import json
import sys
from pathlib import Path

# 프로젝트 루트 (skills/common/ 기준 상위 2단계)
ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = ROOT / "workspace"
RUN_PY = WORKSPACE_DIR / "run.py"
MODELS_DIR = WORKSPACE_DIR / "models"
TEMPLATES_DIR = WORKSPACE_DIR / "templates"
RESULTS_DIR = WORKSPACE_DIR / "results"


def ok(data: dict):
    """성공 결과 출력 후 종료."""
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def fail(message: str):
    """실패 메시지 출력 후 종료."""
    print(json.dumps({"status": "error", "message": message}, ensure_ascii=False),
          file=sys.stderr)
    sys.exit(1)


def list_model_folders() -> list[dict]:
    """workspace/models/ 하위 폴더 목록 반환."""
    if not MODELS_DIR.exists():
        return []
    result = []
    for i, d in enumerate(sorted(MODELS_DIR.iterdir()), 1):
        if d.is_dir():
            result.append({
                "no": i,
                "name": d.name,
                "path": str(d),
                "has_run_py": (d / "run.py").exists(),
                "files": [f.name for f in d.iterdir() if f.is_file()]
            })
    return result


def get_model_folder(name_or_no) -> Path | None:
    """이름 또는 번호로 모델 폴더 반환."""
    folders = list_model_folders()
    if not folders:
        return None
    # 번호로 찾기
    if str(name_or_no).isdigit():
        no = int(name_or_no)
        for f in folders:
            if f["no"] == no:
                return Path(f["path"])
    # 이름으로 찾기
    for f in folders:
        if f["name"] == str(name_or_no):
            return Path(f["path"])
    return None
