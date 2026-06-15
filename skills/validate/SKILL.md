---
name: validate
description: "현재 작업 폴더의 run.py가 9-섹션 표준 구조를 따르는지 검증한다. 작업 순서 2단계 (init 후 필수). 다음과 같은 요청에 사용: '검증해줘', '확인해줘', '맞는지 봐줘', '문제없는지 체크해줘', '구조 맞는지 봐줘', '이상없어?', '바로 학습해도 돼?'."
---
# validate - run.py 검증

## 게이트 조건
- status=initialized 없으면 차단
- "먼저 init(준비)을 실행해주세요" 안내

## 절차
1. 현재 작업 폴더 확인 (.current)
2. 게이트 확인: status=initialized?
3. `skills/validate/scripts/validate_run.py [폴더명]` 실행
4. 검증 항목:
   - **구조**: 9섹션 존재 여부, 필수 함수 존재
   - **내용**: TODO 미입력 항목, NotImplementedError 존재
   - **설정**: MLflow 주소 설정 여부
   - **메타**: 실험명/모델명 기본값 여부 (경고)
5. 결과 보고:
   - ✓ 통과: "검증 완료 — 로컬 테스트 또는 학습 가능"
             `.aiu_state.json`에 `status=validated` 저장
   - ✗ 실패: 항목별 상세 안내 (라인번호 포함)
             에이전트가 수정 도움 제공
6. 실패 항목 수정 후 재검증 권장

## 검증 통과 기준
- 9섹션 모두 존재
- TODO 주석 없음
- NotImplementedError 없음
- MLFLOW_TRACKING_URI 설정됨

## 주의
- 검증만 수행, 파일 수정하지 않는다
- 경고(warning)는 통과 처리 (실험명/모델명 기본값 등)
