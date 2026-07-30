# Evaluation / Trace 모니터링 - 계획

<br>

## 목적

배포된 모델의 품질을 Evaluation(A/B Test) 과 Trace 모니터링으로 관리한다.
"모델 서빙 대상 확대 및 Evaluation/Trace 기능 고도화" 목표의 핵심.

<br>

## 배경 — 기존 자산 재사용

`gen-ai-agent-gateway` 브랜치에 이미 있는 것:
- `judge_register.py` — judge(LLM 평가자) 등록 (평가지 + gateway LLM 선택)
- `evaluate.py` — 등록된 judge 로 수동 평가
- 자동 평가(자동 트래킹)는 gateway 인증 문제로 보류 중
  (`dev_note/게이트웨이_사용정리.md` 참고, 인프라팀 확인 대기)

<br>

## 고도화 방향

- A/B Test: 같은 질의를 여러 모델/버전에 보내 결과 비교
- Trace 모니터링: 운영 중 대화 품질을 지속적으로 관찰
- Dataset 기반 회귀 평가 (dataset_builder 기능과 연결)
- (3.14 검토) Review Queues — 사람이 직접 평가, gateway 인증 불필요
  → 자동평가 막힌 지금 상황의 대안 (`dev_note/Review_설명.png` 참고)

<br>

## 하고 싶은 것

- A/B Test 흐름 설계 (모델 A/B 에 동일 입력 → 결과 비교 → 채점)
- Trace 모니터링 대시보드/알림 필요성 검토
- Dataset(dataset_builder) 등록 후 그걸 이용한 회귀 평가 연결

<br>

## TODO

- [ ] A/B Test 구체 설계 (비교 기준, 판정 방식)
- [ ] 자동평가 인프라팀 확인 결과에 따라 자동/수동 평가 전략 재정리
- [ ] 3.14 업그레이드 시 Review Queues 도입 검토
