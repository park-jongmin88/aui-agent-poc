---
name: local_serve
description: "로컬에 저장된 모델을 FastAPI로 서빙해 추론 엔드포인트를 제공한다. local_run 또는 train 후 언제든 실행 가능. 다음과 같은 요청에 사용: '로컬 서버 띄워줘', '로컬 서빙해줘', '로컬에서 API로 테스트하고 싶어', '엔드포인트 열어줘', '서버 켜줘', '서버 꺼줘'."
---
# local_serve - 로컬 서빙

## 게이트 조건
- status=local_tested 또는 status=trained 없으면 차단
- "먼저 로컬 테스트 또는 학습을 실행해주세요" 안내

## 개념
- workspace/results/ 의 로컬 저장 모델을 FastAPI로 서빙
- 개발자가 curl/Postman으로 직접 테스트 가능
- 에이전트가 서버 시작/종료 제어

## 절차

### 서버 시작
1. 현재 작업 폴더 + 게이트 확인
2. `skills/local_serve/scripts/start_server.py` 실행
3. 서버 정보 출력:
```
✓ 로컬 서버 시작
  주소: http://localhost:8000
  엔드포인트: POST http://localhost:8000/predict

  테스트 예시:
  curl -X POST http://localhost:8000/predict \
       -H "Content-Type: application/json" \
       -d '{"input": [1.0, 2.0, 3.0]}'

  서버 종료: '서버 꺼줘'
```

### 서버 종료
- "서버 꺼줘", "서버 종료" 요청 시
- `skills/local_serve/scripts/stop_server.py` 실행

## 주의
- 서버는 백그라운드에서 실행 (PID를 .aiu_state.json에 저장)
- 포트 충돌 시 다른 포트 제안 (8001, 8002...)
