# =============================================================
#  AIU run.py - 베이스 템플릿 (9-섹션 표준)
#  이 파일은 원본입니다. init 스킬이 model/ 폴더로 복사합니다.
# =============================================================

# -------------------------------------------------------------
# 1. 임포트 영역
# -------------------------------------------------------------
import os
import json
from pathlib import Path

import mlflow
from dotenv import load_dotenv

# TODO: 사용할 프레임워크 임포트 (sklearn / torch / tensorflow)


# -------------------------------------------------------------
# 2. MLflow 연동 영역
# -------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parents[2] / ".env")  # 프로젝트 루트의 .env

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

EXPERIMENT_NAME = "my-experiment"   # TODO: 실험명
MODEL_NAME = "my-model"             # TODO: 모델 레지스트리 등록명

mlflow.set_experiment(EXPERIMENT_NAME)


# -------------------------------------------------------------
# 3. 데이터 준비
# -------------------------------------------------------------
def prepare_data():
    # TODO: 데이터 로딩/생성 (권장: sklearn.datasets.make_classification)
    raise NotImplementedError


# -------------------------------------------------------------
# 4. 모델 준비
# -------------------------------------------------------------
def build_model():
    # TODO: 모델 정의
    raise NotImplementedError


# -------------------------------------------------------------
# 5. 트레이닝 펑션
# -------------------------------------------------------------
def train(model, X_train, y_train):
    # TODO: 학습 로직
    raise NotImplementedError


# -------------------------------------------------------------
# 6. 옵션 - 인풋 샘플
# -------------------------------------------------------------
def get_input_example(X):
    # TODO: 모델 시그니처용 인풋 샘플 반환 (예: X[:5])
    raise NotImplementedError


# -------------------------------------------------------------
# 7. MLflow에 모델 로깅
# -------------------------------------------------------------
def log_model(model, input_example):
    # TODO: 프레임워크에 맞는 로깅 (예: mlflow.sklearn.log_model)
    raise NotImplementedError


# -------------------------------------------------------------
# 8. 옵션 - config.json 정의
# -------------------------------------------------------------
def write_config(save_dir: Path):
    config = {
        "model_name": MODEL_NAME,
        # TODO: 서빙에 필요한 추가 설정
    }
    (save_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# -------------------------------------------------------------
# 9. 런 스타트
# -------------------------------------------------------------
if __name__ == "__main__":
    USE_DATALAKE = False                          # TODO: datalake 사용 여부
    SAVE_DIR = Path(__file__).resolve().parents[2] / "model_result"  # TODO: 저장 경로

    with mlflow.start_run() as run:
        X_train, y_train = prepare_data()
        model = build_model()
        train(model, X_train, y_train)
        log_model(model, get_input_example(X_train))
        write_config(SAVE_DIR)
        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME} 등록 완료")
