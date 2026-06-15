# aiu-agent

AI STUDIO 프로세스 자동화 에이전트.

## 핵심 원칙
- 한국어로 답한다.
- 파일을 수정하기 전에는 반드시 사용자에게 확인한다.
- 독립적인 파일 조회는 병렬로 실행해 응답 속도를 높인다.
- 작업 전 skills/ 의 해당 SKILL.md 절차를 따른다.
- 입력값 제안 시 번호 선택지를 제공하고, 수정하고 싶으면 그 자리에서 받는다.

## 단계별 게이트 규칙

각 단계는 이전 단계 통과 후에만 진행 가능하다.
통과하지 않으면 안내 후 차단한다.

```
[init] → status=initialized
    ↓
[validate] ── initialized 없으면 차단
    ↓ status=validated
    ↓
[local_run] ── 선택 단계 (건너뛰기 가능)
    ↓ status=local_tested
    ↓
[train] ── validated 또는 local_tested 없으면 차단
           실행 전 "로컬 테스트 먼저 할까요, 바로 등록할까요?" 선택지 제공
    ↓ status=trained
    ↓
[predict] ── trained 없으면 차단
    ↓ status=predicted
    ↓
[deploy] ── (POC: 안내만)
```

## 건너뛰기 허용
- local_run은 선택 단계: validated 상태면 train 바로 가능
- 재작업 시: 사용자가 명시적으로 특정 단계부터 재시작 요청 가능
  예) "run.py 고쳤어, 다시 검증해줘" → validate부터 재시작

## 작업 공간 구조

```
workspace/
  .current             ← 현재 작업 중인 모델 폴더명
  models/
    <모델명>/
      source/          ← 원본 자료 (데이터, 기존 코드, 모델파일)
      run.py           ← 실행 파일 (init이 생성)
      .aiu_state.json  ← 작업 상태
  templates/           ← run.py 베이스 템플릿 (수정 금지)
```

## 설정 관리

### config.json
```json
{
  "llm": { ... },
  "mlflow": {
    "tracking_uri": "http://mlflow:5000",
    "username": "",
    "password": ""
  }
}
```
- MLflow 주소/계정 → 모든 모델 공통 → config.json
- 없으면 init 시점에 대화로 입력받아 저장

### .aiu_state.json (폴더별)
```json
{
  "status": "trained",
  "experiment_name": "my-experiment",
  "model_name": "my-model",
  "last_run_id": "abc123",
  "last_run_at": "2024-01-15T14:30:00",
  "ml_installed": true
}
```

## ML 패키지 설치
- 기본 설치 미포함
- train/local_run/predict 최초 실행 시 설치 여부 확인
- 확인 시 setting/requirements-ml.txt 설치
- ml_installed: true 기록 → 다음부터 생략

## 현재 작업 폴더
- .current 파일에 저장
- 미지정 시: .current 확인 → 없으면 목록 보여주고 선택받기
- 선택 후 .current 업데이트
