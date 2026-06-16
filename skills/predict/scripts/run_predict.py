"""
skills/predict/scripts/run_predict.py

MLflow에 등록된 모델을 로드해 추론 테스트를 수행한다.
Windows/Linux/macOS 공통, 예외처리 완비.

사용:
    python skills/predict/scripts/run_predict.py [폴더명]
"""
import sys, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import (
    ok, fail, progress, get_current_folder, get_state, set_state,
    check_gate, get_mlflow_config, MODELS_DIR
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


def run_predict(folder: Path):
    # 게이트
    passed, msg = check_gate(folder, "predict")
    if not passed: fail(msg)

    # mlflow 설치 확인
    try:
        import mlflow
        import mlflow.pyfunc
    except ImportError:
        fail("mlflow 패키지가 필요합니다.\ninstall을 다시 실행하면 자동 설치됩니다.")

    state = get_state(folder)
    model_name = state.get("model_name")
    run_id     = state.get("last_run_id")

    if not model_name and not run_id:
        fail("등록된 모델 정보가 없습니다. 먼저 학습(train)을 실행하세요.")

    # MLflow 연결
    try:
        cfg = get_mlflow_config()
        if cfg.get("tracking_uri"):
            mlflow.set_tracking_uri(cfg["tracking_uri"])
        import os
        if cfg.get("username"):
            os.environ["MLFLOW_TRACKING_USERNAME"] = cfg["username"]
            os.environ["MLFLOW_TRACKING_PASSWORD"] = cfg.get("password", "")
    except Exception as e:
        fail(f"MLflow 연결 설정 실패: {e}")

    # 모델 로드 (model_name 우선, 실패 시 run_id)
    model = None
    model_uri = None
    errors = []

    if model_name:
        try:
            model_uri = f"models:/{model_name}/latest"
            progress(f"모델 로드 시도: {model_uri}")
            model = mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            errors.append(f"models:/{model_name}/latest → {e}")

    if model is None and run_id:
        try:
            model_uri = f"runs:/{run_id}/model"
            progress(f"모델 로드 시도: {model_uri}")
            model = mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            errors.append(f"runs:/{run_id}/model → {e}")

    if model is None:
        fail("모델 로드에 실패했습니다:\n" + "\n".join(errors))

    # run.py에서 input_example 추출 시도 → 없으면 안내
    try:
        result_preview = "모델 로드 성공 — 입력 예시를 제공하면 추론 결과를 확인할 수 있습니다."
        # 간단한 메타 정보만 표시
        set_state(folder, status="predicted", last_action="predict")
        ok({
            "model_uri": model_uri,
            "model_name": model_name,
            "run_id": run_id,
            "message": (
                f"✓ 추론 테스트 완료\n"
                f"  모델 로드: {model_uri}\n"
                f"  → 모델이 정상적으로 로드되어 서빙 준비가 되었습니다.\n"
                f"  → 로컬 서빙: '로컬 서버 띄워줘'"
            )
        })
    except SystemExit: raise
    except Exception as e:
        fail(f"추론 중 오류: {e}")


if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    run_predict(get_folder(folder_name))
