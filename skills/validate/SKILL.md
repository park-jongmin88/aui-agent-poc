---
name: validate
description: "현재 작업 폴더의 run.py가 9-섹션 표준 구조를 따르는지 검증한다. 작업 순서 2단계 (init 후 필수). 다음과 같은 요청에 사용: '검증해줘', '확인해줘', '맞는지 봐줘', '문제없는지 체크해줘', '구조 맞는지 봐줘', '이상없어?', '바로 학습해도 돼?'."
---
# validate - run.py 검증

## 게이트 조건
- status=initialized 없으면 차단
- "먼저 init(준비)을 실행해주세요" 안내

## 스크립트 호출 방식
```
python skills/validate/scripts/validate_run.py [폴더명]
```
- 폴더명 생략 시 `.current` 자동 사용
- 결과: `{"status": "ok", "data": {...}}`

## 절차
1. 현재 작업 폴더 확인 (.current)
2. 게이트 확인: status=initialized?
3. 스크립트 실행 후 결과 파싱:
   - `data.passed == true`:
     ```
     ✓ 검증 통과
       MLflow: {data.mlflow_uri}
       실험명: {data.experiment_name} / 모델명: {data.model_name}
     → 로컬 테스트('로컬 실행해줘') 또는 바로 학습('학습 시작해줘') 가능합니다.
     ```
   - `data.passed == false`:
     ```
     ✗ 검증 실패 — 수정이 필요합니다:
     {data.issues 목록}
     → 수정 후 다시 '검증해줘'를 실행하세요.
     ```
4. `data.warnings` 가 있으면 경고로 안내 (통과는 됨)
5. 실패 항목 수정 도움 제공 (에이전트가 run.py 직접 수정 가능)

## 검증 통과 기준
- 9섹션 모두 존재
- TODO 주석 없음
- NotImplementedError 없음
- MLFLOW_TRACKING_URI 설정됨

## 통과 시
- `.aiu_state.json`에 `status=validated` 자동 저장 (스크립트가 처리)
- 하단 툴바 자동 갱신

## 주의
- 검증만 수행, 파일을 직접 수정하지 않는다
- 단, 사용자가 수정 도움 요청 시 에이전트가 run.py 수정 후 재검증 가능
