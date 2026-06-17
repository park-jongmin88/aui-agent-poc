"""
skills/localserve/scripts/stop_server.py
Windows/Linux/macOS 공통, 예외처리 완비
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    safe_main,
    ok, fail, get_current_folder, get_state, set_state,
    kill_process, safe_unlink, MODELS_DIR
)


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


def stop(folder):
    try:
        state = get_state(folder)
    except Exception as e:
        fail(f"상태 파일 읽기 실패: {e}")

    pid     = state.get("serve_pid")
    port    = state.get("serve_port")
    script  = state.get("server_script")

    if not pid:
        fail("실행 중인 서버가 없습니다.")

    # 프로세스 종료
    killed = kill_process(pid)

    # 임시 스크립트 정리
    if script:
        safe_unlink(Path(script))

    # 상태 초기화
    try:
        set_state(folder,
            serve_pid=None,
            serve_port=None,
            serve_model=None,
            server_script=None,
        )
    except Exception as e:
        # 상태 저장 실패는 치명적이지 않음
        pass

    ok({
        "message": (
            f"✓ 서버 종료 {'완료' if killed else '시도'}\n"
            f"  PID: {pid}  /  포트: {port}"
        )
    })


def _main():
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    stop(get_folder(folder_name))


if __name__ == "__main__":
    safe_main(_main)
