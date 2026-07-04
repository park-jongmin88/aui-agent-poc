# 의존성 정의 (requirements 생성 기준)

폴더 생성 후 requirements 를 채울 때 **이 파일을 기준으로 읽어** 반영한다.
버전을 바꾸거나 의존성을 추가하려면 이 파일만 수정하면 된다. (코드 하드코딩 금지)

## 기본 의존성 (무조건 포함, 프레임워크 중립)
- mlflow=={version}
- kserve==0.15.0
- numpy
- pandas

`{version}` 은 트래킹 URL 에서 조회한 MLflow 버전으로 치환된다.
조회 실패 시 기본값 `3.10.0` 을 사용한다.

## 모델 kind 별 프레임워크 (서버가 CPU 이므로 CPU 경량 버전)
선택한 모델에 맞는 프레임워크만 배포에 포함된다 (안 쓰는 프레임워크는 제외).

| kind | 패키지 |
|---|---|
| sklearn (.pkl/.joblib) | scikit-learn, joblib |
| pytorch (.pt/.pth)     | torch==...+cpu |
| tensorflow (.keras/.h5)| tensorflow-cpu |
| onnx (.onnx)           | onnxruntime |
| xgboost (.bst/.ubj)    | xgboost |
| safetensors            | torch+cpu, safetensors |

- **CPU 서버 전제**: torch 는 `+cpu`, tensorflow 는 `tensorflow-cpu` 를 사용해 이미지 용량/배포 시간을 줄인다.
- 프레임워크별 실제 목록은 엔진의 `requirements_packages_for_kind()` 와 일치한다.

## 추가 의존성 (필요 시 한 줄씩 추가)
# 예시:
# - some-extra-package
