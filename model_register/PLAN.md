# 모델 등록 (유형2: AIU IDE) - 계획

<br>

## 목적

AIU IDE 에서 직접 작성한 ML/LLM 모델을 트레이닝하고 MLflow 에 등록한다.
(사용자 시나리오의 "유형2")

<br>

## 배경 — 기존 자산 재사용

이 기능은 `gen-ai-agent-gateway` 브랜치의 `agent.py` 등록 흐름을 확장한 것.
이미 검증된 부분(MLflow log_model, gateway 연동, code_paths 패키징 등)을
그대로 가져와 여러 모델 유형을 지원하도록 넓힌다.

<br>

## 모델 유형 (5가지, 개선안 기준)

```
1. 순수 ML 모델
2. ML + LLM
3. LLM
4. 시스템 기반 모델
5. Dedicated LLM 모델
```

<br>

## 하고 싶은 것

- 유형별로 등록 흐름이 어떻게 달라지는지 정리
- 공통 부분(MLflow 등록, code_paths, artifacts)은 재사용
- 유형별 특수 처리만 분기

<br>

## TODO

- [ ] 5가지 모델 유형별 등록 시 필요한 정보/파일 차이 정리
- [ ] 기존 agent.py 를 어디까지 재사용하고 어디를 확장할지 결정
- [ ] AIU IDE 연동 방식 확인 (IDE 에서 어떤 형태로 넘어오는지)
