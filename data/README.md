# data/

ML 학습용 샘플 데이터/코드 모음. 각 폴더는 하나의 모델 프로젝트입니다.
Ai Studio 에이전트는 이 폴더 안의 프로젝트를 분석해 MLflow 등록까지 진행합니다.

## 구성 (프레임워크 × 3형태)

### scikit-learn
- `sklearn_iris_clf/`        내장 iris + RandomForest 학습 스크립트 → model.joblib
- `sklearn_wine_pipeline/`   Pipeline(StandardScaler+LogisticRegression) 형태
- `sklearn_digits_saved/`    학습된 모델 파일(svm_model.pkl)만 있는 케이스

### PyTorch
- `pytorch_mlp_clf/`             nn.Module + 학습 루프 → model.pt
- `pytorch_cnn_saved/`           모델 구조(model.py) + 학습된 가중치(cnn_weights.pth)
- `pytorch_regression_dataset/`  커스텀 Dataset/DataLoader 패턴

### TensorFlow / Keras
- `tensorflow_mnist_seq/`       Sequential + 내장 MNIST → model.keras
- `tensorflow_fashion_saved/`   학습된 .h5 모델 파일만 있는 케이스
- `tensorflow_functional_api/`  함수형 API(tf.keras.Model) 구성

## 형태 다양성
- **학습 스크립트형**: iris, wine, mlp, regression, mnist, functional
- **저장 모델형**: digits(.pkl), cnn(.pth), fashion(.h5)
- 각 폴더에 requirements.txt 포함
