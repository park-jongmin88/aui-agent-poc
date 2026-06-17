"""
skills/predict/scripts/inference_test.py

배포된 AI Studio Endpoint URL로 추론 요청을 보낸다.
predict 스킬의 두 번째 선택지 (① 로컬 추론은 run_predict.py).

input_example.json (KServe 형식)을 그대로 POST 한다.

사용:
    python skills/predict/scripts/inference_test.py [폴더명] [--url ENDPOINT_URL]
    - url 미지정 시: 상태(.aiu_state.json)의 endpoint_url 사용
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, progress, get_current_folder, get_state, MODELS_DIR
)


def get_folder(name=None):
    try:
        if name:
            f = MODELS_DIR / name
            if not f.exists():
                fail(f"폴더 없음: workspace/models/{name}")
            return f
        f = get_current_folder()
        if not f:
            fail("현재 작업 폴더가 없습니다.")
        return f
    except SystemExit:
        raise
    except Exception as e:
        fail(f"폴더 확인 오류: {e}")


def load_input_example(folder: Path):
    """input_example.json 탐색."""
    candidates = [
        folder / "input_example.json",
        folder / "source" / "input_example.json",
        Path("input_example.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")), str(p)
            except Exception:
                continue
    return None, None


def run_inference_test(folder: Path, url: str = None):
    try:
        import requests
    except ImportError:
        fail("requests 패키지가 필요합니다.\ninstall을 다시 실행하면 자동 설치됩니다.")

    state = get_state(folder)

    # Endpoint URL 결정: 인자 우선, 없으면 상태에서
    endpoint_url = url or state.get("endpoint_url")
    if not endpoint_url:
        fail(
            "Endpoint URL이 없습니다.\n"
            "먼저 배포(deploy)를 실행하거나 --url 로 직접 지정하세요.\n"
            "예: inference_test.py 폴더명 --url https://...../predict"
        )

    # input_example.json 로드
    input_data, input_path = load_input_example(folder)
    if input_data is None:
        fail(
            "input_example.json 을 찾을 수 없습니다.\n"
            f"  - workspace/models/{folder.name}/input_example.json\n"
            "run.py 실행 시 자동 생성됩니다."
        )

    progress(f"Endpoint 추론 요청: {endpoint_url}")
    progress(f"입력: {input_path}")

    # POST 요청
    try:
        req_msg = json.dumps(input_data)
        headers = {"Content-Type": "application/json"}
        resp = requests.post(endpoint_url, headers=headers, data=req_msg, timeout=30)
    except Exception as e:
        fail(f"Endpoint 요청 실패: {e}\nURL과 서버 상태를 확인하세요: {endpoint_url}")

    # 결과 파싱
    status_code = resp.status_code
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:500]

    if status_code != 200:
        fail(
            f"Endpoint 응답 오류 (status {status_code})\n"
            f"  URL: {endpoint_url}\n"
            f"  응답: {body}"
        )

    ok({
        "endpoint_url": endpoint_url,
        "status_code":  status_code,
        "input_path":   input_path,
        "response":     body,
        "message": (
            f"✓ Endpoint 추론 테스트 완료\n"
            f"  URL    : {endpoint_url}\n"
            f"  상태   : {status_code}\n"
            f"  입력   : {input_path}\n"
            f"  응답   : {body}"
        )
    })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs="?", default=None)
    parser.add_argument("--url", default=None)
    args = parser.parse_args()
    run_inference_test(get_folder(args.folder), args.url)
