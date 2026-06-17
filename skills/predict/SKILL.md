---
name: predict
description: "등록된 모델로 추론 테스트를 수행한다. 두 가지 방식: ① 로컬 추론(MLflow 로드) ② Endpoint 추론(배포 후 URL 요청). 작업 순서 5단계. 다음과 같은 요청에 사용: '추론해줘', '예측해줘', '테스트해줘', '결과 확인해줘', '잘 됐는지 확인해줘', '모델 동작 확인해줘', '엔드포인트 추론 테스트', '배포된 모델 테스트' 영어/추가 표현: '프리딕트', 'predict', 'inference', '인퍼런스', '결과 봐줘', '예측 테스트', '모델 써봐', '잘 나와?'."
---
# predict - 추론 테스트

## 두 가지 추론 방식

추론 요청 시 상황에 맞게 선택지를 제시한다:

### ① 로컬 추론 (배포 전)
- MLflow에 등록된 모델을 로컬에 로드해서 테스트
- 모델이 제대로 등록됐는지 확인하는 용도
- 스크립트: `run_predict.py`
- `mlflow.pyfunc.load_model` 로 로드 → input_example.json 으로 추론

### ② Endpoint 추론 (배포 후)
- 배포된 AI Studio Endpoint URL로 HTTP 요청
- 실제 서빙 환경 동작 확인
- 스크립트: `inference_test.py`
- input_example.json 을 그대로 POST → 응답 확인

> 배포(deploy) 전이면 ①, 배포 후면 ② 를 사용한다.
> 사용자가 "엔드포인트 추론", "배포된 모델 테스트" 라고 하면 ②.

## input_example.json (KServe 형식)
```json
{"input": [{"name": "modelname", "shape": [10, 4], "datatype": "ndarray", "data": [...]}]}
```
- run.py 실행 시 자동 생성됨
- 두 추론 방식 모두 이 파일을 입력으로 사용

## 경로 기준 (중요)
- 모든 경로는 스크립트가 자동 계산한다. 에이전트가 직접 추론하지 않는다.
- 경로 문제를 판단하기 전에 반드시 스크립트를 먼저 실행한다.

## 게이트 조건
- ① 로컬 추론: status=trained 필요
- ② Endpoint 추론: 배포 후 endpoint_url 필요 (또는 --url 직접 지정)

## 스크립트 호출 방식
```
# ① 로컬 추론
python skills/predict/scripts/run_predict.py [폴더명]

# ② Endpoint 추론
python skills/predict/scripts/inference_test.py [폴더명] [--url ENDPOINT_URL]
```
- 폴더명 생략 시 `.current` 자동 사용
- Endpoint URL은 deploy 시 상태에 저장된 값을 자동 사용 (--url로 직접 지정 가능)

## 절차
1. 현재 작업 폴더 + 게이트 확인
2. 추론 방식 선택 (로컬 / Endpoint)
3. 스크립트 실행 후 결과 파싱 (추론 결과 / 응답 출력)
4. 실패 시 `data.message` 로 원인 안내
5. 로컬 추론 성공 시 `status=predicted` 자동 저장

## 주의
- mlflow, requests 패키지 필요 (install 시 자동 설치됨)
- MLflow 서버 또는 Endpoint 접근 필요
