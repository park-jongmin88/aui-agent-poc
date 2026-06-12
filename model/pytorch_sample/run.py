# =============================================================
#  AIU run.py - PyTorch 샘플 (9-섹션 표준)
#  의존성: 이 폴더의 requirements.txt 설치 필요 (pip install -r requirements.txt)
# =============================================================

# -------------------------------------------------------------
# 1. 임포트 영역
# -------------------------------------------------------------
import os
import json
from pathlib import Path

import mlflow
import mlflow.pytorch
from dotenv import load_dotenv
import numpy as np
import torch
import torch.nn as nn
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# -------------------------------------------------------------
# 2. MLflow 연동 영역
# -------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

EXPERIMENT_NAME = "aiu-pytorch-sample"   # TODO: 실험명
MODEL_NAME = "aiu-sample-model"          # TODO: 모델 레지스트리 등록명

mlflow.set_experiment(EXPERIMENT_NAME)


# -------------------------------------------------------------
# 3. 데이터 준비
# -------------------------------------------------------------
def prepare_data():
    X, y = make_classification(
        n_samples=1000, n_features=10, n_informative=6, random_state=42
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return (
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(X_test, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.long),
        torch.tensor(y_test, dtype=torch.long),
    )


# -------------------------------------------------------------
# 4. 모델 준비
# -------------------------------------------------------------
def build_model():
    return nn.Sequential(
        nn.Linear(10, 32), nn.ReLU(),
        nn.Linear(32, 16), nn.ReLU(),
        nn.Linear(16, 2),
    )


# -------------------------------------------------------------
# 5. 트레이닝 펑션
# -------------------------------------------------------------
def train(model, X_train, y_train, epochs=20):
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        loss = criterion(model(X_train), y_train)
        loss.backward()
        optimizer.step()
    return model


# -------------------------------------------------------------
# 6. 옵션 - 인풋 샘플
# -------------------------------------------------------------
def get_input_example(X):
    return X[:5].numpy()


# -------------------------------------------------------------
# 7. MLflow에 모델 로깅
# -------------------------------------------------------------
def log_model(model, input_example):
    mlflow.pytorch.log_model(
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
    config = {"model_name": MODEL_NAME, "framework": "pytorch"}
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

        model.eval()
        with torch.no_grad():
            acc = (model(X_test).argmax(1) == y_test).float().mean().item()
        mlflow.log_metric("accuracy", acc)

        log_model(model, get_input_example(X_train))
        write_config(SAVE_DIR)
        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME} acc={acc:.4f} 등록 완료")
