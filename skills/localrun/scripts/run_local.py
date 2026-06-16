"""
skills/localrun/scripts/run_local.py
Windows/Linux/macOS 공통, 예외처리 완비
"""
import sys, os, re, subprocess, time, json, tempfile, platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, progress, get_current_folder, set_state,
    check_gate, safe_path_str, safe_unlink,
    MODELS_DIR, WORKSPACE_DIR, ROOT
)

RESULTS_DIR = WORKSPACE_DIR / "results"


def get_folder(name=None):
    try:
        if name:
            f = MODELS_DIR / name
            if not f.exists(): fail(f"폴더 없음: workspace/models/{name}")
            return f
        f = get_current_folder()
        if not f: fail("현재 작업 폴더가 없습니다. 폴더를 선택해주세요.")
        return f
    except SystemExit: raise
    except Exception as e: fail(f"폴더 확인 오류: {e}")


def make_local_run_py(folder, results_dir):
    run_py = folder / "run.py"
    if not run_py.exists():
        fail(f"workspace/models/{folder.name}/run.py 없음. 먼저 init을 실행해주세요.")
    try:
        text = run_py.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = run_py.read_text(encoding="utf-8", errors="replace")

    root_s    = safe_path_str(ROOT)
    results_s = safe_path_str(results_dir)
    folder_s  = safe_path_str(folder)

    mock_header = '''\
import sys as _sys, unittest.mock as _mock
_m = _mock.MagicMock()
class _R:
    class info:
        run_id = "local-run"
_m.start_run.return_value.__enter__ = lambda *a: _R()
_m.start_run.return_value.__exit__  = lambda *a: False
_mm = _mock.MagicMock()
_mm.infer_signature = _mock.MagicMock(return_value=None)
for _mod in ["mlflow","mlflow.sklearn","mlflow.pytorch",
             "mlflow.tensorflow","mlflow.pyfunc",
             "mlflow.tracking","mlflow.models"]:
    _sys.modules[_mod] = _m
_sys.modules["mlflow.models"] = _mm
'''

    save_func = f'''\
def _save_local_model(model, _ignored=None):
    import importlib
    from pathlib import Path
    d = Path("{results_s}")
    try: d.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[AIU][경고] 결과 폴더 생성 실패: {{e}}"); return
    saved = False
    if not saved and importlib.util.find_spec("joblib"):
        try:
            import joblib
            joblib.dump(model, d / "model.pkl")
            print(f"[AIU] 저장 완료: {{d}}/model.pkl"); saved = True
        except Exception as e:
            print(f"[AIU][경고] joblib 저장 실패: {{e}}")
    if not saved and hasattr(model, "state_dict"):
        try:
            import torch
            torch.save(model.state_dict(), d / "model.pt")
            print(f"[AIU] 저장 완료: {{d}}/model.pt"); saved = True
        except Exception as e:
            print(f"[AIU][경고] torch 저장 실패: {{e}}")
    if not saved and hasattr(model, "save"):
        try:
            model.save(str(d / "model.h5"))
            print(f"[AIU] 저장 완료: {{d}}/model.h5"); saved = True
        except Exception as e:
            print(f"[AIU][경고] keras 저장 실패: {{e}}")
    if not saved:
        print("[AIU][경고] 모델 저장 방법을 찾지 못했습니다.")

'''

    # 경로 고정
    text = re.sub(r'ROOT\s*=.*', f'ROOT = Path("{root_s}")', text)
    text = re.sub(r'SAVE_DIR\s*=.*', f'SAVE_DIR = Path("{results_s}")', text)
    text = text.replace('Path(__file__).parent', f'Path("{folder_s}")')
    text = text.replace('Path(__file__).resolve().parent', f'Path("{folder_s}")')

    # log_model 블록 뒤에 _save_local_model 삽입
    new_lines, inserted, in_log, depth, base_indent = [], False, False, 0, 0
    for line in text.splitlines():
        new_lines.append(line)
        if inserted: continue
        if not in_log:
            if "log_model(" in line and "def log_model" not in line:
                in_log = True
                base_indent = len(line) - len(line.lstrip())
                depth = line.count("(") - line.count(")")
                if depth <= 0:
                    in_log = False
                    new_lines.append(" " * base_indent + "_save_local_model(model)")
                    inserted = True
        else:
            depth += line.count("(") - line.count(")")
            if depth <= 0:
                in_log = False
                new_lines.append(" " * base_indent + "_save_local_model(model)")
                inserted = True
    text = "\n".join(new_lines)

    try:
        fd, tmp_path = tempfile.mkstemp(suffix="_local_run.py", prefix="aiu_")
        os.close(fd)
        tmp = Path(tmp_path)
        tmp.write_text(mock_header + save_func + text, encoding="utf-8")
        return tmp
    except Exception as e:
        fail(f"임시 파일 생성 실패: {e}")


def run_local(folder):
    passed, msg = check_gate(folder, "localrun")
    if not passed: fail(msg)

    results_dir = RESULTS_DIR / folder.name
    tmp_py = None
    try:
        results_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        fail(f"결과 폴더 생성 실패: {e}")

    progress(f"로컬 학습 시작 → workspace/models/{folder.name}/run.py (MLflow 등록 없음)")

    try:
        tmp_py = make_local_run_py(folder, results_dir)
    except SystemExit: raise
    except Exception as e: fail(f"실행 파일 준비 실패: {e}")

    start = time.time()
    proc = None
    try:
        proc = subprocess.Popen(
            [sys.executable, str(tmp_py)],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        output_lines, accuracy = [], None
        try:
            for raw in proc.stdout:
                line = raw.rstrip()
                if not line: continue
                output_lines.append(line)
                progress(line)
                m = re.search(r'acc(?:uracy)?\s*[=:]\s*([\d.]+)', line, re.IGNORECASE)
                if m:
                    try: accuracy = float(m.group(1))
                    except ValueError: pass
        except Exception: pass

        try:
            proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            proc.kill()
            fail("학습이 5분을 초과했습니다. run.py를 확인하세요.")

        elapsed = round(time.time() - start, 1)
        if proc.returncode != 0:
            tail = "\n".join(output_lines[-8:]) if output_lines else "(출력 없음)"
            fail(f"로컬 학습 중 오류 (종료코드: {proc.returncode}):\n{tail}")

        model_files = []
        try:
            model_files = [
                f for f in results_dir.iterdir()
                if f.is_file() and f.suffix in (".pkl",".joblib",".pt",".pth",".h5",".keras")
            ]
        except Exception: pass

        set_state(folder,
            status="local_tested",
            last_action="localrun",
            local_results_dir=safe_path_str(results_dir),
        )

        ok({
            "folder": folder.name,
            "elapsed": elapsed,
            "accuracy": accuracy,
            "results_dir": safe_path_str(results_dir),
            "model_files": [f.name for f in model_files],
            "message": (
                f"✓ 로컬 테스트 완료 ({elapsed}s)\n"
                f"  저장 위치: {safe_path_str(results_dir)}\n"
                + (f"  모델 파일: {', '.join(f.name for f in model_files)}\n" if model_files else "")
                + (f"  accuracy : {accuracy:.4f}\n" if accuracy else "")
                + "\n→ 이상 없으면 'MLflow에 등록해줘'로 train을 진행하세요.\n"
                + "→ 로컬 서빙 테스트: '로컬 서버 띄워줘'"
            )
        })
    except SystemExit: raise
    except Exception as e: fail(f"로컬 실행 중 예상치 못한 오류: {e}")
    finally:
        safe_unlink(tmp_py)
        if proc and proc.poll() is None:
            try: proc.kill()
            except Exception: pass


if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    run_local(get_folder(folder_name))
