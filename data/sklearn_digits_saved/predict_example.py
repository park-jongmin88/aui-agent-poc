"""저장된 모델(svm_model.pkl) 로드 후 추론 예시."""
import pickle
from sklearn.datasets import load_digits

with open("svm_model.pkl", "rb") as f:
    model = pickle.load(f)

X, y = load_digits(return_X_y=True)
pred = model.predict(X[:5])
print("예측:", pred)
print("실제:", y[:5])
