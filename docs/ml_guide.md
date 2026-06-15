# ML 모델러 실전 가이드

> aiu-agent에서 run.py 작성 시 참고하는 머신러닝 핵심 패턴 모음.
> 문제 유형 → 모델 선택 → 코드 패턴 순서로 구성.

---

## 1. 문제 유형별 모델 선택 가이드

| 문제 유형 | 데이터 특성 | 추천 모델 |
|---|---|---|
| 이진 분류 | 소규모, 해석 필요 | LogisticRegression, DecisionTree |
| 이진 분류 | 중규모, 성능 우선 | RandomForest, GradientBoosting, XGBoost |
| 다중 분류 | 일반 | RandomForest, SVM |
| 회귀 | 선형 관계 | LinearRegression, Ridge, Lasso |
| 회귀 | 비선형 | RandomForest, GradientBoosting |
| 클러스터링 | 군집 수 알 때 | KMeans |
| 클러스터링 | 군집 수 모를 때 | DBSCAN |
| 이미지 분류 | CNN 필요 | PyTorch / TensorFlow |
| 시계열 | 순서 있는 데이터 | LSTM, Transformer |
| 텍스트 분류 | NLP | HuggingFace + fine-tuning |

---

## 2. 데이터 처리 (pandas / numpy)

### 기본 로드 및 탐색
```python
import pandas as pd
import numpy as np

df = pd.read_csv("data.csv")
print(df.shape)           # (행, 열)
print(df.dtypes)          # 컬럼 타입
print(df.describe())      # 통계 요약
print(df.isnull().sum())  # 결측치 확인
```

### 결측치 처리
```python
# 제거
df = df.dropna()

# 평균/중앙값으로 채우기
df["col"].fillna(df["col"].mean(), inplace=True)
df["col"].fillna(df["col"].median(), inplace=True)

# 최빈값으로 채우기 (범주형)
df["col"].fillna(df["col"].mode()[0], inplace=True)
```

### 인코딩
```python
from sklearn.preprocessing import LabelEncoder, OneHotEncoder

# Label Encoding (순서 있는 범주형)
le = LabelEncoder()
df["col_encoded"] = le.fit_transform(df["col"])

# One-Hot Encoding
df = pd.get_dummies(df, columns=["col"], drop_first=True)
```

### 스케일링
```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler

scaler = StandardScaler()       # 평균 0, 분산 1
scaler = MinMaxScaler()         # 0~1 범위

X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)  # fit은 train에만
```

### Train/Test 분리
```python
from sklearn.model_selection import train_test_split

X = df.drop(columns=["target"])
y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y,        # 분류 문제 시 비율 유지
)
```

---

## 3. sklearn 핵심 패턴

### 분류 모델
```python
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC

# 기본 사용법 (모두 동일한 인터페이스)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]  # 양성 확률
```

### 회귀 모델
```python
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
```

### 평가 지표
```python
from sklearn.metrics import (
    # 분류
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, classification_report, confusion_matrix,
    # 회귀
    mean_squared_error, mean_absolute_error, r2_score
)

# 분류
print(f"Accuracy : {accuracy_score(y_test, y_pred):.4f}")
print(f"F1 Score : {f1_score(y_test, y_pred, average='weighted'):.4f}")
print(f"AUC-ROC  : {roc_auc_score(y_test, y_prob):.4f}")
print(classification_report(y_test, y_pred))

# 회귀
mse  = mean_squared_error(y_test, y_pred)
rmse = mse ** 0.5
mae  = mean_absolute_error(y_test, y_pred)
r2   = r2_score(y_test, y_pred)
print(f"RMSE: {rmse:.4f}  MAE: {mae:.4f}  R2: {r2:.4f}")
```

### 교차검증
```python
from sklearn.model_selection import cross_val_score, StratifiedKFold

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
print(f"CV Accuracy: {scores.mean():.4f} ± {scores.std():.4f}")
```

### 하이퍼파라미터 튜닝
```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

param_grid = {
    "n_estimators": [50, 100, 200],
    "max_depth": [None, 5, 10],
    "min_samples_split": [2, 5],
}

# Grid Search (전수 탐색)
gs = GridSearchCV(RandomForestClassifier(), param_grid, cv=5, scoring="f1", n_jobs=-1)
gs.fit(X_train, y_train)
print(gs.best_params_, gs.best_score_)
best_model = gs.best_estimator_

# Random Search (빠른 탐색)
rs = RandomizedSearchCV(
    RandomForestClassifier(), param_grid,
    n_iter=20, cv=5, scoring="f1", random_state=42, n_jobs=-1
)
rs.fit(X_train, y_train)
```

### 모델 저장/로드
```python
import joblib

joblib.dump(model, "model.pkl")
model = joblib.load("model.pkl")
```

---

## 4. PyTorch 핵심 패턴

### 모델 정의
```python
import torch
import torch.nn as nn
import torch.optim as optim

class MyModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x):
        return self.network(x)

model = MyModel(input_dim=10, hidden_dim=64, output_dim=2)
```

### Dataset / DataLoader
```python
from torch.utils.data import Dataset, DataLoader
import torch

class MyDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.LongTensor(y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

train_loader = DataLoader(MyDataset(X_train, y_train), batch_size=32, shuffle=True)
test_loader  = DataLoader(MyDataset(X_test, y_test),  batch_size=32, shuffle=False)
```

### 학습 루프
```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

for epoch in range(50):
    model.train()
    total_loss = 0
    for X_batch, y_batch in train_loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        output = model(X_batch)
        loss = criterion(output, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    avg_loss = total_loss / len(train_loader)
    print(f"Epoch {epoch+1:3d} | Loss: {avg_loss:.4f}")
```

### 평가
```python
model.eval()
all_preds, all_labels = [], []

with torch.no_grad():
    for X_batch, y_batch in test_loader:
        X_batch = X_batch.to(device)
        output = model(X_batch)
        preds = output.argmax(dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(y_batch.numpy())

from sklearn.metrics import accuracy_score
acc = accuracy_score(all_labels, all_preds)
print(f"Test Accuracy: {acc:.4f}")
```

### 저장/로드
```python
# 저장
torch.save(model.state_dict(), "model.pt")

# 로드
model = MyModel(input_dim=10, hidden_dim=64, output_dim=2)
model.load_state_dict(torch.load("model.pt"))
model.eval()
```

---

## 5. TensorFlow / Keras 핵심 패턴

### 모델 정의
```python
import tensorflow as tf
from tensorflow import keras

# Sequential API (단순한 구조)
model = keras.Sequential([
    keras.layers.Dense(64, activation="relu", input_shape=(10,)),
    keras.layers.Dropout(0.3),
    keras.layers.Dense(64, activation="relu"),
    keras.layers.Dense(2, activation="softmax"),  # 분류
])

# Functional API (복잡한 구조)
inputs = keras.Input(shape=(10,))
x = keras.layers.Dense(64, activation="relu")(inputs)
x = keras.layers.Dropout(0.3)(x)
outputs = keras.layers.Dense(2, activation="softmax")(x)
model = keras.Model(inputs, outputs)
```

### 컴파일 & 학습
```python
model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",  # 정수 레이블
    metrics=["accuracy"],
)

history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=32,
    validation_split=0.2,
    callbacks=[
        keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(patience=3, factor=0.5),
    ],
    verbose=1,
)
```

### 평가 & 예측
```python
loss, acc = model.evaluate(X_test, y_test, verbose=0)
print(f"Test Accuracy: {acc:.4f}")

y_pred_prob = model.predict(X_test)
y_pred = y_pred_prob.argmax(axis=1)
```

### 저장/로드
```python
# 전체 모델 저장 (권장)
model.save("model.h5")
model = keras.models.load_model("model.h5")

# SavedModel 형식
model.save("saved_model/")
model = keras.models.load_model("saved_model/")
```

---

## 6. run.py 프레임워크별 MLflow 연동 전체 예시

### sklearn + MLflow
```python
with mlflow.start_run() as run:
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    mlflow.log_params({"n_estimators": 100})
    mlflow.log_metric("accuracy", acc)

    signature = infer_signature(X_train, model.predict(X_train))
    mlflow.sklearn.log_model(model, "model",
        registered_model_name=MODEL_NAME, signature=signature,
        input_example=X_train[:5])
    print(f"[AIU] run_id={run.info.run_id} accuracy={acc:.4f}")
```

### PyTorch + MLflow
```python
with mlflow.start_run() as run:
    # 학습 루프 실행
    for epoch in range(50):
        train(model, train_loader, optimizer, criterion)
        acc = evaluate(model, test_loader)
        mlflow.log_metric("accuracy", acc, step=epoch)

    sample = torch.FloatTensor(X_train[:5])
    mlflow.pytorch.log_model(model, "model",
        registered_model_name=MODEL_NAME,
        input_example=sample.numpy())
    print(f"[AIU] run_id={run.info.run_id}")
```

### TensorFlow + MLflow
```python
with mlflow.start_run() as run:
    history = model.fit(X_train, y_train, epochs=50, validation_split=0.2)

    for epoch, (loss, acc) in enumerate(zip(
        history.history["val_loss"], history.history["val_accuracy"]
    )):
        mlflow.log_metrics({"val_loss": loss, "val_accuracy": acc}, step=epoch)

    mlflow.tensorflow.log_model(model, "model",
        registered_model_name=MODEL_NAME,
        input_example=X_train[:5])
    print(f"[AIU] run_id={run.info.run_id}")
```

---

## 7. 자주 쓰는 패턴 모음

### Feature Importance (sklearn)
```python
import pandas as pd
fi = pd.Series(model.feature_importances_, index=feature_names)
fi.sort_values(ascending=False).head(10)
```

### 불균형 데이터 처리
```python
# class_weight 자동 조정
model = RandomForestClassifier(class_weight="balanced")

# SMOTE 오버샘플링
from imblearn.over_sampling import SMOTE
X_res, y_res = SMOTE(random_state=42).fit_resample(X_train, y_train)
```

### Pipeline (전처리 + 모델 묶기)
```python
from sklearn.pipeline import Pipeline

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("model",  RandomForestClassifier(n_estimators=100)),
])
pipe.fit(X_train, y_train)
y_pred = pipe.predict(X_test)

# Pipeline도 MLflow에 그대로 저장 가능
mlflow.sklearn.log_model(pipe, "model", registered_model_name=MODEL_NAME)
```
