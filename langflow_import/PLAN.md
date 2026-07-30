# Langflow Import (유형1) - 계획

<br>

## 목적

타 플랫폼(Langflow)에서 생성한 파이프라인을 export 한 json 파일을 받아,
트레이닝 후 MLflow 에 등록한다. (사용자 시나리오의 "유형1")

<br>

## 흐름

```
Langflow export 파일 (json)
    ↓
파싱 (노드/엣지 구조 → 우리 파이프라인 구조로 변환)
    ↓
트레이닝 (필요 시)
    ↓
MLflow 실험 / 모델 등록
```

<br>

## 배경 — 서빙 대상 확대와 연결

이 기능은 "모델 서빙 대상 확대" 목표의 구체적인 첫 사례다.
타 플랫폼에서 만든 LLM 모델을 우리 서빙/Ops 체계로 끌어들이는 통로.

<br>

## 하고 싶은 것

- Langflow export json 구조 분석 (노드 타입, 연결 관계)
- 우리 에이전트 파이프라인(prompt/rag/tool/llm 등)과의 매핑 규칙 정의
- 매핑 후 기존 `agent.py` 등록 흐름 재사용

<br>

## TODO

- [ ] Langflow export json 샘플 확보 및 구조 분석
- [ ] 노드 타입 ↔ 우리 asset(prompt/rag/tool/llm) 매핑표 작성
- [ ] 매핑 불가능한 노드 발생 시 처리 방침 (에러 vs 부분 변환)
