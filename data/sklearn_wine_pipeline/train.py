"""sklearn 회귀/분류 — Pipeline(StandardScaler + LogisticRegression).
전처리를 파이프라인으로 묶는 실무 형태. wine 데이터셋 사용.
"""
import joblib
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

def main():
    X, y = load_wine(return_X_y=True)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=0)

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    pipe.fit(X_tr, y_tr)
    print(f"score: {pipe.score(X_te, y_te):.3f}")

    joblib.dump(pipe, "pipeline.joblib")
    print("saved: pipeline.joblib")

if __name__ == "__main__":
    main()
