from __future__ import annotations

import io
import inspect
import json
import logging
import os
import sys
from pathlib import Path
from urllib.parse import quote

import mlflow
import numpy as np
import torch
from torch import nn

from aiu_custom.predict import ModelWrapper


logging.getLogger("mlflow").setLevel(logging.ERROR)


def configure_utf8_stdio() -> None:
    """Windows console encoding guard."""
    if os.name != "nt":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
        elif hasattr(stream, "buffer"):
            setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8"))


configure_utf8_stdio()

PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_MODEL_PATH = PROJECT_DIR / "data" / "torch" / "model.pt"
DATA_MODEL_PATH = SOURCE_MODEL_PATH
MODEL_KIND = "pytorch"
MODEL_LOAD_HINT = "torch.load(MODEL_PATH, map_location='cpu')"
INPUT_EXAMPLE_PATH = PROJECT_DIR / "input_example.json"
CONFIG_DIR = PROJECT_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "config.json"
MODEL_DIR = PROJECT_DIR / "saved_model"
MODEL_PATH = MODEL_DIR / "model.pt"

# AI 환경 설정
# 할당 받은 MLflow tracking server 값을 사용자가 직접 입력합니다.
# 비밀번호 값은 출력하지 않습니다.
mlflow_tracking_uri = ""
mlflow_tracking_username = ""
mlflow_tracking_password = ""
mlflow_experiment_name = "pytorch_sample"
mlflow_register_model_name = "pytorch_sample_model"


class TinyTorchModel(nn.Module):
    def __init__(self, input_dim: int = 4, output_dim: int = 2):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, inputs):
        return self.linear(inputs)


def is_local_tracking_uri() -> bool:
    value = str(mlflow_tracking_uri).strip().lower()
    return value.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0"))


def missing_mlflow_settings() -> list[str]:
    required = {"mlflow_tracking_uri": mlflow_tracking_uri}
    if not is_local_tracking_uri():
        required["mlflow_tracking_username"] = mlflow_tracking_username
        required["mlflow_tracking_password"] = mlflow_tracking_password
    return [name for name, value in required.items() if not value]


def export_mlflow_environment() -> None:
    exports = {
        "MLFLOW_TRACKING_URI": mlflow_tracking_uri,
        "MLFLOW_TRACKING_USERNAME": mlflow_tracking_username,
        "MLFLOW_TRACKING_PASSWORD": mlflow_tracking_password,
        "MLFLOW_EXPERIMENT_NAME": mlflow_experiment_name,
        "MLFLOW_REGISTER_MODEL_NAME": mlflow_register_model_name,
    }
    for name, value in exports.items():
        if value:
            os.environ[name] = value


def mlflow_ui_urls(experiment_id: str, run_id: str | None = None) -> dict[str, str]:
    base_url = str(mlflow_tracking_uri).strip().rstrip("/")
    urls = {
        "tracking_uri": base_url,
        "experiment_url": f"{base_url}/#/experiments/{experiment_id}",
        "experiment_models_url": f"{base_url}/#/experiments/{experiment_id}/models",
        "traces_url": f"{base_url}/#/experiments/{experiment_id}/traces?startTime=ALL",
    }
    if run_id:
        urls["run_url"] = f"{base_url}/#/experiments/{experiment_id}/runs/{run_id}"
    if mlflow_register_model_name:
        model_name = quote(mlflow_register_model_name, safe="")
        urls["registered_model_url"] = f"{base_url}/#/models/{model_name}"
    return urls


def print_mlflow_ui_urls(experiment_id: str, run_id: str | None = None) -> None:
    urls = mlflow_ui_urls(experiment_id, run_id)
    print("MLflow Tracking URI:", urls["tracking_uri"])
    print("MLflow Experiment URI:", urls["experiment_url"])
    print("MLflow Experiment Models URI:", urls["experiment_models_url"])
    print("MLflow Traces URI:", urls["traces_url"])
    if "run_url" in urls:
        print("MLflow Run URI:", urls["run_url"])
    if "registered_model_url" in urls:
        print("MLflow Registered Model URI:", urls["registered_model_url"])


def ensure_registered_model(model_info) -> str:
    model_name = str(mlflow_register_model_name).strip()
    if not model_name:
        return "skipped: mlflow_register_model_name empty"

    try:
        client = mlflow.tracking.MlflowClient()
        client.get_registered_model(model_name)
        return f"exists: {model_name}"
    except Exception:
        pass

    model_uri = getattr(model_info, "model_uri", "")
    if not model_uri:
        return "failed: model_uri missing"

    try:
        registered = mlflow.register_model(model_uri=model_uri, name=model_name)
        version = getattr(registered, "version", "unknown")
        return f"registered: {model_name}, version={version}"
    except Exception as exc:
        return f"failed: {type(exc).__name__}: {exc}"


def log_aiu_pyfunc_model(input_example):
    log_model_params = inspect.signature(mlflow.pyfunc.log_model).parameters
    log_model_args = {
        "python_model": ModelWrapper(),
        "artifacts": {
            "model": MODEL_PATH.as_posix(),
            "config": CONFIG_PATH.as_posix(),
        },
        "input_example": input_example,
        "code_paths": [(Path(__file__).resolve().parent / "aiu_custom").as_posix()],
        "pip_requirements": "requirements.txt",
    }
    if "name" in log_model_params:
        log_model_args["name"] = "ai_studio"
    else:
        log_model_args["artifact_path"] = "ai_studio"
    if "registered_model_name" in log_model_params and mlflow_register_model_name:
        log_model_args["registered_model_name"] = mlflow_register_model_name

    model_info = mlflow.pyfunc.log_model(**log_model_args)
    registry_status = ensure_registered_model(model_info)
    return model_info, registry_status


def prepare_data():
    # 데이터 준비: 외부 데이터셋을 다운로드하지 않는 PyTorch 샘플 tensor
    rng = np.random.default_rng(seed=42)
    train_x = torch.tensor(rng.normal(size=(32, 4)), dtype=torch.float32)
    train_y = (train_x.sum(dim=1) > 0).long()
    test_x = torch.tensor(rng.normal(size=(10, 4)), dtype=torch.float32)
    test_y = (test_x.sum(dim=1) > 0).long()
    return train_x, train_y, test_x, test_y


def train_model(model: nn.Module, train_x: torch.Tensor, train_y: torch.Tensor) -> None:
    # 모델 준비: 간단한 분류 모델을 짧게 학습합니다.
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    model.train()
    for _ in range(5):
        optimizer.zero_grad()
        loss = criterion(model(train_x), train_y)
        loss.backward()
        optimizer.step()


def compute_metrics(model: nn.Module, test_x: torch.Tensor, test_y: torch.Tensor) -> dict[str, float]:
    model.eval()
    with torch.no_grad():
        logits = model(test_x)
        prediction = logits.argmax(dim=1)
        accuracy = (prediction == test_y).float().mean().item()
        loss = nn.CrossEntropyLoss()(logits, test_y).item()
    return {"accuracy": float(accuracy), "loss": float(loss)}


def write_input_example(test_x: torch.Tensor) -> dict:
    # Input example 정의: request 테스트 payload
    sample_data = test_x[:2].detach().cpu().numpy()
    input_example = {
        "inputs": [
            {
                "name": "pytorch_tensor_example",
                "shape": list(sample_data.shape),
                "datatype": str(sample_data.dtype),
                "data": sample_data.tolist(),
            }
        ]
    }
    INPUT_EXAMPLE_PATH.write_text(
        json.dumps(input_example, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return input_example


def main() -> None:
    missing = missing_mlflow_settings()
    if missing:
        print("원격 MLflow 등록 실행을 위해 MLflow/AI Studio 설정을 runtest.py에 직접 입력하세요.")
        print("missing settings:")
        for name in missing:
            print(f"- {name}")
        print("비밀번호 값은 출력하지 않습니다.")
        return

    export_mlflow_environment()
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(mlflow_experiment_name)

    train_x, train_y, test_x, test_y = prepare_data()
    model = TinyTorchModel(input_dim=train_x.shape[1], output_dim=2)
    train_model(model, train_x, train_y)
    metrics = compute_metrics(model, test_x, test_y)
    input_example = write_input_example(test_x)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    config = {"framework": "pytorch", "input_dim": train_x.shape[1], "output_dim": 2}
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=4), encoding="utf-8")
    torch.save(model.state_dict(), MODEL_PATH)

    with mlflow.start_run(run_name=mlflow_register_model_name) as run:
        mlflow.set_tag("data.name", "synthetic_tensor(pytorch)")
        mlflow.log_params(config)
        mlflow.log_metrics(metrics)
        model_info, registry_status = log_aiu_pyfunc_model(input_example)

    print(f"input_example written: {INPUT_EXAMPLE_PATH}")
    print(f"config written: {CONFIG_PATH}")
    print(f"model written: {MODEL_PATH}")
    print("MLflow model logged with artifact_path='ai_studio'")
    print("Model URI:", getattr(model_info, "model_uri", "unknown"))
    print("MLflow Registry:", registry_status)
    print_mlflow_ui_urls(run.info.experiment_id, run.info.run_id)


if __name__ == "__main__":
    main()
