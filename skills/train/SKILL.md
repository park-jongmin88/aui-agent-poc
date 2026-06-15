---
name: train
description: "현재 작업 폴더의 run.py를 실행해 모델을 학습하고 MLflow에 등록한다. 작업 순서 3단계. 다음과 같은 요청에 사용: '학습해줘', '학습 시작해줘', '실행해줘', '돌려줘', 'MLflow에 등록해줘', '훈련시켜줘', '모델 학습시켜줘', '학습 돌려줘'."
---
# train - 모델 학습 및 MLflow 등록

## 절차

### 1. 현재 작업 폴더 확인
- `.current` 파일에서 현재 작업 폴더 확인
- 없으면 폴더 선택 요청

### 2. ML 패키지 설치 확인
- `mlflow` import 시도
- 설치 안 됐으면 사용자에게 확인:
  ```
  학습을 실행하려면 ML 패키지가 필요합니다.
  포함 패키지: mlflow, scikit-learn, pandas, numpy

  지금 설치할까요? (설치 후 바로 학습 진행)
  ```
- 확인 시 `setting/requirements-ml.txt` 설치 진행
- 설치 완료 후 `.aiu_state.json`에 `ml_installed: true` 기록
- 다음부터는 이 확인 생략

### 3. run.py 확인
- `skills/train/scripts/run_train.py --check-only` 실행
- run.py 없음 → init 먼저 안내
- MLflow 미설정 → config.json 확인 안내

### 4. 학습 실행
- 사용자에게 실행 의사 최종 확인
- `skills/train/scripts/run_train.py` 실행
- 실시간 출력 스트리밍
- 완료 시 run_id, 모델명, 주요 메트릭 요약
- `.aiu_state.json`에 `status: trained`, `last_run_id` 저장

## 주의
- 학습은 시간이 오래 걸릴 수 있으므로 실행 전 반드시 사용자 확인
- 병렬 tool call 사용 금지 (순차 실행 필수)
