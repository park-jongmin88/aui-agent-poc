---
name: localrun
description: "run.py를 MLflow 등록 없이 로컬에서만 실행해 모델 동작을 확인한다. 선택 단계 (validate 후, train 전). 다음과 같은 요청에 사용: '로컬에서 테스트해줘', '로컬 실행해줘', 'MLflow 없이 돌려봐', '동작 확인해줘', '먼저 테스트해보고 싶어', '로컬에서 먼저 확인해줘'."
---
# local_run - 로컬 테스트 (선택 단계)

## 경로 기준 (중요)
- **모든 경로는 스크립트가 자동으로 계산한다. 에이전트가 직접 경로를 추론하거나 판단하지 않는다.**
- 현재 작업 디렉토리(cwd)나 OS 경로와 무관하게 동작한다.
- 경로를 "못 찾는다"고 판단하기 전에 반드시 스크립트를 먼저 실행해 결과를 확인한다.

## 게이트 조건
- status=validated 없으면 차단

## 스크립트 호출 방식
```
python skills/localrun/scripts/run_local.py [폴더명]
```
실행 중 스트리밍:
- `{"status": "running"}` → 시작
- `{"status": "progress", "line": "..."}` → 출력 라인
- `{"status": "ok", "data": {...}}` → 완료

## 절차
1. 현재 작업 폴더 + 게이트 확인
2. ML 패키지 확인 (없으면 설치 안내)
3. 스크립트 실행 → 실시간 출력
4. 완료 시 결과 파싱:
   ```
   ✓ 로컬 테스트 완료 ({elapsed}s)
     저장 위치: workspace/results/{폴더명}/
     모델 파일: model.pkl
     accuracy : {accuracy}
   → 이상 없으면 'MLflow에 등록해줘'로 train을 진행하세요.
   → 로컬 서빙 테스트: '로컬 서버 띄워줘'
   ```
5. `.aiu_state.json`에 `status=local_tested` 자동 저장 (스크립트가 처리)

## 개념
- MLflow mock으로 대체 실행 (등록 없이 학습만)
- 결과 모델 → workspace/results/<폴더명>/ 저장
