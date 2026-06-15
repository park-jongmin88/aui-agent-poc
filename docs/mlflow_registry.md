# MLflow Model Registry & 실험 관리

> 모델 등록, 버전 관리, 실험 조회 핵심 정리.

---

## 1. Model Registry 개념

```
실험(Experiment)
  └── Run (run_id)
        └── 아티팩트 (model/)
                        ↓ 등록
         Model Registry
           └── 모델명 (registered_model_name)
                 └── Version 1, 2, 3 ...
                       └── Stage: None → Staging → Production → Archived
```

- **Experiment**: 같은 목적의 Run들을 묶는 단위
- **Run**: 한 번의 학습 실행 (run_id로 식별)
- **Model Registry**: 등록된 모델의 버전 관리소
- **Stage**: 모델 상태 (None / Staging / Production / Archived)

---

## 2. 모델 등록 방법

### 방법 1: log_model 시 등록 (권장)
```python
mlflow.sklearn.log_model(
    model,
    artifact_path="model",
    registered_model_name="my-model",  # 없으면 자동 생성, 있으면 새 버전 추가
)
```

### 방법 2: run 완료 후 등록
```python
result = mlflow.register_model(
    model_uri=f"runs:/{run_id}/model",
    name="my-model",
)
print(f"Version: {result.version}")
```

### 방법 3: 기존 pkl 파일 등록
```python
import joblib
from mlflow.models import infer_signature

model = joblib.load("model.pkl")
signature = infer_signature(X_sample, model.predict(X_sample))

with mlflow.start_run():
    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name="my-pretrained-model",
        signature=signature,
        input_example=X_sample[:5],
    )
```

---

## 3. 버전 관리 (MlflowClient)

```python
from mlflow import MlflowClient
client = MlflowClient()

# 모든 버전 조회
versions = client.search_model_versions("name='my-model'")
for v in versions:
    print(f"Version {v.version} — Stage: {v.current_stage} — run_id: {v.run_id}")

# 특정 버전 정보
v = client.get_model_version("my-model", "1")
print(v.current_stage, v.status)

# Stage 변경
client.transition_model_version_stage(
    name="my-model",
    version="2",
    stage="Production",   # None / Staging / Production / Archived
)

# 최신 버전 조회
latest = client.get_latest_versions("my-model", stages=["Production"])
```

---

## 4. 실험 조회 및 Run 검색

```python
from mlflow import MlflowClient
client = MlflowClient()

# 실험 목록
experiments = client.search_experiments()
for e in experiments:
    print(e.experiment_id, e.name)

# Run 검색 (메트릭 기준 정렬)
runs = mlflow.search_runs(
    experiment_names=["my-experiment"],
    filter_string="metrics.accuracy > 0.9",
    order_by=["metrics.accuracy DESC"],
    max_results=10,
)
# runs는 pandas DataFrame

# 특정 run 정보
run = client.get_run(run_id)
print(run.data.params)    # 파라미터
print(run.data.metrics)   # 메트릭
print(run.info.status)    # FINISHED / FAILED / RUNNING
```

---

## 5. 모델 로드 (URI 패턴)

```python
import mlflow.pyfunc

# Model Registry — 버전 지정
model = mlflow.pyfunc.load_model("models:/my-model/1")

# Model Registry — Stage 지정
model = mlflow.pyfunc.load_model("models:/my-model/Production")
model = mlflow.pyfunc.load_model("models:/my-model/latest")

# Run artifact에서 직접
model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")
```

---

## 6. aiu-agent 실험명·모델명 규칙 (권장)

```
실험명(EXPERIMENT_NAME):  {프로젝트}-{목적}
  예) sklearn-classification, pytorch-image-clf

모델명(MODEL_NAME):       {실험명}-model
  예) sklearn-classification-model, pytorch-image-clf-model
```

- 실험명과 모델명은 **독립적** — 같은 모델명으로 여러 실험에서 등록 가능
- 동일 모델명으로 등록할 때마다 버전이 자동 증가 (v1 → v2 → v3)
- `.aiu_state.json`에 `experiment_name`, `model_name`, `last_run_id` 저장됨

---

## 7. 환경변수 방식 (선택)

```bash
# 서버 주소
export MLFLOW_TRACKING_URI=http://your-mlflow:5000

# 인증
export MLFLOW_TRACKING_USERNAME=user
export MLFLOW_TRACKING_PASSWORD=pass

# 실험명 (코드에서 set_experiment() 안 써도 됨)
export MLFLOW_EXPERIMENT_NAME=my-experiment
```

Python에서:
```python
os.environ["MLFLOW_TRACKING_URI"] = "http://your-mlflow:5000"
os.environ["MLFLOW_TRACKING_USERNAME"] = "user"
os.environ["MLFLOW_TRACKING_PASSWORD"] = "pass"
```
