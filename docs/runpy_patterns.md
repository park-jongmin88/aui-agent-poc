# 데이터 타입별 run.py 패턴

> 표 데이터 / 이미지 / 텍스트 / 시계열 각각의 run.py 완성 패턴.
> 각 패턴을 그대로 섹션 3~7에 붙여넣기 가능.

---

## 1. 표 데이터 (Tabular) — sklearn

```python
# ── 섹션 1: 임포트 ──────────────────────────────────────────
import os, json
from pathlib import Path
import mlflow, mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline
from mlflow.models import infer_signature

# ── 섹션 3: 데이터 준비 ─────────────────────────────────────
def prepare_data():
    data_path = Path(__file__).parent / "source" / "data.csv"
    df = pd.read_csv(data_path)
    df = df.dropna()                          # 결측치 제거
    target_col = "target"                     # TODO: 실제 타겟 컬럼명
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# ── 섹션 4: 모델 준비 ───────────────────────────────────────
def build_model():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(n_estimators=100, random_state=42)),
    ])

# ── 섹션 5: 학습 ────────────────────────────────────────────
def train(model, X_train, y_train):
    model.fit(X_train, y_train)
    y_pred = model.predict(X_train)
    mlflow.log_metric("train_accuracy", accuracy_score(y_train, y_pred))
    mlflow.log_params({"n_estimators": 100, "scaler": "StandardScaler"})
    return model

# ── 섹션 6: 인풋 샘플 ──────────────────────────────────────
def get_input_example(X):
    return X.iloc[:5] if hasattr(X, "iloc") else X[:5]

# ── 섹션 7: MLflow 로깅 ─────────────────────────────────────
def log_model(model, input_example):
    signature = infer_signature(input_example, model.predict(input_example))
    mlflow.sklearn.log_model(
        model, artifact_path="model",
        registered_model_name=MODEL_NAME,
        signature=signature, input_example=input_example,
    )

# ── 섹션 9: 런 스타트 ──────────────────────────────────────
if __name__ == "__main__":
    with mlflow.start_run() as run:
        X_train, X_test, y_train, y_test = prepare_data()
        model = build_model()
        train(model, X_train, y_train)

        y_pred = model.predict(X_test)
        mlflow.log_metrics({
            "test_accuracy": accuracy_score(y_test, y_pred),
            "test_f1":       f1_score(y_test, y_pred, average="weighted"),
        })

        log_model(model, get_input_example(X_train))
        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME}")
```

---

## 2. 이미지 분류 — PyTorch CNN

```python
# ── 섹션 1: 임포트 ──────────────────────────────────────────
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
import mlflow, mlflow.pytorch
from mlflow.models import infer_signature
import numpy as np

# ── 섹션 3: 데이터 준비 ─────────────────────────────────────
class ImageDataset(Dataset):
    def __init__(self, images, labels, transform=None):
        self.images = images        # (N, H, W, C) numpy array
        self.labels = labels
        self.transform = transform or transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225]),
        ])
    def __len__(self): return len(self.images)
    def __getitem__(self, idx):
        img = self.transform(self.images[idx])
        return img, self.labels[idx]

def prepare_data():
    # TODO: 실제 데이터 로드로 교체
    images = np.random.randint(0, 255, (100, 64, 64, 3), dtype=np.uint8)
    labels = np.random.randint(0, 2, 100)
    n = int(len(images) * 0.8)
    train_ds = ImageDataset(images[:n], labels[:n])
    test_ds  = ImageDataset(images[n:], labels[n:])
    return (DataLoader(train_ds, batch_size=16, shuffle=True),
            DataLoader(test_ds,  batch_size=16))

# ── 섹션 4: 모델 준비 ───────────────────────────────────────
def build_model(num_classes=2):
    # TODO: 복잡한 모델은 torchvision.models.resnet18(pretrained=True) 등 사용
    return nn.Sequential(
        nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.AdaptiveAvgPool2d(1), nn.Flatten(),
        nn.Linear(64, num_classes),
    )

# ── 섹션 5: 학습 ────────────────────────────────────────────
def train(model, train_loader, device, epochs=10):
    model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward(); optimizer.step()
            total_loss += loss.item()
        avg = total_loss / len(train_loader)
        mlflow.log_metric("train_loss", avg, step=epoch)
    return model

# ── 섹션 6: 인풋 샘플 ──────────────────────────────────────
def get_input_example(loader):
    imgs, _ = next(iter(loader))
    return imgs[:2].numpy()

# ── 섹션 7: MLflow 로깅 ─────────────────────────────────────
def log_model(model, input_example):
    mlflow.pytorch.log_model(
        model.cpu(), artifact_path="model",
        registered_model_name=MODEL_NAME,
        input_example=input_example,
    )

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mlflow.log_param("device", str(device))
    with mlflow.start_run() as run:
        train_loader, test_loader = prepare_data()
        model = build_model()
        train(model, train_loader, device)
        log_model(model, get_input_example(train_loader))
        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME}")
```

---

## 3. 텍스트 분류 — sklearn TF-IDF

```python
# ── 섹션 1: 임포트 ──────────────────────────────────────────
import mlflow, mlflow.sklearn
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report
from mlflow.models import infer_signature

# ── 섹션 3: 데이터 준비 ─────────────────────────────────────
def prepare_data():
    # TODO: 실제 데이터로 교체
    data_path = Path(__file__).parent / "source" / "texts.csv"
    df = pd.read_csv(data_path)
    # 컬럼명: text, label
    return train_test_split(
        df["text"], df["label"],
        test_size=0.2, random_state=42, stratify=df["label"]
    )

# ── 섹션 4: 모델 준비 ───────────────────────────────────────
def build_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),    # 단어 + 2-gram
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(max_iter=1000, C=1.0)),
    ])

# ── 섹션 5: 학습 ────────────────────────────────────────────
def train(model, X_train, y_train):
    model.fit(X_train, y_train)
    mlflow.log_params({
        "max_features": 10000, "ngram_range": "(1,2)", "C": 1.0
    })
    return model

# ── 섹션 6: 인풋 샘플 ──────────────────────────────────────
def get_input_example(X):
    return X.iloc[:3].tolist()

# ── 섹션 7: MLflow 로깅 ─────────────────────────────────────
def log_model(model, input_example):
    mlflow.sklearn.log_model(
        model, artifact_path="model",
        registered_model_name=MODEL_NAME,
        input_example=input_example,
    )

if __name__ == "__main__":
    with mlflow.start_run() as run:
        X_train, X_test, y_train, y_test = prepare_data()
        model = build_model()
        train(model, X_train, y_train)
        y_pred = model.predict(X_test)
        mlflow.log_metrics({
            "accuracy": accuracy_score(y_test, y_pred),
            "f1":       f1_score(y_test, y_pred, average="weighted"),
        })
        log_model(model, get_input_example(X_train))
        print(classification_report(y_test, y_pred))
        print(f"[AIU] run_id={run.info.run_id} model={MODEL_NAME}")
```

---

## 4. 시계열 예측 — sklearn (Lag Feature 방식)

```python
# ── 섹션 1: 임포트 ──────────────────────────────────────────
import mlflow, mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from mlflow.models import infer_signature

# ── 섹션 3: 데이터 준비 ─────────────────────────────────────
def prepare_data(n_lags=7):
    """시계열 → Lag Feature로 변환."""
    data_path = Path(__file__).parent / "source" / "timeseries.csv"
    df = pd.read_csv(data_path, parse_dates=["date"], index_col="date")
    target = "value"  # TODO: 실제 타겟 컬럼명

    # Lag Feature 생성
    for i in range(1, n_lags + 1):
        df[f"lag_{i}"] = df[target].shift(i)
    df = df.dropna()

    X = df.drop(columns=[target])
    y = df[target]

    # 시간 순서 유지 (shuffle 금지)
    split = int(len(X) * 0.8)
    return X.iloc[:split], X.iloc[split:], y.iloc[:split], y.iloc[split:]

# ── 섹션 4: 모델 준비 ───────────────────────────────────────
def build_model():
    return GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.05,
        max_depth=4, random_state=42
    )

# ── 섹션 5: 학습 ────────────────────────────────────────────
def train(model, X_train, y_train):
    model.fit(X_train, y_train)
    mlflow.log_params({"n_lags": 7, "n_estimators": 200, "lr": 0.05})
    return model

# ── 섹션 6: 인풋 샘플 ──────────────────────────────────────
def get_input_example(X):
    return X.iloc[:3]

# ── 섹션 7: MLflow 로깅 ─────────────────────────────────────
def log_model(model, input_example):
    signature = infer_signature(input_example, model.predict(input_example))
    mlflow.sklearn.log_model(
        model, artifact_path="model",
        registered_model_name=MODEL_NAME,
        signature=signature, input_example=input_example,
    )

if __name__ == "__main__":
    with mlflow.start_run() as run:
        X_train, X_test, y_train, y_test = prepare_data()
        model = build_model()
        train(model, X_train, y_train)
        y_pred = model.predict(X_test)
        rmse = mean_squared_error(y_test, y_pred) ** 0.5
        mlflow.log_metrics({
            "rmse": rmse,
            "mae":  mean_absolute_error(y_test, y_pred),
            "r2":   r2_score(y_test, y_pred),
        })
        log_model(model, get_input_example(X_train))
        print(f"[AIU] run_id={run.info.run_id} RMSE={rmse:.4f}")
```
