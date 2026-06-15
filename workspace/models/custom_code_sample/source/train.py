"""
SVM 분류 모델 학습 코드
로컬에서 개발/테스트 완료된 코드입니다.
"""
from sklearn.svm import SVC
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler
import numpy as np


def prepare_data(n_samples=500, n_features=6, random_state=42):
    """분류 데이터 생성."""
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=4,
        random_state=random_state
    )
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    return train_test_split(X, y, test_size=0.2, random_state=random_state)


def build_model(kernel="rbf", C=1.0, gamma="scale"):
    """SVM 모델 정의."""
    return SVC(kernel=kernel, C=C, gamma=gamma, probability=True)


def train_model(model, X_train, y_train):
    """모델 학습."""
    model.fit(X_train, y_train)
    return model


def evaluate(model, X_test, y_test):
    """모델 평가."""
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred))
    return acc


if __name__ == "__main__":
    X_train, X_test, y_train, y_test = prepare_data()
    model = build_model()
    model = train_model(model, X_train, y_train)
    acc = evaluate(model, X_test, y_test)
    print(f"[DONE] accuracy={acc:.4f}")
