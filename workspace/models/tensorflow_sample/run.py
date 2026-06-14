# =============================================================
#  AIU run.py - TensorFlow(Keras) 샘플 (9-섹션 표준)
#  의존성: 이 폴더의 requirements.txt 설치 필요 (pip install -r requirements.txt)
# =============================================================

# -------------------------------------------------------------
# 1. 임포트 영역
# -------------------------------------------------------------
import os
import json
from pathlib import Path

import mlflow
import mlflow.tensorflow
import numpy as np
import tensorflow as tf
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# -------------------------------------------------------------
# 2. MLflow 연동 영역  (작업 환경이 바뀌면 이 부분만 수정)
# -------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]  # 프로젝트 루트

MLFLOW_TRACKING_URI = "http://your-mlflow:5000"  # TODO: MLflow 서버 주소
MLFLOW_USERNAME = ""                             # TODO: 계정 (인증 없으면 비움)
MLFLOW_PASSWORD = ""                             # TODO:

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
if MLFLOW_USERNAME:
    os.environ["MLFLOW_TRACKING_USERNAME"] = MLFLOW_USERNAME
    os.environ["MLFLOW_TRACKING_PASSWORD"] = MLFLOW_PASSWORD

EXPERIMENT_NAME = "aiu-tensorflow-sample"   # TODO: 실험명
MODEL_NAME = "aiu-sample-model"          # TODO: 모델 레지스트리 등록명

mlflow.set_experiment(EXPERIMENT_NAME)


# -------------------------------------------------------------
# 3. 데이터 준비
# -------------------------------------------------------------
def prepare_data():
    X, y = make_classification(
        n_samples=1000, n_features=10, n_informative=6, random_state=42
    )
    return train_test_split(
        X.astype("float32"), y, test_size=0.2, random_state=42
    )


# -------------------------------------------------------------
# 4. 모델 준비
# -------------------------------------------------------------
def build_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(10,)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(2, activation="softmax"),
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# -------------------------------------------------------------
# 5. 트레이닝 펑션
# -------------------------------------------------------------
def train(model, X_train, y_train, epochs=10):
    model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=0)
    return model


# -------------------------------------------------------------
# 6. 옵션 - 인풋 샘플
# -------------------------------------------------------------
def get_input_example(X):
    return X[:5]


# -------------------------------------------------------------
# 7. MLflow에 모델 로깅
# -------------------------------------------------------------
def log_model(model, input_example):
    mlflow.tensorflow.log_model(
        model,
        name="model",
        input_example=input_example,
        registered_model_name=MODEL_NAME,
    )


# -------------------------------------------------------------
# 8. 옵션 - config.json 정의
# -------------------------------------------------------------
def write_config(save_dir: Path):
    save_dir.mkdir(parents=True, exist_ok=True)
    config = {"model_name": MODEL_NAME, "framework": "tensorflow"}
    (save_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# -------------------------------------------------------------
# 9. 런 스타트
# -------------------------------------------------------------
if __name__ == "__main__":
    USE_DATALAKE = False                     # TODO: datalake 사용 여부
    SAVE_DIR = ROOT / "model_result"         # TODO: 저장 경로

    with mlflow.start_run() as run:
        X_train, X_test, y_train, y_test = prepare_data()
        model = train(build_model(), X_train, y_train)

        _, acc = model.evaluate(X_test, y_test, verbose=0)
        mlflow.log_metric("accuracy", acc)

        log_model(model, get_input_example(X_train))
        write_config(SAVE_DIR)
        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME} acc={acc:.4f} 등록 완료")
