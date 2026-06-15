# tensorflow_sample

## 타입
**TEMPLATE** — TensorFlow/Keras 학습 시작용 샘플

## 설명
TensorFlow/Keras 기반 모델을 MLflow에 등록하기 위한 샘플입니다.

## 파일 구성
- 없음 (source/ 폴더만 존재)

## 예상 init 모드
- **모드**: TEMPLATE
- **프레임워크**: sklearn (기본값 — .h5 파일 없음)
- **주의**: init 후 섹션 1에서 tensorflow import로 수동 변경 필요

## 작업 가이드
1. `init` 실행
2. 섹션 1에서 `import tensorflow as tf` 추가
3. 섹션 4에서 `tf.keras.Sequential` 모델 정의
4. 섹션 5에서 `model.fit()` 작성
