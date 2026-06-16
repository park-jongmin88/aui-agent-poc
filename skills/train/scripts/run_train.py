"""
skills/train/scripts/run_train.py

현재 작업 폴더의 run.py 를 실행해 학습하고 MLflow에 등록한다.
Windows/Linux/macOS 공통, 예외처리 완비.

사용:
    python skills/train/scripts/run_train.py [폴더명] [--check-only]
    --check-only : run.py 존재/MLflow 설정 여부만 확인
"""
import sys, subprocess, time, re, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, progress, get_current_folder, set_state,
    check_gate, check_files_consistency, safe_path_str, MODELS_DIR, ROOT
)


def get_folder(name=None):
    try:
        if name and not name.startswith("--"):
            f = MODELS_DIR / name
            if not f.exists(): fail(f"폴더 없음: workspace/models/{name}")
            return f
        f = get_current_folder()
        if not f: fail("현재 작업 폴더가 없습니다. 폴더를 선택해주세요.")
        return f
    except SystemExit: raise
    except Exception as e: fail(f"폴더 확인 오류: {e}")


def check_run_py(folder: Path) -> dict:
    """run.py 존재 및 MLflow 설정 확인."""
    run_py = folder / "run.py"
    if not run_py.exists():
        fail(
            f"workspace/models/{folder.name}/run.py 가 없습니다.\n"
            "먼저 준비(init)를 실행해주세요."
        )
    try:
        text = run_py.read_text(encoding="utf-8")
    except Exception:
        text = run_py.read_text(encoding="utf-8", errors="replace")

    uri_m = re.search(r'MLFLOW_TRACKING_URI\s*=\s*["\'](.*?)["\']', text)
    uri = uri_m.group(1) if uri_m else ""
    if not uri or "your-mlflow" in uri:
        fail(
            f"run.py의 MLflow 주소가 설정되지 않았습니다.\n"
            "섹션 2의 MLFLOW_TRACKING_URI를 확인해주세요."
        )

    exp_m   = re.search(r'EXPERIMENT_NAME\s*=\s*["\'](.*?)["\']', text)
    model_m = re.search(r'MODEL_NAME\s*=\s*["\'](.*?)["\']', text)
    return {
        "uri": uri,
        "experiment": exp_m.group(1) if exp_m else "",
        "model": model_m.group(1) if model_m else "",
        "run_py": run_py,
    }


def run_training(folder: Path, info: dict):
    progress(f"학습 시작 → MLflow: {info['uri']} / 실험: {info['experiment']}")

    start = time.time()
    proc = None
    try:
        proc = subprocess.Popen(
            [sys.executable, str(info["run_py"])],
            cwd=str(folder),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        output_lines, run_id, accuracy = [], None, None
        try:
            for raw in proc.stdout:
                line = raw.rstrip()
                if not line: continue
                output_lines.append(line)
                progress(line)

                m = re.search(r'run_id[=:\s]+([a-f0-9]{32})', line)
                if m: run_id = m.group(1)
                if "[AIU]" in line:
                    am = re.search(r'acc(?:uracy)?[=:\s]+([\d.]+)', line)
                    if am:
                        try: accuracy = float(am.group(1))
                        except ValueError: pass
        except Exception: pass

        try:
            proc.wait(timeout=1800)  # 최대 30분
        except subprocess.TimeoutExpired:
            proc.kill()
            fail("학습이 30분을 초과했습니다. run.py를 확인하세요.")

        elapsed = round(time.time() - start, 1)
        if proc.returncode != 0:
            tail = "\n".join(output_lines[-8:]) if output_lines else "(출력 없음)"
            fail(f"학습 실행 중 오류 (종료코드: {proc.returncode}):\n{tail}")

        set_state(folder,
            status="trained",
            last_action="train",
            last_run_id=run_id,
            last_run_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        ok({
            "run_id": run_id,
            "model": info["model"],
            "experiment": info["experiment"],
            "mlflow_uri": info["uri"],
            "elapsed": elapsed,
            "accuracy": accuracy,
            "message": (
                f"✓ 학습 완료 ({elapsed}s)\n"
                f"  모델   : {info['model']}\n"
                f"  run_id : {run_id or '(MLflow UI에서 확인)'}\n"
                + (f"  accuracy: {accuracy:.4f}\n" if accuracy else "")
                + "\n→ '추론 테스트해줘'로 predict를 진행하세요."
            )
        })
    except SystemExit: raise
    except Exception as e:
        fail(f"학습 중 예상치 못한 오류: {e}")
    finally:
        if proc and proc.poll() is None:
            try: proc.kill()
            except Exception: pass


if __name__ == "__main__":
    check_only = "--check-only" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    folder = get_folder(args[0] if args else None)

    # 게이트 확인
    # 파일 점검 (삭제/수정 감지)
    fc = check_files_consistency(folder)
    if not fc["ok"]:
        fail(fc["message"])
    if fc["warnings"]:
        for w in fc["warnings"]:
            progress(f"[안내] {w}")
    passed, msg = check_gate(folder, "train")
    if not passed: fail(msg)

    info = check_run_py(folder)
    if check_only:
        ok({"check": "ok", "experiment": info["experiment"],
            "model": info["model"], "mlflow_uri": info["uri"],
            "message": "사전 확인 완료 — 학습을 시작할 수 있습니다."})
    else:
        run_training(folder, info)
