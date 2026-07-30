# Static Endpoint 생성 - 계획

<br>

## 목적

검증된 모델을 고도화된 Static Endpoint 로 배포하여, 레거시 시스템과
단절 없는 연동을 보장하는 전사적 AI Serving 엔진을 구축한다.

<br>

## 배경

- 지금까지(gen-ai-agent-gateway 브랜치)는 MLflow 등록 → KServe 서빙까지 검증됨
- 이번 단계는 여기서 한 걸음 나아가, 서빙된 모델을 **고정된(Static) 엔드포인트**로
  노출해 레거시 시스템이 안정적으로 호출할 수 있게 하는 것

<br>

## 하고 싶은 것

- 모델(ML/LLM/시스템기반/Dedicated LLM 등 모든 유형)을 Static Endpoint 로 배포
- 배포 후에도 내부 모델 버전이 바뀌어도 엔드포인트 주소/계약은 유지
- 레거시 시스템과의 호출 규격(입출력) 단절 없이 연동

<br>

## 참고 (이전 프로젝트에서 검증된 것)

- `gen-ai-agent-gateway` 브랜치의 `agent.py` 가 MLflow 등록 흐름 보유
- KServe 엔드포인트 형식(`v1/models/<model>:predict`), predict 계약(`{"aiu_output":...}`)
  등은 `dev_note/K8s_배포_입출력_정리.md` (다른 브랜치) 참고

<br>

## TODO

- [ ] Static Endpoint 의 정확한 정의 확정 (버전 고정? 주소 고정? 둘 다?)
- [ ] 레거시 연동 어댑터 필요 여부 확인
- [ ] 모델 유형별(ML/LLM/시스템기반/Dedicated) 배포 방식 차이 정리
