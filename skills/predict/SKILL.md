---
name: predict
description: "MLflow에 등록된 모델을 로컬에서 로드해 추론 테스트를 수행한다. 작업 순서 5단계 (train 후). 다음과 같은 요청에 사용: '추론해줘', '예측해줘', '테스트해줘', '결과 확인해줘', '잘 됐는지 확인해줘', '모델 동작 확인해줘', '등록된 모델로 예측해줘'."
---
# predict - 추론 테스트

## 게이트 조건
- status=trained 없으면 차단
- "먼저 train(학습)을 실행해주세요" 안내

## 절차
1. 현재 작업 폴더 + 게이트 확인
2. ML 패키지 설치 확인 (train에서 했으면 생략)
3. `skills/predict/scripts/run_predict.py` 실행
   - .aiu_state.json의 last_run_id 또는 model_name으로 자동 로드
4. 결과 보고
5. `.aiu_state.json`에 `status=predicted` 저장
