# [무조건] 시작 시 .env 체크

이 규칙은 7단계 흐름보다 **먼저** 통과해야 하는 관문이다.

## 절차
1. 루트 `.env` 파일이 있는지 확인한다.
2. **없으면**: `.env` 를 생성해주고(아래 템플릿), 값을 작성하라고 사용자에게 안내한 뒤 대기한다.
3. **있으나 `MLFLOW_TRACKING_URI` 가 비어 있으면**: 입력하라고 안내하고 다음 단계로 진행하지 않는다.
4. 검증은 `scripts/00-setup/check_env.py` 로 수행한다.

## .env 템플릿
```
MLFLOW_TRACKING_URI=
MLFLOW_TRACKING_USERNAME=
MLFLOW_TRACKING_PASSWORD=
MLFLOW_VERSION=
```

## 필수 / 선택
- 필수: `MLFLOW_TRACKING_URI`
- 선택: `MLFLOW_TRACKING_USERNAME`, `MLFLOW_TRACKING_PASSWORD`
- 선택: `MLFLOW_VERSION` — 값이 있으면 requirements 의 mlflow 버전으로 **최우선** 사용한다.
  (없으면 트래킹 URL 조회 → 실패 시 기본값 3.10.0)

## 실행
```
python .opencode/scripts/00-setup/check_env.py --project .
```
