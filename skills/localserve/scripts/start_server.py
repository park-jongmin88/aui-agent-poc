"""
skills/localserve/scripts/start_server.py
Windows/Linux/macOS 공통, 예외처리 완비
"""
import sys, os, subprocess, time, socket, tempfile, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, progress, get_current_folder, get_state, set_state,
    check_gate, safe_path_str, safe_unlink, is_process_alive,
    MODELS_DIR, WORKSPACE_DIR, ROOT
)

RESULTS_DIR = WORKSPACE_DIR / "results"
MODEL_EXTS  = (".pkl", ".joblib", ".pt", ".pth", ".h5", ".keras")


def get_folder(name=None):
    try:
        if name:
            f = MODELS_DIR / name
            if not f.exists(): fail(f"폴더 없음: workspace/models/{name}")
            return f
        f = get_current_folder()
        if not f: fail("현재 작업 폴더가 없습니다.")
        return f
    except SystemExit: raise
    except Exception as e: fail(f"폴더 확인 오류: {e}")


def find_free_port(start=8000, end=8009):
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    fail(f"사용 가능한 포트 없음 ({start}~{end}). 다른 프로세스를 확인하세요.")


def find_model_file(results_dir: Path):
    if not results_dir.exists():
        return None
    try:
        for ext in MODEL_EXTS:
            files = sorted(results_dir.glob(f"*{ext}"))
            if files:
                return files[0]
    except Exception:
        pass
    return None


def make_server_script(model_path: Path, port: int) -> Path:
    ext = model_path.suffix.lower()
    model_s = safe_path_str(model_path)

    if ext in (".pkl", ".joblib"):
        load_code = f'''\
import joblib
from pathlib import Path
try:
    _model = joblib.load("{model_s}")
    print(f"[AIU] 모델 로드 완료: {model_s}")
except Exception as e:
    print(f"[AIU][오류] 모델 로드 실패: {{e}}")
    _model = None

@app.post("/predict")
async def predict(request: Request):
    if _model is None:
        return {{"error": "모델 로드 실패"}}
    try:
        body = await request.json()
        import numpy as np
        data = np.array(body.get("input", []))
        if data.ndim == 1:
            data = data.reshape(1, -1)
        result = _model.predict(data).tolist()
        return {{"prediction": result, "model": "{model_path.name}"}}
    except Exception as e:
        return {{"error": str(e)}}
'''
    elif ext in (".pt", ".pth"):
        load_code = f'''\
import torch
# PyTorch: 모델 클래스 정의가 필요합니다.
# start_server.py 의 load_code 를 수정해 모델 클래스를 로드하세요.
_model = None

@app.post("/predict")
async def predict(request: Request):
    if _model is None:
        return {{"error": "PyTorch 모델 클래스 정의 필요. docs/ml_guide.md 참고."}}
    try:
        body = await request.json()
        import numpy as np
        x = torch.FloatTensor(body.get("input", []))
        with torch.no_grad():
            result = _model(x).numpy().tolist()
        return {{"prediction": result}}
    except Exception as e:
        return {{"error": str(e)}}
'''
    elif ext in (".h5", ".keras"):
        load_code = f'''\
try:
    import tensorflow as tf
    _model = tf.keras.models.load_model("{model_s}")
    print(f"[AIU] TF 모델 로드 완료")
except Exception as e:
    print(f"[AIU][오류] TF 모델 로드 실패: {{e}}")
    _model = None

@app.post("/predict")
async def predict(request: Request):
    if _model is None:
        return {{"error": "모델 로드 실패"}}
    try:
        body = await request.json()
        import numpy as np
        data = np.array(body.get("input", []))
        if data.ndim == 1:
            data = data.reshape(1, -1)
        result = _model.predict(data, verbose=0).tolist()
        return {{"prediction": result, "model": "{model_path.name}"}}
    except Exception as e:
        return {{"error": str(e)}}
'''
    else:
        fail(f"지원하지 않는 모델 형식: {ext}. 지원: pkl/joblib/pt/pth/h5/keras")

    script = f'''\
import uvicorn
from fastapi import FastAPI, Request

app = FastAPI(title="aiu-agent local serve", docs_url="/docs")

{load_code}

@app.get("/health")
def health():
    return {{"status": "ok", "model": "{model_path.name}", "port": {port}}}

@app.get("/")
def root():
    return {{"message": "aiu-agent local serve", "predict": "POST /predict", "health": "GET /health"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port}, log_level="warning")
'''
    try:
        fd, tmp_path = tempfile.mkstemp(suffix="_server.py", prefix="aiu_srv_")
        os.close(fd)
        tmp = Path(tmp_path)
        tmp.write_text(script, encoding="utf-8")
        return tmp
    except Exception as e:
        fail(f"서버 스크립트 생성 실패: {e}")


def check_server_ready(port: int, timeout=8) -> bool:
    """서버 기동 대기 (헬스체크)."""
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def start(folder, port):
    # 게이트
    passed, msg = check_gate(folder, "localserve")
    if not passed: fail(msg)

    # 중복 실행 확인
    state = get_state(folder)
    existing_pid  = state.get("serve_pid")
    existing_port = state.get("serve_port")
    if existing_pid and is_process_alive(existing_pid):
        fail(
            f"이미 서버가 실행 중입니다 (PID: {existing_pid}, 포트: {existing_port})\n"
            f"→ '서버 꺼줘'로 먼저 종료하세요."
        )

    # FastAPI/uvicorn 설치 확인
    try:
        import fastapi, uvicorn
    except ImportError as e:
        fail(
            f"FastAPI/uvicorn이 설치되지 않았습니다: {e}\n"
            "pip install fastapi uvicorn 을 실행하세요."
        )

    # 모델 파일 탐색
    results_dir = RESULTS_DIR / folder.name
    model_file  = find_model_file(results_dir)
    if not model_file:
        fail(
            f"모델 파일을 찾을 수 없습니다: {results_dir}\n"
            f"→ 먼저 로컬 테스트('로컬 실행해줘') 또는 학습('학습해줘')을 실행하세요."
        )

    # 포트 확보
    actual_port = find_free_port(port)
    server_script = None

    try:
        server_script = make_server_script(model_file, actual_port)
    except SystemExit: raise
    except Exception as e: fail(f"서버 스크립트 준비 실패: {e}")

    # 서버 시작
    try:
        proc = subprocess.Popen(
            [sys.executable, str(server_script)],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        safe_unlink(server_script)
        fail(f"서버 프로세스 시작 실패: {e}")

    # 기동 대기
    if not check_server_ready(actual_port, timeout=10):
        try: proc.kill()
        except Exception: pass
        safe_unlink(server_script)
        fail(
            "서버가 10초 내에 응답하지 않습니다.\n"
            "모델 파일이 올바른지 확인하세요."
        )

    # 상태 저장
    set_state(folder,
        serve_pid=proc.pid,
        serve_port=actual_port,
        serve_model=model_file.name,
        server_script=safe_path_str(server_script),
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
            f"  API문서 : GET  http://localhost:{actual_port}/docs\n"
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
    start(get_folder(args.folder), args.port)
