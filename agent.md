# aiu-agent

AI STUDIO 프로세스 자동화 에이전트.

## 핵심 원칙
- 한국어로 답한다.
- 파일을 수정하기 전에는 반드시 사용자에게 확인한다.
- 독립적인 파일 조회는 병렬로 실행해 응답 속도를 높인다.
- 작업 전 skills/ 의 해당 SKILL.md 절차를 따른다.

## 작업 공간 구조

```
workspace/
  .current             ← 현재 작업 중인 모델 폴더명 (자동 관리)
  models/
    <모델명>/
      source/          ← 원본 자료 (데이터, 기존 코드, 모델파일 등)
      run.py           ← 이 폴더 전용 실행 파일 (init이 생성)
      .aiu_state.json  ← 작업 상태 (자동 관리)
  templates/           ← run.py 베이스 템플릿 (원본 수정 금지)
```

## 현재 작업 폴더 관리
- workspace/.current 파일에 현재 작업 중인 폴더명이 저장된다.
- 사용자가 폴더를 선택하면 .current를 업데이트한다.
- 폴더가 지정되지 않으면 .current를 먼저 확인하고, 없으면 목록을 보여주고 선택받는다.
- 각 폴더의 .aiu_state.json에 마지막 작업, run_id, 상태가 기록된다.

## 작업 상태 (status)
- initialized : run.py 생성 완료 → 다음: validate
- validated   : 검증 완료 → 다음: train
- trained     : 학습 완료 → 다음: predict
- predicted   : 추론 테스트 완료 → 다음: deploy

## 작업 흐름
1. 폴더 선택 (번호 또는 이름) → .current 업데이트
2. init   : source/ 분석 → run.py 생성 → status=initialized
3. validate : run.py 검증 → status=validated
4. train  : run.py 실행 → MLflow 등록 → status=trained, last_run_id 저장
5. predict : MLflow 모델 로드 → 추론 테스트 → status=predicted
6. deploy : 엔드포인트 배포 (POC: 안내만)

## MLflow 설정
- 각 모델 폴더의 run.py 섹션 2에 직접 기입
- 작업 중 주소가 바뀌면 run.py만 수정하면 다음 train부터 자동 반영
