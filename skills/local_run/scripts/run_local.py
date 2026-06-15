"""
skills/local_run/scripts/run_local.py

workspace/models/<folder>/run.py 를 MLflow 등록 없이 로컬에서 실행한다.
- MLflow start_run / log_model 을 mock으로 대체
- 결과 모델을 workspace/results/<folder>/ 에 저장
- 학습 완료 후 status=local_tested 저장

사용:
    python skills/local_run/scripts/run_local.py [폴더명]
"""
import sys
import os
import re
import subprocess
import time
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, get_current_folder, get_state, set_state,
    check_gate, MODELS_DIR, WORKSPACE_DIR, ROOT
)


def get_folder(folder_name=None) -> Path:
    if folder_name:
        folder = MODELS_DIR / folder_name
        if not folder.exists():
            fail(f"폴더를 찾을 수 없습니다: workspace/models/{folder_name}")
        return folder
    folder = get_current_folder()
    if not folder:
        fail("현재 작업 폴더가 없습니다. 폴더를 선택해주세요.")
    return folder


def make_local_run_py(folder: Path) -> Path:
    """run.py의 MLflow 등록 부분을 mock으로 대체한 임시 파일 생성."""
    run_py = folder / "run.py"
    if not run_py.exists():
        fail(f"workspace/models/{folder.name}/run.py 가 없습니다. 먼저 init을 실행해주세요.")

    text = run_py.read_text(encoding="utf-8")
    results_dir = WORKSPACE_DIR / "results" / folder.name
    results_dir.mkdir(parents=True, exist_ok=True)

    # MLflow 연결/등록 mock 처리
    mock_header = f'''# ── LOCAL RUN MODE (MLflow 등록 없음) ──────────────────────
import unittest.mock as _mock
_mlflow_mock = _mock.MagicMock()
_mlflow_mock.start_run.return_value.__enter__ = lambda s, *a: _mlflow_mock.start_run.return_value
_mlflow_mock.start_run.return_value.__exit__ = lambda s, *a: False
_mlflow_mock.start_run.return_value.info.run_id = "local-run"
import sys as _sys
_sys.modules["mlflow"] = _mlflow_mock
_sys.modules["mlflow.sklearn"] = _mlflow_mock
_sys.modules["mlflow.pytorch"] = _mlflow_mock
_sys.modules["mlflow.tensorflow"] = _mlflow_mock
_sys.modules["mlflow.pyfunc"] = _mlflow_mock
_sys.modules["mlflow.models"] = _mlflow_mock
LOCAL_RESULTS_DIR = "{str(results_dir)}"
# ────────────────────────────────────────────────────────────

'''

    # ROOT/SAVE_DIR/data_path를 절대경로로 교체 (임시 파일은 경로 레벨이 다름)
    text = re.sub(r'ROOT\s*=.*', f'ROOT = Path("{str(ROOT)}")', text)
    text = re.sub(r'SAVE_DIR\s*=.*', f'SAVE_DIR = Path("{str(results_dir)}")', text)
    # data_path: Path(__file__).parent → 실제 모델 폴더로 고정
    text = text.replace(
        'Path(__file__).parent',
        f'Path("{str(folder)}")'
    )

    # 모델 저장 코드 삽입 (섹션 9 if __name__ 직전)
    save_code = f'''
# ── 로컬 결과 저장 (joblib/torch/tf 자동 감지) ─────────────
def _save_local_model(model, save_dir):
    import importlib
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    if importlib.util.find_spec("joblib"):
        import joblib
        joblib.dump(model, save_dir / "model.pkl")
        print(f"[AIU] 로컬 저장 완료: {{save_dir}}/model.pkl")
    elif hasattr(model, "state_dict"):
        import torch
        torch.save(model.state_dict(), save_dir / "model.pt")
        print(f"[AIU] 로컬 저장 완료: {{save_dir}}/model.pt")
    elif hasattr(model, "save"):
        model.save(str(save_dir / "model.h5"))
        print(f"[AIU] 로컬 저장 완료: {{save_dir}}/model.h5")
    else:
        print(f"[AIU] 모델 저장 방법을 찾지 못했습니다. 수동으로 저장해주세요.")

'''

    # log_model(...) 블록 끝(닫는 괄호) 다음 줄에 _save_local_model 삽입
    new_lines = []
    inserted = False
    in_log_model = False
    paren_depth = 0
    base_indent = 0
    for line in text.splitlines():
        new_lines.append(line)
        stripped = line.strip()
        if not inserted and not in_log_model:
            if "log_model(" in line and "def log_model" not in line:
                in_log_model = True
                base_indent = len(line) - len(line.lstrip())
                paren_depth = line.count("(") - line.count(")")
                if paren_depth <= 0:
                    in_log_model = False
                    new_lines.append(" " * base_indent + "_save_local_model(model, SAVE_DIR)")
                    inserted = True
        elif in_log_model:
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0:
                in_log_model = False
                new_lines.append(" " * base_indent + "_save_local_model(model, SAVE_DIR)")
                inserted = True
    text = "\n".join(new_lines)

    tmp = Path(tempfile.mktemp(suffix="_local_run.py"))
    tmp.write_text(mock_header + save_code + text, encoding="utf-8")
    return tmp, results_dir


def run_local(folder: Path):
    """로컬 실행."""
    # 게이트 확인
    passed, msg = check_gate(folder, "local_run")
    if not passed:
        fail(msg)

    print(json.dumps({
        "status": "running",
        "message": f"로컬 학습 시작 → workspace/models/{folder.name}/run.py (MLflow 등록 없음)"
    }, ensure_ascii=False), flush=True)

    tmp_py, results_dir = make_local_run_py(folder)
    start = time.time()

    try:
        proc = subprocess.Popen(
            [sys.executable, str(tmp_py)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1
        )

        output_lines = []
        accuracy = None

        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            output_lines.append(line)
            print(json.dumps({"status": "progress", "line": line}, ensure_ascii=False), flush=True)

            # 메트릭 파싱
            m = re.search(r'acc(?:uracy)?\s*[=:]\s*([\d.]+)', line, re.IGNORECASE)
            if m:
                accuracy = float(m.group(1))

        proc.wait()
        elapsed = round(time.time() - start, 1)

        if proc.returncode != 0:
            fail(
                f"로컬 학습 실행 중 오류:\n" + "\n".join(output_lines[-5:])
            )

        # 결과 모델 파일 확인
        model_files = list(results_dir.glob("model.*")) if results_dir.exists() else []

        set_state(folder,
            status="local_tested",
            last_action="local_run",
            local_results_dir=str(results_dir),
        )

        ok({
            "folder": folder.name,
            "elapsed": elapsed,
            "accuracy": accuracy,
            "results_dir": str(results_dir),
            "model_files": [f.name for f in model_files],
            "message": (
                f"✓ 로컬 테스트 완료 ({elapsed}s)\n"
                f"  저장 위치: {results_dir}\n"
                + (f"  모델 파일: {', '.join(f.name for f in model_files)}\n" if model_files else "")
                + (f"  accuracy: {accuracy:.4f}\n" if accuracy else "")
                + "\n→ 이상 없으면 'MLflow에 등록해줘'로 train을 진행하세요.\n"
                + "→ 로컬 서빙 테스트: '로컬 서버 띄워줘'"
            )
        })
    finally:
        if tmp_py.exists():
            tmp_py.unlink()


if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    folder = get_folder(folder_name)
    run_local(folder)
