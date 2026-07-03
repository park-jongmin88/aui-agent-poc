from __future__ import annotations

import json
from pathlib import Path

import mlflow.pyfunc
import torch
from torch import nn


def _normalize_path(path):
    value = str(path).replace("\\", "/").replace("＼", "/").replace("￦", "/").replace("₩", "/")
    while "//" in value and not value.startswith("//"):
        value = value.replace("//", "/")
    return value


class TinyTorchModel(nn.Module):
    def __init__(self, input_dim: int = 4, output_dim: int = 2):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, inputs):
        return self.linear(inputs)


def _payload_to_tensor(payload) -> torch.Tensor:
    if isinstance(payload, dict):
        if "inputs" in payload and payload["inputs"]:
            first_input = payload["inputs"][0]
            if isinstance(first_input, dict) and "data" in first_input:
                return torch.tensor(first_input["data"], dtype=torch.float32)
        for key in ("data", "instances", "features", "x"):
            if key in payload:
                return torch.tensor(payload[key], dtype=torch.float32)
    return torch.tensor(payload, dtype=torch.float32)


class ModelWrapper(mlflow.pyfunc.PythonModel):
    def load_context(self, context):
        config_path = Path(_normalize_path(context.artifacts["config"]))
        model_path = Path(_normalize_path(context.artifacts["model"]))
        config = json.loads(config_path.read_text(encoding="utf-8"))

        self.model = TinyTorchModel(
            input_dim=int(config.get("input_dim", 4)),
            output_dim=int(config.get("output_dim", 2)),
        )
        state_dict = torch.load(model_path, map_location="cpu")
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def predict(self, context, model_input, params=None):
        if not hasattr(self, "model"):
            return {
                "status": "model_not_loaded",
                "detail": "MLflow calls load_context() before predict().",
                "input": model_input,
            }
        tensor_input = _payload_to_tensor(model_input)
        with torch.no_grad():
            logits = self.model(tensor_input)
            probabilities = torch.softmax(logits, dim=1)
            prediction = probabilities.argmax(dim=1)
        return {
            "prediction": prediction.cpu().tolist(),
            "probabilities": probabilities.cpu().tolist(),
        }


def predict(payload):
    wrapper = ModelWrapper()
    return wrapper.predict(None, payload)
