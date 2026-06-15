"""
skills/train/scripts/run_train.py

workspace/run.py 를 실행해 모델을 학습하고 MLflow에 등록한다.
실행 중 표준 출력을 실시간으로 스트리밍하고,
완료 시 run_id, 모델명, 주요 메트릭을 JSON으로 반환한다.

사용:
    python skills/train/scripts/run_train.py [--check-only]
    --check-only : run.py 존재/MLflow 설정 여부만 확인하고 종료
"""
import sys
import subprocess
import time
import re
import json
from pathlib import Path

# 공통 유틸
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import ok, fail, RUN_PY, ROOT

CHECK_ONLY = "--check-only" in sys.argv


def check_run_py():
    """run.py 존재 및 MLflow 설정 여부 확인."""
    if not RUN_PY.exists():
        fail(
            "workspace/run.py 가 없습니다.\n"
            "먼저 작업 폴더를 선택하고 준비(init)를 실행해주세요."
        )

    text = RUN_PY.read_text(encoding="utf-8")

    # MLflow URI 설정 확인
    uri_match = re.search(r'MLFLOW_TRACKING_URI\s*=\s*["\'](.+?)["\']', text)
    uri = uri_match.group(1) if uri_match else ""
    if not uri or "your-mlflow" in uri:
        fail(
            "workspace/run.py 의 MLflow 주소가 설정되지 않았습니다.\n"
            "섹션 2의 MLFLOW_TRACKING_URI 를 실제 주소로 수정해주세요."
        )

    # EXPERIMENT_NAME 확인
    exp_match = re.search(r'EXPERIMENT_NAME\s*=\s*["\'](.+?)["\']', text)
    exp = exp_match.group(1) if exp_match else ""

    # MODEL_NAME 확인
    model_match = re.search(r'MODEL_NAME\s*=\s*["\'](.+?)["\']', text)
    model = model_match.group(1) if model_match else ""

    return {"uri": uri, "experiment": exp, "model": model}


def run_training(info: dict):
    """run.py 실행 + 실시간 출력 스트리밍."""
    print(json.dumps({
        "status": "running",
        "message": f"학습 시작 → MLflow: {info['uri']} / 실험: {info['experiment']}",
    }, ensure_ascii=False), flush=True)

    start = time.time()
    proc = subprocess.Popen(
        [sys.executable, str(RUN_PY)],
        cwd=str(ROOT / "workspace"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    output_lines = []
    run_id = None
    accuracy = None

    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        output_lines.append(line)

        # 실시간 진행 상황 스트리밍
        print(json.dumps({"status": "progress", "line": line}, ensure_ascii=False), flush=True)

        # MLflow run_id 파싱
        m = re.search(r'run_id[=:\s]+([a-f0-9]{32})', line)
        if m:
            run_id = m.group(1)

        # [AIU] 결과 라인 파싱
        if "[AIU]" in line:
            acc_m = re.search(r'acc[=:\s]+([\d.]+)', line)
            if acc_m:
                accuracy = float(acc_m.group(1))

    proc.wait()
    elapsed = time.time() - start

    if proc.returncode != 0:
        fail(
            f"학습 실행 중 오류가 발생했습니다. (exit code: {proc.returncode})\n"
            + "\n".join(output_lines[-5:])  # 마지막 5줄만
        )

    ok({
        "run_id": run_id,
        "model": info["model"],
        "experiment": info["experiment"],
        "mlflow_uri": info["uri"],
        "elapsed": round(elapsed, 1),
        "accuracy": accuracy,
        "message": (
            f"✓ 학습 완료 ({elapsed:.1f}s)\n"
            f"  모델: {info['model']}\n"
            f"  run_id: {run_id or '(파싱 실패 - MLflow에서 확인)'}\n"
            + (f"  accuracy: {accuracy:.4f}" if accuracy else "")
        )
    })


if __name__ == "__main__":
    info = check_run_py()

    if CHECK_ONLY:
        ok({"check": "ok", **info})
    else:
        run_training(info)
