---
name: localserve
description: "로컬에 저장된 모델을 FastAPI로 서빙해 추론 엔드포인트를 제공한다. local_run 또는 train 후 언제든 실행 가능. 다음과 같은 요청에 사용: '로컬 서버 띄워줘', '로컬 서빙해줘', '로컬에서 API로 테스트하고 싶어', '엔드포인트 열어줘', '서버 켜줘', '서버 꺼줘', '서버 종료해줘' 영어/추가 표현: '로컬서브', 'local serve', 'localserve', 'serve', 'API 띄워줘', '엔드포인트 띄워줘', '포트 열어줘', '서버 켜줘', '서버 꺼줘', 'stop'."
---
# local_serve - 로컬 서빙

## 경로 기준 (중요)
- **모든 경로는 스크립트가 자동으로 계산한다. 에이전트가 직접 경로를 추론하거나 판단하지 않는다.**
- 현재 작업 디렉토리(cwd)나 OS 경로와 무관하게 동작한다.
- 경로를 "못 찾는다"고 판단하기 전에 반드시 스크립트를 먼저 실행해 결과를 확인한다.

## 게이트 조건
- status=local_tested 없으면 차단 (로컬 테스트 결과물 필요)
- train만 한 경우: MLflow에만 등록되어 로컬 파일이 없으므로 local_run 안내

## 스크립트 호출 방식
```
# 서버 시작
python skills/localserve/scripts/start_server.py [폴더명] [--port 8000]

# 서버 종료
python skills/localserve/scripts/stop_server.py [폴더명]
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
