"""
skills/local_serve/scripts/start_server.py

workspace/results/<folder>/ 의 로컬 저장 모델을 FastAPI로 서빙한다.
서버는 백그라운드로 실행되고 PID를 .aiu_state.json에 저장한다.

사용:
    python skills/local_serve/scripts/start_server.py [폴더명] [--port 8000]
"""
import sys
import os
import json
import subprocess
import time
import socket
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, get_current_folder, get_state, set_state,
    check_gate, MODELS_DIR, WORKSPACE_DIR, ROOT
)


def find_free_port(start=8000):
    for port in range(start, start + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    fail("사용 가능한 포트를 찾지 못했습니다 (8000~8009).")


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


def find_model_file(results_dir: Path):
    """results/ 에서 모델 파일 찾기."""
    for ext in ["*.pkl", "*.joblib", "*.pt", "*.pth", "*.h5", "*.keras"]:
        files = list(results_dir.glob(ext))
        if files:
            return files[0]
    return None


def make_server_script(model_path: Path, port: int) -> Path:
    """FastAPI 서버 스크립트 동적 생성."""
    ext = model_path.suffix.lower()

    if ext in (".pkl", ".joblib"):
        load_code = f"""
import joblib
model = joblib.load("{model_path}")

@app.post("/predict")
async def predict(request: Request):
    body = await request.json()
    import numpy as np
    data = np.array(body["input"])
    if data.ndim == 1:
        data = data.reshape(1, -1)
    result = model.predict(data).tolist()
    return {{"prediction": result, "model": "{model_path.name}"}}
"""
    elif ext in (".pt", ".pth"):
        load_code = f"""
import torch
# TODO: 모델 클래스 정의 필요
# model = MyModel()
# model.load_state_dict(torch.load("{model_path}"))
# model.eval()
model = None

@app.post("/predict")
async def predict(request: Request):
    if model is None:
        return {{"error": "PyTorch 모델 클래스 정의 필요. start_server.py의 load_code 수정 필요."}}
    body = await request.json()
    import numpy as np
    x = torch.FloatTensor(body["input"])
    with torch.no_grad():
        result = model(x).numpy().tolist()
    return {{"prediction": result}}
"""
    elif ext in (".h5", ".keras"):
        load_code = f"""
import tensorflow as tf
model = tf.keras.models.load_model("{model_path}")

@app.post("/predict")
async def predict(request: Request):
    body = await request.json()
    import numpy as np
    data = np.array(body["input"])
    if data.ndim == 1:
        data = data.reshape(1, -1)
    result = model.predict(data).tolist()
    return {{"prediction": result, "model": "{model_path.name}"}}
"""
    else:
        fail(f"지원하지 않는 모델 형식: {ext}")

    script = f"""
import uvicorn
from fastapi import FastAPI, Request

app = FastAPI(title="aiu-agent local serve")

{load_code}

@app.get("/health")
def health():
    return {{"status": "ok", "model": "{model_path.name}"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
"""
    tmp = Path(tempfile.mktemp(suffix="_server.py"))
    tmp.write_text(script, encoding="utf-8")
    return tmp


def start(folder: Path, port: int):
    # 게이트 확인
    passed, msg = check_gate(folder, "local_serve")
    if not passed:
        fail(msg)

    # 이미 서버 실행 중인지 확인
    state = get_state(folder)
    existing_pid = state.get("serve_pid")
    if existing_pid:
        try:
            os.kill(existing_pid, 0)
            fail(f"이미 서버가 실행 중입니다 (PID: {existing_pid}, 포트: {state.get('serve_port')})\n"
                 f"→ '서버 꺼줘'로 먼저 종료하세요.")
        except OSError:
            pass  # 프로세스 없음 — 계속 진행

    # 모델 파일 찾기
    results_dir = WORKSPACE_DIR / "results" / folder.name
    if not results_dir.exists():
        fail(f"결과 폴더가 없습니다: {results_dir}\n"
             f"→ 먼저 로컬 테스트('로컬 실행해줘')를 실행하세요.")

    model_file = find_model_file(results_dir)
    if not model_file:
        fail(f"모델 파일을 찾을 수 없습니다: {results_dir}\n"
             f"→ 로컬 테스트 또는 train을 먼저 실행하세요.")

    # 포트 결정
    actual_port = find_free_port(port)
    server_script = make_server_script(model_file, actual_port)

    # fastapi/uvicorn 설치 확인
    try:
        import fastapi, uvicorn
    except ImportError:
        fail("FastAPI/uvicorn이 설치되지 않았습니다.\n"
             "pip install fastapi uvicorn 을 실행하세요.")

    # 백그라운드 서버 시작
    proc = subprocess.Popen(
        [sys.executable, str(server_script)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 서버 기동 대기 (최대 5초)
    for _ in range(10):
        time.sleep(0.5)
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{actual_port}/health", timeout=1)
            break
        except Exception:
            continue
    else:
        proc.terminate()
        server_script.unlink(missing_ok=True)
        fail("서버 시작에 실패했습니다. 모델 파일 또는 의존성을 확인하세요.")

    # 상태 저장
    set_state(folder,
        serve_pid=proc.pid,
        serve_port=actual_port,
        serve_model=str(model_file),
        server_script=str(server_script),
    )

    ok({
        "pid": proc.pid,
        "port": actual_port,
        "model": model_file.name,
        "message": (
            f"✓ 로컬 서버 시작 (PID: {proc.pid})\n"
            f"  주소    : http://localhost:{actual_port}\n"
            f"  모델    : {model_file.name}\n"
            f"  헬스체크: GET  http://localhost:{actual_port}/health\n"
            f"  추론    : POST http://localhost:{actual_port}/predict\n\n"
            f"  테스트 예시:\n"
            f'  curl -X POST http://localhost:{actual_port}/predict \\\n'
            f'       -H "Content-Type: application/json" \\\n'
            f'       -d \'{{"input": [1.0, 2.0, 3.0]}}\'\n\n'
            f"  서버 종료: '서버 꺼줘'"
        )
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs="?", default=None)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    folder = get_folder(args.folder)
    start(folder, args.port)
