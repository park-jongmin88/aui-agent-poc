"""sklearn 분류 — 내장 iris 데이터셋으로 RandomForest 학습 후 저장.
연구자들이 가장 흔히 쓰는 형태: load_dataset → fit → joblib.dump.
"""
import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def main():
    X, y = load_iris(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_tr, y_tr)

    acc = accuracy_score(y_te, model.predict(X_te))
    print(f"accuracy: {acc:.3f}")

    joblib.dump(model, "model.joblib")
    print("saved: model.joblib")

if __name__ == "__main__":
    main()
