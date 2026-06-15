# MLflow 핵심 API 요약

> aiu-agent에서 run.py 작성 및 MLflow 연동 시 참고하는 핵심 API 정리.

---

## 1. 연결 설정

```python
import mlflow
import os

# 서버 주소 설정
mlflow.set_tracking_uri("http://your-mlflow:5000")

# 인증 (서버에 계정이 있을 때)
os.environ["MLFLOW_TRACKING_USERNAME"] = "username"
os.environ["MLFLOW_TRACKING_PASSWORD"] = "password"

# 실험 설정 (없으면 자동 생성)
mlflow.set_experiment("my-experiment")
```

---

## 2. Run 시작/종료

```python
# with 블록 (권장 — 자동 종료)
with mlflow.start_run() as run:
    print(run.info.run_id)  # run ID 확인
    # ... 학습 코드

# 수동 방식
mlflow.start_run(run_name="optional-name")
# ... 학습 코드
mlflow.end_run()
```

---

## 3. 파라미터 / 메트릭 로깅

```python
# 파라미터 (학습 전 설정값)
mlflow.log_param("n_estimators", 100)
mlflow.log_params({"lr": 0.01, "batch_size": 32})  # 여러 개 한번에

# 메트릭 (학습 결과)
mlflow.log_metric("accuracy", 0.95)
mlflow.log_metric("loss", 0.05, step=10)  # step 지정 가능
mlflow.log_metrics({"accuracy": 0.95, "f1": 0.93})

# 태그
mlflow.set_tag("model_type", "RandomForest")
mlflow.set_tags({"env": "dev", "version": "1.0"})
```

---

## 4. 모델 로깅 (프레임워크별)

### sklearn
```python
import mlflow.sklearn

mlflow.sklearn.log_model(
    sk_model=model,
    artifact_path="model",
    registered_model_name="my-model",   # Model Registry 등록명
    input_example=X_train[:5],          # 자동 signature 추론
)
```

### PyTorch
```python
import mlflow.pytorch

mlflow.pytorch.log_model(
    pytorch_model=model,
    artifact_path="model",
    registered_model_name="my-pytorch-model",
    input_example=sample_tensor,
)
```

### TensorFlow / Keras
```python
import mlflow.tensorflow

mlflow.tensorflow.log_model(
    model=model,
    artifact_path="model",
    registered_model_name="my-tf-model",
    input_example=X_train[:5],
)
```

### pyfunc (범용 — 프레임워크 무관)
```python
import mlflow.pyfunc

mlflow.pyfunc.log_model(
    artifact_path="model",
    python_model=MyCustomModel(),  # mlflow.pyfunc.PythonModel 상속
    registered_model_name="my-custom-model",
)
```

---

## 5. Signature (입출력 스키마)

```python
from mlflow.models import infer_signature

# 자동 추론 (권장)
signature = infer_signature(X_train, model.predict(X_train))

mlflow.sklearn.log_model(
    model,
    artifact_path="model",
    signature=signature,
    input_example=X_train[:5],
)
```

---

## 6. 아티팩트 저장

```python
# 파일 저장
mlflow.log_artifact("model_report.txt")
mlflow.log_artifact("confusion_matrix.png", artifact_path="plots")

# 딕셔너리를 JSON으로 저장
mlflow.log_dict({"config": {"lr": 0.01}}, "config.json")

# 텍스트 저장
mlflow.log_text("학습 완료", "notes.txt")
```

---

## 7. 모델 로드 (추론용)

```python
import mlflow.pyfunc
import mlflow.sklearn

# Model Registry에서 로드 (버전 지정)
model = mlflow.pyfunc.load_model("models:/my-model/1")
model = mlflow.pyfunc.load_model("models:/my-model/latest")

# run_id로 직접 로드
model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")

# 추론
predictions = model.predict(X_test)
```

---

## 8. run.py 전체 패턴 (aiu-agent 표준)

```python
import os
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature

# 설정
mlflow.set_tracking_uri("http://your-mlflow:5000")
mlflow.set_experiment("my-experiment")
MODEL_NAME = "my-sklearn-model"

if __name__ == "__main__":
    with mlflow.start_run() as run:
        # 데이터
        X_train, X_test, y_train, y_test = prepare_data()

        # 파라미터 로깅
        params = {"n_estimators": 100, "max_depth": 5}
        mlflow.log_params(params)

        # 학습
        model = build_model(**params)
        model.fit(X_train, y_train)

        # 메트릭 로깅
        acc = accuracy_score(y_test, model.predict(X_test))
        mlflow.log_metric("accuracy", acc)

        # 모델 등록
        signature = infer_signature(X_train, model.predict(X_train))
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
            signature=signature,
            input_example=X_train[:5],
        )

        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME} accuracy={acc:.4f}")
```

---

## 9. 주요 에러 및 해결

| 에러 | 원인 | 해결 |
|---|---|---|
| `INVALID_PARAMETER_VALUE` | 실험명 중복 또는 잘못된 이름 | `mlflow.set_experiment()` 재확인 |
| `Connection refused` | MLflow 서버 주소 오류 | `tracking_uri` 확인 |
| `RestException: PERMISSION_DENIED` | 인증 실패 | `MLFLOW_TRACKING_USERNAME/PASSWORD` 확인 |
| `MlflowException: Registered Model not found` | Model Registry에 모델 없음 | `registered_model_name` 최초 등록 시 자동 생성 |
| `ValueError: input_example` 타입 오류 | numpy → pandas 변환 필요 | `pd.DataFrame(X_train[:5])` 로 변환 |
