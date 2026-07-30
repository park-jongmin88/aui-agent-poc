# 서빙 등록 (Inference / Custom LLM) - 계획

<br>

## 목적

MLflow 에 등록된 모델을 실제 추론 가능한 서비스로 서빙한다.
Inference 서비스와 Custom LLM 서빙 두 갈래를 다룬다.

<br>

## 배경 — 검증된 패턴 재사용

`gen-ai-agent-gateway` 브랜치에서 이미 KServe 기반 서빙을 검증함:
- `predict()` 계약: `{"aiu_output": ...}` 반환
- 연결정보는 Artifact(`conn.json`)로 분리
- code_paths 로 소스 동봉

이 프로젝트에서는 "타 플랫폼에서 생성한 LLM 모델 직접 서빙" 까지 범위를 넓힌다.

<br>

## 하고 싶은 것

- 순수 ML / ML+LLM / LLM / 시스템기반 / Dedicated LLM 각 유형별 서빙 방식 정리
- 타 플랫폼 LLM 모델(Langflow import 등)을 그대로 서빙할 수 있는 어댑터

<br>

## TODO

- [ ] 모델 유형별 서빙 방식 차이 정리 (KServe 표준 vs Custom Server)
- [ ] 외부에서 온 LLM 모델의 서빙 어댑터 설계
- [ ] 기존 predict() 계약을 유지할지, 유형별로 다르게 할지 결정
