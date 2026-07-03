import os
import io
import json
import sys
import logging
from pathlib import Path


def configure_utf8_stdio() -> None:
    if os.name != "nt":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
        elif hasattr(stream, "buffer"):
            setattr(sys, stream_name, io.TextIOWrapper(stream.buffer, encoding="utf-8"))


def quiet_mlflow_logging() -> None:
    for logger_name in ("mlflow", "mlflow.tracking", "mlflow.tracking.fluent"):
        logging.getLogger(logger_name).setLevel(logging.ERROR)


configure_utf8_stdio()
quiet_mlflow_logging()

PROJECT_DIR = Path(__file__).resolve().parent
AI_STUDIO_DIR = PROJECT_DIR / "ai_studio"
AI_STUDIO_CODE_DIR = AI_STUDIO_DIR / "code"
AI_STUDIO_METRICS_DIR = AI_STUDIO_DIR / "metrics"
AI_STUDIO_TRACKING_DIR = AI_STUDIO_DIR / "tracking"

# MLflow/AI Studio settings
# 사용자가 아래 값을 직접 입력합니다. 비밀번호 값은 출력하지 마세요.
mlflow_tracking_uri = ""
mlflow_tracking_username = ""
mlflow_tracking_password = ""
mlflow_experiment_name = "pytorch_sample"
mlflow_register_model_name = "pytorch_sample_model"


def missing_mlflow_settings() -> list[str]:
    required = {
        "mlflow_tracking_uri": mlflow_tracking_uri,
        "mlflow_tracking_username": mlflow_tracking_username,
        "mlflow_tracking_password": mlflow_tracking_password,
    }
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


def write_visible_outputs() -> Path:
    AI_STUDIO_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    AI_STUDIO_CODE_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {
        "sample_accuracy": 0.97,
        "sample_loss": 0.03,
    }
    for name, value in metrics.items():
        (AI_STUDIO_METRICS_DIR / name).write_text(f"{value}\n", encoding="utf-8")
    summary_path = AI_STUDIO_CODE_DIR / "training_summary.json"
    summary_text = json.dumps(
        {
            "sample": "pytorch",
            "status": "completed",
            "metrics": metrics,
            "artifact": "training_summary.json",
        },
        ensure_ascii=False,
        indent=2,
    )
    summary_path.write_text(summary_text, encoding="utf-8")
    return summary_path


def log_mlflow_outputs(summary_path: Path) -> None:
    try:
        import mlflow
    except Exception as exc:
        print(f"MLflow import failed; local ai_studio outputs were created. reason={exc}")
        return

    quiet_mlflow_logging()
    try:
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment(mlflow_experiment_name)
        with mlflow.start_run(run_name="pytorch_sample_local_training"):
            mlflow.log_param("sample", "pytorch")
            mlflow.log_metric("sample_accuracy", 0.97)
            mlflow.log_metric("sample_loss", 0.03)
            mlflow.log_artifact(str(summary_path), artifact_path="ai_studio/code")
            active_run = mlflow.active_run()
            print(f"MLflow run created: {active_run.info.run_id if active_run else 'unknown'}")
    except Exception as exc:
        print(f"MLflow logging failed; local ai_studio outputs were created. reason={exc}")


def main() -> None:
    missing = missing_mlflow_settings()
    if missing:
        print("MLflow/AI Studio 설정을 run_model.py에 직접 입력하세요.")
        print("missing settings:")
        for name in missing:
            print(f"- {name}")
        print("비밀번호 값은 출력하지 않습니다.")
    export_mlflow_environment()

    summary_path = write_visible_outputs()
    log_mlflow_outputs(summary_path)
    print(f"metrics written: {AI_STUDIO_METRICS_DIR}")
    print(f"code artifacts written: {AI_STUDIO_CODE_DIR}")


if __name__ == "__main__":
    main()
