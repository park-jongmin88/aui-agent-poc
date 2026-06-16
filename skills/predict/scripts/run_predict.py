"""
skills/predict/scripts/run_predict.py

MLflow에 등록된 모델을 로드해 실제 추론 테스트를 수행한다.
- input_example.json 있으면 그대로 사용 (KServe 형식 포함)
- 없으면 state의 모델 정보로 샘플 생성
Windows/Linux/macOS 공통, 예외처리 완비.
"""
import sys, json, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, progress, get_current_folder, get_state, set_state,
    check_gate, check_files_consistency, get_mlflow_config, MODELS_DIR, WORKSPACE_DIR
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


def load_input_example(folder: Path):
    """input_example.json 로드 시도. 없으면 None 반환."""
    # 폴더 내 / workspace 루트 / 현재 디렉토리 순서로 탐색
    candidates = [
        folder / "input_example.json",
        folder / "source" / "input_example.json",
        Path("input_example.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data, str(p)
            except Exception:
                continue
    return None, None


def run_inference(model, input_data, model_uri: str):
    """실제 추론 실행. KServe 형식과 일반 형식 모두 처리."""
    import numpy as np

    result = None
    used_format = "unknown"

    # KServe 형식: {"input": [{"name":..., "shape":..., "data":...}]}
    if isinstance(input_data, dict) and "input" in input_data:
        try:
            inp = input_data["input"][0]
            data = np.array(inp["data"])
            if "shape" in inp:
                data = data.reshape(inp["shape"])
            result = model.predict(data)
            used_format = "KServe"
        except Exception as e:
            progress(f"KServe 형식 추론 실패: {e} — 일반 형식 시도")

    # 일반 형식: numpy array / list
    if result is None:
        try:
            import pandas as pd
            if isinstance(input_data, (list, dict)):
                arr = np.array(input_data)
            else:
                arr = input_data
            result = model.predict(arr)
            used_format = "일반"
        except Exception as e:
            fail(f"추론 실패: {e}\n모델: {model_uri}")

    # 결과 직렬화 (numpy → list)
    if hasattr(result, "tolist"):
        result = result.tolist()

    return result, used_format


def run_predict(folder: Path):
    # 게이트
    # 파일 점검 (삭제/수정 감지)
    fc = check_files_consistency(folder)
    if not fc["ok"]:
        fail(fc["message"])
    if fc["warnings"]:
        for w in fc["warnings"]:
            progress(f"[안내] {w}")
    passed, msg = check_gate(folder, "predict")
    if not passed: fail(msg)

    try:
        import mlflow, mlflow.pyfunc
    except ImportError:
        fail("mlflow 패키지가 필요합니다.\ninstall을 다시 실행하면 자동 설치됩니다.")

    state      = get_state(folder)
    model_name = state.get("model_name")
    run_id     = state.get("last_run_id")

    if not model_name and not run_id:
        fail("등록된 모델 정보가 없습니다. 먼저 학습(train)을 실행하세요.")

    # MLflow 연결
    try:
        cfg = get_mlflow_config()
        if cfg.get("tracking_uri"):
            mlflow.set_tracking_uri(cfg["tracking_uri"])
        os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"
        if cfg.get("username"):
            os.environ["MLFLOW_TRACKING_USERNAME"] = cfg["username"]
            os.environ["MLFLOW_TRACKING_PASSWORD"] = cfg.get("password", "")
    except Exception as e:
        fail(f"MLflow 연결 설정 실패: {e}")

    # 모델 로드
    model, model_uri, errors = None, None, []

    if model_name:
        try:
            model_uri = f"models:/{model_name}/latest"
            progress(f"모델 로드: {model_uri}")
            model = mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            errors.append(f"models:/{model_name}/latest → {e}")

    if model is None and run_id:
        try:
            model_uri = f"runs:/{run_id}/model"
            progress(f"모델 로드: {model_uri}")
            model = mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            errors.append(f"runs:/{run_id}/model → {e}")

    if model is None:
        fail("모델 로드 실패:\n" + "\n".join(errors))

    progress(f"모델 로드 완료: {model_uri}")

    # input_example 로드
    input_data, input_path = load_input_example(folder)

    if input_data is None:
        # input_example.json 없음 — 샘플 생성 시도
        progress("input_example.json 없음 — 샘플 데이터로 추론 시도")
        try:
            import numpy as np
            # model_input_schema에서 shape 추론
            schema = getattr(model, "_model_meta", None)
            sample = np.zeros((1, 10))  # TODO: 실제 feature 수에 맞게
            input_data = sample
            input_path = "(샘플 데이터)"
        except Exception:
            fail(
                "input_example.json 을 찾을 수 없습니다.\n"
                f"다음 위치 중 하나에 생성해주세요:\n"
                f"  - workspace/models/{folder.name}/input_example.json\n"
                f"  - workspace/models/{folder.name}/source/input_example.json\n"
                "run.py 실행 시 자동 생성됩니다 (PYFUNC 모드)."
            )

    # 추론 실행
    progress(f"추론 실행 중... (입력: {input_path})")
    try:
        result, used_format = run_inference(model, input_data, model_uri)
    except SystemExit:
        raise
    except Exception as e:
        fail(f"추론 중 오류: {e}")

    # 결과 미리보기 (최대 5개)
    preview = result[:5] if isinstance(result, list) and len(result) > 5 else result

    set_state(folder, status="predicted", last_action="predict")

    ok({
        "model_uri":    model_uri,
        "model_name":   model_name,
        "run_id":       run_id,
        "input_path":   input_path,
        "input_format": used_format,
        "result_preview": preview,
        "message": (
            f"✓ 추론 테스트 완료\n"
            f"  모델    : {model_uri}\n"
            f"  입력    : {input_path} ({used_format} 형식)\n"
            f"  결과 미리보기: {preview}\n"
            f"  → 로컬 서빙: '로컬 서버 띄워줘'"
        )
    })


if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    run_predict(get_folder(folder_name))
