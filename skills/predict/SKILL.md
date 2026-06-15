---
name: predict
description: "MLflow에 등록된 모델을 로컬에서 로드해 추론 테스트를 수행한다. 작업 순서 5단계 (train 후). 다음과 같은 요청에 사용: '추론해줘', '예측해줘', '테스트해줘', '결과 확인해줘', '잘 됐는지 확인해줘', '모델 동작 확인해줘', '등록된 모델로 예측해줘'."
---
# predict - 추론 테스트

## 게이트 조건
- status=trained 없으면 차단
- "먼저 train(학습)을 실행해주세요" 안내

## 스크립트 호출 방식
```
python skills/predict/scripts/run_predict.py [모델명] [버전]
```
- 모델명/버전 생략 시 `.aiu_state.json`의 model_name, last_run_id 자동 사용

## 절차
1. 현재 작업 폴더 + 게이트 확인
2. ML 패키지 확인 (train에서 설치했으면 생략)
3. 스크립트 실행 후 결과 파싱:
   ```
   ✓ 추론 테스트 완료
     모델  : {model_uri}
     결과  : {result_sample}
   ```
4. `.aiu_state.json`에 `status=predicted` 자동 저장 (스크립트가 처리)
5. 하단 툴바 자동 갱신

## 주의
- mlflow 패키지 필요 (requirements-ml.txt)
- MLflow 서버 접근 필요
