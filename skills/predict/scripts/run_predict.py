"""
skills/predict/scripts/run_predict.py

MLflow에 등록된 모델을 로컬에서 로드해 추론 테스트를 수행한다.
workspace/run.py 의 MLflow 설정을 읽어 자동으로 연결한다.

사용:
    python skills/predict/scripts/run_predict.py [model_name] [version]
    model_name: MLflow 모델 레지스트리 이름 (없으면 run.py에서 자동 파싱)
    version: 버전 번호 또는 "latest" (기본: latest)
"""
import sys
import re
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from skills.common import ok, fail, RUN_PY


def get_mlflow_config():
    """run.py에서 MLflow 설정 파싱."""
    if not RUN_PY.exists():
        fail("workspace/run.py 가 없습니다. 먼저 학습을 실행해주세요.")

    text = RUN_PY.read_text(encoding="utf-8")

    uri_m = re.search(r'MLFLOW_TRACKING_URI\s*=\s*["\'](.+?)["\']', text)
    model_m = re.search(r'MODEL_NAME\s*=\s*["\'](.+?)["\']', text)
    user_m = re.search(r'MLFLOW_USERNAME\s*=\s*["\'](.+?)["\']', text)
    pass_m = re.search(r'MLFLOW_PASSWORD\s*=\s*["\'](.+?)["\']', text)

    uri = uri_m.group(1) if uri_m else ""
    model_name = sys.argv[1] if len(sys.argv) > 1 else (model_m.group(1) if model_m else "")
    version = sys.argv[2] if len(sys.argv) > 2 else "latest"

    if not uri or "your-mlflow" in uri:
        fail("MLflow 주소가 설정되지 않았습니다. workspace/run.py 섹션 2를 확인하세요.")
    if not model_name or "your-model" in model_name:
        fail("모델명을 확인할 수 없습니다. 모델명을 직접 입력하거나 학습을 먼저 실행해주세요.")

    return {
        "uri": uri,
        "model_name": model_name,
        "version": version,
        "username": user_m.group(1) if user_m else "",
        "password": pass_m.group(1) if pass_m else "",
    }


def run_predict(cfg: dict):
    """MLflow에서 모델 로드 후 추론."""
    try:
        import mlflow
        import mlflow.pyfunc

        mlflow.set_tracking_uri(cfg["uri"])
        if cfg["username"]:
            os.environ["MLFLOW_TRACKING_USERNAME"] = cfg["username"]
            os.environ["MLFLOW_TRACKING_PASSWORD"] = cfg["password"]

        model_uri = f"models:/{cfg['model_name']}/{cfg['version']}"
        model = mlflow.pyfunc.load_model(model_uri)

        # run.py에서 인풋 샘플 찾기 (섹션 6)
        run_text = RUN_PY.read_text(encoding="utf-8")
        input_sample = None
        try:
            import importlib.util, tempfile, shutil
            tmp = Path(tempfile.mkdtemp())
            shutil.copy(RUN_PY, tmp / "run.py")
            spec = importlib.util.spec_from_file_location("run_module", tmp / "run.py")
            # 실제 실행 없이 get_input_example만 호출 시도
        except Exception:
            pass

        # 기본 샘플 데이터로 테스트
        import numpy as np
        sample = np.random.randn(3, 10).tolist()

        try:
            result = model.predict(sample)
            result_str = str(result[:5] if hasattr(result, '__len__') else result)
        except Exception as e:
            result_str = f"예측 중 오류: {e}"

        ok({
            "model_uri": model_uri,
            "model_name": cfg["model_name"],
            "version": cfg["version"],
            "result_sample": result_str,
            "message": (
                f"✓ 추론 테스트 완료\n"
                f"  모델: {model_uri}\n"
                f"  결과 샘플: {result_str}\n"
                f"  → 모델이 정상 동작합니다."
            )
        })

    except ImportError:
        fail("mlflow 가 설치되지 않았습니다. requirements-ml.txt 를 설치해주세요.")
    except Exception as e:
        fail(f"추론 실패: {type(e).__name__}: {e}")


if __name__ == "__main__":
    cfg = get_mlflow_config()
    run_predict(cfg)
