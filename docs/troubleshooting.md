# 트러블슈팅 가이드

> aiu-agent 및 MLflow 사용 중 자주 발생하는 문제와 해결 방법.

---

## 1. aiu-agent 관련

### run.py 생성 후 validate 실패

| 증상 | 원인 | 해결 |
|---|---|---|
| `TODO 미입력 N개` | init이 생성한 TODO 주석 미수정 | 해당 라인 직접 수정 후 재검증 |
| `NotImplementedError` | 함수 구현 안 됨 | `raise NotImplementedError` 제거 후 구현 |
| `섹션 N 누락` | 섹션 헤더 형식 오류 | `# N. 섹션명` 형식 확인 |
| `MLflow 주소 미설정` | `MLFLOW_TRACKING_URI` 비어있음 | config.json 또는 run.py 섹션 2 수정 |

### train 실행 중 오류

```
# MLflow 서버 연결 실패
MlflowException: Failed to connect to MLflow server
→ MLFLOW_TRACKING_URI 확인, 서버 상태 확인

# 실험명 없음
MlflowException: Experiment not found
→ mlflow.set_experiment() 실행 여부 확인, 서버에서 실험 생성

# 모델 등록 실패
MlflowException: RESOURCE_ALREADY_EXISTS
→ registered_model_name 이미 다른 타입으로 등록됨, 이름 변경

# 인증 오류
RestException: PERMISSION_DENIED
→ MLFLOW_TRACKING_USERNAME / PASSWORD 환경변수 확인
```

### predict 실패

```
# 모델 없음
MlflowException: Registered Model not found
→ train이 완료됐는지 확인, Model Registry에서 모델명 확인

# 버전 없음
MlflowException: No versions found for model
→ train 시 registered_model_name 확인

# input shape 불일치
ValueError: Input shape mismatch
→ 학습 시와 동일한 전처리(스케일링 등) 적용 여부 확인
   scaler를 MLflow artifact로 같이 저장했는지 확인
```

---

## 2. sklearn 관련

```python
# 오류: fit 전에 predict 호출
NotFittedError: This model is not fitted yet
→ model.fit(X_train, y_train) 먼저 실행

# 오류: 입력 shape 불일치
ValueError: X has 5 features but model expects 10
→ 학습 때와 동일한 피처 수, 동일한 전처리 확인

# 오류: 레이블 타입 불일치
ValueError: Unknown label type: continuous
→ 분류 모델에 연속형 y 전달. y를 정수로 변환
   y = y.astype(int)

# 경고: 수렴 안됨
ConvergenceWarning: Solver did not converge
→ max_iter 증가: LogisticRegression(max_iter=1000)
   또는 스케일링 적용
```

---

## 3. PyTorch 관련

```python
# 오류: GPU/CPU 불일치
RuntimeError: Expected all tensors to be on the same device
→ model과 데이터를 같은 device로
   X = X.to(device); model = model.to(device)

# 오류: 차원 불일치
RuntimeError: mat1 and mat2 shapes cannot be multiplied
→ Linear 레이어 입력 차원 확인
   print(X.shape)로 확인 후 input_dim 수정

# 오류: 그라디언트 누적
→ optimizer.zero_grad()를 루프 시작 시 호출하는지 확인

# NaN loss 발생
→ 학습률이 너무 큼 (lr 0.001 → 0.0001로 낮추기)
→ 입력 데이터 정규화 여부 확인
→ gradient clipping 추가:
   torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

# 모델 로드 시 키 불일치
RuntimeError: Missing key(s) in state_dict
→ 모델 클래스 구조가 저장 시와 다름. 동일한 클래스 정의 사용
```

---

## 4. TensorFlow/Keras 관련

```python
# 오류: shape 불일치
ValueError: Input 0 is incompatible with layer
→ input_shape 확인: input_shape=(feature_count,)

# 오류: 손실함수 선택
- 이진 분류: binary_crossentropy, 마지막 sigmoid
- 다중 분류 (정수 레이블): sparse_categorical_crossentropy, 마지막 softmax
- 다중 분류 (원핫 레이블): categorical_crossentropy, 마지막 softmax
- 회귀: mse 또는 mae, 마지막 linear (activation 없음)

# 과적합 발생
→ Dropout 추가: keras.layers.Dropout(0.3)
→ L2 정규화: kernel_regularizer=keras.regularizers.l2(0.01)
→ EarlyStopping 추가

# GPU 메모리 부족
→ batch_size 줄이기
→ model.predict(X, batch_size=32)로 나눠서 추론
```

---

## 5. 데이터 관련

```python
# 결측치 있을 때 학습 오류
ValueError: Input contains NaN
→ df.isnull().sum()으로 확인 후 fillna() 또는 dropna()

# 범주형 데이터 그대로 넣었을 때
ValueError: could not convert string to float
→ LabelEncoder 또는 pd.get_dummies() 적용

# 클래스 불균형
→ 평가 지표를 accuracy 대신 f1, roc_auc 사용
→ class_weight="balanced" 옵션 사용
→ SMOTE 오버샘플링

# 데이터 스케일 차이가 클 때 (모델 성능 저하)
→ StandardScaler 또는 MinMaxScaler 적용
→ fit은 train에만, transform은 train/test 모두
```
