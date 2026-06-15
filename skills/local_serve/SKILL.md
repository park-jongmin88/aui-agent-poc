---
name: local_serve
description: "로컬에 저장된 모델을 FastAPI로 서빙해 추론 엔드포인트를 제공한다. local_run 또는 train 후 언제든 실행 가능. 다음과 같은 요청에 사용: '로컬 서버 띄워줘', '로컬 서빙해줘', '로컬에서 API로 테스트하고 싶어', '엔드포인트 열어줘', '서버 켜줘', '서버 꺼줘', '서버 종료해줘'."
---
# local_serve - 로컬 서빙

## 게이트 조건
- status=local_tested 없으면 차단 (로컬 테스트 결과물 필요)
- train만 한 경우: MLflow에만 등록되어 로컬 파일이 없으므로 local_run 안내

## 스크립트 호출 방식
```
# 서버 시작
python skills/local_serve/scripts/start_server.py [폴더명] [--port 8000]

# 서버 종료
python skills/local_serve/scripts/stop_server.py [폴더명]
```

## 절차

### 서버 시작
1. 게이트 확인
2. `fastapi`, `uvicorn` 패키지 확인 (없으면 설치 안내)
3. `start_server.py` 실행 후 결과 파싱:
   ```
   ✓ 로컬 서버 시작 (PID: {pid})
     주소    : http://localhost:{port}
     모델    : {model}
     추론    : POST http://localhost:{port}/predict
     테스트  : curl -X POST ... -d '{"input": [...]}'
     서버 종료: '서버 꺼줘'
   ```
4. `.aiu_state.json`에 serve_pid, serve_port 자동 저장

### 서버 종료
1. `stop_server.py` 실행
2. 결과 안내 후 상태 초기화

## 주의
- 서버는 백그라운드 실행 (PID 저장)
- 포트 충돌 시 자동으로 다음 포트 사용 (8000~8009)
- PyTorch 모델은 모델 클래스 정의 필요 (start_server.py 수동 수정)
