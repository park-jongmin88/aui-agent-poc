"""
skills/local_serve/scripts/stop_server.py

실행 중인 로컬 서버를 종료한다.

사용:
    python skills/local_serve/scripts/stop_server.py [폴더명]
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, get_current_folder, get_state, set_state, MODELS_DIR
)


def get_folder(folder_name=None) -> Path:
    if folder_name:
        folder = MODELS_DIR / folder_name
        if not folder.exists():
            fail(f"폴더를 찾을 수 없습니다: workspace/models/{folder_name}")
        return folder
    folder = get_current_folder()
    if not folder:
        fail("현재 작업 폴더가 없습니다.")
    return folder


def stop(folder: Path):
    state = get_state(folder)
    pid = state.get("serve_pid")
    port = state.get("serve_port")
    script = state.get("server_script")

    if not pid:
        fail("실행 중인 서버가 없습니다.")

    # 프로세스 종료
    try:
        os.kill(pid, 15)  # SIGTERM
        import time; time.sleep(0.5)
        try:
            os.kill(pid, 9)  # SIGKILL (남아있으면)
        except OSError:
            pass
        terminated = True
    except OSError:
        terminated = True  # 이미 종료됨

    # 임시 스크립트 파일 정리
    if script and Path(script).exists():
        Path(script).unlink(missing_ok=True)

    # 상태 초기화
    set_state(folder, serve_pid=None, serve_port=None,
              serve_model=None, server_script=None)

    ok({
        "message": (
            f"✓ 서버 종료 완료\n"
            f"  PID: {pid}  /  포트: {port}"
        )
    })


if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    folder = get_folder(folder_name)
    stop(folder)
